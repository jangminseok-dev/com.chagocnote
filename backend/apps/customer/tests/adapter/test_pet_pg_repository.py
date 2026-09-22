from datetime import date
from decimal import Decimal

import pytest

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.profiles import condition, ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _family(session, shop=A, phone="01012345678"):
    customer = await CustomerPgRepository(session).create(shop, customer_profile(phone=phone))
    return customer.id


async def test_반려동물과_질병을_넣고_종류_순서대로_읽는다(db_session):
    repo = PetPgRepository(db_session)
    customer_id = await _family(db_session)
    pet = await repo.add(A, customer_id, pet_profile(
        birth_year=None, birth_date=date(2021, 3, 1), weight_kg=Decimal("12.5"),
        no_known_conditions=False,
        conditions=(condition("other", "눈물 자국"), condition("patella_luxation", note="2기")),
    ))
    assert (pet.name, pet.birth_date, pet.weight_kg, pet.has_conditions) == (
        "콩이", date(2021, 3, 1), Decimal("12.5"), True,
    )
    assert [(c.type_code, c.label, c.custom_label, c.note) for c in pet.conditions] == [
        ("patella_luxation", "슬개골 탈구", None, "2기"), ("other", "기타", "눈물 자국", None),
    ]


async def test_다른_매장에서는_반려동물이_없는_것과_같다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile(
        no_known_conditions=False, conditions=(condition("allergy"),),
    ))
    with pytest.raises(PetNotFoundError):
        await repo.get(B, pet.id)
    with pytest.raises(PetNotFoundError):
        await repo.lock_owner(B, pet.id)
    assert await repo.list_for_customers(B, [pet.customer_id]) == []
    assert await repo.count_for_customer(B, pet.customer_id) == 0
    await repo.delete(B, pet.id)
    with pytest.raises(PetNotFoundError):
        await repo.update(B, pet.id, pet_profile(name="빼앗은 이름"))
    with pytest.raises(PetNotFoundError):
        await repo.set_passed_away(B, pet.id, True)
    kept = await repo.get(A, pet.id)
    assert kept.name == "콩이"
    # B 매장에서의 실패한 update 시도가 질병 행을 지우고 실패로 되돌리지 못한 채 남기면 안 된다.
    assert [c.type_code for c in kept.conditions] == ["allergy"]


async def test_다른_매장_고객에게_반려동물을_붙이면_404_다(db_session):
    repo = PetPgRepository(db_session)
    customer_id = await _family(db_session, shop=A)
    with pytest.raises(PetNotFoundError):
        await repo.add(B, customer_id, pet_profile())


async def test_수정은_질병_목록을_통째로_바꾼다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile(
        no_known_conditions=False, conditions=(condition("allergy"),),
    ))
    updated = await repo.update(A, pet.id, pet_profile(
        name="콩순이", no_known_conditions=False,
        conditions=(condition("heart_disease"), condition("allergy", note="닭고기")),
    ))
    assert updated.name == "콩순이"
    assert [(c.type_code, c.note) for c in updated.conditions] == [
        ("heart_disease", None), ("allergy", "닭고기"),
    ]
    cleared = await repo.update(A, pet.id, pet_profile(no_known_conditions=True, conditions=()))
    assert (cleared.conditions, cleared.no_known_conditions) == ((), True)


async def test_무지개다리는_처음_시각을_지키고_되돌릴_수_있다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile())
    first = await repo.set_passed_away(A, pet.id, True)
    again = await repo.set_passed_away(A, pet.id, True)
    assert first.passed_away and again.passed_away_at == first.passed_away_at
    assert (await repo.set_passed_away(A, pet.id, False)).passed_away is False


async def test_삭제하면_질병도_함께_지워지고_수를_센다(db_session):
    repo = PetPgRepository(db_session)
    customer_id = await _family(db_session)
    first = await repo.add(A, customer_id, pet_profile(no_known_conditions=False,
                                                       conditions=(condition("allergy"),)))
    await repo.add(A, customer_id, pet_profile(name="두부"))
    assert await repo.count_for_customer(A, customer_id) == 2
    await repo.delete(A, first.id)
    assert await repo.count_for_customer(A, customer_id) == 1
    assert [p.name for p in await repo.list_for_customers(A, [customer_id])] == ["두부"]


async def test_익명화한_고객의_반려동물은_없는_것과_같다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile())
    await CustomerPgRepository(db_session).anonymize(A, pet.customer_id)
    with pytest.raises(PetNotFoundError):
        await repo.get(A, pet.id)
    with pytest.raises(PetNotFoundError):
        await repo.lock_owner(A, pet.id)


async def test_질병_종류는_칩_순서대로다(db_session):
    types = await ConditionTypePgRepository(db_session).list_all()
    assert [t.code for t in types][:2] == ["patella_luxation", "heart_disease"]
    assert (types[-1].code, types[-1].label) == ("other", "기타")
