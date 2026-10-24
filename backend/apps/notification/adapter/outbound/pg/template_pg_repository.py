from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import to_template
from notification.adapter.outbound.orm.notification_orm import NotificationTemplateOrm
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.value_objects.template_status import PENDING


def by_kind(templates: list[NotificationTemplate]) -> list[NotificationTemplate]:
    """KINDS 의 순서로."""
    return sorted(templates, key=lambda t: KINDS.index(t.kind))


class TemplatePgRepository(TemplateRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_shop(self, ctx: ShopContext) -> list[NotificationTemplate]:
        rows = await self._session.execute(
            select(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.shop_id == ctx.shop_id)
            .execution_options(populate_existing=True)
        )
        return by_kind([to_template(row) for row in rows.scalars()])

    async def get(self, ctx: ShopContext, kind: str) -> NotificationTemplate | None:
        row = (
            await self._session.execute(
                select(NotificationTemplateOrm)
                .where(NotificationTemplateOrm.shop_id == ctx.shop_id, NotificationTemplateOrm.kind == kind)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        return to_template(row) if row is not None else None

    async def upsert(
        self, ctx: ShopContext, kind: str, text_version: int, provider_template_id: str, requested_at: datetime
    ) -> NotificationTemplate:
        fresh = dict(
            text_version=text_version, provider_template_id=provider_template_id, status=PENDING,
            rejected_reason=None, requested_at=requested_at, decided_at=None,
        )
        row = (
            await self._session.execute(
                pg_insert(NotificationTemplateOrm)
                .values(shop_id=ctx.shop_id, kind=kind, **fresh)
                .on_conflict_do_update(constraint="uq_notification_templates_shop_kind", set_=fresh)
                .returning(NotificationTemplateOrm)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        return to_template(row)

    async def set_status(
        self, ctx: ShopContext, kind: str, status: str, rejected_reason: str | None, decided_at: datetime
    ) -> None:
        await self._session.execute(
            update(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.shop_id == ctx.shop_id, NotificationTemplateOrm.kind == kind)
            .values(status=status, rejected_reason=rejected_reason, decided_at=decided_at)
        )

    async def delete_all(self, ctx: ShopContext) -> int:
        deleted = await self._session.execute(
            delete(NotificationTemplateOrm).where(NotificationTemplateOrm.shop_id == ctx.shop_id)
        )
        return deleted.rowcount
