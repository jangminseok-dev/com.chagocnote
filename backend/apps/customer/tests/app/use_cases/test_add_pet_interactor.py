import pytest

from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.use_cases.add_pet_interactor import AddPetInteractor
from customer.domain.errors import CustomerNotFoundError, PetHealthConflictError
from customer.tests.helpers.fakes import FakeEvents, family, today
from customer.tests.helpers.inputs import pet_input
from customer.tests.helpers.profiles import condition, ctx


def _setup(shop_id=1):
    journal, customers, pets, types, search = family()
    customer = customers.seed(shop_id=shop_id)
    pets.seed(customer.id, "콩이")
    return journal, customer, AddPetInteractor(customers, pets, types, search, today, events=FakeEvents())


async def test_고객을_잠근_뒤_반려동물을_더하고_상세를_돌려준다():
    journal, customer, interactor = _setup()
    view = await interactor.add_pet(AddPetCommand(ctx=ctx(), customer_id=customer.id,
                                                  pet=pet_input(name="두부", species="cat")))
    assert (view.pet.name, view.pet.species, view.owner.phone_masked) == ("두부", "cat", "010-12··-5678")
    assert [s.name for s in view.siblings] == ["콩이"]
    assert journal == [("lock_customer", customer.id), ("add_pet", customer.id), ("rebuild", customer.id)]


async def test_질병_규칙을_어기면_잠그지도_않는다():
    journal, customer, interactor = _setup()
    with pytest.raises(PetHealthConflictError):
        await interactor.add_pet(AddPetCommand(
            ctx=ctx(), customer_id=customer.id,
            pet=pet_input(no_known_conditions=True, conditions=(condition("allergy"),)),
        ))
    assert journal == []


async def test_다른_매장_고객이면_404_다():
    journal, customer, interactor = _setup(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await interactor.add_pet(AddPetCommand(ctx=ctx(shop_id=1), customer_id=customer.id, pet=pet_input()))
    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_더하면_그_아이를_다시_색인하라고_알린다():
    _, customers, pets, types, search = family()
    customer = customers.seed()
    events = FakeEvents()
    view = await AddPetInteractor(customers, pets, types, search, today, events=events).add_pet(
        AddPetCommand(ctx=ctx(), customer_id=customer.id, pet=pet_input(name="두부")))
    assert events.changed == [("pet", view.pet.pet_id)]
