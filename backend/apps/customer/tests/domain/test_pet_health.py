import pytest

from customer.domain.errors import (
    CustomerInputError,
    PetHealthConflictError,
    PetHealthRequiredError,
)
from customer.domain.services.pet_health import check_conditions
from customer.domain.value_objects.condition_entry import ConditionEntry

CODES = frozenset({"patella_luxation", "heart_disease", "other"})


def _entry(code, custom=None, note=None):
    return ConditionEntry(type_code=code, custom_label=custom, note=note)


def test_질병이_있거나_질병_없음을_확인했으면_통과한다():
    assert check_conditions((_entry("patella_luxation", note="2기"),), False, CODES) is None
    assert check_conditions((), True, CODES) is None


def test_둘_다_아니면_PET_HEALTH_REQUIRED_다():
    with pytest.raises(PetHealthRequiredError):
        check_conditions((), False, CODES)


def test_둘_다면_PET_HEALTH_CONFLICT_다():
    with pytest.raises(PetHealthConflictError):
        check_conditions((_entry("heart_disease"),), True, CODES)


def test_기타는_이름이_있어야_하고_여러_개일_수_있다():
    check_conditions((_entry("other", "눈물 자국"), _entry("other", "기침")), False, CODES)
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("other"),), False, CODES)


def test_정해진_질병에는_이름을_직접_넣지_않는다():
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("heart_disease", "심장"),), False, CODES)


def test_같은_정해진_질병을_두_번_넣을_수_없다():
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("heart_disease"), _entry("heart_disease")), False, CODES)


def test_모르는_종류는_VALIDATION_ERROR_다():
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("flu"),), False, CODES)
