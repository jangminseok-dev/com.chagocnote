from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from core.shop_guard import get_shop_access_port
from guardian.adapter.inbound.api.v1.end_customer_guardian_link_router import end_customer_guardian_link_router
from guardian.adapter.inbound.api.v1.end_guardian_link_router import end_guardian_link_router
from guardian.adapter.inbound.api.v1.get_customer_guardian_link_router import get_customer_guardian_link_router
from guardian.adapter.inbound.api.v1.list_guardian_links_router import list_guardian_links_router
from guardian.app.dtos.get_customer_guardian_link_dto import CustomerGuardianLinkView
from guardian.app.dtos.list_guardian_links_dto import GuardianLinkView
from guardian.dependencies.end_customer_guardian_link_provider import get_end_customer_guardian_link_use_case
from guardian.dependencies.end_guardian_link_provider import get_end_guardian_link_use_case
from guardian.dependencies.get_customer_guardian_link_provider import get_get_customer_guardian_link_use_case
from guardian.dependencies.list_guardian_links_provider import get_list_guardian_links_use_case
from guardian.domain.errors import GuardianLinkNotFoundError
from guardian.tests.helpers.api import USER_ID, Recorder, build_app, client
from hub.app.dtos.shop_context import ShopContext

AT = datetime(2026, 11, 13, 10, tzinfo=ZoneInfo("Asia/Seoul"))


class _Access:
    def __init__(self, permissions=("customer:write",)):
        self.permissions = frozenset(permissions)

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role="staff", permissions=self.permissions,
                           timezone="Asia/Seoul")


def _shop_app(router, slot, stub, access=None):
    return build_app(router, slot, stub, overrides={get_shop_access_port: lambda: access or _Access()})


async def test_내_연결_목록():
    stub = Recorder([GuardianLinkView(link_id=1, shop_name="Hiss Haus", linked_at=AT)])
    async with client(build_app(list_guardian_links_router, get_list_guardian_links_use_case, stub)) as c:
        response = await c.get("/v1/me/guardian/links")
    assert response.json() == {
        "items": [{"link_id": 1, "shop_name": "Hiss Haus", "linked_at": "2026-11-13T10:00:00+09:00"}]}
    assert stub.calls[0].user_id == USER_ID


async def test_보호자가_끊으면_204_이고_본문이_없다():
    stub = Recorder()
    async with client(build_app(end_guardian_link_router, get_end_guardian_link_use_case, stub)) as c:
        response = await c.delete("/v1/me/guardian/links/9")
    assert (response.status_code, response.content) == (204, b"")
    assert (stub.calls[0].user_id, stub.calls[0].link_id) == (USER_ID, 9)


async def test_없는_연결을_끊으면_404_이고_범위_밖_ID_는_422_다():
    stub = Recorder(error=GuardianLinkNotFoundError("연결을 찾을 수 없습니다."))
    async with client(build_app(end_guardian_link_router, get_end_guardian_link_use_case, stub)) as c:
        missing = await c.delete("/v1/me/guardian/links/9")
        huge = await c.delete("/v1/me/guardian/links/99999999999")
    assert (missing.status_code, missing.json()["code"]) == (404, "GUARDIAN_LINK_NOT_FOUND")
    assert huge.status_code == 422


@pytest.mark.parametrize("router, slot, method, path", [
    (list_guardian_links_router, get_list_guardian_links_use_case, "get", "/v1/me/guardian/links"),
    (end_guardian_link_router, get_end_guardian_link_use_case, "delete", "/v1/me/guardian/links/9"),
])
async def test_로그인이_없으면_401_이다(router, slot, method, path):
    async with client(build_app(router, slot, Recorder([]), logged_in=False)) as c:
        assert (await getattr(c, method)(path)).status_code == 401


async def test_매장이_보는_응답은_연결_여부와_날짜뿐이다():
    stub = Recorder(CustomerGuardianLinkView(linked=True, linked_at=AT))
    app = _shop_app(get_customer_guardian_link_router, get_get_customer_guardian_link_use_case, stub)
    async with client(app) as c:
        response = await c.get("/v1/shops/3/customers/7/guardian-link")
    assert response.json() == {"linked": True, "linked_at": "2026-11-13T10:00:00+09:00"}
    assert (stub.calls[0].ctx.shop_id, stub.calls[0].customer_id) == (3, 7)


async def test_매장이_끊으면_204_이고_권한이_없으면_403_이다():
    stub = Recorder()
    app = _shop_app(end_customer_guardian_link_router, get_end_customer_guardian_link_use_case, stub)
    async with client(app) as c:
        response = await c.delete("/v1/shops/3/customers/7/guardian-link")
    assert (response.status_code, response.content) == (204, b"")

    denied = _shop_app(end_customer_guardian_link_router, get_end_customer_guardian_link_use_case, Recorder(),
                       access=_Access(permissions=()))
    async with client(denied) as c:
        response = await c.delete("/v1/shops/3/customers/7/guardian-link")
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
