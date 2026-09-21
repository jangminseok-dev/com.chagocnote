import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository

pytestmark = pytest.mark.integration


def _ctx(shop_id):
    return ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset())


async def test_매장을_만들면_기본값이_채워진다(db_session):
    shop = await ShopPgRepository(db_session).create("Hiss Haus", "pet_grooming")
    assert shop.id > 0
    assert (shop.name, shop.business_type, shop.timezone) == ("Hiss Haus", "pet_grooming", "Asia/Seoul")
    assert shop.phone is None and shop.is_closed is False


async def test_만든_매장을_ID_와_컨텍스트로_다시_읽는다(db_session):
    repo = ShopPgRepository(db_session)
    created = await repo.create("Hiss Haus", "pet_grooming")
    assert (await repo.get_by_id(created.id)).name == "Hiss Haus"
    assert (await repo.get(_ctx(created.id))).id == created.id


async def test_매장_정보를_고친다(db_session):
    repo = ShopPgRepository(db_session)
    shop = await repo.create("Hiss Haus", "pet_grooming")
    updated = await repo.update(_ctx(shop.id), "히스 하우스", "02-000-0000", "서울")
    assert (updated.name, updated.phone, updated.address) == ("히스 하우스", "02-000-0000", "서울")
    assert (await repo.get_by_id(shop.id)).name == "히스 하우스"


async def test_수정은_컨텍스트의_매장만_건드린다(db_session):
    repo = ShopPgRepository(db_session)
    a = await repo.create("A 매장", "pet_grooming")
    b = await repo.create("B 매장", "pet_grooming")
    await repo.update(_ctx(a.id), "A 새 이름", None, None)
    assert (await repo.get_by_id(b.id)).name == "B 매장"
