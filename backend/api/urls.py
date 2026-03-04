from django.urls import include, path
from rest_framework import routers

from .views import (
    UserViewSet,
    TokenView
)

router = routers.DefaultRouter()
router.register('users', UserViewSet, basename='users')
router.register('auth/token', TokenView, basename='token')

urlpatterns = [
    path('', include(router.urls)),
]
