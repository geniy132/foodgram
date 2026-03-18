from django.contrib.auth import get_user_model
from django.db import models
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters import rest_framework
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from recipes.models import (
    Favorite,
    Ingredient,
    IngredientRecipe,
    Recipe,
    ShoppingCart,
    Tag
)
from users.models import Follow

from .base_entities import AllowedMethodsMixin
from .filters import RecipeFilter, IngredientFilter
from .permissions import IsAuthorOrReadOnly
from .serializers import (
    AppUserSerializer,
    AvatarSerializer,
    FollowSerializer,
    IngredientSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    RecipeShortSerializer,
    TagSerializer
)

User = get_user_model()


class UserViewSet(DjoserUserViewSet):
    """
    Вьюсет для работы c пользователями.
    """

    queryset = User.objects.all()
    serializer_class = AppUserSerializer
    pagination_class = LimitOffsetPagination

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated],
        url_path='me'
    )
    def me(self, request):
        serializer = self.serializer_class(
            request.user, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['PUT'],
        permission_classes=[IsAuthenticated],
        url_path='me/avatar'
    )
    def avatar(self, request):
        serializer = AvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions'
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = FollowSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)
        serializer = FollowSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['POST'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        if user == author:
            return Response(
                'Нельзя подписаться на самого себя',
                status=status.HTTP_400_BAD_REQUEST
            )
        created, _ = Follow.objects.get_or_create(
            user=user,
            author=author
        )
        if not created:
            return Response(
                'Вы уже подписаны',
                status=status.HTTP_400_BAD_REQUEST
            )
        serializer = FollowSerializer(author, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def unsubscribe(self, request, id=None):
        user = request.user
        author = get_object_or_404(User, id=id)
        count, _ = Follow.objects.filter(user=user, author=author).delete()
        if count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            'Вы не подписаны на этого автора',
            status=status.HTTP_400_BAD_REQUEST
        )


class RecipeView(AllowedMethodsMixin, viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""

    permission_classes = (IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly,)
    pagination_class = LimitOffsetPagination
    filter_backends = (
        rest_framework.DjangoFilterBackend,
        filters.SearchFilter
    )
    filterset_class = RecipeFilter
    search_fields = ('name',)

    def get_queryset(self):
        return (
            Recipe.objects
            .select_related('author')
            .prefetch_related('tags', 'recipe_ingredients__ingredient')
            .add_user_annotations(self.request.user)
        )

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def _handle_relation(self, model, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        if request.method == 'POST':
            created, _ = model.objects.get_or_create(
                user=user, recipe=recipe
            )
            if not created:
                return Response(
                    'Уже добавлено',
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(
                RecipeShortSerializer(recipe).data,
                status=status.HTTP_201_CREATED
            )
        count, _ = model.objects.filter(user=user, recipe=recipe).delete()
        if count:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            'Объекта нет в списке',
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=True,
        methods=['GET'],
        url_path='get-link'
    )
    def get_link(self, request, pk=None):
        short_url = request.build_absolute_uri(f'/s/{pk}/')
        return Response({'short-link': short_url})

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='favorite'
    )
    def favorite(self, request, pk=None):
        return self._handle_relation(Favorite, request, pk)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='shopping_cart'
    )
    def shopping_cart(self, request, pk=None):
        return self._handle_relation(ShoppingCart, request, pk)

    @action(
        detail=False,
        methods=['GET'],
        permission_classes=[IsAuthenticated],
        url_path='download_shopping_cart'
    )
    def download_shopping_cart(self, request):
        ingredients = IngredientRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total=models.Sum('amount')).order_by('ingredient__name')
        text = 'Список покупок:\n\n'
        for ingredient in ingredients:
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['total']
            text += f'• {name} — {amount:g} {unit}\n'
        response = HttpResponse(
            text, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class IngredientView(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с ингредиентами."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None
    filter_backends = (rest_framework.DjangoFilterBackend,)
    filterset_class = IngredientFilter


class TagView(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с тегами."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
