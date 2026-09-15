import uuid
import math
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.core.database import SessionLocal
from app.models.domain import Business, Campaign, LeadScore, SourceRecord
from app.schemas.scoring import (
    LeadScoreOut,
    CampaignScoreMetricsOut,
    QualifiedLeadItemOut,
    QualifiedLeadsResponse
)
from app.services.scoring import score_business, score_campaign_leads, calculate_lead_score
from app.services.export import generate_campaign_leads_csv

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/businesses/{business_id}/score", response_model=LeadScoreOut)
def get_business_score(
    business_id: str,
    campaign_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Task 12: GET /api/businesses/{id}/score
    Get explainable score detail for a business.
    """
    try:
        b_uuid = uuid.UUID(business_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid business ID format")

    business = db.query(Business).filter(Business.id == b_uuid).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    c_uuid = None
    if campaign_id:
        try:
            c_uuid = uuid.UUID(campaign_id)
        except Exception:
            pass

    score_rec = db.query(LeadScore).filter(LeadScore.business_id == b_uuid)
    if c_uuid:
        score_rec = score_rec.filter(LeadScore.campaign_id == c_uuid)
    score_rec = score_rec.order_by(LeadScore.created_at.desc()).first()

    if not score_rec:
        # Score on-the-fly if not scored yet
        res = score_business(b_uuid, campaign_id=c_uuid, db=db)
        if res.get("status") != "success":
            raise HTTPException(status_code=500, detail="Failed to calculate lead score")
        score_rec = db.query(LeadScore).filter(LeadScore.business_id == b_uuid).order_by(LeadScore.created_at.desc()).first()

    return score_rec


@router.post("/businesses/{business_id}/score", response_model=LeadScoreOut)
def trigger_business_score(
    business_id: str,
    campaign_id: Optional[str] = Query(None),
    ruleset: str = Query("default_v1"),
    db: Session = Depends(get_db)
):
    """
    Task 12: POST /api/businesses/{id}/score
    Trigger scoring/re-scoring of a business.
    """
    try:
        b_uuid = uuid.UUID(business_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid business ID format")

    res = score_business(b_uuid, campaign_id=campaign_id, ruleset=ruleset, db=db)
    if res.get("status") != "success":
        raise HTTPException(status_code=404 if "not found" in res.get("error", "").lower() else 500, detail=res.get("error"))

    score_rec = db.query(LeadScore).filter(LeadScore.id == uuid.UUID(res["score_id"])).first()
    return score_rec


@router.post("/campaigns/{campaign_id}/score", response_model=Dict[str, Any])
def trigger_campaign_scoring(
    campaign_id: str,
    ruleset: str = Query("default_v1"),
    db: Session = Depends(get_db)
):
    """
    Task 12: POST /api/campaigns/{id}/score
    Triggers batch lead scoring across all businesses in a campaign.
    """
    try:
        c_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    campaign = db.query(Campaign).filter(Campaign.id == c_uuid).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    res = score_campaign_leads(c_uuid, ruleset=ruleset)
    return res


@router.get("/campaigns/{campaign_id}/scores", response_model=CampaignScoreMetricsOut)
def get_campaign_scores_metrics(
    campaign_id: str,
    db: Session = Depends(get_db)
):
    """
    Task 12 & 14: GET /api/campaigns/{id}/scores
    Aggregates campaign scores, data quality, tier counts, lifecycle status breakdown, and contactability percentages.
    """
    try:
        c_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    campaign = db.query(Campaign).filter(Campaign.id == c_uuid).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Find campaign businesses
    source_records = db.query(SourceRecord).filter(SourceRecord.raw_data.isnot(None)).all()
    b_ids = set()
    for sr in source_records:
        if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(c_uuid):
            if sr.business_id:
                b_ids.add(sr.business_id)

    if not b_ids:
        businesses = db.query(Business).limit(100).all()
    else:
        businesses = db.query(Business).filter(Business.id.in_(b_ids)).all()

    total_count = len(businesses)
    if total_count == 0:
        return CampaignScoreMetricsOut(
            campaign_id=campaign_id,
            total_scored=0,
            qualified_count=0,
            disqualified_count=0,
            avg_score=0.0,
            avg_data_quality=0.0,
            contactable_percentage=0.0,
            email_availability_percentage=0.0,
            phone_availability_percentage=0.0,
            website_availability_percentage=0.0,
            tier_counts={"HOT": 0, "WARM": 0, "COOL": 0, "LOW": 0},
            lifecycle_counts={"NEW": 0, "ENRICHED": 0, "QUALIFIED": 0, "SALES_READY": 0, "DISQUALIFIED": 0}
        )

    scores_list = []
    tier_counts = {"HOT": 0, "WARM": 0, "COOL": 0, "LOW": 0}
    lifecycle_counts = {"NEW": 0, "ENRICHED": 0, "QUALIFIED": 0, "SALES_READY": 0, "DISQUALIFIED": 0}
    
    qualified_cnt = 0
    disqualified_cnt = 0
    dq_scores = []
    phone_cnt = 0
    email_cnt = 0
    website_cnt = 0
    contactable_cnt = 0

    for b in businesses:
        ls = db.query(LeadScore).filter(LeadScore.business_id == b.id).order_by(LeadScore.created_at.desc()).first()
        if not ls:
            # Score if missing
            res = score_business(b.id, campaign_id=c_uuid, db=db)
            ls = db.query(LeadScore).filter(LeadScore.business_id == b.id).order_by(LeadScore.created_at.desc()).first()

        sc_val = ls.total_score if ls else b.lead_score
        scores_list.append(sc_val)

        t_val = ls.tier if ls else ("HOT" if sc_val >= 80 else ("WARM" if sc_val >= 60 else ("COOL" if sc_val >= 40 else "LOW")))
        tier_counts[t_val] = tier_counts.get(t_val, 0) + 1

        l_val = ls.lifecycle_status if ls else b.lifecycle_status
        lifecycle_counts[l_val] = lifecycle_counts.get(l_val, 0) + 1

        if ls and ls.disqualified:
            disqualified_cnt += 1
        else:
            qualified_cnt += 1

        if ls:
            dq_scores.append(ls.data_quality_score)

        has_p = any(c.type in ["phone", "mobile"] for c in b.contacts)
        has_e = any(c.type == "email" for c in b.contacts)
        has_w = bool(b.website)

        if has_p: phone_cnt += 1
        if has_e: email_cnt += 1
        if has_w: website_cnt += 1
        if has_p or has_e: contactable_cnt += 1

    avg_sc = round(sum(scores_list) / len(scores_list), 2) if scores_list else 0.0
    avg_dq = round(sum(dq_scores) / len(dq_scores), 2) if dq_scores else 0.0

    return CampaignScoreMetricsOut(
        campaign_id=campaign_id,
        total_scored=total_count,
        qualified_count=qualified_cnt,
        disqualified_count=disqualified_cnt,
        avg_score=avg_sc,
        avg_data_quality=avg_dq,
        contactable_percentage=round((contactable_cnt / total_count) * 100, 1),
        email_availability_percentage=round((email_cnt / total_count) * 100, 1),
        phone_availability_percentage=round((phone_cnt / total_count) * 100, 1),
        website_availability_percentage=round((website_cnt / total_count) * 100, 1),
        tier_counts=tier_counts,
        lifecycle_counts=lifecycle_counts
    )


@router.get("/campaigns/{campaign_id}/qualified-leads", response_model=QualifiedLeadsResponse)
def get_qualified_leads(
    campaign_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    minimum_score: Optional[int] = Query(None),
    sort_by: str = Query("highest_score", description="highest_score, lowest_score, newest, recently_enriched"),
    db: Session = Depends(get_db)
):
    """
    Task 12 & 15: GET /api/campaigns/{id}/qualified-leads
    Filter & sort qualified leads for a campaign.
    Default sorting: highest score first.
    """
    try:
        c_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    source_records = db.query(SourceRecord).filter(SourceRecord.raw_data.isnot(None)).all()
    b_ids = set()
    for sr in source_records:
        if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(c_uuid):
            if sr.business_id:
                b_ids.add(sr.business_id)

    query = db.query(Business)
    if b_ids:
        query = query.filter(Business.id.in_(b_ids))

    if search:
        query = query.filter(Business.name.ilike(f"%{search}%"))

    if category:
        query = query.filter(Business.category.ilike(f"%{category}%"))

    if minimum_score is not None:
        query = query.filter(Business.lead_score >= minimum_score)

    if status:
        query = query.filter(Business.lifecycle_status.ilike(status))

    # Apply sorting
    if sort_by == "highest_score":
        query = query.order_by(desc(Business.lead_score), desc(Business.created_at))
    elif sort_by == "lowest_score":
        query = query.order_by(asc(Business.lead_score), desc(Business.created_at))
    elif sort_by == "recently_enriched":
        query = query.order_by(desc(Business.last_verified_at), desc(Business.created_at))
    else:  # newest
        query = query.order_by(desc(Business.created_at))

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    businesses = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for b in businesses:
        ls = db.query(LeadScore).filter(LeadScore.business_id == b.id).order_by(LeadScore.created_at.desc()).first()

        # Apply tier filter if requested
        if tier and ls and ls.tier.upper() != tier.upper():
            continue

        loc = b.locations[0] if b.locations else None
        phone_val = next((c.value for c in b.contacts if c.type in ["phone", "mobile"]), None)
        email_val = next((c.value for c in b.contacts if c.type == "email"), None)

        sc = ls.total_score if ls else b.lead_score
        t_val = ls.tier if ls else ("HOT" if sc >= 80 else ("WARM" if sc >= 60 else ("COOL" if sc >= 40 else "LOW")))
        st_val = ls.lifecycle_status if ls else b.lifecycle_status
        is_qual = ls.is_qualified if ls else True

        items.append(QualifiedLeadItemOut(
            id=str(b.id),
            name=b.name,
            category=b.category,
            city=loc.city if loc else None,
            state=loc.state if loc else None,
            phone=phone_val,
            email=email_val,
            website=b.website,
            total_score=sc,
            tier=t_val,
            lifecycle_status=st_val,
            is_qualified=is_qual,
            positive_signals=ls.positive_signals if ls else [],
            reasons=ls.reasons if ls else []
        ))

    return QualifiedLeadsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get("/campaigns/{campaign_id}/export/csv")
def export_qualified_leads_csv(
    campaign_id: str,
    qualified_only: bool = Query(False, description="Filter out disqualified leads")
):
    """
    Task 16: GET /api/campaigns/{id}/export/csv
    Generates and downloads a CSV export file of campaign leads.
    """
    try:
        c_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign ID format")

    csv_content = generate_campaign_leads_csv(c_uuid, qualified_only=qualified_only)
    filename = f"campaign_{campaign_id[:8]}_leads.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
