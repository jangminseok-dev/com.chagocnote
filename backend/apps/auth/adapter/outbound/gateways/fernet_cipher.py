from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """저장된 값을 지금 키로 복호화할 수 없다 (키 교체·값 손상). 원문 예외를 그대로 올리지 않는다 —
    부르는 쪽이 로그에 남길 때 암호문이나 cryptography 의 메시지가 섞이지 않게 하려는 것이다."""


class FernetCipher:
    """제공자 리프레시 토큰을 DB 에 넣기 전에 암호화한다. 키는 IDENTITY_TOKEN_ENC_KEY."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        try:
            return self._fernet.decrypt(encrypted.encode()).decode()
        except InvalidToken as exc:
            raise DecryptionError from exc
