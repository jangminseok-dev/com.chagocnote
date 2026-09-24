import pytest

from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.use_cases.get_pet_interactor import GetPetInteractor
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.fakes import FakeLedger, FakeLibrary, family, today
from customer.tests.helpers.profiles import ctx


async def test_반려동물과_보호자_요약과_같은_보호자의_다른_아이를_돌려준다():
    journal, customers, pets, _, _ = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    view = await GetPetInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_pet(
        GetPetQuery(ctx=ctx(), pet_id=kong.id))
    assert (view.detail.pet.name, view.photo) == ("콩이", None)
    assert (view.detail.owner.name, view.detail.owner.phone_masked) == ("김민지", "010-12··-5678")
    assert [(s.name, s.passed_away) for s in view.detail.siblings] == [("별이", True)]


async def test_다른_매장의_반려동물은_404_다():
    journal, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await GetPetInteractor(customers, pets, FakeLedger(journal), FakeLibrary(), today).get_pet(
            GetPetQuery(ctx=ctx(shop_id=1), pet_id=pet.id))


async def test_가장_최근_완료_기록의_대표_사진이_프로필_사진이다():
    journal, customers, pets, _, _ = family()
    kong = pets.seed(customers.seed().id, "콩이")
    ledger, library = FakeLedger(journal), FakeLibrary()
    ledger.covers, library.ready = {kong.id: 51}, {51}
    view = await GetPetInteractor(customers, pets, ledger, library, today).get_pet(GetPetQuery(ctx=ctx(), pet_id=kong.id))
    assert view.photo == "t/51"
