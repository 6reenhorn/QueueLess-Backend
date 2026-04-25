from django.urls import path

from .views import (
    PushSubscriptionCreateView,
    QueueEntryNotificationAcknowledgeView,
    QueueEntryNotificationListView,
)

urlpatterns = [
    path(
        "entries/<uuid:session_id>/push-subscription/",
        PushSubscriptionCreateView.as_view(),
        name="push-subscription-create",
    ),
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
