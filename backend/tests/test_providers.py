import sys
import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import SessionLocal
from app.models.domain import Campaign, DiscoveryJob, Business, SourceRecord
from app.providers.osm import OpenStreetMapProvider
from app.providers.registry import list_providers, get_provider, get_providers_health
from app.services.quality import calculate_campaign_data_quality
from app.services.discovery import execute_discovery_job

client = TestClient(app)


def test_provider_registry_and_api():
    providers = list_providers()
    provider_ids = [p["id"] for p in providers]
    assert "mock" in provider_ids
    assert "osm" in provider_ids or "openstreetmap" in provider_ids

    osm_inst = get_provider("osm")
    assert isinstance(osm_inst, OpenStreetMapProvider)

    resp = client.get("/api/providers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    mock_p = next((p for p in data if p["provider"] == "mock"), None)
    assert mock_p is not None
    assert mock_p["healthy"] is True


def test_osm_provider_search_mocked():
    provider = OpenStreetMapProvider()
    assert provider.health_check() is True

    class DummyCampaign:
        id = uuid.uuid4()
        target_leads = 10
        keywords = ["Marble Dealer"]
        locations = ["Mumbai"]
        category = "Marble & Granite"

    mock_osm_response = [
        {
            "place_id": 12345,
            "osm_id": 987654321,
            "display_name": "Royal Marble Shop, MG Road, Mumbai, Maharashtra, India",
            "lat": "19.0760",
            "lon": "72.8777",
            "category": "shop",
            "type": "trade",
            "address": {
                "shop": "Royal Marble Shop",
                "road": "MG Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postcode": "400001",
                "country": "India"
            },
            "extratags": {
                "phone": "+91 98200 11223",
                "website": "https://www.royalmarble.example.com",
                "opening_hours": "Mo-Sa 09:00-19:00"
            }
        }
    ]

    mock_response_obj = MagicMock()
    mock_response_obj.status_code = 200
    mock_response_obj.json.return_value = mock_osm_response
    mock_response_obj.raise_for_status.return_value = None

    with patch("httpx.Client.get", return_value=mock_response_obj):
        results = provider.search(DummyCampaign(), page=1, limit=10)
        assert len(results) == 1
        res = results[0]
        assert res["name"] == "Royal Marble Shop"
        assert res["city"] == "Mumbai"
        assert res["phone"] == "+91 98200 11223"
        assert res["website"] == "https://www.royalmarble.example.com"
        assert res["source_name"] == "OpenStreetMap Places API"
        assert res["raw_data"]["place_id"] == 12345


def test_data_quality_calculator():
    db = SessionLocal()
    try:
        camp_id = uuid.uuid4()
        quality = calculate_campaign_data_quality(db, camp_id)
        assert "name_coverage" in quality
        assert "phone_coverage" in quality
        assert "website_coverage" in quality
        assert "address_coverage" in quality
    finally:
        db.close()


def test_discovery_with_osm_provider_mocked():
    db = SessionLocal()
    try:
        camp_id = uuid.uuid4()
        job_id = uuid.uuid4()

        campaign = Campaign(
            id=camp_id,
            name="OSM Provider Campaign",
            category="Marble & Granite",
            keywords=["marble"],
            locations=["Mumbai"],
            provider="osm",
            target_leads=5,
            status="queued"
        )
        db.add(campaign)

        job = DiscoveryJob(
            id=job_id,
            campaign_id=camp_id,
            provider="osm",
            status="queued",
            target_count=5
        )
        db.add(job)
        db.commit()

        mock_osm_payload = [
            {
                "place_id": 99901,
                "osm_id": 88801,
                "display_name": "Test OSM Stone Co, Mumbai",
                "lat": "19.0",
                "lon": "72.8",
                "address": {"city": "Mumbai"},
                "extratags": {"phone": "+91 90000 00001"}
            }
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_osm_payload
        mock_response.raise_for_status.return_value = None

        with patch("httpx.Client.get", return_value=mock_response):
            execute_discovery_job(str(camp_id), str(job_id))

        db.refresh(campaign)
        db.refresh(job)

        assert campaign.status == "completed"
        assert campaign.provider == "osm"
        assert campaign.discovered_count == 5
        assert campaign.started_at is not None
        assert campaign.completed_at is not None
        duration = (campaign.completed_at - campaign.started_at).total_seconds()
        assert duration >= 0

        # Verify source record raw_data retained
        sr = db.query(SourceRecord).filter(SourceRecord.source_name == "OpenStreetMap Places API").first()
        assert sr is not None
        assert sr.source_name == "OpenStreetMap Places API"
        assert sr.raw_data is not None
        assert sr.raw_data.get("place_id") == 99901
    finally:
        db.close()
