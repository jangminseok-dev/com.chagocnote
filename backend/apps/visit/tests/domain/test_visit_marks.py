import pytest

from visit.domain.services.visit_marks import PAID, REPORT_SENT, is_paid, is_report_unsent, is_unpaid, marks_of
from visit.tests.helpers.builders import kst, record, visit

DONE = dict(status="completed", started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))


@pytest.mark.parametrize(("total", "method", "paid"), [
    (None, None, False), (None, "card", False),     # 총액이 없으면 아니다
    (55_000, None, False),                          # 받을 나머지가 있는데 결제 수단이 없다
    (55_000, "cash", True),
    (0, None, True),                                # 받을 나머지가 0 이다
])
def test_결제_완료는_총액이_있고_나머지가_0이거나_결제_수단이_있다(total, method, paid):
    assert is_paid(record(1, total_amount=total, payment_method=method)) is paid


def test_기록이_없으면_결제_완료가_아니다():
    assert is_paid(None) is False


def test_줄의_낱말은_결제_완료_알림장_보냄_차례다():
    done = visit(**DONE)
    paid = record(1, total_amount=55_000, payment_method="card")
    assert marks_of(done, paid, report_live=True) == [PAID, REPORT_SENT]
    assert marks_of(done, None, report_live=False) == []
    assert marks_of(visit(), paid, report_live=False) == []          # 완료 전에는 결제 완료가 없다


def test_결제_안_적음은_완료이고_결제_완료가_아닌_방문이다():
    assert is_unpaid(visit(**DONE), record(1, total_amount=None)) is True
    assert is_unpaid(visit(**DONE), None) is True
    assert is_unpaid(visit(**DONE), record(1, total_amount=10_000, payment_method="card")) is False
    assert is_unpaid(visit(), None) is False                          # 완료 전은 남은 일이 아니다


def test_알림장_안_보냄은_기록이_있고_알림장_줄이_한_번도_없고_넘기지_않았고_매장이_센다():
    done, rec = visit(**DONE), record(1)
    assert is_report_unsent(done, rec, ever_sent=False, count=True) is True
    assert is_report_unsent(done, None, ever_sent=False, count=True) is False        # 기록이 없다
    assert is_report_unsent(done, rec, ever_sent=True, count=True) is False          # 보낸 적이 있다(끊었거나 끝났어도)
    assert is_report_unsent(visit(**DONE, report_skipped_at=kst(9, 23, 20)), rec, ever_sent=False, count=True) is False
    assert is_report_unsent(done, rec, ever_sent=False, count=False) is False        # 매장이 세지 않기로 했다
    assert is_report_unsent(visit(), rec, ever_sent=False, count=True) is False      # 완료 전
