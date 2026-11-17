"""반복의 간격·횟수 기본값(⑭ 설계 3.7, 공통 11절) — 아이의 주기를 1~12 로 자른 값, 모르면 매장의 기본 간격, 횟수 6."""
from dataclasses import replace

from hub.app.dtos.pet_revisit import PetRevisitFact
from visit.app.dtos.get_repeat_defaults_dto import GetRepeatDefaultsQuery, RepeatDefaultsView
from visit.app.use_cases.get_repeat_defaults_interactor import GetRepeatDefaultsInteractor
from visit.domain.value_objects.revisit_settings import DEFAULT_REVISIT_SETTINGS
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeRevisitSettingsRepository, FakeVisits

NOW = kst(11, 17, 10)


def _setup():
    visits, directory, settings = FakeVisits(), FakeDirectory(), FakeRevisitSettingsRepository()
    interactor = GetRepeatDefaultsInteractor(visits, directory=directory, settings=settings, now=lambda: NOW)
    return visits, directory, settings, interactor


def _done(visits, pet_id, *starts):
    for at in starts:
        visits.seed(pet_id=pet_id, status="completed", starts_at=at, started_at=at, completed_at=at)


async def _defaults(interactor, pet_ids):
    return await interactor.get_repeat_defaults(GetRepeatDefaultsQuery(ctx=ctx(), customer_id=1, pet_ids=pet_ids))


async def test_아이의_계산한_주기를_간격으로_쓰고_근거와_아이를_준다():
    visits, _, _, interactor = _setup()
    _done(visits, 101, kst(7, 15, 14), kst(8, 19, 14), kst(9, 23, 14))   # 35·35일 → 5주
    assert await _defaults(interactor, (101,)) == RepeatDefaultsView(
        interval_weeks=5, source="cycle", pet_id=101, cycle_weeks=5, count=6)


async def test_주기를_모르면_매장의_기본_간격을_1에서_12로_자른다():
    _, _, settings, interactor = _setup()
    settings.rows[1] = replace(DEFAULT_REVISIT_SETTINGS, default_cycle_weeks=30)
    assert await _defaults(interactor, (101,)) == RepeatDefaultsView(12, "shop", None, None, 6)


async def test_여러_마리면_짧은_쪽():
    visits, directory, _, interactor = _setup()
    _done(visits, 101, kst(7, 15, 14), kst(8, 19, 14), kst(9, 23, 14))
    directory.revisits[102] = PetRevisitFact(grooming_cycle_weeks=3, revisit_nudged_on=None)
    assert await _defaults(interactor, (101, 102)) == RepeatDefaultsView(3, "cycle", 102, 3, 6)


async def test_아이가_없으면_매장_값():
    _, directory, _, interactor = _setup()
    assert await _defaults(interactor, ()) == RepeatDefaultsView(4, "shop", None, None, 6)
    assert directory.revisit_calls == []   # 아이가 없으면 묻지 않는다
