import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models.domain import Campaign, Business, SourceRecord, LeadScore, PipelineJob
from app.providers.osm import parse_search_query
from app.services.pipeline import start_pipeline_job, get_pipeline_job_status
from app.services.deduplication import deduplicate_campaign_records

router = APIRouter()

class QuickSearchRequest(BaseModel):
    query: Optional[str] = Field(None, description="Natural search query, e.g. 'Restaurants in Mumbai'")
    category: Optional[str] = Field("Restaurants", description="Business category or industry")
    location: Optional[str] = Field("Mumbai", description="City or locality")
    quantity: int = Field(100, ge=10, le=10000, description="Target lead quantity (100, 500, 1000, 5000, 10000)")
    provider: str = Field("osm", description="Data provider ('osm', 'mock', 'authorized')")

@router.post("/find-businesses")
def find_businesses(req: QuickSearchRequest, db: Session = Depends(get_db)):
    """
    Core Phase 7 Business Data Finder API.
    Parses search input, provisions a data discovery campaign, and starts background data collection.
    """
    category = req.category or "Commercial"
    location = req.location or "Mumbai"

    # Natural query parsing if query string passed
    if req.query and req.query.strip():
        parsed = parse_search_query(req.query.strip())
        category = parsed.get("category") or category
        if parsed.get("location"):
            location = parsed.get("location")

    camp_name = f"{category} in {location}"

    campaign = Campaign(
        id=uuid.uuid4(),
        name=camp_name,
        category=category,
        keywords=[category],
        locations=[location],
        target_leads=req.quantity,
        provider=req.provider or "osm",
        status="QUEUED",
        created_at=datetime.now(timezone.utc)
    )
    db.add(campaign)
    db.commit()

    # Launch pipeline job
    job_res = start_pipeline_job(campaign.id, batch_size=100)
    job_id = job_res.get("job_id")

    return {
        "status": "success",
        "campaign_id": str(campaign.id),
        "job_id": job_id,
        "search_name": camp_name,
        "category": category,
        "location": location,
        "requested_quantity": req.quantity,
        "provider": campaign.provider,
        "message": "Business Data Finder collection initiated"
    }


