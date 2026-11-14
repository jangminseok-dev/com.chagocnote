from datetime import date

from hub.app.dtos.search_source import SourceDocument
from hub.app.ports.search_source_port import SearchSourcePort
from visit.app.use_cases.visit_search_source_interactor import VisitSearchSourceInteractor
from visit.tests.helpers.builders import ctx, kst, record
from visit.tests.helpers.fakes import FakeRecords, FakeVisits


def _world():
    visits = FakeVisits()
    records = FakeRecords(visits)
    return visits, records, VisitSearchSourceInteractor(visits=visits, records=records)


async def test_방문의_세_글이_문서가_된다():
    visits, records, source = _world()
    visit = visits.seed(memo="발톱 짧게", starts_at=kst(11, 3, 14))
    records.seed(record(visit.id, care_note="얌전했어요", internal_note="귀를 만지면 싫어함"))
    assert await source.documents(ctx(), "visit", visit.id) == [
        SourceDocument(kind="care_note", source_id=visit.id, customer_id=1, pet_id=101, visit_id=visit.id,
                       happened_on=date(2026, 11, 3), body="얌전했어요"),
        SourceDocument(kind="internal_note", source_id=visit.id, customer_id=1, pet_id=101, visit_id=visit.id,
                       happened_on=date(2026, 11, 3), body="귀를 만지면 싫어함"),
        SourceDocument(kind="visit_memo", source_id=visit.id, customer_id=1, pet_id=101, visit_id=visit.id,
                       happened_on=date(2026, 11, 3), body="발톱 짧게"),
    ]


async def test_기록이_없으면_예약_메모만이고_빈_글은_문서가_아니다():
    visits, records, source = _world()
    memo_only = visits.seed(memo="  가위컷 원함  ", pet_id=None)
    blank = visits.seed(memo="   ")
    records.seed(record(blank.id, care_note="", internal_note="\n \t"))
    [doc] = await source.documents(ctx(), "visit", memo_only.id)
    assert (doc.kind, doc.body, doc.pet_id) == ("visit_memo", "가위컷 원함", None)
    assert await source.documents(ctx(), "visit", blank.id) == []


async def test_취소한_방문의_글도_문서다():
    visits, _, source = _world()
    canceled = visits.seed(memo="다음 주로 미룸", status="canceled", canceled_at=kst(9, 22, 9),
                           cancel_reason="customer_request")
    assert [d.body for d in await source.documents(ctx(), "visit", canceled.id)] == ["다음 주로 미룸"]


async def test_날짜는_매장_시간대의_방문_날이다():
    """한국 시간 11월 4일 0시 30분은 UTC 로 11월 3일이다 — 매장의 날로 적는다."""
    visits, _, source = _world()
    late = visits.seed(memo="늦은 예약", starts_at=kst(11, 3, 23, 30))
    early = visits.seed(memo="이른 예약", starts_at=kst(11, 4, 0, 30))
    assert [(await source.documents(ctx(), "visit", v.id))[0].happened_on for v in (late, early)] == [
        date(2026, 11, 3), date(2026, 11, 4)]


async def test_없는_방문과_다른_매장의_방문과_다른_대상은_빈_목록이다():
    visits, _, source = _world()
    visit = visits.seed(memo="발톱 짧게")
    assert await source.documents(ctx(), "visit", 999) == []
    assert await source.documents(ctx(shop_id=2), "visit", visit.id) == []
    assert await source.documents(ctx(), "pet", visit.id) == []
    assert await source.documents(ctx(), "customer", visit.id) == []


def test_허브_포트의_구현이다():
    assert isinstance(_world()[2], SearchSourcePort)
