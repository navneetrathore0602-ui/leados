import sys
import os
import uuid
import pytest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.domain import Campaign, DiscoveryJob, Business, SourceRecord, BusinessLocation, BusinessContact
from app.providers.mock import MockDiscoveryProvider
from app.services.normalization import normalize_business_name, normalize_website, normalize_phone
from app.services.deduplication import find_duplicate_business
from app.services.discovery import execute_discovery_job

def test_normalization_rules():
    assert normalize_business_name("ABC MARBLES PVT. LTD.") == "abc marbles"
    assert normalize_business_name("Royal Stone House Private Limited") == "royal stone house"
    assert normalize_website("https://WWW.AbcMarbles.Example.In/") == "abcmarbles.example.in"
    assert normalize_phone("+91 (98200) 12345") == "919820012345"

def test_mock_discovery_provider():
    provider = MockDiscoveryProvider(seed=123)
    assert provider.health_check() is True

    class DummyCampaign:
        id = uuid.uuid4()
        target_leads = 20
        keywords = ["Marble Dealer"]
        locations = ["Mumbai"]
        category = "Marble & Granite"

    results = provider.search(DummyCampaign(), page=1, limit=10)
    assert len(results) == 10
    item = results[0]
    assert "name" in item
    assert "city" in item
    assert item["source_name"] == "Mock Discovery Provider"

def test_deduplication_engine():
    db = SessionLocal()
    try:
        # Create dummy existing business
        b_id = uuid.uuid4()
        b = Business(
            id=b_id,
            name="Unique Test Marble",
            normalized_name="unique test marble",
            website="https://www.uniquetestmarble.example.com",
            category="Marble"
        )
        db.add(b)
        db.commit()

        # Test matching by normalized name
        matched, confidence, reason = find_duplicate_business(
            db=db,
            normalized_name="unique test marble",
            norm_website="uniquetestmarble.example.com"
        )
        assert matched is not None
        assert matched.id == b_id
        assert confidence >= 0.80

        # Clean up
        db.delete(b)
        db.commit()
    finally:
        db.close()

def test_full_discovery_job_execution():
    db = SessionLocal()
    try:
        camp_id = uuid.uuid4()
        job_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        campaign = Campaign(
            id=camp_id,
            name="End to End Discovery Campaign",
            category="Marble & Granite",
            keywords=["marble dealer", "granite dealer"],
            locations=["Mumbai", "Thane"],
            target_leads=30,
            min_rating=3.5,
            min_reviews=5,
            status="queued",
            created_at=now
        )
        db.add(campaign)

        job = DiscoveryJob(
            id=job_id,
            campaign_id=camp_id,
            provider="mock",
            status="queued",
            target_count=30,
            created_at=now
        )
        db.add(job)
        db.commit()

        # Clear existing test businesses for clean deduplication state
        db.query(SourceRecord).delete()
        db.query(BusinessLocation).delete()
        db.query(BusinessContact).delete()
        db.query(Business).delete()
        db.commit()

        # Execute discovery service synchronously for test assertion
        execute_discovery_job(str(camp_id), str(job_id))

        db.refresh(campaign)
        db.refresh(job)

        assert campaign.status == "completed"
        assert job.status == "completed"
        assert campaign.discovered_count > 0
        assert (campaign.unique_count + campaign.duplicate_count) == campaign.discovered_count
        assert campaign.unique_count > 0

        # Verify source records retained
        source_records_count = db.query(SourceRecord).count()
        assert source_records_count > 0

    finally:
        db.close()
