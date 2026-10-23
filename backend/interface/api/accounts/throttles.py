import hashlib

from rest_framework.throttling import SimpleRateThrottle


class LoginUsernameThrottle(SimpleRateThrottle):
    """Limits sign-in attempts per username, whatever the client address.

    The per-address throttle does not slow a guesser who rotates addresses.
    """

    scope = "login_user"

    def get_cache_key(self, request, view):
        data = request.data
        username = data.get("username") if hasattr(data, "get") else None
        if not isinstance(username, str) or not username.strip():
            return None
        ident = hashlib.sha256(username.strip().lower().encode()).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": ident}
