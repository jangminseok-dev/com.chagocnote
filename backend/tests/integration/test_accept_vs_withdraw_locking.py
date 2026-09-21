"""F4 — 회원 탈퇴와 겹친 초대 수락이 소속을 되살리지 못한다. 실제 두 세션으로 확인한다."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.use_cases.guard_active_user_interactor import GuardActiveUserInteractor
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.domain.errors import AccountUnavailableError
from tenancy.domain.services.invite_code import hash_invite_code

pytestmark = pytest.mark.integration

EXPIRES = datetime.now(timezone.utc) + timedelta(days=7)


class _OpenLimiter:
    async def hit(self, user_id):
        return 1


def _accept(session, user_id):
    interactor = AcceptInviteInteractor(
        invites=InvitePgRepository(session), members=MemberPgRepository(session),
        shops=ShopPgRepository(session), limiter=_OpenLimiter(),
        users=GuardActiveUserInteractor(UserPgRepository(session)),
    )
    return interactor.accept(AcceptInviteCommand(user_id=user_id, code="ABCD2345"))


async def test_탈퇴가_유저_행을_쥔_동안_수락은_기다리고_탈퇴한_뒤에는_거절된다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await UserPgRepository(setup).create_with_identity(
            SocialProfile(Provider.DEV, "leaving", None, "떠나는 사람", None, None)
        )
        shop = await ShopPgRepository(setup).create("Hiss Haus", "pet_grooming")
        await InvitePgRepository(setup).create_owner_invite(shop.id, hash_invite_code("ABCD2345"), EXPIRES)
        await setup.commit()

    async with factory() as withdrawing, factory() as accepting:
        users = UserPgRepository(withdrawing)
        assert (await users.lock(user.id)).id == user.id   # 탈퇴가 맨 앞에서 하는 일
        await users.anonymize(user.id)

        # 같은 유저의 수락은 유저 행에서 기다린다 — 매장 행이나 초대 행까지 가지 못한다.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_accept(accepting, user.id), timeout=0.5)
        await accepting.rollback()

        await withdrawing.commit()
        with pytest.raises(AccountUnavailableError):
            await asyncio.wait_for(_accept(accepting, user.id), timeout=0.5)
        await accepting.rollback()

    async with factory() as check:
        members = (await check.execute(text("SELECT count(*) FROM shop_members"))).scalar_one()
        used = (await check.execute(text("SELECT used_count FROM shop_invites"))).scalar_one()
        # 보조 단언이다. 수락 세션은 어느 쪽이든 롤백하므로 이 값은 잠금이 없어도 같다. 판별은 위의 두 raises 가 한다.
        assert (members, used) == (0, 0)
