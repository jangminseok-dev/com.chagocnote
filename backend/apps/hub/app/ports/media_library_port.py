from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.media_urls import MediaUrls
from hub.app.dtos.shop_context import ShopContext


class MediaLibraryPort(ABC):
    """구현: media. 사용: visit(기록의 사진·영상), customer(반려동물 프로필 사진).

    media 는 어느 기록이 미디어를 가져갔는지 모른다 — 가져갔다는 사실(attached_at)만 안다. 연결은 가져간 쪽이
    자기 표에 적는다. 가져가지 않은 채 하루가 지난 미디어는 정리 스크립트가 지운다(설계 7.5).
    """

    @abstractmethod
    async def claim(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str]:
        """미디어를 가져간다(attached_at 을 찍는다). 돌려주는 값은 {media_id: kind(photo·video)}.

        전부 되거나 전부 안 된다 — 하나라도 안 되면 아무것도 바꾸지 않고 허브 오류를 던진다:
        MediaClaimNotFoundError(없거나 다른 매장), MediaClaimNotReadyError(아직 확인 전),
        MediaClaimAlreadyAttachedError(이미 다른 기록이 가져갔다). 조건부 UPDATE 라 네트워크가 없고,
        방문 행을 잠근 채 불러도 된다. 두 요청이 같은 미디어를 동시에 가져가면 늦은 쪽이 AlreadyAttached 다.
        """

    @abstractmethod
    async def release(self, ctx: ShopContext, media_ids: list[int]) -> None:
        """가져간 것을 놓는다. 놓인 미디어는 다시 가져갈 수 있고, 아무도 가져가지 않으면 정리 스크립트가 지운다."""

    @abstractmethod
    async def read_urls(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, MediaUrls]:
        """준비된 이 매장의 미디어의 읽기 URL. 없거나 준비 전인 ID 는 빠진다. 서명은 계산이라 네트워크가 없다."""
