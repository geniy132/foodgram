from django.views.generic.base import RedirectView

from .models import Recipe


class ShortLinkRedirectView(RedirectView):
    """Перенаправление с короткой ссылки на страницу рецепта."""

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        recipe_id = kwargs.get('pk')
        try:
            Recipe.objects.get(pk=recipe_id)
            return f'/recipes/{recipe_id}/'
        except Recipe.DoesNotExist:
            return '/not-found/'
