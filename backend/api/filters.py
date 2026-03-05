from django_filters import rest_framework as filters


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.NumberFilter(
        method='filter_is_favorited'
    )
    is_in_shopping_cart = filters.NumberFilter(
        method='filter_is_in_shopping_cart'
    )
    author = filters.NumberFilter(field_name='author__id', lookup_expr='exact')
    tags = filters.CharFilter(field_name='tags__slug', lookup_expr='exact')

    def filter_is_favorited(self, queryset, name, value):
        return queryset.filter(is_favorited=bool(int(value)))

    def filter_is_in_shopping_cart(self, queryset, name, value):
        return queryset.filter(is_in_shopping_cart=bool(int(value)))
