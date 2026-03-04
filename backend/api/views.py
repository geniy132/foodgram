from django.contrib.auth import get_user_model, authenticate
from django.core.files.storage import default_storage
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import AccessToken

from .permissions import (
    CustomIsAuthenticated,
    IsAdminOrOwnerOrReadOnly,
    IsAdminOrReadAndCreateOnly
)
from .serializers import (
    AvatarSerializer,
    AppUserSerializer,
    TokenSerializer,
    PasswordSerializer
)
from users.models import BlacklistedToken

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
        permission_classes=[CustomIsAuthenticated],
        url_path='me'
    )
    def me(self, request):
        if request.method == 'GET':
            serializer = self.serializer_class(request.user)
            return Response(serializer.data)
        else:
            instance = request.user
            serializer = self.serializer_class(
                instance,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['PUT', 'DELETE'],
        permission_classes=[CustomIsAuthenticated, IsAdminOrOwnerOrReadOnly],
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
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=[CustomIsAuthenticated, IsAdminOrOwnerOrReadOnly],
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


class TokenView(
    viewsets.GenericViewSet,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin
):
    """
    Вьюсет для работы с токеном.
    """

    queryset = User.objects.all()
    serializer_class = TokenSerializer

    @action(
        detail=False,
        methods=['POST'],
        url_path='login'
    )
    def create_token(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = request.data.get('email')
        password = request.data.get('password')
        user = authenticate(email=email, password=password)
        access_token = AccessToken.for_user(user)
        return Response(
            {'access': str(access_token)},
            status=status.HTTP_200_OK
        )

    @action(
        detail=False,
        methods=['POST'],
        permission_classes=[CustomIsAuthenticated, IsAdminOrOwnerOrReadOnly],
        url_path='logout'
    )
    def delete_token(self, request, *args, **kwargs):
        token = request.auth
        if token:
            blacklisted_token = BlacklistedToken.objects.create(
                token=str(token)
            )
            blacklisted_token.save()
            return Response(status=status.HTTP_204_NO_CONTENT)
