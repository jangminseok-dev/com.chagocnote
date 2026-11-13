from __future__ import annotations

from zoneinfo import ZoneInfo

from guardian.app.dtos.get_customer_guardian_link_dto import CustomerGuardianLinkView, GetCustomerGuardianLinkQuery
from guardian.app.ports.input.get_customer_guardian_link_use_case import GetCustomerGuardianLinkUseCase
from guardian.app.ports.output.guardian_link_repository import GuardianLinkRepository


class GetCustomerGuardianLinkInteractor(GetCustomerGuardianLinkUseCase):
    """매장이 고객의 보호자 연결을 본다 — 여부와 이은 날뿐. 보호자가 누구인지는 주지 않는다(⑦ 설계 G14).

    범위는 가드가 준 `ShopContext` 의 매장이다 — 다른 매장의 고객 ID 를 넣으면 연결이 없는 것으로 보인다.
    """

    def __init__(self, links: GuardianLinkRepository) -> None:
        self._links = links

    async def get_link(self, query: GetCustomerGuardianLinkQuery) -> CustomerGuardianLinkView:
        link = await self._links.find_live_for_customer(query.ctx.shop_id, query.customer_id)
        if link is None:
            return CustomerGuardianLinkView(linked=False, linked_at=None)
        return CustomerGuardianLinkView(
            linked=True, linked_at=link.created_at.astimezone(ZoneInfo(query.ctx.timezone)))
