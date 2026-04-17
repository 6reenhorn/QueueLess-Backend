import random

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mock_api.models import Institution
from notifications.models import Notification

from .models import QueueEntry, QueueEntryStatus
from .serializers import (
    InstitutionQueueEntrySerializer,
    QueueEntryStatusSerializer,
    QueueJoinSerializer,
)


class QueueJoinView(APIView):
    def post(self, request):
        serializer = QueueJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        institution_id = serializer.validated_data["institution_id"]
        phone_number = serializer.validated_data.get("phone_number", "")
        browser_push_opt_in = serializer.validated_data.get(
            "browser_push_opt_in", False
        )
        near_turn_threshold = serializer.validated_data.get("near_turn_threshold", 3)

        retries = 3
        entry = None
        for attempt in range(retries):
            try:
                with transaction.atomic():
                    try:
                        institution = Institution.objects.select_for_update().get(
                            pk=institution_id
                        )
                    except Institution.DoesNotExist:
                        return Response(
                            {"detail": "Institution not found."},
                            status=status.HTTP_404_NOT_FOUND,
                        )

                    if not institution.is_available_for_queue:
                        return Response(
                            {
                                "detail": (
                                    "Institution is not currently available "
                                    "for queueing."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    latest_entry = (
                        QueueEntry.objects.select_for_update()
                        .filter(institution=institution)
                        .order_by("-queue_number")
                        .first()
                    )
                    queue_number = (
                        latest_entry.queue_number if latest_entry else 0
                    ) + 1
                    current_serving_number = (
                        QueueEntry.objects.filter(institution=institution).aggregate(
                            value=Max("current_serving_number")
                        )["value"]
                        or 0
                    )

                    entry = QueueEntry.objects.create(
                        institution=institution,
                        queue_number=queue_number,
                        current_serving_number=current_serving_number,
                        phone_number=phone_number,
                        browser_push_opt_in=browser_push_opt_in,
                        near_turn_threshold=near_turn_threshold,
                        status=QueueEntryStatus.WAITING,
                    )
                break
            except IntegrityError:
                if attempt == retries - 1:
                    return Response(
                        {
                            "detail": (
                                "Could not allocate a queue number due to "
                                "concurrent requests. Please retry."
                            )
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

        response_serializer = QueueEntryStatusSerializer(entry)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class QueueEntryStatusView(APIView):
    def get(self, request, session_id):
        try:
            entry = QueueEntry.objects.get(session_id=session_id)
        except QueueEntry.DoesNotExist:
            return Response(
                {"detail": "Queue entry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = QueueEntryStatusSerializer(entry)
        return Response(serializer.data)


class InstitutionQueueStatusView(APIView):
    def get(self, request, institution_id):
        try:
            institution = Institution.objects.get(pk=institution_id)
        except Institution.DoesNotExist:
            return Response(
                {"detail": "Institution not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        status_filter = request.query_params.get("status", "").strip()
        active_only = (
            str(request.query_params.get("active_only", "true")).lower() != "false"
        )

        queryset = QueueEntry.objects.filter(institution=institution).order_by(
            "queue_number"
        )

        if status_filter:
            requested_statuses = [
                value.strip().lower()
                for value in status_filter.split(",")
                if value.strip()
            ]
            valid_statuses = {choice[0] for choice in QueueEntryStatus.choices}
            invalid_statuses = [
                value for value in requested_statuses if value not in valid_statuses
            ]
            if invalid_statuses:
                return Response(
                    {
                        "detail": "Invalid status filter values provided.",
                        "invalid_statuses": invalid_statuses,
                        "valid_statuses": sorted(valid_statuses),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(status__in=requested_statuses)
        elif active_only:
            queryset = queryset.filter(
                status__in=[QueueEntryStatus.WAITING, QueueEntryStatus.NOTIFIED]
            )

        result_count = queryset.count()
        serialized_entries = InstitutionQueueEntrySerializer(queryset, many=True)
        return Response(
            {
                "institution": {
                    "id": institution.id,
                    "name": institution.name,
                    "institution_type": institution.institution_type,
                    "status": institution.status,
                    "is_active": institution.is_active,
                    "is_available_for_queue": institution.is_available_for_queue,
                },
                "filters": {
                    "status": status_filter or None,
                    "active_only": active_only,
                },
                "count": result_count,
                "results": serialized_entries.data,
            }
        )


class QueueSimulateTickView(APIView):
    """
    Simulates queue movement with random increments to mimic real operations.
    """

    permission_classes = [permissions.IsAdminUser]

    def post(self, request, institution_id):
        randomize = (
            str(request.query_params.get("randomize", "true")).lower() != "false"
        )

        with transaction.atomic():
            try:
                institution = Institution.objects.select_for_update().get(
                    pk=institution_id
                )
            except Institution.DoesNotExist:
                return Response(
                    {"detail": "Institution not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            active_entries = list(
                QueueEntry.objects.select_for_update()
                .filter(
                    institution=institution,
                    status__in=[QueueEntryStatus.WAITING, QueueEntryStatus.NOTIFIED],
                )
                .order_by("queue_number")
            )

            if not active_entries:
                return Response(
                    {
                        "institution_id": institution.id,
                        "message": "No active queue entries to simulate.",
                    }
                )

            current_serving = max(
                entry.current_serving_number for entry in active_entries
            )
            highest_queue_number = max(entry.queue_number for entry in active_entries)
            increment = random.choice([0, 1, 1, 1, 2]) if randomize else 1
            capped_current_serving = min(
                current_serving + increment,
                highest_queue_number,
            )
            new_current_serving = max(current_serving, capped_current_serving)

            QueueEntry.objects.filter(
                institution=institution,
                status__in=[QueueEntryStatus.WAITING, QueueEntryStatus.NOTIFIED],
            ).update(current_serving_number=new_current_serving)

            now = timezone.now()
            served_entries = list(
                QueueEntry.objects.filter(
                    institution=institution,
                    status__in=[QueueEntryStatus.WAITING, QueueEntryStatus.NOTIFIED],
                    queue_number__lte=new_current_serving,
                )
            )

            for entry in served_entries:
                entry.status = QueueEntryStatus.SERVED
                entry.served_at = now
                entry.save(update_fields=["status", "served_at", "updated_at"])
                Notification.objects.create(
                    queue_entry=entry,
                    channel=Notification.Channel.SYSTEM,
                    event_type=Notification.EventType.TURN_CALLED,
                    message=f"Queue #{entry.queue_number} is now being served.",
                    delivered=True,
                )

            near_turn_entries = list(
                QueueEntry.objects.filter(
                    institution=institution,
                    status=QueueEntryStatus.WAITING,
                    near_turn_notified=False,
                    queue_number__gt=new_current_serving,
                )
            )

            notified_count = 0
            for entry in near_turn_entries:
                people_ahead = max(entry.queue_number - new_current_serving - 1, 0)
                if people_ahead <= entry.near_turn_threshold:
                    entry.status = QueueEntryStatus.NOTIFIED
                    entry.near_turn_notified = True
                    entry.save(
                        update_fields=["status", "near_turn_notified", "updated_at"]
                    )
                    notified_count += 1
                    Notification.objects.create(
                        queue_entry=entry,
                        channel=Notification.Channel.SYSTEM,
                        event_type=Notification.EventType.NEAR_TURN,
                        message=(
                            f"Queue #{entry.queue_number}: please prepare, "
                            f"{people_ahead} ahead of you."
                        ),
                        delivered=True,
                    )

        return Response(
            {
                "institution_id": institution.id,
                "randomized": randomize,
                "increment": increment,
                "current_serving_number": new_current_serving,
                "served_count": len(served_entries),
                "notified_count": notified_count,
            }
        )
