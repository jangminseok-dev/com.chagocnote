from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm
from visit.domain.entities.menu import Menu


def to_menu(orm: ServiceMenuOrm) -> Menu:
    return Menu(
        id=orm.id, shop_id=orm.shop_id, name=orm.name,
        default_duration_minutes=orm.default_duration_minutes, sort_order=orm.sort_order,
        archived_at=orm.archived_at,
    )
