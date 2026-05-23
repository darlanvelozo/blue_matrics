"""Serializers de auth."""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenants.models import Tenant

from .models import Membership, User


def _build_unique_slug(base: str) -> str:
    base = slugify(base) or "empresa"
    slug = base
    i = 1
    while Tenant.objects.filter(slug=slug).exists():
        i += 1
        slug = f"{base}-{i}"
    return slug


def _trial_days() -> int:
    return 7  # configurável depois


def tokens_for_user(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class RegisterSerializer(serializers.Serializer):
    """Cria User + Tenant + Membership(owner) em uma transação."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    company_name = serializers.CharField(max_length=200)

    def validate_email(self, value: str) -> str:
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return value.lower()

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    @transaction.atomic
    def create(self, validated_data: dict) -> dict:
        company = validated_data["company_name"]
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            full_name=validated_data.get("full_name", ""),
        )
        from datetime import timedelta
        tenant = Tenant.objects.create(
            name=company,
            slug=_build_unique_slug(company),
            status=Tenant.Status.TRIAL,
            trial_ends_at=timezone.now() + timedelta(days=_trial_days()),
        )
        Membership.objects.create(
            user=user,
            tenant=tenant,
            role=Membership.Role.OWNER,
            is_active=True,
        )
        return {"user": user, "tenant": tenant}


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs: dict) -> dict:
        user = authenticate(
            request=self.context.get("request"),
            username=attrs["email"].lower(),
            password=attrs["password"],
        )
        if user is None or not user.is_active:
            raise serializers.ValidationError(
                {"email": "Credenciais inválidas."}
            )
        attrs["user"] = user
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """Recebe e-mail, retorna sempre 200 (não revela se conta existe)."""
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Valida uid + token (PasswordResetTokenGenerator do Django) e troca a senha."""
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_new_password(self, value: str) -> str:
        validate_password(value)
        return value


class UserSerializer(serializers.ModelSerializer):
    tenant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("public_id", "email", "full_name", "is_staff", "tenant")
        read_only_fields = fields

    def get_tenant(self, user: User) -> dict | None:
        membership = (
            user.memberships.select_related("tenant")
            .filter(is_active=True)
            .order_by("-is_owner" if False else "-created_at")
            .first()
        )
        if not membership:
            return None
        t = membership.tenant
        return {
            "public_id": str(t.public_id),
            "name": t.name,
            "slug": t.slug,
            "status": t.status,
            "trial_ends_at": t.trial_ends_at.isoformat() if t.trial_ends_at else None,
            "role": membership.role,
        }
