import pytest

from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.use_cases.create_menu_interactor import CreateMenuInteractor
from visit.domain.errors import MenuNameTakenError, VisitInputError
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, Journal


async def test_설정을_준비한_뒤_만든다():
    journal = Journal()
    view = await CreateMenuInteractor(FakeSchedule(journal), FakeMenus(journal)).create_menu(
        CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=None, price=None))
    assert (view.name, view.default_duration_minutes, view.archived) == ("발톱", None, False)
    assert journal == [("ensure", 1), ("create_menu", "발톱")]


async def test_소요_규칙에_어긋나면_쓰지_않는다():
    journal = Journal()
    with pytest.raises(VisitInputError):
        await CreateMenuInteractor(FakeSchedule(journal), FakeMenus(journal)).create_menu(
            CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=15, price=None))
    assert journal == []


async def test_보관하지_않은_메뉴와_이름이_겹치면_MENU_NAME_TAKEN_이다():
    menus = FakeMenus()
    menus.seed("목욕")
    with pytest.raises(MenuNameTakenError):
        await CreateMenuInteractor(FakeSchedule(), menus).create_menu(
            CreateMenuCommand(ctx=ctx(), name="목욕", default_duration_minutes=60, price=None))


async def test_정가를_함께_넣는다():
    view = await CreateMenuInteractor(FakeSchedule(), FakeMenus()).create_menu(
        CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=None, price=10_000))
    assert view.price == 10_000
