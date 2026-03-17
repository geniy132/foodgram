from django.contrib import admin
from django.db.models import Count
from pytils.translit import slugify

from .models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag
)


class IngredientRecipeInline(admin.TabularInline):
    """Позволяет добавлять ингредиенты прямо в карточке рецепта."""
    model = IngredientRecipe
    extra = 1
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'pub_date',
        'get_favorite_count',
        'get_tags',
        'get_ingredients'
    )
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('author', 'tags', 'pub_date')
    inlines = (IngredientRecipeInline,)

    @admin.display(description='Теги')
    def get_tags(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ", ".join(ing.name for ing in obj.ingredients.all())

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'tags', 'ingredients', 'author'
        ).annotate(
            favorite_count=Count('favorites')
        )

    @admin.display(description='В избранном', ordering='favorite_count')
    def get_favorite_count(self, obj):
        return obj.favorite_count


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            recipes_count=Count('recipes')
        )

    @admin.display(
        description='Использован в рецептах',
        ordering='recipes_count'
    )
    def get_recipes_count(self, obj):
        return obj.recipes_count


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = slugify(obj.name)
        super().save_model(request, obj, form, change)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
