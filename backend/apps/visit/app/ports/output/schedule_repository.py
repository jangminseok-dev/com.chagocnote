from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings


class ScheduleRepository(ABC):
    """매장 일정 설정과 임시 휴무. 설정 행은 매장을 처음 쓸 때 만든다."""

    @abstractmethod
    async def ensure(self, ctx: ShopContext) -> ScheduleSettings:
        """설정을 읽는다. 없으면 기본값으로 만들고 **같은 트랜잭션에서** 기본 메뉴를 넣는다.

        두 요청이 동시에 처음 써도 설정과 기본 메뉴는 한 번만 들어간다(INSERT … ON CONFLICT DO NOTHING).
        """

    @abstractmethod
    async def update(self, ctx: ShopContext, settings: ScheduleSettings) -> ScheduleSettings:
        """통째로 바꾼다(쉬는 요일도). 설정 행이 이미 있어야 한다(ensure 뒤에 부른다)."""

    @abstractmethod
    async def list_closed_dates(self, ctx: ShopContext, start: date, end: date) -> list[ClosedDate]:
        """start 부터 end 까지(둘 다 포함) 날짜 순으로."""

    @abstractmethod
    async def add_closed_date(self, ctx: ShopContext, day: date, note: str | None) -> ClosedDate:
        """이미 있으면 그대로 두고 있는 것을 돌려준다. 설정 행이 이미 있어야 한다(ensure 뒤에 부른다)."""

    @abstractmethod
    async def delete_closed_date(self, ctx: ShopContext, day: date) -> None:
        """없으면 아무것도 하지 않는다."""
