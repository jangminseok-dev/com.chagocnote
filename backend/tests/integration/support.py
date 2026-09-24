"""실제 배선 통합 테스트가 함께 쓰는 도우미."""
from __future__ import annotations

from dataclasses import dataclass

import httpx
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class Wired:
    auth: AsyncClient   # 인증 프로세스 (auth_main.app)
    api: AsyncClient    # API 프로세스 (main.app)
    engine: AsyncEngine

    async def login(self, name: str) -> dict:
        response = await self.auth.post("/v1/auth/social", json={"provider": "dev", "token": name})
        assert response.status_code == 200, response.text
        return response.json()

    async def execute(self, sql: str, **params) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(text(sql), params)


async def make_operator(wired: Wired, name: str = "운영자") -> dict:
    login = await wired.login(name)
    await wired.execute("INSERT INTO platform_operators (user_id) VALUES (:id)", id=login["user_id"])
    return login


async def open_shop(wired: Wired, operator: dict, name: str = "Hiss Haus") -> dict:
    response = await wired.api.post(
        "/v1/platform/shops", json={"name": name}, headers=bearer(operator["access_token"])
    )
    assert response.status_code == 201, response.text
    return response.json()


async def accept_invite(wired: Wired, login: dict, code: str):
    return await wired.api.post(
        "/v1/invites/accept", json={"code": code}, headers=bearer(login["access_token"])
    )


async def shop_with_owner(wired: Wired, operator: dict, shop_name: str, owner_name: str):
    shop = await open_shop(wired, operator, shop_name)
    owner = await wired.login(owner_name)
    assert (await accept_invite(wired, owner, shop["owner_invite_code"])).status_code == 200
    return shop["shop_id"], owner


async def staff_invite(wired: Wired, shop_id: int, owner: dict) -> str:
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/invites", headers=bearer(owner["access_token"])
    )
    assert response.status_code == 201, response.text
    return response.json()["code"]


def error_of(response) -> tuple[int, str]:
    return (response.status_code, response.json()["code"])


class FakeKakaoStrategy(SocialProviderPort):
    """통합 테스트용 두 번째 제공자. 토큰으로 받은 이름을 그대로 카카오 신원으로 확인해 준다.

    한 유저는 제공자마다 신원을 하나만 가지므로, 연결·해제를 실제 배선으로 돌리려면 dev 말고 하나가 더 필요하다.
    """

    def __init__(self) -> None:
        self.revoked: list[str] = []

    async def verify(self, credentials) -> SocialProfile:
        name = credentials.token.strip()
        return SocialProfile(Provider.KAKAO, f"kakao-{name.lower()}", None, name, None, None)

    async def revoke(self, identity) -> None:
        self.revoked.append(identity.provider_user_id)


PHOTO = {"kind": "photo", "content_type": "image/jpeg", "byte_size": 3000, "width": 3000, "height": 2000}


async def issue_media(wired: Wired, shop_id: int, headers: dict, body: dict = PHOTO) -> dict:
    response = await wired.api.post(f"/v1/shops/{shop_id}/media/uploads", json=body, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()


async def upload_media(issued: dict, sizes=(3000, 800, 200)) -> None:
    """렌디션마다 서명 URL 로 서명한 형식 그대로 PUT 한다. 영상이면 표시용이 없다."""
    puts = issued["puts"]
    async with httpx.AsyncClient() as http:
        for name, size in zip(("original", "display", "thumb"), sizes):
            if puts[name] is None:
                continue
            content_type = "video/mp4" if name == "original" and ".mp4" in puts[name] else "image/jpeg"
            put = await http.put(puts[name], content=b"\x00" * size, headers={"Content-Type": content_type})
            assert put.status_code == 200, put.text


async def ready_photo(wired: Wired, shop_id: int, headers: dict) -> int:
    """발급 → 올리기 → 확인까지 마친 사진 하나의 ID. `media_storage` 픽스처가 필요하다."""
    issued = await issue_media(wired, shop_id, headers)
    await upload_media(issued)
    confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    return issued["media_id"]
