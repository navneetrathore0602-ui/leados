import sys
import os
import pytest
import uuid
import csv
import io
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.core.database import SessionLocal
from app.models.domain import Business, Campaign, LeadScore, BusinessContact, BusinessLocation, BusinessSocial, SourceRecord
from app.services.scoring import calculate_lead_score, score_business, score_campaign_leads
from app.services.export import generate_campaign_leads_csv

client = TestClient(app)


def test_scoring_formula_ideal_lead():
    """Test scoring logic for an ideal, fully matched lead."""
    campaign = Campaign(
        id=uuid.uuid4(),
        name="Test Campaign",
        category="restaurants",
        locations=["Mumbai, India"],
        require_phone=True,
        require_email=False,
        min_rating=4.0
    )
    
    business = Business(
        id=uuid.uuid4(),
        name="Royal Spice Restaurant",
        category="restaurants",
        subcategory="Fine Dining",
        description="Premier authentic Indian restaurant in Mumbai",
        website="https://royalspice.com",
        rating=4.8,
        review_count=150
    )
    business.contacts = [
        BusinessContact(type="phone", value="+91 98765 43210"),
        BusinessContact(type="email", value="info@royalspice.com")
    ]
    business.locations = [
        BusinessLocation(address="123 MG Road", city="Mumbai", state="Maharashtra", country="India")
    ]
    business.socials = [
        BusinessSocial(platform="linkedin", profile_url="https://linkedin.com/company/royalspice"),
        BusinessSocial(platform="instagram", profile_url="https://instagram.com/royalspice")
    ]
    business.source_records = [
        SourceRecord(source_name="nominatim", source_url="https://nominatim.openstreetmap.org")
    ]
    
    score_data = calculate_lead_score(business, campaign)
    
    assert score_data["total_score"] == 100
    assert score_data["tier"] == "HOT"
    assert score_data["is_qualified"] is True
    assert score_data["disqualified"] is False
    assert score_data["scoring_version"] == "v1"
    
    # Check component scores
    assert score_data["business_fit_score"] == 30
    assert score_data["location_fit_score"] == 20
    assert score_data["contactability_score"] == 20
    assert score_data["digital_presence_score"] == 15
    assert score_data["data_quality_score"] == 15


def test_scoring_disqualification_rule():
    """Test disqualification when required phone is missing."""
    campaign = Campaign(
        id=uuid.uuid4(),
        name="Phone Required Campaign",
        category="dentists",
        locations=["Delhi"],
        require_phone=True,
        min_rating=4.0
    )
    
    business_no_phone = Business(
        id=uuid.uuid4(),
        name="Delhi Dental Clinic",
        category="dentists",
        website="https://delhidental.com",
        rating=4.5,
        review_count=20
    )
    business_no_phone.contacts = [] # Missing phone
    business_no_phone.locations = [BusinessLocation(city="Delhi")]
    
    score_data = calculate_lead_score(business_no_phone, campaign)
    
    assert score_data["disqualified"] is True
    assert score_data["is_qualified"] is False
    assert score_data["disqualification_reason"] is not None
    assert score_data["disqualified_rule"] == "REQUIRE_PHONE"


def test_scoring_mismatched_category_and_location():
    """Test lower scores when category and location do not match campaign."""
    campaign = Campaign(
        id=uuid.uuid4(),
        name="Bangalore IT Campaign",
        category="software development",
        locations=["Bangalore, Karnataka"],
    )
    
    business_mismatch = Business(
        id=uuid.uuid4(),
        name="Mumbai Bakery",
        category="bakery",
        rating=3.0,
        review_count=5
    )
    business_mismatch.contacts = [BusinessContact(type="phone", value="+91 22 12345678")]
    business_mismatch.locations = [BusinessLocation(city="Mumbai")]
    
    score_data = calculate_lead_score(business_mismatch, campaign)
    
    assert score_data["business_fit_score"] < 15
    assert score_data["location_fit_score"] < 10
    assert score_data["tier"] in ["COOL", "LOW"]


