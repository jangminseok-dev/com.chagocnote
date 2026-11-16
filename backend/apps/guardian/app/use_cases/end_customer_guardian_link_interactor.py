from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from guardian.app.dtos.end_customer_guardian_link_dto import EndCustomerGuardianLinkCommand
from guardian.app.ports.input.end_customer_guardian_link_use_case import EndCustomerGuardianLinkUseCase
from guardian.app.ports.output.family_invite_repository import FamilyInviteRepository
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.services.family_links import end_primary
from guardian.domain.errors import GuardianLinkNotFoundError


class EndCustomerGuardianLinkInteractor(EndCustomerGuardianLinkUseCase):
    """매장이 고객의 보호자 연결을 끊는다. 범위는 가드가 준 `ShopContext` 의 매장이다."""

    def __init__(
        self, links: GuardianLinkRepository, now: Callable[[], datetime], invites: FamilyInviteRepository | None = None,
    ) -> None:
        self._links = links
        self._now = now
        self._invites = invites

    async def end_link(self, command: EndCustomerGuardianLinkCommand) -> None:
        """기본 연결을 끊으면 가족까지 다 끊긴다(⑫). 기본 연결 행부터 잠근다."""
        link = await self._links.find_live_for_customer(command.ctx.shop_id, command.customer_id)
        primary = None if link is None else await self._links.lock_primary(link.id)
        if primary is None:
            raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
        if self._invites is None:
            if not await self._links.end(primary.id, "shop", self._now()):
                raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
            return
        await end_primary(self._links, self._invites, primary, "shop", self._now())
