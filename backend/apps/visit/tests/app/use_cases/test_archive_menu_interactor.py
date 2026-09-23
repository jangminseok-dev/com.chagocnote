import pytest

from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.use_cases.archive_menu_interactor import ArchiveMenuInteractor
from visit.domain.errors import MenuNotFoundError
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus


async def test_보관한다():
    menus = FakeMenus()
    bath = menus.seed("목욕")
    view = await ArchiveMenuInteractor(menus).archive_menu(ArchiveMenuCommand(ctx=ctx(), menu_id=bath.id))
    assert view.archived
    assert menus.journal == [("archive_menu", bath.id)]


async def test_다른_매장의_메뉴는_MENU_NOT_FOUND_다():
    menus = FakeMenus()
    theirs = menus.seed("목욕", shop_id=2)
    with pytest.raises(MenuNotFoundError):
        await ArchiveMenuInteractor(menus).archive_menu(ArchiveMenuCommand(ctx=ctx(shop_id=1), menu_id=theirs.id))
