import argparse
import os
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from mock_api.models import Institution
from queue_tracker.models import ACTIVE_QUEUE_STATUSES
from queue_tracker.services import simulate_queue_tick_for_institution


class Command(BaseCommand):
    help = "Run the mock queue worker loop for active institutions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=None,
            help="Seconds to wait between worker cycles.",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single cycle and exit.",
        )
        parser.add_argument(
            "--randomize",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="Use randomized increments when advancing the queue.",
        )

    def handle(self, *args, **options):
        once = options["once"]
        randomize = options["randomize"]
        interval = options["interval"]

        if not once:
            if interval is None:
                interval_from_env = os.getenv("QUEUE_WORKER_INTERVAL_SECONDS", "15")
                try:
                    interval = int(interval_from_env)
                except ValueError as exc:
                    raise CommandError(
                        "QUEUE_WORKER_INTERVAL_SECONDS must be an integer."
                    ) from exc

            if interval < 1:
                raise CommandError("--interval must be at least 1 second.")

        interval_label = f"{interval}s" if interval is not None else "n/a"

        self.stdout.write(
            self.style.SUCCESS(
                "Queue worker started "
                f"(interval={interval_label}, randomize={randomize}, once={once})."
            )
        )

        while True:
            close_old_connections()

            active_institutions = (
                Institution.objects.filter(
                    is_active=True,
                    queue_entries__status__in=ACTIVE_QUEUE_STATUSES,
                )
                .distinct()
                .order_by("id")
            )

            processed_any = False
            for institution in active_institutions:
                processed_any = True
                try:
                    result = simulate_queue_tick_for_institution(
                        institution.id,
                        randomize=randomize,
                        grace_period_seconds=settings.QUEUE_GRACE_PERIOD_SECONDS,
                    )
                except Institution.DoesNotExist:
                    continue

                if result.get("message"):
                    self.stdout.write(
                        (
                            f"[{institution.id}] {institution.name}: "
                            f"{result['message']}"
                        )
                    )
                    continue

                self.stdout.write(
                    (
                        f"[{institution.id}] {institution.name}: "
                        f"served={result['served_count']}, "
                        f"notified={result['notified_count']}, "
                        f"expired={result.get('expired_count', 0)}, "
                        f"current_serving={result['current_serving_number']}"
                    )
                )

            if not processed_any:
                self.stdout.write("No active institutions with queue entries.")

            if once:
                self.stdout.write(
                    self.style.SUCCESS("Queue worker completed one cycle.")
                )
                return

            close_old_connections()
            time.sleep(interval)
