"""가족과 함께 보기의 규칙(⑫ 설계 3.5·8절). 초대의 기간과 횟수는 고정이고 가족 수는 매장이 정한다."""
from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta

from guardian.domain.errors import GuardianInputError

INVITE_HOURS = 24                 # 고정 — 잘못 전달된 주소가 살아 있는 시간을 묶는다
FAMILY_MAX_DEFAULT = 3            # 매장이 정한다(사용자 결정 2026-11-16)
FAMILY_MAX_RANGE = (0, 10)        # 0 이면 가족 초대가 없다
_CODE = re.compile(r"^[A-Za-z0-9_-]{43}$")


def new_invite_code() -> str:
    """43자 무작위(256비트). 원문은 돌려주기만 하고 저장하지 않는다."""
    return secrets.token_urlsafe(32)


def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def is_code_shaped(code: str | None) -> bool:
    return code is not None and _CODE.fullmatch(code) is not None


def invite_expires_at(now: datetime) -> datetime:
    return now + timedelta(hours=INVITE_HOURS)


def check_family_max(value: int) -> None:
    low, high = FAMILY_MAX_RANGE
    if not low <= value <= high:
        raise GuardianInputError(f"가족은 {low}명에서 {high}명 사이로 정해 주세요.")
