from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models

from .constants import (
    COOKING_TIME_MIN,
    COOKING_TIME_MAX,
    INGREDIENT_AMOUNT_MIN,
    INGREDIENT_AMOUNT_MAX,
    INGREDIENT_NAME_LENGTH,
    INGREDIENT_UNIT_LENGTH,
    RECIPE_NAME_LENGTH,
    SHORT_NAME_LENGTH,
    SLUG_MAX_LENGTH
)

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингредиента."""

    name = models.CharField(
        'Название',
        max_length=INGREDIENT_NAME_LENGTH
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=INGREDIENT_UNIT_LENGTH
    )

    class Meta:
        verbose_name = 'ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_unit'
            ),
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
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
        null=True,
        max_length=SLUG_MAX_LENGTH
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'
        ordering = ('name',)

    def __str__(self):
        return self.name[:SHORT_NAME_LENGTH]


class UserRecipeBaseModel(models.Model):
    """Абстрактная модель для Избранного и Списка покупок."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        'Recipe',
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_%(class)s'
            )
        ]


class ShoppingCart(UserRecipeBaseModel):
    """Модель списка покупок."""

    class Meta(UserRecipeBaseModel.Meta):
        verbose_name = 'список покупок'
        verbose_name_plural = 'Покупки'
        default_related_name = 'shopping_cart'


class Favorite(UserRecipeBaseModel):
    """Модель избранного."""

    class Meta(UserRecipeBaseModel.Meta):
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'


class RecipeQuerySet(models.QuerySet):
    """
    QuerySet для работы с рецептами.
    """

    def add_user_annotations(self, user):
        if user.is_anonymous:
            return self.annotate(
                is_favorited=models.Value(
                    False, output_field=models.BooleanField()
                ),
                is_in_shopping_cart=models.Value(
                    False, output_field=models.BooleanField()
                )
            )
        return self.annotate(
            is_favorited=models.Exists(
                Favorite.objects.filter(
                    user=user, recipe=models.OuterRef('pk')
                )
            ),
            is_in_shopping_cart=models.Exists(
                ShoppingCart.objects.filter(
                    user=user, recipe=models.OuterRef('pk')
                )
            )
        )


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
        max_length=RECIPE_NAME_LENGTH)
    text = models.TextField(
        'Описание'
    )
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[
            validators.MinValueValidator(
                COOKING_TIME_MIN,
                message='Минимум 1 минута'
            ),
            validators.MaxValueValidator(
                COOKING_TIME_MAX,
                message='Слишком долгое приготовление'
            )
        ]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор рецепта'
    )
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True
    )
    objects = RecipeQuerySet.as_manager()

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)
        constraints = [
            models.UniqueConstraint(
                fields=('author', 'name'),
                name='unique_dish'
            ),
        ]

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
        validators=[
            validators.MinValueValidator(
                INGREDIENT_AMOUNT_MIN,
                message='Минимальное количество - 1'
            ),
            validators.MaxValueValidator(
                INGREDIENT_AMOUNT_MAX,
                message='Максимальное количество - 32000'
            )
        ]
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        constraints = [
            models.UniqueConstraint(
                fields=['recipe', 'ingredient'],
                name='unique_ingredient'
            )
        ]

    def __str__(self):
        return f'{self.ingredient} ({self.amount}) в рецепте {self.recipe}'
