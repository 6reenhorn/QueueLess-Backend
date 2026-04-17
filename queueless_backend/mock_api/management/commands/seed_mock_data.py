import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Max
from django.utils import timezone

from mock_api.models import Institution
from queue_tracker.models import QueueEntry, QueueEntryStatus

INSTITUTION_SEED_DATA = [
    {
        "name": "Civil Service Commission (CSC)",
        "institution_type": Institution.InstitutionType.GOVERNMENT,
        "address": "Batasan Hills, Quezon City",
    },
    {
        "name": "Commission on Elections (COMELEC)",
        "institution_type": Institution.InstitutionType.GOVERNMENT,
        "address": "Palacio del Gobernador, Intramuros, Manila",
    },
    {
        "name": "Commission on Audit (COA)",
        "institution_type": Institution.InstitutionType.GOVERNMENT,
        "address": "Commonwealth Avenue, Quezon City",
    },
    {
        "name": "Government Service Insurance System (GSIS)",
        "institution_type": Institution.InstitutionType.GOVERNMENT,
        "address": "Financial Center, Pasay",
    },
    {
        "name": "Land Bank of the Philippines",
        "institution_type": Institution.InstitutionType.BANK,
        "address": "Malate, Manila",
    },
    {
        "name": "Development Bank of the Philippines (DBP)",
        "institution_type": Institution.InstitutionType.BANK,
        "address": "Makati City",
    },
    {
        "name": ("Al-Amanah Islamic Investment Bank of the Philippines"),
        "institution_type": Institution.InstitutionType.BANK,
        "address": "Makati City",
    },
    {
        "name": "Philippine Postal Savings Bank (UCPB)",
        "institution_type": Institution.InstitutionType.BANK,
        "address": "Liwasang Bonifacio, Manila",
    },
    {
        "name": "Philippine National Oil Co. (PNOC)",
        "institution_type": Institution.InstitutionType.UTILITY,
        "address": "Taguig City",
    },
    {
        "name": "Philippine Power Corp. (PCCP)",
        "institution_type": Institution.InstitutionType.UTILITY,
        "address": "Ortigas Center, Pasig",
    },
]


class Command(BaseCommand):
    help = "Seed mock institutions and optional queue entries for API simulation."

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-queues",
            action="store_true",
            help="Create institutions only and skip queue entry generation.",
        )
        parser.add_argument(
            "--min-queue",
            type=int,
            default=5,
            help="Minimum random queue entries per institution.",
        )
        parser.add_argument(
            "--max-queue",
            type=int,
            default=12,
            help="Maximum random queue entries per institution.",
        )
        parser.add_argument(
            "--reset-queues",
            action="store_true",
            help="Delete existing queue entries for seeded institutions first.",
        )

    def handle(self, *args, **options):
        skip_queues = options["skip_queues"]
        min_queue = options["min_queue"]
        max_queue = options["max_queue"]
        reset_queues = options["reset_queues"]

        if min_queue < 0 or max_queue < 0:
            self.stderr.write(self.style.ERROR("Queue limits cannot be negative."))
            return

        if min_queue > max_queue:
            self.stderr.write(
                self.style.ERROR("--min-queue cannot be greater than --max-queue.")
            )
            return

        seeded_institutions = []
        created_count = 0
        updated_count = 0

        for payload in INSTITUTION_SEED_DATA:
            institution, created = Institution.objects.update_or_create(
                name=payload["name"],
                institution_type=payload["institution_type"],
                defaults={
                    "address": payload["address"],
                    "api_endpoint": "",
                    "status": Institution.Status.OPEN,
                    "is_active": True,
                },
            )
            seeded_institutions.append(institution)
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Institutions seeded. "
                f"Created: {created_count}, Updated: {updated_count}."
            )
        )

        if skip_queues:
            self.stdout.write("Queue generation skipped (--skip-queues).")
            return

        total_queues_created = 0
        now = timezone.now()

        for institution in seeded_institutions:
            if reset_queues:
                QueueEntry.objects.filter(institution=institution).delete()

            existing_queue_state = QueueEntry.objects.filter(
                institution=institution
            ).aggregate(
                max_queue_number=Max("queue_number"),
                max_current_serving_number=Max("current_serving_number"),
            )
            existing_max = existing_queue_state["max_queue_number"]

            if existing_max is None:
                baseline_current_serving = random.randint(0, 7)
                next_queue_number = baseline_current_serving + 1
            else:
                baseline_current_serving = min(
                    existing_queue_state["max_current_serving_number"] or 0,
                    existing_max,
                )
                next_queue_number = existing_max + 1

            entries_to_create = random.randint(min_queue, max_queue)

            for i in range(entries_to_create):
                queue_number = next_queue_number + i
                status = random.choices(
                    [QueueEntryStatus.WAITING, QueueEntryStatus.NOTIFIED],
                    weights=[0.75, 0.25],
                    k=1,
                )[0]
                expires_at = None
                if random.random() < 0.15:
                    expires_at = now + timedelta(minutes=random.randint(15, 45))

                QueueEntry.objects.create(
                    institution=institution,
                    queue_number=queue_number,
                    current_serving_number=baseline_current_serving,
                    phone_number=f"09{random.randint(100_000_000, 999_999_999)}",
                    browser_push_opt_in=random.choice([True, False]),
                    near_turn_threshold=random.randint(2, 5),
                    near_turn_notified=status == QueueEntryStatus.NOTIFIED,
                    status=status,
                    expires_at=expires_at,
                )
                total_queues_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Queue entries generated: {total_queues_created} across "
                f"{len(seeded_institutions)} institutions."
            )
        )
