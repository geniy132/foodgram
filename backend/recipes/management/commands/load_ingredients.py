import json

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    def handle(self, *args, **options):
        path = 'data/ingredients.json'
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        Ingredient.objects.bulk_create(
            [Ingredient(**item) for item in data],
            ignore_conflicts=True
        )
        self.stdout.write(self.style.SUCCESS('Ингредиенты загружены!'))
