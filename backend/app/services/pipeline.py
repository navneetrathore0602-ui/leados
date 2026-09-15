import uuid
import threading
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.domain import Campaign, Business, PipelineJob, DiscoveryJob, EnrichmentJob, LeadScore, SourceRecord
from app.services.discovery import run_campaign_discovery
from app.services.normalization import normalize_business_records
from app.services.deduplication import deduplicate_campaign_records
from app.services.enrichment import run_campaign_enrichment
from app.services.scoring import score_campaign_leads, score_business
from app.services.export_excel import generate_campaign_leads_xlsx

logger = logging.getLogger(__name__)

# Global registry for active thread references
_ACTIVE_PIPELINE_THREADS: Dict[str, threading.Thread] = {}


def start_pipeline_job(campaign_id: Any, batch_size: int = 100) -> Dict[str, Any]:
    """
    Launches an asynchronous, batch-processed Lead Pipeline Job for a campaign.
    Returns immediately with job_id and status='QUEUED'.
    """
    db: Session = SessionLocal()
    try:
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "failed", "error": "Campaign not found"}

        # Check for existing running job
        existing = db.query(PipelineJob).filter(
            PipelineJob.campaign_id == campaign_id,
            PipelineJob.status.in_(["QUEUED", "RUNNING"])
        ).first()

        if existing:
            return {
                "status": "success",
                "job_id": str(existing.id),
                "job_status": existing.status,
                "message": "Existing pipeline job is already active"
            }

        job = PipelineJob(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            status="QUEUED",
            current_stage="DISCOVERY",
            total_records=campaign.target_leads or 100,
            processed_records=0,
            successful_records=0,
            partial_records=0,
            failed_records=0,
            progress_percent=0.0,
            batch_size=batch_size,
            stage_progress={
                "DISCOVERY": 0,
                "NORMALIZATION": 0,
                "DEDUPLICATION": 0,
                "ENRICHMENT": 0,
                "SCORING": 0,
                "EXPORT": 0
            },
            created_at=datetime.now(timezone.utc)
        )
        db.add(job)
        db.commit()

        job_id_str = str(job.id)

        # Launch background thread for pipeline execution
        thread = threading.Thread(
            target=_run_pipeline_worker,
            args=(job_id_str, str(campaign_id), batch_size),
            daemon=True
        )
        _ACTIVE_PIPELINE_THREADS[job_id_str] = thread
        thread.start()

        return {
            "status": "success",
            "job_id": job_id_str,
            "job_status": "QUEUED",
            "message": "Lead Pipeline job enqueued successfully"
        }
    finally:
        db.close()


def get_pipeline_job_status(job_id: Any) -> Dict[str, Any]:
    """
    Retrieves live status and stage-by-stage progress for a pipeline job.
    """
    db: Session = SessionLocal()
    try:
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)

        job = db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
        if not job:
            return {"status": "failed", "error": "Job not found"}

        return {
            "status": "success",
            "job_id": str(job.id),
            "campaign_id": str(job.campaign_id),
            "job_status": job.status,
            "current_stage": job.current_stage,
            "total_records": job.total_records,
            "processed_records": job.processed_records,
            "successful_records": job.successful_records,
            "partial_records": job.partial_records,
            "failed_records": job.failed_records,
            "progress_percent": round(job.progress_percent, 1),
            "stage_progress": job.stage_progress or {},
            "batch_size": job.batch_size,
            "error_summary": job.error_summary,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
    finally:
        db.close()


def cancel_pipeline_job(job_id: Any) -> Dict[str, Any]:
    """
    Gracefully cancels a running pipeline job.
    """
    db: Session = SessionLocal()
    try:
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)

        job = db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
        if not job:
            return {"status": "failed", "error": "Job not found"}

        if job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            return {"status": "failed", "error": f"Job is already {job.status}"}

        job.status = "CANCELLED"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        return {"status": "success", "message": f"Job {job_id} cancelled successfully"}
    finally:
        db.close()


