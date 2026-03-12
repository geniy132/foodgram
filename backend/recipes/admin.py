from django.contrib import admin
from .models import (
    Tag,
    Recipe,
    Ingredient,
    IngredientRecipe,
    ShoppingCart,
    Favorite
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
        'get_favorite_count',
        'get_tags',
        'get_ingredients'
    )
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('author', 'tags')
    inlines = (IngredientRecipeInline,)

    @admin.display(description='Теги')
    def get_tags(self, obj):
        return ", ".join(tag.name for tag in obj.tags.all())

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ", ".join(ing.name for ing in obj.ingredients.all())

    @admin.display(description='В избранном')
    def get_favorite_count(self, obj):
        return obj.favorites.count()

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related(
            'tags', 'ingredients', 'author'
        )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
