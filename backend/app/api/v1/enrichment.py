import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.domain import Business, Campaign, EnrichmentJob, BusinessSocial, BusinessCandidateField
from app.schemas.enrichment import (
    EnrichmentJobOut,
    BusinessEnrichmentDetailOut,
    BatchEnrichmentResponse,
    BusinessSocialOut,
    BusinessCandidateFieldOut
)
from app.services.enrichment import execute_business_enrichment, execute_campaign_batch_enrichment
from app.services.quality import calculate_campaign_data_quality

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/businesses/{business_id}/enrich", response_model=Dict[str, Any])
def enrich_single_business(
    business_id: str,
    background_tasks: BackgroundTasks,
    provider: str = Query("website", description="Enrichment provider name"),
    db: Session = Depends(get_db)
):
    """
    Task 14: POST /api/businesses/{id}/enrich
    Triggers business profile enrichment asynchronously or synchronously.
    """
    try:
        b_uuid = uuid.UUID(business_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid business ID format")

    business = db.query(Business).filter(Business.id == b_uuid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    job = EnrichmentJob(
        id=uuid.uuid4(),
        business_id=b_uuid,
        provider=provider,
        status="queued"
    )
    db.add(job)
    db.commit()

    # Execute enrichment task in background so HTTP response does not block
    background_tasks.add_task(execute_business_enrichment, str(b_uuid), str(job.id), provider)

    return {
        "status": "queued",
        "job_id": str(job.id),
        "business_id": business_id,
        "provider": provider,
        "message": "Business profile enrichment job queued successfully."
    }


@router.get("/businesses/{business_id}/enrichment", response_model=BusinessEnrichmentDetailOut)
def get_business_enrichment_detail(
    business_id: str,
    db: Session = Depends(get_db)
):
    """
    Task 14: GET /api/businesses/{id}/enrichment
    Get enrichment details, social profiles, candidate fields, and jobs for a business.
    """
    try:
        b_uuid = uuid.UUID(business_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid business ID format")

    business = db.query(Business).filter(Business.id == b_uuid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    socials = db.query(BusinessSocial).filter(BusinessSocial.business_id == b_uuid).all()
    candidates = db.query(BusinessCandidateField).filter(BusinessCandidateField.business_id == b_uuid).all()
    jobs = db.query(EnrichmentJob).filter(EnrichmentJob.business_id == b_uuid).order_by(EnrichmentJob.created_at.desc()).all()

    return BusinessEnrichmentDetailOut(
        business_id=str(business.id),
        name=business.name,
        website=business.website,
        description=business.description,
        socials=socials,
        candidates=candidates,
        jobs=jobs,
        quality_score={
            "phone_present": 100.0 if any(c.type in ["phone", "mobile"] for c in business.contacts) else 0.0,
            "website_present": 100.0 if business.website else 0.0,
            "email_present": 100.0 if any(c.type == "email" for c in business.contacts) else 0.0,
            "social_present": 100.0 if socials else 0.0
        }
    )


@router.get("/businesses/{business_id}/enrichment/jobs", response_model=List[EnrichmentJobOut])
def get_business_enrichment_jobs(
    business_id: str,
    db: Session = Depends(get_db)
):
    """
    Task 14: GET /api/businesses/{id}/enrichment/jobs
    Get job history for business enrichment.
    """
    try:
        b_uuid = uuid.UUID(business_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid business ID format")

    jobs = db.query(EnrichmentJob).filter(EnrichmentJob.business_id == b_uuid).order_by(EnrichmentJob.created_at.desc()).all()
    return jobs


@router.post("/campaigns/{campaign_id}/enrich", response_model=Dict[str, Any])
def enrich_campaign_leads(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    provider: str = Query("website", description="Enrichment provider name"),
    db: Session = Depends(get_db)
):
    """
    Task 14: POST /api/campaigns/{id}/enrich
    Triggers batch lead enrichment across all businesses in a campaign.
    """
    try:
        c_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    campaign = db.query(Campaign).filter(Campaign.id == c_uuid).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Queue background task for non-blocking batch execution
    background_tasks.add_task(execute_campaign_batch_enrichment, str(c_uuid), provider)

    return {
        "status": "queued",
        "campaign_id": campaign_id,
        "provider": provider,
        "message": f"Batch enrichment for campaign '{campaign.name}' queued successfully."
    }


@router.get("/campaigns/{campaign_id}/enrichment", response_model=Dict[str, Any])
def get_campaign_enrichment_status(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """
    Task 14: GET /api/campaigns/{id}/enrichment
    Returns campaign enrichment metrics, job counts, and coverages.
    """
    try:
        c_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    campaign = db.query(Campaign).filter(Campaign.id == c_uuid).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    quality = calculate_campaign_data_quality(db, c_uuid)

    jobs = db.query(EnrichmentJob).filter(EnrichmentJob.campaign_id == c_uuid).all()
    completed_jobs = len([j for j in jobs if j.status == "completed"])
    running_jobs = len([j for j in jobs if j.status == "running"])
    failed_jobs = len([j for j in jobs if j.status == "failed"])

    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "total_jobs": len(jobs),
        "completed_jobs": completed_jobs,
        "running_jobs": running_jobs,
        "failed_jobs": failed_jobs,
        "quality_metrics": quality
    }
