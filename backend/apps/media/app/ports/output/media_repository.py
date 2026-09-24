from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from media.domain.entities.media_object import MediaObject
from media.domain.value_objects.new_media import NewMedia


class MediaRepository(ABC):
    """media_objects 표. 모든 메서드가 ShopContext 의 매장으로 거른다."""

    @abstractmethod
    async def create(self, ctx: ShopContext, new: NewMedia) -> MediaObject:
        """pending 으로 넣는다. 키는 ID 로 정해진다(`media_rules.object_keys`)."""

    @abstractmethod
    async def get(self, ctx: ShopContext, media_id: int) -> MediaObject:
        """없거나 다른 매장이면 MediaNotFoundError."""

    @abstractmethod
    async def mark_ready(self, ctx: ShopContext, media_id: int, size_bytes: int) -> bool:
        """pending 일 때만 ready 로 바꾼다(조건부 UPDATE). 바꿨으면 True — 동시에 두 번 확인해도 한 번만 바뀐다."""

    @abstractmethod
    async def attach_all(self, ctx: ShopContext, media_ids: list[int]) -> dict[int, str] | None:
        """준비됐고 아무도 가져가지 않은 이 매장의 미디어에 attached_at 을 찍는다. 전부 찍었으면 {id: kind},
        하나라도 못 찍었으면 아무것도 바꾸지 않고 None(세이브포인트)."""

    @abstractmethod
    async def detach(self, ctx: ShopContext, media_ids: list[int]) -> None: ...

    @abstractmethod
    async def list(self, ctx: ShopContext, media_ids: list[int]) -> list[MediaObject]:
        """이 매장의 것만, 상태와 상관없이."""
