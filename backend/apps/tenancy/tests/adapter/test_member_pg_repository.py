import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from hub.app.dtos.membership_summary import MembershipSummary
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.domain.errors import AlreadyMemberError
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration


def _ctx(shop_id):
    return ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset())


async def _shop(session, name="Hiss Haus"):
    return await ShopPgRepository(session).create(name, "pet_grooming")


async def test_사장의_접근_기록에는_모든_권한이_있다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    member = await repo.add(shop.id, user_id=7, role=RoleCode.OWNER)
    record = await repo.find_access(shop.id, user_id=7)
    assert (record.member_id, record.role) == (member.id, "owner")
    assert {"member:manage", "shop:update", "sales:read"} <= record.permissions
    assert (record.shop_suspended, record.shop_closed) == (False, False)


async def test_직원의_접근_기록에는_입력_권한만_있다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=8, role=RoleCode.STAFF)
    record = await repo.find_access(shop.id, user_id=8)
    assert record.permissions == {"reservation:write", "customer:write", "record:write", "sales:write"}


async def test_멤버가_아니면_접근_기록이_없다(db_session):
    shop = await _shop(db_session)
    assert await MemberPgRepository(db_session).find_access(shop.id, user_id=404) is None


async def test_닫히거나_정지된_매장은_접근_기록에_표시된다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=7, role=RoleCode.OWNER)
    await db_session.execute(
        text("UPDATE shops SET closed_at = now(), suspended_at = now() WHERE id = :id"), {"id": shop.id}
    )
    record = await repo.find_access(shop.id, user_id=7)
    assert (record.shop_suspended, record.shop_closed) == (True, True)


async def test_같은_매장에_두_번_합류할_수_없다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    with pytest.raises(AlreadyMemberError):
        await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    # 실패한 뒤에도 세션을 계속 쓸 수 있어야 한다.
    assert len(await repo.list_active(_ctx(shop.id))) == 1


async def test_내보낸_멤버는_접근할_수_없고_다시_합류할_수_있다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    member = await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    await repo.remove(_ctx(shop.id), member.id)
    assert await repo.find_access(shop.id, user_id=7) is None
    assert await repo.list_active(_ctx(shop.id)) == []
    rejoined = await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    assert rejoined.id != member.id


async def test_멤버_목록과_단건_조회는_컨텍스트의_매장만_본다(db_session):
    a, b = await _shop(db_session, "A 매장"), await _shop(db_session, "B 매장")
    repo = MemberPgRepository(db_session)
    a_owner = await repo.add(a.id, user_id=1, role=RoleCode.OWNER)
    a_staff = await repo.add(a.id, user_id=2, role=RoleCode.STAFF)
    b_owner = await repo.add(b.id, user_id=3, role=RoleCode.OWNER)

    assert [m.id for m in await repo.list_active(_ctx(a.id))] == [a_owner.id, a_staff.id]
    assert (await repo.get_active(_ctx(a.id), a_staff.id)).role is RoleCode.STAFF
    # B 매장의 멤버 ID 를 A 매장의 컨텍스트로는 읽을 수 없다.
    assert await repo.get_active(_ctx(a.id), b_owner.id) is None


async def test_역할_변경과_내보내기는_컨텍스트의_매장만_건드린다(db_session):
    a, b = await _shop(db_session, "A 매장"), await _shop(db_session, "B 매장")
    repo = MemberPgRepository(db_session)
    b_staff = await repo.add(b.id, user_id=3, role=RoleCode.STAFF)

    await repo.change_role(_ctx(a.id), b_staff.id, RoleCode.OWNER)
    await repo.remove(_ctx(a.id), b_staff.id)
    assert (await repo.get_active(_ctx(b.id), b_staff.id)).role is RoleCode.STAFF

    await repo.change_role(_ctx(b.id), b_staff.id, RoleCode.OWNER)
    assert (await repo.get_active(_ctx(b.id), b_staff.id)).role is RoleCode.OWNER


async def test_사장_수를_센다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=1, role=RoleCode.OWNER)
    await repo.add(shop.id, user_id=2, role=RoleCode.STAFF)
    removed_owner = await repo.add(shop.id, user_id=3, role=RoleCode.OWNER)
    await repo.remove(_ctx(shop.id), removed_owner.id)
    assert await repo.count_owners(_ctx(shop.id)) == 1


async def test_유저가_속한_매장을_매장_ID_순으로_돌려준다(db_session):
    a, b = await _shop(db_session, "A 매장"), await _shop(db_session, "B 매장")
    repo = MemberPgRepository(db_session)
    await repo.add(b.id, user_id=7, role=RoleCode.STAFF)
    await repo.add(a.id, user_id=7, role=RoleCode.OWNER)
    await repo.add(a.id, user_id=8, role=RoleCode.STAFF)
    assert await repo.list_for_user(7) == [
        MembershipSummary(shop_id=a.id, shop_name="A 매장", role="owner"),
        MembershipSummary(shop_id=b.id, shop_name="B 매장", role="staff"),
    ]
    assert await repo.list_for_user(404) == []


async def _committed_shops(db_engine, *names):
    """두 세션이 함께 볼 수 있도록 매장을 커밋해 둔다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as session:
        shops = [await ShopPgRepository(session).create(name, "pet_grooming") for name in names]
        await session.commit()
    return factory, [shop.id for shop in shops]


async def _lock(session, shop_id):
    await asyncio.wait_for(
        MemberPgRepository(session).lock_membership_changes(_ctx(shop_id)), timeout=0.5
    )


async def test_같은_매장의_멤버십_변경은_매장_행_잠금으로_직렬화된다(db_engine):
    factory, (shop_id,) = await _committed_shops(db_engine, "Hiss Haus")
    async with factory() as one, factory() as two:
        await _lock(one, shop_id)
        # 세션 1 이 쥐고 있는 동안 세션 2 는 기다리다 제한 시간을 넘긴다.
        with pytest.raises(TimeoutError):
            await _lock(two, shop_id)
        await two.rollback()

        await one.commit()
        await _lock(two, shop_id)  # 풀렸으니 이제 얻는다
        await two.rollback()


async def test_다른_매장의_잠금은_서로_막지_않는다(db_engine):
    factory, (a_id, b_id) = await _committed_shops(db_engine, "A 매장", "B 매장")
    async with factory() as one, factory() as two:
        await _lock(one, a_id)
        await _lock(two, b_id)
        await one.rollback()
        await two.rollback()


async def test_내보내진_소속과_닫힌_매장은_목록에서_빠진다(db_session):
    a = await _shop(db_session, "A 매장")
    b = await _shop(db_session, "B 매장")
    c = await _shop(db_session, "C 매장")
    repo = MemberPgRepository(db_session)
    removed = await repo.add(a.id, user_id=7, role=RoleCode.STAFF)
    await repo.remove(_ctx(a.id), removed.id)
    await repo.add(b.id, user_id=7, role=RoleCode.OWNER)
    await db_session.execute(text("UPDATE shops SET closed_at = now() WHERE id = :id"), {"id": b.id})
    await repo.add(c.id, user_id=7, role=RoleCode.STAFF)
    assert [m.shop_id for m in await repo.list_for_user(7)] == [c.id]
