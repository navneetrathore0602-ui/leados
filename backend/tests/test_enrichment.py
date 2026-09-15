import sys
import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import SessionLocal
from app.models.domain import Business, BusinessContact, BusinessSocial, BusinessCandidateField, EnrichmentJob, Campaign, DiscoveryJob, SourceRecord, BusinessLocation
from app.enrichment.base import EnrichmentProvider
from app.enrichment.mock import MockEnrichmentProvider
from app.enrichment.website import WebsiteEnrichmentProvider, is_plausible_phone, validate_email_syntax, normalize_social_url
from app.enrichment.registry import get_enrichment_provider, list_enrichment_providers
from app.services.enrichment import execute_business_enrichment, execute_campaign_batch_enrichment
from app.services.quality import calculate_campaign_data_quality

client = TestClient(app)


def test_is_plausible_phone_precision():
    # 1. Reject software version numbers and floating point decimals
    assert is_plausible_phone("5.6666666666666") is False
    assert is_plausible_phone("3.1415926535") is False
    assert is_plausible_phone("Python 3.12.1") is False

    # 2. Reject standalone years
    assert is_plausible_phone("2024") is False
    assert is_plausible_phone("2025") is False
    assert is_plausible_phone("2026") is False

    # 3. Reject repeating digits
    assert is_plausible_phone("0000000000") is False

    # 4. Reject standalone postal codes without phone context
    assert is_plausible_phone("400001") is False

    # 5. Accept legitimate phones
    assert is_plausible_phone("+91 98200 77889") is True
    assert is_plausible_phone("+1 (800) 555-0199") is True
    assert is_plausible_phone("022-28349900", context_text="Call phone: 022-28349900") is True


def test_validate_email_syntax_precision():
    assert validate_email_syntax("info@example.com") == "info@example.com"
    assert validate_email_syntax("sales.mumbai@corp.co.in") == "sales.mumbai@corp.co.in"
    assert validate_email_syntax("invalid-email") is None
    assert validate_email_syntax("user@domain..com") is None
    assert validate_email_syntax("user..name@domain.com") is None
    assert validate_email_syntax("user@domain") is None


def test_normalize_social_url_canonicalization():
    # Strip tracking parameters
    res = normalize_social_url("https://www.instagram.com/apex_stone/?utm_source=ig_web&igshid=12345", "instagram")
    assert res is not None
    assert res["profile_url"] == "https://www.instagram.com/apex_stone"
    assert res["username"] == "apex_stone"

    # Reject generic share links
    assert normalize_social_url("https://www.facebook.com/sharer/sharer.php?u=https://example.com", "facebook") is None
    assert normalize_social_url("https://twitter.com/intent/tweet?text=hello", "x") is None


def test_enrichment_provider_registry():
    providers = list_enrichment_providers()
    p_ids = [p["id"] for p in providers]
    assert "website" in p_ids
    assert "mock" in p_ids

    mock_inst = get_enrichment_provider("mock")
    assert isinstance(mock_inst, MockEnrichmentProvider)
    assert mock_inst.health_check() is True

    web_inst = get_enrichment_provider("website")
    assert isinstance(web_inst, WebsiteEnrichmentProvider)


def test_mock_enrichment_provider():
    provider = MockEnrichmentProvider(seed=99)
    class DummyBusiness:
        id = uuid.uuid4()
        name = "Apex Stone Studio"
        website = "https://www.apexstone.example.com"

    res = provider.enrich(DummyBusiness())
    assert res["website"]["value"] == "https://www.apexstone.example.com"
    assert res["phone"]["value"] is not None
    assert res["email"]["verification_status"] == "syntax_valid"
    assert len(res["social_profiles"]) >= 2
    assert len(res["candidate_fields"]) >= 1


