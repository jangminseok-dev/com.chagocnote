from __future__ import annotations

from zoneinfo import ZoneInfo

from guardian.app.dtos.list_guardian_links_dto import GuardianLinkView, ListGuardianLinksQuery
from guardian.app.ports.input.list_guardian_links_use_case import ListGuardianLinksUseCase
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository
from guardian.app.ports.output.guardian_settings_repository import GuardianSettingsRepository
from hub.app.ports.shop_profile_port import ShopProfilePort


class ListGuardianLinksInteractor(ListGuardianLinksUseCase):
    """내 연결 목록 — 매장 이름과 이은 날. 정지했거나 폐업한(또는 없는) 매장의 연결은 뺀다.

    반려동물은 싣지 않는다 — 이 스포크는 고객·반려동물을 읽지 않는다(visit 의 보호자용 읽기가 준다).
    """

    def __init__(
        self, links: GuardianLinkRepository, shops: ShopProfilePort, settings: GuardianSettingsRepository | None = None,
    ) -> None:
        self._links = links
        self._shops = shops
        self._settings = settings

    async def list_links(self, query: ListGuardianLinksQuery) -> list[GuardianLinkView]:
        views = []
        links = await self._links.list_live_for_user(query.user_id)
        counts = await self._links.family_counts([link.id for link in links if not link.is_family])
        for link in links:
            shop = await self._shops.public_profile(link.shop_id)
            if shop is None or not shop.open:
                continue
            views.append(GuardianLinkView(
                link_id=link.id, shop_name=shop.name,
                linked_at=link.created_at.astimezone(ZoneInfo(shop.timezone)),
                role="family" if link.is_family else "primary",
                family_count=0 if link.is_family else counts.get(link.id, 0),
                family_max=0 if link.is_family or self._settings is None else await self._settings.family_max(link.shop_id),
            ))
        return views
