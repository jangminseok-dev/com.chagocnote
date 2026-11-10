from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from notification.domain.entities.notification_template import NotificationTemplate


class TemplateRepository(ABC):
    """매장 채널에 등록한 종류별 템플릿의 심사 상태(notification_templates). 매장 범위, (shop, kind) 유일."""

    @abstractmethod
    async def list_for_shop(self, ctx: ShopContext) -> list[NotificationTemplate]:
        """종류 순(KINDS 의 순서)."""

    @abstractmethod
    async def get(self, ctx: ShopContext, kind: str) -> NotificationTemplate | None: ...

    @abstractmethod
    async def upsert(
        self, ctx: ShopContext, kind: str, text_version: int, provider_template_id: str, requested_at: datetime
    ) -> NotificationTemplate:
        """등록·검수 요청한 판을 적는다. 기존 줄이 approved 면 대기 칸(pending_*)에만 적고 나머지는 그대로 둔다 —
        심사가 끝날 때까지 옛 판으로 계속 보낸다(이미 대기 판이 있으면 덮는다). 그 밖(없음·pending·rejected)은 그 줄을
        pending·새 판·새 업체 ID 로 덮고 rejected_reason·decided_at 과 대기 칸을 비운다."""

    @abstractmethod
    async def set_status(
        self, ctx: ShopContext, kind: str, status: str, rejected_reason: str | None, decided_at: datetime
    ) -> None:
        """심사 결과를 적는다. 그 종류의 줄이 없으면 아무것도 하지 않는다."""

    @abstractmethod
    async def decide_pending(
        self, ctx: ShopContext, kind: str, approved: bool, rejected_reason: str | None, decided_at: datetime
    ) -> None:
        """대기 판의 심사 결과. 승인이면 대기 판을 본 칸(text_version·provider_template_id)으로 올리고 decided_at 을 적고
        rejected_reason 을 비운다. 반려면 본 칸은 그대로 두고 rejected_reason 만 적는다. 어느 쪽이든 대기 칸을 비운다.
        status 는 건드리지 않는다. 대기 칸이 빈 줄에는 아무것도 하지 않는다."""

    @abstractmethod
    async def delete_all(self, ctx: ShopContext) -> int:
        """연동 해제 — 이 매장의 줄을 모두 지우고 지운 수를 돌려준다."""
