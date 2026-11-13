from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.end_customer_guardian_link_dto import EndCustomerGuardianLinkCommand
from guardian.app.ports.input.end_customer_guardian_link_use_case import EndCustomerGuardianLinkUseCase
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.errors import GuardianLinkNotFoundError


class EndCustomerGuardianLinkInteractor(EndCustomerGuardianLinkUseCase):
    """매장이 고객의 보호자 연결을 끊는다. 범위는 가드가 준 `ShopContext` 의 매장이다."""

    def __init__(self, links: GuardianLinkRepository, now: Callable[[], datetime]) -> None:
        self._links = links
        self._now = now

    async def end_link(self, command: EndCustomerGuardianLinkCommand) -> None:
        link = await self._links.find_live_for_customer(command.ctx.shop_id, command.customer_id)
        if link is None or not await self._links.end(link.id, "shop", self._now()):
            raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
