import pytest
from sqlalchemy import text

from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.value_objects.report_settings import DEFAULT_REPORT_SETTINGS, ReportSettings
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
WEEK = ReportSettings(link_days=7, show_menus=False, show_shop_info=False, show_weight=True, show_amount=True)
FOREVER = ReportSettings(link_days=None, show_menus=True, show_shop_info=False, show_weight=False, show_amount=True)


async def _row_count(session) -> int:
    return (await session.execute(text("SELECT count(*) FROM visit_shop_settings"))).scalar_one()


async def test_설정_행이_없으면_기본값을_주고_행을_만들지_않는다(db_session):
    assert await ReportSettingsPgRepository(db_session).get(A) == DEFAULT_REPORT_SETTINGS
    assert await _row_count(db_session) == 0


async def test_일정_설정이_만든_행은_알림장_기본값을_갖는다(db_session):
    await SchedulePgRepository(db_session).ensure(A)
    assert await ReportSettingsPgRepository(db_session).get(A) == DEFAULT_REPORT_SETTINGS


@pytest.mark.parametrize("settings", [WEEK, FOREVER])
async def test_바꾼_설정을_돌려주고_다시_읽어도_같다(db_session, settings):
    repo = ReportSettingsPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    assert await repo.update(A, settings) == settings
    assert await repo.get(A) == settings


async def test_다시_바꾸면_나중_것이_남는다(db_session):
    repo = ReportSettingsPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    await repo.update(A, WEEK)
    await repo.update(A, FOREVER)
    assert await repo.get(A) == FOREVER


async def test_알림장_설정을_바꿔도_일정_설정은_그대로다(db_session):
    schedule = SchedulePgRepository(db_session)
    before = await schedule.ensure(A)
    await ReportSettingsPgRepository(db_session).update(A, WEEK)
    assert await schedule.ensure(A) == before


async def test_매장마다_따로다(db_session):
    repo = ReportSettingsPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    await repo.update(A, WEEK)
    assert await repo.get(B) == DEFAULT_REPORT_SETTINGS   # B 는 행이 없다
    await SchedulePgRepository(db_session).ensure(B)
    await repo.update(B, FOREVER)
    assert (await repo.get(A), await repo.get(B)) == (WEEK, FOREVER)
