from datetime import date, time
from decimal import Decimal

from hub.app.dtos.draft_candidate import DraftCandidate
from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from visit.adapter.outbound.rule_draft_parser_adapter import RuleDraftParserAdapter
from visit.app.dtos.parse_visit_draft_dto import ParseVisitDraftCommand
from visit.app.use_cases.parse_visit_draft_interactor import ParseVisitDraftInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, Journal

NOW = kst(9, 24, 15)   # 2026-09-24(목) 15:00 KST


def _candidate(customer_id, name, pets=(), matched=(), exact=True):
    return DraftCandidate(
        customer=CustomerBrief(customer_id=customer_id, name=name, phone_masked="010-12··-5678"),
        pets=tuple(PetBrief(pet_id=pet_id, customer_id=customer_id, name=pet_name, species="dog", breed="말티즈",
                            weight_kg=Decimal("3.2"), passed_away=False) for pet_id, pet_name in pets),
        matched_pet_ids=tuple(matched), exact=exact,
    )


def _setup(settings=None):
    journal = Journal()
    schedule = FakeSchedule(journal) if settings is None else FakeSchedule(journal, settings=settings)
    menus, directory = FakeMenus(journal), FakeDirectory(journal)
    interactor = ParseVisitDraftInteractor(schedule, menus, directory, RuleDraftParserAdapter(), now=lambda: NOW)
    return journal, menus, directory, interactor


async def _parse(interactor, text):
    return await interactor.parse_visit_draft(ParseVisitDraftCommand(ctx=ctx(), text=text))


async def test_후보가_하나면_그_아이를_고른_초안이다():
    journal, menus, directory, interactor = _setup()
    bath = menus.seed("목욕", 60)
    menus.seed("전체 미용", 150, archived=True)
    directory.candidates = [_candidate(7, "이수진", pets=((11, "두부"), (12, "콩이")), matched=(12,))]

    draft = await _parse(interactor, "안녕하세요 콩이 내일 오후 2시에 목욕 가능할까요?")

    assert (draft.date, draft.time) == (date(2026, 9, 25), time(14, 0))
    assert [c.customer_id for c in draft.customer_candidates] == [7]
    assert [(p.pet_id, p.name) for p in draft.customer_candidates[0].pets] == [(11, "두부"), (12, "콩이")]
    assert (draft.customer_candidates[0].matched_pet_ids, draft.pet_ids) == ([12], [12])
    assert draft.menu_ids == [bath.id]
    assert (draft.guessed.date, draft.guessed.time, draft.guessed.who, draft.guessed.menu) == (False, False, False, False)
    assert ("find_draft_candidates", ("콩이", "콩", "가능할까요", "가능할까")) in journal


async def test_후보가_여럿이면_아이를_고르지_않고_누구는_짐작함이다():
    _, _, directory, interactor = _setup()
    directory.candidates = [_candidate(7, "이수진", pets=((11, "콩이"),), matched=(11,)),
                            _candidate(8, "김민지", pets=((21, "콩이"),), matched=(21,))]
    draft = await _parse(interactor, "콩이 2시")
    assert ([c.customer_id for c in draft.customer_candidates], draft.pet_ids) == ([7, 8], [])
    assert (draft.guessed.who, draft.guessed.time, draft.time) == (True, True, time(14, 0))


async def test_후보가_하나라도_부분_일치면_누구는_짐작함이다():
    _, _, directory, interactor = _setup()
    directory.candidates = [_candidate(7, "이수진", pets=((11, "콩순이"),), exact=False)]
    draft = await _parse(interactor, "콩순 내일")
    assert (draft.pet_ids, draft.guessed.who) == ([], True)


async def test_낱말이_없으면_후보를_묻지_않는다():
    journal, _, _, interactor = _setup()
    draft = await _parse(interactor, "내일 오후 2시")
    assert (draft.customer_candidates, draft.guessed.who) == ([], True)
    assert not any(entry[0] == "find_draft_candidates" for entry in journal)


async def test_메뉴는_보관하지_않은_것만_메뉴표_순서로():
    _, menus, _, interactor = _setup()
    menus.seed("전체 미용", 150, archived=True)
    hygiene, bath = menus.seed("위생", 60), menus.seed("목욕", 60)
    draft = await _parse(interactor, "목욕이랑 위생, 전체미용도")
    assert (draft.menu_ids, draft.guessed.menu) == ([hygiene.id, bath.id], False)


async def test_표지_없는_시각은_매장의_영업시간으로_짐작한다():
    _, _, _, interactor = _setup(ScheduleSettings(opens_at=time(6, 0), closes_at=time(15, 0),
                                                  default_duration_minutes=60, closed_weekdays=frozenset()))
    draft = await _parse(interactor, "6시")
    assert (draft.time, draft.guessed.time) == (time(6, 0), True)


async def test_설정이_없으면_준비하고_그_영업시간을_쓴다__아무것도_저장하지_않는다():
    journal, _, _, interactor = _setup()
    draft = await _parse(interactor, "2시")
    assert (draft.time, draft.date) == (time(14, 0), None)
    assert journal == [("ensure", 1)]   # 쓰기 호출이 없다


async def test_오늘은_매장_시간대로_센다():
    _, _, _, interactor = _setup()
    interactor._now = lambda: kst(9, 25, 0, 30)   # 한국 9/25 00:30 = UTC 9/24 15:30
    draft = await _parse(interactor, "오늘")
    assert draft.date == date(2026, 9, 25)
