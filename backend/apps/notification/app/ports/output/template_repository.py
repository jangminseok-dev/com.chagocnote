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
        """(shop, kind) 가 있으면 그 줄을 pending·새 판·새 업체 ID 로 덮고 rejected_reason·decided_at 을 비운다."""

    @abstractmethod
    async def set_status(
        self, ctx: ShopContext, kind: str, status: str, rejected_reason: str | None, decided_at: datetime
    ) -> None:
        """심사 결과를 적는다. 그 종류의 줄이 없으면 아무것도 하지 않는다."""

    @abstractmethod
    async def delete_all(self, ctx: ShopContext) -> int:
        """연동 해제 — 이 매장의 줄을 모두 지우고 지운 수를 돌려준다."""
