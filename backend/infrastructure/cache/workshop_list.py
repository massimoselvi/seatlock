"""Cache of the public workshops list.

Entries carry a version number. Bumping the version invalidates every page at once,
without needing to know which keys exist.
"""

from django.core.cache import cache

from application.workshops.interfaces import WorkshopListCache

VERSION_KEY = "workshops:list:version"


def list_key(page: int) -> str:
    return f"workshops:list:v{cache.get(VERSION_KEY, 1)}:page{page}"


class DjangoWorkshopListCache(WorkshopListCache):
    def invalidate(self) -> None:
        # Called through UnitOfWork.on_commit, so it only runs for committed changes.
        try:
            cache.incr(VERSION_KEY)
        except ValueError:
            cache.set(VERSION_KEY, 2, timeout=None)
