from django.urls import include, path
from rest_framework import routers

from .views import IngredientView, RecipeView, TagView, UserViewSet


router = routers.DefaultRouter()
router.register('ingredients', IngredientView, basename='ingredients')
router.register('recipes', RecipeView, basename='recipes')
router.register('tags', TagView, basename='tags')
router.register('users', UserViewSet, basename='users')

urlpatterns = [
    path('auth/', include('djoser.urls.authtoken')),
    path('', include(router.urls)),

]
