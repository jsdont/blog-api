from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager

if TYPE_CHECKING:
    from apps.auths.models import User


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email: str) -> str:
        return super().normalize_email(email.strip()).lower()

    def get_by_natural_key(self, username: str) -> User:
        return self.get(email=self.normalize_email(username))

    def create_user(
        self,
        email: str,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        **extra_fields: Any,
    ) -> User:
        if not email or not email.strip():
            raise ValueError("Email is required.")
        if not first_name.strip() or not last_name.strip():
            raise ValueError("First name and last name are required.")

        user = self.model(
            email=self.normalize_email(email),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            **extra_fields,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        first_name: str = "",
        last_name: str = "",
        **extra_fields: Any,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields["is_staff"] is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields["is_superuser"] is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            **extra_fields,
        )
