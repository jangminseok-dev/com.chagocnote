from dataclasses import replace

from customer.app.use_cases.customer_search_source_interactor import CustomerSearchSourceInteractor
from customer.domain.entities.pet import PetCondition
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx
from hub.app.dtos.search_source import SourceDocument
from hub.app.ports.search_source_port import SearchSourcePort


def _world():
    _, customers, pets, _, _ = family()
    return customers, pets, CustomerSearchSourceInteractor(customers=customers, pets=pets)


def _condition(condition_id, label, note=None, custom=None):
    return PetCondition(type_code="etc" if custom else "heart_disease", label=label, custom_label=custom, note=note,
                        condition_id=condition_id)


async def test_반려동물의_특이사항과_지병이_문서가_된다():
    customers, pets, source = _world()
    owner = customers.seed()
    pet = pets.seed(owner.id, conditions=(
        _condition(41, "심장 질환", note="약 복용 중"), _condition(42, "슬개골 탈구"),
        _condition(43, "기타", note=" ", custom="췌장염"),
    ))
    pets.rows[pet.id] = replace(pet, memo="  드라이를 무서워해요 ")
    assert await source.documents(ctx(), "pet", pet.id) == [
        SourceDocument(kind="pet_memo", source_id=pet.id, customer_id=owner.id, pet_id=pet.id, visit_id=None,
                       happened_on=None, body="드라이를 무서워해요"),
        SourceDocument(kind="condition_note", source_id=41, customer_id=owner.id, pet_id=pet.id, visit_id=None,
                       happened_on=None, body="심장 질환 — 약 복용 중"),
        # 메모가 없어도 지병 이름만으로 문서가 된다 — 지병 이름으로 찾을 수 있게.
        SourceDocument(kind="condition_note", source_id=42, customer_id=owner.id, pet_id=pet.id, visit_id=None,
                       happened_on=None, body="슬개골 탈구"),
        # 기타는 적어 둔 이름을 쓴다.
        SourceDocument(kind="condition_note", source_id=43, customer_id=owner.id, pet_id=pet.id, visit_id=None,
                       happened_on=None, body="췌장염"),
    ]


async def test_특이사항이_비고_지병이_없으면_문서가_없다():
    customers, pets, source = _world()
    pet = pets.seed(customers.seed().id)
    assert await source.documents(ctx(), "pet", pet.id) == []


async def test_무지개다리를_건넌_아이의_글도_문서다():
    customers, pets, source = _world()
    pet = pets.seed(customers.seed().id, passed_away=True)
    pets.rows[pet.id] = replace(pets.rows[pet.id], memo="입질이 있었어요")
    assert [d.body for d in await source.documents(ctx(), "pet", pet.id)] == ["입질이 있었어요"]


async def test_보호자_메모가_문서가_된다():
    customers, _, source = _world()
    owner = customers.seed()
    customers.rows[owner.id] = replace(owner, memo=" 전화보다 문자를 원하심 ")
    blank = customers.seed(name="이수진", phone="01099998888")
    assert await source.documents(ctx(), "customer", owner.id) == [
        SourceDocument(kind="customer_memo", source_id=owner.id, customer_id=owner.id, pet_id=None, visit_id=None,
                       happened_on=None, body="전화보다 문자를 원하심"),
    ]
    assert await source.documents(ctx(), "customer", blank.id) == []


async def test_익명화한_고객과_그_아이는_빈_목록이다():
    customers, pets, source = _world()
    owner = customers.seed()
    customers.rows[owner.id] = replace(owner, memo="전화보다 문자를 원하심")
    pet = pets.seed(owner.id)
    pets.rows[pet.id] = replace(pet, memo="드라이를 무서워해요")
    await customers.anonymize(ctx(), owner.id)
    assert await source.documents(ctx(), "customer", owner.id) == []
    assert await source.documents(ctx(), "pet", pet.id) == []


async def test_다른_매장의_것과_없는_것과_다른_대상은_빈_목록이다():
    customers, pets, source = _world()
    owner = customers.seed()
    customers.rows[owner.id] = replace(owner, memo="전화보다 문자를 원하심")
    pet = pets.seed(owner.id)
    pets.rows[pet.id] = replace(pet, memo="드라이를 무서워해요")
    assert await source.documents(ctx(shop_id=2), "customer", owner.id) == []
    assert await source.documents(ctx(shop_id=2), "pet", pet.id) == []
    assert await source.documents(ctx(), "customer", 999) == []
    assert await source.documents(ctx(), "pet", 999) == []
    assert await source.documents(ctx(), "visit", pet.id) == []


def test_허브_포트의_구현이다():
    assert isinstance(_world()[2], SearchSourcePort)
