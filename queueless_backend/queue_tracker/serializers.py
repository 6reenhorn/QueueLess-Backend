from django.db.models import Max
from rest_framework import serializers

from mock_api.models import Institution

from .models import QueueEntry


class QueueJoinSerializer(serializers.Serializer):
    institution_id = serializers.IntegerField()
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    browser_push_opt_in = serializers.BooleanField(default=False)
    near_turn_threshold = serializers.IntegerField(min_value=1, max_value=10, default=3)

    def validate_institution_id(self, value: int) -> int:
        try:
            institution = Institution.objects.get(pk=value)
        except Institution.DoesNotExist as exc:
            raise serializers.ValidationError("Institution not found.") from exc

        if not institution.is_available_for_queue:
            raise serializers.ValidationError(
                "Institution is not currently available for queueing."
            )

        return value


class QueueEntryStatusSerializer(serializers.ModelSerializer):
    people_ahead = serializers.IntegerField(read_only=True)

    class Meta:
        model = QueueEntry
        fields = [
            "session_id",
            "institution_id",
            "queue_number",
            "current_serving_number",
            "status",
            "near_turn_threshold",
            "near_turn_notified",
            "issued_at",
            "updated_at",
            "people_ahead",
        ]


class InstitutionQueueEntrySerializer(serializers.ModelSerializer):
    people_ahead = serializers.IntegerField(read_only=True)

    class Meta:
        model = QueueEntry
        fields = [
            "session_id",
            "queue_number",
            "current_serving_number",
            "status",
            "near_turn_notified",
            "near_turn_threshold",
            "people_ahead",
            "issued_at",
            "updated_at",
            "served_at",
            "expires_at",
        ]


def get_next_queue_number_for_institution(institution: Institution) -> int:
    latest = QueueEntry.objects.filter(institution=institution).aggregate(
        value=Max("queue_number")
    )["value"]
    return (latest or 0) + 1
