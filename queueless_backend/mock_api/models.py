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

    name = models.CharField(max_length=255)
    institution_type = models.CharField(
        max_length=20,
        choices=InstitutionType.choices,
        default=InstitutionType.OTHER,
    )
    api_endpoint = models.URLField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "institution_type"],
                name="uniq_institution_name_per_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_institution_type_display()})"
