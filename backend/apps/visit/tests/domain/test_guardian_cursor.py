import pytest

from visit.domain.errors import VisitInputError
from visit.domain.services.guardian_cursor import decode_cursor, encode_cursor
from visit.tests.helpers.builders import kst


def _raw(text: str) -> str:
    import base64

    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_쪽_표시는_감쌌다_풀면_같은_값이다():
    at = kst(10, 2, 14)
    assert decode_cursor(encode_cursor(at, 7)) == (at, 7)


@pytest.mark.parametrize("cursor", [
    "", "이상한글자", "!!!!", _raw("2026-10-02T14:00:00+09:00"), _raw("2026-10-02T14:00:00|7"),
    _raw("2026-10-02T14:00:00+09:00|0"), _raw("2026-10-02T14:00:00+09:00|99999999999"),
    _raw("2026-10-02T14:00:00+09:00|x"), _raw("어제|7"), _raw("a|b|c"),
    # UTC 로 바꾸면 범위를 넘는 시각 — DB 바인딩에서 터지지 않게 여기서 거른다.
    _raw("9999-12-31T23:59:59-01:00|1"), _raw("0001-01-01T00:00:00+01:00|1"),
], ids=lambda c: c[:12] or "빈 값")
def test_깨졌거나_범위를_넘는_쪽_표시는_어떤_것이든_422_다(cursor):
    with pytest.raises(VisitInputError):
        decode_cursor(cursor)
