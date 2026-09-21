"""F-I1 — 소셜 로그인은 해제된 수단으로 그 유저의 세션을 내주지 않는다. 실제 두 세션으로 확인한다.

해제는 `DELETE`(미커밋) → 모든 세션 폐기(세대 INCR) → 새 토큰 발급 → 커밋 순서로 돈다. 로그인이
유저 행을 잠그지 않으면, 커밋 전의 `find_by_identity`가 아직 그 신원을 보고(READ COMMITTED) 해제가
커밋된 **뒤에** 새 세대로 토큰을 저장해, 해제한 수단이 30일 세션을 쥐게 된다(G5 위반).

`asyncio.gather`로 HTTP 요청 두 개를 보내는 방식은 이 저장소에서 판별력이 없다고 두 번 확인됐다 —
세션 두 개로 잠금 시점을 직접 제어한다. 토큰 원문은 단언에 쓰지 않는다. 판별은 "기다리는가"와
"누구의 세션을 받았는가"로 한다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.factory.social_provider_factory import SocialProviderFactory
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.dtos.token_dto import AccessToken
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.token_issuer_port import TokenIssuerPort
from auth.app.services.session_issuer import SessionIssuer
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile
from tests.integration.support import FakeKakaoStrategy

pytestmark = pytest.mark.integration


class _StubTokenIssuer(TokenIssuerPort):
    def issue_access(self, user_id: int) -> AccessToken:
        return AccessToken(token=f"access-{user_id}", expires_in=900)


class _StubRefreshStore(RefreshTokenStorePort):
    """세대와 저장은 Redis 의 일이라 여기서는 흉내만 낸다. 판별은 Postgres 잠금이 한다."""

    async def current_generation(self, user_id: int) -> int:
        return 0

    async def save(self, token: str, user_id: int, generation: int) -> None:
        pass

    async def take(self, token: str):
        raise NotImplementedError

    async def revoke(self, token: str) -> None:
        pass

    async def revoke_all(self, user_id: int) -> None:
        pass


def _login(session, resolver):
    interactor = SocialLoginInteractor(
        providers=resolver, users=UserPgRepository(session),
        sessions=SessionIssuer(_StubTokenIssuer(), _StubRefreshStore()),
    )
    return interactor.login(
        SocialLoginCommand(
            provider="kakao", token="DubuKakao",
            authorization_code=None, nonce=None, display_name=None,
        )
    )


async def test_해제가_유저_행을_쥔_동안_로그인은_기다리고_해제한_뒤에는_새_계정이_된다(db_engine):
    resolver = SocialProviderFactory({Provider.KAKAO: FakeKakaoStrategy()})
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        users = UserPgRepository(setup)
        user = await users.create_with_identity(
            SocialProfile(Provider.DEV, "login-race-dev", None, "두부보호자", None, None)
        )
        await users.add_identity(
            user.id,
            SocialProfile(Provider.KAKAO, "kakao-dubukakao", None, "두부보호자", None, None),
        )
        await setup.commit()

    async with factory() as unlinking, factory() as logging_in:
        users = UserPgRepository(unlinking)
        assert (await users.lock(user.id)).id == user.id   # 해제가 맨 앞에서 하는 일
        await users.delete_identity(user.id, Provider.KAKAO)
        # 해제는 여기서 모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다. 커밋은 아직이다.

        # 카카오 로그인은 유저 행에서 기다린다 — 토큰을 내주기 전이다.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_login(logging_in, resolver), timeout=0.5)
        await logging_in.rollback()

        await unlinking.commit()

        # 풀려난 뒤의 로그인은 그 유저의 세션을 받지 못한다 — 해제된 수단은 빈 새 계정이 된다.
        result = await asyncio.wait_for(_login(logging_in, resolver), timeout=1)
        got_unlinked_users_session = result.user_id == user.id
        assert not got_unlinked_users_session
        assert result.is_new_user
        await logging_in.rollback()

    async with factory() as check:
        count = (
            await check.execute(
                text("SELECT count(*) FROM social_identities WHERE user_id = :id"), {"id": user.id}
            )
        ).scalar_one()
        # 보조 단언이다. 로그인 세션은 롤백하므로 잠금이 없어도 같다. 판별은 위의 raises 와 user_id 가 한다.
        assert count == 1
