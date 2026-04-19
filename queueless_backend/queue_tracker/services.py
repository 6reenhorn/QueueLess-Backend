import random

from django.core.cache import cache
from django.db import transaction
from django.db.models import ExpressionWrapper, F, IntegerField, Max, Value
from django.utils import timezone

from mock_api.models import Institution
from notifications.models import Notification

from .models import ACTIVE_QUEUE_STATUSES, QueueEntry, QueueEntryStatus


def maybe_auto_tick_institution(
    institution_id: int,
    *,
    interval_seconds: int = 15,
    randomize: bool = True,
):
    now = timezone.now().timestamp()
    interval = max(1, int(interval_seconds))
    last_tick_key = f"queue:auto_tick:last:{institution_id}"
    lock_key = f"queue:auto_tick:lock:{institution_id}"

    last_tick_ts = cache.get(last_tick_key)
    if last_tick_ts is not None and (now - float(last_tick_ts)) < interval:
        return None

    if not cache.add(lock_key, "1", timeout=interval):
        return None

    try:
        now = timezone.now().timestamp()
        last_tick_ts = cache.get(last_tick_key)
        if last_tick_ts is not None and (now - float(last_tick_ts)) < interval:
            return None

        result = simulate_queue_tick_for_institution(
            institution_id=institution_id,
            randomize=randomize,
        )
        cache.set(last_tick_key, now, timeout=max(60, interval * 4))
        return result
    finally:
        cache.delete(lock_key)


def auto_tick_active_institutions(
    *,
    interval_seconds: int = 15,
    randomize: bool = True,
    force: bool = False,
):
    institution_ids = list(
        QueueEntry.objects.filter(status__in=ACTIVE_QUEUE_STATUSES)
        .values_list("institution_id", flat=True)
        .distinct()
    )

    ticked = 0
    skipped = 0
    for institution_id in institution_ids:
        if force:
            simulate_queue_tick_for_institution(
                institution_id=institution_id,
                randomize=randomize,
            )
            ticked += 1
            continue

        result = maybe_auto_tick_institution(
            institution_id=institution_id,
            interval_seconds=interval_seconds,
            randomize=randomize,
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
):
    with transaction.atomic():
        institution = Institution.objects.select_for_update().get(pk=institution_id)

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
                "served_count": 0,
                "notified_count": 0,
                "message": "No active queue entries to simulate.",
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
        served_entries = list(
            QueueEntry.objects.filter(
                institution=institution,
                status__in=ACTIVE_QUEUE_STATUSES,
                queue_number__lte=new_current_serving,
            )
        )

        if served_entries:
            served_entry_ids = [entry.id for entry in served_entries]
            QueueEntry.objects.filter(pk__in=served_entry_ids).update(
                status=QueueEntryStatus.SERVED,
                served_at=now,
                updated_at=now,
            )
            Notification.objects.bulk_create(
                [
                    Notification(
                        queue_entry=entry,
                        channel=Notification.Channel.SYSTEM,
                        event_type=Notification.EventType.TURN_CALLED,
                        message=f"Queue #{entry.queue_number} is now being served.",
                        delivered=False,
                    )
                    for entry in served_entries
                ]
            )

        near_turn_entries = list(
            QueueEntry.objects.filter(
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
            "served_count": len(served_entries),
            "notified_count": len(near_turn_entries),
        }
