from django.urls import path

from .views import (
    QueueEntryNotificationAcknowledgeView,
    QueueEntryNotificationListView,
)

urlpatterns = [
    path(
        "entries/<uuid:session_id>/notifications/",
        QueueEntryNotificationListView.as_view(),
        name="queue-entry-notifications",
    ),
    path(
        "entries/<uuid:session_id>/notifications/<int:notification_id>/ack/",
        QueueEntryNotificationAcknowledgeView.as_view(),
        name="queue-entry-notification-ack",
    ),
]
