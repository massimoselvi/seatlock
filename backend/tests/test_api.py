import pytest
from django.utils import timezone

from workshops.models import Workshop


def test_health(client):
    assert client.get("/api/health/").json() == {"status": "ok"}


@pytest.mark.django_db
def test_workshop_list_reports_seats_left(client):
    Workshop.objects.create(title="Async Python", starts_at=timezone.now(), capacity=8)
    data = client.get("/api/workshops/").json()
    assert data["results"][0]["seats_left"] == 8
