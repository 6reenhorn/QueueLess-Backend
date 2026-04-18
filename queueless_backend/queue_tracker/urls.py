from django.urls import path

from .views import (
    InstitutionQueueStatusView,
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
]
