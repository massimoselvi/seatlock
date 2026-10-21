import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from workshops import services
from workshops.models import Workshop

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def workshop():
    return Workshop.objects.create(title="Async Python", starts_at=timezone.now(), capacity=1)


def client_for(username: str, *, staff: bool = False) -> APIClient:
    user = User.objects.create_user(username, f"{username}@example.com", "pw", is_staff=staff)
    client = APIClient()
    client.force_authenticate(user)
    return client


def register_users(workshop, *names):
    for name in names:
        user = User.objects.create_user(name, f"{name}@example.com", "pw")
        services.register(user=user, workshop_id=workshop.pk)


def test_dashboard_is_staff_only(workshop):
    assert APIClient().get("/api/organizer/workshops/").status_code in (401, 403)
    assert client_for("ada").get("/api/organizer/workshops/").status_code == 403


def test_dashboard_reports_seats_and_waitlist(workshop):
    register_users(workshop, "ada", "bob", "cy")

    row = client_for("boss", staff=True).get("/api/organizer/workshops/").json()["results"][0]

    assert (row["seats_taken"], row["seats_left"], row["waitlist_size"]) == (1, 0, 2)


def test_registrations_list_shows_who_and_status(workshop):
    register_users(workshop, "ada", "bob")

    url = f"/api/organizer/workshops/{workshop.pk}/registrations/"
    rows = client_for("boss", staff=True).get(url).json()

    who = [(r["username"], r["status"]) for r in rows]
    assert who == [("ada", "confirmed"), ("bob", "waitlisted")]
    assert rows[0]["email"] == "ada@example.com"


def test_registrations_list_is_staff_only(workshop):
    response = client_for("ada").get(f"/api/organizer/workshops/{workshop.pk}/registrations/")
    assert response.status_code == 403
