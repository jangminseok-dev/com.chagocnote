"""방문을 화면에 보여 줄 모양으로 조립한다 — 보호자·반려동물 이름은 허브 포트로, 메뉴 이름은 메뉴표에서.

여러 슬라이스가 쓰기를 마친 뒤 같은 모양으로 돌려준다. 이름을 방문에 복사해 두지 않는다(설계 5.3).
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.visit_view_dto import VisitView
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.visit import Visit


async def describe_visits(
    ctx: ShopContext, visits: list[Visit], directory: CustomerDirectoryPort, menus: MenuRepository
) -> list[VisitView]:
    if not visits:
        return []
    briefs = await directory.briefs(
        ctx,
        sorted({v.customer_id for v in visits}),
        sorted({v.pet_id for v in visits if v.pet_id is not None}),
    )
    menu_names = {}
    if any(v.menu_ids for v in visits):
        # 보관한 메뉴도 이름을 보여 준다 — 지난 방문이 가리키고 있다.
        menu_names = {m.id: m.name for m in await menus.list(ctx, include_archived=True)}
    zone = ZoneInfo(ctx.timezone)
    return [VisitView.of(v, briefs, menu_names, zone) for v in visits]
