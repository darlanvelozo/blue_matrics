"""
Endpoints REST para gerenciar o histórico do chat IA.

- GET    /api/insights/chats               → lista conversas do usuário
- POST   /api/insights/chats               → cria conversa nova (vazia)
- GET    /api/insights/chats/<id>          → recupera mensagens da conversa
- PATCH  /api/insights/chats/<id>          → renomeia ({title})
- DELETE /api/insights/chats/<id>          → apaga conversa + mensagens

Cada conversa é escopada por (tenant, user) — o usuário só vê as próprias.
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.utils import get_request_tenant

from .models import ChatMessage, ChatSession


def _serialize_session(s: ChatSession, *, with_messages: bool = False) -> dict:
    data: dict = {
        "id": s.id,
        "title": s.title,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
        "message_count": s.messages.count(),
    }
    if with_messages:
        data["messages"] = [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "blueprint": m.blueprint,
                "tools_called": m.tools_called,
                "used_llm": m.used_llm,
                "llm_provider": m.llm_provider,
                "llm_error": m.llm_error or None,
                "created_at": m.created_at.isoformat(),
            }
            for m in s.messages.order_by("created_at")
        ]
    return data


class ChatSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        qs = ChatSession.objects.filter(
            tenant=tenant, user=request.user,
        ).order_by("-updated_at")[:100]
        return Response({"sessions": [_serialize_session(s) for s in qs]})

    def post(self, request: Request) -> Response:
        """Cria uma sessão vazia (usado pelo botão 'Nova conversa')."""
        tenant = get_request_tenant(request)
        if tenant is None:
            return Response(
                {"error": {"code": "no_tenant", "message": "Tenant não encontrado."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        title = (request.data.get("title") or "Nova conversa").strip()[:200]
        session = ChatSession.objects.create(
            tenant=tenant, user=request.user, title=title,
        )
        return Response(_serialize_session(session), status=status.HTTP_201_CREATED)


class ChatSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, request: Request, pk: int) -> ChatSession | None:
        tenant = get_request_tenant(request)
        if tenant is None:
            return None
        return ChatSession.objects.filter(
            pk=pk, tenant=tenant, user=request.user,
        ).first()

    def get(self, request: Request, pk: int) -> Response:
        session = self._get(request, pk)
        if session is None:
            return Response(
                {"error": {"code": "not_found", "message": "Conversa não encontrada."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(_serialize_session(session, with_messages=True))

    def patch(self, request: Request, pk: int) -> Response:
        session = self._get(request, pk)
        if session is None:
            return Response(
                {"error": {"code": "not_found", "message": "Conversa não encontrada."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        title = request.data.get("title")
        if title is not None:
            session.title = (title or "").strip()[:200] or "Nova conversa"
            session.save(update_fields=["title", "updated_at"])
        return Response(_serialize_session(session))

    def delete(self, request: Request, pk: int) -> Response:
        session = self._get(request, pk)
        if session is None:
            return Response(
                {"error": {"code": "not_found", "message": "Conversa não encontrada."}},
                status=status.HTTP_404_NOT_FOUND,
            )
        session.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
