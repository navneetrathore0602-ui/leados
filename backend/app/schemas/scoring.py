from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict

class LeadScoreOut(BaseModel):
    id: Any
    business_id: Any
    campaign_id: Optional[Any] = None
    total_score: int
    tier: str
    lifecycle_status: str
    business_fit_score: int
    location_fit_score: int
    contactability_score: int
    digital_presence_score: int
    data_quality_score: int
    scoring_version: str
    scoring_ruleset: str
    positive_signals: Optional[List[str]] = []
    negative_signals: Optional[List[str]] = []
    reasons: Optional[List[str]] = []
    is_qualified: bool
    disqualified: bool
    disqualification_reason: Optional[str] = None
    disqualified_rule: Optional[str] = None
    scored_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class CampaignScoreMetricsOut(BaseModel):
    campaign_id: str
    total_scored: int
    qualified_count: int
    disqualified_count: int
    avg_score: float
    avg_data_quality: float
    contactable_percentage: float
    email_availability_percentage: float
    phone_availability_percentage: float
    website_availability_percentage: float
    tier_counts: Dict[str, int]
    lifecycle_counts: Dict[str, int]

class QualifiedLeadItemOut(BaseModel):
    id: Any
    name: str
    category: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    total_score: int
    tier: str
    lifecycle_status: str
    is_qualified: bool
    positive_signals: Optional[List[str]] = []
    reasons: Optional[List[str]] = []

class QualifiedLeadsResponse(BaseModel):
    items: List[QualifiedLeadItemOut]
    total: int
    page: int
    page_size: int
    total_pages: int
