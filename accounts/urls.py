from django.urls import path, include

from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import ( TokenRefreshView, )

from .views import *

router = DefaultRouter()
router.register(r'consumer', ConsumerViewSet, basename='consumer')
router.register(r'seller', SellerViewSet, basename = 'seller')


urlpatterns = [
    path('', include(router.urls)),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
