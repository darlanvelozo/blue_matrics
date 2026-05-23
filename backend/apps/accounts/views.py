"""Views de auth: register, login, refresh, me, password reset."""
from __future__ import annotations

import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.notifications.mailer import send_password_reset, send_welcome
from apps.security.models import AuditAction, log_action
from apps.security.rate_limit import rate_limit

from .models import User
from .serializers import (
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UserSerializer,
    tokens_for_user,
)

logger = logging.getLogger(__name__)

PASSWORD_RESET_TTL_MINUTES = 60  # alinhado com PASSWORD_RESET_TIMEOUT padrão do Django


class RegisterView(APIView):
    permission_classes = [AllowAny]

    @rate_limit(key_prefix="auth-register", limit=5, window_seconds=300)
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        user = result["user"]
        tenant = result["tenant"]
        tokens = tokens_for_user(user)

        log_action(
            action=AuditAction.REGISTER,
            actor=user, tenant=tenant,
            metadata={"company": tenant.name},
            request=request,
        )

        send_welcome(
            to=user.email,
            name=(user.full_name or user.email.split("@")[0]),
            tenant_name=tenant.name,
        )

        return Response(
            {
                "user": UserSerializer(user).data,
                "tenant": {
                    "public_id": str(tenant.public_id),
                    "name": tenant.name,
                    "slug": tenant.slug,
                    "status": tenant.status,
                    "trial_ends_at": (
                        tenant.trial_ends_at.isoformat() if tenant.trial_ends_at else None
                    ),
                },
                "tokens": tokens,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    @rate_limit(key_prefix="auth-login", limit=10, window_seconds=60)
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tokens = tokens_for_user(user)
        log_action(action=AuditAction.LOGIN, actor=user, request=request)
        return Response(
            {"user": UserSerializer(user).data, "tokens": tokens},
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return Response(UserSerializer(request.user).data)


class PasswordResetRequestView(APIView):
    """
    Recebe email, gera token e dispara e-mail. Sempre responde 200 — não revela
    se a conta existe (proteção contra user enumeration).
    """

    permission_classes = [AllowAny]

    @rate_limit(key_prefix="auth-pwd-reset", limit=5, window_seconds=900)
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user is not None:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_url = (
                f"{settings.FRONTEND_URL.rstrip('/')}/reset-password"
                f"?uid={uid}&token={token}"
            )
            send_password_reset(
                to=user.email,
                name=(user.full_name or user.email.split("@")[0]),
                reset_url=reset_url,
                ttl_minutes=PASSWORD_RESET_TTL_MINUTES,
            )
            log_action(
                action=AuditAction.PASSWORD_RESET_REQUEST,
                actor=user,
                request=request,
            )
        else:
            # Log silencioso pra detectar abuse, mas não delata pro caller
            logger.info("password reset solicitado para email inexistente: %s", email)

        return Response(
            {"detail": "Se a conta existir, um link de redefinição foi enviado."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Valida uid+token e troca a senha. Resposta 400 se inválido/expirado."""

    permission_classes = [AllowAny]

    @rate_limit(key_prefix="auth-pwd-confirm", limit=10, window_seconds=900)
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_pk = int(force_str(urlsafe_base64_decode(uid)))
            user = User.objects.get(pk=user_pk, is_active=True)
        except (ValueError, TypeError, User.DoesNotExist):
            return Response(
                {"error": {"code": "invalid_token", "message": "Link inválido ou expirado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, token):
            return Response(
                {"error": {"code": "invalid_token", "message": "Link inválido ou expirado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        log_action(
            action=AuditAction.PASSWORD_RESET_CONFIRM,
            actor=user,
            request=request,
        )
        return Response({"detail": "Senha alterada com sucesso."}, status=status.HTTP_200_OK)


# Re-exporta refresh do SimpleJWT
__all__ = [
    "RegisterView", "LoginView", "MeView", "TokenRefreshView",
    "PasswordResetRequestView", "PasswordResetConfirmView",
]
