import importlib.util

import pytest
from django.core.exceptions import ImproperlyConfigured

import config.settings as settings_module


@pytest.fixture
def load_settings(monkeypatch):
    """Re-evaluate config.settings with a controlled environment, ignoring any local .env."""
    monkeypatch.setattr("environ.Env.read_env", staticmethod(lambda *a, **k: None))

    def load(**env):
        for name in ("DEBUG", "SECRET_KEY", "FORCE_HTTPS"):
            monkeypatch.delenv(name, raising=False)
        for name, value in env.items():
            monkeypatch.setenv(name, value)
        # A fresh module object each time: reload() would keep attributes from earlier loads.
        spec = importlib.util.spec_from_file_location("under_test", settings_module.__file__)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return load


def test_missing_secret_key_stops_startup_when_debug_is_off(load_settings):
    with pytest.raises(ImproperlyConfigured):
        load_settings(DEBUG="false")


def test_default_dev_key_is_rejected_when_debug_is_off(load_settings):
    with pytest.raises(ImproperlyConfigured):
        load_settings(DEBUG="false", SECRET_KEY="dev-insecure-change-me")


def test_debug_keeps_working_without_a_secret_key(load_settings):
    loaded = load_settings(DEBUG="true")
    assert loaded.DEBUG is True


def test_production_cookies_are_secure(load_settings):
    loaded = load_settings(DEBUG="false", SECRET_KEY="x" * 60)
    assert loaded.SESSION_COOKIE_SECURE and loaded.CSRF_COOKIE_SECURE


def test_force_https_enables_redirect_hsts_and_exempts_health(load_settings):
    loaded = load_settings(DEBUG="false", SECRET_KEY="x" * 60, FORCE_HTTPS="true")
    assert loaded.SECURE_SSL_REDIRECT is True
    assert loaded.SECURE_HSTS_SECONDS >= 31536000
    assert loaded.SECURE_PROXY_SSL_HEADER == ("HTTP_X_FORWARDED_PROTO", "https")
    assert r"^api/health/$" in loaded.SECURE_REDIRECT_EXEMPT


def test_https_is_off_by_default(load_settings):
    loaded = load_settings(DEBUG="false", SECRET_KEY="x" * 60)
    assert not getattr(loaded, "SECURE_SSL_REDIRECT", False)