@router.get("/results/{campaign_id}")
def get_search_results(
    campaign_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    search: Optional[str] = None,
    contactable_only: bool = False,
    db: Session = Depends(get_db)
):
    """
    Retrieves full results dataset, data quality breakdown, and paginated lead table.
    """
    try:
        camp_uuid = uuid.UUID(campaign_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid campaign UUID")

    campaign = db.query(Campaign).filter(Campaign.id == camp_uuid).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Fetch associated businesses
    source_records = db.query(SourceRecord).filter(SourceRecord.raw_data.isnot(None)).all()
    b_ids = set()

    for sr in source_records:
        r_data = sr.raw_data
        if isinstance(r_data, str):
            try:
                import json
                r_data = json.loads(r_data)
            except Exception:
                r_data = {}
        if isinstance(r_data, dict) and r_data.get("generated_for_campaign") == str(campaign_id):
            if sr.business_id:
                b_ids.add(sr.business_id)

    if not b_ids:
        all_businesses = []
    else:
        query = db.query(Business).options(
            joinedload(Business.locations),
            joinedload(Business.contacts),
            joinedload(Business.socials),
            joinedload(Business.scores),
            joinedload(Business.source_records)
        ).filter(Business.id.in_(b_ids))
        all_businesses = query.all()

    # Calculate Data Quality Metrics
    total_found = len(all_businesses)
    unique_count = len(all_businesses)
    duplicate_count = campaign.duplicate_count or 0

    phone_count = 0
    email_count = 0
    website_count = 0
    social_count = 0
    rating_count = 0

    formatted_leads = []

    for b in all_businesses:
        phone_c = next((c for c in b.contacts if c.type in ['phone', 'mobile', 'whatsapp']), None)
        email_c = next((c for c in b.contacts if c.type == 'email'), None)
        
        phone_val = phone_c.value if phone_c else None
        email_val = email_c.value if email_c else None
        
        if phone_val: phone_count += 1
        if email_val: email_count += 1
        if b.website: website_count += 1
        if b.socials: social_count += 1
        if b.rating: rating_count += 1

        # Text search filter
        if search and search.strip():
            s_term = search.lower().strip()
            matches = (
                s_term in (b.name or "").lower() or
                s_term in (b.category or "").lower() or
                s_term in (phone_val or "").lower() or
                s_term in (email_val or "").lower()
            )
            if not matches:
                continue

        if contactable_only and not phone_val and not email_val:
            continue

        loc = b.locations[0] if b.locations else None
        social_dict = {s.platform.lower(): s.profile_url for s in (b.socials or [])}
        score_obj = b.scores[0] if b.scores else None
        src_obj = b.source_records[0] if b.source_records else None

        place_id_val = ""
        google_maps_url_val = ""
        if src_obj:
            if isinstance(src_obj.raw_data, dict):
                place_id_val = src_obj.raw_data.get("id") or src_obj.raw_data.get("place_id") or ""
            google_maps_url_val = src_obj.source_url or ""
            if not google_maps_url_val and place_id_val:
                google_maps_url_val = f"https://www.google.com/maps/place/?q=place_id:{place_id_val}"

        formatted_leads.append({
            "id": str(b.id),
            "name": b.name,
            "category": b.category or campaign.category or "Commercial",
            "address": loc.address if loc else "",
            "city": loc.city if loc else (campaign.locations[0] if campaign.locations else ""),
            "state": loc.state if loc else "Maharashtra",
            "country": loc.country if loc else "India",
            "postal_code": loc.postal_code if loc else "",
            "phone": phone_val or "",
            "email": email_val or "",
            "website": b.website or "",
            "rating": float(b.rating) if b.rating else None,
            "review_count": b.review_count or 0,
            "place_id": place_id_val,
            "google_maps_url": google_maps_url_val,
            "instagram": social_dict.get("instagram", ""),
            "facebook": social_dict.get("facebook", ""),
            "linkedin": social_dict.get("linkedin", ""),
            "youtube": social_dict.get("youtube", ""),
            "x": social_dict.get("x", "") or social_dict.get("twitter", ""),
            "score": score_obj.total_score if score_obj else 50,
            "tier": score_obj.tier if score_obj else "WARM",
            "source": src_obj.source_name if src_obj else (campaign.provider or "Google Places API"),
            "discovered_at": b.created_at.isoformat() if b.created_at else None
        })

    # Pagination slice
    filtered_total = len(formatted_leads)
    start_idx = (page - 1) * limit
    end_idx = min(start_idx + limit, filtered_total)
    paged_leads = formatted_leads[start_idx:end_idx]

    return {
        "status": "success",
        "campaign_id": str(campaign.id),
        "campaign_name": campaign.name,
        "requested_quantity": campaign.target_leads or 100,
        "metrics": {
            "requested": campaign.target_leads or 100,
            "discovered": total_found,
            "unique": unique_count,
            "duplicates": duplicate_count,
            "phone_available": phone_count,
            "phone_pct": round((phone_count / total_found * 100), 1) if total_found else 0,
            "email_available": email_count,
            "email_pct": round((email_count / total_found * 100), 1) if total_found else 0,
            "website_available": website_count,
            "website_pct": round((website_count / total_found * 100), 1) if total_found else 0,
            "social_available": social_count,
            "social_pct": round((social_count / total_found * 100), 1) if total_found else 0,
            "rating_available": rating_count
        },
        "pagination": {
            "total": filtered_total,
            "page": page,
            "limit": limit,
            "pages": (filtered_total + limit - 1) // limit if limit else 1
        },
        "leads": paged_leads
    }
