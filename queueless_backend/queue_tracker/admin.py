from django.contrib import admin

from .models import QueueEntry


@admin.register(QueueEntry)
class QueueEntryAdmin(admin.ModelAdmin):
    list_display = (
        "institution",
        "queue_number",
        "current_serving_number",
        "status",
        "near_turn_notified",
        "issued_at",
    )
    list_filter = ("institution", "status", "near_turn_notified")
    search_fields = ("institution__name", "=queue_number", "phone_number")
