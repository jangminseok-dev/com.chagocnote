from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from decimal import Decimal

from visit.app.dtos.guardian_report_dto import SentMedia, SentReport
from visit.domain.services.guardian_cursor import MediaCursor


class GuardianReportRepository(ABC):
    """보호자용 읽기가 쓰는 알림장 — 그 고객의 방문 가운데 **끊지 않은 알림장**(기간이 지났어도 된다)과 기록이
    있는 것. `ShopContext` 는 `public_context`(권한 빔)이고 customer_id 는 가드가 확인한 연결의 고객이다."""

    @abstractmethod
    async def list_sent(
        self, ctx: ShopContext, customer_id: int, *, pet_id: int | None, before: tuple[datetime, int] | None,
        limit: int,
    ) -> list[SentReport]:
        """방문 시작 시각·방문 ID 역순. before 는 (시작 시각, 방문 ID) — 그보다 앞선 것만. 메뉴는 싣지 않는다."""

    @abstractmethod
    async def get_sent(self, ctx: ShopContext, customer_id: int, report_id: int) -> SentReport | None:
        """그 고객의 것이 아니거나 끊었거나 기록이 없으면 None."""

    @abstractmethod
    async def pet_ids_with_reports(self, ctx: ShopContext, customer_id: int) -> list[int]:
        """알림장을 받은 적 있는 아이들(오름차순). 보호자만의 방문은 세지 않는다."""

    # --- 모아 보기(⑫) — 조건은 한 장의 조립과 같다(끊지 않음·기록 있음·알림장에서 빼지 않은 미디어) ---

    @abstractmethod
    async def list_media(
        self, ctx: ShopContext, customer_id: int, *, pet_id: int | None, year: int | None, phase: str | None,
        before: MediaCursor | None, limit: int,
    ) -> list[SentMedia]:
        """방문 시작 시각·방문 ID 역순, 한 방문 안에서는 후 → 전·순서대로(한 장의 순서와 같다).
        year 는 매장 시간대의 해다. 질의 수는 쪽의 크기와 상관없다."""

    @abstractmethod
    async def media_years(self, ctx: ShopContext, customer_id: int, *, pet_id: int | None) -> list[int]:
        """보이는 미디어가 있는 해(최근부터)."""

    @abstractmethod
    async def weights(self, ctx: ShopContext, customer_id: int, pet_id: int, limit: int) -> list[tuple[datetime, Decimal]]:
        """보이는 알림장의 기록에 적힌 몸무게 — (방문 시작 시각, kg), 최근부터 limit 개."""

