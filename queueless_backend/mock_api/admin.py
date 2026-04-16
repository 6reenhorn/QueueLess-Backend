from django.contrib import admin

from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "institution_type",
        "api_endpoint",
        "status",
        "is_active",
        "available_for_queue",
    )
    list_filter = ("institution_type", "status", "is_active")
    search_fields = ("name", "institution_type", "address", "api_endpoint")

    @admin.display(boolean=True, description="Queue Available")
    def available_for_queue(self, obj):
        return obj.is_available_for_queue
