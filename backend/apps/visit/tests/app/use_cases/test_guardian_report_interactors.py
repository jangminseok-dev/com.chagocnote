"""보호자용 읽기 — 연결(GuardianContext)의 고객이 받은 알림장만, 공개 알림장과 같은 조립으로(스텁)."""
from dataclasses import replace

import pytest

from hub.app.dtos.guardian import GuardianContext
from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.guardian_report_dto import (
    ListGuardianPetsQuery,
    ListGuardianReportsQuery,
    ReadGuardianReportQuery,
)
from visit.app.use_cases.list_guardian_pets_interactor import ListGuardianPetsInteractor
from visit.app.use_cases.list_guardian_reports_interactor import ListGuardianReportsInteractor
from visit.app.use_cases.read_guardian_report_interactor import ReadGuardianReportInteractor
from visit.domain.errors import ReportNotFoundError, VisitInputError
from visit.domain.services.report_rules import hide
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeShopProfile,
    FakeVisits,
)

SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone="02-123-4567", address=None, timezone="Asia/Seoul",
                   open=True)
GUARDIAN = GuardianContext(link_id=9, user_id=5, shop_id=1, customer_id=1)


class _World:
    """매장 1 의 고객 1(아이 101·102)과 고객 2(아이 201). 알림장은 `sent` 로 하나씩 보낸다."""

    def __init__(self) -> None:
        self.visits, self.settings = FakeVisits(), FakeReportSettingsRepository()
        self.records, self.reports = FakeRecords(self.visits), FakeReportRepository(self.visits)
        self.reports.records = self.records
        self.menus, self.directory, self.library = FakeMenus(), FakeDirectory(), FakeLibrary()
        self.shops = FakeShopProfile({1: SHOP})
        self.directory.family(1, pets=(101, 102))
        self.directory.family(2, pets=(201,))
        self._next_public = 0

    async def sent(self, day, *, customer_id=1, pet_id=101, media=(), hidden=(), care_note="눈물 자국",
                   expires_at=None):
        """day 일(10월) 14시의 완료 방문에 보낸 알림장. media 는 (미디어 ID, 단계) 들."""
        found = self.visits.seed(status="completed", starts_at=kst(10, day, 14), started_at=kst(10, day, 14),
                                 customer_id=customer_id, pet_id=pet_id)
        for media_id, _ in media:
            self.library.add(media_id, attached=True)
        written = record(found.id, media=tuple((m, "photo", phase, i) for i, (m, phase) in enumerate(media)),
                         care_note=care_note, internal_note="내부 메모")
        self.records.seed(replace(written, media=hide(written, tuple(hidden))))
        self._next_public += 1
        public_id = self._next_public.to_bytes(16, "big")
        return await self.reports.create(ctx(), found.id, public_id, expires_at, kst(10, day, 15))

    def pets(self):
        return ListGuardianPetsInteractor(self.reports, self.directory, self.shops)

    def lister(self):
        return ListGuardianReportsInteractor(self.reports, self.records, self.directory, self.library, self.shops)

    def reader(self):
        return ReadGuardianReportInteractor(
            self.reports, self.records, self.settings, self.menus, self.directory, self.library, self.shops)

    async def listed(self, **query):
        return await self.lister().list_reports(ListGuardianReportsQuery(guardian=GUARDIAN, **{
            "pet_id": None, "cursor": None, **query}))


async def test_지난_알림장은_최신순이고_날짜_아이_대표_사진_수를_준다():
    world = _World()
    first = await world.sent(1, media=((51, "before"), (52, "after")))
    second = await world.sent(8, pet_id=102, media=((61, "after"),))
    page = await world.listed()
    assert [(i.report_id, i.visit_date.isoformat(), i.pet_id, i.pet_name, i.media_count) for i in page.items] == [
        (second.id, "2026-10-08", 102, "아이102", 1), (first.id, "2026-10-01", 101, "아이101", 2)]
    assert (page.items[1].cover.url, page.items[0].cover.url) == ("t/52", "t/61")   # 대표는 후 사진의 썸네일
    assert page.next_cursor is None


