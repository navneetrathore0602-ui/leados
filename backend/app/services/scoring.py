import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.domain import Business, Campaign, LeadScore, BusinessContact, BusinessSocial, BusinessCandidateField, SourceRecord


def calculate_lead_score(business: Business, campaign: Optional[Campaign] = None, ruleset: str = "default_v1") -> Dict[str, Any]:
    """
    Deterministic Lead Intelligence Engine.
    Calculates component scores:
    - Business Fit (0-30 pts)
    - Location Fit (0-20 pts)
    - Contactability (0-20 pts)
    - Digital Presence (0-15 pts)
    - Data Quality (0-15 pts)
    Sums to 0-100 total score.
    Assigns tier (HOT, WARM, COOL, LOW), lifecycle status, positive/negative signals, and qualification rules.
    """
    positive_signals: List[str] = []
    negative_signals: List[str] = []
    reasons: List[str] = []

    is_qualified = True
    disqualified = False
    disqualification_reason: Optional[str] = None
    disqualified_rule: Optional[str] = None

    # 1. Business Fit (0-30 pts)
    business_fit = 0
    b_category = (business.category or "").strip().lower()

    if campaign and campaign.category:
        camp_cat = campaign.category.strip().lower()
        if camp_cat and b_category:
            if camp_cat in b_category or b_category in camp_cat:
                business_fit += 20
                positive_signals.append(f"Strong industry match for '{campaign.category}'")
                reasons.append(f"+20: Industry match ({business.category})")
            else:
                business_fit += 5
                negative_signals.append(f"Industry mismatch (Business: '{business.category}', Target: '{campaign.category}')")
                reasons.append("+5: Partial industry alignment")
        elif b_category:
            business_fit += 10
            positive_signals.append(f"Category identified: {business.category}")
            reasons.append("+10: Category specified")
    elif b_category:
        business_fit += 15
        positive_signals.append(f"Category present: {business.category}")
        reasons.append("+15: Category specified")

    if business.description and len(business.description.strip()) > 20:
        business_fit += 5
        positive_signals.append("Rich business description available")
        reasons.append("+5: Detailed business description")

    if business.subcategory:
        business_fit += 5
        reasons.append("+5: Subcategory specified")

    business_fit = min(business_fit, 30)

    # 2. Location Fit (0-20 pts)
    location_fit = 0
    primary_loc = business.locations[0] if business.locations else None
    loc_city = (primary_loc.city or "").strip().lower() if primary_loc else ""
    loc_state = (primary_loc.state or "").strip().lower() if primary_loc else ""

    if campaign and campaign.locations:
        camp_locs = [l.strip().lower() for l in (campaign.locations if isinstance(campaign.locations, list) else [])]
        matched_loc = False
        for cl in camp_locs:
            if cl and (cl in loc_city or cl in loc_state or loc_city in cl):
                location_fit += 15
                positive_signals.append(f"Exact location match for target '{cl.title()}'")
                reasons.append(f"+15: Target location match ({primary_loc.city if primary_loc else 'Matched'})")
                matched_loc = True
                break
        if not matched_loc:
            if primary_loc and (primary_loc.city or primary_loc.state):
                location_fit += 5
                negative_signals.append("Business location differs from target campaign geography")
                reasons.append("+5: Location present but outside primary target")
            else:
                location_fit += 0
                negative_signals.append("Missing location details")
    elif primary_loc and (primary_loc.city or primary_loc.address):
        location_fit += 15
        positive_signals.append(f"Location recorded: {primary_loc.city or primary_loc.address}")
        reasons.append("+15: Physical location verified")
    elif primary_loc:
        location_fit += 10
        reasons.append("+10: Partial location recorded")

    if primary_loc and primary_loc.address:
        location_fit += 5
        reasons.append("+5: Full street address available")

    location_fit = min(location_fit, 20)

    # 3. Contactability (0-20 pts)
    contactability = 0
    has_phone = any(c.type in ["phone", "mobile"] for c in business.contacts)
    has_email = any(c.type == "email" for c in business.contacts)
    has_website = bool(business.website and business.website.strip())
    has_socials = bool(business.socials and len(business.socials) > 0)

    if has_phone:
        contactability += 8
        positive_signals.append("Valid business phone number available")
        reasons.append("+8: Direct phone line available")

    if has_email:
        contactability += 7
        positive_signals.append("Syntax-valid email address found")
        reasons.append("+7: Email address recorded")

    if has_website:
        contactability += 3
        positive_signals.append("Official website active")
        reasons.append("+3: Website URL available")

    if has_socials:
        contactability += 2
        positive_signals.append("Social media contact channels present")
        reasons.append("+2: Social profile channels present")

    if not has_phone and not has_email:
        negative_signals.append("No direct phone or email contact channels available")

    contactability = min(contactability, 20)

    # 4. Digital Presence (0-15 pts)
    digital_presence = 0

    if has_website:
        digital_presence += 5
        reasons.append("+5: Website active")

    social_count = len(business.socials) if business.socials else 0
    if social_count >= 2:
        digital_presence += 4
        positive_signals.append(f"Active multi-platform social presence ({social_count} profiles)")
        reasons.append(f"+4: Multi-channel social profiles ({social_count})")
    elif social_count == 1:
        digital_presence += 2
        reasons.append("+2: Single social profile present")

    if business.rating and float(business.rating) >= 4.0:
        digital_presence += 3
        positive_signals.append(f"High rating: {business.rating}/5.0")
        reasons.append(f"+3: High customer rating ({business.rating})")
    elif business.rating and float(business.rating) >= 3.0:
        digital_presence += 1
        reasons.append(f"+1: Moderate rating ({business.rating})")

    if business.review_count and business.review_count >= 10:
        digital_presence += 3
        positive_signals.append(f"Established review base ({business.review_count} reviews)")
        reasons.append(f"+3: Strong review volume ({business.review_count})")

    digital_presence = min(digital_presence, 15)

    # 5. Data Quality (0-15 pts)
    data_quality = 0

    fields_present = sum([
        1 if business.name else 0,
        1 if business.category else 0,
        1 if primary_loc and primary_loc.address else 0,
        1 if has_phone else 0,
        1 if has_website else 0,
        1 if has_email else 0
    ])
    data_quality += min(fields_present, 6)
    reasons.append(f"+{min(fields_present, 6)}: Data field completeness ({fields_present}/6 key fields)")

    source_count = len(business.source_records) if business.source_records else 0
    if source_count >= 1:
        data_quality += 4
        positive_signals.append("Multi-source provenance verified")
        reasons.append("+4: Provenance source records present")

    conflicting_candidates = [c for c in (business.candidate_fields or []) if getattr(c, "status", "") == "conflicting"]
    if not conflicting_candidates:
        data_quality += 5
        reasons.append("+5: Zero data conflicts detected")
    else:
        negative_signals.append(f"{len(conflicting_candidates)} conflicting candidate data value(s)")
        reasons.append(f"0: Data conflict detected ({len(conflicting_candidates)} items)")

    data_quality = min(data_quality, 15)

    # Total Score Sum
    total_score = business_fit + location_fit + contactability + digital_presence + data_quality
    total_score = min(max(total_score, 0), 100)

    # Qualification Rules Engine
    if campaign:
        if campaign.require_phone and not has_phone:
            is_qualified = False
            disqualified = True
            disqualification_reason = "Missing required phone contact line"
            disqualified_rule = "REQUIRE_PHONE"
            negative_signals.append("DISQUALIFIED: Failed campaign requirement 'require_phone'")

        elif campaign.require_email and not has_email:
            is_qualified = False
            disqualified = True
            disqualification_reason = "Missing required email address"
            disqualified_rule = "REQUIRE_EMAIL"
            negative_signals.append("DISQUALIFIED: Failed campaign requirement 'require_email'")

        elif campaign.require_website and not has_website:
            is_qualified = False
            disqualified = True
            disqualification_reason = "Missing required business website"
            disqualified_rule = "REQUIRE_WEBSITE"
            negative_signals.append("DISQUALIFIED: Failed campaign requirement 'require_website'")

        elif campaign.min_rating and business.rating and float(business.rating) < float(campaign.min_rating):
            is_qualified = False
            disqualified = True
            disqualification_reason = f"Rating {business.rating} below minimum required {campaign.min_rating}"
            disqualified_rule = "MIN_RATING"
            negative_signals.append(f"DISQUALIFIED: Rating below campaign threshold ({campaign.min_rating})")

        elif campaign.min_reviews and business.review_count and business.review_count < campaign.min_reviews:
            is_qualified = False
            disqualified = True
            disqualification_reason = f"Review count {business.review_count} below minimum {campaign.min_reviews}"
            disqualified_rule = "MIN_REVIEWS"
            negative_signals.append(f"DISQUALIFIED: Reviews below campaign threshold ({campaign.min_reviews})")

    # Lead Tier Classification
    if total_score >= 80:
        tier = "HOT"
    elif total_score >= 60:
        tier = "WARM"
    elif total_score >= 40:
        tier = "COOL"
    else:
        tier = "LOW"

    # Lead Lifecycle Status Flow
    if disqualified:
        lifecycle_status = "DISQUALIFIED"
    elif total_score >= 70 and (has_phone or has_email) and has_website:
        lifecycle_status = "SALES_READY"
    elif is_qualified and total_score >= 40:
        lifecycle_status = "QUALIFIED"
    elif has_website or has_phone or has_email:
        lifecycle_status = "ENRICHED"
    else:
        lifecycle_status = "NEW"

    return {
        "total_score": total_score,
        "tier": tier,
        "lifecycle_status": lifecycle_status,
        "business_fit_score": business_fit,
        "location_fit_score": location_fit,
        "contactability_score": contactability,
        "digital_presence_score": digital_presence,
        "data_quality_score": data_quality,
        "scoring_version": "v1",
        "scoring_ruleset": ruleset,
        "positive_signals": positive_signals,
        "negative_signals": negative_signals,
        "reasons": reasons,
        "is_qualified": is_qualified,
        "disqualified": disqualified,
        "disqualification_reason": disqualification_reason,
        "disqualified_rule": disqualified_rule
    }


