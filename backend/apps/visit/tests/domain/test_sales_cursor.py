import base64
from datetime import date

import pytest

from visit.domain.errors import VisitInputError
from visit.domain.services.sales_cursor import (
    decode_due_cursor,
    decode_visit_cursor,
    encode_due_cursor,
    encode_visit_cursor,
)
from visit.tests.helpers.builders import kst


def _raw(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_방문_쪽_표시는_감쌌다_풀면_같은_값이다():
    at = kst(11, 5, 11)
    assert decode_visit_cursor(encode_visit_cursor(at, 7)) == (at, 7)


@pytest.mark.parametrize("day,pet_id", [(date(2026, 8, 3), 103), (date(2025, 11, 14), 1), (date(2026, 9, 18), 9_223_372_036_854_775_807)])
def test_다시_올_때_쪽_표시는_감쌌다_풀면_같은_값이다(day, pet_id):
    assert decode_due_cursor(encode_due_cursor(day, pet_id)) == (day, pet_id)


def test_쪽_표시는_주소에_넣을_수_있는_글자뿐이다():
    assert encode_due_cursor(date(2026, 8, 3), 103).replace("-", "").replace("_", "").isalnum()


@pytest.mark.parametrize("cursor", [
    "", "이상한글자", "!!!!", _raw("2026-08-03"), _raw("2026-08-03|"), _raw("|103"), _raw("2026-08-03|0"),
    _raw("2026-08-03|-1"), _raw("2026-08-03|x"), _raw("2026-08-03|9223372036854775808"),
    _raw("2026-13-03|103"), _raw("2026-02-30|103"), _raw("20260803|103"), _raw("2026-08-03T00:00:00|103"),
    _raw("어제|103"), _raw("a|b|c"), _raw("0000-01-01|103"), _raw("10000-01-01|1"),
], ids=lambda c: c[:12] or "빈 값")
def test_깨진_다시_올_때_쪽_표시는_어떤_것이든_422_다(cursor):
    with pytest.raises(VisitInputError):
        decode_due_cursor(cursor)


@pytest.mark.parametrize("cursor", ["", "!!!!", _raw("2026-11-05T11:00:00|7"), _raw("9999-12-31T23:59:59-01:00|1")])
def test_깨진_방문_쪽_표시는_422_다(cursor):
    with pytest.raises(VisitInputError):
        decode_visit_cursor(cursor)
