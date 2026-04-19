import uuid

from django.db import models
from django.db.models import Q


class QueueEntryStatus(models.TextChoices):
    WAITING = "waiting", "Waiting"
    NOTIFIED = "notified", "Notified"
    SERVING = "serving", "Serving"
    SERVED = "served", "Served"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


ACTIVE_QUEUE_STATUSES = (
    QueueEntryStatus.WAITING,
    QueueEntryStatus.NOTIFIED,
    QueueEntryStatus.SERVING,
)


class QueueEntry(models.Model):
    institution = models.ForeignKey(
        "mock_api.Institution",
        on_delete=models.CASCADE,
        related_name="queue_entries",
    )
    session_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    queue_number = models.PositiveIntegerField()
    current_serving_number = models.PositiveIntegerField(default=0)
    phone_number = models.CharField(max_length=20, blank=True)
    browser_push_opt_in = models.BooleanField(default=False)
    near_turn_threshold = models.PositiveSmallIntegerField(default=3)
    near_turn_notified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=QueueEntryStatus.choices,
        default=QueueEntryStatus.WAITING,
    )
    issued_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    served_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    turn_called_at = models.DateTimeField(null=True, blank=True)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["institution_id", "queue_number"]
        indexes = [
            models.Index(fields=["institution", "status"]),
            models.Index(fields=["institution", "queue_number"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(current_serving_number__gte=0),
                name="queue_current_serving_non_negative",
            ),
            models.UniqueConstraint(
                fields=["institution", "queue_number"],
                condition=Q(status__in=ACTIVE_QUEUE_STATUSES),
                name="uniq_active_queue_number_per_institution",
            ),
        ]

    @property
    def people_ahead(self) -> int:
        return max(self.queue_number - self.current_serving_number - 1, 0)

    def __str__(self) -> str:
        return f"{self.institution.name} - #{self.queue_number} ({self.status})"
