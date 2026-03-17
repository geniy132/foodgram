from django.contrib.auth import get_user_model
from django.db import transaction
from djoser.serializers import UserSerializer
from rest_framework import serializers, validators

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag

from .fields import Base64ImageField

User = get_user_model()


class AppUserSerializer(UserSerializer):
    """
    Сериализатор для работы с пользователями.
    """

    avatar = serializers.SerializerMethodField('get_image_url', read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        return (
            request is not None
            and request.user.is_authenticated
            and request.user != obj
            and request.user.follower.filter(author=obj).exists()
        )

    def get_image_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )


class AvatarSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с аватаркой.
    """

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ['avatar']


class FollowSerializer(AppUserSerializer):
    """Сериализатор для вывода подписок (автор + его рецепты)."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.ReadOnlyField(source='recipes.count')

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar',
            'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit') if request else None
        queryset = obj.recipes.all()
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except (ValueError, TypeError):
                pass
        return RecipeShortSerializer(queryset, many=True).data


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра списка ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для связи ингредиента и рецепта.
    """

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с тегами.
    """

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeBaseSerializer(serializers.ModelSerializer):
    """Базовый класс сериализатора для работы с рецептами."""

    author = AppUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientRecipeSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )
    image = Base64ImageField()
    is_favorited = serializers.BooleanField(
        read_only=True,
        default=False
    )
    is_in_shopping_cart = serializers.BooleanField(
        read_only=True,
        default=False
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )


class RecipeReadSerializer(RecipeBaseSerializer):
    """
    Сериализатор только для чтения,
    использует поля и настройки из RecipeBaseSerializer.
    """


class RecipeWriteSerializer(RecipeBaseSerializer):
    """Сериализатор для записи."""

    author = serializers.HiddenField(default=serializers.CurrentUserDefault())
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=True,
        allow_empty=False
    )
    ingredients = IngredientRecipeSerializer(
        source='recipe_ingredients',
        many=True,
        required=True,
        allow_empty=False
    )

    class Meta(RecipeBaseSerializer.Meta):
        validators = [
            validators.UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=['author', 'name'],
                message='У вас уже есть рецепт с таким названием!'
            )
        ]

    def validate(self, data):
        tags = self.initial_data.get('tags')
        ingredients = self.initial_data.get('ingredients')
        if not tags or not ingredients:
            raise serializers.ValidationError('Поля обязательны!')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги повторяются!')
        ingredient_ids = [ingredient.get('id') for ingredient
                          in ingredients if ingredient.get('id')]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError('Ингредиенты повторяются!')
        return data

    def process_ingredients(self, recipe, ingredients_data):
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients_data
        ])

    @transaction.atomic
    def create(self, validated_data):
        author = validated_data.pop('author')
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        self.process_ingredients(recipe, ingredients)
        return recipe

    @transaction.atomic
    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('recipe_ingredients', None)
        validated_data.pop('author', None)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.process_ingredients(instance, ingredients)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого отображения рецепта
    в списках покупок, избранном и подписках.
    """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('__all__',)
