import sys
import os
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

def test_create_campaign_validation_errors():
    # Empty name error
    resp = client.post("/api/campaigns", json={"name": "", "category": "Test"})
    assert resp.status_code == 400 or resp.status_code == 422

    # No category and no keywords
    resp = client.post("/api/campaigns", json={"name": "Test Campaign", "keywords": []})
    assert resp.status_code == 400

    # Negative target_leads
    resp = client.post("/api/campaigns", json={"name": "Test", "category": "Cat", "target_leads": -5})
    assert resp.status_code == 422

    # Invalid rating > 5
    resp = client.post("/api/campaigns", json={"name": "Test", "category": "Cat", "min_rating": 6.0})
    assert resp.status_code == 422

def test_campaign_crud_lifecycle():
    # 1. Create valid campaign
    payload = {
        "name": "Mumbai Marble Dealers",
        "description": "Test discovery campaign",
        "category": "Marble & Granite",
        "keywords": ["marble dealer", "granite dealer"],
        "locations": ["Mumbai", "Thane"],
        "target_leads": 50,
        "min_rating": 4.0,
        "min_reviews": 10,
        "require_phone": True,
        "require_website": False,
        "provider": "mock"
    }
    create_resp = client.post("/api/campaigns", json=payload)
    assert create_resp.status_code in [200, 201]
    data = create_resp.json()
    campaign_id = data["id"]
    assert data["name"] == "Mumbai Marble Dealers"
    assert data["status"] == "draft"

    # 2. Get list of campaigns
    list_resp = client.get("/api/campaigns")
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert campaign_id in ids

    # 3. Get single campaign detail
    get_resp = client.get(f"/api/campaigns/{campaign_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == campaign_id

    # 4. Start campaign
    start_resp = client.post(f"/api/campaigns/{campaign_id}/start")
    assert start_resp.status_code == 200
    # In TestClient background tasks execute synchronously
    assert start_resp.json()["status"] in ["queued", "running", "completed"]

    # 5. Create another campaign to test pause and cancel
    camp2_resp = client.post("/api/campaigns", json={"name": "Pause Test Campaign", "category": "Test"})
    assert camp2_resp.status_code == 201
    c2_id = camp2_resp.json()["id"]

    # Cancel draft/paused campaign
    cancel_resp = client.post(f"/api/campaigns/{c2_id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # 6. Cannot start cancelled campaign without reset
    restart_resp = client.post(f"/api/campaigns/{c2_id}/start")
    assert restart_resp.status_code == 400
