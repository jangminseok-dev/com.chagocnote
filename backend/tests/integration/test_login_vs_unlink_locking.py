"""F-I1 — 소셜 로그인은 해제·탈퇴로 사라진 수단으로 그 유저의 세션을 내주지 않는다.

세 시나리오를 실제 두 세션으로 확인한다.

(a) 해제가 유저 행을 쥔 동안 로그인이 기다리다가, 해제가 커밋된 뒤 그 **같은 호출**이 풀려나
    무엇을 돌려주는지 본다 — 새로 조회해서 얻은 두 번째 로그인이 아니라, 막혀 있던 바로 그 호출이다.
(b) 탈퇴가 유저 행을 쥔 동안에도 같은 모양이 성립한다.
(c) 순서를 뒤집어, 로그인이 유저 행을 쥔 채 커밋하기 전에는 해제가 그 잠금에서 기다린다.

`asyncio.wait_for`로 막힌 호출 자체를 감싸면 타임아웃이 그 호출을 취소해 버려, 커밋 뒤에 새로
호출한 로그인이 통과하는 것과 구별이 안 된다 — 잠금은 있되 잠근 뒤 신원을 다시 보는 코드가 없어도
그 모양으로는 통과한다. 그래서 여기서는 `asyncio.create_task`로 호출을 띄운 뒤 `asyncio.sleep`으로
양보하고 `task.done()`이 거짓임을 확인해 "취소하지 않고 기다리는 중"임을 본 다음, 상대편이 커밋한
뒤 **같은 task**를 `asyncio.wait_for`로 거둔다. `asyncio.gather`로 HTTP 요청 두 개를 보내는 방식은
이 저장소에서 판별력이 없다고 이미 확인됐다. 토큰 원문은 단언에 쓰지 않는다.
"""
import asyncio

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.factory.social_provider_factory import SocialProviderFactory
from auth.adapter.outbound.pg.operator_pg_repository import OperatorPgRepository
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.dtos.token_dto import AccessToken
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
from auth.app.dtos.withdraw_dto import WithdrawCommand
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.token_issuer_port import TokenIssuerPort
from auth.app.services.session_issuer import SessionIssuer
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.app.use_cases.unlink_identity_interactor import UnlinkIdentityInteractor
from auth.app.use_cases.withdraw_interactor import WithdrawInteractor
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tests.integration.support import FakeKakaoStrategy

pytestmark = pytest.mark.integration

# FakeKakaoStrategy 는 토큰을 소문자로 낮춰 "kakao-{이름}" 을 신원으로 확인해 준다. _login() 이 항상
# 이 토큰으로 로그인하므로, 미리 심어 두는 카카오 신원도 항상 이 값이어야 "이미 연결된 신원"으로 잡힌다.
_KAKAO_TOKEN = "DubuKakao"
_KAKAO_SUB = f"kakao-{_KAKAO_TOKEN.lower()}"


class _StubTokenIssuer(TokenIssuerPort):
    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False
    ) -> AccessToken:
        return AccessToken(token=f"access-{user_id}", expires_in=900)


class _RecordingRefreshStore(RefreshTokenStorePort):
    """세대와 저장은 Redis 의 일이라 여기서는 흉내만 낸다. 판별은 Postgres 잠금이 한다.

    누구에게 저장을 요청했는지만 기록해, 해제·탈퇴된 유저에게 새 세션이 저장되지 않았는지 본다.
    """

    def __init__(self) -> None:
        self.saved_for_user_ids: list[int] = []

    async def current_generation(self, user_id: int) -> int:
        return 0

    async def save(self, token: str, user_id: int, generation: int) -> None:
        self.saved_for_user_ids.append(user_id)

    async def take(self, token: str):
        raise NotImplementedError

    async def revoke(self, token: str) -> None:
        pass

    async def revoke_all(self, user_id: int) -> None:
        pass


def _login(session, resolver, store):
    interactor = SocialLoginInteractor(
        providers=resolver, users=UserPgRepository(session),
        sessions=SessionIssuer(_StubTokenIssuer(), store),
    )
    return interactor.login(
        SocialLoginCommand(
            provider="kakao", token=_KAKAO_TOKEN,
            authorization_code=None, nonce=None, display_name=None,
        )
    )


def _unlink(session, user_id, provider, store):
    interactor = UnlinkIdentityInteractor(
        users=UserPgRepository(session), store=store,
        sessions=SessionIssuer(_StubTokenIssuer(), store),
    )
    return interactor.unlink(UnlinkIdentityCommand(user_id=user_id, provider=provider, auth_time=1_700_000_000))


def _withdraw(session, user_id, store):
    interactor = WithdrawInteractor(
        users=UserPgRepository(session),
        operators=OperatorPgRepository(session),
        lifecycle=ApplyWithdrawalInteractor(
            members=MemberPgRepository(session), shops=ShopPgRepository(session),
            invites=InvitePgRepository(session),
        ),
        store=store,
    )
    return interactor.withdraw(WithdrawCommand(user_id=user_id, confirm_close_shops=False))