def resume_pipeline_job(job_id: Any) -> Dict[str, Any]:
    """
    Resumes a paused or cancelled pipeline job safely using idempotency.
    """
    db: Session = SessionLocal()
    try:
        if isinstance(job_id, str):
            job_id = uuid.UUID(job_id)

        job = db.query(PipelineJob).filter(PipelineJob.id == job_id).first()
        if not job:
            return {"status": "failed", "error": "Job not found"}

        if job.status in ["RUNNING", "COMPLETED"]:
            return {"status": "failed", "error": f"Job cannot be resumed from status {job.status}"}

        job.status = "QUEUED"
        job.updated_at = datetime.now(timezone.utc)
        db.commit()

        job_id_str = str(job.id)
        campaign_id_str = str(job.campaign_id)

        thread = threading.Thread(
            target=_run_pipeline_worker,
            args=(job_id_str, campaign_id_str, job.batch_size or 100),
            daemon=True
        )
        _ACTIVE_PIPELINE_THREADS[job_id_str] = thread
        thread.start()

        return {"status": "success", "message": f"Job {job_id} resumed successfully"}
    finally:
        db.close()


def _run_pipeline_worker(job_id_str: str, campaign_id_str: str, batch_size: int):
    """
    Internal background worker function executing the 6 pipeline stages.
    Handles idempotency, batching, status updates, and failure isolation.
    """
    db: Session = SessionLocal()
    job_uuid = uuid.UUID(job_id_str)
    camp_uuid = uuid.UUID(campaign_id_str)

    try:
        job = db.query(PipelineJob).filter(PipelineJob.id == job_uuid).first()
        if not job or job.status == "CANCELLED":
            return

        job.status = "RUNNING"
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        campaign = db.query(Campaign).filter(Campaign.id == camp_uuid).first()
        stage_prog = job.stage_progress or {
            "DISCOVERY": 0, "NORMALIZATION": 0, "DEDUPLICATION": 0,
            "ENRICHMENT": 0, "SCORING": 0, "EXPORT": 0
        }

        # -------------------------------------------------------------
        # STAGE 1: DISCOVERY
        # -------------------------------------------------------------
        if stage_prog.get("DISCOVERY", 0) < 100:
            if _check_cancelled(db, job_uuid): return

            job.current_stage = "DISCOVERY"
            db.commit()

            # Execute discovery service
            disc_res = run_campaign_discovery(camp_uuid, provider=campaign.provider or "mock", db=db)
            stage_prog["DISCOVERY"] = 100
            job.stage_progress = stage_prog
            job.progress_percent = 16.6
            db.commit()

        # -------------------------------------------------------------
        # STAGE 2: NORMALIZATION
        # -------------------------------------------------------------
        if stage_prog.get("NORMALIZATION", 0) < 100:
            if _check_cancelled(db, job_uuid): return

            job.current_stage = "NORMALIZATION"
            db.commit()

            # Find business records linked to campaign
            source_records = db.query(SourceRecord).all()
            b_ids = set()
            for sr in source_records:
                r_data = sr.raw_data
                if isinstance(r_data, str):
                    try:
                        import json
                        r_data = json.loads(r_data)
                    except Exception:
                        r_data = {}
                if isinstance(r_data, dict) and r_data.get("generated_for_campaign") == campaign_id_str:
                    if sr.business_id:
                        b_ids.add(sr.business_id)

            if not b_ids:
                businesses = db.query(Business).limit(1000).all()
            else:
                businesses = db.query(Business).filter(Business.id.in_(b_ids)).all()

            normalize_business_records(businesses, db=db)
            stage_prog["NORMALIZATION"] = 100
            job.stage_progress = stage_prog
            job.progress_percent = 33.3
            db.commit()

        # -------------------------------------------------------------
        # STAGE 3: DEDUPLICATION
        # -------------------------------------------------------------
        if stage_prog.get("DEDUPLICATION", 0) < 100:
            if _check_cancelled(db, job_uuid): return

            job.current_stage = "DEDUPLICATION"
            db.commit()

            deduplicate_campaign_records(camp_uuid, db=db)
            stage_prog["DEDUPLICATION"] = 100
            job.stage_progress = stage_prog
            job.progress_percent = 50.0
            db.commit()

        # -------------------------------------------------------------
        # STAGE 4: ENRICHMENT (BATCH PROCESSED)
        # -------------------------------------------------------------
        if stage_prog.get("ENRICHMENT", 0) < 100:
            if _check_cancelled(db, job_uuid): return

            job.current_stage = "ENRICHMENT"
            db.commit()

            # For Google Places providers: SKIP blocking external website HTTP scraping/enrichment stage
            if (campaign.provider or "").lower() in ["google", "google_places"]:
                logger.info(f"Skipping website enrichment for Google Places campaign {campaign_id_str}: SKIPPED / NOT REQUIRED FOR GOOGLE")
                stage_prog["ENRICHMENT"] = 100
                job.stage_progress = stage_prog
                job.progress_percent = 83.3
                db.commit()
            else:
                # Get target businesses
                source_records = db.query(SourceRecord).all()
                b_ids = set()
                for sr in source_records:
                    if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == campaign_id_str:
                        if sr.business_id:
                            b_ids.add(sr.business_id)

                if not b_ids:
                    businesses = db.query(Business).limit(1000).all()
                else:
                    businesses = db.query(Business).filter(Business.id.in_(b_ids)).all()

                job.total_records = len(businesses)
                db.commit()

                # Process in configurable batches
                succ_cnt = 0
                part_cnt = 0
                fail_cnt = 0
                processed = 0

                provider_name = "website"
                if campaign.provider == "mock":
                    provider_name = "mock"

                for i in range(0, len(businesses), batch_size):
                    if _check_cancelled(db, job_uuid): return

                    batch = businesses[i:i + batch_size]
                    for b in batch:
                        try:
                            # Idempotency check: skip if already successfully enriched recently
                            existing_enrich = db.query(EnrichmentJob).filter(
                                EnrichmentJob.business_id == b.id,
                                EnrichmentJob.status == "completed"
                            ).first()

                            if not existing_enrich:
                                enrich_res = run_campaign_enrichment([b.id], campaign_id=camp_uuid, provider=provider_name, db=db)
                                reach_state = enrich_res.get("reachability_state", "SUCCESS")
                                if reach_state == "SUCCESS":
                                    succ_cnt += 1
                                elif reach_state == "PARTIAL":
                                    part_cnt += 1
                                else:
                                    fail_cnt += 1
                            else:
                                succ_cnt += 1
                        except Exception as ex:
                            logger.warning(f"Enrichment error for business {b.id}: {ex}")
                            fail_cnt += 1
                        
                        processed += 1

                    # Update job progress after batch
                    job.processed_records = processed
                    job.successful_records = succ_cnt
                    job.partial_records = part_cnt
                    job.failed_records = fail_cnt
                    
                    pct = (processed / len(businesses)) * 100 if len(businesses) > 0 else 100
                    stage_prog["ENRICHMENT"] = min(int(pct), 100)
                    job.stage_progress = stage_prog
                    job.progress_percent = 50.0 + (pct * 0.33)
                    db.commit()

                stage_prog["ENRICHMENT"] = 100
                job.stage_progress = stage_prog
                job.progress_percent = 83.3
                db.commit()

        # -------------------------------------------------------------
        # STAGE 5: SCORING
        # -------------------------------------------------------------
        if stage_prog.get("SCORING", 0) < 100:
            if _check_cancelled(db, job_uuid): return

            job.current_stage = "SCORING"
            db.commit()

            score_campaign_leads(camp_uuid)
            stage_prog["SCORING"] = 100
            job.stage_progress = stage_prog
            job.progress_percent = 95.0
            db.commit()

        # -------------------------------------------------------------
        # STAGE 6: EXPORT (PRE-GENERATE DEFAULT XLSX)
        # -------------------------------------------------------------
        if stage_prog.get("EXPORT", 0) < 100:
            if _check_cancelled(db, job_uuid): return

            job.current_stage = "EXPORT"
            db.commit()

            generate_campaign_leads_xlsx(camp_uuid)
            stage_prog["EXPORT"] = 100
            job.stage_progress = stage_prog
            job.progress_percent = 100.0
            db.commit()

        # Mark Job Complete
        job.status = "COMPLETED"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as e:
        logger.error(f"Pipeline job {job_id_str} failed: {e}", exc_info=True)
        try:
            job = db.query(PipelineJob).filter(PipelineJob.id == job_uuid).first()
            if job:
                job.status = "FAILED"
                job.error_summary = str(e)
                job.completed_at = datetime.now(timezone.utc)
                db.commit()
        except Exception:
            pass
    finally:
        _ACTIVE_PIPELINE_THREADS.pop(job_id_str, None)
        db.close()


def _check_cancelled(db: Session, job_uuid: uuid.UUID) -> bool:
    """Helper to check if job was cancelled by user."""
    job = db.query(PipelineJob).filter(PipelineJob.id == job_uuid).first()
    if job and job.status == "CANCELLED":
        return True
    return False
