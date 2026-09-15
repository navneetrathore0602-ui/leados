from typing import List, Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class LocationSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[UUID] = None
    address: Optional[str] = None
    locality: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class ContactSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: Optional[str] = None
    value: Optional[str] = None
    normalized_value: Optional[str] = None
    is_verified: bool = False
    confidence: Optional[float] = None
    source: Optional[str] = None
    last_verified_at: Optional[datetime] = None

class SourceRecordSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    discovered_at: Optional[datetime] = None
    confidence: Optional[float] = None

class LeadListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    lead_score: int = 0
    verification_score: int = 0
    status: str = "new"
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None

class LeadDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    normalized_name: Optional[str] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    employee_count_estimate: Optional[int] = None
    lead_score: int = 0
    verification_score: int = 0
    status: str = "new"
    first_seen_at: Optional[datetime] = None
    last_verified_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    locations: List[LocationSchema] = []
    contacts: List[ContactSchema] = []
    source_records: List[SourceRecordSchema] = []

class PaginatedLeadsResponse(BaseModel):
    items: List[LeadListItemSchema]
    total: int
    page: int
    page_size: int
    total_pages: int
