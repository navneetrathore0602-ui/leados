import pytest
import io
import openpyxl
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.domain import Campaign, Business, SourceRecord, BusinessContact, BusinessLocation
from app.providers.osm import parse_search_query
from app.services.export_excel import generate_campaign_leads_xlsx

client = TestClient(app)

def test_parse_search_query_natural_input():
    """Verify natural language query parsing into category and location components."""
    parsed1 = parse_search_query("Restaurants in Mumbai")
    assert parsed1["category"].lower() == "restaurants"
    assert parsed1["location"].lower() == "mumbai"

    parsed2 = parse_search_query("Dentists in Bandra, Mumbai")
    assert parsed2["category"].lower() == "dentists"
    assert parsed2["location"].lower() == "bandra, mumbai"

    parsed3 = parse_search_query("Hotels")
    assert parsed3["category"] == "Hotels"
    assert parsed3["location"] == ""


def test_quick_search_api_flow():
    """Verify POST /api/v1/search/find-businesses and GET /api/v1/search/results/{campaign_id}."""
    payload = {
        "query": "Dentists in Delhi",
        "category": "Dentists",
        "location": "Delhi",
        "quantity": 50,
        "provider": "mock"
    }

    # 1. Initiate Find Businesses search
    res = client.post("/api/v1/search/find-businesses", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "campaign_id" in data
    assert data["requested_quantity"] == 50

    camp_id = data["campaign_id"]

    # 2. Fetch search results dataset
    res_results = client.get(f"/api/v1/search/results/{camp_id}")
    assert res_results.status_code == 200
    results_data = res_results.json()
    assert results_data["status"] == "success"
    assert "metrics" in results_data
    assert "leads" in results_data
    assert results_data["requested_quantity"] == 50


def test_excel_export_row_count_reconciliation():
    """Verify that generated XLSX row count strictly matches database records."""
    db = SessionLocal()
    try:
        # Create campaign and 10 mock businesses
        camp = Campaign(
            name="Test Excel Reconciliation",
            category="Cafes",
            locations=["Pune"],
            target_leads=10,
            provider="mock"
        )
        db.add(camp)
        db.commit()

        b_ids = []
        for i in range(10):
            b = Business(
                name=f"Cafe {i}",
                category="Cafes",
                website=f"https://cafe{i}.com" if i % 2 == 0 else None,
                rating=4.5
            )
            db.add(b)
            db.commit()

            loc = BusinessLocation(business_id=b.id, city="Pune", country="India")
            db.add(loc)

            sr = SourceRecord(
                source_name="mock",
                business_id=b.id,
                raw_data={"generated_for_campaign": str(camp.id)}
            )
            db.add(sr)
            b_ids.append(b.id)
        db.commit()

        # Generate XLSX
        xlsx_bytes = generate_campaign_leads_xlsx(camp.id)
        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))

        ws_leads = wb["SALES LEADS"]
        ws_summary = wb["SUMMARY"]

        data_rows = ws_leads.max_row - 1
        assert data_rows == 10  # Must match 10 DB leads exactly

    finally:
        db.close()
