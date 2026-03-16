import base64

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.files.base import ContentFile
from rest_framework import serializers, validators

from recipes.models import Ingredient, IngredientRecipe, Recipe, Tag

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

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(min_value=1)

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


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с рецептами.
    """

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
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart',
                  'name', 'image', 'text', 'cooking_time')
        validators = [
            validators.UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=['author', 'name'],
                message='У вас уже есть рецепт с таким названием!'
            )
        ]

    def get_ingredients(self, obj):
        return IngredientRecipeSerializer(
            obj.recipe_ingredients.all(), many=True
        ).data

    def validate(self, data):
        data['author'] = self.context.get('request').user
        tags = self.initial_data.get('tags')
        ingredients = self.initial_data.get('ingredients')
        if not tags or not ingredients:
            raise serializers.ValidationError(
                'Поля тегов и ингредиентов обязательны!'
            )
        if tags and len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги не должны повторяться!')
        ingredient_ids = [ingredient.get('id') for ingredient in ingredients
                          if ingredient.get('id')]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError('Ингредиенты повторяются!')
        return data

    def process_ingredients(self, recipe, ingredients_data):
        IngredientRecipe.objects.filter(recipe=recipe).delete()
        IngredientRecipe.objects.bulk_create([
            IngredientRecipe(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients_data
        ])

    def create(self, validated_data):
        author = validated_data.pop('author')
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('recipe_ingredients')
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        self.process_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('recipe_ingredients', None)
        validated_data.pop('author', None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
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

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['author'] = AppUserSerializer(
            instance.author,
            context=self.context
        ).data
        representation['tags'] = TagSerializer(
            instance.tags.all(),
            many=True
        ).data
        return representation


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого отображения рецепта
    в списках покупок, избранном и подписках.
    """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('__all__',)
