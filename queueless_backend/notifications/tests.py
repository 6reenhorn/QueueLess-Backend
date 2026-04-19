from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from mock_api.models import Institution
from queue_tracker.models import QueueEntry, QueueEntryStatus

from .models import Notification


class NotificationApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.institution = Institution.objects.create(
            name="Civil Service Commission",
            institution_type=Institution.InstitutionType.GOVERNMENT,
            status=Institution.Status.OPEN,
            is_active=True,
        )
        self.queue_entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=5,
            current_serving_number=3,
            near_turn_threshold=2,
            status=QueueEntryStatus.NOTIFIED,
        )
        self.notification_near_turn = Notification.objects.create(
            queue_entry=self.queue_entry,
            channel=Notification.Channel.SYSTEM,
            event_type=Notification.EventType.NEAR_TURN,
            message="Queue #5: please prepare, 1 ahead of you.",
            delivered=False,
        )
        self.notification_turn_called = Notification.objects.create(
            queue_entry=self.queue_entry,
            channel=Notification.Channel.SYSTEM,
            event_type=Notification.EventType.TURN_CALLED,
            message="Queue #5 is now being served.",
            delivered=True,
        )

    def test_list_notifications_for_session(self):
        response = self.client.get(
            f"/api/queue/entries/{self.queue_entry.session_id}/notifications/"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["institution_id"], self.institution.id)

    def test_list_notifications_with_filters(self):
        response = self.client.get(
            (
                f"/api/queue/entries/{self.queue_entry.session_id}/notifications/"
                "?delivered=false&event_type=near_turn"
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["id"], self.notification_near_turn.id
        )

    def test_list_notifications_invalid_event_type(self):
        response = self.client.get(
            (
                f"/api/queue/entries/{self.queue_entry.session_id}/notifications/"
                "?event_type=invalid"
            )
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("valid_event_types", response.data)

    def test_acknowledge_notification(self):
        response = self.client.patch(
            (
                f"/api/queue/entries/{self.queue_entry.session_id}/notifications/"
                f"{self.notification_near_turn.id}/ack/"
            ),
            {
                "delivered": True,
                "external_reference": "push-abc-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification_near_turn.refresh_from_db()
        self.assertTrue(self.notification_near_turn.delivered)
        self.assertEqual(
            self.notification_near_turn.external_reference,
            "push-abc-123",
        )

    def test_acknowledge_notification_not_found_for_session(self):
        other_entry = QueueEntry.objects.create(
            institution=self.institution,
            queue_number=6,
            current_serving_number=3,
            near_turn_threshold=2,
            status=QueueEntryStatus.WAITING,
        )
        response = self.client.patch(
            (
                f"/api/queue/entries/{other_entry.session_id}/notifications/"
                f"{self.notification_near_turn.id}/ack/"
            ),
            {"delivered": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
