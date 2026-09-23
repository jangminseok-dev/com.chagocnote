from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.use_cases.list_menus_interactor import ListMenusInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, Journal


async def test_설정을_준비한_뒤_보관하지_않은_메뉴를_순서대로():
    journal = Journal()
    menus = FakeMenus(journal)
    menus.seed("목욕")
    menus.seed("위생", archived=True)
    menus.seed("전체 미용", minutes=None)
    menus.seed("남의 메뉴", shop_id=2)
    views = await ListMenusInteractor(FakeSchedule(journal), menus).list_menus(
        ListMenusQuery(ctx=ctx(), include_archived=False))
    assert [(v.name, v.default_duration_minutes, v.archived) for v in views] == [
        ("목욕", 60, False), ("전체 미용", None, False)]
    assert journal == [("ensure", 1)]


async def test_보관한_메뉴도_달라면_준다():
    menus = FakeMenus()
    menus.seed("목욕")
    menus.seed("위생", archived=True)
    views = await ListMenusInteractor(FakeSchedule(), menus).list_menus(
        ListMenusQuery(ctx=ctx(), include_archived=True))
    assert [(v.name, v.archived) for v in views] == [("목욕", False), ("위생", True)]
