from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitHistoryRepository(ABC):
    """한 보호자·한 아이의 지난 방문 — 완료 이력과 가족 묶음. 모든 메서드가 ShopContext 의 매장으로 거른다.

    상세·'지난번처럼'·다음 예약 초안·완료 후 최근 방문 갱신이 받는다.
    """

    @abstractmethod
    async def latest_completed_start(self, ctx: ShopContext, customer_id: int) -> datetime | None:
        """그 보호자의 마지막 완료 방문의 시작 시각 — 고객 목록 '최근 방문순'의 원본."""

    @abstractmethod
    async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
        """같은 가족 묶음(같은 보호자 + 같은 시작 시각)의 방문 — 상태와 상관없이."""

    @abstractmethod
    async def last_completed_before(
        self, ctx: ShopContext, customer_id: int, pet_id: int | None, before: datetime
    ) -> Visit | None:
        """before 전에 시작한 마지막 완료 방문. pet_id 가 있으면 그 아이의, 없으면 보호자만의 방문 가운데서."""

    @abstractmethod
    async def last_completed_of_pet(self, ctx: ShopContext, pet_id: int) -> Visit | None:
        """그 아이의 마지막 완료 방문('지난번처럼'의 원본)."""

    @abstractmethod
    async def completed_starts(
        self, ctx: ShopContext, customer_id: int, pet_id: int | None, limit: int
    ) -> list[datetime]:
        """그 아이(pet_id 가 None 이면 보호자만의 방문)의 완료 방문 시작 시각, 최근 것부터 limit 개."""
