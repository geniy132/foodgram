from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models

from .constants import (
    SHORT_NAME_LENGTH,
    NAME_MAX_LENGTH,
    TEXT_MAX_LENGTH,
    SLUG_MAX_LENGTH,
    UNIT_MAX_LENGTH
)
from .mixins import SlugModelMixin

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингридиента."""
    name = models.CharField(
        'Название',
        unique=True,
        max_length=SHORT_NAME_LENGTH
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=UNIT_MAX_LENGTH
    )

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Tag(SlugModelMixin, models.Model):
    """Модель тега."""
    name = models.CharField(
        'Название',
        unique=True,
        max_length=SHORT_NAME_LENGTH
    )
    slug = models.SlugField(
        'Cлаг',
        unique=True,
        blank=True,
        max_length=SLUG_MAX_LENGTH
    )

    def get_slug_content(self):
        return self.name

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name[:SHORT_NAME_LENGTH]


class Recipe(models.Model):
    """Модель рецепта."""

    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipe',
        related_name='recipes',
        verbose_name='Ингридиенты'
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='recipes',
        verbose_name='Теги'
    )
    image = models.ImageField(
        'Фото блюда',
        upload_to='images/dish_images',
    )
    name = models.CharField(
        'Название',
        max_length=NAME_MAX_LENGTH)
    text = models.TextField(
        'Описание',
        max_length=TEXT_MAX_LENGTH
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            validators.MinValueValidator(
                1, message='Минимум 1 минута'
            ),
            validators.MaxValueValidator(
                32000, message='Слишком долгое приготовление'
            )
        ]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта'
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-id',)
        constraints = (
            models.UniqueConstraint(
                fields=('author', 'name'),
                name='unique_dish'
            ),
        )

    def __str__(self):
        return self.name[:SHORT_NAME_LENGTH]


class IngredientRecipe(models.Model):
    """Промежуточная модель ингридиента."""
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipes'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        default=0
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient_in_recipe'
            )
        ]

    def __str__(self):
        amount = self.amount if self.amount else 'по вкусу'
        return f'{self.ingredient} ({amount}) в рецепте {self.recipe}'


class ShoppingCart(models.Model):
    """Модель списка покупок."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='shopping_cart'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='shopping_cart'
    )

    class Meta:
        verbose_name = 'список покупок'
        verbose_name_plural = 'Покупки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_cart_recipe'
            )
        ]


class Favorite(models.Model):
    """Модель избранного."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE, related_name='favorites'
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]
