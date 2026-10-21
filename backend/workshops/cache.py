"""Cache of the public workshops list.

Entries carry a version number. Bumping the version invalidates every page at once,
without needing to know which keys exist.
"""

from django.core.cache import cache
from django.db import transaction

VERSION_KEY = "workshops:list:version"


def list_key(query_string: str) -> str:
    return f"workshops:list:v{cache.get(VERSION_KEY, 1)}:{query_string}"


def invalidate_workshop_list() -> None:
    """Drop cached lists once the surrounding transaction commits."""

    def bump() -> None:
        try:
            cache.incr(VERSION_KEY)
        except ValueError:
            cache.set(VERSION_KEY, 2, timeout=None)

    transaction.on_commit(bump)
