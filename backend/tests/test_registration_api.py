import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from workshops.models import Registration, Workshop

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def workshop():
    return Workshop.objects.create(title="Async Python", starts_at=timezone.now(), capacity=1)


def client_for(username: str) -> APIClient:
    user = User.objects.create_user(username, f"{username}@example.com", "pw")
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_register_requires_login(workshop):
    response = APIClient().post(f"/api/workshops/{workshop.pk}/register/")
    assert response.status_code in (401, 403)


def test_register_confirms_then_waitlists(workshop):
    first = client_for("ada").post(f"/api/workshops/{workshop.pk}/register/")
    second = client_for("bob").post(f"/api/workshops/{workshop.pk}/register/")
    assert first.json()["status"] == "confirmed"
    assert second.json()["status"] == "waitlisted"


def test_register_is_idempotent(workshop):
    client = client_for("ada")
    one = client.post(f"/api/workshops/{workshop.pk}/register/").json()
    two = client.post(f"/api/workshops/{workshop.pk}/register/").json()
    assert one["id"] == two["id"]
    assert Registration.objects.count() == 1


def test_register_unknown_workshop_is_404():
    assert client_for("ada").post("/api/workshops/999/register/").status_code == 404


def test_cancel_promotes_first_waiting_user(workshop, django_capture_on_commit_callbacks):
    ada, bob = client_for("ada"), client_for("bob")
    confirmed = ada.post(f"/api/workshops/{workshop.pk}/register/").json()
    waiting = bob.post(f"/api/workshops/{workshop.pk}/register/").json()

    with django_capture_on_commit_callbacks(execute=True):
        response = ada.post(f"/api/registrations/{confirmed['id']}/cancel/")

    assert response.json()["status"] == "cancelled"
    assert Registration.objects.get(pk=waiting["id"]).status == "confirmed"


def test_cannot_cancel_someone_elses_registration(workshop):
    confirmed = client_for("ada").post(f"/api/workshops/{workshop.pk}/register/").json()
    response = client_for("bob").post(f"/api/registrations/{confirmed['id']}/cancel/")
    assert response.status_code == 404
    assert Registration.objects.get(pk=confirmed["id"]).status == "confirmed"


def test_list_returns_only_my_registrations(workshop):
    ada, bob = client_for("ada"), client_for("bob")
    ada.post(f"/api/workshops/{workshop.pk}/register/")
    bob.post(f"/api/workshops/{workshop.pk}/register/")
    results = ada.get("/api/registrations/").json()["results"]
    assert [r["status"] for r in results] == ["confirmed"]
