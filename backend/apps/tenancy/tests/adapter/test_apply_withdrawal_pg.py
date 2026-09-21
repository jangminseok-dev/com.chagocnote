"""실제 리포지토리로 도는 탈퇴의 소속 정리 — 막히면 요청의 트랜잭션이 통째로 되돌아가는 것까지 본다."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tenancy.domain.errors import OwnershipTransferRequiredError
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration


def _interactor(session):
    return ApplyWithdrawalInteractor(
        MemberPgRepository(session), ShopPgRepository(session), InvitePgRepository(session)
    )


async def _active_user_ids(session, shop_id):
    rows = await session.execute(
        text("SELECT user_id FROM shop_members WHERE shop_id = :id AND removed_at IS NULL ORDER BY user_id"),
        {"id": shop_id},
    )
    return list(rows.scalars())


async def test_막힌_탈퇴는_앞서_처리한_매장도_되돌린다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        shops, members = ShopPgRepository(setup), MemberPgRepository(setup)
        first = await shops.create("직원으로 있는 매장", "pet_grooming")
        second = await shops.create("혼자 사장인 매장", "pet_grooming")
        await members.add(first.id, user_id=1, role=RoleCode.OWNER)
        await members.add(first.id, user_id=7, role=RoleCode.STAFF)
        await members.add(second.id, user_id=7, role=RoleCode.OWNER)
        await members.add(second.id, user_id=2, role=RoleCode.STAFF)
        await setup.commit()

    async with factory() as session:
        with pytest.raises(OwnershipTransferRequiredError):
            await _interactor(session).apply_withdrawal(7, close_sole_owned=True)
        # 막히기 전에 첫 매장은 이미 처리됐다. 그래서 아래의 롤백이 의미가 있다.
        assert await _active_user_ids(session, first.id) == [1]
        await session.rollback()   # 요청의 get_db 가 예외에서 하는 일

    async with factory() as check:
        assert await _active_user_ids(check, first.id) == [1, 7]
        assert await _active_user_ids(check, second.id) == [2, 7]


async def test_혼자뿐인_매장을_닫고_만들어_둔_초대까지_무효화한다(db_session):
    shops, members, invites = (
        ShopPgRepository(db_session), MemberPgRepository(db_session), InvitePgRepository(db_session)
    )
    shop = await shops.create("Hiss Haus", "pet_grooming")
    owner = await members.add(shop.id, user_id=7, role=RoleCode.OWNER)
    ctx = ShopContext(shop_id=shop.id, member_id=owner.id, role="owner", permissions=frozenset())
    await invites.create(ctx, RoleCode.STAFF, "hash-left-behind",
                         datetime.now(timezone.utc) + timedelta(days=7), max_uses=1)

    await _interactor(db_session).apply_withdrawal(7, close_sole_owned=True)

    assert (await shops.get_by_id(shop.id)).is_closed is True
    assert await _active_user_ids(db_session, shop.id) == []
    assert (await invites.find_by_code_hash_for_update("hash-left-behind")).revoked_at is not None
