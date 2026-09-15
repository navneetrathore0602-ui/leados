from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.domain import Business, SourceRecord, BusinessLocation, BusinessContact, BusinessSocial

def calculate_campaign_data_quality(db: Session, campaign_id: Any) -> Dict[str, float]:
    """
    Calculate Data Quality metrics for a campaign based on its discovered businesses.
    Returns percentage coverages: name, phone, website, email, social, description, services, address, rating, reviews.
    """
    source_records = (
        db.query(SourceRecord)
        .filter(SourceRecord.raw_data.isnot(None))
        .all()
    )

    campaign_b_ids = set()
    for sr in source_records:
        if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(campaign_id):
            if sr.business_id:
                campaign_b_ids.add(sr.business_id)

    if not campaign_b_ids:
        businesses = db.query(Business).limit(100).all()
    else:
        businesses = db.query(Business).filter(Business.id.in_(campaign_b_ids)).all()

    total = len(businesses)
    if total == 0:
        return {
            "name_coverage": 0.0,
            "phone_coverage": 0.0,
            "website_coverage": 0.0,
            "email_coverage": 0.0,
            "social_coverage": 0.0,
            "description_coverage": 0.0,
            "services_coverage": 0.0,
            "address_coverage": 0.0,
            "rating_coverage": 0.0,
            "reviews_coverage": 0.0
        }

    name_count = 0
    phone_count = 0
    website_count = 0
    email_count = 0
    social_count = 0
    description_count = 0
    services_count = 0
    address_count = 0
    rating_count = 0
    reviews_count = 0

    for b in businesses:
        if b.name and b.name.strip():
            name_count += 1
        if b.website and b.website.strip():
            website_count += 1
        if b.description and b.description.strip() and "Discovered via Campaign" not in b.description:
            description_count += 1
        if b.rating is not None and float(b.rating) > 0:
            rating_count += 1
        if b.review_count is not None and b.review_count > 0:
            reviews_count += 1
        
        has_phone = any(c.type in ["phone", "mobile"] and c.value for c in b.contacts)
        if has_phone:
            phone_count += 1

        has_email = any(c.type == "email" and c.value for c in b.contacts)
        if has_email:
            email_count += 1

        if len(b.socials) > 0:
            social_count += 1

        has_loc = any((l.address or l.city) for l in b.locations)
        if has_loc:
            address_count += 1

    return {
        "name_coverage": round((name_count / total) * 100, 1),
        "phone_coverage": round((phone_count / total) * 100, 1),
        "website_coverage": round((website_count / total) * 100, 1),
        "email_coverage": round((email_count / total) * 100, 1),
        "social_coverage": round((social_count / total) * 100, 1),
        "description_coverage": round((description_count / total) * 100, 1),
        "services_coverage": round((services_count / total) * 100, 1),
        "address_coverage": round((address_count / total) * 100, 1),
        "rating_coverage": round((rating_count / total) * 100, 1),
        "reviews_coverage": round((reviews_count / total) * 100, 1)
    }
