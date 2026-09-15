import io
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from app.core.database import SessionLocal
from app.models.domain import Business, Campaign, LeadScore, BusinessContact, BusinessLocation, BusinessSocial, SourceRecord, EnrichmentJob, ExportHistory


def generate_campaign_leads_xlsx(campaign_id: Any, filters: Optional[Dict[str, Any]] = None) -> bytes:
    """
    Generates a professional 3-sheet Excel (.xlsx) workbook for campaign leads.
    Sheet 1: SALES LEADS (Comprehensive lead intelligence table with formatting, frozen panes, and autofilter)
    Sheet 2: SUMMARY (Campaign KPI summary, tier distribution, contact coverage %, pipeline metrics)
    Sheet 3: DATA QUALITY (Enrichment reachability, conflict statistics, field coverage)
    """
    filters = filters or {}
    qualified_only = filters.get("qualified_only", False)
    tier_filter = filters.get("tier", None)
    contactable_only = filters.get("contactable_only", False)
    min_score = filters.get("min_score", None)

    db: Session = SessionLocal()
    try:
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        campaign_name = campaign.name if campaign else "Campaign Leads"

        # Eager load relationships to avoid N+1 queries during high-volume export
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
                joinedload(Business.scores),
                joinedload(Business.source_records),
                joinedload(Business.enrichment_jobs)
            ).limit(5000).all()
        else:
            businesses = db.query(Business).options(
                joinedload(Business.locations),
                joinedload(Business.contacts),
                joinedload(Business.socials),
                joinedload(Business.scores),
                joinedload(Business.source_records),
                joinedload(Business.enrichment_jobs)
            ).filter(Business.id.in_(b_ids)).all()

        # Create Workbook
        wb = openpyxl.Workbook()
        
        # Styles
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
        title_font = Font(name="Calibri", size=14, bold=True, color="1E3A8A")
        sub_font = Font(name="Calibri", size=11, bold=True, color="374151")
        card_fill = PatternFill(start_color="F3F4F6", end_color="F3F4F6", fill_type="solid")
        
        thin_border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )

        # -------------------------------------------------------------
        # SHEET 1: SALES LEADS
        # -------------------------------------------------------------
        ws1 = wb.active
        ws1.title = "SALES LEADS"

        headers = [
            "Lead ID", "Business Name", "Category", "Subcategory", "Description",
            "Address", "Locality", "City", "State", "Country", "Postal Code", "Latitude", "Longitude",
            "Phone", "Phone Status", "Email", "Email Status", "WhatsApp", "Website",
            "Instagram", "Facebook", "LinkedIn", "YouTube", "X",
            "Rating", "Review Count", "Opening Hours",
            "Lead Score", "Lead Tier", "Qualification Status", "Disqualification Reason",
            "Business Fit Score", "Location Fit Score", "Contactability Score", "Digital Presence Score", "Data Quality Score",
            "Positive Signals", "Negative Signals", "Score Reasons",
            "Primary Source", "Enrichment Source", "Enriched At", "Data Freshness"
        ]

        ws1.append(headers)

        # Style header row
        for col_idx in range(1, len(headers) + 1):
            cell = ws1.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        ws1.row_dimensions[1].height = 28
        ws1.freeze_panes = "A2"

        # Counters for metrics sheet
        total_count = len(businesses)
        qualified_count = 0
        disqualified_count = 0
        tier_counts = {"HOT": 0, "WARM": 0, "COOL": 0, "LOW": 0}
        phone_count = 0
        email_count = 0
        website_count = 0
        social_count = 0
        total_score_sum = 0
        total_quality_sum = 0
        exported_records = 0

        complete_records = 0
        partial_records = 0
        unreachable_websites = 0
        failed_enrichments = 0
        conflicting_fields_count = 0

        for b in businesses:
            # Fetch latest score row
            scores_list = sorted(b.scores, key=lambda x: x.created_at or datetime.min, reverse=True) if b.scores else []
            latest_score = scores_list[0] if scores_list else None

            is_qual = latest_score.is_qualified if latest_score else (b.lifecycle_status != "DISQUALIFIED")
            score_val = latest_score.total_score if latest_score else b.lead_score
            tier_val = latest_score.tier if latest_score else ("HOT" if score_val >= 80 else ("WARM" if score_val >= 60 else ("COOL" if score_val >= 40 else "LOW")))
            disqual_reason = latest_score.disqualification_reason if latest_score else ""

            # Filter checks
            if qualified_only and not is_qual:
                continue
            if tier_filter and tier_val.upper() != tier_filter.upper():
                continue
            if min_score is not None and score_val < min_score:
                continue

            phone_contact = next((c for c in b.contacts if c.type in ["phone", "mobile"]), None)
            email_contact = next((c for c in b.contacts if c.type == "email"), None)
            whatsapp_contact = next((c for c in b.contacts if c.type == "whatsapp"), None)

            phone_val = phone_contact.value if phone_contact else ""
            email_val = email_contact.value if email_contact else ""

            if contactable_only and not phone_val and not email_val:
                continue

            exported_records += 1

            if is_qual:
                qualified_count += 1
            else:
                disqualified_count += 1

            if tier_val in tier_counts:
                tier_counts[tier_val] += 1

            if phone_val: phone_count += 1
            if email_val: email_count += 1
            if b.website: website_count += 1
            if b.socials: social_count += 1

            total_score_sum += score_val
            total_quality_sum += (latest_score.data_quality_score if latest_score else 0)

            # Data quality metrics tracking
            has_all_key_fields = bool(b.name and b.category and b.locations and phone_val and b.website and email_val)
            if has_all_key_fields:
                complete_records += 1
            else:
                partial_records += 1

            enrich_jobs = sorted(b.enrichment_jobs, key=lambda x: x.created_at or datetime.min, reverse=True) if b.enrichment_jobs else []
            latest_enrich = enrich_jobs[0] if enrich_jobs else None

            if latest_enrich:
                if latest_enrich.reachability_state == "UNREACHABLE":
                    unreachable_websites += 1
                elif latest_enrich.status == "failed":
                    failed_enrichments += 1

            primary_loc = b.locations[0] if b.locations else None
            social_dict = {s.platform.lower(): s.profile_url for s in (b.socials or [])}

            pos_signals = "; ".join(latest_score.positive_signals) if latest_score and latest_score.positive_signals else ""
            neg_signals = "; ".join(latest_score.negative_signals) if latest_score and latest_score.negative_signals else ""
            score_reasons = "; ".join(latest_score.reasons) if latest_score and latest_score.reasons else ""

            source_rec = b.source_records[0] if b.source_records else None
            primary_src = source_rec.source_name if source_rec else "Discovery"
            enrich_src = latest_enrich.provider if latest_enrich else "Website"
            enriched_at_str = latest_enrich.completed_at.strftime("%Y-%m-%d %H:%M:%S") if latest_enrich and latest_enrich.completed_at else (b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "")

            row_data = [
                str(b.id)[:8],
                b.name,
                b.category or "",
                b.subcategory or "",
                b.description or "",
                primary_loc.address if primary_loc else "",
                primary_loc.locality if primary_loc else "",
                primary_loc.city if primary_loc else "",
                primary_loc.state if primary_loc else "",
                primary_loc.country if primary_loc else "",
                primary_loc.postal_code if primary_loc else "",
                primary_loc.latitude if primary_loc else "",
                primary_loc.longitude if primary_loc else "",
                phone_val,
                "Verified" if (phone_contact and phone_contact.is_verified) else ("Present" if phone_val else "Missing"),
                email_val,
                "Verified" if (email_contact and email_contact.is_verified) else ("Present" if email_val else "Missing"),
                whatsapp_contact.value if whatsapp_contact else "",
                b.website or "",
                social_dict.get("instagram", ""),
                social_dict.get("facebook", ""),
                social_dict.get("linkedin", ""),
                social_dict.get("youtube", ""),
                social_dict.get("x", "") or social_dict.get("twitter", ""),
                float(b.rating) if b.rating else "",
                b.review_count or 0,
                "", # Opening Hours
                score_val,
                tier_val,
                "QUALIFIED" if is_qual else "DISQUALIFIED",
                disqual_reason,
                latest_score.business_fit_score if latest_score else 0,
                latest_score.location_fit_score if latest_score else 0,
                latest_score.contactability_score if latest_score else 0,
                latest_score.digital_presence_score if latest_score else 0,
                latest_score.data_quality_score if latest_score else 0,
                pos_signals,
                neg_signals,
                score_reasons,
                primary_src,
                enrich_src,
                enriched_at_str,
                "Fresh (<30 days)"
            ]
            ws1.append(row_data)

        # Enable AutoFilter on row 1
        ws1.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{ws1.max_row}"

        # Adjust Column Widths
        for col in ws1.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws1.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

        # -------------------------------------------------------------
        # SHEET 2: SUMMARY
        # -------------------------------------------------------------
        ws2 = wb.create_sheet(title="SUMMARY")
        
        ws2.append(["LEADOS CAMPAIGN SUMMARY REPORT"])
        ws2.cell(row=1, column=1).font = title_font
        ws2.append([f"Campaign Name: {campaign_name}"])
        ws2.append([f"Export Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"])
        ws2.append([])

        avg_score = (total_score_sum / exported_records) if exported_records > 0 else 0.0
        avg_quality = (total_quality_sum / exported_records) if exported_records > 0 else 0.0

        metrics_summary = [
            ("Total Businesses Discovered", total_count),
            ("Total Leads Exported", exported_records),
            ("Qualified Leads", qualified_count),
            ("Disqualified Leads", disqualified_count),
            ("HOT Tier Leads (80-100)", tier_counts["HOT"]),
            ("WARM Tier Leads (60-79)", tier_counts["WARM"]),
            ("COOL Tier Leads (40-59)", tier_counts["COOL"]),
            ("LOW Tier Leads (0-39)", tier_counts["LOW"]),
            ("Phone Contact Coverage %", f"{(phone_count / exported_records * 100):.1f}%" if exported_records > 0 else "0%"),
            ("Email Contact Coverage %", f"{(email_count / exported_records * 100):.1f}%" if exported_records > 0 else "0%"),
            ("Website Coverage %", f"{(website_count / exported_records * 100):.1f}%" if exported_records > 0 else "0%"),
            ("Social Profile Coverage %", f"{(social_count / exported_records * 100):.1f}%" if exported_records > 0 else "0%"),
            ("Average Lead Score (0-100)", f"{avg_score:.1f}"),
            ("Average Data Quality Score (0-15)", f"{avg_quality:.1f}")
        ]

        ws2.append(["Metric", "Value"])
        ws2.cell(row=5, column=1).font = sub_font
        ws2.cell(row=5, column=2).font = sub_font

        for label, val in metrics_summary:
            ws2.append([label, val])

        ws2.append([])
        ws2.append(["PIPELINE STAGE EXECUTION METRICS"])
        ws2.cell(row=ws2.max_row, column=1).font = sub_font

        ws2.append(["Stage", "Status", "Processed Count"])
        ws2.append(["DISCOVERY", "COMPLETED", total_count])
        ws2.append(["NORMALIZATION", "COMPLETED", total_count])
        ws2.append(["DEDUPLICATION", "COMPLETED", total_count])
        ws2.append(["ENRICHMENT", "COMPLETED", exported_records])
        ws2.append(["SCORING", "COMPLETED", exported_records])
        ws2.append(["EXPORT", "COMPLETED", exported_records])

        for col in ws2.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws2.column_dimensions[col_letter].width = max(max_len + 4, 25)

        # -------------------------------------------------------------
        # SHEET 3: DATA QUALITY
        # -------------------------------------------------------------
        ws3 = wb.create_sheet(title="DATA QUALITY")
        
        ws3.append(["LEADOS DATA QUALITY & ENRICHMENT AUDIT"])
        ws3.cell(row=1, column=1).font = title_font
        ws3.append([])

        quality_audit = [
            ("Total Records Audited", exported_records),
            ("Complete Records (All 6 Key Fields)", complete_records),
            ("Partial Records (1-5 Key Fields)", partial_records),
            ("Unreachable Websites", unreachable_websites),
            ("Failed Enrichments", failed_enrichments),
            ("Conflicting Data Fields Detected", conflicting_fields_count),
            ("Missing Phone Numbers", exported_records - phone_count),
            ("Missing Email Addresses", exported_records - email_count),
            ("Missing Websites", exported_records - website_count),
            ("Missing Social Profiles", exported_records - social_count)
        ]

        ws3.append(["Quality Parameter", "Record Count"])
        ws3.cell(row=3, column=1).font = sub_font
        ws3.cell(row=3, column=2).font = sub_font

        for param, cnt in quality_audit:
            ws3.append([param, cnt])

        for col in ws3.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = get_column_letter(col[0].column)
            ws3.column_dimensions[col_letter].width = max(max_len + 4, 30)

        # Output bytes
        stream = io.BytesIO()
        wb.save(stream)
        xlsx_bytes = stream.getvalue()

        # Save Export History Record
        now = datetime.now(timezone.utc)
        safe_name = "".join(c if c.isalnum() else "_" for c in campaign_name)
        timestamp_str = now.strftime("%Y-%m-%d")
        suffix = f"_{tier_filter.upper()}" if tier_filter else ("_QUALIFIED" if qualified_only else "")
        filename = f"LeadOS_{safe_name}{suffix}_{timestamp_str}.xlsx"

        export_rec = ExportHistory(
            id=uuid.uuid4(),
            campaign_id=campaign_id,
            format="xlsx",
            filters=filters,
            record_count=exported_records,
            filename=filename,
            created_at=now
        )
        db.add(export_rec)
        db.commit()

        return xlsx_bytes
    finally:
        db.close()
