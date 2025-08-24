from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import CategoryViewset

router = DefaultRouter()
router.register(r'', CategoryViewset, basename = 'category')

urlpatterns = [
    path('', include(router.urls)),
]
