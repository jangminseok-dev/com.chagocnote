from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from zoneinfo import ZoneInfo

from guardian.app.dtos.family_dto import FamilyMemberView, ListFamilyQuery
from guardian.app.ports.input.list_family_use_case import ListFamilyUseCase
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.domain.errors import GuardianLinkNotFoundError
from hub.app.ports.shop_profile_port import ShopProfilePort


class ListFamilyInteractor(ListFamilyUseCase):
    """기본 보호자가 함께 보는 가족을 본다 — 한 사람에 한 줄, 이은 날. 읽으면 새 줄의 알림을 거둔다."""

    def __init__(self, links: GuardianLinkRepository, shops: ShopProfilePort, now: Callable[[], datetime]) -> None:
        self._links = links
        self._shops = shops
        self._now = now

    async def list_family(self, command: ListFamilyQuery) -> list[FamilyMemberView]:
        primary = await self._links.get_live(command.user_id, command.link_id)
        if primary is None or primary.is_family:
            raise GuardianLinkNotFoundError("연결을 찾을 수 없습니다.")
        shop = await self._shops.public_profile(primary.shop_id)
        zone = ZoneInfo(shop.timezone if shop is not None else "Asia/Seoul")
        views = [
            FamilyMemberView(family_id=f.id, linked_at=f.created_at.astimezone(zone), unseen=f.seen_by_primary_at is None)
            for f in await self._links.list_family(primary.id)
        ]
        await self._links.mark_family_seen(primary.id, self._now())
        return views
