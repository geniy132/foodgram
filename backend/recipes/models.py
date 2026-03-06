from django.contrib.auth import get_user_model
from django.db import models

from .constants import (
    SHORT_NAME_LENGTH,
    NAME_MAX_LENGHT,
    TEXT_MAX_LENGTH,
    SLUG_MAX_LENGTH
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
        max_length=SHORT_NAME_LENGTH
    )

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name[:SHORT_NAME_LENGTH]


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

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name[:SHORT_NAME_LENGTH]


class Recipe(SlugModelMixin, models.Model):
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
        null=True,
        default=None
    )
    name = models.CharField(
        'Название',
        max_length=NAME_MAX_LENGHT)
    text = models.TextField(
        'Описание',
        max_length=TEXT_MAX_LENGTH
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта'
    )
    is_favorited = models.BooleanField(
        'Избранное',
        default=False,
        blank=True
    )
    is_in_shopping_cart = models.BooleanField(
        'В списке покупок',
        default=False,
        blank=True
    )
    slug = models.SlugField(
        'Адрес для рецепта',
        unique=True,
        blank=True,
        max_length=SLUG_MAX_LENGTH,
        help_text=('Укажите адрес для страницы рецепта. Используйте только '
                   'латиницу, цифры, дефисы и знаки подчёркивания')
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('name',)
        constraints = (
            models.UniqueConstraint(
                fields=('author', 'name'),
                name='unique_dish'
            ),
        )

    def __str__(self):
        return self.name[:SHORT_NAME_LENGTH]

    def get_slug_content(self):
        return f'{self.name}-{self.author.id}'


class IngredientRecipe(models.Model):
    """Промежуточная модель ингридиента."""
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    amount = models.CharField('Количество', max_length=50)

    def __str__(self):
        return f'{self.ingredient} {self.recipe}'
