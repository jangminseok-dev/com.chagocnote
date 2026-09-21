from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from auth.adapter.outbound.strategy.apple_identity_strategy import (
    APPLE_JWKS_URL,
    AppleIdentityStrategy,
)
from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.adapter.outbound.strategy.google_identity_strategy import (
    GOOGLE_JWKS_URL,
    GoogleIdentityStrategy,
)
from auth.adapter.outbound.strategy.jwks_verifier import http_jwks_fetchers
from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.domain.errors import UnsupportedProviderError
from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class AppleSettings:
    bundle_id: str
    team_id: str
    key_id: str
    private_key_pem: str = field(repr=False)   # 원문이 로그·예외 메시지에 찍히지 않게 막는다


class SocialProviderFactory(SocialProviderResolverPort):
    def __init__(self, strategies: dict[Provider, SocialProviderPort]) -> None:
        self._strategies = strategies

    def resolve(self, provider: Provider) -> SocialProviderPort:
        try:
            return self._strategies[provider]
        except KeyError as exc:
            raise UnsupportedProviderError(
                f"{provider.value} 로그인은 지금 사용할 수 없습니다."
            ) from exc


def build_social_provider_factory(
    *, app_env: str, kakao_app_id: str, google_client_ids: tuple[str, ...],
    apple: AppleSettings | None, http: httpx.AsyncClient, kakao_admin_key: str = "",
) -> SocialProviderFactory:
    """설정값이 있는 제공자만 등록한다. dev 제공자는 개발 환경에서만 등록한다."""
    strategies: dict[Provider, SocialProviderPort] = {}
    if app_env == "dev":
        strategies[Provider.DEV] = DevIdentityStrategy()
    if kakao_app_id:
        strategies[Provider.KAKAO] = KakaoIdentityStrategy(kakao_app_id, http, kakao_admin_key)
    if google_client_ids:
        fetch, refetch = http_jwks_fetchers(http, GOOGLE_JWKS_URL)
        strategies[Provider.GOOGLE] = GoogleIdentityStrategy(google_client_ids, fetch, refetch)
    if apple is not None:
        fetch, refetch = http_jwks_fetchers(http, APPLE_JWKS_URL)
        strategies[Provider.APPLE] = AppleIdentityStrategy(
            apple.bundle_id, apple.team_id, apple.key_id, apple.private_key_pem,
            http, fetch, refetch_jwks=refetch,
        )
    return SocialProviderFactory(strategies)
