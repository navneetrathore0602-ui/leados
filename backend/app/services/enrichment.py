import uuid
import time
import math
import statistics
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.config import settings
from app.models.domain import Campaign, Business, BusinessContact, BusinessLocation, BusinessSocial, BusinessCandidateField, SourceRecord, EnrichmentJob
from app.enrichment.registry import get_enrichment_provider
from app.services.normalization import normalize_phone, normalize_website

# Domain rate limiting lock and timestamp tracker
_domain_last_request: Dict[str, float] = {}
_domain_lock = threading.Lock()


def _enforce_domain_rate_limit(website_url: Optional[str]) -> None:
    """
    Enforces ENRICHMENT_DOMAIN_DELAY_SECONDS gap between requests to the same domain.
    """
    if not website_url or not isinstance(website_url, str):
        return
    try:
        parsed = urllib.parse.urlparse(website_url if website_url.startswith("http") else f"https://{website_url}")
        domain = parsed.netloc.lower()
        if not domain:
            return

        delay = float(getattr(settings, "ENRICHMENT_DOMAIN_DELAY_SECONDS", 1.0))
        with _domain_lock:
            last_time = _domain_last_request.get(domain, 0.0)
            now = time.time()
            wait_time = delay - (now - last_time)
            if wait_time > 0:
                time.sleep(wait_time)
            _domain_last_request[domain] = time.time()
    except Exception:
        pass


def calculate_latencies(durations: List[float]) -> Dict[str, float]:
    """
    Calculates average, median, and P95 latency percentiles from a list of duration values.
    """
    if not durations:
        return {"avg": 0.0, "median": 0.0, "p95": 0.0}
    sorted_d = sorted(durations)
    avg_val = round(sum(sorted_d) / len(sorted_d), 2)
    median_val = round(statistics.median(sorted_d), 2)
    idx_95 = max(0, min(len(sorted_d) - 1, int(math.ceil(0.95 * len(sorted_d)) - 1)))
    p95_val = round(sorted_d[idx_95], 2)
    return {"avg": avg_val, "median": median_val, "p95": p95_val}


