"""G1 — 로그인 수단이 둘일 때 서로 다른 수단의 해제가 동시에 와도 0개가 되지 않는다.

실제 두 세션으로 확인한다. `asyncio.gather`로 HTTP 요청 두 개를 보내는 방식은 이 저장소의
DB 왕복이 너무 빨라서 (docker 안의 로컬 Postgres) 잠금을 빼도 우연히 순차 실행처럼 끝나
판별력이 낮았다 — 직접 세션 두 개로 잠금 시점을 제어한다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.dtos.token_dto import AccessToken
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.token_issuer_port import TokenIssuerPort
from auth.app.services.session_issuer import SessionIssuer
from auth.app.use_cases.unlink_identity_interactor import UnlinkIdentityInteractor
from auth.domain.errors import LastIdentityError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile

pytestmark = pytest.mark.integration


class _StubTokenIssuer(TokenIssuerPort):
    def issue_access(
        self, user_id: int, *, auth_time: int | None = None, fresh_login: bool = False
    ) -> AccessToken:
        return AccessToken(token=f"access-{user_id}", expires_in=900)


class _StubRefreshStore(RefreshTokenStorePort):
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


def _unlink(session, user_id, provider):
    interactor = UnlinkIdentityInteractor(
        users=UserPgRepository(session), store=_StubRefreshStore(),
        sessions=SessionIssuer(_StubTokenIssuer(), _StubRefreshStore()),
    )
    return interactor.unlink(UnlinkIdentityCommand(user_id=user_id, provider=provider, auth_time=1_700_000_000))


async def test_동시에_서로_다른_수단을_해제해도_하나는_남는다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        users = UserPgRepository(setup)
        user = await users.create_with_identity(
            SocialProfile(Provider.DEV, "unlink-race", None, "두부보호자", None, None)
        )
        await users.add_identity(
            user.id, SocialProfile(Provider.KAKAO, "unlink-race-kakao", None, "두부보호자", None, None)
        )
        await setup.commit()

    async with factory() as first, factory() as second:
        first_users = UserPgRepository(first)
        assert (await first_users.lock(user.id)).id == user.id   # "dev" 해제가 맨 앞에서 하는 일

        # 같은 유저의 "kakao" 해제는 유저 행에서 기다린다 — 몇 개가 남았는지 세기도 전이다.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_unlink(second, user.id, "kakao"), timeout=0.5)
        await second.rollback()

        await first_users.delete_identity(user.id, Provider.DEV)
        await first.commit()

        # "dev" 해제가 커밋된 뒤에는 신원이 하나뿐이라 "kakao" 해제가 막힌다.
        with pytest.raises(LastIdentityError):
            await asyncio.wait_for(_unlink(second, user.id, "kakao"), timeout=0.5)
        await second.rollback()

    async with factory() as check:
        count = (
            await check.execute(
                text("SELECT count(*) FROM social_identities WHERE user_id = :id"), {"id": user.id}
            )
        ).scalar_one()
        # 보조 단언이다. 둘째 세션은 어느 쪽이든 롤백하므로 이 값은 잠금이 없어도 같다. 판별은 위의 두 raises 가 한다.
        assert count == 1
