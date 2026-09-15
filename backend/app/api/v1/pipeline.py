from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import uuid

from app.core.database import SessionLocal
from app.schemas.pipeline import PipelineJobCreate, PipelineJobResponse
from app.services.pipeline import (
    start_pipeline_job,
    get_pipeline_job_status,
    cancel_pipeline_job,
    resume_pipeline_job
)

router = APIRouter()


@router.post("/campaigns/{campaign_id}/run-pipeline", response_model=Dict[str, Any])
@router.post("/campaigns/{campaign_id}/run", response_model=Dict[str, Any])
def run_campaign_pipeline(campaign_id: str, payload: Optional[PipelineJobCreate] = None):
    """
    Enqueues and starts a multi-stage Lead Pipeline Job for a campaign.
    Runs asynchronously in batches. Returns job_id and status='QUEUED'.
    """
    batch_size = payload.batch_size if payload else 100
    res = start_pipeline_job(campaign_id, batch_size=batch_size)
    if res.get("status") == "failed":
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.get("/jobs/{job_id}", response_model=Dict[str, Any])
def get_job_status(job_id: str):
    """
    Retrieves live pipeline job status, stage percentage indicators, and metrics.
    """
    res = get_pipeline_job_status(job_id)
    if res.get("status") == "failed":
        raise HTTPException(status_code=44, detail=res.get("error"))
    return res


@router.post("/jobs/{job_id}/cancel", response_model=Dict[str, Any])
def cancel_job(job_id: str):
    """
    Gracefully cancels a running pipeline job.
    """
    res = cancel_pipeline_job(job_id)
    if res.get("status") == "failed":
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res


@router.post("/jobs/{job_id}/resume", response_model=Dict[str, Any])
def resume_job(job_id: str):
    """
    Resumes a paused or cancelled pipeline job safely using idempotency.
    """
    res = resume_pipeline_job(job_id)
    if res.get("status") == "failed":
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
