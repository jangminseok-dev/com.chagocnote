"""초대 코드 — 사람이 보고 입력하는 8자리. DB 에는 해시만 둔다."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 헷갈리는 I·O·0·1 을 뺐다
_LENGTH = 8
INVITE_TTL = timedelta(days=7)


def generate_invite_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))


def normalize_invite_code(raw: str) -> str:
    """사람이 입력한 모양(소문자, 공백, 하이픈)을 저장할 때의 모양으로 맞춘다."""
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def hash_invite_code(code: str) -> str:
    return hashlib.sha256(normalize_invite_code(code).encode()).hexdigest()
