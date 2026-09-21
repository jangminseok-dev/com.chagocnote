"""auth 슬라이스 프로바이더들이 함께 쓰는 조립 함수.

인증 프로세스 전용 비밀값이 필요한 조립은 core.auth_config 를 함수 안에서 import 한다.
모듈 최상단에서 import 하면 그 값이 없는 API 프로세스에서 이 모듈을 불러올 때 실패한다.
"""
from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.factory.social_provider_factory import (
    AppleSettings,
    build_social_provider_factory,
)
from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.adapter.outbound.pg.operator_pg_repository import OperatorPgRepository
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.adapter.outbound.redis.refresh_token_redis_store import RefreshTokenRedisStore
from auth.app.ports.output.operator_repository import OperatorRepository
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.provider_revoker import ProviderRevoker
from auth.app.services.session_issuer import SessionIssuer
from core import config
from core.redis import get_redis

_http: httpx.AsyncClient | None = None
_resolver: SocialProviderResolverPort | None = None


def get_http() -> httpx.AsyncClient:
    """제공자를 부르는 공용 클라이언트. 처음 쓸 때 만들고 프로세스가 끝날 때 닫는다."""
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=5.0)
    return _http


async def dispose_http() -> None:
    global _http, _resolver
    if _http is not None:
        await _http.aclose()
    _http = None
    _resolver = None  # 캐시된 제공자 목록이 방금 닫은 클라이언트를 붙들고 있으므로 함께 비운다.


def build_user_repository(db: AsyncSession) -> UserRepository:
    """읽기만 하는 경로용. 제공자 토큰을 저장하거나 복호화할 수 없다."""
    return UserPgRepository(db)


def build_user_repository_with_cipher(db: AsyncSession) -> UserRepository:
    """인증 프로세스 전용. 로그인·연결·해제·탈퇴가 쓴다."""
    from core.auth_config import IDENTITY_TOKEN_ENC_KEY

    return UserPgRepository(db, FernetCipher(IDENTITY_TOKEN_ENC_KEY))


def build_operator_repository(db: AsyncSession) -> OperatorRepository:
    return OperatorPgRepository(db)


def build_refresh_store() -> RefreshTokenStorePort:
    return RefreshTokenRedisStore(get_redis(), config.REFRESH_TOKEN_TTL_SECONDS)


def build_session_issuer() -> SessionIssuer:
    from core.auth_config import JWT_PRIVATE_KEY

    return SessionIssuer(
        JwtTokenIssuer(JWT_PRIVATE_KEY, config.ACCESS_TOKEN_TTL_SECONDS), build_refresh_store()
    )


def build_provider_resolver() -> SocialProviderResolverPort:
    """공개키 캐시를 유지하려고 프로세스에 하나만 만든다."""
    global _resolver
    if _resolver is None:
        from core.auth_config import KAKAO_ADMIN_KEY

        apple = None
        if config.APPLE_BUNDLE_ID and config.APPLE_PRIVATE_KEY:
            apple = AppleSettings(
                config.APPLE_BUNDLE_ID, config.APPLE_TEAM_ID,
                config.APPLE_KEY_ID, config.APPLE_PRIVATE_KEY,
            )
        _resolver = build_social_provider_factory(
            app_env=config.APP_ENV,
            kakao_app_id=config.KAKAO_APP_ID,
            google_client_ids=config.GOOGLE_CLIENT_IDS,
            apple=apple,
            http=get_http(),
            kakao_admin_key=KAKAO_ADMIN_KEY,
        )
    return _resolver


def build_provider_revoker() -> ProviderRevoker:
    return ProviderRevoker(build_provider_resolver())
