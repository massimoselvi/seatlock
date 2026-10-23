"""Token auth with a lifetime. DRF's own tokens never expire."""

from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import AuthenticationFailed


def is_expired(token: Token) -> bool:
    return token.created + timedelta(hours=settings.AUTH_TOKEN_TTL_HOURS) <= timezone.now()


def issue_token(user) -> Token:
    """Reuse the user's live token (so other devices stay signed in), replace an expired one."""
    token, created = Token.objects.get_or_create(user=user)
    if not created and is_expired(token):
        token.delete()
        token = Token.objects.create(user=user)
    return token


class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if is_expired(token):
            token.delete()
            raise AuthenticationFailed("Token expired. Sign in again.")
        return user, token
