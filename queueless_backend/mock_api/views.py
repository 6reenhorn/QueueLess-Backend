from django.db.models import Count, ExpressionWrapper, IntegerField, Max, Q, Value
from django.db.models.functions import Coalesce
from rest_framework import viewsets

from queue_tracker.models import QueueEntryStatus

from .models import Institution
from .serializers import InstitutionSerializer


class InstitutionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InstitutionSerializer

    def get_queryset(self):
        return Institution.objects.annotate(
            queue_waiting_count=Count(
                "queue_entries",
                filter=Q(
                    queue_entries__status__in=[
                        QueueEntryStatus.WAITING,
                        QueueEntryStatus.NOTIFIED,
                    ]
                ),
            ),
            current_serving_number=Coalesce(
                Max("queue_entries__current_serving_number"),
                Value(0),
            ),
            next_queue_number=ExpressionWrapper(
                Coalesce(Max("queue_entries__queue_number"), Value(0)) + Value(1),
                output_field=IntegerField(),
            ),
        ).order_by("name")
