from __future__ import annotations

from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from hub.app.dtos.guardian import GuardianContext
from hub.app.errors import GuardianAccessDeniedError
from hub.app.ports.guardian_access_port import GuardianAccessPort


class ResolveGuardianAccessInteractor(GuardianAccessPort):
    """보호자 가드(core/guardian_guard)가 쓰는 접근 확인 — 그 계정의 살아 있는 연결인지 매 요청마다 DB 에서 본다."""

    def __init__(self, links: GuardianLinkRepository) -> None:
        self._links = links

    async def resolve(self, user_id: int, link_id: int) -> GuardianContext:
        link = await self._links.get_live(user_id, link_id)
        if link is None:
            raise GuardianAccessDeniedError("연결을 찾을 수 없습니다.")
        return GuardianContext(link_id=link.id, user_id=link.user_id, shop_id=link.shop_id,
                               customer_id=link.customer_id)
