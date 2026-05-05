from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Max
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from mock_api.models import Institution

from .models import ACTIVE_QUEUE_STATUSES, QueueEntry, QueueEntryStatus
from .query_params import parse_bool_query_param
from .serializers import (
    InstitutionQueueEntrySerializer,
    QueueEntryStatusSerializer,
    QueueJoinSerializer,
)
from .services import (
    auto_tick_active_institutions,
    cancel_queue_entry,
    check_in_serving_entry,
    expire_stale_serving_entries,
    maybe_auto_tick_institution,
    simulate_queue_tick_for_institution,
)
from .throttles import BurstRateThrottle, JoinQueueRateThrottle


class QueueJoinView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [JoinQueueRateThrottle]

    def post(self, request):
        serializer = QueueJoinSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        institution_id = serializer.validated_data["institution_id"]
        queue_number = serializer.validated_data["queue_number"]
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

                    # Get the most recent serving number for this institution
                    # (Usually tracked on the latest served entries)
                    current_serving_number = (
                        QueueEntry.objects.filter(institution=institution).aggregate(
                            value=Max("current_serving_number")
                        )["value"]
                        or 0
                    )

                    # Validation: Can't track a number that is already served
                    if queue_number <= current_serving_number:
                        return Response(
                            {
                                "detail": (
                                    f"Ticket #{queue_number} has already been served. "
                                    f"Current serving number is "
                                    f"#{current_serving_number}."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    # Check for duplicate active tracking
                    # (handled by DB constraint, but we can be explicit)
                    if QueueEntry.objects.filter(
                        institution=institution,
                        queue_number=queue_number,
                        status__in=ACTIVE_QUEUE_STATUSES,
                    ).exists():
                        return Response(
                            {
                                "detail": (
                                    f"Ticket #{queue_number} is already "
                                    "being tracked by another user."
                                )
                            },
                            status=status.HTTP_400_BAD_REQUEST,
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
                # If on last attempt, return error. Otherwise, retry.
                if attempt == retries - 1:
                    return Response(
                        {"detail": f"Ticket #{queue_number} is already being tracked."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                continue

        response_serializer = QueueEntryStatusSerializer(entry)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class QueueEntryStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BurstRateThrottle]

    def get(self, request, session_id):
        try:
            entry = QueueEntry.objects.get(session_id=session_id)
        except QueueEntry.DoesNotExist:
            return Response(
                {"detail": "Queue entry not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        with transaction.atomic():
            expire_stale_serving_entries(
                institution_id=entry.institution_id,
                grace_period_seconds=settings.QUEUE_GRACE_PERIOD_SECONDS,
            )

            tick_result = maybe_auto_tick_institution(
                institution_id=entry.institution_id,
                interval_seconds=settings.QUEUE_AUTO_TICK_INTERVAL_SECONDS,
                randomize=settings.QUEUE_AUTO_TICK_RANDOMIZE,
                grace_period_seconds=settings.QUEUE_GRACE_PERIOD_SECONDS,
            )
            if tick_result is not None:
                entry.refresh_from_db()
            else:
                entry.refresh_from_db()

        serializer = QueueEntryStatusSerializer(entry)
        return Response(serializer.data)


class QueueEntryCheckInView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BurstRateThrottle]

    def patch(self, request, session_id):
        entry, error = check_in_serving_entry(session_id)
        if error:
            if error.get("code") == "NOT_FOUND":
                return Response(
                    {"detail": error["message"]},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"detail": error["message"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = QueueEntryStatusSerializer(entry)
        return Response(serializer.data)


class QueueEntryCancelView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [BurstRateThrottle]

    def post(self, request, session_id):
        entry, error = cancel_queue_entry(session_id)
        if error:
            if error.get("code") == "NOT_FOUND":
                return Response(
                    {"detail": error["message"]},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {"detail": error["message"]},
                status=status.HTTP_400_BAD_REQUEST,
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
            queryset = queryset.filter(status__in=ACTIVE_QUEUE_STATUSES)

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


class QueueAutoTickView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        randomize = parse_bool_query_param(
            request.query_params.get("randomize"),
            default=settings.QUEUE_AUTO_TICK_RANDOMIZE,
        )
        force = parse_bool_query_param(
            request.query_params.get("force"),
            default=False,
        )

        result = auto_tick_active_institutions(
            interval_seconds=settings.QUEUE_AUTO_TICK_INTERVAL_SECONDS,
            randomize=randomize,
            force=force,
            grace_period_seconds=settings.QUEUE_GRACE_PERIOD_SECONDS,
        )
        return Response(result)
