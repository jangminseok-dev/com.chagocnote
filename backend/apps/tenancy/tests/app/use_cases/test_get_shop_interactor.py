from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.use_cases.get_shop_interactor import GetShopInteractor
from tenancy.domain.entities.shop import Shop

CTX = ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset())


class _StubShops:
    def __init__(self):
        self.contexts = []

    async def get(self, ctx):
        self.contexts.append(ctx)
        return Shop(id=3, name="Hiss Haus", business_type="pet_grooming", phone="02-000-0000",
                    address="서울", timezone="Asia/Seoul", suspended_at=None, closed_at=None)


async def test_컨텍스트의_매장_정보를_돌려준다():
    shops = _StubShops()
    view = await GetShopInteractor(shops).get_shop(GetShopQuery(ctx=CTX))
    assert shops.contexts == [CTX]
    assert (view.shop_id, view.name, view.business_type) == (3, "Hiss Haus", "pet_grooming")
    assert (view.phone, view.address, view.timezone) == ("02-000-0000", "서울", "Asia/Seoul")
