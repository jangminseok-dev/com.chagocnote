from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from notification.adapter.outbound.mappers.notification_mapper import to_channel, to_message, to_template
from notification.adapter.outbound.orm.notification_orm import (
    NotificationChannelOrm,
    NotificationMessageOrm,
    NotificationTemplateOrm,
)
from notification.adapter.outbound.pg.template_pg_repository import by_kind
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    DELIVERED_STATUSES,
    PENDING_STATUSES,
    SCHEDULED,
    SENDING,
)
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import PENDING

_PENDING_INDEX = "uq_notification_messages_pending"
_M = NotificationMessageOrm


class MessagePgRepository(MessageRepository, NotificationQueueRepository):
    """notification_messages 표 하나를 두 포트로 내놓는다 — 매장 범위(구독자·API)와 전 매장(디스패처)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def _rows(self, statement) -> list[NotificationMessage]:
        rows = await self._session.execute(statement.execution_options(populate_existing=True))
        return [to_message(row) for row in rows.scalars()]

    # --- 매장 범위 ----------------------------------------------------------------------------------------------

    async def create(self, ctx: ShopContext, new: NewMessage) -> NotificationMessage:
        if new.shop_id != ctx.shop_id:
            raise ValueError("메시지의 매장이 컨텍스트의 매장과 다릅니다.")
        statement = (
            insert(_M)
            .values(
                shop_id=ctx.shop_id, visit_id=new.visit_id, customer_id=new.customer_id, pet_id=new.pet_id,
                kind=new.kind, scheduled_at=new.scheduled_at, variables=dict(new.variables),
                requested_by_member_id=new.requested_by_member_id,
            )
            .returning(_M)
            .execution_options(populate_existing=True)
        )
        # 세이브포인트 — 유일 위반이 트랜잭션 전체를 버리지 않게. 늦은 쪽은 앞선 쪽의 커밋까지 색인에서 기다렸다가 여기서 걸린다.
        try:
            async with self._session.begin_nested():
                row = (await self._session.execute(statement)).scalar_one()
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) == _PENDING_INDEX:
                raise MessageAlreadyPendingError("같은 방문·종류의 알림이 이미 대기 중입니다.") from exc
            raise
        return to_message(row)

    async def cancel_pending(
        self, ctx: ShopContext, reason: str, visit_id: int | None = None, kinds: Iterable[str] | None = None
    ) -> int:
        conditions = [_M.shop_id == ctx.shop_id, _M.status.in_(PENDING_STATUSES)]
        if visit_id is not None:
            conditions.append(_M.visit_id == visit_id)
        if kinds is not None:
            conditions.append(_M.kind.in_(list(kinds)))
        canceled = await self._session.execute(
            update(_M).where(*conditions).values(status=CANCELED, canceled_reason=reason)
        )
        return canceled.rowcount

    async def list_pending(self, ctx: ShopContext, kind: str) -> list[NotificationMessage]:
        return await self._rows(
            select(_M)
            .where(_M.shop_id == ctx.shop_id, _M.kind == kind, _M.status == SCHEDULED)
            .order_by(_M.scheduled_at, _M.id)
        )

    async def has_delivered(self, ctx: ShopContext, visit_id: int, kind: str, url: str | None = None) -> bool:
        conditions = [_M.shop_id == ctx.shop_id, _M.visit_id == visit_id, _M.kind == kind,
                      _M.status.in_(DELIVERED_STATUSES)]
        if url is not None:
            conditions.append(_M.variables["url"].astext == url)
        found = await self._session.execute(select(_M.id).where(*conditions).limit(1))
        return found.first() is not None

    async def has_pending_for_group(self, ctx: ShopContext, customer_id: int, kind: str, starts_at_iso: str) -> bool:
        found = await self._session.execute(
            select(_M.id).where(
                _M.shop_id == ctx.shop_id, _M.customer_id == customer_id, _M.kind == kind,
                _M.status.in_(PENDING_STATUSES), _M.variables["starts_at"].astext == starts_at_iso,
            ).limit(1)
        )
        return found.first() is not None

    async def last_delivered_at(self, ctx: ShopContext, customer_id: int, kind: str) -> datetime | None:
        return (
            await self._session.execute(
                select(func.max(_M.sent_at)).where(
                    _M.shop_id == ctx.shop_id, _M.customer_id == customer_id, _M.kind == kind,
                    _M.status.in_(DELIVERED_STATUSES),
                )
            )
        ).scalar_one()

    async def count_sent_since(self, ctx: ShopContext, since: datetime) -> int:
        return (
            await self._session.execute(
                select(func.count()).select_from(_M).where(
                    _M.shop_id == ctx.shop_id, _M.provider_message_id.is_not(None), _M.created_at >= since
                )
            )
        ).scalar_one()

    async def list_for_visit(self, ctx: ShopContext, visit_id: int) -> list[NotificationMessage]:
        return await self._rows(
            select(_M)
            .where(_M.shop_id == ctx.shop_id, _M.visit_id == visit_id)
            .order_by(_M.created_at.desc(), _M.id.desc())
        )

    async def get(self, ctx: ShopContext, message_id: int) -> NotificationMessage | None:
        found = await self._rows(select(_M).where(_M.shop_id == ctx.shop_id, _M.id == message_id))
        return found[0] if found else None

    async def save(self, ctx: ShopContext, message: NotificationMessage) -> None:
        await self._session.execute(
            update(_M)
            .where(_M.shop_id == ctx.shop_id, _M.id == message.id)
            .values(
                status=message.status, attempts=message.attempts, next_attempt_at=message.next_attempt_at,
                scheduled_at=message.scheduled_at, channel_used=message.channel_used,
                provider_message_id=message.provider_message_id, error_code=message.error_code,
                error_kind=message.error_kind, sent_at=message.sent_at, canceled_reason=message.canceled_reason,
            )
        )

    # --- 전 매장(디스패처) ---------------------------------------------------------------------------------------

    async def claim_due(self, now: datetime, limit: int) -> list[NotificationMessage]:
        due = (
            select(_M.id)
            .where(_M.status == SCHEDULED, _M.scheduled_at <= now)
            .order_by(_M.scheduled_at, _M.id)
            .limit(limit)
            .with_for_update(skip_locked=True)   # 다른 디스패처가 쥔 줄은 건너뛴다(N6)
        )
        claimed = await self._rows(
            update(_M).where(_M.id.in_(due)).values(status=SENDING, updated_at=now).returning(_M)
        )
        return sorted(claimed, key=lambda m: (m.scheduled_at, m.id))

    async def recover_stuck(self, before: datetime) -> int:
        recovered = await self._session.execute(
            update(_M)
            .where(_M.status == SENDING, _M.updated_at < before)
            .values(status=SCHEDULED, attempts=_M.attempts + 1)
        )
        return recovered.rowcount

    async def list_accepted(self, now: datetime) -> list[NotificationMessage]:
        return await self._rows(
            select(_M).where(_M.status == ACCEPTED, _M.next_attempt_at <= now).order_by(_M.next_attempt_at, _M.id)
        )

    async def list_pending_templates(self) -> list[NotificationTemplate]:
        rows = await self._session.execute(
            select(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.status == PENDING)
            .order_by(NotificationTemplateOrm.id)
            .execution_options(populate_existing=True)
        )
        return [to_template(row) for row in rows.scalars()]

    async def list_linked_channels(self) -> list[NotificationChannel]:
        rows = await self._session.execute(
            select(NotificationChannelOrm)
            .where(NotificationChannelOrm.status == LINKED)
            .order_by(NotificationChannelOrm.shop_id)
            .execution_options(populate_existing=True)
        )
        return [to_channel(row) for row in rows.scalars()]

    async def list_templates_for_shops(self, shop_ids: list[int]) -> dict[int, list[NotificationTemplate]]:
        grouped: dict[int, list[NotificationTemplate]] = {shop_id: [] for shop_id in shop_ids}
        if not shop_ids:
            return grouped
        rows = await self._session.execute(
            select(NotificationTemplateOrm)
            .where(NotificationTemplateOrm.shop_id.in_(shop_ids))
            .execution_options(populate_existing=True)
        )
        for row in rows.scalars():
            grouped[row.shop_id].append(to_template(row))
        return {shop_id: by_kind(templates) for shop_id, templates in grouped.items()}
