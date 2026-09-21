from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


async def _shop_with_owner(session):
    shop = await ShopPgRepository(session).create("Hiss Haus", "pet_grooming")
    owner = await MemberPgRepository(session).add(shop.id, user_id=1, role=RoleCode.OWNER)
    ctx = ShopContext(shop_id=shop.id, member_id=owner.id, role="owner", permissions=frozenset())
    return shop, ctx


async def test_직원용_초대를_만들고_해시로_다시_찾는다(db_session):
    shop, ctx = await _shop_with_owner(db_session)
    repo = InvitePgRepository(db_session)
    created = await repo.create(ctx, RoleCode.STAFF, "hash-a", EXPIRES, max_uses=1)
    found = await repo.find_by_code_hash_for_update("hash-a")
    assert found.id == created.id
    assert (found.shop_id, found.role, found.max_uses, found.used_count) == (shop.id, RoleCode.STAFF, 1, 0)
    assert found.expires_at == EXPIRES and found.revoked_at is None
    made_by = (
        await db_session.execute(text("SELECT created_by_member_id FROM shop_invites WHERE id = :id"), {"id": created.id})
    ).scalar_one()
    assert made_by == ctx.member_id


async def test_사장용_첫_초대는_만든_멤버가_없고_한_번만_쓸_수_있다(db_session):
    shop = await ShopPgRepository(db_session).create("Hiss Haus", "pet_grooming")
    repo = InvitePgRepository(db_session)
    invite = await repo.create_owner_invite(shop.id, "hash-owner", EXPIRES + timedelta(days=1))
    assert (invite.role, invite.max_uses) == (RoleCode.OWNER, 1)
    made_by = (
        await db_session.execute(text("SELECT created_by_member_id FROM shop_invites WHERE id = :id"), {"id": invite.id})
    ).scalar_one()
    assert made_by is None


async def test_모르는_해시는_None_이다(db_session):
    assert await InvitePgRepository(db_session).find_by_code_hash_for_update("nope") is None


async def test_사용하면_횟수가_오른다(db_session):
    _, ctx = await _shop_with_owner(db_session)
    repo = InvitePgRepository(db_session)
    invite = await repo.create(ctx, RoleCode.STAFF, "hash-b", EXPIRES, max_uses=1)
    await repo.mark_used(invite.id)
    assert (await repo.find_by_code_hash_for_update("hash-b")).used_count == 1


async def _revoked_at(session, code_hash):
    return (
        await session.execute(
            text("SELECT revoked_at FROM shop_invites WHERE code_hash = :h"), {"h": code_hash}
        )
    ).scalar_one()


async def test_멤버가_만든_미사용_초대만_무효화한다(db_session):
    shop, ctx = await _shop_with_owner(db_session)
    other = await MemberPgRepository(db_session).add(shop.id, user_id=2, role=RoleCode.OWNER)
    other_ctx = ShopContext(shop_id=shop.id, member_id=other.id, role="owner", permissions=frozenset())
    repo = InvitePgRepository(db_session)
    await repo.create(ctx, RoleCode.STAFF, "hash-unused", EXPIRES, max_uses=1)
    used = await repo.create(ctx, RoleCode.STAFF, "hash-used", EXPIRES, max_uses=1)
    await repo.mark_used(used.id)
    await repo.create(other_ctx, RoleCode.STAFF, "hash-other-member", EXPIRES, max_uses=1)

    await repo.revoke_created_by(ctx, ctx.member_id)

    assert await _revoked_at(db_session, "hash-unused") is not None
    assert await _revoked_at(db_session, "hash-used") is None
    assert await _revoked_at(db_session, "hash-other-member") is None


async def test_다른_매장의_초대는_무효화하지_않는다(db_session):
    _, a_ctx = await _shop_with_owner(db_session)
    b_shop = await ShopPgRepository(db_session).create("B 매장", "pet_grooming")
    b_owner = await MemberPgRepository(db_session).add(b_shop.id, user_id=3, role=RoleCode.OWNER)
    b_ctx = ShopContext(shop_id=b_shop.id, member_id=b_owner.id, role="owner", permissions=frozenset())
    repo = InvitePgRepository(db_session)
    await repo.create(b_ctx, RoleCode.STAFF, "hash-b-shop", EXPIRES, max_uses=1)

    # A 매장의 컨텍스트로는 B 매장 멤버의 초대에 손댈 수 없다.
    await repo.revoke_created_by(a_ctx, b_owner.id)

    assert await _revoked_at(db_session, "hash-b-shop") is None
