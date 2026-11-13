import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from visit.adapter.outbound.pg.report_settings_pg_repository import ReportSettingsPgRepository
from visit.adapter.outbound.pg.sales_goal_pg_repository import SalesGoalPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_설정_행이_없으면_None_이고_행을_만들지_않는다(db_session):
    assert await SalesGoalPgRepository(db_session).get(A) is None
    count = (await db_session.execute(text("SELECT count(*) FROM visit_shop_settings"))).scalar_one()
    assert count == 0


async def test_일정_설정이_만든_행에는_목표가_없다(db_session):
    await SchedulePgRepository(db_session).ensure(A)
    assert await SalesGoalPgRepository(db_session).get(A) is None


@pytest.mark.parametrize("amount", [1, 5_000_000, 100_000_000])
async def test_정한_목표를_돌려주고_다시_읽어도_같다(db_session, amount):
    repo = SalesGoalPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    assert await repo.put(A, amount) == amount
    assert await repo.get(A) == amount


async def test_None_으로_지운다(db_session):
    repo = SalesGoalPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    await repo.put(A, 5_000_000)
    assert await repo.put(A, None) is None
    assert await repo.get(A) is None


async def test_목표를_바꿔도_일정과_알림장_설정은_그대로다(db_session):
    schedule = SchedulePgRepository(db_session)
    before = await schedule.ensure(A)
    report_before = await ReportSettingsPgRepository(db_session).get(A)
    await SalesGoalPgRepository(db_session).put(A, 5_000_000)
    assert await schedule.ensure(A) == before
    assert await ReportSettingsPgRepository(db_session).get(A) == report_before


async def test_다른_매장의_목표는_보이지_않고_바뀌지_않는다(db_session):
    repo = SalesGoalPgRepository(db_session)
    await SchedulePgRepository(db_session).ensure(A)
    await SchedulePgRepository(db_session).ensure(B)
    await repo.put(A, 5_000_000)
    assert await repo.get(B) is None
    await repo.put(B, 7_000_000)
    assert await repo.get(A) == 5_000_000


@pytest.mark.parametrize("amount", [0, -1, 100_000_001])
async def test_범위_밖_목표는_표가_막는다(db_session, amount):
    await SchedulePgRepository(db_session).ensure(A)
    with pytest.raises(IntegrityError):
        await SalesGoalPgRepository(db_session).put(A, amount)