def execute_business_enrichment(business_id: Any, job_id: Optional[Any] = None, provider_name: str = "website", campaign_id: Optional[Any] = None) -> Dict[str, Any]:
    """
    Executes single business profile enrichment, applies merge rules & provenance tracking,
    records page-level telemetry & reachability state, and updates database records & job status.
    """
    if isinstance(business_id, str):
        try:
            business_id = uuid.UUID(business_id)
        except Exception:
            pass

    if campaign_id and isinstance(campaign_id, str):
        try:
            campaign_id = uuid.UUID(campaign_id)
        except Exception:
            pass

    db: Session = SessionLocal()
    start_time = time.time()
    now = datetime.now(timezone.utc)

    job = None
    if job_id:
        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except Exception:
                pass
        job = db.query(EnrichmentJob).filter(EnrichmentJob.id == job_id).first()

    try:
        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            if job:
                job.status = "failed"
                job.error_code = "BUSINESS_NOT_FOUND"
                job.error_message = f"Business {business_id} not found"
                db.commit()
            return {"status": "failed", "error": "BUSINESS_NOT_FOUND"}

        # Enforce safety delay between requests to same domain
        _enforce_domain_rate_limit(business.website)

        # Create job if not provided
        if not job:
            job = EnrichmentJob(
                id=uuid.uuid4(),
                business_id=business.id,
                campaign_id=campaign_id,
                provider=provider_name,
                status="running",
                started_at=now,
                created_at=now
            )
            db.add(job)
        else:
            if campaign_id and not job.campaign_id:
                job.campaign_id = campaign_id
            job.status = "running"
            job.started_at = now

        db.commit()

        provider = get_enrichment_provider(provider_name)
        
        # Execute enrichment
        result = provider.enrich(business)

        fields_attempted = ["website", "phone", "email", "whatsapp", "social_profiles", "description", "services", "opening_hours"]
        fields_found = []
        fields_verified = []

        # 1. Website Update
        web_res = result.get("website")
        if web_res and web_res.get("value"):
            fields_found.append("website")
            if not business.website or float(web_res.get("confidence", 0.7)) >= 0.85:
                business.website = web_res["value"]
                fields_verified.append("website")

        # 2. Description Update
        desc_res = result.get("description")
        if desc_res and desc_res.get("value"):
            fields_found.append("description")
            if not business.description or "Discovered via Campaign" in business.description:
                business.description = desc_res["value"]
                fields_verified.append("description")

        # 3. Phone Contacts Update
        phone_res = result.get("phone")
        if phone_res and phone_res.get("value"):
            fields_found.append("phone")
            norm_p = phone_res.get("normalized_value") or normalize_phone(phone_res["value"])
            
            existing_phone = next((c for c in business.contacts if c.type in ["phone", "mobile"] and c.normalized_value == norm_p), None)
            if not existing_phone:
                new_contact = BusinessContact(
                    id=uuid.uuid4(),
                    business_id=business.id,
                    type="phone",
                    value=phone_res["value"],
                    normalized_value=norm_p,
                    is_verified=True if float(phone_res.get("confidence", 0.7)) >= 0.85 else False,
                    confidence=phone_res.get("confidence", 0.90),
                    source=phone_res.get("source", "website_enrichment"),
                    first_seen_at=now,
                    last_verified_at=now
                )
                db.add(new_contact)
                fields_verified.append("phone")

        # 4. Email Contacts Update
        email_res = result.get("email")
        if email_res and email_res.get("value"):
            fields_found.append("email")
            norm_e = email_res.get("normalized_value") or email_res["value"].lower().strip()
            
            existing_email = next((c for c in business.contacts if c.type == "email" and c.normalized_value == norm_e), None)
            if not existing_email:
                new_email = BusinessContact(
                    id=uuid.uuid4(),
                    business_id=business.id,
                    type="email",
                    value=email_res["value"],
                    normalized_value=norm_e,
                    is_verified=False,
                    confidence=email_res.get("confidence", 0.85),
                    source=email_res.get("source", "website_enrichment"),
                    first_seen_at=now,
                    last_verified_at=now
                )
                db.add(new_email)
                fields_verified.append("email")

        # 5. WhatsApp Contact Update
        wa_res = result.get("whatsapp")
        if wa_res and wa_res.get("value"):
            fields_found.append("whatsapp")
            existing_wa = next((c for c in business.contacts if c.type == "whatsapp"), None)
            if not existing_wa:
                db.add(BusinessContact(
                    id=uuid.uuid4(),
                    business_id=business.id,
                    type="whatsapp",
                    value=wa_res["value"],
                    normalized_value=wa_res["value"],
                    is_verified=True,
                    confidence=wa_res.get("confidence", 0.90),
                    source=wa_res.get("source", "website_whatsapp_link"),
                    first_seen_at=now,
                    last_verified_at=now
                ))

        # 6. Social Profiles Update
        socials_res = result.get("social_profiles", [])
        if socials_res:
            fields_found.append("social_profiles")
            for soc in socials_res:
                existing_soc = db.query(BusinessSocial).filter(
                    BusinessSocial.business_id == business.id,
                    BusinessSocial.platform == soc["platform"],
                    BusinessSocial.profile_url == soc["profile_url"]
                ).first()
                if not existing_soc:
                    db.add(BusinessSocial(
                        id=uuid.uuid4(),
                        business_id=business.id,
                        platform=soc["platform"],
                        profile_url=soc["profile_url"],
                        username=soc.get("username"),
                        source=soc.get("source", "website_social_link"),
                        confidence=soc.get("confidence", 0.90),
                        discovered_at=now
                    ))
            fields_verified.append("social_profiles")

        # 7. Candidate / Conflicting Fields
        candidates_res = result.get("candidate_fields", [])
        if candidates_res:
            for cand in candidates_res:
                existing_cand = db.query(BusinessCandidateField).filter(
                    BusinessCandidateField.business_id == business.id,
                    BusinessCandidateField.field_name == cand["field_name"],
                    BusinessCandidateField.value == cand["value"]
                ).first()
                if not existing_cand:
                    db.add(BusinessCandidateField(
                        id=uuid.uuid4(),
                        business_id=business.id,
                        field_name=cand["field_name"],
                        value=cand["value"],
                        normalized_value=cand.get("normalized_value"),
                        source=cand.get("source"),
                        source_url=cand.get("source_url"),
                        confidence=cand.get("confidence", 0.70),
                        status=cand.get("status", "candidate"),
                        discovered_at=now
                    ))

        duration_sec = round(time.time() - start_time, 2)
        end_time = datetime.now(timezone.utc)

        # Telemetry & Reachability Metrics
        page_durations = result.get("page_durations_ms", [])
        latencies = calculate_latencies(page_durations)

        job.reachability_state = result.get("reachability_state", "UNREACHABLE" if not fields_found else "SUCCESS")
        job.pages_attempted = result.get("pages_attempted", 0)
        job.pages_successful = result.get("pages_successful", 0)
        job.pages_failed = result.get("pages_failed", 0)
        job.total_http_requests = result.get("total_http_requests", 0)
        job.telemetry_logs = result.get("telemetry_logs", [])
        job.avg_duration_ms = latencies["avg"]
        job.median_duration_ms = latencies["median"]
        job.p95_duration_ms = latencies["p95"]

        job.phone_found_count = 1 if phone_res else 0
        job.email_found_count = 1 if email_res else 0
        job.social_found_count = len(socials_res)

        job.status = "completed" if fields_found else ("partial" if job.reachability_state in ("SUCCESS", "PARTIAL") else "failed")
        job.fields_attempted = fields_attempted
        job.fields_found = fields_found
        job.fields_verified = fields_verified
        job.completed_at = end_time
        job.duration = duration_sec

        business.verification_score = min(business.verification_score + len(fields_found) * 10, 100)
        business.last_verified_at = end_time
        business.updated_at = end_time

        db.commit()

        return {
            "status": job.status,
            "business_id": str(business.id),
            "job_id": str(job.id),
            "reachability_state": job.reachability_state,
            "fields_found": fields_found,
            "fields_verified": fields_verified,
            "duration": duration_sec,
            "avg_duration_ms": job.avg_duration_ms,
            "median_duration_ms": job.median_duration_ms,
            "p95_duration_ms": job.p95_duration_ms
        }

    except Exception as e:
        db.rollback()
        duration_sec = round(time.time() - start_time, 2)
        if job:
            try:
                job.status = "failed"
                job.error_code = "ENRICHMENT_ERROR"
                job.error_message = str(e)
                job.duration = duration_sec
                db.commit()
            except Exception:
                pass
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


