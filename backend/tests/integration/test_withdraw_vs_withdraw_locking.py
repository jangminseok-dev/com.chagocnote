"""H5 — 같은 유저의 탈퇴가 동시에 두 번 와도 한 번만 처리된다. 실제 두 세션으로 확인한다.

HTTP 요청 두 개를 `asyncio.gather` 로 보내는 `test_account_flow_wiring.py` 쪽 테스트는 배선 확인용이다.
탈퇴의 `lock` 을 `get` 으로 바꿔도 다섯 번에 네 번은 통과할 만큼 판별력이 낮았다 — 잠금은 여기서 본다.

`get` 으로 바꾸면 둘째 탈퇴도 매장·유저 행에서 결국 한 번 멈추지만, 멈추기 **전에** 읽어 둔
신원 목록을 그대로 돌려준다. 그래서 "멈추는가"가 아니라 "풀려난 뒤에 무엇을 돌려주는가"를 본다 —
빈 결과여야 제공자 쪽 연결을 두 번 끊지 않는다.
"""
import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.pg.operator_pg_repository import OperatorPgRepository
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.dtos.withdraw_dto import WithdrawCommand
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.use_cases.withdraw_interactor import WithdrawInteractor
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tests.integration.support import NoGuardians

pytestmark = pytest.mark.integration


class _StubStore(RefreshTokenStorePort):
    """세대는 Redis 의 일이다. 여기서 보는 것은 Postgres 잠금뿐이다."""

    def __init__(self) -> None:
        self.revoked_all = []

    async def current_generation(self, user_id: int) -> int:
        return 0

    async def save(self, token: str, user_id: int, generation: int) -> None:
        pass

    async def take(self, token: str):
        raise NotImplementedError

    async def revoke(self, token: str) -> None:
        pass

    async def revoke_all(self, user_id: int) -> None:
        self.revoked_all.append(user_id)


def _withdraw(session, user_id, store):
    interactor = WithdrawInteractor(
        guardians=NoGuardians(),
        users=UserPgRepository(session),
        operators=OperatorPgRepository(session),
        lifecycle=ApplyWithdrawalInteractor(
            members=MemberPgRepository(session), shops=ShopPgRepository(session),
            invites=InvitePgRepository(session),
        ),
        store=store,
    )
    return interactor.withdraw(WithdrawCommand(user_id=user_id, confirm_close_shops=False))


async def test_첫_탈퇴가_유저_행을_쥔_동안_둘째는_기다리고_빈_결과로_끝난다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await UserPgRepository(setup).create_with_identity(
            SocialProfile(Provider.DEV, "double-leaver", None, "떠나는 사람", None, None)
        )
        await setup.commit()

    async with factory() as first, factory() as second:
        first_store, second_store = _StubStore(), _StubStore()
        first_result = await _withdraw(first, user.id, first_store)
        assert len(first_result.revocations) == 1   # 끊을 신원 하나를 찾았다. 커밋은 아직이다.

        # 둘째 탈퇴를 취소하지 않고 들고 있다가, 풀려난 그 호출이 무엇을 돌려주는지 본다.
        second_task = asyncio.create_task(_withdraw(second, user.id, second_store))
        await asyncio.sleep(0.2)   # 둘째가 유저 행에서 멈출 시간을 준다
        assert not second_task.done()

        await first.commit()
        second_result = await asyncio.wait_for(second_task, timeout=1)
        assert second_result.revocations == ()   # 제공자 쪽 연결을 두 번 끊지 않는다
        assert second_store.revoked_all == []    # 이미 끊긴 세션을 또 끊지 않는다
        await second.rollback()
