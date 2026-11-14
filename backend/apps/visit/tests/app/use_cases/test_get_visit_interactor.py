from datetime import timedelta

import pytest

from visit.app.dtos.get_visit_dto import GetVisitQuery
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.domain.errors import VisitNotFoundError
from visit.tests.helpers.builders import ctx, kst, record
from visit.domain.services.report_token import read_token
from visit.tests.helpers.fakes import (
    FakeChecks,
    FakeDirectory,
    FakeLibrary,
    FakeMenus,
    FakeRecords,
    FakeReportRepository,
    FakeVisits,
)

NOW = kst(9, 24, 10)
KEY = bytes(range(32))
NO_LINK = ("none", None, None, None, None)


def _interactor(visits, directory, records, library, reports=None):
    return GetVisitInteractor(
        visits, visits, visits, FakeMenus(), directory, records, library, reports or FakeReportRepository(visits),
        now=lambda: NOW, link_key=KEY, web_base_url="https://r.example", checks=FakeChecks())


def _setup():
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    return visits, _interactor(visits, directory, FakeRecords(visits), FakeLibrary())


def _with_records():
    visits, directory, library = FakeVisits(), FakeDirectory(), FakeLibrary()
    directory.family(1, pets=(101,))
    records = FakeRecords(visits)
    for media_id in (51, 52, 61):
        library.add(media_id, kind="video" if media_id == 61 else "photo", attached=True)
    return visits, records, _interactor(visits, directory, records, library)


def _with_reports():
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101,))
    reports = FakeReportRepository(visits)
    return visits, reports, _interactor(visits, directory, FakeRecords(visits), FakeLibrary(), reports)


async def test_묶음_지난_방문_노쇼_횟수를_함께_준다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(8, 1, 14), status="completed",
                started_at=kst(8, 1, 14), completed_at=kst(8, 1, 15))
    last = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                       started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 10, 14), status="completed",
                started_at=kst(9, 10, 14), completed_at=kst(9, 10, 15))   # 형제의 방문은 지난 방문이 아니다
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 16, 14), status="no_show")
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert detail.visit.visit_id == kong.id
    assert [v.visit_id for v in detail.group] == [bori.id]
    assert (detail.previous_visit.visit_id, detail.previous_visit.starts_at.isoformat()) == (
        last.id, "2026-09-02T14:00:00+09:00")
    assert detail.no_show_count == 1


async def test_지난_방문이_없으면_비어_있다():
    visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert (detail.group, detail.previous_visit, detail.no_show_count) == ([], None, 0)


async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    visits, interactor = _setup()
    theirs = visits.seed(shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.get_visit(GetVisitQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))


async def test_기록과_대표_사진_지난_방문의_대표_사진을_함께_준다():
    visits, records, interactor = _with_records()
    last = visits.seed(pet_id=101, starts_at=kst(9, 2, 14), status="completed", started_at=kst(9, 2, 14),
                       completed_at=kst(9, 2, 15))
    today = visits.seed(pet_id=101, starts_at=kst(9, 23, 14), status="in_progress", started_at=kst(9, 23, 14))
    records.seed(record(last.id, media=((61, "video", "after", 0),)))
    records.seed(record(today.id, media=((51, "photo", "before", 0), (52, "photo", "after", 0)),
                        care_note="눈물 자국", version=3))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=today.id))
    assert (detail.record.care_note, detail.record.version, [m.media_id for m in detail.record.media]) == (
        "눈물 자국", 3, [51, 52])
    assert (detail.cover, detail.previous_visit.cover) == ("t/52", "t/61")


async def test_기록이_없으면_record_와_cover_가_비어_있다():
    visits, _, interactor = _with_records()
    kong = visits.seed(pet_id=101, starts_at=kst(9, 23, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert (detail.record, detail.cover) == (None, None)


def _link(detail):
    link = detail.report
    return link.status, link.url, link.expires_at, link.first_viewed_at, link.created_at


async def test_보낸_적이_없으면_report_는_none_이다():
    visits, _, interactor = _with_reports()
    kong = visits.seed(pet_id=101, starts_at=kst(9, 23, 14))
    assert _link(await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))) == NO_LINK


async def test_살아_있는_링크의_주소와_시각을_매장_시간대로_준다():
    visits, reports, interactor = _with_reports()
    done = visits.seed(pet_id=101, starts_at=kst(9, 23, 14), status="completed", started_at=kst(9, 23, 14),
                       completed_at=kst(9, 23, 16))
    other = visits.seed(pet_id=101, starts_at=kst(9, 2, 14), status="completed", started_at=kst(9, 2, 14),
                        completed_at=kst(9, 2, 16))
    await reports.create(ctx(), done.id, bytes(range(16)), kst(10, 23, 18), kst(9, 23, 18))
    await reports.mark_viewed(reports.rows[0].id, kst(9, 23, 19))
    link = (await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=done.id))).report
    assert (link.status, read_token(link.url.removeprefix("https://r.example/r/"), KEY)) == (
        "live", bytes(range(16)))
    assert [t.isoformat() for t in (link.created_at, link.first_viewed_at, link.expires_at)] == [
        "2026-09-23T18:00:00+09:00", "2026-09-23T19:00:00+09:00", "2026-10-23T18:00:00+09:00"]
    assert _link(await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=other.id))) == NO_LINK   # 그 방문의 것만


async def test_끊었거나_기간이_지난_링크는_none_이다():
    visits, reports, interactor = _with_reports()
    done = dict(pet_id=101, status="completed", started_at=kst(9, 2, 14), completed_at=kst(9, 2, 16))
    revoked = visits.seed(starts_at=kst(9, 2, 14), **done)
    expired = visits.seed(starts_at=kst(9, 9, 14), **done)
    await reports.create(ctx(), revoked.id, bytes(16), None, NOW - timedelta(days=8))
    await reports.revoke(ctx(), revoked.id, NOW - timedelta(days=1))
    await reports.create(ctx(), expired.id, bytes(16), NOW, NOW - timedelta(days=7))   # 지금 끝난다
    for visit in (revoked, expired):
        assert _link(await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=visit.id))) == NO_LINK
