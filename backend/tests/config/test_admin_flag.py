import importlib

import pytest
from django.urls import clear_url_caches

import config.urls as urls_module


@pytest.fixture
def reload_urls():
    def reload():
        clear_url_caches()
        return importlib.reload(urls_module)

    yield reload
    clear_url_caches()
    importlib.reload(urls_module)


@pytest.mark.django_db
def test_admin_is_mounted_when_enabled(client, settings, reload_urls):
    settings.ADMIN_ENABLED = True
    reload_urls()
    assert client.get("/admin/login/").status_code == 200


@pytest.mark.django_db
def test_admin_is_gone_when_disabled(client, settings, reload_urls):
    settings.ADMIN_ENABLED = False
    reload_urls()
    assert client.get("/admin/login/").status_code == 404