async def _create_user_with_dev_and_kakao(factory, dev_sub: str):
    async with factory() as setup:
        users = UserPgRepository(setup)
        user = await users.create_with_identity(
            SocialProfile(Provider.DEV, dev_sub, None, "두부보호자", None, None)
        )
        await users.add_identity(
            user.id, SocialProfile(Provider.KAKAO, _KAKAO_SUB, None, "두부보호자", None, None)
        )
        await setup.commit()
    return user


async def test_해제가_유저_행을_쥔_동안_로그인은_기다리고_해제한_뒤에는_새_계정이_된다(db_engine):
    resolver = SocialProviderFactory({Provider.KAKAO: FakeKakaoStrategy()})
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    user = await _create_user_with_dev_and_kakao(factory, "login-race-dev")

    async with factory() as unlinking, factory() as logging_in:
        login_store = _RecordingRefreshStore()
        users = UserPgRepository(unlinking)
        assert (await users.lock(user.id)).id == user.id   # 해제가 맨 앞에서 하는 일
        await users.delete_identity(user.id, Provider.KAKAO)
        # 해제는 여기서 모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다. 커밋은 아직이다.

        login_task = asyncio.create_task(_login(logging_in, resolver, login_store))
        await asyncio.sleep(0.2)   # 로그인이 유저 행 잠금에서 멈출 시간을 준다
        assert not login_task.done()   # 취소하지 않고 "기다리는 중"임을 본다

        await unlinking.commit()

        # 막혀 있던 바로 그 호출이 풀려난다 — 해제된 수단은 빈 새 계정이 된다.
        result = await asyncio.wait_for(login_task, timeout=1)
        got_unlinked_users_session = result.user_id == user.id
        assert not got_unlinked_users_session
        assert result.is_new_user
        saved_for_unlinked_user = user.id in login_store.saved_for_user_ids
        saved_only_for_new_user = login_store.saved_for_user_ids == [result.user_id]
        assert not saved_for_unlinked_user
        assert saved_only_for_new_user
        await logging_in.rollback()


async def test_탈퇴가_유저_행을_쥔_동안_로그인은_기다리고_탈퇴한_뒤에는_새_계정이_된다(db_engine):
    resolver = SocialProviderFactory({Provider.KAKAO: FakeKakaoStrategy()})
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    user = await _create_user_with_dev_and_kakao(factory, "login-race-withdraw-dev")

    async with factory() as withdrawing, factory() as logging_in:
        withdraw_store = _RecordingRefreshStore()
        # 탈퇴는 유저 행 잠금부터 시작해 아무도 안 겹치므로 바로 끝까지 간다. 커밋은 아직이다.
        withdraw_result = await _withdraw(withdrawing, user.id, withdraw_store)
        assert len(withdraw_result.revocations) == 2

        login_store = _RecordingRefreshStore()
        login_task = asyncio.create_task(_login(logging_in, resolver, login_store))
        await asyncio.sleep(0.2)   # 로그인이 유저 행 잠금에서 멈출 시간을 준다
        assert not login_task.done()

        await withdrawing.commit()

        result = await asyncio.wait_for(login_task, timeout=1)
        got_withdrawn_users_session = result.user_id == user.id
        assert not got_withdrawn_users_session
        assert result.is_new_user
        saved_for_withdrawn_user = user.id in login_store.saved_for_user_ids
        saved_only_for_new_user = login_store.saved_for_user_ids == [result.user_id]
        assert not saved_for_withdrawn_user
        assert saved_only_for_new_user
        await logging_in.rollback()


async def test_로그인이_유저_행을_쥔_동안_해제는_기다린다(db_engine):
    resolver = SocialProviderFactory({Provider.KAKAO: FakeKakaoStrategy()})
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    user = await _create_user_with_dev_and_kakao(factory, "login-first-dev")

    async with factory() as logging_in, factory() as unlinking:
        login_store = _RecordingRefreshStore()
        # 겹치는 상대가 없으니 로그인은 바로 끝까지 간다 — 다만 유저 행 잠금은 커밋 전까지 쥔 채다.
        login_result = await _login(logging_in, resolver, login_store)
        got_existing_users_session = login_result.user_id == user.id
        assert got_existing_users_session

        unlink_store = _RecordingRefreshStore()
        unlink_task = asyncio.create_task(_unlink(unlinking, user.id, "dev", unlink_store))
        await asyncio.sleep(0.2)   # 해제가 유저 행 잠금에서 멈출 시간을 준다
        assert not unlink_task.done()

        await logging_in.commit()

        unlink_result = await asyncio.wait_for(unlink_task, timeout=1)
        assert unlink_result.identities == ("kakao",)
        await unlinking.rollback()
