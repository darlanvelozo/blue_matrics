from django.urls import path

from .views import (
    AuthorizeView,
    CallbackView,
    CredentialsView,
    DisconnectView,
    StatusView,
)

urlpatterns = [
    path("contaazul/status", StatusView.as_view(), name="contaazul-status"),
    path("contaazul/credentials", CredentialsView.as_view(), name="contaazul-credentials"),
    path("contaazul/authorize", AuthorizeView.as_view(), name="contaazul-authorize"),
    path("contaazul/callback", CallbackView.as_view(), name="contaazul-callback"),
    path("contaazul/disconnect", DisconnectView.as_view(), name="contaazul-disconnect"),
]
