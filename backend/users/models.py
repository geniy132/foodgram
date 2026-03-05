from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import (
    EMAIL_MAX_LENGTH,
    SHORT_NAME_LENGTH,
    USER_NAME_MAX_LENGTH,
    TOKEN_MAX_LENGTH
)
from .validators import username_validator


class AppUser(AbstractUser):
    """Кастомная модель пользователя."""

    email = models.EmailField(
        'Электронная почта',
        unique=True,
        max_length=EMAIL_MAX_LENGTH
    )
    username = models.SlugField(
        'Имя пользователя',
        unique=True,
        max_length=USER_NAME_MAX_LENGTH,
        validators=[username_validator]
    )
    is_subscribed = models.BooleanField(
        'Подписан',
        default=False,
        blank=True
    )
    avatar = models.ImageField(
        'Аватарка',
        upload_to='images/avatars/',
        null=True,
        default=None
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username[:SHORT_NAME_LENGTH]


class BlacklistedToken(models.Model):
    """Модель "черного списка" токенов."""

    token = models.CharField('Токен', max_length=TOKEN_MAX_LENGTH)
    blacklist_time = models.DateTimeField('Время удаления', auto_now_add=True)

    class Meta:
        verbose_name = 'токен'
        verbose_name_plural = 'Токены'
        ordering = ('-blacklist_time',)

    def __str__(self):
        return self.token
