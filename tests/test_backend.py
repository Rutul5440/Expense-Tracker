import pytest
from fastapi.testclient import TestClient
from backend.main import app, seed_default_categories
from backend.database import Base, engine


@pytest.fixture(scope="module")
def client():
    # Reset and recreate clean database tables for testing
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_default_categories()
    with TestClient(app) as c:
        yield c



def test_auth_registration_and_login(client):
    # Register user 1
    reg_payload = {
        "email": "user1@example.com",
        "username": "User One",
        "password": "password123"
    }
    reg_resp = client.post("/api/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == "user1@example.com"
    token1 = reg_data["access_token"]

    # Profile check with Bearer header
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token1}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "User One"

    # Login user 1
    login_resp = client.post("/api/auth/login", json={"email": "user1@example.com", "password": "password123"})
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()


def test_user_data_isolation(client):
    # Register User A
    user_a_token = client.post("/api/auth/register", json={
        "email": "usera@example.com", "username": "User A", "password": "passa123"
    }).json()["access_token"]

    # Register User B
    user_b_token = client.post("/api/auth/register", json={
        "email": "userb@example.com", "username": "User B", "password": "passb123"
    }).json()["access_token"]

    headers_a = {"Authorization": f"Bearer {user_a_token}"}
    headers_b = {"Authorization": f"Bearer {user_b_token}"}

    # Fetch categories
    categories = client.get("/api/categories", headers=headers_a).json()
    food_cat = next((c for c in categories if c["name"] == "Food & Dining"), categories[0])

    # User A creates expense
    exp_a = client.post("/api/expenses", headers=headers_a, json={
        "amount": 500.0, "category_id": food_cat["id"], "description": "User A Swiggy", "date": "2026-08-08"
    }).json()

    # User B lists expenses -> should NOT see User A's expense
    b_expenses = client.get("/api/expenses", headers=headers_b).json()
    assert not any(e["id"] == exp_a["id"] for e in b_expenses)

    # User A lists expenses -> should see expense
    a_expenses = client.get("/api/expenses", headers=headers_a).json()
    assert any(e["id"] == exp_a["id"] for e in a_expenses)


def test_categories_endpoint(client):
    response = client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 12
    names = [c["name"] for c in data]
    assert "Food & Dining" in names
    assert "Transport" in names


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


def test_friends_and_split_expenses(client):
    # Register test user
    user_token = client.post("/api/auth/register", json={
        "email": "splituser@example.com", "username": "Split User", "password": "pass123"
    }).json()["access_token"]

    headers = {"Authorization": f"Bearer {user_token}"}

    # 1. Add Friend 1 and Friend 2
    f1 = client.post("/api/friends", headers=headers, json={"name": "Friend 1"}).json()
    f2 = client.post("/api/friends", headers=headers, json={"name": "Friend 2"}).json()
    assert f1["name"] == "Friend 1"
    assert f2["name"] == "Friend 2"

    # 2. Friend 1 pays for Soda (₹20 total split between Friend 1 and Friend 2)
    # Friend 1 pays, User & Friend 2 participants (10 each) or Friend 1 pays for User & Friend 2
    split1 = client.post("/api/splits", headers=headers, json={
        "title": "Soda",
        "total_amount": 20.0,
        "transaction_type": "EXPENSE",
        "paid_by_user": False,
        "paid_by_friend_id": f1["id"],
        "date": "2026-08-22",
        "participants": [
            {"is_user": True},
            {"friend_id": f2["id"]}
        ]
    })
    assert split1.status_code == 201

    # Check friend balances: User owes Friend 1 ₹10. Net(Friend 1) = -10.0
    friends = client.get("/api/friends", headers=headers).json()
    friend1_data = next(f for f in friends if f["id"] == f1["id"])
    assert friend1_data["net_balance"] == -10.0

    # 3. User pays for Ice Cream (₹50 total split between User and Friend 1)
    split2 = client.post("/api/splits", headers=headers, json={
        "title": "Ice Cream",
        "total_amount": 50.0,
        "transaction_type": "EXPENSE",
        "paid_by_user": True,
        "date": "2026-08-22",
        "participants": [
            {"is_user": True},
            {"friend_id": f1["id"]}
        ]
    })
    assert split2.status_code == 201

    # Check friend balances: Friend 1 owed User ₹25 for Ice Cream.
    # Previously User owed Friend 1 ₹10 for Soda.
    # Net balance for Friend 1 = +25 - 10 = +15.0 (Friend 1 owes User ₹15.0)
    friends = client.get("/api/friends", headers=headers).json()
    friend1_data = next(f for f in friends if f["id"] == f1["id"])
    assert friend1_data["net_balance"] == 15.0

    # 4. Settle Up ₹15 with Friend 1
    settle_resp = client.post("/api/splits/settle", headers=headers, json={
        "friend_id": f1["id"],
        "amount": 15.0,
        "notes": "Paid via UPI"
    })
    assert settle_resp.status_code == 201

    # Check net balance after settlement -> should be 0.0
    friends_after = client.get("/api/friends", headers=headers).json()
    friend1_after = next(f for f in friends_after if f["id"] == f1["id"])
    assert friend1_after["net_balance"] == 0.0

