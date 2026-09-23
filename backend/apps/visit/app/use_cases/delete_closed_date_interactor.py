from __future__ import annotations

from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand
from visit.app.ports.input.delete_closed_date_use_case import DeleteClosedDateUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository


class DeleteClosedDateInteractor(DeleteClosedDateUseCase):
    """없는 날을 지워도 성공이다(두 번 눌러도 같은 결과)."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def delete_closed_date(self, command: DeleteClosedDateCommand) -> None:
        await self._schedule.delete_closed_date(command.ctx, command.day)
