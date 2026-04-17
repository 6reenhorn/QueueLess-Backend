from django.db.models import Max
from rest_framework import serializers

from .models import Institution


class InstitutionSerializer(serializers.ModelSerializer):
    queue_waiting_count = serializers.SerializerMethodField()
    current_serving_number = serializers.SerializerMethodField()
    next_queue_number = serializers.SerializerMethodField()

    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "institution_type",
            "address",
            "api_endpoint",
            "status",
            "is_active",
            "is_available_for_queue",
            "queue_waiting_count",
            "current_serving_number",
            "next_queue_number",
        ]

    def get_queue_waiting_count(self, obj: Institution) -> int:
        return obj.queue_entries.filter(status__in=["waiting", "notified"]).count()

    def get_current_serving_number(self, obj: Institution) -> int:
        value = obj.queue_entries.aggregate(value=Max("current_serving_number"))[
            "value"
        ]
        return value or 0

    def get_next_queue_number(self, obj: Institution) -> int:
        value = obj.queue_entries.aggregate(value=Max("queue_number"))["value"]
        return (value or 0) + 1
