from rest_framework import serializers

from .models import QueueEntry


class QueueJoinSerializer(serializers.Serializer):
    institution_id = serializers.IntegerField(min_value=1)
    phone_number = serializers.CharField(
        max_length=20, required=False, allow_blank=True
    )
    browser_push_opt_in = serializers.BooleanField(default=False)
    near_turn_threshold = serializers.IntegerField(
        min_value=1,
        max_value=10,
        default=3,
    )


class QueueEntryStatusSerializer(serializers.ModelSerializer):
    institution_id = serializers.IntegerField(read_only=True)
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
