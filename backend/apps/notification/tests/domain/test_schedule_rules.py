from datetime import time, timedelta

import pytest

from notification.domain.errors import NotificationInputError
from notification.domain.services.schedule_rules import (
    MAX_ATTEMPTS,
    RETRY_DELAYS,
    check_settings,
    deferred_for_daytime,
    is_mobile_number,
    is_too_late,
    next_visit_at,
    next_visit_weeks,
    reminder_at,
    retry_at,
)
from notification.tests.helpers.builders import TZ, kst, settings

SIX_PM = time(18, 0)


# 리마인드 시각 — 예약 전날 매장 설정 시각


def test_리마인드는_예약_전날_설정_시각이다():
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 13, 9)) == kst(10, 14, 18)


def test_전날은_매장_시간대의_날짜로_센다():
    """KST 00:30 예약은 UTC 로는 그 전날 15:30 이다. 전날은 KST 기준 14일이어야 한다."""
    assert reminder_at(kst(10, 15, 0, 30), SIX_PM, TZ, now=kst(10, 13, 9)) == kst(10, 14, 18)


def test_리마인드_시각이_지금이거나_지났으면_없다():
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 14, 18)) is None
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 14, 18, 1)) is None


def test_리마인드_시각_1분_전이면_있다():
    assert reminder_at(kst(10, 15, 14), SIX_PM, TZ, now=kst(10, 14, 17, 59)) == kst(10, 14, 18)


# 다음 예약 제안의 주 수(⑬ 설계 3.4) — 직접 정한 값 → 알림 설정의 고정 주 수 → 계산한 값 → 매장의 기본 간격


@pytest.mark.parametrize(("cycle_weeks", "source", "fixed", "expected"), [
    (2, "manual", 6, 2),       # 아이에게 직접 정한 값이 가장 앞선다
    (2, "manual", None, 2),
    (3, "computed", 6, 6),     # 알림 설정의 고정 주 수가 계산한 값보다 앞선다
    (3, "computed", None, 3),
    (None, "single", None, 5),   # 간격 하나는 주기가 아니다 — 매장의 기본 간격
    (None, "none", None, 5),
    (None, "single", 6, 6),
])
def test_다음_예약_제안의_주_수의_순서(cycle_weeks, source, fixed, expected):
    assert next_visit_weeks(cycle_weeks, source, 5, fixed) == expected


# 다음 예약 제안 시각 — 완료일 + N주 되는 날 리마인드 시각


def test_다음_예약_제안은_완료일에_주를_더한_날의_리마인드_시각이다():
    assert next_visit_at(kst(10, 15, 14), 4, SIX_PM, TZ) == kst(11, 12, 18)


def test_다음_예약_제안의_완료일은_매장_시간대로_센다():
    assert next_visit_at(kst(10, 15, 0, 30), 1, time(8, 0), TZ) == kst(10, 22, 8)


# 야간 미룸 — 매장 시간대 08:00~21:00


@pytest.mark.parametrize(("at", "expected"), [
    (kst(10, 15, 7, 59), kst(10, 15, 8)),         # 아침 전 → 같은 날 08:00
    (kst(10, 15, 8, 0), kst(10, 15, 8, 0)),       # 경계 08:00 은 그대로
    (kst(10, 15, 14), kst(10, 15, 14)),           # 낮은 그대로
    (kst(10, 15, 21, 0), kst(10, 15, 21, 0)),     # 경계 21:00 은 그대로
    (kst(10, 15, 23, 30), kst(10, 16, 8)),        # 밤 → 다음 날 08:00
    (kst(10, 15, 0, 10), kst(10, 15, 8)),         # KST 자정 직후(UTC 전날) → 같은 KST 날 08:00
])
def test_야간이면_아침_8시로_미룬다(at, expected):
    assert deferred_for_daytime(at, TZ) == expected


def test_21시_1초_뒤는_다음_날_아침이다():
    assert deferred_for_daytime(kst(10, 15, 21) + timedelta(seconds=1), TZ) == kst(10, 16, 8)


# 너무 늦음 — 예약 1시간 전을 넘기면 보내지 않는다


def test_정확히_1시간_전은_늦지_않고_59분_전은_늦다():
    starts = kst(10, 15, 14)
    assert is_too_late(kst(10, 15, 13), starts) is False
    assert is_too_late(kst(10, 15, 13, 1), starts) is True


# 재시도 — 1분·5분·30분 뒤, 세 번 뒤 없음


def test_재시도_간격과_상한():
    assert MAX_ATTEMPTS == 3
    assert RETRY_DELAYS == (timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=30))
    now = kst(10, 15, 14)
    assert retry_at(0, now) == now + timedelta(minutes=1)
    assert retry_at(1, now) == now + timedelta(minutes=5)
    assert retry_at(2, now) == now + timedelta(minutes=30)
    assert retry_at(3, now) is None
    assert retry_at(4, now) is None


# 설정 검사


@pytest.mark.parametrize("overrides", [
    dict(reminder_time=time(8, 0)), dict(reminder_time=time(21, 0)),
    dict(next_visit_after_weeks=None), dict(next_visit_after_weeks=1), dict(next_visit_after_weeks=52),
    dict(next_visit_cooldown_days=1), dict(next_visit_cooldown_days=365),
])
def test_경계_안의_설정은_받는다(overrides):
    check_settings(settings(**overrides))


@pytest.mark.parametrize("overrides", [
    dict(reminder_time=time(7, 59)), dict(reminder_time=time(21, 1)), dict(reminder_time=time(22, 0)),
    dict(next_visit_after_weeks=0), dict(next_visit_after_weeks=53),
    dict(next_visit_cooldown_days=0), dict(next_visit_cooldown_days=366),
])
def test_경계_밖의_설정은_거절한다(overrides):
    with pytest.raises(NotificationInputError):
        check_settings(settings(**overrides))


# 휴대폰 번호


@pytest.mark.parametrize(("phone", "expected"), [
    ("01012345678", True),
    ("0212345678", False),
    ("010-1234-5678", False),
    ("0101234567", False),
    ("010123456789", False),
    ("", False),
])
def test_휴대폰_번호는_010_으로_시작하는_숫자_11자리다(phone, expected):
    assert is_mobile_number(phone) is expected
