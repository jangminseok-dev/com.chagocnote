import pytest

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.errors import MenuNameTakenError, MenuNotFoundError
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _prepared(session, *shops):
    for shop in shops:
        await SchedulePgRepository(session).ensure(shop)
    return MenuPgRepository(session)


async def test_새_메뉴는_맨_뒤_순서다(db_session):
    menus = await _prepared(db_session, A)
    nail = await menus.create(A, "발톱", None, None)
    assert (nail.sort_order, nail.default_duration_minutes, nail.archived) == (6, None, False)
    assert [m.name for m in await menus.list(A, include_archived=False)][-1] == "발톱"


async def test_순서값이_상한에_닿아도_새_메뉴_추가는_된다(db_session):
    menus = await _prepared(db_session, A)
    [bath, *_] = await menus.list(A, include_archived=False)
    await menus.update(A, bath.id, bath.name, bath.default_duration_minutes, 32_767, None)
    nail = await menus.create(A, "발톱", None, None)
    assert nail.sort_order <= 32_767


async def test_보관하지_않은_메뉴끼리_이름이_겹치면_MENU_NAME_TAKEN_이고_세션은_계속_쓴다(db_session):
    menus = await _prepared(db_session, A)
    with pytest.raises(MenuNameTakenError):
        await menus.create(A, "목욕", 60, None)
    [bath] = [m for m in await menus.list(A, include_archived=False) if m.name == "목욕"]
    await menus.archive(A, bath.id)
    again = await menus.create(A, "목욕", 70, None)   # 보관한 이름은 다시 쓸 수 있다
    with pytest.raises(MenuNameTakenError):
        await menus.update(A, again.id, "위생", 60, 1, None)


async def test_보관은_처음_시각을_지키고_목록에서_빠진다(db_session):
    menus = await _prepared(db_session, A)
    [bath, *_] = await menus.list(A, include_archived=False)
    first = await menus.archive(A, bath.id)
    second = await menus.archive(A, bath.id)
    assert first.archived_at == second.archived_at
    assert bath.id not in [m.id for m in await menus.list(A, include_archived=False)]
    assert bath.id in [m.id for m in await menus.list(A, include_archived=True)]


async def test_다른_매장의_메뉴는_고치거나_보관하지_못한다(db_session):
    """V1 — 다른 매장 컨텍스트로는 404 이고 값도 그대로다."""
    menus = await _prepared(db_session, A, B)
    [theirs, *_] = await menus.list(B, include_archived=False)
    with pytest.raises(MenuNotFoundError):
        await menus.update(A, theirs.id, "침입", 10, 1, None)
    with pytest.raises(MenuNotFoundError):
        await menus.archive(A, theirs.id)
    [still, *_] = await menus.list(B, include_archived=False)
    assert (still.name, still.archived) == (theirs.name, False)


async def test_정가를_넣고_바꾸고_비운다(db_session):
    await SchedulePgRepository(db_session).ensure(A)
    menus = MenuPgRepository(db_session)
    nail = await menus.create(A, "발톱", None, 10_000)
    assert nail.price == 10_000
    assert (await menus.update(A, nail.id, "발톱", None, nail.sort_order, 12_000)).price == 12_000
    assert (await menus.update(A, nail.id, "발톱", None, nail.sort_order, None)).price is None
