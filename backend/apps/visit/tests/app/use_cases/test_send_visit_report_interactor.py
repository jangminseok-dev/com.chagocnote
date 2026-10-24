from dataclasses import replace
from datetime import timedelta

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from hub.app.dtos.visit_events import VisitReportIssued, VisitReportRevoked
from visit.app.dtos.revoke_visit_report_dto import RevokeVisitReportCommand
from visit.app.dtos.send_visit_report_dto import SendVisitReportCommand
from visit.app.use_cases.revoke_visit_report_interactor import RevokeVisitReportInteractor
from visit.app.use_cases.send_visit_report_interactor import SendVisitReportInteractor
from visit.domain.errors import (
    ReportEmptyError,
    VisitInputError,
    VisitNoRecordYetError,
    VisitNotCompletedError,
    VisitNotFoundError,
)
from visit.domain.services.report_rules import hide
from visit.domain.services.report_token import read_token
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeEvents,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeReportSettingsRepository,
    FakeShopProfile,
    FakeVisits,
    Journal,
)

KEY = bytes(range(32))
NOW = kst(9, 24, 10)
SHOP = ShopProfile(shop_id=1, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)


class _World:
    def __init__(self) -> None:
        self.journal = Journal()
        self.now = NOW
        self.visits, self.settings = FakeVisits(self.journal), FakeReportSettingsRepository()
        self.records = FakeRecords(self.visits, self.journal)
        self.reports = FakeReportRepository(self.visits, self.journal)
        self.events = FakeEvents(self.journal)
        directory, library = FakeDirectory(self.journal), FakeLibrary()
        directory.family(1, pets=(101,))
        for media_id in (51, 52):
            library.add(media_id, attached=True)
        self.interactor = SendVisitReportInteractor(
            visits=self.visits, records=self.records, settings=self.settings, reports=self.reports,
            menus=FakeMenus(), directory=directory, library=library, shops=FakeShopProfile({1: SHOP}),
            events=self.events, now=lambda: self.now, link_key=KEY, web_base_url="https://r.example",
        )
        self.revoker = RevokeVisitReportInteractor(self.visits, self.reports, directory, events=self.events,
                                                   now=lambda: self.now)

    def completed(self, status="completed", care_note="눈물 자국", hidden=(), **fields):
        """사진 둘(전 51, 후 52)이 있는 기록이 달린 방문."""
        found = self.visits.seed(status=status, starts_at=kst(9, 23, 14), started_at=kst(9, 23, 14), **fields)
        written = record(found.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                         care_note=care_note)
        self.records.seed(replace(written, media=hide(written, hidden)))
        return found

    async def send(self, visit_id, hidden=(), shop_id=1):
        return await self.interactor.send_visit_report(
            SendVisitReportCommand(ctx=ctx(shop_id=shop_id), visit_id=visit_id, hidden_media_ids=tuple(hidden)))

    async def revoke(self, visit_id):
        await self.revoker.revoke_visit_report(RevokeVisitReportCommand(ctx=ctx(), visit_id=visit_id))

    def hidden(self, visit_id):
        return {m.media_id for m in self.records.rows[visit_id].media if m.hidden}

    def written(self):
        return [e[0] for e in self.journal if e[0] in ("create_report", "set_hidden")]


def _public_id(link):
    return read_token(link.url.removeprefix("https://r.example/r/"), KEY)


@pytest.mark.parametrize("link_days, expires_at", [
    (7, "2026-10-01T10:00:00+09:00"), (30, "2026-10-24T10:00:00+09:00"), (None, None),
])
async def test_처음_보내면_잠근_뒤_링크를_만들고_기간은_매장이_정한_대로다(link_days, expires_at):
    w = _World()
    w.settings.rows[1] = replace(DEFAULT_REPORT_SETTINGS, link_days=link_days)
    visit_id = w.completed().id

    sent = await w.send(visit_id, hidden=(52,))

    [row] = w.reports.rows
    assert (row.visit_id, row.created_by_member_id, row.created_at, len(row.public_id)) == (visit_id, 11, NOW, 16)
    assert (sent.link.status, _public_id(sent.link)) == ("live", row.public_id)
    assert sent.link.created_at.isoformat() == "2026-09-24T10:00:00+09:00"
    assert (sent.link.expires_at.isoformat() if sent.link.expires_at else None) == expires_at
    assert [(m.media_id, m.hidden) for m in sent.report.media] == [(52, True), (51, False)]
    assert (sent.report.cover.url, sent.report.settings.link_days) == ("d/51", link_days)
    assert [e[0] for e in w.journal] == ["lock_family", "lock_visits", "close_expired_reports", "create_report",
                                         "set_hidden", "publish"]


async def test_다시_보내면_같은_링크이고_뺀_사진만_바뀐다():
    w = _World()
    visit_id = w.completed().id
    first = await w.send(visit_id, hidden=(52,))
    w.settings.rows[1] = replace(DEFAULT_REPORT_SETTINGS, link_days=7)   # 기간은 만들 때 정해진다
    w.now = NOW + timedelta(days=1)

    again = await w.send(visit_id, hidden=(51,))

    assert again.link == first.link and len(w.reports.rows) == 1
    assert w.hidden(visit_id) == {51}   # 52 는 되살아났다
    assert [(m.media_id, m.hidden) for m in again.report.media] == [(52, False), (51, True)]
    assert await w.send(visit_id, hidden=(51,)) == again   # 같은 본문이면 결과가 같다


