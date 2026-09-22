import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.phone_number import (
    format_phone,
    mask_phone,
    normalize_phone,
    phone_last4,
)


@pytest.mark.parametrize(
    "raw, digits",
    [
        ("010-1234-5678", "01012345678"),
        (" 010 1234 5678 ", "01012345678"),
        ("011-123-4567", "0111234567"),
        ("02-123-4567", "021234567"),
        ("(02) 1234-5678", "0212345678"),
        ("031-123-4567", "0311234567"),
        ("064-7123-4567", "06471234567"),
        ("070-1234-5678", "07012345678"),
    ],
)
def test_숫자만_남기고_한국_번호_형식을_받는다(raw, digits):
    assert normalize_phone(raw) == digits


@pytest.mark.parametrize(
    "raw",
    ["", "1234", "010-123-456", "010-1234-56789", "012-1234-5678", "080-123-4567",
     "+82 10-1234-5678", "０１０-1234-5678", "010-abcd-5678"],
)
def test_형식이_아니면_VALIDATION_ERROR_다(raw):
    with pytest.raises(CustomerInputError) as caught:
        normalize_phone(raw)
    assert caught.value.code == "VALIDATION_ERROR"


def test_오류_문구에_입력한_번호를_담지_않는다():
    with pytest.raises(CustomerInputError) as caught:
        normalize_phone("010-1234")
    assert "1234" not in str(caught.value)


def test_하이픈_모양으로_보여_준다():
    assert format_phone("01012345678") == "010-1234-5678"
    assert format_phone("0111234567") == "011-123-4567"
    assert format_phone("021234567") == "02-123-4567"
    assert format_phone("0212345678") == "02-1234-5678"


def test_가운데_자리의_앞_두_글자만_남기고_가린다():
    assert mask_phone("01012345678") == "010-12··-5678"
    assert mask_phone("0111234567") == "011-12·-4567"
    assert mask_phone("021234567") == "02-12·-4567"
    assert mask_phone("0212345678") == "02-12··-5678"


def test_뒷자리_네_개():
    assert phone_last4("01012345678") == "5678"
