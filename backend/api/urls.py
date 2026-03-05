from django.urls import include, path
from rest_framework import routers

from .views import (
    UserViewSet,
    TokenView,
    RecipeView,
    TagView
)

router = routers.DefaultRouter()
router.register('recipes', RecipeView, basename='recipes')
router.register('tags', TagView, basename='tags')
router.register('users', UserViewSet, basename='users')
router.register('auth/token', TokenView, basename='token')

urlpatterns = [
    path('', include(router.urls)),
]
