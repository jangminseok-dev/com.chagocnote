from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.value_objects.new_message import NewMessage


class MessageRepository(ABC):
    """알림 줄(notification_messages)의 매장 범위 포트 — 구독자·설정·방문별 내역·재발송이 쓴다.

    쓰기는 고객 행 → 방문 행을 잠근 트랜잭션 안에서 부른다(잠금 순서의 끝 "→ 알림 행").
    """

    @abstractmethod
    async def create(self, ctx: ShopContext, new: NewMessage) -> NotificationMessage:
        """새 줄을 넣는다. 같은 방문·같은 종류의 대기 줄(scheduled·sending)이 있으면 MessageAlreadyPendingError —
        세이브포인트 안에서 넣으므로 트랜잭션은 계속 쓸 수 있다. new.shop_id 가 ctx 의 매장과 다르면 ValueError."""

    @abstractmethod
    async def cancel_pending(
        self, ctx: ShopContext, reason: str, visit_id: int | None = None, kinds: Iterable[str] | None = None
    ) -> int:
        """대기 줄(scheduled·sending)을 canceled 로. visit_id 가 없으면 매장 전체, kinds 가 없으면 전 종류. 바꾼 수."""

    @abstractmethod
    async def list_pending(self, ctx: ShopContext, kind: str) -> list[NotificationMessage]:
        """scheduled 인 줄만, scheduled_at 순 — 설정을 바꿀 때 다시 계산할 것."""

    @abstractmethod
    async def has_delivered(self, ctx: ShopContext, visit_id: int, kind: str, url: str | None = None) -> bool:
        """보낸 줄(sent·fallback_sent)이 있는가. url 을 주면 variables 의 url 이 같은 줄만(알림장)."""

    @abstractmethod
    async def has_pending_for_group(self, ctx: ShopContext, customer_id: int, kind: str, starts_at_iso: str) -> bool:
        """같은 보호자·같은 종류·같은 시작 시각(variables 의 starts_at)의 대기 줄(scheduled·sending)이 있는가 —
        가족 묶음(두 마리)을 한 통으로 보내려고 둘째 방문의 줄을 만들지 않는 데 쓴다."""

    @abstractmethod
    async def last_delivered_at(self, ctx: ShopContext, customer_id: int, kind: str) -> datetime | None:
        """그 고객에게 그 종류를 마지막으로 보낸 시각(쿨다운)."""

    @abstractmethod
    async def count_sent_since(self, ctx: ShopContext, since: datetime) -> int:
        """업체에 넘긴 줄(provider_message_id 가 있는)의 수, created_at >= since — 하루 상한."""

    @abstractmethod
    async def list_for_visit(self, ctx: ShopContext, visit_id: int) -> list[NotificationMessage]:
        """created_at 역순, id 역순."""

    @abstractmethod
    async def get(self, ctx: ShopContext, message_id: int) -> NotificationMessage | None:
        """없거나 다른 매장의 것이면 None."""

    @abstractmethod
    async def save(self, ctx: ShopContext, message: NotificationMessage) -> None:
        """id 로 찾아 바뀔 수 있는 칸만 UPDATE — status, attempts, next_attempt_at, scheduled_at, channel_used,
        provider_message_id, error_code, error_kind, sent_at, canceled_reason. 다른 매장의 줄은 건드리지 않는다."""
