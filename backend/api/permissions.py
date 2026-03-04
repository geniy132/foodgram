from rest_framework import permissions

from users.models import BlacklistedToken


class CustomIsAuthenticated(permissions.IsAuthenticated):
    """
    Переопределяем пермишн IsAuthenticated таким образом,
    чтобы он отсеивал токены из чёрного списка.
    """
    def has_permission(self, request, view):
        if super().has_permission(request, view):
            token = request.auth
            if token and not BlacklistedToken.objects.filter(
                token=str(token)
            ).exists():
                return True
        return False


class IsAdminOrReadAndCreateOnly(permissions.BasePermission):
    """
    Позволяет всем создавать пользователя и просматривать список
    пользователей. Остальные операции доступны только администратору.
    """
    def has_permission(self, request, view):
        return bool(
            request.method in ['GET', 'POST'] or request.user.is_staff
        )


class IsAdminOrOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение на уровне объекта.
    Позволяет редактировать или удалять объект только автору
    или администратору.
    """

    def has_object_permission(self, request, view, obj):
        return bool(
            request.method in permissions.SAFE_METHODS
            or (request.user and request.user.is_authenticated
                and (obj.author == request.user
                     or request.user.is_staff))
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешение на уровне объекта.
    Позволяет создавать или редактировать объект только администратору.
    """

    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or (request.user and request.user.is_authenticated
                and request.user.is_staff)
        )


class OnlyAdmin(permissions.BasePermission):
    """
    Разрешает все действия только роли администратору.
    """
    def has_permission(self, request, view):
        return request.user.is_staff
