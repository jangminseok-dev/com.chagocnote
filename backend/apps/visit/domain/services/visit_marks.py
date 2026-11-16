"""줄의 낱말과 남은 일(⑬ 설계 3.5·4.4, 공통 6·7절) — 끝낸 일은 줄의 낱말로, 남은 일은 하루 머리의 숫자로.

`marks` 코드와 차례는 이 파일이 정본이다: paid(결제 완료) · report_sent(알림장 보냄) · pass_used(정기권, ⑭) ·
deposit_received(예약금 받음, ⑮). 앱은 아는 코드만 낱말로 바꾼다. 금액 숫자는 어디에도 싣지 않는다.
"""
from __future__ import annotations

from visit.domain.entities.visit import COMPLETED, Visit
from visit.domain.entities.visit_record import VisitRecord

PAID = "paid"
REPORT_SENT = "report_sent"


def remaining_of(record: VisitRecord) -> int:
    """받을 나머지 = 총액 − 정기권 몫 − 예약금 몫(공통 6절). ⑭·⑮ 전에는 총액 그대로다 — 돈을 가르는 함수가
    생기면 그 나머지를 받는다."""
    return record.total_amount or 0


def is_paid(record: VisitRecord | None) -> bool:
    """결제 완료 — 기록에 총액이 있고, (받을 나머지가 0 이거나 결제 수단이 있다)."""
    if record is None or record.total_amount is None:
        return False
    return remaining_of(record) == 0 or record.payment_method is not None


def marks_of(visit: Visit, record: VisitRecord | None, report_live: bool) -> list[str]:
    """그 방문의 끝낸 일 — 차례대로. 결제 완료는 완료한 방문에만 붙는다."""
    marks = []
    if visit.status == COMPLETED and is_paid(record):
        marks.append(PAID)
    if report_live:
        marks.append(REPORT_SENT)
    return marks


def is_unpaid(visit: Visit, record: VisitRecord | None) -> bool:
    """남은 일 '결제 안 적음' — 완료했고 결제 완료가 아니다."""
    return visit.status == COMPLETED and not is_paid(record)


def is_report_unsent(visit: Visit, record: VisitRecord | None, *, ever_sent: bool, count: bool) -> bool:
    """남은 일 '알림장 안 보냄' — 완료했고 기록이 있는데 알림장 줄이 한 번도 없고(끊었거나 기간이 끝난 것은 보낸
    것이다) 하루 마무리에서 넘기지도 않았다. 매장이 세지 않기로 했으면(count=False) 세지 않는다."""
    return (count and visit.status == COMPLETED and record is not None and not ever_sent
            and visit.report_skipped_at is None)
