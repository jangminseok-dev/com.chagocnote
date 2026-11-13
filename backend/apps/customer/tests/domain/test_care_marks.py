from datetime import date
from types import SimpleNamespace

import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.care_marks import (
    caution_active,
    caution_until,
    check_consent_day,
    clean_reason,
    conditions_added,
)

TODAY = date(2026, 11, 14)


def _c(code, custom=None, note=None):
    return SimpleNamespace(type_code=code, custom_label=custom, note=note)


@pytest.mark.parametrize("text,expected", [
    ("노쇼 2번", "노쇼 2번"),
    ("  입질이 있어요\n", "입질이 있어요"),
    ("가", "가"),
    ("가" * 100, "가" * 100),
    (" " + "가" * 100 + " ", "가" * 100),   # 공백을 뗀 뒤의 길이로 본다
])
def test_사유는_앞뒤_공백을_떼고_1자에서_100자다(text, expected):
    assert clean_reason(text) == expected


@pytest.mark.parametrize("text", ["", "   ", "\n\t", "가" * 101])
def test_빈_사유와_100자를_넘는_사유는_거절한다(text):
    with pytest.raises(CustomerInputError) as raised:
        clean_reason(text)
    assert "가가" not in str(raised.value)   # 사유를 오류 메시지에 싣지 않는다


def test_주의_표시는_단_날로부터_365일_뒤에_끝난다():
    assert caution_until(TODAY) == date(2027, 11, 14)
    assert caution_until(date(2028, 2, 29)) == date(2029, 2, 28)   # 윤일


@pytest.mark.parametrize("until,active", [
    (date(2026, 11, 15), True),
    (date(2026, 11, 14), True),    # 끝나는 날 당일까지 살아 있다
    (date(2026, 11, 13), False),
    (None, False),
])
def test_끝나는_날이_지나면_살아_있지_않다(until, active):
    assert caution_active(until, TODAY) is active


def test_동의를_받은_날은_오늘이나_지난_날이다():
    check_consent_day(TODAY, TODAY)
    check_consent_day(date(2020, 1, 1), TODAY)
    with pytest.raises(CustomerInputError):
        check_consent_day(date(2026, 11, 15), TODAY)


@pytest.mark.parametrize("before,after,added", [
    ([], [_c("heart_disease")], True),                                         # 처음 적었다
    ([_c("allergy")], [_c("allergy"), _c("heart_disease")], True),             # 하나 더했다
    ([_c("allergy"), _c("heart_disease")], [_c("allergy")], False),            # 뺐다
    ([_c("allergy")], [], False),                                               # 다 뺐다
    ([_c("allergy", note="닭")], [_c("allergy", note="닭·소")], False),         # 메모만 고쳤다
    ([_c("allergy")], [_c("heart_disease")], True),                            # 바꿨다
    ([_c("other", "눈물 자국")], [_c("other", "귓병")], True),                  # 기타를 다른 기타로
    ([_c("other", "눈물 자국")], [_c("other", "눈물 자국")], False),
    ([], [], False),
])
def test_지병이_하나라도_늘었는지(before, after, added):
    assert conditions_added(before, after) is added
