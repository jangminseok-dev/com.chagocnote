from __future__ import annotations

from tenancy.domain.errors import LastOwnerError


def ensure_owner_remains(owner_count: int) -> None:
    """사장 한 명이 자리에서 빠지기 직전(역할 낮춤·내보내기)에 부른다. owner_count 는 빠지기 전의 사장 수다."""
    if owner_count <= 1:
        raise LastOwnerError(
            "매장에는 사장이 한 명 이상 있어야 합니다. 다른 멤버를 먼저 사장으로 지정해 주세요."
        )
