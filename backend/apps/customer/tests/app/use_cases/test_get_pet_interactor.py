import pytest

from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.use_cases.get_pet_interactor import GetPetInteractor
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_반려동물과_보호자_요약과_같은_보호자의_다른_아이를_돌려준다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    view = await GetPetInteractor(customers, pets, today).get_pet(GetPetQuery(ctx=ctx(), pet_id=kong.id))
    assert view.pet.name == "콩이"
    assert (view.owner.name, view.owner.phone_masked) == ("김민지", "010-12··-5678")
    assert [(s.name, s.passed_away) for s in view.siblings] == [("별이", True)]


async def test_다른_매장의_반려동물은_404_다():
    _, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await GetPetInteractor(customers, pets, today).get_pet(GetPetQuery(ctx=ctx(shop_id=1), pet_id=pet.id))
