import pytest
from django.contrib.auth import get_user_model

User = get_user_model()
PASSWORD = "correct-horse-battery"

pytestmark = pytest.mark.django_db


def signup(client, **overrides):
    payload = {"username": "ada", "email": "ada@example.com", "password": PASSWORD} | overrides
    return client.post("/api/auth/signup/", payload, content_type="application/json")


def test_signup_returns_token_and_user(client):
    response = signup(client)
    assert response.status_code == 201
    body = response.json()
    assert body["token"]
    assert body["user"]["username"] == "ada"
    assert "password" not in body["user"]


def test_signup_rejects_duplicate_email(client):
    signup(client)
    response = signup(client, username="ada2", email="ADA@example.com")
    assert response.status_code == 400
    assert "email" in response.json()


def test_signup_rejects_weak_password(client):
    response = signup(client, password="123")
    assert response.status_code == 400


def test_login_with_valid_credentials(client):
    signup(client)
    response = client.post(
        "/api/auth/login/",
        {"username": "ada", "password": PASSWORD},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["token"]


def test_login_with_wrong_password(client):
    signup(client)
    response = client.post(
        "/api/auth/login/",
        {"username": "ada", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_me_requires_token(client):
    assert client.get("/api/auth/me/").status_code == 401


def test_me_and_logout(client):
    token = signup(client).json()["token"]
    auth = {"HTTP_AUTHORIZATION": f"Token {token}"}

    assert client.get("/api/auth/me/", **auth).json()["username"] == "ada"
    assert client.post("/api/auth/logout/", **auth).status_code == 204
    assert client.get("/api/auth/me/", **auth).status_code == 401


def test_workshops_list_stays_public(client):
    assert client.get("/api/workshops/").status_code == 200
