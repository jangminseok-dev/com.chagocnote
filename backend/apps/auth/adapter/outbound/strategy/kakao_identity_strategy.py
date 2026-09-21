from __future__ import annotations

import httpx

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.errors import ProviderRevokeError, ProviderVerificationError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

_TOKEN_INFO_URL = "https://kapi.kakao.com/v1/user/access_token_info"
_ME_URL = "https://kapi.kakao.com/v2/user/me"
_UNLINK_URL = "https://kapi.kakao.com/v1/user/unlink"


class KakaoIdentityStrategy(SocialProviderPort):
    """카카오 액세스 토큰을 카카오에 직접 확인한다.

    토큰이 우리 앱에서 발급된 것인지(app_id) 먼저 본다. 이 확인이 없으면
    다른 서비스에서 받은 카카오 토큰으로 우리 서비스에 로그인할 수 있다.
    """

    def __init__(self, app_id: str, http: httpx.AsyncClient, admin_key: str = "") -> None:
        self._app_id = app_id
        self._http = http
        self._admin_key = admin_key

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        headers = {"Authorization": f"Bearer {credentials.token}"}
        info = await self._http.get(_TOKEN_INFO_URL, headers=headers)
        if info.status_code != 200 or str(info.json().get("app_id")) != self._app_id:
            raise ProviderVerificationError("카카오 토큰을 확인할 수 없습니다.")
        me = await self._http.get(_ME_URL, headers=headers)
        if me.status_code != 200:
            raise ProviderVerificationError("카카오 사용자 정보를 가져올 수 없습니다.")
        body = me.json()
        if "id" not in body:
            raise ProviderVerificationError("카카오 응답에 사용자 식별자가 없습니다.")
        account = body.get("kakao_account") or {}
        profile = account.get("profile") or {}
        return SocialProfile(
            provider=Provider.KAKAO,
            provider_user_id=str(body["id"]),
            email=account.get("email"),
            display_name=profile.get("nickname"),
            profile_image_url=profile.get("profile_image_url"),
            provider_refresh_token=None,
        )

    async def revoke(self, identity: IdentityRevocation) -> None:
        """어드민 키로 그 사용자와 우리 앱의 연결을 끊는다. 사용자의 카카오 토큰이 필요 없다."""
        if not self._admin_key:
            raise ProviderRevokeError("카카오 어드민 키가 없어 연결을 끊을 수 없습니다.")
        try:
            response = await self._http.post(
                _UNLINK_URL,
                headers={"Authorization": f"KakaoAK {self._admin_key}"},
                data={"target_id_type": "user_id", "target_id": identity.provider_user_id},
            )
        except httpx.HTTPError as exc:
            raise ProviderRevokeError("카카오에 연결할 수 없습니다.") from exc
        if response.status_code != 200:
            raise ProviderRevokeError(f"카카오가 연결 끊기를 거절했습니다 (상태 {response.status_code}).")
