"""매장이 고친 동의서 글의 규칙(⑪-B)."""
import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.consent_text import BODY_MAX, check_body


@pytest.mark.parametrize("body", ["한 줄", "가" * BODY_MAX, "첫 줄\n둘째 줄"])
def test_글자가_있고_2000자_안이면_받는다(body):
    check_body(body)


@pytest.mark.parametrize("body", ["", "   ", "\n\n", "가" * (BODY_MAX + 1)])
def test_빈_글과_넘치는_글은_받지_않는다(body):
    with pytest.raises(CustomerInputError):
        check_body(body)


def test_오류_글에_매장이_적은_글이_들어가지_않는다():
    with pytest.raises(CustomerInputError) as caught:
        check_body("비밀" * 1500)
    assert "비밀" not in str(caught.value)
