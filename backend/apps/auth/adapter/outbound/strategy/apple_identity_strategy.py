from __future__ import annotations

import hashlib
import time
from collections.abc import Callable

import httpx
from jose import jwt

from auth.adapter.outbound.strategy.jwks_verifier import JwksFetcher, verify_with_jwks
from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.errors import ProviderRevokeError, ProviderVerificationError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
_ISSUER = "https://appleid.apple.com"
_TOKEN_URL = "https://appleid.apple.com/auth/token"
_REVOKE_URL = "https://appleid.apple.com/auth/revoke"


class AppleIdentityStrategy(SocialProviderPort):
    """Apple ID 토큰을 검증하고, 인가 코드를 Apple 리프레시 토큰으로 바꾼다.

    리프레시 토큰은 회원 탈퇴 때 Apple 쪽 연결을 끊는 데 쓴다 (App Store 요구 사항).
    """

    def __init__(
        self, bundle_id: str, team_id: str, key_id: str, private_key_pem: str,
        http: httpx.AsyncClient, fetch_jwks: JwksFetcher,
        now: Callable[[], float] = time.time,
        refetch_jwks: JwksFetcher | None = None,
    ) -> None:
        self._bundle_id = bundle_id
        self._team_id = team_id
        self._key_id = key_id
        self._private_key_pem = private_key_pem
        self._http = http
        self._fetch_jwks = fetch_jwks
        self._now = now
        self._refetch_jwks = refetch_jwks

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        claims = await verify_with_jwks(
            credentials.token, self._fetch_jwks, (_ISSUER,), (self._bundle_id,), self._refetch_jwks
        )
        expected = hashlib.sha256((credentials.nonce or "").encode()).hexdigest()
        if credentials.nonce is None or claims.get("nonce") != expected:
            raise ProviderVerificationError("Apple 로그인 요청을 확인할 수 없습니다.")
        refresh = None
        if credentials.authorization_code:
            refresh = await self._exchange(credentials.authorization_code)
        return SocialProfile(
            provider=Provider.APPLE,
            provider_user_id=str(claims["sub"]),
            email=claims.get("email"),
            display_name=credentials.display_name,
            profile_image_url=None,
            provider_refresh_token=refresh,
        )

    def _client_secret(self) -> str:
        issued_at = int(self._now())
        return jwt.encode(
            {"iss": self._team_id, "iat": issued_at, "exp": issued_at + 300,
             "aud": _ISSUER, "sub": self._bundle_id},
            self._private_key_pem, algorithm="ES256", headers={"kid": self._key_id},
        )

    async def _exchange(self, authorization_code: str) -> str | None:
        response = await self._http.post(_TOKEN_URL, data={
            "client_id": self._bundle_id,
            "client_secret": self._client_secret(),
            "code": authorization_code,
            "grant_type": "authorization_code",
        })
        if response.status_code != 200:
            raise ProviderVerificationError("Apple 인가 코드를 확인할 수 없습니다.")
        return response.json().get("refresh_token")

    async def revoke(self, identity: IdentityRevocation) -> None:
        """저장해 둔 Apple 리프레시 토큰을 폐기한다 (App Store 심사 가이드라인 5.1.1(v))."""
        if not identity.provider_refresh_token:
            raise ProviderRevokeError("저장된 Apple 리프레시 토큰이 없어 연결을 끊을 수 없습니다.")
        try:
            response = await self._http.post(_REVOKE_URL, data={
                "client_id": self._bundle_id,
                "client_secret": self._client_secret(),
                "token": identity.provider_refresh_token,
                "token_type_hint": "refresh_token",
            })
        except httpx.HTTPError as exc:
            raise ProviderRevokeError("Apple 에 연결할 수 없습니다.") from exc
        if response.status_code != 200:
            raise ProviderRevokeError(f"Apple 이 토큰 폐기를 거절했습니다 (상태 {response.status_code}).")
