"""라우터 테스트가 스텁 유스케이스에서 돌려줄 방문 보기 값."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from visit.app.dtos.visit_view_dto import CustomerBriefView, MenuBriefView, PetBriefView, VisitView

_SEOUL = ZoneInfo("Asia/Seoul")


def visit_view(visit_id: int = 1, **overrides) -> VisitView:
    fields = dict(
        visit_id=visit_id,
        customer=CustomerBriefView(customer_id=1, name="김민지", phone_masked="010-12··-5678"),
        pet=PetBriefView(pet_id=101, name="콩이", species="dog", breed="말티즈", weight_kg=Decimal("3.2")),
        starts_at=datetime(2026, 10, 2, 14, tzinfo=_SEOUL), ends_at=datetime(2026, 10, 2, 15, 30, tzinfo=_SEOUL),
        duration_minutes=90, status="reserved", started_at=None, completed_at=None, canceled_at=None,
        cancel_reason=None, memo=None, menus=[MenuBriefView(menu_id=1, name="목욕")],
        status_changed_by_member_id=None,
    )
    return replace(VisitView(**fields), **overrides)
