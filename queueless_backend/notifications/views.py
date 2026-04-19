from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from queue_tracker.models import QueueEntry
from queue_tracker.query_params import (
    INVALID_BOOLEAN_QUERY_VALUE,
    VALID_BOOLEAN_QUERY_VALUES,
    parse_bool_query_param_strict,
)
from queue_tracker.services import maybe_auto_tick_institution

from .models import Notification
from .serializers import NotificationAcknowledgeSerializer, NotificationSerializer


class QueueEntryNotificationListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, session_id):
        try:
            queue_entry = QueueEntry.objects.get(session_id=session_id)
        except QueueEntry.DoesNotExist:
            return Response(
                {"detail": "Queue entry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        maybe_auto_tick_institution(
            institution_id=queue_entry.institution_id,
            interval_seconds=settings.QUEUE_AUTO_TICK_INTERVAL_SECONDS,
            randomize=settings.QUEUE_AUTO_TICK_RANDOMIZE,
        )

        delivered_filter_raw = request.query_params.get("delivered")
        delivered_filter = parse_bool_query_param_strict(delivered_filter_raw)
        if delivered_filter is INVALID_BOOLEAN_QUERY_VALUE:
            return Response(
                {
                    "detail": "Invalid delivered filter value provided.",
                    "valid_values": list(VALID_BOOLEAN_QUERY_VALUES),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        event_type_filter = request.query_params.get("event_type", "").strip().lower()
        limit_raw = request.query_params.get("limit", "50").strip()
        try:
            limit = max(1, min(int(limit_raw), 100))
        except ValueError:
            return Response(
                {"detail": "Query parameter 'limit' must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = (
            Notification.objects.filter(queue_entry=queue_entry)
            .select_related("queue_entry")
            .order_by("-sent_at", "-id")
        )

        if delivered_filter is not None:
            queryset = queryset.filter(delivered=delivered_filter)

        if event_type_filter:
            valid_event_types = {choice[0] for choice in Notification.EventType.choices}
            if event_type_filter not in valid_event_types:
                return Response(
                    {
                        "detail": "Invalid event_type filter value provided.",
                        "valid_event_types": sorted(valid_event_types),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(event_type=event_type_filter)

        notifications = list(queryset[:limit])
        serializer = NotificationSerializer(notifications, many=True)

        return Response(
            {
                "session_id": str(queue_entry.session_id),
                "institution_id": queue_entry.institution_id,
                "queue_number": queue_entry.queue_number,
                "count": len(notifications),
                "results": serializer.data,
            }
        )


class QueueEntryNotificationAcknowledgeView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, session_id, notification_id):
        try:
            queue_entry = QueueEntry.objects.get(session_id=session_id)
        except QueueEntry.DoesNotExist:
            return Response(
                {"detail": "Queue entry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            notification = Notification.objects.select_related("queue_entry").get(
                id=notification_id,
                queue_entry=queue_entry,
            )
        except Notification.DoesNotExist:
            return Response(
                {"detail": "Notification not found for this queue entry."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = NotificationAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        update_fields = ["delivered", "updated_at"]
        notification.delivered = serializer.validated_data["delivered"]
        if "external_reference" in serializer.validated_data:
            notification.external_reference = serializer.validated_data[
                "external_reference"
            ]
            update_fields.append("external_reference")
        if "error_detail" in serializer.validated_data:
            notification.error_detail = serializer.validated_data["error_detail"]
            update_fields.append("error_detail")
        notification.save(update_fields=update_fields)

        response_serializer = NotificationSerializer(notification)
        return Response(response_serializer.data)
