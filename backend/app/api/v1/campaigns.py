import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Campaign, DiscoveryJob
from app.schemas.campaign import CampaignCreate, CampaignUpdate, CampaignResponse, DiscoveryJobResponse
from app.services.discovery import execute_discovery_job
from app.services.quality import calculate_campaign_data_quality

router = APIRouter()

def build_campaign_response(campaign: Campaign, db: Session) -> CampaignResponse:
    duration = None
    if campaign.started_at and campaign.completed_at:
        # Handles naive / aware datetime math
        start_ts = campaign.started_at.timestamp()
        end_ts = campaign.completed_at.timestamp()
        duration = round(max(end_ts - start_ts, 0.0), 1)

    jobs_resp = []
    for j in campaign.jobs:
        j_duration = None
        if j.started_at and j.completed_at:
            j_duration = round(max(j.completed_at.timestamp() - j.started_at.timestamp(), 0.0), 1)

        jobs_resp.append(DiscoveryJobResponse(
            id=j.id,
            campaign_id=j.campaign_id,
            provider=j.provider or "mock",
            status=j.status or "queued",
            target_count=j.target_count or 0,
            discovered_count=j.discovered_count or 0,
            unique_count=j.unique_count or 0,
            duplicate_count=j.duplicate_count or 0,
            failed_count=j.failed_count or 0,
            error_message=j.error_message,
            duration_seconds=j_duration,
            started_at=j.started_at,
            completed_at=j.completed_at,
            created_at=j.created_at
        ))

    data_quality = calculate_campaign_data_quality(db, campaign.id)

    return CampaignResponse(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        category=campaign.category,
        keywords=campaign.keywords or [],
        locations=campaign.locations or [],
        target_leads=campaign.target_leads or 100,
        min_rating=float(campaign.min_rating) if campaign.min_rating else 0.0,
        min_reviews=campaign.min_reviews or 0,
        require_phone=campaign.require_phone or False,
        require_website=campaign.require_website or False,
        require_email=campaign.require_email or False,
        provider=campaign.provider or "mock",
        status=campaign.status or "draft",
        discovered_count=campaign.discovered_count or 0,
        unique_count=campaign.unique_count or 0,
        duplicate_count=campaign.duplicate_count or 0,
        failed_count=campaign.failed_count or 0,
        duration_seconds=duration,
        data_quality=data_quality,
        created_at=campaign.created_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
        jobs=jobs_resp
    )

@router.post("", response_model=CampaignResponse, status_code=201)
@router.post("/", response_model=CampaignResponse, status_code=201)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    if not payload.name or not payload.name.strip():
        raise HTTPException(status_code=400, detail="Campaign name is required")

    if not payload.category and not payload.keywords:
        raise HTTPException(status_code=400, detail="At least one category or keyword is required")

    campaign_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    campaign = Campaign(
        id=campaign_id,
        name=payload.name.strip(),
        description=payload.description,
        category=payload.category,
        keywords=payload.keywords,
        locations=payload.locations,
        target_leads=payload.target_leads,
        min_rating=payload.min_rating,
        min_reviews=payload.min_reviews,
        require_phone=payload.require_phone,
        require_website=payload.require_website,
        require_email=payload.require_email,
        provider=payload.provider or "mock",
        status="draft",
        created_at=now
    )

    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return build_campaign_response(campaign, db)

@router.get("", response_model=List[CampaignResponse])
@router.get("/", response_model=List[CampaignResponse])
def list_campaigns(db: Session = Depends(get_db)):
    campaigns = db.query(Campaign).order_by(Campaign.created_at.desc()).all()
    return [build_campaign_response(c, db) for c in campaigns]

@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return build_campaign_response(campaign, db)

@router.patch("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(campaign_id: UUID, payload: CampaignUpdate, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status in ["running", "completed"]:
        raise HTTPException(status_code=400, detail="Cannot edit a running or completed campaign")

    update_data = payload.model_dump(exclude_unset=True)
    for field, val in update_data.items():
        if val is not None:
            setattr(campaign, field, val)

    db.commit()
    db.refresh(campaign)
    return build_campaign_response(campaign, db)

@router.post("/{campaign_id}/start", response_model=CampaignResponse)
def start_campaign(
    campaign_id: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status in ["completed", "cancelled"]:
        raise HTTPException(
            status_code=400,
            detail=f"Campaign is in '{campaign.status}' state and cannot be restarted directly."
        )

    if campaign.status == "running":
        return build_campaign_response(campaign, db)

    now = datetime.now(timezone.utc)

    # Create a new discovery job
    job_id = uuid.uuid4()
    job = DiscoveryJob(
        id=job_id,
        campaign_id=campaign.id,
        provider=campaign.provider or "mock",
        status="queued",
        target_count=campaign.target_leads,
        created_at=now
    )
    db.add(job)

    campaign.status = "queued"
    if not campaign.started_at:
        campaign.started_at = now

    db.commit()
    db.refresh(campaign)

    # Dispatch asynchronous background task execution
    background_tasks.add_task(execute_discovery_job, str(campaign.id), str(job_id))

    return build_campaign_response(campaign, db)

@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
def pause_campaign(campaign_id: UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in ["running", "queued"]:
        raise HTTPException(status_code=400, detail=f"Cannot pause campaign in state '{campaign.status}'")

    campaign.status = "paused"
    for j in campaign.jobs:
        if j.status in ["running", "queued"]:
            j.status = "paused"

    db.commit()
    db.refresh(campaign)
    return build_campaign_response(campaign, db)

@router.post("/{campaign_id}/cancel", response_model=CampaignResponse)
def cancel_campaign(campaign_id: UUID, db: Session = Depends(get_db)):
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = "cancelled"
    for j in campaign.jobs:
        if j.status in ["running", "queued", "paused"]:
            j.status = "cancelled"

    db.commit()
    db.refresh(campaign)
    return build_campaign_response(campaign, db)
