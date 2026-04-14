from django.contrib import admin

from .models import Institution


@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ("name", "institution_type", "api_endpoint", "is_active")
    list_filter = ("institution_type", "is_active")
    search_fields = ("name", "institution_type", "api_endpoint")
