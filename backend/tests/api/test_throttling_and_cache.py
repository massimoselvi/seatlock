import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from domain.workshops.exceptions import WorkshopNotFound
from infrastructure import container
from infrastructure.db.models import Workshop

User = get_user_model()
pytestmark = pytest.mark.django_db


@pytest.fixture
def workshop():
    return Workshop.objects.create(
        title="Async Python", starts_at=timezone.now() + timezone.timedelta(days=1), capacity=5
    )


@pytest.fixture
def user():
    return User.objects.create_user("ada", "ada@example.com", "pw")


def test_registration_endpoint_is_rate_limited(workshop, user):
    client = APIClient()
    client.force_authenticate(user)
    url = f"/api/workshops/{workshop.pk}/register/"

    statuses = [client.post(url).status_code for _ in range(11)]

    assert statuses[:10] == [200] * 10
    assert statuses[10] == 429


def test_workshop_list_is_cached_until_seats_change(
    workshop, user, django_capture_on_commit_callbacks
):
    client = APIClient()
    first = client.get("/api/workshops/").json()
    assert first["results"][0]["seats_left"] == 5

    # A direct write does not invalidate the cache: the old page is still served.
    Workshop.objects.create(
        title="Another", starts_at=timezone.now() + timezone.timedelta(days=1), capacity=1
    )
    assert client.get("/api/workshops/").json()["count"] == 1

    # A seat change invalidates it after commit.
    with django_capture_on_commit_callbacks(execute=True):
        container.register_for_workshop().execute(user_id=user.pk, workshop_id=workshop.pk)
    fresh = client.get("/api/workshops/").json()
    assert fresh["count"] == 2
    assert fresh["results"][0]["seats_left"] == 4


def test_cache_is_not_invalidated_on_rollback(workshop, user):
    client = APIClient()
    client.get("/api/workshops/")
    with pytest.raises(WorkshopNotFound):
        container.register_for_workshop().execute(user_id=user.pk, workshop_id=9999)
    Workshop.objects.create(
        title="Another", starts_at=timezone.now() + timezone.timedelta(days=1), capacity=1
    )
    assert client.get("/api/workshops/").json()["count"] == 1


def test_unknown_query_parameters_share_one_cache_entry(workshop, django_assert_num_queries):
    client = APIClient()
    client.get("/api/workshops/?x=1")

    with django_assert_num_queries(0):
        client.get("/api/workshops/?x=2&y=three")
        client.get("/api/workshops/")
        client.get("/api/workshops/?page=1")


def test_invalid_page_is_not_cached_and_answers_normally(workshop):
    client = APIClient()
    assert client.get("/api/workshops/?page=abc").status_code == 404
    assert client.get("/api/workshops/?page=999999").status_code == 404
    assert client.get("/api/workshops/?page=-1").status_code == 404


def post_login(client, username="nobody", **extra):
    return client.post(
        "/api/auth/login/",
        {"username": username, "password": "wrong"},
        content_type="application/json",
        **extra,
    )


def test_login_is_rate_limited(client):
    statuses = [post_login(client).status_code for _ in range(11)]

    assert statuses[:10] == [400] * 10
    assert statuses[10] == 429


def test_spoofed_forwarded_for_prefix_does_not_reset_the_limit(client, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 2}

    statuses = [
        # The attacker invents the first address. The last two come from CloudFront and the ALB.
        post_login(client, HTTP_X_FORWARDED_FOR=f"6.6.6.{i}, 203.0.113.7, 10.0.0.1").status_code
        for i in range(11)
    ]

    assert statuses[10] == 429


def test_different_real_clients_have_separate_limits(client, settings):
    settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 2}
    for _ in range(10):
        post_login(client, HTTP_X_FORWARDED_FOR="203.0.113.7, 10.0.0.1")

    # A different username too: the per-username limit is separate from the per-address one.
    other = post_login(client, "someone-else", HTTP_X_FORWARDED_FOR="198.51.100.9, 10.0.0.1")

    assert other.status_code == 400
