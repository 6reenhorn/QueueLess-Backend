import random
from datetime import timedelta
from uuid import uuid4

from django.core.cache import cache
from django.db import transaction
from django.db.models import ExpressionWrapper, F, IntegerField, Max, Value
from django.utils import timezone

from mock_api.models import Institution
from notifications.models import Notification

from .models import ACTIVE_QUEUE_STATUSES, QueueEntry, QueueEntryStatus


def expire_stale_serving_entries(institution_id, grace_period_seconds):
    """
    Expire SERVING entries whose grace period has elapsed
    AND who have NOT checked in.

    Returns the list of expired QueueEntry instances.
    """
    with transaction.atomic():
        cutoff = timezone.now() - timedelta(seconds=grace_period_seconds)
        stale_qs = QueueEntry.objects.select_for_update().filter(
            institution_id=institution_id,
            status=QueueEntryStatus.SERVING,
            turn_called_at__lte=cutoff,
            checked_in_at__isnull=True,
        )
        expired_entries = list(stale_qs)
        if expired_entries:
            now = timezone.now()
            expired_ids = [entry.id for entry in expired_entries]
            QueueEntry.objects.filter(pk__in=expired_ids).update(
                status=QueueEntryStatus.EXPIRED,
                updated_at=now,
            )
            Notification.objects.bulk_create(
                [
                    Notification(
                        queue_entry=entry,
                        channel=Notification.Channel.SYSTEM,
                        event_type=Notification.EventType.SESSION_EXPIRED,
                        message=(
                            f"Queue #{entry.queue_number} expired "
                            f"(no check-in within grace period)."
                        ),
                        delivered=False,
                    )
                    for entry in expired_entries
                ]
            )
        return expired_entries


def check_in_serving_entry(session_id):
    """
    Mark a SERVING entry as checked in. Stops the auto-expiry timer.

    Returns (entry, error). If successful, error is None.
    'error' is a dict with 'code' and 'message'.
    """
    with transaction.atomic():
        try:
            entry = QueueEntry.objects.select_for_update().get(session_id=session_id)
        except QueueEntry.DoesNotExist:
            return None, {"code": "NOT_FOUND", "message": "Queue entry not found."}

        if entry.status != QueueEntryStatus.SERVING:
            return None, {
                "code": "INVALID_STATUS",
                "message": (
                    f"Cannot check in: status is '{entry.status}', "
                    "expected 'serving'."
                ),
            }

        if entry.checked_in_at is not None:
            return entry, None  # Already checked in, idempotent

        entry.checked_in_at = timezone.now()
        entry.save(update_fields=["checked_in_at", "updated_at"])
        return entry, None


def maybe_auto_tick_institution(
    institution_id: int,
    *,
    interval_seconds: int = 15,
    randomize: bool = True,
    grace_period_seconds: int = 180,
):
    now = timezone.now().timestamp()
    interval = max(1, int(interval_seconds))
    last_tick_key = f"queue:auto_tick:last:{institution_id}"
    lock_key = f"queue:auto_tick:lock:{institution_id}"
    lock_token = str(uuid4())
    lock_timeout = max(30, interval * 2)

    last_tick_ts = cache.get(last_tick_key)
    if last_tick_ts is not None and (now - float(last_tick_ts)) < interval:
        return None

    if not cache.add(lock_key, lock_token, timeout=lock_timeout):
        return None

    try:
        now = timezone.now().timestamp()
        last_tick_ts = cache.get(last_tick_key)
        if last_tick_ts is not None and (now - float(last_tick_ts)) < interval:
            return None

        result = simulate_queue_tick_for_institution(
            institution_id=institution_id,
            randomize=randomize,
            grace_period_seconds=grace_period_seconds,
        )
        cache.set(last_tick_key, now, timeout=max(60, interval * 4))
        return result
    finally:
        # Note: This is a non-atomic TOCTOU check-and-delete.
        # In production with Redis, use a Lua script for an atomic release.
        try:
            if cache.get(lock_key) == lock_token:
                cache.delete(lock_key)
        except Exception:
            pass


def auto_tick_active_institutions(
    *,
    interval_seconds: int = 15,
    randomize: bool = True,
    force: bool = False,
    grace_period_seconds: int = 180,
):
    active_institution_ids = QueueEntry.objects.filter(
        status__in=ACTIVE_QUEUE_STATUSES
    ).values_list("institution_id", flat=True)

    institution_ids = list(
        Institution.objects.filter(
            is_active=True,
            id__in=active_institution_ids,
        )
        .values_list("id", flat=True)
        .distinct()
    )

    interval = max(1, int(interval_seconds))

    ticked = 0
    skipped = 0
    for institution_id in institution_ids:
        if force:
            simulate_queue_tick_for_institution(
                institution_id=institution_id,
                randomize=randomize,
                grace_period_seconds=grace_period_seconds,
            )
            cache.set(
                f"queue:auto_tick:last:{institution_id}",
                timezone.now().timestamp(),
                timeout=max(60, interval * 4),
            )
            ticked += 1
            continue

        result = maybe_auto_tick_institution(
            institution_id=institution_id,
            interval_seconds=interval_seconds,
            randomize=randomize,
            grace_period_seconds=grace_period_seconds,
        )
        if result is None:
            skipped += 1
        else:
            ticked += 1

    return {
        "institutions_considered": len(institution_ids),
        "institutions_ticked": ticked,
        "institutions_skipped": skipped,
        "force": force,
    }


