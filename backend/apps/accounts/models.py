"""User custom + Membership (User ↔ Tenant com papel)."""
from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Manager custom: e-mail como identificador."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):  # type: ignore[no-untyped-def]
        if not email:
            raise ValueError("E-mail é obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[no-untyped-def]
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):  # type: ignore[no-untyped-def]
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser deve ter is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser deve ter is_superuser=True")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Usuário do sistema. Pode pertencer a múltiplos tenants via Membership."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        indexes = [models.Index(fields=["email"])]

    def __str__(self) -> str:
        return self.email


class Membership(models.Model):
    """Liga User a Tenant + papel."""

    class Role(models.TextChoices):
        OWNER = "owner", "Owner"
        ADMIN = "admin", "Admin"
        VIEWER = "viewer", "Viewer"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="memberships"
    )
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.OWNER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "tenant"], name="uniq_user_tenant"),
        ]
        indexes = [
            models.Index(fields=["tenant", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} @ {self.tenant.slug} ({self.role})"

    @property
    def is_owner(self) -> bool:
        return self.role == self.Role.OWNER