def score_business(business_id: Any, campaign_id: Optional[Any] = None, ruleset: str = "default_v1", db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Scores a single business and records structured LeadScore entry in the database.
    """
    own_session = False
    if db is None:
        db = SessionLocal()
        own_session = True

    try:
        if isinstance(business_id, str):
            business_id = uuid.UUID(business_id)

        business = db.query(Business).filter(Business.id == business_id).first()
        if not business:
            return {"status": "failed", "error": "Business not found"}

        campaign = None
        if campaign_id:
            if isinstance(campaign_id, str):
                campaign_id = uuid.UUID(campaign_id)
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()

        score_res = calculate_lead_score(business, campaign, ruleset)

        # Update business table fields
        business.lead_score = score_res["total_score"]
        business.lifecycle_status = score_res["lifecycle_status"]

        now = datetime.now(timezone.utc)
        lead_score_record = LeadScore(
            id=uuid.uuid4(),
            business_id=business.id,
            campaign_id=campaign.id if campaign else None,
            total_score=score_res["total_score"],
            tier=score_res["tier"],
            lifecycle_status=score_res["lifecycle_status"],
            business_fit_score=score_res["business_fit_score"],
            location_fit_score=score_res["location_fit_score"],
            contactability_score=score_res["contactability_score"],
            digital_presence_score=score_res["digital_presence_score"],
            data_quality_score=score_res["data_quality_score"],
            scoring_version=score_res["scoring_version"],
            scoring_ruleset=score_res["scoring_ruleset"],
            positive_signals=score_res["positive_signals"],
            negative_signals=score_res["negative_signals"],
            reasons=score_res["reasons"],
            is_qualified=score_res["is_qualified"],
            disqualified=score_res["disqualified"],
            disqualification_reason=score_res["disqualification_reason"],
            disqualified_rule=score_res["disqualified_rule"],
            scored_at=now
        )
        db.add(lead_score_record)
        db.commit()

        return {
            "status": "success",
            "business_id": str(business.id),
            "score_id": str(lead_score_record.id),
            "total_score": score_res["total_score"],
            "tier": score_res["tier"],
            "lifecycle_status": score_res["lifecycle_status"],
            "is_qualified": score_res["is_qualified"],
            "disqualified": score_res["disqualified"],
            "scoring_details": score_res
        }
    except Exception as e:
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        if own_session:
            db.close()


def score_campaign_leads(campaign_id: Any, ruleset: str = "default_v1") -> Dict[str, Any]:
    """
    Batch scores all businesses associated with a campaign.
    """
    db = SessionLocal()
    try:
        if isinstance(campaign_id, str):
            campaign_id = uuid.UUID(campaign_id)

        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return {"status": "failed", "error": "Campaign not found"}

        # Find businesses linked to this campaign via SourceRecords or recent category matches
        from app.models.domain import SourceRecord
        source_records = db.query(SourceRecord).filter(SourceRecord.raw_data.isnot(None)).all()
        b_ids = set()

        for sr in source_records:
            if isinstance(sr.raw_data, dict) and sr.raw_data.get("generated_for_campaign") == str(campaign_id):
                if sr.business_id:
                    b_ids.add(sr.business_id)

        if not b_ids:
            businesses = db.query(Business).limit(100).all()
            b_ids = {b.id for b in businesses}

        scored_count = 0
        qualified_count = 0
        disqualified_count = 0
        hot_count = 0
        warm_count = 0
        cool_count = 0
        low_count = 0

        for b_id in b_ids:
            res = score_business(b_id, campaign_id=campaign_id, ruleset=ruleset, db=db)
            if res.get("status") == "success":
                scored_count += 1
                if res.get("is_qualified"):
                    qualified_count += 1
                else:
                    disqualified_count += 1

                t = res.get("tier")
                if t == "HOT": hot_count += 1
                elif t == "WARM": warm_count += 1
                elif t == "COOL": cool_count += 1
                elif t == "LOW": low_count += 1

        return {
            "status": "completed",
            "campaign_id": str(campaign_id),
            "total_scored": scored_count,
            "qualified_count": qualified_count,
            "disqualified_count": disqualified_count,
            "tier_counts": {
                "HOT": hot_count,
                "WARM": warm_count,
                "COOL": cool_count,
                "LOW": low_count
            }
        }
    finally:
        db.close()
