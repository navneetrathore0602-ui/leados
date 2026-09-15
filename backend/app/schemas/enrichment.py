from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, ConfigDict

class BusinessSocialOut(BaseModel):
    id: Any
    platform: str
    profile_url: str
    username: Optional[str] = None
    source: Optional[str] = None
    confidence: Optional[float] = None
    discovered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BusinessCandidateFieldOut(BaseModel):
    id: Any
    field_name: str
    value: str
    normalized_value: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None
    status: Optional[str] = None
    discovered_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class EnrichmentJobOut(BaseModel):
    id: Any
    business_id: Optional[Any] = None
    campaign_id: Optional[Any] = None
    provider: str
    status: str
    reachability_state: Optional[str] = None
    pages_attempted: Optional[int] = None
    pages_successful: Optional[int] = None
    pages_failed: Optional[int] = None
    total_http_requests: Optional[int] = None
    telemetry_logs: Optional[List[Dict[str, Any]]] = None
    avg_duration_ms: Optional[float] = None
    median_duration_ms: Optional[float] = None
    p95_duration_ms: Optional[float] = None
    phone_found_count: Optional[int] = None
    email_found_count: Optional[int] = None
    social_found_count: Optional[int] = None
    fields_attempted: Optional[List[str]] = None
    fields_found: Optional[List[str]] = None
    fields_verified: Optional[List[str]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class BusinessEnrichmentDetailOut(BaseModel):
    business_id: Any
    name: str
    website: Optional[str] = None
    description: Optional[str] = None
    socials: List[BusinessSocialOut] = []
    candidates: List[BusinessCandidateFieldOut] = []
    jobs: List[EnrichmentJobOut] = []
    quality_score: Dict[str, float] = {}

class BatchEnrichmentResponse(BaseModel):
    status: str
    campaign_id: str
    total_businesses: int
    enriched_count: int
    failed_count: int
    unreachable_count: Optional[int] = 0
    total_duration: float
    avg_latency_ms: Optional[float] = None
    median_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None

