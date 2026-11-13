"""내 연결 목록, 보호자·매장의 끊기, 보호자 가드가 쓰는 접근 확인(스텁)."""
from dataclasses import replace

import pytest

from guardian.app.dtos.end_customer_guardian_link_dto import EndCustomerGuardianLinkCommand
from guardian.app.dtos.end_guardian_link_dto import EndGuardianLinkCommand
from guardian.app.dtos.get_customer_guardian_link_dto import GetCustomerGuardianLinkQuery
from guardian.app.dtos.list_guardian_links_dto import ListGuardianLinksQuery
from guardian.app.use_cases.end_customer_guardian_link_interactor import EndCustomerGuardianLinkInteractor
from guardian.app.use_cases.end_guardian_link_interactor import EndGuardianLinkInteractor
from guardian.app.use_cases.get_customer_guardian_link_interactor import GetCustomerGuardianLinkInteractor
from guardian.app.use_cases.list_guardian_links_interactor import ListGuardianLinksInteractor
from guardian.app.use_cases.resolve_guardian_access_interactor import ResolveGuardianAccessInteractor
from guardian.domain.errors import GuardianLinkNotFoundError
from guardian.tests.helpers.builders import kst
from guardian.tests.helpers.fakes import FakeLinks, FakeShops
from hub.app.dtos.guardian import GuardianContext
from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.errors import GuardianAccessDeniedError

NOW, LATER = kst(11, 13, 10), kst(11, 14, 9)
SHOP = ShopProfile(shop_id=3, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"customer:write"}),
                  timezone="Asia/Seoul")


async def _links():
    links = FakeLinks()
    await links.create(5, 3, 7, "report_link", NOW)          # 1 — 내 것(매장 3)
    await links.create(5, 4, 9, "report_link", LATER)        # 2 — 내 것(매장 4)
    await links.create(6, 3, 8, "report_link", NOW)          # 3 — 남의 것
    return links


async def test_내_연결_목록은_이은_순이고_매장_이름과_매장_시간대의_이은_날을_준다():
    links = await _links()
    shops = FakeShops({3: SHOP, 4: replace(SHOP, shop_id=4, name="두부네", timezone="America/New_York")})
    items = await ListGuardianLinksInteractor(links, shops).list_links(ListGuardianLinksQuery(user_id=5))
    assert [(i.link_id, i.shop_name, i.linked_at.isoformat()) for i in items] == [
        (1, "Hiss Haus", "2026-11-13T10:00:00+09:00"), (2, "두부네", "2026-11-13T19:00:00-05:00")]


async def test_정지했거나_없는_매장의_연결은_목록에서_빠진다():
    links = await _links()
    shops = FakeShops({3: replace(SHOP, open=False)})        # 매장 4 는 없다
    assert await ListGuardianLinksInteractor(links, shops).list_links(ListGuardianLinksQuery(user_id=5)) == []


async def test_보호자가_자기_연결을_끊는다():
    links = await _links()
    interactor = EndGuardianLinkInteractor(links, now=lambda: LATER)
    await interactor.end_link(EndGuardianLinkCommand(user_id=5, link_id=1))
    assert (links.rows[1].ended_at, links.rows[1].ended_by) == (LATER, "guardian")


@pytest.mark.parametrize("link_id", [3, 99], ids=["남의 연결", "없는 연결"])
async def test_남의_연결과_없는_연결은_끊지_못하고_그대로다(link_id):
    links = await _links()
    with pytest.raises(GuardianLinkNotFoundError):
        await EndGuardianLinkInteractor(links, now=lambda: LATER).end_link(
            EndGuardianLinkCommand(user_id=5, link_id=link_id))
    assert links.rows[3].is_live


async def test_이미_끝난_연결은_다시_끊지_못한다():
    links = await _links()
    interactor = EndGuardianLinkInteractor(links, now=lambda: LATER)
    await interactor.end_link(EndGuardianLinkCommand(user_id=5, link_id=1))
    with pytest.raises(GuardianLinkNotFoundError):
        await interactor.end_link(EndGuardianLinkCommand(user_id=5, link_id=1))


async def test_접근_확인은_내_살아_있는_연결이면_컨텍스트를_준다():
    links = await _links()
    assert await ResolveGuardianAccessInteractor(links).resolve(5, 1) == GuardianContext(
        link_id=1, user_id=5, shop_id=3, customer_id=7)


@pytest.mark.parametrize("user_id, link_id", [(5, 3), (5, 99)], ids=["남의 연결", "없는 연결"])
async def test_접근_확인은_남의_연결과_없는_연결을_구분하지_않고_거절한다(user_id, link_id):
    with pytest.raises(GuardianAccessDeniedError):
        await ResolveGuardianAccessInteractor(await _links()).resolve(user_id, link_id)


async def test_접근_확인은_끝난_연결을_거절한다():
    links = await _links()
    await links.end(1, "shop", LATER)
    with pytest.raises(GuardianAccessDeniedError):
        await ResolveGuardianAccessInteractor(links).resolve(5, 1)


async def test_매장은_고객의_연결_여부와_이은_날만_본다():
    links = await _links()
    interactor = GetCustomerGuardianLinkInteractor(links)
    linked = await interactor.get_link(GetCustomerGuardianLinkQuery(ctx=CTX, customer_id=7))
    assert (linked.linked, linked.linked_at.isoformat()) == (True, "2026-11-13T10:00:00+09:00")
    assert not hasattr(linked, "user_id")
    none = await interactor.get_link(GetCustomerGuardianLinkQuery(ctx=CTX, customer_id=9))   # 9 는 매장 4 의 고객이다
    assert (none.linked, none.linked_at) == (False, None)


async def test_매장이_고객의_연결을_끊는다():
    links = await _links()
    await EndCustomerGuardianLinkInteractor(links, now=lambda: LATER).end_link(
        EndCustomerGuardianLinkCommand(ctx=CTX, customer_id=7))
    assert (links.rows[1].ended_by, links.rows[2].is_live, links.rows[3].is_live) == ("shop", True, True)


async def test_연결이_없는_고객과_다른_매장의_고객은_끊을_것이_없다():
    links = await _links()
    interactor = EndCustomerGuardianLinkInteractor(links, now=lambda: LATER)
    for customer_id in (99, 9):
        with pytest.raises(GuardianLinkNotFoundError):
            await interactor.end_link(EndCustomerGuardianLinkCommand(ctx=CTX, customer_id=customer_id))
    assert links.rows[2].is_live       # 매장 4 의 연결은 그대로다
