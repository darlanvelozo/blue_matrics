from django.urls import path

from .views import (
    AuthorizeView,
    CallbackView,
    CredentialsView,
    DisconnectView,
    ExchangeCodeView,
    ManualTokenView,
    StatusView,
)

urlpatterns = [
    path("contaazul/status", StatusView.as_view(), name="contaazul-status"),
    path("contaazul/credentials", CredentialsView.as_view(), name="contaazul-credentials"),
    path("contaazul/authorize", AuthorizeView.as_view(), name="contaazul-authorize"),
    path("contaazul/callback", CallbackView.as_view(), name="contaazul-callback"),
    path(
        "contaazul/exchange-code",
        ExchangeCodeView.as_view(),
        name="contaazul-exchange-code",
    ),
    path(
        "contaazul/manual-token",
        ManualTokenView.as_view(),
        name="contaazul-manual-token",
    ),
    path("contaazul/disconnect", DisconnectView.as_view(), name="contaazul-disconnect"),
]
