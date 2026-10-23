"""The sweep repairs the one gap that ADR 0002 accepts: a promotion lost after the commit."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from config.celery import app
from infrastructure import container
from infrastructure.db.models import Registration, Workshop

User = get_user_model()
pytestmark = pytest.mark.django_db

TASK = "workshops.tasks.sweep_waitlists"


def client_for(username: str) -> APIClient:
    user = User.objects.create_user(username, f"{username}@example.com", "pw")
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_sweep_promotes_after_a_lost_enqueue(django_capture_on_commit_callbacks):
    workshop = Workshop.objects.create(
        title="Async Python", starts_at=timezone.now() + timezone.timedelta(days=1), capacity=1
    )
    ada, bob = client_for("ada"), client_for("bob")
    confirmed = ada.post(f"/api/workshops/{workshop.pk}/register/").json()
    waiting = bob.post(f"/api/workshops/{workshop.pk}/register/").json()

    # The crash window: the cancel commits, the process dies before on_commit runs the enqueue.
    with django_capture_on_commit_callbacks(execute=False):
        ada.post(f"/api/registrations/{confirmed['id']}/cancel/")
    assert Registration.objects.get(pk=waiting["id"]).status == "waitlisted"

    assert container.sweep_waitlists().execute() == 1

    assert Registration.objects.get(pk=waiting["id"]).status == "confirmed"
    assert container.sweep_waitlists().execute() == 0


def test_sweep_is_scheduled_and_registered():
    from django.conf import settings

    entry = settings.CELERY_BEAT_SCHEDULE["sweep-waitlists"]
    assert entry["task"] == TASK
    assert entry["schedule"] > 0
    app.loader.import_default_modules()
    assert TASK in app.tasks
