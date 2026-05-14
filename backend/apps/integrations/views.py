"""
Endpoints do fluxo OAuth Conta Azul.

  GET /api/integrations/contaazul/status      — status para o frontend
  GET /api/integrations/contaazul/authorize   — gera state e devolve URL pro consent
  GET /api/integrations/contaazul/callback    — Conta Azul redireciona com ?code & ?state
  POST /api/integrations/contaazul/disconnect — remove conexão (revoga local)
"""
from __future__ import annotations

import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ContaAzulConnection, OAuthState
from .services import ContaAzulOAuthService, OAuthError


def _serialize(conn: ContaAzulConnection) -> dict:
    return {
        "status": conn.status,
        "scope": conn.scope,
        "expires_at": conn.expires_at.isoformat() if conn.expires_at else None,
        "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
        "last_synced_at": (
            conn.last_synced_at.isoformat() if conn.last_synced_at else None
        ),
        "last_error": conn.last_error,
        "has_credentials": conn.has_credentials,
        "client_id": conn.client_id,  # NÃO sensível; o secret nunca é exposto
        "redirect_uri": settings.CONTA_AZUL["REDIRECT_URI"],
    }


class StatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.tenants.utils import get_request_tenant
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conn, _ = ContaAzulConnection.objects.get_or_create(tenant=tenant)
        return Response(_serialize(conn))


class AuthorizeView(APIView):
    """
    Gera um `state` opaco, persiste e devolve a URL onde o browser deve ir.
    O frontend recebe `{ url }` e faz `window.location.href = url`.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.tenants.utils import get_request_tenant
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        conn, _ = ContaAzulConnection.objects.get_or_create(tenant=tenant)

        state = secrets.token_urlsafe(32)
        OAuthState.objects.create(
            state=state,
            tenant=tenant,
            initiated_by_email=getattr(request.user, "email", "")[:254],
        )

        try:
            url = ContaAzulOAuthService.for_connection(conn).build_authorize_url(state=state)
        except OAuthError as e:
            return Response(
                {"error": {"code": "oauth_misconfigured", "message": str(e)}},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({"url": url, "state": state})


class CallbackView(APIView):
    """
    Endpoint público chamado pela Conta Azul após o consent.
    Recebe ?code= & ?state=, troca o code por tokens e redireciona o usuário
    para o frontend (`{FRONTEND_URL}/app/integrations?status=...`).
    """

    permission_classes = [AllowAny]

    def get(self, request: Request) -> HttpResponseRedirect:
        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        err = request.query_params.get("error", "")

        front = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        redirect_base = f"{front.rstrip('/')}/app/integrations"

        def _err(reason: str) -> str:
            return f"{redirect_base}?{urlencode({'status': 'error', 'reason': reason})}"

        if err:
            return HttpResponseRedirect(_err(err[:120]))
        if not code or not state:
            return HttpResponseRedirect(_err("missing_code_or_state"))

        try:
            oauth_state = OAuthState.objects.select_related("tenant").get(state=state)
        except OAuthState.DoesNotExist:
            return HttpResponseRedirect(_err("invalid_state"))

        if oauth_state.is_consumed() or oauth_state.is_expired():
            return HttpResponseRedirect(_err("state_expired_or_used"))

        tenant = oauth_state.tenant
        conn, _ = ContaAzulConnection.objects.get_or_create(tenant=tenant)

        try:
            tokens = ContaAzulOAuthService.for_connection(conn).exchange_code(code)
        except OAuthError as e:
            conn.mark_error(str(e))
            conn.save()
            return HttpResponseRedirect(_err("token_exchange_failed"))
        conn.set_access_token(tokens.access_token, expires_in=tokens.expires_in)
        if tokens.refresh_token:
            conn.set_refresh_token(tokens.refresh_token)
        conn.scope = tokens.scope
        conn.mark_connected()
        conn.save()

        oauth_state.consumed_at = timezone.now()
        oauth_state.save(update_fields=["consumed_at"])

        return HttpResponseRedirect(
            f"{redirect_base}?{urlencode({'status': 'connected'})}"
        )


class CredentialsView(APIView):
    """
    GET → devolve `{has_credentials, client_id, redirect_uri}` (secret nunca exposto).
    PUT → atualiza `client_id` + `client_secret`. Se a conexão estava conectada,
    revoga tokens locais (forçando re-auth com as novas credenciais).
    DELETE → remove credenciais (e revoga conexão).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        from apps.tenants.utils import get_request_tenant
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        conn, _ = ContaAzulConnection.objects.get_or_create(tenant=tenant)
        return Response({
            "has_credentials": conn.has_credentials,
            "client_id": conn.client_id,
            "redirect_uri": settings.CONTA_AZUL["REDIRECT_URI"],
        })

    def put(self, request: Request) -> Response:
        from apps.tenants.utils import get_request_tenant
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        client_id = (request.data.get("client_id") or "").strip()
        client_secret = (request.data.get("client_secret") or "").strip()

        if not client_id or not client_secret:
            return Response(
                {
                    "error": {
                        "code": "missing_fields",
                        "message": "client_id e client_secret são obrigatórios.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(client_id) > 255 or len(client_secret) > 500:
            return Response(
                {
                    "error": {
                        "code": "invalid_length",
                        "message": "Valor longo demais.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        conn, _ = ContaAzulConnection.objects.get_or_create(tenant=tenant)
        rotated = bool(conn.client_id and conn.client_id != client_id)

        conn.client_id = client_id
        conn.set_client_secret(client_secret)

        if rotated or conn.status == ContaAzulConnection.Status.CONNECTED:
            # se trocou as credenciais ou já estava conectado, tokens antigos
            # podem não funcionar — revogamos local para forçar reconectar
            conn.access_token_enc = ""
            conn.refresh_token_enc = ""
            conn.expires_at = None
            conn.status = ContaAzulConnection.Status.DISCONNECTED
            conn.last_error = ""
        conn.save()
        return Response({
            "has_credentials": conn.has_credentials,
            "client_id": conn.client_id,
            "redirect_uri": settings.CONTA_AZUL["REDIRECT_URI"],
        })

    def delete(self, request: Request) -> Response:
        from apps.tenants.utils import get_request_tenant
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            conn = ContaAzulConnection.objects.get(tenant=tenant)
        except ContaAzulConnection.DoesNotExist:
            return Response({"has_credentials": False})

        conn.client_id = ""
        conn.client_secret_enc = ""
        conn.access_token_enc = ""
        conn.refresh_token_enc = ""
        conn.expires_at = None
        conn.status = ContaAzulConnection.Status.DISCONNECTED
        conn.save()
        return Response({"has_credentials": False})


class DisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        from apps.tenants.utils import get_request_tenant
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            conn = ContaAzulConnection.objects.get(tenant=tenant)
        except ContaAzulConnection.DoesNotExist:
            return Response({"status": "disconnected"})

        conn.access_token_enc = ""
        conn.refresh_token_enc = ""
        conn.expires_at = None
        conn.status = ContaAzulConnection.Status.DISCONNECTED
        conn.last_error = ""
        conn.save()
        return Response(_serialize(conn))
