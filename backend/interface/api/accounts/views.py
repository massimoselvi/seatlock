"""Accounts use Django's own auth directly.

Sign-up and login are a generic subdomain: Django already solves them, and they hold no seat
rules. Wrapping them in use cases and repositories would add files and no protection.
"""

from rest_framework import generics, permissions, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .authentication import issue_token
from .serializers import SignupSerializer, UserSerializer
from .throttles import LoginUsernameThrottle


class SignupView(generics.CreateAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token = issue_token(user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class LoginView(ObtainAuthToken):
    """DRF's own view switches throttling off, which leaves passwords open to guessing."""

    throttle_classes = [ScopedRateThrottle, LoginUsernameThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        token = issue_token(serializer.validated_data["user"])
        return Response({"token": token.key})
