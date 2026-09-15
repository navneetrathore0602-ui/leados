from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.models.domain import Business, BusinessLocation, BusinessContact
from app.schemas.stats import LeadStatsResponse

router = APIRouter()

@router.get("", response_model=LeadStatsResponse)
def get_stats(db: Session = Depends(get_db)):
    total_businesses = db.query(func.count(Business.id)).scalar() or 0
    total_leads = total_businesses

    hot_leads = db.query(func.count(Business.id)).filter(Business.lead_score >= 80).scalar() or 0
    warm_leads = db.query(func.count(Business.id)).filter(Business.lead_score >= 50, Business.lead_score < 80).scalar() or 0
    cold_leads = db.query(func.count(Business.id)).filter(Business.lead_score < 50).scalar() or 0

    verified_contacts = db.query(func.count(BusinessContact.id)).filter(BusinessContact.is_verified == True).scalar() or 0

    # Group by category
    category_counts = (
        db.query(Business.category, func.count(Business.id))
        .filter(Business.category.isnot(None))
        .group_by(Business.category)
        .all()
    )
    businesses_by_category = {cat: count for cat, count in category_counts}

    # Group by city
    city_counts = (
        db.query(BusinessLocation.city, func.count(BusinessLocation.business_id.distinct()))
        .filter(BusinessLocation.city.isnot(None))
        .group_by(BusinessLocation.city)
        .all()
    )
    businesses_by_city = {city: count for city, count in city_counts}

    return LeadStatsResponse(
        total_businesses=total_businesses,
        total_leads=total_leads,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        verified_contacts=verified_contacts,
        businesses_by_category=businesses_by_category,
        businesses_by_city=businesses_by_city
    )
