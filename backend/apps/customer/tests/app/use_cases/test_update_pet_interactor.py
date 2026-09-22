from datetime import date

import pytest

from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.use_cases.update_pet_interactor import UpdatePetInteractor
from customer.domain.errors import CustomerInputError, PetNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.inputs import pet_input
from customer.tests.helpers.profiles import condition, ctx


def _setup(shop_id=1):
    journal, customers, pets, types, search = family()
    pet = pets.seed(customers.seed(shop_id=shop_id).id)
    return journal, pet, UpdatePetInteractor(customers, pets, types, search, today)


async def test_고객을_잠근_뒤_고치고_검색_줄을_다시_만든다():
    journal, pet, interactor = _setup()
    view = await interactor.update_pet(UpdatePetCommand(
        ctx=ctx(), pet_id=pet.id,
        pet=pet_input(name="콩순이", no_known_conditions=False,
                      conditions=(condition("other", "눈물 자국"),)),
    ))
    assert view.pet.name == "콩순이"
    assert [(c.label, c.custom_label) for c in view.pet.conditions] == [("기타", "눈물 자국")]
    assert journal == [("lock_customer", pet.customer_id), ("update_pet", pet.id), ("rebuild", pet.customer_id)]


async def test_생일과_태어난_해를_함께_보내면_VALIDATION_ERROR_다():
    journal, pet, interactor = _setup()
    with pytest.raises(CustomerInputError):
        await interactor.update_pet(UpdatePetCommand(
            ctx=ctx(), pet_id=pet.id, pet=pet_input(birth_date=date(2021, 1, 1), birth_year=2021),
        ))
    assert journal == []


async def test_다른_매장의_반려동물은_404_다():
    journal, pet, interactor = _setup(shop_id=2)
    with pytest.raises(PetNotFoundError):
        await interactor.update_pet(UpdatePetCommand(ctx=ctx(shop_id=1), pet_id=pet.id, pet=pet_input()))
    assert journal == []
