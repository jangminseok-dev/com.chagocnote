"""알림장 링크의 토큰 — 만들기와 읽기(설계 5절). 키는 인자로 받는다.

    token = base64url( public_id(16) ‖ HMAC-SHA256(key, public_id)[:16] )   # 43글자, 패딩 없음

DB 에는 public_id 만 있고 토큰은 그때마다 다시 계산한다. 서명이 맞지 않는 토큰은 DB 를 읽기 전에 떨어진다.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets

TOKEN_LENGTH = 43
_PUBLIC_ID_BYTES = 16
_SIGNATURE_BYTES = 16
_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{%d}" % TOKEN_LENGTH)


def new_public_id() -> bytes:
    return secrets.token_bytes(_PUBLIC_ID_BYTES)


def make_token(public_id: bytes, key: bytes) -> str:
    return _encode(public_id + _sign(public_id, key))


def read_token(token: str, key: bytes) -> bytes | None:
    """토큰이 가리키는 public_id. 우리가 만든 토큰이 아니면 None — 어떤 입력에도 예외를 던지지 않는다."""
    if not isinstance(token, str) or _TOKEN_PATTERN.fullmatch(token) is None:
        return None
    raw = base64.urlsafe_b64decode(token + "=")
    # 마지막 글자는 뒤 2비트가 버려진다 — 같은 바이트로 풀리는 다른 글자열을 받지 않는다.
    if _encode(raw) != token:
        return None
    public_id, signature = raw[:_PUBLIC_ID_BYTES], raw[_PUBLIC_ID_BYTES:]
    if not hmac.compare_digest(signature, _sign(public_id, key)):
        return None
    return public_id


def _sign(public_id: bytes, key: bytes) -> bytes:
    return hmac.new(key, public_id, hashlib.sha256).digest()[:_SIGNATURE_BYTES]


def _encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
