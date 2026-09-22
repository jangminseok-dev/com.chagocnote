from datetime import date

import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.pet_age import age_label, check_birth

TODAY = date(2026, 9, 22)


def test_생일과_태어난_해는_하나만_받는다():
    check_birth(date(2020, 1, 1), None, TODAY)
    check_birth(None, 2020, TODAY)
    check_birth(None, None, TODAY)   # 모름
    with pytest.raises(CustomerInputError):
        check_birth(date(2020, 1, 1), 2020, TODAY)


@pytest.mark.parametrize(
    "birth_date, birth_year",
    [(date(2026, 9, 23), None), (date(1985, 1, 1), None), (None, 2027), (None, 1985)],
)
def test_미래이거나_너무_오래된_값은_VALIDATION_ERROR_다(birth_date, birth_year):
    with pytest.raises(CustomerInputError):
        check_birth(birth_date, birth_year, TODAY)


def test_오늘_태어났거나_올해_태어난_것은_받는다():
    assert check_birth(TODAY, None, TODAY) is None
    assert check_birth(None, 2026, TODAY) is None


def test_생일이_있으면_만_나이이고_한_살_전에는_개월이다():
    assert age_label(date(2023, 9, 22), None, TODAY) == "3살"
    assert age_label(date(2023, 9, 23), None, TODAY) == "2살"    # 생일 전날
    assert age_label(date(2026, 3, 10), None, TODAY) == "6개월"
    assert age_label(date(2026, 9, 1), None, TODAY) == "0개월"
    assert age_label(date(2025, 9, 23), None, TODAY) == "11개월"


def test_태어난_해만_있으면_해의_차이다():
    assert age_label(None, 2021, TODAY) == "5살"
    assert age_label(None, 2026, TODAY) == "1살 미만"


def test_둘_다_없으면_나이_모름이다():
    assert age_label(None, None, TODAY) == "나이 모름"
