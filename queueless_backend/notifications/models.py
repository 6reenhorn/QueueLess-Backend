from django.db import models


class Notification(models.Model):
    class Channel(models.TextChoices):
        BROWSER = "browser", "Browser Push"
        SMS = "sms", "SMS"
        SYSTEM = "system", "System"

    class EventType(models.TextChoices):
        NEAR_TURN = "near_turn", "Near Turn"
        TURN_CALLED = "turn_called", "Turn Called"
        SESSION_EXPIRED = "session_expired", "Session Expired"
        GENERIC = "generic", "Generic"

    queue_entry = models.ForeignKey(
        "queue_tracker.QueueEntry",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    channel = models.CharField(max_length=20, choices=Channel.choices)
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    delivered = models.BooleanField(default=False)
    external_reference = models.CharField(max_length=120, blank=True)
    error_detail = models.TextField(blank=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["queue_entry", "event_type"]),
            models.Index(fields=["channel", "delivered"]),
        ]

    def __str__(self) -> str:
        return f"{self.queue_entry} - {self.channel} - {self.event_type}"
