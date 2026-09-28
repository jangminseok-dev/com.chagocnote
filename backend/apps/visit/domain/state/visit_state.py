"""방문 상태 전이 — State 패턴. 상태마다 할 수 있는 행동만 구현하고, 나머지는 바탕 클래스가 거절한다.

행동은 다섯 가지다: 시작(start), 완료(complete), 취소(cancel), 노쇼(no_show), 되돌리기(revert).
예약됨에서 바로 완료하면 "바로 완료"다(시작 시각 = 완료 시각). 미용 중인 방문의 취소는 되돌린 뒤 한다.

행동을 더할 때 고치는 곳은 둘이다 — `ACTIONS`에 이름을, 바탕 클래스에 같은 이름의 메서드(기본은 거절)를.
`transition()`은 행동 이름으로 상태 객체의 메서드를 찾아 부르므로 if 체인을 늘리지 않는다.
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
from visit.domain.errors import (
    VisitInputError,
    VisitNotYetError,
    VisitReportSentError,
    VisitStateConflictError,
)
from visit.domain.services.visit_schedule import local_date

ACTIONS = frozenset({"start", "complete", "cancel", "no_show", "revert"})

# 끝난 방문을 다시 시간을 차지하는 예약으로 만드는 행동 — 가족 확인(무지개다리 아이인지)을 다시 거쳐야 한다(V7).
SLOT_RECLAIMING_ACTIONS = frozenset({"revert"})


@dataclass(frozen=True)
class StatusChange:
    """전이의 결과 — 방문 행의 상태 칸을 통째로 이 값으로 바꾼다. 없는 시각은 비운다."""

    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    canceled_at: datetime | None = None
    cancel_reason: str | None = None


@dataclass(frozen=True)
class TransitionRequest:
    """행동 하나에 딸린 입력. 모든 행동이 같은 모양을 받으므로 상태 메서드의 서명이 하나다."""

    now: datetime
    tz: str
    cancel_reason: str | None = None


class VisitState(ABC):
    status: ClassVar[str]

    def start(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        raise self._refuse("시작")

    def complete(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        raise self._refuse("완료")

    def cancel(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        raise self._refuse("취소")

    def no_show(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        raise self._refuse("노쇼 처리")

    def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        # 알림장을 보낸 완료 방문은 되돌릴 수 없다 — 그 규칙은 CompletedState 에 있다.
        return StatusChange(status=RESERVED)

    def _refuse(self, action: str) -> VisitStateConflictError:
        return VisitStateConflictError(f"지금 상태({self.status})에서는 {action}할 수 없습니다.")


def _check_day_reached(visit: Visit, request: TransitionRequest) -> None:
    if local_date(visit.starts_at, request.tz) > local_date(request.now, request.tz):
        raise VisitNotYetError("예약한 날이 되어야 시작하거나 완료할 수 있습니다.")


class ReservedState(VisitState):
    status = RESERVED

    def start(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        _check_day_reached(visit, request)
        return StatusChange(status=IN_PROGRESS, started_at=request.now)

    def complete(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        _check_day_reached(visit, request)
        return StatusChange(status=COMPLETED, started_at=request.now, completed_at=request.now)   # 바로 완료

    def cancel(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        return StatusChange(status=CANCELED, canceled_at=request.now, cancel_reason=request.cancel_reason)

    def no_show(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        if visit.starts_at > request.now:
            raise VisitNotYetError("예약 시각이 지나야 노쇼로 처리할 수 있습니다.")
        return StatusChange(status=NO_SHOW)

    def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        raise self._refuse("되돌리기")


class InProgressState(VisitState):
    status = IN_PROGRESS

    def complete(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        return StatusChange(status=COMPLETED, started_at=visit.started_at, completed_at=request.now)


class CompletedState(VisitState):
    status = COMPLETED

    def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
        if visit.has_live_report:
            raise VisitReportSentError("알림장을 보낸 방문입니다. 링크를 먼저 끊어 주세요.")
        return super().revert(visit, request)


class CanceledState(VisitState):
    status = CANCELED


class NoShowState(VisitState):
    status = NO_SHOW


_STATES: dict[str, VisitState] = {
    state.status: state
    for state in (ReservedState(), InProgressState(), CompletedState(), CanceledState(), NoShowState())
}


def check_action(action: str, cancel_reason: str | None) -> None:
    """행동 이름과 취소 사유의 짝을 확인한다. 취소 사유는 취소에만, 그리고 취소에는 반드시 있어야 한다."""
    if action not in ACTIONS:
        raise VisitInputError("알 수 없는 행동입니다.")
    if (action == "cancel") != (cancel_reason is not None):
        raise VisitInputError("취소 사유는 취소할 때만, 반드시 보내 주세요.")
    if cancel_reason is not None and cancel_reason not in CANCEL_REASONS:
        raise VisitInputError("취소 사유가 올바르지 않습니다.")


def pets_to_confirm(action: str, visits: list[Visit]) -> tuple[int, ...]:
    """이 행동 앞에서 가족 확인에 넘길 반려동물 — 시간을 다시 차지하는 행동이면 그 방문들의 아이, 아니면 없음."""
    if action not in SLOT_RECLAIMING_ACTIONS:
        return ()
    return tuple(sorted({v.pet_id for v in visits if v.pet_id is not None}))


def transition(
    visit: Visit, action: str, now: datetime, tz: str, cancel_reason: str | None = None
) -> StatusChange:
    """방문 하나에 행동 하나를 적용한 결과."""
    check_action(action, cancel_reason)
    handler = getattr(_STATES[visit.status], action)
    return handler(visit, TransitionRequest(now=now, tz=tz, cancel_reason=cancel_reason))
