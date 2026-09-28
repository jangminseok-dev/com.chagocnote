"""실제 리포지토리로 도는 매장 공개 정보 — 로그인한 사용자 없이 매장 ID 만으로 읽는다."""
import pytest
from sqlalchemy import text

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.use_cases.get_shop_profile_interactor import GetShopProfileInteractor

pytestmark = pytest.mark.integration


def _ctx(shop_id):
    return ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset())


async def test_매장의_공개_정보를_읽는다(db_session):
    shops = ShopPgRepository(db_session)
    bare = await shops.create("Hiss Haus", "pet_grooming")
    full = await shops.create("다른 매장", "pet_grooming")
    await shops.update(_ctx(full.id), "다른 매장", "02-000-0000", "서울")
    port = GetShopProfileInteractor(shops)
    assert await port.public_profile(bare.id) == ShopProfile(
        shop_id=bare.id, name="Hiss Haus", phone=None, address=None, timezone="Asia/Seoul", open=True)
    assert await port.public_profile(full.id) == ShopProfile(
        shop_id=full.id, name="다른 매장", phone="02-000-0000", address="서울", timezone="Asia/Seoul", open=True)


async def test_없는_매장이면_None_이다(db_session):
    shop = await ShopPgRepository(db_session).create("Hiss Haus", "pet_grooming")
    assert await GetShopProfileInteractor(ShopPgRepository(db_session)).public_profile(shop.id + 1) is None


@pytest.mark.parametrize("column", ["suspended_at", "closed_at"])
async def test_정지했거나_폐업한_매장은_영업_중이_아니다(db_session, column):
    shops = ShopPgRepository(db_session)
    stopped = await shops.create("멈춘 매장", "pet_grooming")
    running = await shops.create("하는 매장", "pet_grooming")
    await db_session.execute(text(f"UPDATE shops SET {column} = now() WHERE id = :id"), {"id": stopped.id})
    db_session.expire_all()
    port = GetShopProfileInteractor(shops)
    assert [(await port.public_profile(s.id)).open for s in (stopped, running)] == [False, True]
