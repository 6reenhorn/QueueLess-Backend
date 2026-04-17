from rest_framework import viewsets

from .models import Institution
from .serializers import InstitutionSerializer


class InstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.all().order_by("name")
