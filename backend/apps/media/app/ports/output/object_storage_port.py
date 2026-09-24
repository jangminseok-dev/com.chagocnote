from __future__ import annotations

from abc import ABC, abstractmethod

from media.domain.services.url_expiry import SigningWindow
from media.domain.value_objects.object_info import ObjectInfo


class ObjectStoragePort(ABC):
    """객체 저장소(S3·MinIO). 올리기·내려받기는 앱이 서명 URL 로 직접 하고, 서버는 서명·확인·삭제만 한다(설계 7.4)."""

    @abstractmethod
    def presign_put(self, key: str, content_type: str, expires_in_seconds: int) -> str:
        """앱이 인증 헤더 없이 PUT 할 URL. Content-Type 이 서명에 든다 — 다른 형식으로 올리면 저장소가 거절한다."""

    @abstractmethod
    def presign_get(self, key: str, window: SigningWindow) -> str:
        """읽기 URL. 같은 창이면 글자까지 같다(앱·CDN 캐시)."""

    @abstractmethod
    async def head(self, key: str) -> ObjectInfo | None:
        """없으면 None. 잠금을 쥔 채 부르지 않는다(외부 네트워크)."""

    @abstractmethod
    async def delete(self, keys: list[str]) -> None:
        """없는 키는 조용히 넘어간다. 잠금을 쥔 채 부르지 않는다."""
