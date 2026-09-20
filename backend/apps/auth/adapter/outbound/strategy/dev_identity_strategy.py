from __future__ import annotations

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile


class DevIdentityStrategy(SocialProviderPort):
    """개발 환경 전용 — 입력한 이름으로 바로 로그인된다. 팩토리가 APP_ENV=dev 일 때만 등록한다."""

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        name = credentials.token.strip()
        if not name:
            raise ProviderVerificationError("개발용 로그인에는 이름이 필요합니다.")
        return SocialProfile(
            provider=Provider.DEV,
            provider_user_id=name.lower(),
            email=None,
            display_name=name,
            profile_image_url=None,
            provider_refresh_token=None,
        )