def test_website_enrichment_html_parsing_mocked():
    provider = WebsiteEnrichmentProvider()

    class DummyBusiness:
        id = uuid.uuid4()
        name = "Royal Marbles"
        website = "https://www.royalmarbles.example.com"

    mock_html = """
    <!DOCTYPE html>
    <html>
      <head>
        <title>Royal Marbles - Premium Stone Solutions</title>
        <meta name="description" content="Royal Marbles is the top supplier of Indian marble and granite in Mumbai.">
      </head>
      <body>
        <h1>Welcome to Royal Marbles</h1>
        <p>Call us at +91 98200 77889 or email info@royalmarbles.example.com</p>
        <a href="tel:+919820077889">Phone Us</a>
        <a href="mailto:sales@royalmarbles.example.com">Email Sales</a>
        <a href="https://wa.me/919820077889">Chat on WhatsApp</a>
        <a href="https://www.instagram.com/royalmarbles_mumbai/?utm_source=test">Instagram</a>
        <a href="https://www.facebook.com/royalmarblesmumbai/">Facebook</a>
        <a href="https://www.linkedin.com/company/royal-marbles-pvt-ltd/">LinkedIn</a>
      </body>
    </html>
    """

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "text/html"}
    mock_response.text = mock_html
    mock_response.content = mock_html.encode("utf-8")

    with patch("httpx.Client.get", return_value=mock_response):
        res = provider.enrich(DummyBusiness())

    assert res["reachability_state"] == "SUCCESS"
    assert res["phone"] is not None
    assert res["phone"]["normalized_value"] == "919820077889"
    assert res["email"] is not None
    assert res["email"]["verification_status"] == "syntax_valid"
    assert res["whatsapp"] is not None
    assert "wa.me" in res["whatsapp"]["value"]
    
    platforms = [s["platform"] for s in res["social_profiles"]]
    assert "instagram" in platforms
    assert "facebook" in platforms
    assert "linkedin" in platforms
    assert res["description"]["value"].startswith("Royal Marbles is")
    assert len(res["telemetry_logs"]) >= 1


def test_single_business_enrichment_service():
    db = SessionLocal()
    try:
        b_id = uuid.uuid4()
        b = Business(
            id=b_id,
            name="Enrichment Test Company",
            category="Stone Supplies",
            website="https://www.enrichmenttest.example.com"
        )
        db.add(b)
        db.commit()

        # Execute single business enrichment with mock provider
        result = execute_business_enrichment(str(b_id), provider_name="mock")
        assert result["status"] in ["completed", "partial"]

        db.refresh(b)
        assert len(b.contacts) > 0
        assert len(b.socials) > 0
        assert len(b.candidate_fields) > 0

        # Check job record
        job = db.query(EnrichmentJob).filter(EnrichmentJob.business_id == b_id).first()
        assert job is not None
        assert job.status in ["completed", "partial"]
        assert job.reachability_state is not None
        assert job.duration >= 0

        # Clean up
        db.delete(b)
        db.commit()
    finally:
        db.close()


def test_batch_campaign_enrichment_service():
    db = SessionLocal()
    try:
        c_id = uuid.uuid4()
        j_id = uuid.uuid4()
        b_id = uuid.uuid4()

        camp = Campaign(
            id=c_id,
            name="Batch Enrichment Campaign",
            category="Testing",
            status="completed"
        )
        db.add(camp)

        b = Business(
            id=b_id,
            name="Batch Test Lead",
            website="https://www.batchtest.example.com"
        )
        db.add(b)

        sr = SourceRecord(
            id=uuid.uuid4(),
            business_id=b_id,
            source_name="Mock Provider",
            raw_data={"generated_for_campaign": str(c_id)}
        )
        db.add(sr)
        db.commit()

        res = execute_campaign_batch_enrichment(str(c_id), provider_name="mock")
        assert res["status"] == "completed"
        assert res["enriched_count"] >= 1
        assert "avg_latency_ms" in res
        assert "median_latency_ms" in res
        assert "p95_latency_ms" in res

        db.refresh(camp)
        quality = calculate_campaign_data_quality(db, c_id)
        assert "phone_coverage" in quality
        assert "website_coverage" in quality
        assert "email_coverage" in quality

        # Clean up
        db.delete(sr)
        db.delete(b)
        db.delete(camp)
        db.commit()
    finally:
        db.close()


def test_enrichment_api_endpoints():
    db = SessionLocal()
    try:
        b_id = uuid.uuid4()
        c_id = uuid.uuid4()

        b = Business(id=b_id, name="API Test Business")
        c = Campaign(id=c_id, name="API Test Campaign")
        db.add(b)
        db.add(c)
        db.commit()

        # 1. Trigger single business enrichment
        post_resp = client.post(f"/api/businesses/{b_id}/enrich?provider=mock")
        assert post_resp.status_code == 200
        assert post_resp.json()["status"] == "queued"

        # 2. Get business enrichment details
        get_resp = client.get(f"/api/businesses/{b_id}/enrichment")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["business_id"] == str(b_id)

        # 3. Trigger campaign batch enrichment
        camp_post = client.post(f"/api/campaigns/{c_id}/enrich?provider=mock")
        assert camp_post.status_code == 200
        assert camp_post.json()["status"] == "queued"

        # 4. Get campaign enrichment status
        camp_get = client.get(f"/api/campaigns/{c_id}/enrichment")
        assert camp_get.status_code == 200
        assert "quality_metrics" in camp_get.json()

        # Clean up
        db.delete(b)
        db.delete(c)
        db.commit()
    finally:
        db.close()

