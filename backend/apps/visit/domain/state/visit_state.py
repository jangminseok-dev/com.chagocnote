"""방문 상태 전이 — State 패턴. 상태마다 할 수 있는 행동만 구현하고, 나머지는 바탕 클래스가 거절한다.

행동은 다섯 가지다: 시작(start), 완료(complete), 취소(cancel), 노쇼(no_show), 되돌리기(revert).
예약됨에서 바로 완료하면 "바로 완료"다(시작 시각 = 완료 시각). 미용 중인 방문의 취소는 되돌린 뒤 한다.
"""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from visit.domain.entities.visit import (
    CANCEL_REASONS,
    CANCELED,
    COMPLETED,
    IN_PROGRESS,
    NO_SHOW,
    RESERVED,
    Visit,
)
from visit.domain.errors import VisitInputError, VisitNotYetError, VisitStateConflictError
from visit.domain.services.visit_schedule import local_date

ACTIONS = frozenset({"start", "complete", "cancel", "no_show", "revert"})


@dataclass(frozen=True)
class StatusChange:
    """전이의 결과 — 방문 행의 상태 칸을 통째로 이 값으로 바꾼다. 없는 시각은 비운다."""

    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    canceled_at: datetime | None = None
    cancel_reason: str | None = None


class VisitState(ABC):
    status: ClassVar[str]

    def start(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        raise self._refuse("시작")

    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        raise self._refuse("완료")

    def cancel(self, visit: Visit, now: datetime, reason: str) -> StatusChange:
        raise self._refuse("취소")

    def no_show(self, visit: Visit, now: datetime) -> StatusChange:
        raise self._refuse("노쇼 처리")

    def revert(self, visit: Visit) -> StatusChange:
        # 알림장을 보낸 뒤에는 되돌릴 수 없다는 규칙이 ⑤에서 더해진다.
        return StatusChange(status=RESERVED)

    def _refuse(self, action: str) -> VisitStateConflictError:
        return VisitStateConflictError(f"지금 상태({self.status})에서는 {action}할 수 없습니다.")


def _check_day_reached(visit: Visit, now: datetime, tz: str) -> None:
    if local_date(visit.starts_at, tz) > local_date(now, tz):
        raise VisitNotYetError("예약한 날이 되어야 시작하거나 완료할 수 있습니다.")


class ReservedState(VisitState):
    status = RESERVED

    def start(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        _check_day_reached(visit, now, tz)
        return StatusChange(status=IN_PROGRESS, started_at=now)

    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        _check_day_reached(visit, now, tz)
        return StatusChange(status=COMPLETED, started_at=now, completed_at=now)   # 바로 완료

    def cancel(self, visit: Visit, now: datetime, reason: str) -> StatusChange:
        return StatusChange(status=CANCELED, canceled_at=now, cancel_reason=reason)

    def no_show(self, visit: Visit, now: datetime) -> StatusChange:
        if visit.starts_at > now:
            raise VisitNotYetError("예약 시각이 지나야 노쇼로 처리할 수 있습니다.")
        return StatusChange(status=NO_SHOW)

    def revert(self, visit: Visit) -> StatusChange:
        raise self._refuse("되돌리기")


class InProgressState(VisitState):
    status = IN_PROGRESS

    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        return StatusChange(status=COMPLETED, started_at=visit.started_at, completed_at=now)


class CompletedState(VisitState):
    status = COMPLETED


class CanceledState(VisitState):
    status = CANCELED


class NoShowState(VisitState):
    status = NO_SHOW


_STATES: dict[str, VisitState] = {
    state.status: state
    for state in (ReservedState(), InProgressState(), CompletedState(), CanceledState(), NoShowState())
}


def transition(
    visit: Visit, action: str, now: datetime, tz: str, cancel_reason: str | None = None
) -> StatusChange:
    """방문 하나에 행동 하나를 적용한 결과. 취소 사유는 취소에만, 그리고 취소에는 반드시 있어야 한다."""
    if action not in ACTIONS:
        raise VisitInputError("알 수 없는 행동입니다.")
    if (action == "cancel") != (cancel_reason is not None):
        raise VisitInputError("취소 사유는 취소할 때만, 반드시 보내 주세요.")
    if cancel_reason is not None and cancel_reason not in CANCEL_REASONS:
        raise VisitInputError("취소 사유가 올바르지 않습니다.")
    state = _STATES[visit.status]
    if action == "start":
        return state.start(visit, now, tz)
    if action == "complete":
        return state.complete(visit, now, tz)
    if action == "cancel":
        return state.cancel(visit, now, cancel_reason)
    if action == "no_show":
        return state.no_show(visit, now)
    return state.revert(visit)
