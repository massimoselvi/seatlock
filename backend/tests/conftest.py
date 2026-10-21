import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _celery_eager(settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True


@pytest.fixture(autouse=True)
def _local_memory_cache(settings):
    """Tests and CI run without Redis; clear the cache so throttle counters never leak."""
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
    cache.clear()
    yield
    cache.clear()
