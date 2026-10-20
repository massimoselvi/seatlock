from django.db.models import Count, Q
from django.http import JsonResponse
from rest_framework import viewsets

from .models import Registration, Workshop
from .serializers import WorkshopSerializer


def health(request):
    return JsonResponse({"status": "ok"})


class WorkshopViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = WorkshopSerializer
    queryset = Workshop.objects.annotate(
        seats_taken=Count(
            "registrations",
            filter=Q(registrations__status=Registration.Status.CONFIRMED),
        )
    )
