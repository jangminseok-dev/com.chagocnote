from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.dtos.shop_context import public_context


def test_공개_조회의_컨텍스트는_권한이_비어_있고_매장의_시간대를_쓴다():
    shop = ShopProfile(shop_id=3, name="Hiss Haus", phone=None, address=None, timezone="Asia/Tokyo", open=True)
    assert public_context(shop) == ShopContext(
        shop_id=3, member_id=0, role="public", permissions=frozenset(), timezone="Asia/Tokyo")
