from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from visit.app.dtos.report_target_dto import ReportTarget


class PublicReportRepository(ABC):
    """로그인이 없는 공개 조회가 쓰는 알림장 링크.

    `ShopContext` 를 받지 않는 **유일한** 저장소다. 보호자는 멤버가 아니라 매장 컨텍스트가 없다 — 서명을 확인한
    토큰의 public_id 가 곧 범위이고, 매장은 찾은 방문에서 읽는다. 서명을 확인하지 않은 값을 넘기지 않는다.
    """

    @abstractmethod
    async def find(self, public_id: bytes) -> ReportTarget | None:
        """끊었든 기간이 지났든 줄이 있으면 준다 — 404 와 410 을 가르는 것은 부르는 쪽이다."""

    @abstractmethod
    async def mark_viewed(self, report_id: int, now: datetime) -> None:
        """처음 연 시각을 적는다. 이미 적혀 있으면 그대로 둔다 — 조건부 UPDATE 한 줄이라 잠금이 없다."""
