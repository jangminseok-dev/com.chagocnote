import pytest
from sqlalchemy import text

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError
from customer.tests.helpers.profiles import condition, ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_등록한_고객을_컨텍스트의_매장에서만_읽는다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile(phone_alt="021234567", memo="오전 선호"))
    assert (created.shop_id, created.name, created.phone, created.phone_alt, created.memo) == (
        1, "김민지", "01012345678", "021234567", "오전 선호",
    )
    assert (await repo.get_active(A, created.id)).id == created.id
    with pytest.raises(CustomerNotFoundError):
        await repo.get_active(B, created.id)
    with pytest.raises(CustomerNotFoundError):
        await repo.lock_active(B, created.id)
    assert await repo.find_active_by_phone(B, "01012345678") is None
    assert await repo.list_active(B, [created.id]) == []


async def test_같은_매장의_살아_있는_번호는_CUSTOMER_PHONE_TAKEN_이다(db_session):
    repo = CustomerPgRepository(db_session)
    await repo.create(A, customer_profile())
    with pytest.raises(CustomerPhoneTakenError):
        await repo.create(A, customer_profile(name="다른 사람"))
    # 세이브포인트로 되돌렸으니 같은 트랜잭션을 계속 쓸 수 있다. 다른 매장은 같은 번호를 쓸 수 있다.
    assert (await repo.create(B, customer_profile())).shop_id == 2


async def test_번호를_바꾸다_겹치면_CUSTOMER_PHONE_TAKEN_이다(db_session):
    repo = CustomerPgRepository(db_session)
    first = await repo.create(A, customer_profile())
    second = await repo.create(A, customer_profile(phone="01099998888"))
    with pytest.raises(CustomerPhoneTakenError):
        await repo.update(A, second.id, customer_profile(phone=first.phone), consent_changed=False)
    assert (await repo.get_active(A, second.id)).phone == "01099998888"


async def test_동의가_바뀔_때만_동의_시각을_새로_찍는다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile())
    await db_session.execute(
        text("UPDATE customers SET marketing_consent_changed_at = now() - interval '1 day'")
    )
    kept = await repo.update(A, created.id, customer_profile(memo="메모"), consent_changed=False)
    changed = await repo.update(A, created.id, customer_profile(marketing_consent=True), consent_changed=True)
    assert kept.marketing_consent_changed_at < changed.marketing_consent_changed_at
    assert changed.marketing_consent is True


async def test_다른_매장의_고객은_고치지_못한다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile())
    with pytest.raises(CustomerNotFoundError):
        await repo.update(B, created.id, customer_profile(name="빼앗은 이름"), consent_changed=False)
    assert (await repo.get_active(A, created.id)).name == "김민지"


async def test_익명화는_개인정보만_지우고_틀을_남긴다(db_session):
    customers, pets = CustomerPgRepository(db_session), PetPgRepository(db_session)
    created = await customers.create(A, customer_profile(phone_alt="021234567", memo="메모"))
    await pets.add(A, created.id, pet_profile(memo="겁이 많음", no_known_conditions=False,
                                              conditions=(condition("allergy", note="닭고기"),)))
    await customers.anonymize(A, created.id)

    with pytest.raises(CustomerNotFoundError):
        await customers.get_active(A, created.id)
    row = (await db_session.execute(text(
        "SELECT name, phone, phone_alt, memo, deleted_at IS NOT NULL FROM customers"
    ))).one()
    assert tuple(row) == (None, None, None, None, True)
    pet = (await db_session.execute(text("SELECT name, memo, species, breed FROM pets"))).one()
    assert tuple(pet) == (None, None, "dog", "말티즈")
    assert (await db_session.execute(text("SELECT count(*) FROM pet_conditions"))).scalar_one() == 0
    # 익명화한 번호로 다시 등록하면 새 고객이다.
    again = await customers.create(A, customer_profile())
    assert again.id != created.id


async def test_다른_매장의_익명화는_아무것도_지우지_않는다(db_session):
    customers, pets = CustomerPgRepository(db_session), PetPgRepository(db_session)
    created = await customers.create(A, customer_profile())
    pet = await pets.add(A, created.id, pet_profile(no_known_conditions=False,
                                                     conditions=(condition("allergy"),)))
    await customers.anonymize(B, created.id)
    assert (await customers.get_active(A, created.id)).name == "김민지"
    # B 매장 컨텍스트로 부른 익명화가 A 매장 고객의 반려동물·질병까지 지우면 안 된다.
    kept = await pets.get(A, pet.id)
    assert kept.name == "콩이"
    assert len(kept.conditions) == 1


async def test_주의_표시를_달고_고치고_푼다_다른_매장은_건드리지_못한다(db_session):
    from datetime import date

    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile())
    await db_session.execute(text("UPDATE customers SET updated_at = now() - interval '1 day'"))
    before = (await db_session.execute(text("SELECT updated_at FROM customers"))).scalar_one()

    marked = await repo.set_caution(A, created.id, "노쇼 2번", date(2027, 11, 14), 42)
    assert (marked.caution_reason, marked.caution_until) == ("노쇼 2번", date(2027, 11, 14))
    row = (await db_session.execute(text(
        "SELECT caution_set_at IS NOT NULL, caution_set_by_member_id, updated_at FROM customers"
    ))).one()
    assert tuple(row) == (True, 42, before)   # 주의 표시는 '수정'이 아니다 — 최근순을 흔들지 않는다

    with pytest.raises(CustomerNotFoundError):
        await repo.set_caution(B, created.id, "남의 매장", date(2027, 1, 1), 7)
    assert (await repo.get_active(A, created.id)).caution_reason == "노쇼 2번"

    cleared = await repo.set_caution(A, created.id, None, None, None)
    assert (cleared.caution_reason, cleared.caution_until) == (None, None)
    row = (await db_session.execute(text(
        "SELECT caution_reason, caution_until, caution_set_at, caution_set_by_member_id FROM customers"
    ))).one()
    assert tuple(row) == (None, None, None, None)


async def test_익명화는_주의_표시와_미용_동의도_지운다(db_session):
    from datetime import date

    customers, pets = CustomerPgRepository(db_session), PetPgRepository(db_session)
    created = await customers.create(A, customer_profile())
    pet = await pets.add(A, created.id, pet_profile())
    other = await customers.create(B, customer_profile())
    other_pet = await pets.add(B, other.id, pet_profile())
    for shop, customer, animal in ((A, created, pet), (B, other, other_pet)):
        await customers.set_caution(shop, customer.id, "입질", date(2027, 1, 1), 11)
        await pets.set_grooming_consent(shop, animal.id, date(2026, 3, 1), 11)

    await customers.anonymize(A, created.id)

    row = (await db_session.execute(text(
        "SELECT caution_reason, caution_until, caution_set_at, caution_set_by_member_id "
        "FROM customers WHERE id = :id"
    ), {"id": created.id})).one()
    assert tuple(row) == (None, None, None, None)
    consent = (await db_session.execute(text(
        "SELECT grooming_consent_on, grooming_consent_by_member_id FROM pets WHERE id = :id"
    ), {"id": pet.id})).one()
    assert tuple(consent) == (None, None)
    # 다른 매장의 것은 그대로다.
    assert (await customers.get_active(B, other.id)).caution_reason == "입질"
    assert (await pets.get(B, other_pet.id)).grooming_consent_on == date(2026, 3, 1)
