"""F-I2 — 방금 소속이 끊긴 멤버의 이름으로 살아 있는 초대가 만들어지지 않는다. 실제 두 세션으로 확인한다.

초대 INSERT 는 `shop_id` 외래 키의 암묵적 `FOR KEY SHARE` 때문에 내보내기가 쥔 매장 행 잠금에서
어차피 한 번 멈춘다. 그래서 "멈추는가"만으로는 판별이 안 된다 — 멈춘 바로 그 호출을 취소하지 않고
들고 있다가, 풀려난 뒤에 무엇을 하는지를 본다. 잠금·재확인이 없으면 내보내기의 `revoke_created_by`가
끝난 **뒤에** 초대를 만들어, 무효화되지 않은 초대가 남는다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.dtos.create_invite_dto import CreateInviteCommand
from tenancy.app.use_cases.create_invite_interactor import CreateInviteInteractor
from tenancy.domain.errors import NotAMemberError
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration


def _create(session, ctx):
    interactor = CreateInviteInteractor(
        members=MemberPgRepository(session), invites=InvitePgRepository(session)
    )
    return interactor.create(CreateInviteCommand(ctx=ctx))


async def test_소속이_끊긴_뒤에_풀려난_초대_생성은_거절되고_살아_있는_초대를_남기지_않는다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        shop = await ShopPgRepository(setup).create("Hiss Haus", "pet_grooming")
        member = await MemberPgRepository(setup).add(shop.id, 7, RoleCode.OWNER)
        await setup.commit()

    ctx = ShopContext(
        shop_id=shop.id, member_id=member.id, role="owner",
        permissions=frozenset({"member:manage"}),
    )

    async with factory() as removing, factory() as creating:
        members = MemberPgRepository(removing)
        await members.lock_membership_changes(shop.id)   # 내보내기가 맨 앞에서 하는 일
        await members.remove(ctx, member.id)
        await InvitePgRepository(removing).revoke_created_by(ctx, member.id)

        create_task = asyncio.create_task(_create(creating, ctx))
        await asyncio.sleep(0.2)   # 초대 생성이 매장 행에서 멈출 시간을 준다
        assert not create_task.done()

        await removing.commit()
        try:
            with pytest.raises(NotAMemberError):
                await asyncio.wait_for(create_task, timeout=1)
        finally:
            # 만들어진 것이 있으면 그대로 남긴다 — 아래 검사가 실제로 판별하게 한다.
            await creating.commit()

    async with factory() as check:
        live = (
            await check.execute(
                text(
                    "SELECT count(*) FROM shop_invites "
                    "WHERE shop_id = :s AND revoked_at IS NULL AND used_count < max_uses"
                ),
                {"s": shop.id},
            )
        ).scalar_one()
        assert live == 0
