import os
import time

from django.core.management.base import BaseCommand, CommandError

from mock_api.models import Institution
from queue_tracker.models import ACTIVE_QUEUE_STATUSES
from queue_tracker.services import simulate_queue_tick_for_institution


class Command(BaseCommand):
    help = "Run the mock queue worker loop for active institutions."

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=int(os.getenv("QUEUE_WORKER_INTERVAL_SECONDS", "15")),
            help="Seconds to wait between worker cycles.",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Run a single cycle and exit.",
        )
        parser.add_argument(
            "--randomize",
            action="store_true",
            default=True,
            help="Use randomized increments when advancing the queue.",
        )
        parser.add_argument(
            "--no-randomize",
            action="store_false",
            dest="randomize",
            help="Advance queues by one step per cycle.",
        )

    def handle(self, *args, **options):
        interval = options["interval"]
        if interval < 1:
            raise CommandError("--interval must be at least 1 second.")

        once = options["once"]
        randomize = options["randomize"]

        self.stdout.write(
            self.style.SUCCESS(
                "Queue worker started "
                f"(interval={interval}s, randomize={randomize}, once={once})."
            )
        )

        while True:
            active_institutions = (
                Institution.objects.filter(
                    is_active=True,
                    queue_entries__status__in=ACTIVE_QUEUE_STATUSES,
                )
                .distinct()
                .order_by("id")
            )

            if not active_institutions.exists():
                self.stdout.write("No active institutions with queue entries.")
            else:
                for institution in active_institutions:
                    try:
                        result = simulate_queue_tick_for_institution(
                            institution.id,
                            randomize=randomize,
                        )
                    except Institution.DoesNotExist:
                        continue

                    if result.get("message"):
                        self.stdout.write(
                            f"[{institution.id}] {institution.name}: {result['message']}"
                        )
                        continue

                    self.stdout.write(
                        (
                            f"[{institution.id}] {institution.name}: "
                            f"served={result['served_count']}, "
                            f"notified={result['notified_count']}, "
                            f"current_serving={result['current_serving_number']}"
                        )
                    )

            if once:
                self.stdout.write(
                    self.style.SUCCESS("Queue worker completed one cycle.")
                )
                return

            time.sleep(interval)
