"""
Mailer centralizado. Toda mensagem transacional do BI AZUL passa por aqui.

- Usa o EMAIL_BACKEND configurado (SMTP em prod, console em dev).
- Falhas são logadas mas NÃO propagam — operação principal (signup, password reset)
  não pode quebrar por causa de email travado.
- Templates em texto puro: simples, legíveis no inbox, sem render Jinja
  enquanto o volume não justifica.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailResult:
    sent: bool
    error: str | None = None


def _send(subject: str, body_text: str, to: str, *, body_html: str | None = None) -> EmailResult:
    if not to:
        return EmailResult(sent=False, error="empty recipient")
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=body_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to],
        )
        if body_html:
            msg.attach_alternative(body_html, "text/html")
        msg.send(fail_silently=False)
        return EmailResult(sent=True)
    except Exception as e:  # noqa: BLE001 — captura tudo para não derrubar o caller
        logger.warning("mailer falhou (to=%s, subj=%r): %s", to, subject, e)
        return EmailResult(sent=False, error=str(e))


def send_welcome(*, to: str, name: str, tenant_name: str) -> EmailResult:
    subject = "Bem-vindo(a) ao BI AZUL"
    body = (
        f"Olá {name},\n\n"
        f"Sua conta no BI AZUL foi criada — empresa: {tenant_name}.\n\n"
        "Próximos passos:\n"
        f"  1. Acesse {settings.FRONTEND_URL}/app/integrations e conecte sua Conta Azul.\n"
        "  2. Aguarde a primeira sincronização (~2 min para empresas pequenas).\n"
        "  3. Faça sua primeira pergunta para o Analista IA em /app/ai.\n\n"
        "Você tem 7 dias de trial. Qualquer dúvida, responda este e-mail.\n\n"
        "— Equipe BI AZUL"
    )
    return _send(subject, body, to)


def send_password_reset(*, to: str, name: str, reset_url: str, ttl_minutes: int) -> EmailResult:
    subject = "Redefinir sua senha — BI AZUL"
    body = (
        f"Olá {name},\n\n"
        "Recebemos um pedido de redefinição de senha para sua conta.\n\n"
        f"Para criar uma senha nova, clique no link abaixo (válido por {ttl_minutes} minutos):\n\n"
        f"{reset_url}\n\n"
        "Se você não fez essa solicitação, ignore este e-mail — sua senha atual continua valendo.\n\n"
        "— Equipe BI AZUL"
    )
    return _send(subject, body, to)


def send_payment_failed(*, to: str, name: str, amount: str, retry_url: str) -> EmailResult:
    subject = "Falha no pagamento — BI AZUL"
    body = (
        f"Olá {name},\n\n"
        f"Não conseguimos processar o pagamento de {amount} da sua assinatura BI AZUL.\n\n"
        "Sua conta continua ativa por alguns dias enquanto tentamos novamente. "
        "Para evitar a suspensão, atualize seu método de pagamento:\n\n"
        f"{retry_url}\n\n"
        "Precisa de ajuda? Responda este e-mail.\n\n"
        "— Equipe BI AZUL"
    )
    return _send(subject, body, to)


def send_trial_ending(*, to: str, name: str, days_left: int, billing_url: str) -> EmailResult:
    subject = f"Seu trial termina em {days_left} dias — BI AZUL"
    body = (
        f"Olá {name},\n\n"
        f"Seu trial do BI AZUL termina em {days_left} dia(s).\n\n"
        "Se quiser manter o acesso completo (todos os dashboards, Analista IA, "
        "sincronização Conta Azul), escolha seu plano:\n\n"
        f"  • Mensal — R$ 499/mês\n"
        f"  • Anual — R$ 4.499/ano (~25% off, equivale a R$ 374,92/mês)\n\n"
        f"Assinar: {billing_url}\n\n"
        "— Equipe BI AZUL"
    )
    return _send(subject, body, to)
