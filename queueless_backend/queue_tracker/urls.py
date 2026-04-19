from django.urls import path

from .views import (
    InstitutionQueueStatusView,
    QueueAutoTickView,
    QueueEntryCheckInView,
    QueueEntryStatusView,
    QueueJoinView,
    QueueSimulateTickView,
)

urlpatterns = [
    path("join/", QueueJoinView.as_view(), name="queue-join"),
    path(
        "institutions/<int:institution_id>/entries/",
        InstitutionQueueStatusView.as_view(),
        name="queue-institution-entries",
    ),
    path(
        "entries/<uuid:session_id>/status/",
        QueueEntryStatusView.as_view(),
        name="queue-entry-status",
    ),
    path(
        "institutions/<int:institution_id>/simulate-tick/",
        QueueSimulateTickView.as_view(),
        name="queue-simulate-tick",
    ),
    path(
        "entries/<uuid:session_id>/check-in/",
        QueueEntryCheckInView.as_view(),
        name="queue-entry-check-in",
    ),
    path(
        "auto-tick/",
        QueueAutoTickView.as_view(),
        name="queue-auto-tick",
    ),
]
