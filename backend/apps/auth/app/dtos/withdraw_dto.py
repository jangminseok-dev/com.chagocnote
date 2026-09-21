from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.identity_revocation import IdentityRevocation


@dataclass(frozen=True)
class WithdrawCommand:
    user_id: int
    confirm_close_shops: bool


@dataclass(frozen=True)
class WithdrawResult:
    revocations: tuple[IdentityRevocation, ...]   # 커밋 뒤에 제공자 쪽 연결을 끊을 신원들
