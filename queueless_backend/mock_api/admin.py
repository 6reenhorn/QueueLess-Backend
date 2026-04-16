from django.contrib import admin

from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "institution_type", "api_endpoint", "status", "is_active")
    list_filter = ("institution_type", "status", "is_active")
    search_fields = ("name", "institution_type", "address", "api_endpoint")
