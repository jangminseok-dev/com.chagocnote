import pytest

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _family(session, shop, phone="01012345678"):
    customer = await CustomerPgRepository(session).create(shop, customer_profile(phone=phone))
    pet = await PetPgRepository(session).add(shop, customer.id, pet_profile())
    return customer.id, pet.id


async def test_살아_있는_가족은_이름과_가린_번호를_돌려준다(db_session):
    customer_id, pet_id = await _family(db_session, A)
    repo = FamilyBriefPgRepository(db_session)
    [customer] = await repo.list_customer_briefs(A, [customer_id])
    assert (customer.name, customer.phone_masked) == ("김민지", "010-12··-5678")
    [pet] = await repo.list_pet_briefs(A, [pet_id])
    assert (pet.customer_id, pet.name, pet.species, pet.breed, pet.passed_away) == (
        customer_id, "콩이", "dog", "말티즈", False)


async def test_익명화한_가족도_틀은_돌려주고_이름은_비운다(db_session):
    customer_id, pet_id = await _family(db_session, A)
    await CustomerPgRepository(db_session).anonymize(A, customer_id)
    repo = FamilyBriefPgRepository(db_session)
    [customer] = await repo.list_customer_briefs(A, [customer_id])
    assert (customer.name, customer.phone_masked) == (None, None)
    [pet] = await repo.list_pet_briefs(A, [pet_id])
    assert (pet.name, pet.breed) == (None, "말티즈")


async def test_다른_매장의_ID_는_빠진다(db_session):
    """V1 — 다른 매장 방문이 가리키는 가족의 이름이 새지 않는다."""
    customer_id, pet_id = await _family(db_session, B)
    repo = FamilyBriefPgRepository(db_session)
    assert await repo.list_customer_briefs(A, [customer_id]) == []
    assert await repo.list_pet_briefs(A, [pet_id]) == []
