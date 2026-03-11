from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import (
    EMAIL_MAX_LENGTH,
    SHORT_NAME_LENGTH,
    USER_NAME_MAX_LENGTH,
)
from .validators import username_validator


class AppUser(AbstractUser):
    """Кастомная модель пользователя."""

    email = models.EmailField(
        'Электронная почта',
        unique=True,
        max_length=EMAIL_MAX_LENGTH
    )
    username = models.CharField(
        'Имя пользователя',
        unique=True,
        max_length=USER_NAME_MAX_LENGTH,
        validators=[username_validator]
    )
    avatar = models.ImageField(
        'Аватарка',
        upload_to='images/avatars/',
        null=True,
        blank=True,
        default=None
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        return self.username[:SHORT_NAME_LENGTH]


class Follow(models.Model):
    """Модель подписок."""

    user = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name='follower'
    )
    author = models.ForeignKey(
        AppUser, on_delete=models.CASCADE, related_name='following'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_follow'
            ),
            models.CheckConstraint(
                condition=~models.Q(user=models.F('author')),
                name='no_self_follow'
            )
        ]
