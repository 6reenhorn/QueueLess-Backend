from rest_framework import serializers

from .models import Institution


class InstitutionSerializer(serializers.ModelSerializer):
    queue_waiting_count = serializers.IntegerField(read_only=True)
    current_serving_number = serializers.IntegerField(read_only=True)
    next_queue_number = serializers.IntegerField(read_only=True)

    class Meta:
        model = Institution
        fields = [
            "id",
            "name",
            "institution_type",
            "address",
            "api_endpoint",
            "status",
            "is_active",
            "is_available_for_queue",
            "queue_waiting_count",
            "current_serving_number",
            "next_queue_number",
        ]