async def test_기간이_지난_뒤_보내면_옛_줄을_닫고_새_링크를_만든다():
    """R20·R4"""
    w = _World()
    w.settings.rows[1] = replace(DEFAULT_REPORT_SETTINGS, link_days=7)
    visit_id = w.completed().id
    first = await w.send(visit_id)
    w.now = NOW + timedelta(days=7)   # 끝나는 바로 그 시각

    second = await w.send(visit_id)

    old, new = w.reports.rows
    assert (old.revoked_at, new.revoked_at, new.created_at) == (w.now, None, w.now)
    assert _public_id(first.link) == old.public_id != new.public_id == _public_id(second.link)
    assert second.link.expires_at.isoformat() == "2026-10-08T10:00:00+09:00"


async def test_끊은_뒤_보내면_새_링크이고_뺀_사진은_끊어도_그대로다():
    """R4"""
    w = _World()
    visit_id = w.completed().id
    first = await w.send(visit_id, hidden=(52,))
    await w.revoke(visit_id)
    assert w.hidden(visit_id) == {52}

    second = await w.send(visit_id, hidden=(52,))

    assert [r.revoked_at for r in w.reports.rows] == [NOW, None]
    assert _public_id(first.link) != _public_id(second.link)


@pytest.mark.parametrize("status", ["reserved", "in_progress", "canceled", "no_show"])
async def test_완료하지_않은_방문은_VISIT_NOT_COMPLETED_다(status):
    w = _World()
    with pytest.raises(VisitNotCompletedError):
        await w.send(w.completed(status=status).id)
    assert w.written() == []


async def test_기록이_없는_방문은_VISIT_NO_RECORD_YET_이다():
    w = _World()
    with pytest.raises(VisitNoRecordYetError):
        await w.send(w.visits.seed(status="completed", started_at=kst(9, 23, 14)).id)
    assert w.written() == []


@pytest.mark.parametrize("care_note", [None, "", "  \n "])
async def test_전부_빼고_메모도_없으면_REPORT_EMPTY_이고_아무것도_바뀌지_않는다(care_note):
    w = _World()
    visit_id = w.completed(care_note=care_note, hidden=(52,)).id
    with pytest.raises(ReportEmptyError):
        await w.send(visit_id, hidden=(51, 52))
    assert (w.reports.rows, w.hidden(visit_id), w.written()) == ([], {52}, [])


async def test_메모가_있으면_사진을_전부_빼고도_처음_보낼_수_있다():
    w = _World()
    sent = await w.send(w.completed(care_note="눈물 자국").id, hidden=(51, 52))
    assert (sent.link.status, sent.report.cover) == ("live", None)


async def test_살아_있는_링크가_있으면_메모가_없어도_전부_뺄_수_있다():
    w = _World()
    visit_id = w.completed(care_note=None).id
    first = await w.send(visit_id)

    emptied = await w.send(visit_id, hidden=(51, 52))

    assert emptied.link == first.link and len(w.reports.rows) == 1
    assert (w.hidden(visit_id), emptied.report.cover) == ({51, 52}, None)


@pytest.mark.parametrize("hidden", [(99,), (52, 99), (52, 52)])
async def test_이_기록의_것이_아닌_미디어와_중복은_VALIDATION_ERROR_다(hidden):
    """R14"""
    w = _World()
    visit_id = w.completed().id
    with pytest.raises(VisitInputError):
        await w.send(visit_id, hidden=hidden)
    assert w.written() == []


async def test_없는_방문과_다른_매장의_방문에는_보낼_수_없다():
    """R2"""
    w = _World()
    theirs = w.completed(shop_id=2)
    for visit_id in (theirs.id, 999):
        with pytest.raises(VisitNotFoundError):
            await w.send(visit_id, shop_id=1)
    assert w.journal == []


async def test_처음_보내면_주소와_기간을_실은_VisitReportIssued_를_발행한다():
    w = _World()
    visit = w.completed()
    sent = await w.send(visit.id)
    [event] = w.events.published
    assert isinstance(event, VisitReportIssued)
    assert (event.ctx, event.visit_id, event.customer_id, event.pet_id, event.starts_at, event.occurred_at,
            event.family_pet_ids) == (ctx(), visit.id, 1, 101, kst(9, 23, 14), NOW, (101,))
    assert (event.url, event.expires_at) == (sent.link.url, w.reports.rows[0].expires_at)


async def test_끊으면_VisitReportRevoked_를_끊은_뒤에_발행한다():
    w = _World()
    visit = w.completed()
    await w.send(visit.id)
    await w.revoke(visit.id)
    issued, revoked = w.events.published
    assert isinstance(revoked, VisitReportRevoked)
    assert (revoked.ctx, revoked.visit_id, revoked.customer_id, revoked.pet_id, revoked.starts_at, revoked.occurred_at,
            revoked.family_pet_ids) == (ctx(), visit.id, 1, 101, kst(9, 23, 14), NOW, (101,))
    names = [e[0] for e in w.journal]
    assert names.index("revoke_report") < len(names) - 1 == names.index("publish", names.index("revoke_report"))


async def test_살아_있는_링크로_다시_보내면_발행하지_않고_끊은_뒤_보내면_다시_발행한다():
    """알림톡은 링크마다 한 번이다."""
    w = _World()
    visit_id = w.completed().id
    first = await w.send(visit_id)
    await w.send(visit_id, hidden=(52,))
    assert [e.url for e in w.events.published] == [first.link.url]
    await w.revoke(visit_id)
    second = await w.send(visit_id)
    assert [(type(e).__name__, getattr(e, "url", None)) for e in w.events.published] == [
        ("VisitReportIssued", first.link.url), ("VisitReportRevoked", None), ("VisitReportIssued", second.link.url)]


async def test_빈_알림장이면_발행하지_않는다():
    w = _World()
    visit_id = w.completed(care_note=None, hidden=(52,)).id
    with pytest.raises(ReportEmptyError):
        await w.send(visit_id, hidden=(51, 52))
    assert w.events.published == []