def simulate_queue_tick_for_institution(
    institution_id: int,
    randomize: bool = True,
    grace_period_seconds: int = 180,
):
    with transaction.atomic():
        institution = Institution.objects.select_for_update().get(pk=institution_id)

        # --- Step 1: Expire stale no-shows ---
        expired_entries = expire_stale_serving_entries(
            institution_id=institution.id,
            grace_period_seconds=grace_period_seconds,
        )

        # --- Step 2: Auto-serve checked-in SERVING entries ---
        checked_in_serving = list(
            QueueEntry.objects.select_for_update().filter(
                institution=institution,
                status=QueueEntryStatus.SERVING,
                checked_in_at__isnull=False,
            )
        )
        if checked_in_serving:
            now = timezone.now()
            checked_in_ids = [entry.id for entry in checked_in_serving]
            QueueEntry.objects.filter(pk__in=checked_in_ids).update(
                status=QueueEntryStatus.SERVED,
                served_at=now,
                updated_at=now,
            )
            Notification.objects.bulk_create(
                [
                    Notification(
                        queue_entry=entry,
                        channel=Notification.Channel.SYSTEM,
                        event_type=Notification.EventType.SESSION_COMPLETED,
                        message=f"Queue #{entry.queue_number} has been completed.",
                        delivered=False,
                    )
                    for entry in checked_in_serving
                ]
            )

        # --- Step 3: Advance current_serving_number ---
        active_entries = list(
            QueueEntry.objects.select_for_update()
            .filter(
                institution=institution,
                status__in=ACTIVE_QUEUE_STATUSES,
            )
            .order_by("queue_number")
        )

        if not active_entries:
            last_known_serving_number = (
                QueueEntry.objects.filter(institution=institution).aggregate(
                    value=Max("current_serving_number")
                )["value"]
                or 0
            )
            return {
                "institution_id": institution.id,
                "randomized": randomize,
                "increment": 0,
                "current_serving_number": last_known_serving_number,
                "served_count": len(checked_in_serving),
                "notified_count": 0,
                "expired_count": len(expired_entries),
                "message": "No active queue entries to advance.",
            }

        current_serving = max(entry.current_serving_number for entry in active_entries)
        highest_queue_number = max(entry.queue_number for entry in active_entries)
        clamped_current_serving = min(current_serving, highest_queue_number)
        increment = random.choice([0, 1, 1, 1, 2]) if randomize else 1
        capped_current_serving = min(
            clamped_current_serving + increment,
            highest_queue_number,
        )
        new_current_serving = max(clamped_current_serving, capped_current_serving)

        now = timezone.now()
        QueueEntry.objects.filter(
            institution=institution,
            status__in=ACTIVE_QUEUE_STATUSES,
        ).update(
            current_serving_number=new_current_serving,
            updated_at=now,
        )

        # --- Step 4: Transition newly-reached entries to SERVING ---
        newly_serving_entries = list(
            QueueEntry.objects.select_for_update().filter(
                institution=institution,
                status__in=(QueueEntryStatus.WAITING, QueueEntryStatus.NOTIFIED),
                queue_number__lte=new_current_serving,
            )
        )

        if newly_serving_entries:
            newly_serving_ids = [entry.id for entry in newly_serving_entries]
            QueueEntry.objects.filter(pk__in=newly_serving_ids).update(
                status=QueueEntryStatus.SERVING,
                turn_called_at=now,
                expires_at=now + timedelta(seconds=grace_period_seconds),
                updated_at=now,
            )
            Notification.objects.bulk_create(
                [
                    Notification(
                        queue_entry=entry,
                        channel=Notification.Channel.SYSTEM,
                        event_type=Notification.EventType.TURN_CALLED,
                        message=(
                            f"Queue #{entry.queue_number}: it's your turn! "
                            f"Please check in to confirm your presence."
                        ),
                        delivered=False,
                    )
                    for entry in newly_serving_entries
                ]
            )

        # --- Step 5: Near-turn notifications ---
        near_turn_entries = list(
            QueueEntry.objects.select_for_update()
            .filter(
                institution=institution,
                status=QueueEntryStatus.WAITING,
                near_turn_notified=False,
                queue_number__gt=new_current_serving,
            )
            .annotate(
                people_ahead_calc=ExpressionWrapper(
                    F("queue_number") - Value(new_current_serving) - Value(1),
                    output_field=IntegerField(),
                )
            )
            .filter(people_ahead_calc__lte=F("near_turn_threshold"))
        )

        if near_turn_entries:
            notified_entry_ids = [entry.id for entry in near_turn_entries]
            QueueEntry.objects.filter(pk__in=notified_entry_ids).update(
                status=QueueEntryStatus.NOTIFIED,
                near_turn_notified=True,
                updated_at=now,
            )
            Notification.objects.bulk_create(
                [
                    Notification(
                        queue_entry=entry,
                        channel=Notification.Channel.SYSTEM,
                        event_type=Notification.EventType.NEAR_TURN,
                        message=(
                            f"Queue #{entry.queue_number}: please prepare, "
                            f"{entry.people_ahead_calc} ahead of you."
                        ),
                        delivered=False,
                    )
                    for entry in near_turn_entries
                ]
            )

        return {
            "institution_id": institution.id,
            "randomized": randomize,
            "increment": increment,
            "current_serving_number": new_current_serving,
            "served_count": len(checked_in_serving),
            "newly_serving_count": len(newly_serving_entries),
            "notified_count": len(near_turn_entries),
            "expired_count": len(expired_entries),
        }
