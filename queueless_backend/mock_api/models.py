from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Institution(TimeStampedModel):
    class InstitutionType(models.TextChoices):
        BANK = "bank", "Bank"
        GOVERNMENT = "government", "Government Office"
        UTILITY = "utility", "Utility Provider"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"
        PAUSED = "paused", "Paused"

    name = models.CharField(max_length=255)
    institution_type = models.CharField(
        max_length=20,
        choices=InstitutionType.choices,
        default=InstitutionType.OTHER,
    )
    address = models.CharField(max_length=500, blank=True, default="")
    api_endpoint = models.URLField(max_length=500, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        help_text=(
            "Operational state of the institution (for example, whether it is "
            "open, closed, or paused)."
        ),
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Administrative flag indicating whether this institution should be "
            "enabled in the application, independent of its operational status."
        ),
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "institution_type"],
                name="uniq_institution_name_per_type",
            )
        ]

    def __str__(self) -> str:
        return (
            f"{self.name} ({self.get_institution_type_display()})"
            f" - {self.get_status_display()}"
        )

    @property
    def is_available_for_queue(self) -> bool:
        return self.is_active and self.status == self.Status.OPEN
