import io
import csv
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload

from app.core.database import SessionLocal
from app.models.domain import Business, Campaign, LeadScore, BusinessContact, BusinessLocation, BusinessSocial, SourceRecord, ExportHistory


def generate_campaign_leads_csv(campaign_id: Any, filters: Optional[Dict[str, Any]] = None, qualified_only: bool = False) -> str:
    """
    Generates a structured CSV export string for campaign leads.
    Supports filters (qualified_only, tier, contactable_only, min_score) and eager loads relationships to eliminate N+1 queries.
    """
    filters = filters or {}
    if qualified_only:
        filters["qualified_only"] = True
        
    qual_filter = filters.get("qualified_only", False)
    tier_filter = filters.get("tier", None)
    contactable_only = filters.get("contactable_only", False)
    min_score = filters.get("min_score", None)

    db: Session = SessionLocal()
    try:
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        source_records = db.query(SourceRecord).filter(SourceRecord.raw_data.isnot(None)).all()
        b_ids = set()

        for sr in source_records:
            if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(campaign_id):
                if sr.business_id:
                    b_ids.add(sr.business_id)

        if not b_ids:
            businesses = db.query(Business).options(
                joinedload(Business.locations),
                joinedload(Business.contacts),
                joinedload(Business.socials),
                joinedload(Business.scores)
            ).limit(5000).all()
        else:
            businesses = db.query(Business).options(
                joinedload(Business.locations),
                joinedload(Business.contacts),
                joinedload(Business.socials),
                joinedload(Business.scores)
            ).filter(Business.id.in_(b_ids)).all()

        output = io.StringIO()
        writer = csv.writer(output)

        # CSV Header
        writer.writerow([
            "Business ID",
            "Business Name",
            "Category",
            "Subcategory",
            "Address",
            "City",
            "State",
            "Country",
            "Primary Phone",
            "Primary Email",
            "Website",
            "Social Profiles",
            "Lead Score",
            "Tier",
            "Lifecycle Status",
            "Verification Score (%)",
            "Is Qualified",
            "Disqualification Reason",
            "Positive Signals",
            "Score Reasons",
            "Discovered / Enriched At"
        ])

        exported_count = 0

        for b in businesses:
            scores_list = sorted(b.scores, key=lambda x: x.created_at or datetime.min, reverse=True) if b.scores else []
            latest_score = scores_list[0] if scores_list else None

            is_qual_val = latest_score.is_qualified if latest_score else (b.lifecycle_status != "DISQUALIFIED")
            score_val = latest_score.total_score if latest_score else b.lead_score
            tier_val = latest_score.tier if latest_score else ("HOT" if score_val >= 80 else ("WARM" if score_val >= 60 else ("COOL" if score_val >= 40 else "LOW")))

            if qual_filter and not is_qual_val:
                continue
            if tier_filter and tier_val.upper() != tier_filter.upper():
                continue
            if min_score is not None and score_val < min_score:
                continue

            phone_contact = next((c.value for c in b.contacts if c.type in ["phone", "mobile"]), "")
            email_contact = next((c.value for c in b.contacts if c.type == "email"), "")

            if contactable_only and not phone_contact and not email_contact:
                continue

            exported_count += 1
            primary_loc = b.locations[0] if b.locations else None
            addr = primary_loc.address if primary_loc else ""
            city = primary_loc.city if primary_loc else ""
            state = primary_loc.state if primary_loc else ""
            country = primary_loc.country if primary_loc else ""

            socials_str = "; ".join([s.profile_url for s in (b.socials or [])])

            status_val = latest_score.lifecycle_status if latest_score else b.lifecycle_status
            disqual_reason = latest_score.disqualification_reason if latest_score else ""

            pos_signals = "; ".join(latest_score.positive_signals) if latest_score and latest_score.positive_signals else ""
            score_reasons = "; ".join(latest_score.reasons) if latest_score and latest_score.reasons else ""

            created_at_str = b.created_at.isoformat() if b.created_at else ""

            writer.writerow([
                str(b.id),
                b.name,
                b.category or "",
                b.subcategory or "",
                addr,
                city,
                state,
                country,
                phone_contact,
                email_contact,
                b.website or "",
                socials_str,
                score_val,
                tier_val,
                status_val,
                b.verification_score,
                "Yes" if is_qual_val else "No",
                disqual_reason or "",
                pos_signals,
                score_reasons,
                created_at_str
            ])

        # Record Export History
        now = datetime.now(timezone.utc)
        export_rec = ExportHistory(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            format="csv",
            filters=filters,
            record_count=exported_count,
            filename=f"LeadOS_Export_{str(campaign_id)[:8]}_{now.strftime('%Y%m%d')}.csv",
            created_at=now
        )
        db.add(export_rec)
        db.commit()

        return output.getvalue()
    finally:
        db.close()
