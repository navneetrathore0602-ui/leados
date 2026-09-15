import uuid
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.domain import Campaign, DiscoveryJob, Business, BusinessLocation, BusinessContact, SourceRecord
from app.providers.registry import get_provider
from app.services.normalization import normalize_business_name, normalize_website, normalize_phone
from app.services.deduplication import find_duplicate_business

def calculate_lead_score(rating: Optional[float], review_count: Optional[int], has_website: bool, has_phone: bool) -> int:
    score = 40  # base score
    if rating:
        score += int(rating * 8)  # up to 40 pts
    if review_count:
        score += min(int(review_count / 5), 15)  # up to 15 pts
    if has_website:
        score += 15
    if has_phone:
        score += 10
    return min(max(score, 0), 100)

def execute_discovery_job(campaign_id: Any, job_id: Any):
    """
    Asynchronous discovery worker function executing campaign search,
    normalization, deduplication, and persistence via selected provider.
    """
    if isinstance(campaign_id, str):
        try:
            campaign_id = uuid.UUID(campaign_id)
        except Exception:
            pass
    if isinstance(job_id, str):
        try:
            job_id = uuid.UUID(job_id)
        except Exception:
            pass

    db: Session = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()

        if not campaign or not job:
            return

        # Mark job and campaign as running
        now = datetime.now(timezone.utc)
        job.status = "running"
        job.started_at = now
        campaign.status = "running"
        if not campaign.started_at:
            campaign.started_at = now
        db.commit()

        # Instantiate provider via Provider Registry
        provider_name = campaign.provider or job.provider or "mock"
        provider = get_provider(provider_name)
        job.provider = provider_name

        # Enforce controlled test safety limit
        target_total = min(
            job.target_count or campaign.target_leads or 100,
            settings.DISCOVERY_TEST_LIMIT
        )
        job.target_count = target_total

        page = 1

        discovered_count = 0
        unique_count = 0
        duplicate_count = 0
        failed_count = 0

        while discovered_count < target_total:
            db.refresh(job)
            db.refresh(campaign)
            if job.status in ["paused", "cancelled"] or campaign.status in ["paused", "cancelled"]:
                break

            fetch_limit = target_total - discovered_count
            
            try:
                items = provider.search(campaign, page=page, limit=fetch_limit)
                page += 1
            except Exception as pe:
                err_msg = str(pe)
                job.status = "failed"
                job.error_message = err_msg
                campaign.status = "failed"
                db.commit()
                return

            if not items:
                break

            for item in items:
                # Apply filter requirements
                min_r = float(campaign.min_rating) if campaign.min_rating else 0.0
                min_rev = campaign.min_reviews or 0

                rating_val = item.get("rating") or 0.0
                rev_val = item.get("review_count") or 0

                if rating_val < min_r or rev_val < min_rev:
                    failed_count += 1
                    continue

                if campaign.require_phone and not item.get("phone"):
                    failed_count += 1
                    continue

                if campaign.require_website and not item.get("website"):
                    failed_count += 1
                    continue

                if campaign.require_email and not item.get("email"):
                    failed_count += 1
                    continue

                # Normalization
                raw_name = item.get("name", "")
                norm_name = normalize_business_name(raw_name)
                norm_site = normalize_website(item.get("website", ""))
                norm_ph = normalize_phone(item.get("phone", ""))
                city = item.get("city")

                discovered_count += 1

                # Raw data enrichment for campaign tracking
                raw_payload = item.get("raw_data") if (isinstance(item, dict) and "raw_data" in item and item["raw_data"]) else dict(item)
                if isinstance(raw_payload, dict):
                    raw_payload["generated_for_campaign"] = str(campaign.id)

                # Deduplication check
                matched_b, confidence, reason = find_duplicate_business(
                    db=db,
                    normalized_name=norm_name,
                    norm_phone=norm_ph,
                    norm_website=norm_site,
                    city=city
                )

                if matched_b and confidence >= 0.75:
                    duplicate_count += 1
                    # Retain raw SourceRecord linked to matched business (Task 9)
                    source_rec = SourceRecord(
                        id=uuid.uuid4(),
                        business_id=matched_b.id,
                        source_name=item.get("source_name", "Discovery Provider"),
                        source_url=item.get("source_url"),
                        raw_data=raw_payload,
                        discovered_at=now,
                        confidence=confidence
                    )
                    db.add(source_rec)
                else:
                    unique_count += 1
                    b_id = uuid.uuid4()
                    l_score = calculate_lead_score(
                        rating=item.get("rating"),
                        review_count=item.get("review_count"),
                        has_website=bool(item.get("website")),
                        has_phone=bool(item.get("phone"))
                    )

                    v_score = 90 if item.get("phone") and item.get("website") else 75

                    business = Business(
                        id=b_id,
                        name=raw_name,
                        normalized_name=norm_name,
                        category=item.get("category"),
                        subcategory=item.get("subcategory"),
                        description=f"Discovered via Campaign: {campaign.name}",
                        website=item.get("website"),
                        rating=item.get("rating"),
                        review_count=item.get("review_count"),
                        employee_count_estimate=15,
                        lead_score=l_score,
                        verification_score=v_score,
                        status="qualified" if l_score >= 80 else "new",
                        first_seen_at=now,
                        last_verified_at=now,
                        created_at=now,
                        updated_at=now
                    )
                    db.add(business)

                    # Location
                    loc = BusinessLocation(
                        id=uuid.uuid4(),
                        business_id=b_id,
                        address=item.get("address"),
                        locality=item.get("locality", "Central"),
                        city=item.get("city"),
                        state=item.get("state"),
                        country=item.get("country"),
                        postal_code=item.get("postal_code"),
                        latitude=item.get("latitude"),
                        longitude=item.get("longitude"),
                        created_at=now
                    )
                    db.add(loc)

                    # Contacts
                    if item.get("phone"):
                        db.add(BusinessContact(
                            id=uuid.uuid4(),
                            business_id=b_id,
                            type="phone",
                            value=item["phone"],
                            normalized_value=norm_ph,
                            is_verified=True,
                            confidence=95.0,
                            source=item.get("source_name", "Discovery Provider"),
                            first_seen_at=now,
                            last_verified_at=now
                        ))

                    if item.get("email"):
                        db.add(BusinessContact(
                            id=uuid.uuid4(),
                            business_id=b_id,
                            type="email",
                            value=item["email"],
                            normalized_value=item["email"].lower(),
                            is_verified=True,
                            confidence=90.0,
                            source=item.get("source_name", "Discovery Provider"),
                            first_seen_at=now,
                            last_verified_at=now
                        ))

                    # Source Record (Retains raw provider payload - Task 9)
                    db.add(SourceRecord(
                        id=uuid.uuid4(),
                        business_id=b_id,
                        source_name=item.get("source_name", "Discovery Provider"),
                        source_url=item.get("source_url"),
                        raw_data=raw_payload,
                        discovered_at=now,
                        confidence=95.0
                    ))

            # Batch commit per page
            job.discovered_count = discovered_count
            job.unique_count = unique_count
            job.duplicate_count = duplicate_count
            job.failed_count = failed_count

            campaign.discovered_count = discovered_count
            campaign.unique_count = unique_count
            campaign.duplicate_count = duplicate_count
            campaign.failed_count = failed_count

            db.commit()
            page += 1

        # Complete job if not paused/cancelled
        db.refresh(job)
        db.refresh(campaign)
        if job.status not in ["paused", "cancelled"]:
            end_time = datetime.now(timezone.utc)
            job.status = "completed"
            job.completed_at = end_time
            campaign.status = "completed"
            campaign.completed_at = end_time
            db.commit()

    except Exception as e:
        db.rollback()
        try:
            job = db.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if job:
                job.status = "failed"
                job.error_message = f"UNKNOWN_ERROR: {str(e)}"
            if campaign:
                campaign.status = "failed"
            db.commit()
        except Exception:
            pass
    finally:
        db.close()


def run_campaign_discovery(campaign_id: Any, provider: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Synchronously or asynchronously runs campaign discovery by managing DiscoveryJob.
    """
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "failed", "error": "Campaign not found"}

        now = datetime.now(timezone.utc)
        job_id = uuid.uuid4()
        job = DiscoveryJob(
            id=job_id,
            campaign_id=campaign.id,
            provider=provider or campaign.provider or "mock",
            status="queued",
            target_count=campaign.target_leads or 100,
            created_at=now
        )
        db.add(job)
        db.commit()

        execute_discovery_job(campaign.id, job.id)

        db.refresh(campaign)
        return {
            "status": "success",
            "campaign_id": str(campaign.id),
            "job_id": str(job.id),
            "discovered_count": campaign.discovered_count,
            "unique_count": campaign.unique_count,
            "duplicate_count": campaign.duplicate_count
        }
    finally:
        if own_session:
            db.close()

