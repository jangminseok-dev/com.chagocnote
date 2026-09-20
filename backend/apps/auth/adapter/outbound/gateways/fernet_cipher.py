from __future__ import annotations

from cryptography.fernet import Fernet


class FernetCipher:
    """제공자 리프레시 토큰을 DB 에 넣기 전에 암호화한다. 키는 IDENTITY_TOKEN_ENC_KEY."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()
