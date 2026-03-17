class AllowedMethodsMixin:
    """Миксин для ограничения метода put."""

    http_method_names = ['get', 'post', 'patch', 'delete']