async def test_뺀_사진은_수와_대표에서_빠지고_사진이_없으면_대표가_없다():
    world = _World()
    await world.sent(1, media=((51, "after"), (52, "after")), hidden=(51,))
    await world.sent(2, media=())
    page = await world.listed()
    assert [(i.media_count, i.cover.url if i.cover else None) for i in page.items] == [(0, None), (1, "t/52")]


async def test_스물한_장이면_스무_장과_다음_쪽_표시를_주고_다음_쪽에_한_장이_있다():
    world = _World()
    for day in range(1, 22):
        await world.sent(day)
    page = await world.listed()
    assert len(page.items) == 20 and page.next_cursor is not None
    rest = await world.listed(cursor=page.next_cursor)
    assert [i.visit_date.isoformat() for i in rest.items] == ["2026-10-01"]
    assert rest.next_cursor is None


async def test_깨진_쪽_표시는_422_다():
    world = _World()
    with pytest.raises(VisitInputError):
        await world.listed(cursor="이상한-글자")


async def test_아이로_거르면_그_아이의_알림장만이고_보호자만의_방문은_빠진다():
    world = _World()
    await world.sent(1, pet_id=101)
    await world.sent(2, pet_id=102)
    alone = await world.sent(3, pet_id=None)
    assert [i.pet_id for i in (await world.listed(pet_id=102)).items] == [102]
    everything = (await world.listed()).items
    assert [(i.report_id, i.pet_id, i.pet_name) for i in everything][0] == (alone.id, None, None)
    pets = await world.pets().list_pets(ListGuardianPetsQuery(guardian=GUARDIAN))
    assert [(p.pet_id, p.name) for p in pets] == [(101, "아이101"), (102, "아이102")]


async def test_아이_목록은_알림장을_받은_적_있는_아이만이고_남의_고객의_아이는_없다():
    world = _World()
    await world.sent(1, pet_id=102)
    await world.sent(2, customer_id=2, pet_id=201)
    pets = await world.pets().list_pets(ListGuardianPetsQuery(guardian=GUARDIAN))
    assert [p.pet_id for p in pets] == [102]


async def test_끊은_알림장은_없고_기간이_지난_알림장은_있다():
    world = _World()
    gone = await world.sent(1)
    world.reports.rows = [replace(r, revoked_at=kst(10, 2)) for r in world.reports.rows]
    old = await world.sent(2, expires_at=kst(10, 3))      # 한참 전에 기간이 끝났다
    assert [i.report_id for i in (await world.listed()).items] == [old.id]
    with pytest.raises(ReportNotFoundError):
        await world.reader().read_report(ReadGuardianReportQuery(guardian=GUARDIAN, report_id=gone.id))


async def test_한_장은_공개_알림장과_같은_조립이고_기간이_없다():
    world = _World()
    sent = await world.sent(1, media=((51, "before"), (52, "after")), hidden=(52,), expires_at=kst(10, 3))
    view = await world.reader().read_report(ReadGuardianReportQuery(guardian=GUARDIAN, report_id=sent.id))
    assert (view.report.pet_name, view.report.care_note) == ("아이101", "눈물 자국")
    assert [(m.media_id, m.hidden) for m in view.report.media] == [(51, False)]
    assert view.expires_at is None
    assert not hasattr(view.report, "internal_note")


async def test_다른_고객의_알림장과_없는_알림장은_404_다():
    world = _World()
    theirs = await world.sent(1, customer_id=2, pet_id=201)
    for report_id in (theirs.id, 999):
        with pytest.raises(ReportNotFoundError):
            await world.reader().read_report(ReadGuardianReportQuery(guardian=GUARDIAN, report_id=report_id))


@pytest.mark.parametrize("shop", [None, replace(SHOP, open=False)], ids=["없는 매장", "정지·폐업"])
async def test_매장이_닫혔으면_목록과_아이는_비고_한_장은_404_다(shop):
    world = _World()
    sent = await world.sent(1)
    if shop is None:
        world.shops.shops.clear()
    else:
        world.shops.shops[1] = shop
    assert (await world.listed()).items == ()
    assert await world.pets().list_pets(ListGuardianPetsQuery(guardian=GUARDIAN)) == []
    with pytest.raises(ReportNotFoundError):
        await world.reader().read_report(ReadGuardianReportQuery(guardian=GUARDIAN, report_id=sent.id))
