"""보호자 경로의 관문 — 경로의 link_id 가 로그인한 계정의 살아 있는 연결인지 매 요청마다 확인하고 GuardianContext 를 돌려준다.

`core/shop_guard.py` 의 보호자 쪽 짝이다. 확인 자체는 허브의 GuardianAccessPort 가 한다(구현: guardian).
보호자용 읽기를 가진 스포크(visit)가 guardian 을 import 하면 허브-스포크 위반이라 이 의존성은 core 에 둔다.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path

from core.security import get_current_user_id
from hub.app.dtos.guardian import GuardianContext
from hub.app.ports.guardian_access_port import GuardianAccessPort


def get_guardian_access_port() -> GuardianAccessPort:
    """허브 포트 자리. 진입점이 app.dependency_overrides 로 guardian 의 구현을 꽂는다."""
    raise RuntimeError("GuardianAccessPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


async def get_guardian_context(
    link_id: Annotated[int, Path(ge=1, le=2_147_483_647)],
    user_id: int = Depends(get_current_user_id),
    access: GuardianAccessPort = Depends(get_guardian_access_port),
) -> GuardianContext:
    """내 연결이 아니면 404 `GUARDIAN_LINK_NOT_FOUND`(허브 오류) — 없는 연결·남의 연결·끝난 연결을 구분하지 않는다.

    int32 를 넘는 값은 DB 에 닿기 전에 422 로 막는다.
    """
    return await access.resolve(user_id, link_id)
