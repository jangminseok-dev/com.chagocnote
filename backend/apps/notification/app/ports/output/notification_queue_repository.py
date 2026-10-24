from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_template import NotificationTemplate


class NotificationQueueRepository(ABC):
    """요청 밖에서 도는 디스패처가 쓰는 전 매장 질의.

    `ShopContext` 를 받지 않는 저장소다 — 공개 알림장의 `PublicReportRepository` 와 같은 예외. 디스패처는 매장이 아니라
    "시각이 된 줄 전부"를 집고, 매장별 읽기는 집은 줄의 shop_id 로 `system_context` 를 만들어 매장 범위 포트로 한다.
    """

    @abstractmethod
    async def claim_due(self, now: datetime, limit: int) -> list[NotificationMessage]:
        """status='scheduled' AND scheduled_at <= now 인 줄을 scheduled_at·id 순으로 limit 만큼 FOR UPDATE SKIP LOCKED 로
        집어 sending 으로 바꾸고(updated_at = now) 바뀐 줄을 돌려준다. 커밋은 부르는 쪽 — 커밋한 뒤 업체를 부른다(N6·N14)."""

    @abstractmethod
    async def recover_stuck(self, before: datetime) -> int:
        """집은 뒤 죽어 남은 sending(updated_at < before)을 scheduled 로 되돌리고 attempts 를 하나 올린다(N7). 바꾼 수."""

    @abstractmethod
    async def list_accepted(self, now: datetime) -> list[NotificationMessage]:
        """status='accepted' AND next_attempt_at <= now — next_attempt_at 을 '다음에 상태를 물을 시각'으로 쓴다."""

    @abstractmethod
    async def list_pending_templates(self) -> list[NotificationTemplate]:
        """심사 중인 템플릿 전부(매장 불문), id 순."""

    @abstractmethod
    async def list_linked_channels(self) -> list[NotificationChannel]:
        """연동된 채널 전부, shop_id 순."""

    @abstractmethod
    async def list_templates_for_shops(self, shop_ids: list[int]) -> dict[int, list[NotificationTemplate]]:
        """넘긴 매장마다 템플릿 목록(KINDS 순). 템플릿이 없는 매장은 빈 목록."""
