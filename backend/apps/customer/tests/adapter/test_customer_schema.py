import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


async def test_질병_종류_시드가_설계_순서대로_들어_있다(db_session):
    rows = (
        await db_session.execute(
            text("SELECT code, label FROM pet_condition_types ORDER BY sort_order")
        )
    ).all()
    assert rows == [
        ("patella_luxation", "슬개골 탈구"), ("heart_disease", "심장 질환"),
        ("skin_disease", "피부병"), ("arthritis", "관절염"), ("allergy", "알레르기"),
        ("ear_disease", "귀 질환"), ("disc_disease", "디스크"), ("seizure", "발작·뇌전증"),
        ("diabetes", "당뇨"), ("other", "기타"),
    ]


async def test_pg_trgm_확장이_켜져_있다(db_session):
    installed = (
        await db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
    ).scalar()
    assert installed == 1


async def _insert_customer(session, shop_id=1, phone="01012345678", deleted=False):
    row = await session.execute(
        text(
            "INSERT INTO customers (shop_id, name, phone, marketing_consent, "
            "marketing_consent_changed_at, deleted_at) "
            "VALUES (:shop, '김민지', :phone, false, now(), CASE WHEN :deleted THEN now() END) "
            "RETURNING id"
        ),
        {"shop": shop_id, "phone": phone, "deleted": deleted},
    )
    return row.scalar_one()


async def _violates(session, sql, **params) -> str:
    """제약 위반이 일어나는지 세이브포인트 안에서 보고, 걸린 제약 이름을 돌려준다."""
    with pytest.raises(IntegrityError) as caught:
        async with session.begin_nested():
            await session.execute(text(sql), params)
    return caught.value.orig.__cause__.constraint_name


async def test_살아_있는_고객의_번호는_매장_안에서_하나다(db_session):
    await _insert_customer(db_session)
    await _insert_customer(db_session, shop_id=2)                     # 다른 매장은 괜찮다
    await _insert_customer(db_session, deleted=True)                  # 익명화한 고객과는 겹쳐도 된다
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await _insert_customer(db_session)


async def test_살아_있는_고객은_이름과_번호가_있어야_한다(db_session):
    name = await _violates(
        db_session,
        "INSERT INTO customers (shop_id, name, phone, marketing_consent, marketing_consent_changed_at) "
        "VALUES (1, NULL, '01012345678', false, now())",
    )
    assert name == "ck_customers_alive_has_name_phone"


async def test_반려동물_CHECK_제약(db_session):
    customer_id = await _insert_customer(db_session)
    base = (
        "INSERT INTO pets (customer_id, name, species, breed, sex, neutered, birth_date, birth_year, "
        "weight_kg, no_known_conditions) VALUES (:c, '콩이', :species, '말티즈', :sex, true, "
        ":birth_date, :birth_year, :weight, true)"
    )
    ok = dict(c=customer_id, species="dog", sex="female", birth_date=None, birth_year=None, weight=3.2)
    await db_session.execute(text(base), ok)   # 나이 모름은 된다
    from datetime import date

    cases = [
        ({"species": "bird"}, "ck_pets_species"),
        ({"sex": "unknown"}, "ck_pets_sex"),
        ({"weight": 0}, "ck_pets_weight_positive"),
        ({"birth_date": date(2020, 1, 1), "birth_year": 2020}, "ck_pets_one_birth_field"),
    ]
    for override, constraint in cases:
        assert await _violates(db_session, base, **{**ok, **override}) == constraint


async def test_질병_행_제약(db_session):
    customer_id = await _insert_customer(db_session)
    pet_id = (
        await db_session.execute(
            text(
                "INSERT INTO pets (customer_id, name, species, breed, sex, neutered, weight_kg, "
                "no_known_conditions) VALUES (:c, '콩이', 'dog', '말티즈', 'female', true, 3.2, false) "
                "RETURNING id"
            ),
            {"c": customer_id},
        )
    ).scalar_one()
    insert = "INSERT INTO pet_conditions (pet_id, type_code, custom_label) VALUES (:p, :code, :label)"
    await db_session.execute(text(insert), {"p": pet_id, "code": "other", "label": "기침"})
    await db_session.execute(text(insert), {"p": pet_id, "code": "other", "label": "눈물"})   # 기타는 여러 개
    await db_session.execute(text(insert), {"p": pet_id, "code": "allergy", "label": None})

    assert await _violates(db_session, insert, p=pet_id, code="allergy", label=None) == "uq_pet_conditions_pet_type"
    assert await _violates(db_session, insert, p=pet_id, code="other", label=None) == "ck_pet_conditions_other_label"
    assert await _violates(db_session, insert, p=pet_id, code="arthritis", label="관절") == "ck_pet_conditions_other_label"
