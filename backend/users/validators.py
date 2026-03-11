import re

from django.core.exceptions import ValidationError


def username_validator(value):
    allowed_chars = r'^[\w.@+-]+\Z'
    if not re.match(allowed_chars, value):
        invalid_chars = re.sub(allowed_chars, '', value)
        raise ValidationError(
            f'Недопустимые символы в имени пользователя: {invalid_chars}'
        )
    if value.lower() == 'me':
        raise ValidationError('Имя пользователя "me" запрещено.')
