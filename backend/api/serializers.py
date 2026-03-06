import base64

from django.core.files.base import ContentFile
from django.contrib.auth import (
    get_user_model,
    authenticate,
    update_session_auth_hash
)
from django.contrib.auth.password_validation import validate_password
from django.utils.text import slugify
from rest_framework import serializers, validators

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
    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'password', 'is_subscribed', 'avatar'
        )

    def get_image_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class TokenSerializer(serializers.Serializer):
    """
    Сериализатор для работы с отправкой токена.
    """

    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError(
                'Неверный email или пароль.'
            )
        return data


class AvatarSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с аватаркой.
    """

    avatar = Base64ImageField(required=False, allow_null=True)

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


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с ингридиентами.
    """
    amount = serializers.CharField() 

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


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
    ingredients = IngredientSerializer(required=True, many=True)
    tags = TagSerializer(required=True, many=True)
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('slug',)

    def validate(self, data):
        request = self.context.get('request')
        name = data.get('name', self.instance.name if self.instance else None)
        author = request.user
        recipe_id = self.instance.id if self.instance else None
        if Recipe.objects.filter(
            author=author, name=name
        ).exclude(id=recipe_id).exists():
            raise serializers.ValidationError(
                'У вас уже есть рецепт с таким названием!'
            )
        return data

    def process_relations(self, recipe, tags_data, ingredients_data):
        if ingredients_data is not None:
            IngredientRecipe.objects.filter(recipe=recipe).delete()
            ingredient_list = []
            for item in ingredients_data:
                raw_name = item.get('name')
                clean_name = raw_name.strip().lower() if raw_name else ''
                amount = item.get('amount')
                unit = item.get('measurement_unit')
                if not amount or str(amount).strip() == "":
                    raise serializers.ValidationError("Количество не может быть пустым")
                ingredient, created = Ingredient.objects.get_or_create(
                    name=clean_name,
                    defaults={'measurement_unit': unit}
                )
                ingredient_list.append(
                    IngredientRecipe(
                        recipe=recipe,
                        ingredient=ingredient,
                        amount=str(amount)
                    )
                )
            IngredientRecipe.objects.bulk_create(ingredient_list)

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self.process_relations(recipe, tags, ingredients)
        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        self.process_relations(instance, tags, ingredients)
        return instance
