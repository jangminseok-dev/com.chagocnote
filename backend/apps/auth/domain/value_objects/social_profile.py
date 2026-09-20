from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class SocialProfile:
    """제공자가 확인해 준 신원. 앱이 보낸 값이 아니라 제공자 응답에서만 만든다."""

    provider: Provider
    provider_user_id: str
    email: str | None
    display_name: str | None
    profile_image_url: str | None
    provider_refresh_token: str | None
