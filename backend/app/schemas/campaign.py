from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

class DiscoveryJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    provider: str
    status: str
    target_count: int
    discovered_count: int
    unique_count: int
    duplicate_count: int
    failed_count: int
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

class CampaignCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Campaign name required")
    description: Optional[str] = None
    category: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    target_leads: int = Field(100, gt=0, description="Target leads must be positive")
    min_rating: float = Field(0.0, ge=0.0, le=5.0, description="Rating between 0 and 5")
    min_reviews: int = Field(0, ge=0, description="Min reviews must be >= 0")
    require_phone: bool = False
    require_website: bool = False
    require_email: bool = False
    provider: str = Field("mock", description="Discovery provider (mock or openstreetmap)")

    @field_validator("keywords", mode="after")
    def check_keywords_or_category(cls, v: List[str], values) -> List[str]:
        cleaned = [k.strip() for k in v if k and k.strip()]
        return cleaned

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    target_leads: Optional[int] = Field(None, gt=0)
    min_rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    min_reviews: Optional[int] = Field(None, ge=0)
    require_phone: Optional[bool] = None
    require_website: Optional[bool] = None
    require_email: Optional[bool] = None
    provider: Optional[str] = None

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    keywords: Optional[List[str]] = None
    locations: Optional[List[str]] = None
    target_leads: int
    min_rating: Optional[float] = 0.0
    min_reviews: Optional[int] = 0
    require_phone: bool = False
    require_website: bool = False
    require_email: bool = False
    provider: str = "mock"
    status: str = "draft"
    discovered_count: int = 0
    unique_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0
    duration_seconds: Optional[float] = None
    data_quality: Optional[Dict[str, float]] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    jobs: List[DiscoveryJobResponse] = []
