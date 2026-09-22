from datetime import date
from decimal import Decimal

import pytest

from customer.domain.errors import CustomerInputError, PetHealthRequiredError
from customer.domain.value_objects.customer_profile import CustomerProfile
from customer.domain.value_objects.pet_profile import PetProfile


def test_보호자_번호와_보조_연락처를_숫자만으로_바꾼다():
    profile = CustomerProfile.create(
        name="김민지", phone="010-1234-5678", phone_alt="02-123-4567",
        marketing_consent=True, memo=None,
    )
    assert (profile.phone, profile.phone_alt) == ("01012345678", "021234567")


def test_보조_연락처도_형식을_본다():
    with pytest.raises(CustomerInputError):
        CustomerProfile.create(name="김민지", phone="01012345678", phone_alt="123",
                               marketing_consent=False, memo=None)


def _pet(**overrides):
    fields = dict(
        name="콩이", species="dog", breed="말티즈", sex="female", neutered=True,
        birth_date=None, birth_year=2021, weight_kg=Decimal("3.2"), no_known_conditions=True,
        memo=None, conditions=(), known_condition_codes=frozenset({"other"}),
        today=date(2026, 9, 22),
    )
    fields.update(overrides)
    return PetProfile.create(**fields)


def test_반려동물은_나이와_질병_규칙을_둘_다_거친다():
    assert _pet().birth_year == 2021
    with pytest.raises(CustomerInputError):
        _pet(birth_date=date(2021, 1, 1))
    with pytest.raises(PetHealthRequiredError):
        _pet(no_known_conditions=False)
