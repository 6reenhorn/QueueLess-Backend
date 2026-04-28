from datetime import timedelta

from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from mock_api.models import Institution
from notifications.models import Notification

from .models import QueueEntry, QueueEntryStatus
from .services import (
    check_in_serving_entry,
    maybe_auto_tick_institution,
    simulate_queue_tick_for_institution,
)


class QueueTrackerSmokeTest(SimpleTestCase):
    def test_sanity(self):
        self.assertTrue(True)


class QueueTickServiceTests(TestCase):
    def setUp(self):
        self.institution = Institution.objects.create(
            name="Civil Service Commission",
            institution_type=Institution.InstitutionType.GOVERNMENT,
            status=Institution.Status.OPEN,
            is_active=True,
        )

    def test_tick_with_no_active_entries(self):
        result = simulate_queue_tick_for_institution(
            self.institution.id, randomize=False
        )

        self.assertEqual(result["institution_id"], self.institution.id)
        self.assertEqual(result["served_count"], 0)
        self.assertEqual(result["notified_count"], 0)
        self.assertIn("message", result)

    def test_tick_with_no_active_entries_uses_last_known_serving_number(self):
        QueueEntry.objects.create(
            institution=self.institution,
            queue_number=4,
            current_serving_number=3,
            near_turn_threshold=2,
            status=QueueEntryStatus.SERVED,
        )

        result = simulate_queue_tick_for_institution(
            self.institution.id,
            randomize=False,
        )

        self.assertEqual(result["current_serving_number"], 3)
        self.assertEqual(result["served_count"], 0)
        self.assertEqual(result["notified_count"], 0)

    def test_tick_advances_and_transitions_to_serving(self):
        waiting_entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=4,
            near_turn_threshold=2,
            status=QueueEntryStatus.WAITING,
        )
        waiting_entry_to_notify = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=6,
            current_serving_number=4,
            near_turn_threshold=2,
            status=QueueEntryStatus.WAITING,
        )

        result = simulate_queue_tick_for_institution(
            self.institution.id, randomize=False
        )

        waiting_entry.refresh_from_db()
        waiting_entry_to_notify.refresh_from_db()

        self.assertEqual(result["increment"], 1)
        self.assertEqual(result["current_serving_number"], 5)
        self.assertEqual(result["newly_serving_count"], 1)
        self.assertEqual(result["notified_count"], 1)

        # Should be SERVING, not SERVED
        self.assertEqual(waiting_entry.status, QueueEntryStatus.SERVING)
        self.assertIsNotNone(waiting_entry.turn_called_at)

        self.assertEqual(
            waiting_entry_to_notify.status,
            QueueEntryStatus.NOTIFIED,
        )

        turn_called_notifications = Notification.objects.filter(
            queue_entry=waiting_entry,
            event_type=Notification.EventType.TURN_CALLED,
            delivered=False,
        )
        self.assertEqual(turn_called_notifications.count(), 1)
        self.assertIn("it's your turn!", turn_called_notifications[0].message)

    def test_checked_in_entry_served_on_next_tick(self):
        serving_entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=5,
            status=QueueEntryStatus.SERVING,
            turn_called_at=timezone.now(),
            checked_in_at=timezone.now(),
        )

        result = simulate_queue_tick_for_institution(
            self.institution.id, randomize=False
        )

        serving_entry.refresh_from_db()
        self.assertEqual(serving_entry.status, QueueEntryStatus.SERVED)
        self.assertEqual(result["served_count"], 1)

    def test_expired_entries_skipped_on_next_tick(self):
        # Grace period is 180s by default
        expired_serving = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=5,
            status=QueueEntryStatus.SERVING,
            turn_called_at=timezone.now() - timedelta(seconds=200),
            checked_in_at=None,
        )

        result = simulate_queue_tick_for_institution(
            self.institution.id, randomize=False
        )

        expired_serving.refresh_from_db()
        self.assertEqual(expired_serving.status, QueueEntryStatus.EXPIRED)
        self.assertEqual(result["expired_count"], 1)

        expiry_notifications = Notification.objects.filter(
            queue_entry=expired_serving,
            event_type=Notification.EventType.SESSION_EXPIRED,
        )
        self.assertEqual(expiry_notifications.count(), 1)

    def test_expires_at_populated_when_serving(self):
        # Create an entry that will transition to SERVING on next tick
        QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=4,
            status=QueueEntryStatus.WAITING,
        )

        simulate_queue_tick_for_institution(
            self.institution.id, randomize=False, grace_period_seconds=180
        )

        entry = QueueEntry.objects.get(institution=self.institution, queue_number=5)
        self.assertEqual(entry.status, QueueEntryStatus.SERVING)
        self.assertIsNotNone(entry.expires_at)
        # expires_at should be roughly turn_called_at + 180s
        expected_expiry = entry.turn_called_at + timedelta(seconds=180)
        self.assertAlmostEqual(
            entry.expires_at.timestamp(), expected_expiry.timestamp(), places=1
        )


class QueueAutoTickServiceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.active_institution = Institution.objects.create(
            name="Active Office",
            institution_type=Institution.InstitutionType.GOVERNMENT,
            status=Institution.Status.OPEN,
            is_active=True,
        )

    def test_maybe_auto_tick_skips_within_interval(self):
        QueueEntry.objects.create(
            institution=self.active_institution,
            queue_number=6,
            current_serving_number=5,
            status=QueueEntryStatus.WAITING,
        )

        first_result = maybe_auto_tick_institution(
            institution_id=self.active_institution.id,
            interval_seconds=60,
            randomize=False,
        )
        second_result = maybe_auto_tick_institution(
            institution_id=self.active_institution.id,
            interval_seconds=60,
            randomize=False,
        )

        self.assertIsNotNone(first_result)
        self.assertIsNone(second_result)


class QueueCheckInTests(TestCase):
    def setUp(self):
        self.institution = Institution.objects.create(
            name="Test Office",
            institution_type=Institution.InstitutionType.GOVERNMENT,
            status=Institution.Status.OPEN,
            is_active=True,
        )

    def test_check_in_success(self):
        entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=5,
            status=QueueEntryStatus.SERVING,
            turn_called_at=timezone.now(),
        )

        updated_entry, error = check_in_serving_entry(entry.session_id)

        self.assertIsNone(error)
        self.assertIsNotNone(updated_entry.checked_in_at)

    def test_check_in_invalid_status(self):
        entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=4,
            status=QueueEntryStatus.WAITING,
        )

        updated_entry, error = check_in_serving_entry(entry.session_id)

        self.assertIsNone(updated_entry)
        self.assertIn("Cannot check in", error["message"])
        self.assertEqual(error["code"], "INVALID_STATUS")


class QueueJoinViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.institution = Institution.objects.create(
            name="Test Office",
            institution_type=Institution.InstitutionType.GOVERNMENT,
            status=Institution.Status.OPEN,
            is_active=True,
        )

    def test_join_with_valid_ticket(self):
        response = self.client.post(
            "/api/queue/join/",
            {
                "institution_id": self.institution.id,
                "queue_number": 10,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["queue_number"], 10)

    def test_join_with_already_served_ticket(self):
        # Create a served entry to set the current serving number to 10
        QueueEntry.objects.create(
            institution=self.institution,
            queue_number=10,
            current_serving_number=10,
            status=QueueEntryStatus.SERVED,
        )

        response = self.client.post(
            "/api/queue/join/",
            {
                "institution_id": self.institution.id,
                "queue_number": 5,  # 5 < 10
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already been served", response.data["detail"])

    def test_join_with_duplicate_active_ticket(self):
        # Someone is already tracking #15
        QueueEntry.objects.create(
            institution=self.institution,
            queue_number=15,
            current_serving_number=10,
            status=QueueEntryStatus.WAITING,
        )

        response = self.client.post(
            "/api/queue/join/",
            {
                "institution_id": self.institution.id,
                "queue_number": 15,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already being tracked", response.data["detail"])


class QueueCancellationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.institution = Institution.objects.create(
            name="Test Office",
            institution_type=Institution.InstitutionType.GOVERNMENT,
            status=Institution.Status.OPEN,
            is_active=True,
        )

    def test_cancel_success(self):
        entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=4,
            status=QueueEntryStatus.WAITING,
        )

        response = self.client.post(f"/api/queue/entries/{entry.session_id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        entry.refresh_from_db()
        self.assertEqual(entry.status, QueueEntryStatus.CANCELLED)

        # Verify notification created
        notifications = Notification.objects.filter(
            queue_entry=entry,
            message__icontains="cancelled",
        )
        self.assertTrue(notifications.exists())

    def test_cancel_already_cancelled(self):
        entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=4,
            status=QueueEntryStatus.CANCELLED,
        )

        response = self.client.post(f"/api/queue/entries/{entry.session_id}/cancel/")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot cancel", response.data["detail"])

    def test_rejoin_after_cancel(self):
        # 1. Join
        entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=20,
            current_serving_number=10,
            status=QueueEntryStatus.WAITING,
        )

        # 2. Try to join again with same number (should fail)
        response_join_fail = self.client.post(
            "/api/queue/join/",
            {
                "institution_id": self.institution.id,
                "queue_number": 20,
            },
        )
        self.assertEqual(response_join_fail.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Cancel first entry
        response_cancel = self.client.post(
            f"/api/queue/entries/{entry.session_id}/cancel/"
        )
        self.assertEqual(response_cancel.status_code, status.HTTP_200_OK)

        # 4. Try to join again with same number (should succeed now)
        response_join_success = self.client.post(
            "/api/queue/join/",
            {
                "institution_id": self.institution.id,
                "queue_number": 20,
            },
        )
        self.assertEqual(response_join_success.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_join_success.data["queue_number"], 20)