def execute_campaign_batch_enrichment(campaign_id: Any, provider_name: str = "website") -> Dict[str, Any]:
    """
    Triggers batch enrichment concurrently across businesses discovered by a campaign
    with bounded worker pool and domain safety rate limiting.
    """
    if isinstance(campaign_id, str):
        try:
            campaign_id = uuid.UUID(campaign_id)
        except Exception:
            pass

    db: Session = SessionLocal()
    start_batch_time = time.time()

    try:
        source_records = db.query(SourceRecord).filter(SourceRecord.raw_data.isnot(None)).all()
        business_ids = set()

        for sr in source_records:
            if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(campaign_id):
                if sr.business_id:
                    business_ids.add(sr.business_id)

        if not business_ids:
            businesses = db.query(Business).limit(50).all()
            business_ids = {b.id for b in businesses}

        max_concurrency = int(getattr(settings, "ENRICHMENT_MAX_CONCURRENCY", 5))

        results = []
        with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            future_to_bid = {
                executor.submit(execute_business_enrichment, b_id, None, provider_name): b_id
                for b_id in business_ids
            }
            for future in as_completed(future_to_bid):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as ex:
                    results.append({"status": "failed", "error": str(ex)})

        enriched_count = sum(1 for r in results if r.get("status") in ["completed", "partial"])
        failed_count = sum(1 for r in results if r.get("status") == "failed")
        unreachable_count = sum(1 for r in results if r.get("reachability_state") == "UNREACHABLE")

        all_avg_ms = [r.get("avg_duration_ms", 0.0) for r in results if r.get("avg_duration_ms")]
        batch_latencies = calculate_latencies(all_avg_ms)
        total_duration = round(time.time() - start_batch_time, 2)

        return {
            "status": "completed",
            "campaign_id": str(campaign_id),
            "total_businesses": len(business_ids),
            "enriched_count": enriched_count,
            "failed_count": failed_count,
            "unreachable_count": unreachable_count,
            "total_duration": total_duration,
            "avg_latency_ms": batch_latencies["avg"],
            "median_latency_ms": batch_latencies["median"],
            "p95_latency_ms": batch_latencies["p95"]
        }
    finally:
        db.close()


def run_campaign_enrichment(business_ids: List[Any], campaign_id: Optional[Any] = None, provider: str = "website", db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Runs enrichment for a list of business IDs or campaign ID.
    """
    if business_ids and len(business_ids) > 0:
        b_id = business_ids[0]
        return execute_business_enrichment(b_id, campaign_id, provider_name=provider)
    elif campaign_id:
        return execute_campaign_batch_enrichment(campaign_id, provider_name=provider)
    return {"status": "failed", "error": "No business_ids or campaign_id provided"}


