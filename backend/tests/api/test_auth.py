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

    me = client.get("/api/auth/me/", **auth).json()
    assert me["username"] == "ada"
    assert me["is_staff"] is False
    assert client.post("/api/auth/logout/", **auth).status_code == 204
    assert client.get("/api/auth/me/", **auth).status_code == 401


def test_workshops_list_stays_public(client):
    assert client.get("/api/workshops/").status_code == 200


def _age_token(hours):
    from datetime import timedelta

    from django.utils import timezone
    from rest_framework.authtoken.models import Token

    Token.objects.update(created=timezone.now() - timedelta(hours=hours))


def _login(client, remote_addr="127.0.0.1", **overrides):
    payload = {"username": "ada", "password": PASSWORD} | overrides
    return client.post(
        "/api/auth/login/", payload, content_type="application/json", REMOTE_ADDR=remote_addr
    )


def test_expired_token_is_rejected_and_removed(client, settings):
    from rest_framework.authtoken.models import Token

    settings.AUTH_TOKEN_TTL_HOURS = 24
    token = signup(client).json()["token"]
    _age_token(hours=25)
    response = client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Token {token}")
    assert response.status_code == 401
    assert not Token.objects.filter(key=token).exists()


def test_login_reuses_a_live_token_and_replaces_an_expired_one(client, settings):
    settings.AUTH_TOKEN_TTL_HOURS = 24
    first = signup(client).json()["token"]
    assert _login(client).json()["token"] == first
    _age_token(hours=25)
    fresh = _login(client).json()["token"]
    assert fresh != first
    assert client.get("/api/auth/me/", HTTP_AUTHORIZATION=f"Token {fresh}").status_code == 200


def test_login_is_throttled_per_username_across_addresses(client):
    codes = [
        _login(client, f"10.0.0.{n}", username="victim", password="wrong").status_code
        for n in range(12)
    ]
    assert codes[:10] == [400] * 10
    assert 429 in codes[10:]
