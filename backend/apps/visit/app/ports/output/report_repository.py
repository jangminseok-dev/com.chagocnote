from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit_report import VisitReport


class ReportRepository(ABC):
    """알림장 링크(visit_reports). 매장 범위 — 방문의 매장(ShopContext)으로 거른다.

    쓰기는 방문 행을 잠근 **뒤에만** 부른다. '살아 있다'는 끊지 않았고 기간이 지나지 않았다는 뜻이다.
    """

    @abstractmethod
    async def get_live(self, ctx: ShopContext, visit_id: int, now: datetime) -> VisitReport | None:
        """그 방문의 살아 있는 링크. 없거나 다른 매장의 방문이면 None."""

    @abstractmethod
    async def live_visit_ids(self, ctx: ShopContext, visit_ids: list[int], now: datetime) -> set[int]:
        """살아 있는 링크가 있는 방문의 ID — 목록의 '보냄' 표시를 방문 수와 상관없이 한 번에 읽는다."""

    @abstractmethod
    async def close_expired(self, ctx: ShopContext, visit_id: int, now: datetime) -> None:
        """끊지 않았는데 기간이 지난 줄을 끊는다(revoked_at = now). 새 줄을 넣기 전에 부른다 — 부분 유일 색인은
        기간을 모르므로 닫지 않으면 새 줄이 유일 위반이 된다."""

    @abstractmethod
    async def create(
        self, ctx: ShopContext, visit_id: int, public_id: bytes, expires_at: datetime | None, now: datetime
    ) -> VisitReport:
        """새 줄을 넣는다. 만든 사람은 ctx 의 멤버, 보낸 시각은 now."""

    @abstractmethod
    async def set_show_review(self, ctx: ShopContext, report_id: int, show_review: bool) -> None:
        """그 알림장에 리뷰 남기기 줄을 넣는가(⑫). 다시 보낼 때 바뀐다."""

    @abstractmethod
    async def revoke(self, ctx: ShopContext, visit_id: int, now: datetime) -> bool:
        """그 방문의 살아 있는 줄을 끊는다. 끊은 것이 있으면 True."""

    @abstractmethod
    async def revoke_for_customer(self, ctx: ShopContext, customer_id: int, now: datetime) -> None:
        """그 보호자의 방문들의, 끊지 않은 줄을 모두 끊는다(익명화)."""
