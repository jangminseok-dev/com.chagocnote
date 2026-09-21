from __future__ import annotations

from auth.domain.errors import LastIdentityError


def ensure_identity_remains(identity_count: int) -> None:
    """로그인 수단 하나를 해제하기 직전에 부른다. identity_count 는 해제하기 전의 수다."""
    if identity_count <= 1:
        raise LastIdentityError(
            "마지막 로그인 수단은 해제할 수 없습니다. 다른 로그인 수단을 먼저 연결해 주세요."
        )