def test_score_business_persistence():
    """Test scoring a business and persisting the LeadScore in DB."""
    db = SessionLocal()
    try:
        campaign = Campaign(
            name="DB Test Campaign",
            category="plumbers",
            locations=["Pune"],
            require_phone=False
        )
        db.add(campaign)
        db.commit()
        
        business = Business(
            name="Pune Plumbing Works",
            category="plumbers",
            rating=4.2,
            review_count=45
        )
        business.contacts = [BusinessContact(type="phone", value="+91 99999 88888")]
        business.locations = [BusinessLocation(city="Pune")]
        db.add(business)
        db.commit()
        
        lead_score_dict = score_business(business.id, campaign.id, db=db)
        
        assert lead_score_dict["status"] == "success"
        assert lead_score_dict["total_score"] > 0
        assert lead_score_dict["scoring_details"]["scoring_version"] == "v1"
        
        # Check business lifecycle status update
        db.refresh(business)
        assert business.lifecycle_status in ["QUALIFIED", "SALES_READY", "ENRICHED"]
    finally:
        db.close()


def test_csv_export_generation():
    """Test generating CSV export for campaign leads."""
    db = SessionLocal()
    try:
        campaign = Campaign(
            name="Export Test Campaign",
            category="lawyers",
            locations=["Delhi"]
        )
        db.add(campaign)
        db.commit()
        
        business = Business(
            name="Legal Edge Chambers",
            category="lawyers",
            website="https://legaledge.in",
            rating=4.9,
            review_count=80
        )
        business.contacts = [
            BusinessContact(type="phone", value="+91 11 23456789"),
            BusinessContact(type="email", value="contact@legaledge.in")
        ]
        business.locations = [BusinessLocation(address="Connaught Place", city="Delhi")]
        db.add(business)
        db.commit()
        
        # Score lead
        score_business(business.id, campaign.id, db=db)
        
        # Export CSV
        csv_text = generate_campaign_leads_csv(campaign.id)
        
        reader = csv.DictReader(io.StringIO(csv_text))
        rows = list(reader)
        
        assert len(rows) >= 1
        found = any(r["Business Name"] == "Legal Edge Chambers" for r in rows)
        assert found is True
    finally:
        db.close()


def test_api_scoring_endpoints():
    """Test REST API endpoints for scoring and qualification."""
    db = SessionLocal()
    try:
        campaign = Campaign(
            name="API Campaign",
            category="clinics",
            locations=["Chennai"]
        )
        db.add(campaign)
        db.commit()
        
        business = Business(
            name="Chennai Health Center",
            category="clinics",
            rating=4.5,
            review_count=30
        )
        business.contacts = [BusinessContact(type="phone", value="+91 44 24680000")]
        business.locations = [BusinessLocation(city="Chennai")]
        db.add(business)
        db.commit()
        
        camp_id = str(campaign.id)
        bus_id = str(business.id)
    finally:
        db.close()
    
    # 1. Score single business via API
    resp = client.post(f"/api/v1/businesses/{bus_id}/score?campaign_id={camp_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["business_id"] == bus_id
    assert "total_score" in data
    
    # 2. Batch score campaign via API
    resp_batch = client.post(f"/api/v1/campaigns/{camp_id}/score")
    assert resp_batch.status_code == 200
    batch_data = resp_batch.json()
    assert batch_data["total_scored"] >= 1
    
    # 3. Get qualified leads via API
    resp_qual = client.get(f"/api/v1/campaigns/{camp_id}/qualified-leads")
    assert resp_qual.status_code == 200
    qual_data = resp_qual.json()
    assert "items" in qual_data
    
    # 4. Get CSV export via API
    resp_csv = client.get(f"/api/v1/campaigns/{camp_id}/export/csv")
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
