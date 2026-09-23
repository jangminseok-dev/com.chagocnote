import pytest

from visit.app.dtos.update_menu_dto import UpdateMenuCommand
from visit.app.use_cases.update_menu_interactor import UpdateMenuInteractor
from visit.domain.errors import MenuNotFoundError, VisitInputError
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus


async def test_이름_소요_순서를_바꾼다():
    menus = FakeMenus()
    bath = menus.seed("목욕")
    view = await UpdateMenuInteractor(menus).update_menu(
        UpdateMenuCommand(ctx=ctx(), menu_id=bath.id, name="목욕(대형견)", default_duration_minutes=90,
                          sort_order=9))
    assert (view.name, view.default_duration_minutes, view.sort_order) == ("목욕(대형견)", 90, 9)


async def test_소요_규칙에_어긋나면_쓰지_않는다():
    menus = FakeMenus()
    bath = menus.seed("목욕")
    with pytest.raises(VisitInputError):
        await UpdateMenuInteractor(menus).update_menu(
            UpdateMenuCommand(ctx=ctx(), menu_id=bath.id, name="목욕", default_duration_minutes=700,
                              sort_order=1))
    assert menus.journal == []


async def test_다른_매장의_메뉴는_MENU_NOT_FOUND_다():
    menus = FakeMenus()
    theirs = menus.seed("목욕", shop_id=2)
    with pytest.raises(MenuNotFoundError):
        await UpdateMenuInteractor(menus).update_menu(
            UpdateMenuCommand(ctx=ctx(shop_id=1), menu_id=theirs.id, name="침입", default_duration_minutes=None,
                              sort_order=1))
