import base64

from django.core.files.base import ContentFile
from django.contrib.auth import (
    get_user_model,
    update_session_auth_hash
)
from django.contrib.auth.password_validation import validate_password
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from recipes.models import Recipe, Ingredient, Tag, IngredientRecipe

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class AppUserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с пользователями.
    """

    avatar = serializers.SerializerMethodField('get_image_url', read_only=True)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    is_subscribed = serializers.SerializerMethodField()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user.is_anonymous or user == obj:
            return False
        return user.follower.filter(author=obj).exists()

    def get_image_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'password', 'is_subscribed', 'avatar'
        )
        extra_kwargs = {'password': {'write_only': True, 'required': True}}


class AvatarSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с аватаркой.
    """

    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ['avatar']


class PasswordSerializer(serializers.Serializer):
    """
    Сериализатор для работы с паролем.
    """

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, data):
        password = data['current_password']
        user = self.context['request'].user
        if not user.check_password(password):
            raise serializers.ValidationError(
                {'current_password': 'Неверный старый пароль.'}
            )
        return data

    def update(self, instance, validated_data):
        instance.set_password(validated_data['new_password'])
        instance.save()
        update_session_auth_hash(self.context['request'], instance)
        return instance


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
        limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all()
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except (ValueError, TypeError):
                pass
        return RecipeShortSerializer(queryset, many=True).data


class IngredientSerializer(serializers.ModelSerializer):
    """Для просмотра списка ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientRecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для связи ингредиента и рецепта.
    """

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = IngredientRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def to_internal_value(self, data):
        amount = data.get('amount')
        if amount == 'по вкусу' or not amount:
            data['amount'] = 0
        return super().to_internal_value(data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        if not instance.amount:
            representation['amount'] = 'по вкусу'
            representation['measurement_unit'] = ''
        return representation


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с тегами.
    """

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')

    def to_internal_value(self, data):
        if isinstance(data, int):
            try:
                return Tag.objects.get(id=data)
            except Tag.DoesNotExist:
                raise serializers.ValidationError(
                    'Тег с указанным ID не найден.'
                )
        return super().to_internal_value(data)


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с рецептами.
    """

    author = AppUserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')

    def get_ingredients(self, obj):
        return IngredientRecipeSerializer(
            obj.recipe_ingredients.all(), many=True
        ).data

    def validate(self, data):
        request = self.context.get('request')
        tags = self.initial_data.get('tags')
        ingredients = self.initial_data.get('ingredients')
        if not tags or not ingredients:
            raise serializers.ValidationError('Заполните все поля')
        if Tag.objects.filter(id__in=tags).count() != len(set(tags)):
            raise serializers.ValidationError('Указан несуществующий тег!')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги не должны повторяться!')
        ingredients_ids = [
            item.get('id') for item in ingredients if item.get('id')
        ]
        if len(ingredients_ids) != len(set(ingredients_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться!'
            )
        name = data.get('name')
        if Recipe.objects.filter(author=request.user, name=name).exclude(
            id=self.instance.id if self.instance else None
        ).exists():
            raise serializers.ValidationError('У вас уже есть такой рецепт')
        data['ingredients'] = ingredients
        return data

    def process_ingredients(self, recipe, ingredients):
        IngredientRecipe.objects.filter(recipe=recipe).delete()
        ingredient_list = []
        for item in ingredients:
            amount = item.get('amount')
            if amount == 'по вкусу' or not amount:
                amount = 0
            ingredient_list.append(IngredientRecipe(
                recipe=recipe,
                ingredient=get_object_or_404(Ingredient, id=item.get('id')),
                amount=int(amount)
            ))
        IngredientRecipe.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = self.initial_data.get('tags')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.process_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients', None)
        tags = self.initial_data.get('tags')
        instance = super().update(instance, validated_data)
        if tags:
            instance.tags.set(tags)
        if ingredients:
            self.process_ingredients(instance, ingredients)
        return instance

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and user.favorites.filter(recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and user.shopping_cart.filter(recipe=obj).exists()
        )


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого отображения рецепта
    в списках покупок, избранном и подписках.
    """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('__all__',)
