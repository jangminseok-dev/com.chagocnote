"""visit 테스트가 함께 쓰는 값 — 매장 컨텍스트와 방문·메뉴 엔티티를 짧게 만든다."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.menu import Menu
from visit.domain.entities.visit import RESERVED, Visit
from visit.domain.entities.visit_record import RecordMedia, VisitRecord

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
    {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}
)
TZ = "Asia/Seoul"


def kst(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """2026년 한국 시각을 UTC 로. 테스트의 모든 시각은 이것으로 만든다."""
    from zoneinfo import ZoneInfo

    return datetime(2026, month, day, hour, minute, tzinfo=ZoneInfo(TZ)).astimezone(timezone.utc)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "owner") -> ShopContext:
    permissions = OWNER_PERMISSIONS if role == "owner" else STAFF_PERMISSIONS
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=permissions,
                       timezone=TZ)


def visit(**overrides) -> Visit:
    fields = dict(
        id=1, shop_id=1, customer_id=1, pet_id=101, starts_at=kst(9, 23, 14), duration_minutes=90,
        status=RESERVED, started_at=None, completed_at=None, canceled_at=None, cancel_reason=None,
        memo=None, menu_ids=(), created_by_member_id=11, status_changed_by_member_id=None,
    )
    fields.update(overrides)
    return Visit(**fields)


def menu(menu_id: int = 1, name: str = "목욕", minutes: int | None = 60, shop_id: int = 1,
         archived: bool = False, price: int | None = None) -> Menu:
    return Menu(id=menu_id, shop_id=shop_id, name=name, default_duration_minutes=minutes,
                sort_order=menu_id, archived_at=kst(9, 1) if archived else None, price=price)


def but(entity, **changes):
    return replace(entity, **changes)


def record(visit_id: int, media: tuple[tuple[int, str, str, int], ...] = (), **overrides) -> VisitRecord:
    """media 는 (media_id, kind, phase, sort_order) 묶음들."""
    fields = dict(
        visit_id=visit_id, weight_kg=None, care_note=None, internal_note=None, payment_method=None,
        total_amount=None, items=(), media=tuple(RecordMedia(*m) for m in media), version=1,
        created_by_member_id=11, updated_by_member_id=11,
    )
    fields.update(overrides)
    return VisitRecord(**fields)
