from datetime import datetime, timezone
from decimal import Decimal

import pytest

from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx
from hub.app.dtos.customer_contact import CustomerContact
from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError


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


async def test_다른_보호자의_반려동물이면_허브_오류_PET_NOT_FOUND_다():
    """V2 — 같은 매장이라도 다른 가족의 아이를 끼워 넣을 수 없다."""
    _, customers, pets, _, directory = _directory()
    mine, theirs = customers.seed(), customers.seed(phone="01099998888")
    other_pet = pets.seed(theirs.id, "남의 아이")
    with pytest.raises(FamilyPetNotFoundError):
        await directory.lock_family(ctx(), mine.id, (other_pet.id,))


async def test_무지개다리_아이면_허브_오류_PET_PASSED_AWAY_다():
    _, customers, pets, _, directory = _directory()
    customer = customers.seed()
    star = pets.seed(customer.id, "별이", passed_away=True)
    with pytest.raises(FamilyPetPassedAwayError):
        await directory.lock_family(ctx(), customer.id, (star.id,))


async def test_다른_매장의_고객이면_허브_오류_CUSTOMER_NOT_FOUND_다():
    _, customers, _, _, directory = _directory()
    customer = customers.seed(shop_id=2)
    with pytest.raises(FamilyNotFoundError):
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


# --- 카톡 초안 후보(find_draft_candidates) ---


def _directory_with_search():
    journal, customers, pets, _, search = family()
    return journal, customers, pets, search, CustomerDirectoryInteractor(customers, pets, _FakeBriefs(), search)


async def test_낱말이_없으면_검색을_부르지_않고_빈_목록이다():
    journal, _, _, _, directory = _directory_with_search()
    assert await directory.find_draft_candidates(ctx(), ()) == []
    assert journal == []


async def test_반려동물_이름_정확_일치가_보호자_이름_전화_부분_일치보다_앞선다():
    _, customers, pets, search, directory = _directory_with_search()
    partial = customers.seed(name="콩순이맘", phone="01000000001")     # "콩" 부분 일치뿐
    by_phone = customers.seed(name="박서준", phone="01098765678")      # 뒷자리 5678
    by_owner = customers.seed(name="김민지", phone="01000000003")      # 보호자 이름
    by_pet = customers.seed(name="이하나", phone="01000000004")        # 반려동물 이름
    pets.seed(by_pet.id, "콩이"), pets.seed(by_pet.id, "두부"), pets.seed(partial.id, "콩")
    search.matches = [partial.id, by_phone.id, by_owner.id, by_pet.id]

    found = await directory.find_draft_candidates(ctx(), ("콩이", "김민지", "5678"))

    assert [c.customer.customer_id for c in found] == [by_pet.id, by_owner.id, by_phone.id, partial.id]
    assert [c.exact for c in found] == [True, True, False, False]
    kong = next(p.id for p in pets.rows.values() if p.name == "콩이")
    assert found[0].matched_pet_ids == (kong,)
    assert [p.name for p in found[0].pets] == ["콩이", "두부"]
    assert found[0].customer.phone_masked == "010-00··-0004"


async def test_전체_번호_8자리_이상은_포함으로_맞춘다():
    _, customers, _, search, directory = _directory_with_search()
    partial = customers.seed(name="박서준맘", phone="01000000002")     # 전화도 이름도 부분 일치뿐(rank 3)
    customer = customers.seed(name="박서준", phone="01098765678")
    search.matches = [partial.id, customer.id]

    found = await directory.find_draft_candidates(ctx(), ("01098765678",))
    assert (found[0].customer.customer_id, found[0].exact) == (customer.id, False)

    found_hyphen = await directory.find_draft_candidates(ctx(), ("010-9876-5678",))
    assert [c.customer.customer_id for c in found_hyphen] == [customer.id, partial.id]
    assert found_hyphen[0].exact is False


async def test_후보는_다섯_가족까지_ID_오름차순이다():
    _, customers, _, search, directory = _directory_with_search()
    ids = [customers.seed(name=f"보호자{i}", phone=f"0100000000{i}").id for i in range(7)]
    search.matches = ids
    found = await directory.find_draft_candidates(ctx(), ("보호자",))
    assert [c.customer.customer_id for c in found] == ids[:5]


async def test_검색은_낱말을_OR_로_20가족까지_묻는다():
    journal, _, _, _, directory = _directory_with_search()
    await directory.find_draft_candidates(ctx(), ("콩이", "010-1234-5678"))
    assert journal == [("match_any", ("콩이", "01012345678"), 20)]


async def test_무지개다리_아이는_후보의_반려동물에서_빠진다():
    _, customers, pets, search, directory = _directory_with_search()
    customer = customers.seed()
    pets.seed(customer.id, "콩이", passed_away=True)
    pets.seed(customer.id, "두부")
    search.matches = [customer.id]
    found = await directory.find_draft_candidates(ctx(), ("콩이",))
    assert [p.name for p in found[0].pets] == ["두부"]
    assert (found[0].matched_pet_ids, found[0].exact) == ((), False)   # 무지개다리 아이의 이름은 일치로 치지 않는다


async def test_익명화한_고객과_다른_매장의_ID_는_후보가_아니다():
    _, customers, _, search, directory = _directory_with_search()
    gone = customers.seed()
    other = customers.seed(shop_id=2, phone="01099990000")
    await customers.anonymize(ctx(), gone.id)
    search.matches = [gone.id, other.id]
    assert await directory.find_draft_candidates(ctx(), ("김민지",)) == []


async def test_몸무게는_반려동물_저장소로_넘긴다():
    journal, customers, pets, _, directory = _directory()
    customer = customers.seed()
    pet = pets.seed(customer.id)
    await directory.set_pet_weight(ctx(), pet.id, Decimal("4.1"))
    assert (pets.rows[pet.id].weight_kg, journal[-1]) == (Decimal("4.1"), ("set_weight", pet.id, Decimal("4.1")))


# --- 보호자 연락처(contact) — notification 만 부른다 ---


async def test_연락처는_살아_있는_고객의_이름_번호_동의를_그대로_주고_잠그지_않는다():
    journal, customers, _, _, directory = _directory()
    customer = customers.seed(name="박서준", phone="01098765432", consent=True)
    assert await directory.contact(ctx(), customer.id) == CustomerContact(
        customer_id=customer.id, name="박서준", phone="01098765432", marketing_consent=True,
    )
    assert journal == []


async def test_익명화한_고객의_연락처는_None_이다():
    """N8 — 보내는 순간 연락처가 None 이면 notification 이 취소한다."""
    _, customers, _, _, directory = _directory()
    customer = customers.seed()
    await customers.anonymize(ctx(), customer.id)
    assert await directory.contact(ctx(), customer.id) is None


async def test_다른_매장_고객의_연락처는_None_이다():
    _, customers, _, _, directory = _directory()
    customer = customers.seed(shop_id=2)
    assert await directory.contact(ctx(shop_id=1), customer.id) is None
