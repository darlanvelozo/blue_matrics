"""Testes da camada de criptografia."""
from __future__ import annotations

import pytest

from apps.integrations.crypto import CryptoError, decrypt, encrypt


class TestCrypto:
    def test_roundtrip(self):
        plain = "token-secreto-abc123"
        cipher = encrypt(plain)
        assert cipher != plain
        assert decrypt(cipher) == plain

    def test_different_outputs_each_call(self):
        # Fernet inclui IV aleatório → ciphertexts diferentes para mesmo plain
        plain = "x"
        assert encrypt(plain) != encrypt(plain)

    def test_decrypt_invalid_raises(self):
        with pytest.raises(CryptoError):
            decrypt("not-a-real-token")

    def test_encrypt_non_string_raises(self):
        with pytest.raises(TypeError):
            encrypt(123)  # type: ignore[arg-type]
