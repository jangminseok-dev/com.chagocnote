from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from media.domain.services.url_expiry import signing_window

SEOUL = ZoneInfo("Asia/Seoul")


def _kst(day, hour, minute=0):
    return datetime(2026, 9, day, hour, minute, tzinfo=SEOUL)


def test_하루_안에서는_서명_시각이_같다():
    morning, night = signing_window(_kst(24, 4), "Asia/Seoul"), signing_window(_kst(25, 3, 59), "Asia/Seoul")
    assert morning == night
    assert morning.signed_at == _kst(24, 4).astimezone(timezone.utc)


def test_04시_전은_전날_창이다():
    assert signing_window(_kst(24, 3, 59), "Asia/Seoul").signed_at == _kst(23, 4).astimezone(timezone.utc)


def test_남은_유효_시간은_24시간에서_48시간이다():
    for now in (_kst(24, 4), _kst(24, 15), _kst(25, 3, 59)):
        window = signing_window(now, "Asia/Seoul")
        assert timedelta(hours=24) < window.expires_at - now <= timedelta(hours=48)


def test_매장_시간대로_하루를_센다():
    now = datetime(2026, 9, 24, 3, 0, tzinfo=timezone.utc)   # 서울 12시, 뉴욕 전날 23시
    assert signing_window(now, "Asia/Seoul").signed_at == _kst(24, 4).astimezone(timezone.utc)
    ny = ZoneInfo("America/New_York")
    assert signing_window(now, "America/New_York").signed_at == datetime(2026, 9, 23, 4, tzinfo=ny).astimezone(timezone.utc)
