"""search 테스트가 함께 쓰는 값."""
from __future__ import annotations

from datetime import date, datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from search.domain.entities.search_document import SearchDocument

NOW = datetime(2026, 11, 15, 3, 0, tzinfo=timezone.utc)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "staff") -> ShopContext:
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=frozenset())


def doc(kind: str = "care_note", source_id: int = 7, *, customer_id: int = 1, pet_id: int | None = 101,
        visit_id: int | None = None, happened_on: date | None = None, body: str = "얌전했어요",
        embedding: tuple[float, ...] | None = None, model: str | None = None) -> SearchDocument:
    """방문 계열이면 visit_id 는 source_id, 날짜는 2026-11-03 이 기본이다."""
    visit_kind = kind in ("care_note", "internal_note", "visit_memo")
    return SearchDocument(
        kind=kind, source_id=source_id, customer_id=customer_id, pet_id=pet_id,
        visit_id=visit_id if visit_id is not None else (source_id if visit_kind else None),
        happened_on=happened_on if happened_on is not None else (date(2026, 11, 3) if visit_kind else None),
        body=body, embedding=embedding, model=model,
    )
