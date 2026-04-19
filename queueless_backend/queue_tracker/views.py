from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mock_api.models import Institution

from .models import QueueEntry, QueueEntryStatus
from .serializers import (
    InstitutionQueueEntrySerializer,
    QueueEntryStatusSerializer,
    QueueJoinSerializer,
)
from .services import simulate_queue_tick_for_institution


def parse_bool_query_param(value, default: bool = True) -> bool:
    if value is None:
        return default

    normalized_value = str(value).strip().lower()
    truthy_values = {"1", "true", "t", "yes", "y", "on"}
    falsy_values = {"0", "false", "f", "no", "n", "off"}

    if normalized_value in truthy_values:
        return True
    if normalized_value in falsy_values:
        return False
    return default


class QueueJoinView(APIView):
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.AllowAny]

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
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, institution_id):
        try:
            institution = Institution.objects.get(pk=institution_id)
        except Institution.DoesNotExist:
            return Response(
                {"detail": "Institution not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        status_filter = request.query_params.get("status", "").strip()
        active_only = parse_bool_query_param(
            request.query_params.get("active_only"),
            default=True,
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

        entries = list(queryset)
        result_count = len(entries)
        serialized_entries = InstitutionQueueEntrySerializer(entries, many=True)
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
        randomize = parse_bool_query_param(
            request.query_params.get("randomize"),
            default=True,
        )
        try:
            result = simulate_queue_tick_for_institution(
                institution_id=institution_id,
                randomize=randomize,
            )
        except Institution.DoesNotExist:
            return Response(
                {"detail": "Institution not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(result)
