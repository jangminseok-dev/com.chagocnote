import pytest

from visit.app.dtos.get_sales_goal_dto import GetSalesGoalQuery, SalesGoalView
from visit.app.dtos.update_sales_goal_dto import UpdateSalesGoalCommand
from visit.app.use_cases.get_sales_goal_interactor import GetSalesGoalInteractor
from visit.app.use_cases.update_sales_goal_interactor import UpdateSalesGoalInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSalesGoalRepository, FakeSchedule, Journal


async def test_목표를_읽는다_없으면_None_이고_설정_행을_만들지_않는다():
    journal = Journal()
    goals = FakeSalesGoalRepository(journal)
    interactor = GetSalesGoalInteractor(goals=goals)
    assert await interactor.get_sales_goal(GetSalesGoalQuery(ctx=ctx())) == SalesGoalView(monthly_amount=None)
    goals.rows[1] = 5_000_000
    assert await interactor.get_sales_goal(GetSalesGoalQuery(ctx=ctx())) == SalesGoalView(monthly_amount=5_000_000)
    assert journal == []


async def test_정하기는_설정_행을_준비한_뒤_쓴다():
    journal = Journal()
    goals = FakeSalesGoalRepository(journal)
    interactor = UpdateSalesGoalInteractor(schedule=FakeSchedule(journal), goals=goals)
    view = await interactor.update_sales_goal(UpdateSalesGoalCommand(ctx=ctx(), monthly_amount=5_000_000))
    assert view == SalesGoalView(monthly_amount=5_000_000)
    assert goals.rows[1] == 5_000_000
    assert journal == [("ensure", 1), ("put_sales_goal", 1)]


@pytest.mark.parametrize("amount", [0, None])
async def test_0_과_None_은_목표_없음으로_저장한다(amount):
    goals = FakeSalesGoalRepository()
    goals.rows[1] = 5_000_000
    interactor = UpdateSalesGoalInteractor(schedule=FakeSchedule(), goals=goals)
    view = await interactor.update_sales_goal(UpdateSalesGoalCommand(ctx=ctx(), monthly_amount=amount))
    assert view == SalesGoalView(monthly_amount=None)
    assert goals.rows[1] is None


async def test_다른_매장의_목표는_건드리지_않는다():
    goals = FakeSalesGoalRepository()
    goals.rows[2] = 7_000_000
    interactor = UpdateSalesGoalInteractor(schedule=FakeSchedule(), goals=goals)
    await interactor.update_sales_goal(UpdateSalesGoalCommand(ctx=ctx(shop_id=1), monthly_amount=5_000_000))
    assert goals.rows == {2: 7_000_000, 1: 5_000_000}
