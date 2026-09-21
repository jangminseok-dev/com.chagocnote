from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand
from tenancy.app.use_cases.update_shop_interactor import UpdateShopInteractor
from tenancy.domain.entities.shop import Shop

CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"shop:update"}))


class _StubShops:
    def __init__(self):
        self.updates = []

    async def update(self, ctx, name, phone, address):
        self.updates.append((ctx, name, phone, address))
        return Shop(id=3, name=name, business_type="pet_grooming", phone=phone, address=address,
                    timezone="Asia/Seoul", suspended_at=None, closed_at=None)


async def test_이름_전화_주소를_고치고_고친_정보를_돌려준다():
    shops = _StubShops()
    view = await UpdateShopInteractor(shops).update_shop(
        UpdateShopCommand(ctx=CTX, name="히스 하우스", phone=None, address="서울 성동구")
    )
    assert shops.updates == [(CTX, "히스 하우스", None, "서울 성동구")]
    assert (view.name, view.phone, view.address) == ("히스 하우스", None, "서울 성동구")
