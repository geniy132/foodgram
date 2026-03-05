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

from recipes.models import Recipe, Ingridient, Tag, IngridientRecipe

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


class IngridientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для работы с ингридиентами.
    """

    ingridient_name = serializers.CharField(source='name')

    class Meta:
        model = Ingridient
        fields = ('id', 'ingridient_name')


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

    ingridients = IngridientSerializer(required=True, many=True)
    itags = TagSerializer(required=True, many=True)
    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        model = Recipe
        fields = (
            'ingridients', 'tags', 'image', 'name', 'text',
            'cooking_time'
        )
        read_only_fields = ('author', 'slug',)

        validators = [
            validators.UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=('author', 'name')
            )
        ]

    def create(self, validated_data):
        ingridients = validated_data.pop('ingridients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        for ingridient in ingridients:
            current_ingridient, status = Ingridient.objects.get_or_create(
                **ingridient
            )
            IngridientRecipe.objects.create(
                recipe=recipe,
                ingridient=current_ingridient
            )

        for tag in tags:
            current_tag, _ = Tag.objects.get_or_create(**tag)
            recipe.tags.add(current_tag)

        return recipe

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.text = validated_data.get('text', instance.text)
        instance.cooking_time = validated_data.get(
            'cooking_time', instance.cooking_time
        )
        instance.image = validated_data.get('image', instance.image)

        ingridients_data = validated_data.pop('ingridients')
        tags_data = validated_data.pop('tags')

        instance.ingridients.clear()
        instance.tags.clear()
        for ingridient_data in ingridients_data:
            current_ingridient, status = Ingridient.objects.get_or_create(
                **ingridient_data
            )
            IngridientRecipe.objects.create(
                recipe=instance,
                ingridient=current_ingridient
            )
        for tag_data in tags_data:
            tag, status = Tag.objects.get_or_create(**tag_data)
            instance.tags.add(tag)
        instance.save()
        return instance
