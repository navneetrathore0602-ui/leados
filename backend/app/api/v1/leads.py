import math
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.core.database import get_db
from app.models.domain import Business, BusinessLocation, BusinessContact
from app.schemas.lead import PaginatedLeadsResponse, LeadListItemSchema, LeadDetailSchema, LocationSchema, ContactSchema, SourceRecordSchema

router = APIRouter()

@router.get("", response_model=PaginatedLeadsResponse)
def get_leads(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search term for name, category, or city"),
    category: Optional[str] = Query(None, description="Filter by category"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    status: Optional[str] = Query(None, description="Filter by status"),
    minimum_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum lead score"),
    db: Session = Depends(get_db)
):
    query = db.query(Business)

    # Join location if filtering by city or state or searching city
    if city or state or (search and search.strip()):
        query = query.outerjoin(BusinessLocation, Business.id == BusinessLocation.business_id)

    if category:
        query = query.filter(Business.category.ilike(f"%{category}%"))

    if status:
        query = query.filter(Business.status == status)

    if minimum_score is not None:
        query = query.filter(Business.lead_score >= minimum_score)

    if city:
        query = query.filter(BusinessLocation.city.ilike(f"%{city}%"))

    if state:
        query = query.filter(BusinessLocation.state.ilike(f"%{state}%"))

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Business.name.ilike(term),
                Business.category.ilike(term),
                Business.subcategory.ilike(term),
                BusinessLocation.city.ilike(term)
            )
        )

    # Distinct businesses count and items
    query = query.distinct()
    total = query.count()

    offset = (page - 1) * page_size
    businesses = query.order_by(Business.lead_score.desc(), Business.created_at.desc()).offset(offset).limit(page_size).all()

    items = []
    for b in businesses:
        primary_location = b.locations[0] if b.locations else None
        phone_contact = next((c for c in b.contacts if c.type == "phone"), None)
        email_contact = next((c for c in b.contacts if c.type == "email"), None)

        items.append(
            LeadListItemSchema(
                id=b.id,
                name=b.name,
                category=b.category,
                subcategory=b.subcategory,
                website=b.website,
                rating=float(b.rating) if b.rating is not None else None,
                review_count=b.review_count,
                lead_score=b.lead_score or 0,
                verification_score=b.verification_score or 0,
                status=b.status or "new",
                city=primary_location.city if primary_location else None,
                state=primary_location.state if primary_location else None,
                phone=phone_contact.value if phone_contact else None,
                email=email_contact.value if email_contact else None,
                created_at=b.created_at
            )
        )

    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return PaginatedLeadsResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

@router.get("/{lead_id}", response_model=LeadDetailSchema)
def get_lead_by_id(lead_id: UUID, db: Session = Depends(get_db)):
    business = db.query(Business).filter(Business.id == lead_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Lead not found")

    locations = [
        LocationSchema(
            id=loc.id,
            address=loc.address,
            locality=loc.locality,
            city=loc.city,
            state=loc.state,
            country=loc.country,
            postal_code=loc.postal_code,
            latitude=loc.latitude,
            longitude=loc.longitude
        ) for loc in business.locations
    ]

    contacts = [
        ContactSchema(
            id=con.id,
            type=con.type,
            value=con.value,
            normalized_value=con.normalized_value,
            is_verified=con.is_verified,
            confidence=float(con.confidence) if con.confidence is not None else None,
            source=con.source,
            last_verified_at=con.last_verified_at
        ) for con in business.contacts
    ]

    source_records = [
        SourceRecordSchema(
            id=src.id,
            source_name=src.source_name,
            source_url=src.source_url,
            discovered_at=src.discovered_at,
            confidence=float(src.confidence) if src.confidence is not None else None
        ) for src in business.source_records
    ]

    return LeadDetailSchema(
        id=business.id,
        name=business.name,
        normalized_name=business.normalized_name,
        category=business.category,
        subcategory=business.subcategory,
        description=business.description,
        website=business.website,
        rating=float(business.rating) if business.rating is not None else None,
        review_count=business.review_count,
        employee_count_estimate=business.employee_count_estimate,
        lead_score=business.lead_score or 0,
        verification_score=business.verification_score or 0,
        status=business.status or "new",
        first_seen_at=business.first_seen_at,
        last_verified_at=business.last_verified_at,
        created_at=business.created_at,
        updated_at=business.updated_at,
        locations=locations,
        contacts=contacts,
        source_records=source_records
    )
