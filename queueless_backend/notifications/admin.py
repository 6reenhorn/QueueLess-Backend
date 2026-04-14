from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = (
		"queue_entry",
		"channel",
		"event_type",
		"delivered",
		"sent_at",
	)
	list_filter = ("channel", "event_type", "delivered")
	search_fields = ("queue_entry__institution__name", "message", "external_reference")
