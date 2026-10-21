from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from . import services
from .models import Registration, Workshop
from .serializers import RegistrationSerializer, WorkshopSerializer


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
