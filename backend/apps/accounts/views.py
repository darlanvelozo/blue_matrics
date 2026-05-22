"""Views de auth: register, login, refresh, me."""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenRefreshView

from apps.security.models import AuditAction, log_action
from apps.security.rate_limit import rate_limit

from .serializers import (
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
    tokens_for_user,
)


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


# Re-exporta refresh do SimpleJWT
__all__ = ["RegisterView", "LoginView", "MeView", "TokenRefreshView"]
