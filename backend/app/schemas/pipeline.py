from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class PipelineJobCreate(BaseModel):
    batch_size: Optional[int] = Field(default=100, ge=1, le=1000)


class PipelineJobResponse(BaseModel):
    status: str
    job_id: str
    campaign_id: Optional[str] = None
    job_status: Optional[str] = None
    current_stage: Optional[str] = None
    total_records: Optional[int] = 0
    processed_records: Optional[int] = 0
    successful_records: Optional[int] = 0
    partial_records: Optional[int] = 0
    failed_records: Optional[int] = 0
    progress_percent: Optional[float] = 0.0
    stage_progress: Optional[Dict[str, int]] = {}
    batch_size: Optional[int] = 100
    error_summary: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ExportRequest(BaseModel):
    format: str = Field(default="xlsx", pattern="^(xlsx|csv)$")
    qualified_only: Optional[bool] = False
    tier: Optional[str] = None  # HOT, WARM, COOL, LOW
    contactable_only: Optional[bool] = False
    min_score: Optional[int] = None


class ExportHistoryResponse(BaseModel):
    id: str
    campaign_id: str
    format: str
    filters: Optional[Dict[str, Any]] = {}
    record_count: int
    filename: str
    created_at: Optional[str] = None
