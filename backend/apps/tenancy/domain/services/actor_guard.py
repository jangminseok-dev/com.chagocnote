from __future__ import annotations

from tenancy.domain.entities.member import Member
from tenancy.domain.errors import NotAMemberError


def ensure_actor_unchanged(actor: Member | None, expected_role: str) -> None:
    """매장 행을 잠근 뒤 다시 읽은 행위자가 요청 가드가 본 그대로인지 확인한다.

    가드가 소속과 권한을 확인한 뒤 잠금을 얻는 사이에 행위자가 내보내지거나 역할이 낮춰질 수 있다.
    expected_role 은 그 가드가 본 역할(`ShopContext.role`)이다.
    """
    if actor is None:
        raise NotAMemberError("더는 이 매장의 멤버가 아닙니다.")
    if actor.role.value != expected_role:
        raise NotAMemberError("이 매장에서의 역할이 바뀌었습니다. 다시 확인해 주세요.")
