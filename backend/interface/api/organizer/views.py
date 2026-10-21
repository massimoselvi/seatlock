from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from infrastructure.db import queries

from .serializers import OrganizerRegistrationSerializer, OrganizerWorkshopSerializer


class OrganizerWorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    """Staff-only view: seats taken, waitlist size and who is registered."""

    serializer_class = OrganizerWorkshopSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = queries.organizer_workshops()

    @action(detail=True, methods=["get"])
    def registrations(self, request, pk=None):
        workshop = self.get_object()
        rows = workshop.registrations.select_related("user").order_by("created_at", "id")
        return Response(OrganizerRegistrationSerializer(rows, many=True).data)
