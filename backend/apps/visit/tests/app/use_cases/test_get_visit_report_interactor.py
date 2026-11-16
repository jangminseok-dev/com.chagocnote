from dataclasses import replace
from decimal import Decimal

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from visit.app.dtos.get_visit_report_dto import GetVisitReportQuery
from visit.app.dtos.report_view_dto import ReportShopView
from visit.app.use_cases.get_visit_report_interactor import GetVisitReportInteractor
from visit.domain.errors import VisitNoRecordYetError, VisitNotFoundError
from visit.domain.services.report_rules import hide
from core.link_token import read_token
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
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

KEY = bytes(range(32))
NOW = kst(9, 24, 10)
SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)


class _World:
    def __init__(self) -> None:
        self.visits, self.settings = FakeVisits(), FakeReportSettingsRepository()
        self.records, self.reports = FakeRecords(self.visits), FakeReportRepository(self.visits)
        directory, library = FakeDirectory(), FakeLibrary()
        directory.family(1, pets=(101,))
        for media_id in (51, 52):
            library.add(media_id, attached=True)
        self.interactor = GetVisitReportInteractor(
            visits=self.visits, records=self.records, settings=self.settings, reports=self.reports,
            menus=FakeMenus(), directory=directory, library=library, shops=FakeShopProfile({1: SHOP}),
            now=lambda: NOW, link_key=KEY, web_base_url="https://r.example",
        )

    def completed(self, status="completed", **fields):
        """사진 둘(전 51, 후 52)과 몸무게가 있는 기록이 달린 방문. 52 는 알림장에서 뺐다."""
        found = self.visits.seed(status=status, starts_at=kst(9, 23, 14), started_at=kst(9, 23, 14), **fields)
        written = record(found.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                         weight_kg=Decimal("3.4"), care_note="눈물 자국")
        self.records.seed(replace(written, media=hide(written, (52,))))
        return found

    async def preview(self, visit_id, shop_id=1):
        return await self.interactor.get_visit_report(GetVisitReportQuery(ctx=ctx(shop_id=shop_id), visit_id=visit_id))


async def test_미리보기는_뺀_사진을_표시와_함께_주고_보낸_적이_없으면_링크가_없다():
    world = _World()
    found = await world.preview(world.completed().id)
    assert (found.report.pet_name, found.report.care_note) == ("아이101", "눈물 자국")
    assert [(m.media_id, m.hidden) for m in found.report.media] == [(52, True), (51, False)]
    assert found.report.cover.url == "d/51"
    assert (found.link.status, found.link.url) == ("none", None)


async def test_매장이_정한_설정대로_담는다():
    world = _World()
    assert (await world.preview(world.completed().id)).report.settings == DEFAULT_REPORT_SETTINGS
    chosen = ReportSettings(link_days=7, show_menus=False, show_shop_info=True, show_weight=True, show_amount=False)
    world.settings.rows[1] = chosen
    report = (await world.preview(1)).report
    assert (report.settings, report.menus, report.weight_kg) == (chosen, None, Decimal("3.4"))
    assert report.shop == ReportShopView(name="Hiss Haus", phone=None, address=None)


async def test_살아_있는_링크의_주소와_시각을_매장_시간대로_준다():
    world = _World()
    visit_id = world.completed().id
    await world.reports.create(ctx(), visit_id, bytes(range(16)), kst(10, 23, 15), kst(9, 23, 15))
    link = (await world.preview(visit_id)).link
    assert read_token(link.url.removeprefix("https://r.example/r/"), KEY) == bytes(range(16))
    assert (link.status, link.expires_at.isoformat(), link.first_viewed_at, link.created_at.isoformat()) == (
        "live", "2026-10-23T15:00:00+09:00", None, "2026-09-23T15:00:00+09:00")


async def test_기간이_지난_링크는_없는_것이다():
    world = _World()
    visit_id = world.completed().id
    await world.reports.create(ctx(), visit_id, bytes(range(16)), NOW, kst(9, 23, 15))   # 지금 끝난다
    assert (await world.preview(visit_id)).link.status == "none"


async def test_미용_중인_방문도_미리_본다():
    world = _World()
    found = await world.preview(world.completed(status="in_progress").id)
    assert found.report.care_note == "눈물 자국"


async def test_없는_방문과_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    """R2"""
    world = _World()
    theirs = world.completed(shop_id=2)
    for visit_id in (theirs.id, 999):
        with pytest.raises(VisitNotFoundError):
            await world.preview(visit_id, shop_id=1)


async def test_기록이_없는_방문은_VISIT_NO_RECORD_YET_이다():
    world = _World()
    with pytest.raises(VisitNoRecordYetError):
        await world.preview(world.visits.seed(status="completed", started_at=kst(9, 23, 14)).id)
