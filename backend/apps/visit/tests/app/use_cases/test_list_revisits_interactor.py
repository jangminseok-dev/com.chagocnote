from datetime import date, timedelta

from hub.app.dtos.pet_revisit import PetRevisitFact
from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.count_revisits_dto import CountRevisitsQuery
from visit.app.dtos.list_revisits_dto import ListRevisitsQuery
from visit.app.use_cases.count_revisits_interactor import CountRevisitsInteractor
from visit.app.use_cases.list_revisits_interactor import PAGE_SIZE, ListRevisitsInteractor
from visit.domain.value_objects.revisit_settings import RevisitSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeRecords,
    FakeRevisitSettingsRepository,
    FakeShopProfile,
    FakeVisits,
)

NOW = kst(11, 17, 15)
TODAY = date(2026, 11, 17)


class _World:
    def __init__(self, pets=tuple(range(101, 131))):
        self.visits, self.directory, self.library = FakeVisits(), FakeDirectory(), FakeLibrary()
        self.records, self.settings = FakeRecords(self.visits), FakeRevisitSettingsRepository()
        self.directory.family(1, pets=pets)
        shop = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
        self.lister = ListRevisitsInteractor(
            history=self.visits, directory=self.directory, records=self.records, library=self.library,
            settings=self.settings, shops=FakeShopProfile({1: shop}), now=lambda: NOW)
        self.counter = CountRevisitsInteractor(
            history=self.visits, directory=self.directory, settings=self.settings, now=lambda: NOW)

    def came(self, pet_id: int, *days_ago: int, customer_id: int = 1):
        """그 아이가 days_ago 일 전들(매장 시간대 오후 2시)에 완료한 방문."""
        for d in days_ago:
            at = kst(11, 17, 14) - timedelta(days=d)
            self.visits.seed(customer_id=customer_id, pet_id=pet_id, starts_at=at, status="completed",
                             started_at=at, completed_at=at)

    async def list(self, bucket, cursor=None):
        return await self.lister.list_revisits(ListRevisitsQuery(ctx=ctx(), bucket=bucket, cursor=cursor))

    async def counts(self):
        return await self.counter.count_revisits(CountRevisitsQuery(ctx=ctx()))


async def test_곧과_지남으로_나누고_다음_올_때가_이른_순이다():
    w = _World()
    w.came(101, 50, 92, 134)    # 6주 주기 — 다음 올 때 8일 전 → 지남
    w.came(102, 25, 53, 81)     # 4주 주기 — 3일 뒤 → 곧
    w.came(103, 15, 29)         # 2주 간격 하나 — 어림 4주 → 13일 뒤, 어디에도 없다
    w.came(104, 30)             # 한 번 — 어림 4주 → 2일 전 → 지남(어림)
    w.came(105, 10, 52, 94)     # 6주 주기 — 32일 뒤 → 없다

    due, soon = await w.list("due"), await w.list("soon")
    assert [(i.pet.pet_id, i.due_date, i.cycle_source, i.estimated) for i in due.items] == [
        (101, TODAY - timedelta(days=8), "computed", False), (104, TODAY - timedelta(days=2), "none", True)]
    assert [(i.pet.pet_id, i.due_date, i.cycle_weeks) for i in soon.items] == [(102, TODAY + timedelta(days=3), 4)]
    assert soon.items[0].last_visit_date == TODAY - timedelta(days=25)
    counts = await w.counts()
    assert (counts.soon, counts.due) == (1, 2)


async def test_앞날_예약_무지개다리_익명화_한_해_넘김_다른_매장은_빠진다():
    w = _World()
    w.directory.family(2, pets=(201,), passed=(201,))
    w.directory.family(3, pets=(301,), shop_id=2)
    w.directory.pet_names[102] = None                 # 익명화한 고객의 아이
    for pet in (101, 102, 103, 104, 201):
        w.came(pet, 60, customer_id=2 if pet == 201 else 1)
    w.came(105, 400)                                  # 한 해를 넘겼다
    w.came(301, 60, customer_id=3)
    w.visits.seed(customer_id=1, pet_id=103, starts_at=kst(11, 20, 14))                    # 앞날 예약
    w.visits.seed(customer_id=1, pet_id=104, starts_at=kst(11, 10, 14), status="in_progress",
                  started_at=kst(11, 10, 14))                                             # 미용 중(날짜가 지났어도)
    w.visits.seed(customer_id=1, pet_id=101, starts_at=kst(11, 17, 9))                     # 오늘 오전 — 지났어도 앞날
    due = await w.list("due")
    assert [i.pet.pet_id for i in due.items] == []
    assert (await w.counts()).due == 0


async def test_안내_글은_매장_이름_아이_이름_지난_주_수를_채운다():
    w = _World()
    w.came(101, 43)
    [item] = (await w.list("due")).items
    assert item.message == (
        "안녕하세요, Hiss Haus예요.\n아이101가 미용한 지 6주가 됐어요.\n편하신 날 알려 주시면 예약 잡아 드릴게요.")
    w.settings.rows[1] = RevisitSettings(revisit_message="{아이} 미용할 때가 됐어요 ({주}주)")
    assert (await w.list("due")).items[0].message == "아이101 미용할 때가 됐어요 (6주)"


async def test_안내한_날은_마지막_방문보다_뒤일_때만_보인다():
    w = _World()
    w.came(101, 43)
    w.came(102, 43)
    w.directory.revisits[101] = PetRevisitFact(grooming_cycle_weeks=None, revisit_nudged_on=TODAY - timedelta(days=3))
    w.directory.revisits[102] = PetRevisitFact(grooming_cycle_weeks=None, revisit_nudged_on=TODAY - timedelta(days=50))
    items = {i.pet.pet_id: i.nudged_on for i in (await w.list("due")).items}
    assert items == {101: TODAY - timedelta(days=3), 102: None}


async def test_직접_정한_주기와_매장의_곧_날_수를_따른다():
    w = _World()
    w.came(101, 20)
    w.directory.revisits[101] = PetRevisitFact(grooming_cycle_weeks=3, revisit_nudged_on=None)   # 1일 뒤 → 곧
    assert [i.cycle_source for i in (await w.list("soon")).items] == ["manual"]
    w.directory.revisits[101] = PetRevisitFact(grooming_cycle_weeks=4, revisit_nudged_on=None)   # 8일 뒤
    assert (await w.list("soon")).items == []
    w.settings.rows[1] = RevisitSettings(revisit_soon_days=10)
    assert [i.pet.pet_id for i in (await w.list("soon")).items] == [101]


async def test_20개씩_나누고_커서로_잇는다():
    w = _World()
    for pet in range(101, 126):
        w.came(pet, 40 + pet % 7)
    first = await w.list("due")
    assert len(first.items) == PAGE_SIZE and first.next_cursor is not None
    rest = await w.list("due", first.next_cursor)
    assert len(rest.items) == 5 and rest.next_cursor is None
    seen = [i.pet.pet_id for i in first.items + rest.items]
    assert sorted(seen) == list(range(101, 126)) and len(set(seen)) == 25


async def test_질의_수는_아이_수와_상관없다():
    w = _World()
    for pet in range(101, 126):
        w.came(pet, 40, 82, 124)
    await w.list("due")
    await w.counts()
    assert len(w.directory.revisit_calls) == 2   # 목록 한 번 + 수 한 번
    assert w.visits.revisit_calls == 2
