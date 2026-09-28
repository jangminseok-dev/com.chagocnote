from datetime import timedelta

from visit.app.dtos.list_visit_feed_dto import ListVisitFeedQuery
from visit.app.use_cases.list_visit_feed_interactor import ListVisitFeedInteractor
from visit.domain.entities.visit_record import RecordItem
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeVisits,
)

NOW = kst(9, 24, 10)


class _World:
    def __init__(self):
        self.visits, self.directory, self.menus = FakeVisits(), FakeDirectory(), FakeMenus()
        self.directory.family(1, pets=(101, 102))
        self.records, self.library = FakeRecords(self.visits), FakeLibrary()
        self.bath, self.trim = self.menus.seed("목욕"), self.menus.seed("전체 미용")
        self.reports = FakeReportRepository(self.visits)
        self.interactor = ListVisitFeedInteractor(self.visits, self.records, self.menus, self.reports,
                                                  self.directory, self.library, now=lambda: NOW)

    def done(self, day, pet_id=101, menu_ids=(), shop_id=1):
        return self.visits.seed(pet_id=pet_id, starts_at=kst(9, day, 10), status="completed", shop_id=shop_id,
                                started_at=kst(9, day, 10), completed_at=kst(9, day, 12), menu_ids=menu_ids)

    async def feed(self, cursor=None, limit=20, pet_id=None, shop_id=1):
        return await self.interactor.list_visit_feed(
            ListVisitFeedQuery(ctx=ctx(shop_id=shop_id), cursor=cursor, limit=limit, pet_id=pet_id))


async def test_완료_방문을_완료_시각_역순으로_카드로_준다():
    w = _World()
    older = w.done(2, menu_ids=(w.bath.id,))
    newer = w.done(9, pet_id=102)
    w.visits.seed(pet_id=101, starts_at=kst(9, 10, 10))   # 예약됨은 나오지 않는다
    w.library.add(51, attached=True)
    w.records.seed(record(newer.id, media=((51, "photo", "after", 0),), care_note="가" * 100,
                          items=(RecordItem(w.trim.id, 50_000),)))
    view = await w.feed()
    assert [i.visit_id for i in view.items] == [newer.id, older.id]
    first, second = view.items
    assert (first.cover, first.media_count, first.menus, len(first.care_note)) == ("t/51", 1, ["전체 미용"], 80)
    assert (second.cover, second.media_count, second.menus, second.care_note) == (None, 0, ["목욕"], None)
    assert (first.pet.name, first.customer.name, first.completed_at.isoformat()) == (
        "아이102", "김민지", "2026-09-09T12:00:00+09:00")
    assert view.next_cursor is None


async def test_커서로_이어_읽고_그_아이만_거를_수_있다():
    w = _World()
    ids = [w.done(day).id for day in (1, 2, 3)]
    w.done(4, pet_id=102)
    first = await w.feed(limit=2, pet_id=101)
    rest = await w.feed(cursor=first.next_cursor, limit=2, pet_id=101)
    assert ([i.visit_id for i in first.items], [i.visit_id for i in rest.items], rest.next_cursor) == (
        [ids[2], ids[1]], [ids[0]], None)


async def test_다른_매장의_방문은_나오지_않는다():
    w = _World()
    w.done(2, shop_id=2)
    assert (await w.feed()).items == []


async def test_알림장을_보낸_방문을_알리고_링크는_한_번에_읽는다():
    w = _World()
    expired, revoked, never, sent = [w.done(day) for day in (1, 2, 3, 4)]
    sent_at = NOW - timedelta(days=7)
    await w.reports.create(ctx(), sent.id, bytes(16), None, sent_at)
    await w.reports.create(ctx(), expired.id, bytes(16), NOW, sent_at)   # 지금 끝난다
    await w.reports.create(ctx(), revoked.id, bytes(16), None, sent_at)
    await w.reports.revoke(ctx(), revoked.id, NOW)
    view = await w.feed()
    assert [(i.visit_id, i.report_sent) for i in view.items] == [
        (sent.id, True), (never.id, False), (revoked.id, False), (expired.id, False)]
    assert w.reports.reads == ["live_visit_ids"]
