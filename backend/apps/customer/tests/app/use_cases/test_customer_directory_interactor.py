from datetime import datetime, timezone
from decimal import Decimal

import pytest

from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.domain.errors import CustomerNotFoundError, PetNotFoundError, PetPassedAwayError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx
from hub.app.dtos.family_brief import CustomerBrief, PetBrief


class _FakeBriefs:
    def __init__(self):
        self.calls = []

    async def list_customer_briefs(self, ctx, customer_ids):
        self.calls.append(("customers", customer_ids))
        return [CustomerBrief(customer_id=i, name=None, phone_masked=None) for i in customer_ids]

    async def list_pet_briefs(self, ctx, pet_ids):
        self.calls.append(("pets", pet_ids))
        return [PetBrief(pet_id=i, customer_id=1, name=None, species="dog", breed="말티즈",
                         weight_kg=Decimal("3.2"), passed_away=False) for i in pet_ids]


def _directory():
    journal, customers, pets, _, search = family()
    briefs = _FakeBriefs()
    return journal, customers, pets, briefs, CustomerDirectoryInteractor(customers, pets, briefs, search)


async def test_고객_행을_잠그고_반려동물이_그_가족인지_본다():
    journal, customers, pets, _, directory = _directory()
    customer = customers.seed()
    kong, dubu = pets.seed(customer.id, "콩이"), pets.seed(customer.id, "두부")
    await directory.lock_family(ctx(), customer.id, (kong.id, dubu.id))
    assert journal == [("lock_customer", customer.id)]


async def test_반려동물_없이_보호자만_잠글_수_있다():
    journal, customers, _, _, directory = _directory()
    customer = customers.seed()
    await directory.lock_family(ctx(), customer.id, ())
    assert journal == [("lock_customer", customer.id)]


async def test_다른_보호자의_반려동물이면_PET_NOT_FOUND_다():
    """V2 — 같은 매장이라도 다른 가족의 아이를 끼워 넣을 수 없다."""
    _, customers, pets, _, directory = _directory()
    mine, theirs = customers.seed(), customers.seed(phone="01099998888")
    other_pet = pets.seed(theirs.id, "남의 아이")
    with pytest.raises(PetNotFoundError):
        await directory.lock_family(ctx(), mine.id, (other_pet.id,))


async def test_무지개다리_아이면_PET_PASSED_AWAY_다():
    _, customers, pets, _, directory = _directory()
    customer = customers.seed()
    star = pets.seed(customer.id, "별이", passed_away=True)
    with pytest.raises(PetPassedAwayError):
        await directory.lock_family(ctx(), customer.id, (star.id,))


async def test_다른_매장의_고객이면_CUSTOMER_NOT_FOUND_다():
    _, customers, _, _, directory = _directory()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await directory.lock_family(ctx(shop_id=1), customer.id, ())


async def test_요약은_ID_로_찾게_묶는다():
    _, _, _, briefs, directory = _directory()
    found = await directory.briefs(ctx(), [1, 2], [101])
    assert set(found.customers) == {1, 2} and set(found.pets) == {101}
    assert briefs.calls == [("customers", [1, 2]), ("pets", [101])]


async def test_빈_목록이면_읽지_않는다():
    _, _, _, briefs, directory = _directory()
    found = await directory.briefs(ctx(), [], [])
    assert (found.customers, found.pets, briefs.calls) == ({}, {}, [])


async def test_마지막_방문_시각은_검색_포트로_넘긴다():
    journal, _, _, _, directory = _directory()
    at = datetime(2026, 9, 23, 5, tzinfo=timezone.utc)
    await directory.set_last_visit(ctx(), 1, at)
    await directory.set_last_visit(ctx(), 1, None)
    assert journal == [("set_last_visit", 1, at), ("set_last_visit", 1, None)]
