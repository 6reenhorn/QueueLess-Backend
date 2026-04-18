from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import InstitutionViewSet

router = DefaultRouter()
router.register("institutions", InstitutionViewSet, basename="institution")

urlpatterns = [
    path("", include(router.urls)),
]
