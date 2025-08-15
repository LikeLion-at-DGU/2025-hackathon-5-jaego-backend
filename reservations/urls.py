from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import *

router = DefaultRouter()
urlpatterns = [
    path('reservations/', include(router.urls)),
]
