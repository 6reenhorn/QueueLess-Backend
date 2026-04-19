from django.test import SimpleTestCase, TestCase

from mock_api.models import Institution
from notifications.models import Notification

from .models import QueueEntry, QueueEntryStatus
from .services import simulate_queue_tick_for_institution


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

    def test_tick_advances_and_notifies(self):
        waiting_entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=4,
            near_turn_threshold=2,
            status=QueueEntryStatus.WAITING,
        )
        notified_entry = QueueEntry.objects.create(
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
        notified_entry.refresh_from_db()

        self.assertEqual(result["increment"], 1)
        self.assertEqual(result["current_serving_number"], 5)
        self.assertEqual(result["served_count"], 1)
        self.assertEqual(result["notified_count"], 1)
        self.assertEqual(waiting_entry.status, QueueEntryStatus.SERVED)
        self.assertEqual(notified_entry.status, QueueEntryStatus.NOTIFIED)

        turn_called_notifications = Notification.objects.filter(
            queue_entry=waiting_entry,
            event_type=Notification.EventType.TURN_CALLED,
            delivered=True,
        )
        near_turn_notifications = Notification.objects.filter(
            queue_entry=notified_entry,
            event_type=Notification.EventType.NEAR_TURN,
            delivered=True,
        )

        self.assertEqual(turn_called_notifications.count(), 1)
        self.assertEqual(near_turn_notifications.count(), 1)
        self.assertIn(
            "Queue #5 is now being served.", turn_called_notifications[0].message
        )
        self.assertIn("please prepare", near_turn_notifications[0].message)
