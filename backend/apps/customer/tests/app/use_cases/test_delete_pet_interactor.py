import pytest

from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.domain.errors import LastPetError, PetHasVisitsError, PetNotFoundError
from customer.tests.helpers.fakes import FakeEvents, FakeLedger, family
from customer.tests.helpers.profiles import ctx


async def test_고객을_잠근_뒤_세고_지우고_검색_줄을_다시_만든다():
    journal, customers, pets, _, search = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "두부")
    await DeletePetInteractor(pets, search, FakeLedger(journal), events=FakeEvents()).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
    assert journal == [("lock_customer", customer.id), ("delete_pet", kong.id), ("rebuild", customer.id)]


async def test_마지막_반려동물이면_LAST_PET_이다():
    journal, customers, pets, _, search = family()
    only = pets.seed(customers.seed().id)
    with pytest.raises(LastPetError):
        await DeletePetInteractor(pets, search, FakeLedger(journal), events=FakeEvents()).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=only.id))
    assert only.id in pets.rows
    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_무지개다리인_아이도_수에_들어간다():
    """무지개다리 아이가 남아 있으면 마지막이 아니다 — 가족 기록이 남는다."""
    journal, customers, pets, _, search = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    await DeletePetInteractor(pets, search, FakeLedger(journal), events=FakeEvents()).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
    assert kong.id not in pets.rows


async def test_다른_매장의_반려동물은_404_다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await DeletePetInteractor(pets, search, FakeLedger(journal), events=FakeEvents()).delete_pet(DeletePetCommand(ctx=ctx(shop_id=1), pet_id=pet.id))


async def test_방문_기록이_있는_반려동물은_PET_HAS_VISITS_다():
    """취소된 방문만 있어도 지우지 않는다 — 무지개다리를 쓴다. 고객 행을 잠근 뒤에 묻는다."""
    journal, customers, pets, _, search = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "두부")
    ledger = FakeLedger(journal)
    ledger.pets_with_visits.add(kong.id)
    with pytest.raises(PetHasVisitsError):
        await DeletePetInteractor(pets, search, ledger, events=FakeEvents()).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
    assert kong.id in pets.rows
    assert journal == [("lock_customer", customer.id)]


async def test_지우면_그_아이를_다시_색인하라고_알린다():
    """색인기가 빈 목록을 읽고 그 아이의 특이사항·지병 문서를 지운다."""
    journal, customers, pets, _, search = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "두부")
    events = FakeEvents()
    await DeletePetInteractor(pets, search, FakeLedger(journal), events=events).delete_pet(
        DeletePetCommand(ctx=ctx(), pet_id=kong.id))
    assert events.changed == [("pet", kong.id)]
