from django.db import models
from pytils.translit import slugify


class SlugModelMixin(models.Model):

    class Meta:
        abstract = True

    def get_slug_content(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            max_slug_length = self._meta.get_field('slug').max_length
            self.slug = slugify(self.get_slug_content())[:max_slug_length]
        super().save(*args, **kwargs)
