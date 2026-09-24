import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.app.use_cases.resolve_shop_access_interactor import ResolveShopAccessInteractor
from hub.app.errors import ShopAccessClosedError, ShopAccessDeniedError, ShopAccessSuspendedError


class _StubMembers:
    def __init__(self, record):
        self.record = record
        self.calls = []

    async def find_access(self, shop_id, user_id):
        self.calls.append((shop_id, user_id))
        return self.record


def _record(**overrides):
    base = dict(member_id=11, role="staff", permissions=frozenset({"record:write"}),
                shop_suspended=False, shop_closed=False, timezone="Asia/Tokyo")
    return ShopAccessRecord(**{**base, **overrides})


async def test_멤버면_컨텍스트를_돌려준다():
    members = _StubMembers(_record())
    ctx = await ResolveShopAccessInteractor(members).resolve(user_id=5, shop_id=3)
    assert ctx == ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset({"record:write"}),
                              timezone="Asia/Tokyo")
    assert members.calls == [(3, 5)]


async def test_멤버가_아니면_NOT_A_MEMBER_다():
    with pytest.raises(ShopAccessDeniedError):
        await ResolveShopAccessInteractor(_StubMembers(None)).resolve(user_id=5, shop_id=3)


async def test_닫힌_매장은_SHOP_CLOSED_다():
    with pytest.raises(ShopAccessClosedError):
        await ResolveShopAccessInteractor(_StubMembers(_record(shop_closed=True))).resolve(5, 3)


async def test_정지된_매장은_SHOP_SUSPENDED_다():
    with pytest.raises(ShopAccessSuspendedError):
        await ResolveShopAccessInteractor(_StubMembers(_record(shop_suspended=True))).resolve(5, 3)
