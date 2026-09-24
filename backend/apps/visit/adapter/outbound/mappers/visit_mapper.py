from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm, VisitOrm
from visit.domain.entities.menu import Menu
from visit.domain.entities.visit import Visit


def to_menu(orm: ServiceMenuOrm) -> Menu:
    return Menu(
        id=orm.id, shop_id=orm.shop_id, name=orm.name,
        default_duration_minutes=orm.default_duration_minutes, sort_order=orm.sort_order,
        archived_at=orm.archived_at, price=orm.price,
    )


def to_visit(orm: VisitOrm, menu_ids: list[int]) -> Visit:
    return Visit(
        id=orm.id, shop_id=orm.shop_id, customer_id=orm.customer_id, pet_id=orm.pet_id,
        starts_at=orm.starts_at, duration_minutes=orm.duration_minutes, status=orm.status,
        started_at=orm.started_at, completed_at=orm.completed_at, canceled_at=orm.canceled_at,
        cancel_reason=orm.cancel_reason, memo=orm.memo, menu_ids=tuple(menu_ids),
        created_by_member_id=orm.created_by_member_id,
        status_changed_by_member_id=orm.status_changed_by_member_id,
    )
