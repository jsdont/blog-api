from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.auths.constants import NAME_MAX_LENGTH
from apps.auths.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=NAME_MAX_LENGTH)
    last_name = models.CharField(max_length=NAME_MAX_LENGTH)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    def clean(self) -> None:
        super().clean()
        self.email = User.objects.normalize_email(self.email)

    def __str__(self) -> str:
        return self.email
