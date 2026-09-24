from __future__ import annotations

from abc import ABC, abstractmethod

from media.app.dtos.media_myself_dto import MediaMyselfQuery, MediaMyselfResponse


class MediaMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: MediaMyselfQuery) -> MediaMyselfResponse: ...
