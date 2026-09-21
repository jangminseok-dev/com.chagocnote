from __future__ import annotations

from dataclasses import dataclass, field

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class SocialProfile:
    """제공자가 확인해 준 신원. 신원을 가르는 값(provider_user_id, email)은 제공자 응답에서만 만든다.

    예외는 Apple 의 display_name 하나다. Apple 은 이름을 서버에 주지 않고 첫 로그인 때 앱에만 주므로
    앱이 보낸 값을 그대로 쓴다. 표시 이름일 뿐 신원 확인에는 쓰이지 않는다.
    """

    provider: Provider
    provider_user_id: str
    email: str | None
    display_name: str | None
    profile_image_url: str | None
    provider_refresh_token: str | None = field(repr=False)
