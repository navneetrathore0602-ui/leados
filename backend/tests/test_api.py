import sys
import os
import pytest
from fastapi.testclient import TestClient

# Add backend root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()

def test_get_stats():
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_businesses" in data
    assert "total_leads" in data
    assert "hot_leads" in data
    assert "warm_leads" in data
    assert "cold_leads" in data
    assert "verified_contacts" in data
    assert "businesses_by_category" in data
    assert "businesses_by_city" in data

def test_get_leads_pagination():
    response = client.get("/api/leads?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5

def test_get_leads_search():
    response = client.get("/api/leads?search=Apex")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert "Apex" in item["name"] or "Apex" in (item["category"] or "")

def test_get_leads_category_filter():
    response = client.get("/api/leads?category=Technology")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert "Technology" in (item["category"] or "")

def test_get_leads_score_filter():
    response = client.get("/api/leads?minimum_score=80")
    assert response.status_code == 200
    data = response.json()
    for item in data["items"]:
        assert item["lead_score"] >= 80

def test_get_lead_by_id():
    # First fetch list to get a valid lead_id
    list_resp = client.get("/api/leads?page_size=1")
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    assert len(items) > 0

    lead_id = items[0]["id"]
    detail_resp = client.get(f"/api/leads/{lead_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == lead_id
    assert "locations" in detail
    assert "contacts" in detail
    assert "source_records" in detail

def test_get_lead_by_invalid_id():
    response = client.get("/api/leads/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
