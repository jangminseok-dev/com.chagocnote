from __future__ import annotations

from auth.adapter.outbound.strategy.jwks_verifier import JwksFetcher, verify_with_jwks
from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleIdentityStrategy(SocialProviderPort):
    def __init__(self, client_ids: tuple[str, ...], fetch_jwks: JwksFetcher) -> None:
        self._client_ids = client_ids
        self._fetch_jwks = fetch_jwks

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        claims = await verify_with_jwks(
            credentials.token, self._fetch_jwks, _ISSUERS, self._client_ids
        )
        return SocialProfile(
            provider=Provider.GOOGLE,
            provider_user_id=str(claims["sub"]),
            email=claims.get("email"),
            display_name=claims.get("name"),
            profile_image_url=claims.get("picture"),
            provider_refresh_token=None,
        )
