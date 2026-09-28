from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.report_settings import ReportSettings


class ReportSettingsRepository(ABC):
    """매장의 알림장 설정. 일정 설정과 같은 행(visit_shop_settings)의 다른 칸이다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> ReportSettings:
        """설정 행이 없으면 기본값을 돌려준다. 행을 만들지 않는다(공개 조회도 이것을 부른다)."""

    @abstractmethod
    async def update(self, ctx: ShopContext, settings: ReportSettings) -> ReportSettings:
        """통째로 바꾼다. 설정 행이 이미 있어야 한다(ScheduleRepository.ensure 뒤에 부른다)."""
