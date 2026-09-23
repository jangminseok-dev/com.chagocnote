from __future__ import annotations

from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.app.ports.input.add_closed_date_use_case import AddClosedDateUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository


class AddClosedDateInteractor(AddClosedDateUseCase):
    """임시 휴무 추가. 이미 있으면 그대로 둔다(두 번 눌러도 하나). 그날의 예약은 그대로다(경고만 생긴다)."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def add_closed_date(self, command: AddClosedDateCommand) -> ClosedDateView:
        await self._schedule.ensure(command.ctx)   # 휴무 행은 설정 행을 가리킨다(외래 키)
        return ClosedDateView.of(
            await self._schedule.add_closed_date(command.ctx, command.day, command.note)
        )
