import pytest
from fastapi.testclient import TestClient
from backend.main import app, seed_default_categories
from backend.database import Base, engine


@pytest.fixture(scope="module")
def client():
    # Ensure tables and default seed exist for testing
    Base.metadata.create_all(bind=engine)
    seed_default_categories()
    with TestClient(app) as c:
        yield c


def test_categories_endpoint(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 12
    # Verify default categories exist
    names = [c["name"] for c in data]
    assert "Food & Dining" in names
    assert "Transport" in names


def test_add_and_list_expense(client):
    # Fetch categories to get ID for Food & Dining
    cat_resp = client.get("/api/categories")
    categories = cat_resp.json()
    food_cat = next((c for c in categories if c["name"] == "Food & Dining"), categories[0])

    # Create expense
    payload = {
        "amount": 350.0,
        "category_id": food_cat["id"],
        "description": "Test Swiggy Order",
        "raw_input": "swiggy 350",
        "date": "2026-08-07"
    }
    post_resp = client.post("/api/expenses", json=payload)
    assert post_resp.status_code == 201
    created = post_resp.json()
    assert created["amount"] == 350.0
    assert created["description"] == "Test Swiggy Order"
    expense_id = created["id"]

    # List expenses
    get_resp = client.get("/api/expenses")
    assert get_resp.status_code == 200
    items = get_resp.json()
    assert any(item["id"] == expense_id for item in items)

    # Clean up test expense
    del_resp = client.delete(f"/api/expenses/{expense_id}")
    assert del_resp.status_code == 204


def test_ai_parse_endpoint(client):
    payload = {"text": "spent 200 on petrol yesterday"}
    resp = client.post("/api/ai/parse", json=payload)
    assert resp.status_code == 200
    parsed = resp.json()
    assert parsed["amount"] == 200.0
    assert parsed["category_name"] == "Transport"
    assert "date" in parsed


def test_dashboard_and_report_endpoints(client):
    current_month = "2026-08"
    dash_resp = client.get(f"/api/dashboard/{current_month}")
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert "total_amount" in dash_data
    assert "category_breakdown" in dash_data

    report_resp = client.get(f"/api/reports/{current_month}")
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert "ai_summary" in report_data
