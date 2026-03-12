from rest_framework import permissions


class IsAdminOrReadAndCreateOnly(permissions.BasePermission):
    """
    Разрешает только ['GET', 'POST'].
    Остальные операции доступны только администратору.
    """

    def has_permission(self, request, view):
        return bool(
            request.method in ['GET', 'POST'] or request.user.is_staff
        )


class IsAdminOrOwnerOrReadOnly(permissions.BasePermission):
    """
    Разрешение на уровне объекта: вносить изменения в базу
    может автор или администратор.
    """

    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_staff
            or obj.author == request.user
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Разрешение на уровне объекта: вносить изменения в базу
    может только администратор.
    """

    def has_permission(self, request, view):
        return bool(
            request.method in permissions.SAFE_METHODS
            or (request.user and request.user.is_authenticated
                and request.user.is_staff)
        )
