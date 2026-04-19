from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    session_id = serializers.UUIDField(source="queue_entry.session_id", read_only=True)
    institution_id = serializers.IntegerField(
        source="queue_entry.institution_id",
        read_only=True,
    )
    queue_number = serializers.IntegerField(
        source="queue_entry.queue_number",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "session_id",
            "institution_id",
            "queue_number",
            "channel",
            "event_type",
            "message",
            "delivered",
            "external_reference",
            "error_detail",
            "sent_at",
            "updated_at",
        ]


class NotificationAcknowledgeSerializer(serializers.Serializer):
    delivered = serializers.BooleanField(required=True)
    external_reference = serializers.CharField(
        max_length=120,
        required=False,
        allow_blank=True,
    )
    error_detail = serializers.CharField(required=False, allow_blank=True)
