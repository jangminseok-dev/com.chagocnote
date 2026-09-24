from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitBoardRepository(ABC):
    """하루·달력·시간 칸이 보는 시간 범위의 방문. 모든 메서드가 ShopContext 의 매장으로 거른다.

    하루 목록·월 달력·시간 칸 조회와 저장 뒤 경고(`visit_warnings`)가 받는다.
    """

    @abstractmethod
    async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """시작 시각이 [start, end) 인 방문 — 상태와 상관없이, 시작 순으로."""

    @abstractmethod
    async def unresolved_before(self, ctx: ShopContext, before: datetime) -> tuple[int, datetime | None]:
        """시작 시각이 before 전인데 아직 예약됨인 방문(정리 안 된 예약)의 수와 가장 이른 시작 시각."""

    @abstractmethod
    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """[start, end) 와 시간이 겹치는 살아 있는 방문(예약됨·미용 중)."""
