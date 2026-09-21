import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.domain.services.invite_code import hash_invite_code

pytestmark = pytest.mark.integration

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _OpenLimiter:
    async def hit(self, user_id):
        return 1


class _ActiveUser:
    async def lock_active(self, user_id):
        return True


def _accept(session, user_id):
    interactor = AcceptInviteInteractor(
        invites=InvitePgRepository(session), members=MemberPgRepository(session),
        shops=ShopPgRepository(session), limiter=_OpenLimiter(), users=_ActiveUser(),
        now=lambda: EXPIRES - timedelta(days=1),
    )
    return interactor.accept(AcceptInviteCommand(user_id=user_id, code="ABCD2345"))


async def test_멤버십_변경이_매장을_잠근_동안_초대_수락은_기다린다(db_engine):
    """E1 — 수락이 초대 행보다 매장 행을 먼저 잠그는지 실제 DB 로 확인한다.

    세션 1 이 매장 행을 쥔 동안 세션 2 의 수락을 태스크로 띄워 둔다. 잠깐 양보한 뒤 세션 3 이 초대
    행을 NOWAIT 로 잠가 본다 — 수락이 아직 초대 행에 닿지 않았다면 성공해야 한다(옛 순서였다면 수락이
    이미 초대 행을 쥐고 있어 NOWAIT 가 즉시 실패한다). 그다음 매장 행 잠금을 풀어 수락이 끝까지
    진행되는 것까지 확인한다. 매장 행 잠금은 검사 결과와 무관하게 항상 풀어, 세션 2 가 영영 멈춰
    있지 않게 한다.
    """
    code_hash = hash_invite_code("ABCD2345")
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        shop = await ShopPgRepository(setup).create("Hiss Haus", "pet_grooming")
        await InvitePgRepository(setup).create_owner_invite(shop.id, code_hash, EXPIRES)
        await setup.commit()

    async with factory() as one, factory() as two, factory() as three:
        await MemberPgRepository(one).lock_membership_changes(shop.id)
        accept_task = asyncio.create_task(_accept(two, user_id=7))
        try:
            await asyncio.sleep(0.2)  # 세션 2 가 매장 행 잠금에서 멈출 시간을 준다
            assert not accept_task.done()

            lock_task = asyncio.create_task(
                three.execute(
                    text("SELECT id FROM shop_invites WHERE code_hash = :h FOR UPDATE NOWAIT"),
                    {"h": code_hash},
                )
            )
            await asyncio.sleep(0.2)
            assert lock_task.done()
            lock_task.result()  # 옛 순서였다면 여기서 LockNotAvailableError 가 다시 올라온다
            await three.rollback()
        finally:
            await one.commit()  # 검사 결과와 무관하게 매장 행 잠금을 풀어 세션 2 를 진행시킨다

        result = await asyncio.wait_for(accept_task, timeout=1)
        assert result.role == "owner"
        await two.rollback()
