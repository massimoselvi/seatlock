from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework import generics, mixins, permissions, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Registration, Workshop
from .serializers import (
    OrganizerRegistrationSerializer,
    OrganizerWorkshopSerializer,
    RegistrationSerializer,
    SignupSerializer,
    UserSerializer,
    WorkshopSerializer,
)


def health(request):
    return JsonResponse({"status": "ok"})


class WorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkshopSerializer
    queryset = Workshop.objects.annotate(
        seats_taken=Count(
            "registrations",
            filter=Q(registrations__status=Registration.Status.CONFIRMED),
        )
    ).order_by("starts_at", "id")

    @action(detail=True, methods=["post"], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, pk=None):
        try:
            registration = services.register(user=request.user, workshop_id=int(pk))
        except Workshop.DoesNotExist:
            raise NotFound("Workshop not found.") from None
        return Response(RegistrationSerializer(registration).data, status=status.HTTP_200_OK)


class OrganizerWorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff-only view: seats taken, waitlist size and who is registered."""

    serializer_class = OrganizerWorkshopSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = Workshop.objects.annotate(
        seats_taken=Count(
            "registrations", filter=Q(registrations__status=Registration.Status.CONFIRMED)
        ),
        waitlist_size=Count(
            "registrations", filter=Q(registrations__status=Registration.Status.WAITLISTED)
        ),
    ).order_by("starts_at", "id")

    @action(detail=True, methods=["get"])
    def registrations(self, request, pk=None):
        workshop = self.get_object()
        rows = workshop.registrations.select_related("user").order_by("created_at", "id")
        return Response(OrganizerRegistrationSerializer(rows, many=True).data)


class RegistrationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user).select_related("workshop")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        try:
            registration = services.cancel(user=request.user, registration_id=int(pk))
        except Registration.DoesNotExist:
            raise NotFound("Registration not found.") from None
        return Response(RegistrationSerializer(registration).data)


class SignupView(generics.CreateAPIView):
    serializer_class = SignupSerializer
    permission_classes = [permissions.AllowAny]
    authentication_classes: list = []

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
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
        Token.objects.filter(user=request.user).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
