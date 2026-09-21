from __future__ import annotations

import logging
from collections.abc import Sequence

from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.domain.errors import ProviderRevokeError, UnsupportedProviderError
from auth.domain.value_objects.identity_revocation import IdentityRevocation

logger = logging.getLogger(__name__)


class ProviderRevoker:
    """탈퇴와 로그인 수단 해제가 함께 쓰는 제공자 쪽 연결 끊기.

    DB 커밋이 끝난 뒤(백그라운드 작업)에 부른다. 잠금을 쥔 채 외부 HTTP 를 부르지 않으려는 것이다.
    끊지 못해도 탈퇴·해제는 이미 끝났다. 실패는 로그로만 남긴다.
    """

    def __init__(self, providers: SocialProviderResolverPort) -> None:
        self._providers = providers

    async def revoke_all(self, identities: Sequence[IdentityRevocation]) -> None:
        for identity in identities:
            try:
                await self._providers.resolve(identity.provider).revoke(identity)
            except (ProviderRevokeError, UnsupportedProviderError) as exc:
                # 토큰은 남기지 않는다. 제공자와 이유만 남긴다.
                logger.warning(
                    "제공자 연결 끊기 실패 | provider=%s | %s", identity.provider.value, exc
                )
