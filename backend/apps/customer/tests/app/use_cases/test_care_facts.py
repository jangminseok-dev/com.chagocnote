"""CustomerDirectoryPort.care_facts — 확인할 것의 재료(③-B). 매장 경계, 익명화, 기한 지난 주의."""
from dataclasses import replace
from datetime import date

from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.domain.entities.pet import PetCondition
from customer.tests.helpers.fakes import TODAY, FakeSearch, family
from customer.tests.helpers.profiles import ctx
from hub.app.dtos.care_facts import CautionFact, ConditionFact


def _directory(customers, pets, journal):
    return CustomerDirectoryInteractor(customers, pets, briefs=None, search=FakeSearch(journal))


async def test_아이의_나이_지병_동의와_보호자의_주의_표시를_돌려준다():
    journal, customers, pets, _, _ = family()
    owner = customers.seed()
    customers.rows[owner.id] = replace(owner, caution_reason="노쇼 2번", caution_until=date(2027, 1, 1))
    pet = pets.seed(owner.id, conditions=[
        PetCondition(type_code="heart_disease", label="심장 질환", custom_label=None, note="약 복용"),
        PetCondition(type_code="other", label="기타", custom_label="눈물 자국", note=None),
    ])
    pets.rows[pet.id] = replace(pets.rows[pet.id], grooming_consent_on=date(2026, 3, 1))

    facts = await _directory(customers, pets, journal).care_facts(ctx(), (owner.id,), (pet.id,), TODAY)

    assert facts.known_customers == {owner.id}
    assert facts.cautions == {owner.id: CautionFact(reason="노쇼 2번", until=date(2027, 1, 1))}
    fact = facts.pets[pet.id]
    assert (fact.customer_id, fact.birth_date, fact.birth_year, fact.consent_on, fact.passed_away) == (
        owner.id, None, 2021, date(2026, 3, 1), False,
    )
    # 기타는 직접 적은 이름으로, 정해진 종류는 종류의 이름으로.
    assert fact.conditions == (ConditionFact("심장 질환", "약 복용"), ConditionFact("눈물 자국", None))


async def test_기한이_지난_주의는_없고_끝나는_날_당일은_있다():
    journal, customers, pets, _, _ = family()
    ended, last_day = customers.seed(), customers.seed(phone="01099998888")
    customers.rows[ended.id] = replace(ended, caution_reason="옛일", caution_until=date(2026, 9, 21))
    customers.rows[last_day.id] = replace(last_day, caution_reason="오늘까지", caution_until=TODAY)

    facts = await _directory(customers, pets, journal).care_facts(ctx(), (ended.id, last_day.id), (), TODAY)

    assert set(facts.cautions) == {last_day.id}
    assert facts.known_customers == {ended.id, last_day.id}
    assert facts.pets == {}


async def test_다른_매장과_익명화한_고객과_그_아이는_빠진다():
    journal, customers, pets, _, _ = family()
    mine, other = customers.seed(), customers.seed(shop_id=2, phone="01055556666")
    customers.rows[other.id] = replace(other, caution_reason="남의 매장", caution_until=date(2027, 1, 1))
    my_pet, other_pet = pets.seed(mine.id), pets.seed(other.id)
    gone = customers.seed(phone="01077778888")
    gone_pet = pets.seed(gone.id)
    await customers.anonymize(ctx(), gone.id)

    facts = await _directory(customers, pets, journal).care_facts(
        ctx(shop_id=1), (mine.id, other.id, gone.id, 999), (my_pet.id, other_pet.id, gone_pet.id, 888), TODAY,
    )

    assert facts.known_customers == {mine.id}
    assert facts.cautions == {}
    assert set(facts.pets) == {my_pet.id}


async def test_묻지_않은_아이는_나오지_않고_무지개다리_아이는_표시와_함께_나온다():
    journal, customers, pets, _, _ = family()
    owner = customers.seed()
    asked, unasked = pets.seed(owner.id, passed_away=True), pets.seed(owner.id, name="두부")

    facts = await _directory(customers, pets, journal).care_facts(ctx(), (owner.id,), (asked.id,), TODAY)

    assert set(facts.pets) == {asked.id}
    assert facts.pets[asked.id].passed_away is True


async def test_고객을_주지_않으면_아무것도_읽지_않는다():
    journal, customers, pets, _, _ = family()
    facts = await _directory(customers, pets, journal).care_facts(ctx(), (), (101,), TODAY)
    assert (facts.known_customers, facts.cautions, facts.pets) == (frozenset(), {}, {})
