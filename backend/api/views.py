from django.db.models import Sum
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response

from .base_entities import AllowedMethodsMixin
from .filters import RecipeFilter
from .permissions import (
    IsAdminOrReadOnly,
    IsAdminOrOwnerOrReadOnly,
    IsAdminOrReadAndCreateOnly
)
from .serializers import (
    AvatarSerializer,
    AppUserSerializer,
    PasswordSerializer,
    RecipeSerializer,
    RecipeShortSerializer,
    FollowSerializer,
    IngredientSerializer,
    TagSerializer
)

from recipes.models import (
    Recipe,
    Ingredient,
    Tag,
    Favorite,
    ShoppingCart,
    IngredientRecipe
)
from users.models import Follow

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для работы c пользователями.
    """

    queryset = User.objects.all()
    serializer_class = AppUserSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsAdminOrReadAndCreateOnly,)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                {
                    'email': user.email,
                    'id': user.id,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        detail=False,
        methods=['GET', 'PATCH'],
        permission_classes=[IsAuthenticated],
        url_path='me'
    )
    def me(self, request):
        if request.method == 'GET':
            serializer = self.serializer_class(
                request.user, context={'request': request}
            )
            return Response(serializer.data)
        else:
            instance = request.user
            serializer = self.serializer_class(
                instance,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['PUT', 'DELETE'],
        permission_classes=[IsAuthenticated, IsAdminOrOwnerOrReadOnly],
        url_path='me/avatar'
    )
    def avatar(self, request):
        instance = request.user
        if request.method == 'DELETE':
            default_storage.delete(instance.avatar.name)
            instance.avatar = None
            instance.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            serializer = AvatarSerializer(
                instance,
                data=request.data
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=[IsAuthenticated, IsAdminOrOwnerOrReadOnly],
        url_path='set_password'
    )
    def set_password(self, request):
        instance = request.user
        serializer = PasswordSerializer(
            instance,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
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
        methods=['POST', 'DELETE'],
        permission_classes=[IsAuthenticated],
        url_path='subscribe'
    )
    def subscribe(self, request, pk=None):
        user = request.user
        author = get_object_or_404(User, id=pk)
        if request.method == 'POST':
            if user == author:
                return Response(
                    'Нельзя подписаться на самого себя',
                    status=status.HTTP_400_BAD_REQUEST
                )
            if Follow.objects.filter(user=user, author=author).exists():
                return Response(
                    'Вы уже подписаны',
                    status=status.HTTP_400_BAD_REQUEST
                )
            Follow.objects.create(user=user, author=author)
            serializer = FollowSerializer(author, context={'request': request})
            return Response(serializer.data, status=201)
        if request.method == 'DELETE':
            subscription = Follow.objects.filter(user=user, author=author)
            if subscription.exists():
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                'Вы не подписаны на этого автора',
                status=status.HTTP_400_BAD_REQUEST
            )


class RecipeView(AllowedMethodsMixin, viewsets.ModelViewSet):
    """Вьюсет для работы с рецептами."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = (
        IsAdminOrOwnerOrReadOnly,
        IsAuthenticatedOrReadOnly,
    )
    pagination_class = LimitOffsetPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    filterset_class = RecipeFilter
    search_fields = ('name',)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _handle_relation(self, model, request, pk):
        user = request.user
        recipe = get_object_or_404(Recipe, id=pk)
        obj = model.objects.filter(user=user, recipe=recipe)
        if request.method == 'POST':
            if obj.exists():
                return Response(
                    'Уже добавлено',
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=user, recipe=recipe)
            return Response(
                RecipeShortSerializer(recipe).data,
                status=status.HTTP_201_CREATED)
        if obj.exists():
            obj.delete()
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
            'ingredient__name', 'ingredient__measurement_unit'
        ).annotate(total=Sum('amount')).order_by('ingredient__name')
        text = 'Список покупок:\n'
        for ingredient in ingredients:
            total = ingredient['total']
            amount = f'{total:g}' if total is not None else 'по вкусу'
            name = ingredient['ingredient__name']
            unit = ingredient['ingredient__measurement_unit']
            text += f'• {name} ({unit}) — {amount}\n'
        response = HttpResponse(
            text, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response


class IngredientView(viewsets.ReadOnlyModelViewSet):
    """Вьюсет для работы с ингридиентами."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = Ingredient.objects.all()
        name = self.request.query_params.get('name')
        if name:
            return queryset.filter(name__istartswith=name)
        return queryset


class TagView(viewsets.ModelViewSet):
    """Вьюсет для работы с тегами."""

    queryset = Tag.objects.all()
    permission_classes = (IsAdminOrReadOnly,)
    serializer_class = TagSerializer
    pagination_class = None
