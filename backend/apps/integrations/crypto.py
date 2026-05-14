"""
Criptografia simétrica para tokens OAuth em repouso.

Estratégia:
- Chave Fernet (32 bytes urlsafe-base64) em `settings.FERNET_KEY`
- `encrypt(plain)` → str urlsafe
- `decrypt(ciphertext)` → str
- Em testes, a chave é fixa (settings.test) para reprodutibilidade
"""
from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class CryptoError(Exception):
    """Falha de cripto (chave ausente, token corrompido)."""


@lru_cache(maxsize=1)
def _fernet() -> Fernet:
    key = getattr(settings, "FERNET_KEY", "") or ""
    if not key:
        raise CryptoError(
            "FERNET_KEY ausente. Gere com `make fernet-key` e coloque em .env."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plain: str) -> str:
    """Cifra string UTF-8 e devolve o token urlsafe base64."""
    if not isinstance(plain, str):
        raise TypeError("encrypt espera str")
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt(ciphertext: str) -> str:
    """Decifra um token gerado por `encrypt`. Lança CryptoError em token inválido."""
    if not isinstance(ciphertext, str):
        raise TypeError("decrypt espera str")
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise CryptoError("Token criptografado inválido ou chave incorreta.") from e
