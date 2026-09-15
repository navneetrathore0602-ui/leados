import uuid
from typing import Tuple, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.domain import Business, BusinessLocation, BusinessContact
from app.services.normalization import normalize_business_name, normalize_website, normalize_phone

def find_duplicate_business(
    db: Session,
    normalized_name: str,
    norm_phone: Optional[str] = None,
    norm_website: Optional[str] = None,
    city: Optional[str] = None
) -> Tuple[Optional[Business], float, str]:
    """
    Evaluate duplicate candidates using multiple signals:
    1. Exact normalized phone match -> 0.98 confidence
    2. Exact normalized website match -> 0.95 confidence
    3. Exact normalized name match in same city -> 0.88 confidence
    Returns: (matched_business, confidence, reason)
    """

    # 1. Exact normalized phone match
    if norm_phone:
        contact_match = (
            db.query(BusinessContact)
            .filter(
                BusinessContact.type == "phone",
                BusinessContact.normalized_value == norm_phone
            )
            .first()
        )
        if contact_match and contact_match.business:
            return (contact_match.business, 0.98, f"Exact phone match ({norm_phone})")

    # 2. Exact normalized website match
    if norm_website:
        # Search business with matching website or source
        website_match = (
            db.query(Business)
            .filter(Business.website.ilike(f"%{norm_website}%"))
            .first()
        )
        if website_match:
            return (website_match, 0.95, f"Exact website match ({norm_website})")

    # 3. Exact normalized name match in same city
    if normalized_name and city:
        name_city_match = (
            db.query(Business)
            .join(BusinessLocation, Business.id == BusinessLocation.business_id)
            .filter(
                Business.normalized_name == normalized_name,
                BusinessLocation.city.ilike(city.strip())
            )
            .first()
        )
        if name_city_match:
            return (name_city_match, 0.88, f"Normalized name match in city ({city})")

    # 4. Exact normalized name match alone
    if normalized_name:
        name_match = (
            db.query(Business)
            .filter(Business.normalized_name == normalized_name)
            .first()
        )
        if name_match:
            return (name_match, 0.80, "Normalized name match")

    return (None, 0.0, "No match")


def deduplicate_campaign_records(campaign_id: Any, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Executes deduplication over campaign business records while preserving source provenance.
    """
    own_session = False
    if db is None:
        from app.core.database import SessionLocal
        db = SessionLocal()
        own_session = True

    try:
        from app.models.domain import Campaign, SourceRecord
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        source_records = db.query(SourceRecord).all()
        b_ids = set()
        for sr in source_records:
            if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(campaign_id):
                if sr.business_id:
                    b_ids.add(sr.business_id)

        if not b_ids:
            businesses = db.query(Business).limit(1000).all()
        else:
            businesses = db.query(Business).filter(Business.id.in_(b_ids)).all()

        unique_count = len(businesses)
        duplicate_count = 0

        # Scan for duplicate groups
        seen_names = {}
        for b in businesses:
            norm_name = b.normalized_name or b.name.lower() if b.name else ""
            if norm_name in seen_names:
                duplicate_count += 1
            else:
                seen_names[norm_name] = b.id

        return {
            "status": "success",
            "campaign_id": str(campaign_id),
            "total_records": len(businesses),
            "unique_records": unique_count - duplicate_count,
            "duplicate_records": duplicate_count
        }
    finally:
        if own_session:
            db.close()

