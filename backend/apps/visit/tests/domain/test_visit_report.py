from datetime import timedelta

import pytest

from visit.domain.entities.visit_report import VisitReport
from visit.tests.helpers.builders import kst

NOW = kst(9, 28, 15)
SECOND = timedelta(seconds=1)


def _report(expires_at=None, revoked_at=None):
    return VisitReport(id=1, visit_id=1, public_id=b"p" * 16, expires_at=expires_at, revoked_at=revoked_at,
                       first_viewed_at=None, created_by_member_id=11, created_at=kst(9, 1))


def test_기간이_남은_링크는_살아_있다():
    assert _report(expires_at=NOW + SECOND).is_live(NOW)


def test_기간이_끝나는_바로_그_시각에는_닫혀_있다():
    assert not _report(expires_at=NOW).is_live(NOW)


def test_기간이_지난_링크는_닫혀_있다():
    assert not _report(expires_at=NOW - SECOND).is_live(NOW)


def test_무기한_링크는_살아_있다():
    assert _report(expires_at=None).is_live(NOW)


@pytest.mark.parametrize("expires_at", [None, NOW + SECOND])
def test_끊은_링크는_기간이_남았어도_닫혀_있다(expires_at):
    assert not _report(expires_at=expires_at, revoked_at=NOW - SECOND).is_live(NOW)
