from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.visit_events import (
    VisitCanceled,
    VisitClosed,
    VisitEvent,
    VisitReportIssued,
    VisitReportRevoked,
    VisitRescheduled,
    VisitReserved,
)
from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
from notification.app.ports.input.handle_visit_event_use_case import HandleVisitEventUseCase
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_settings import NotificationSettings
from notification.domain.services.schedule_rules import interval_weeks, next_visit_at, reminder_at
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import APPROVED


def _iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


class HandleVisitEventInteractor(HandleVisitEventUseCase):
    """visit 이벤트를 받아 같은 트랜잭션에서 알림 줄을 만들고 취소한다(설계 5.2 표).

    연동되지 않은 매장(채널이 linked 가 아니거나 설정이 없음)은 아무것도 하지 않는다 — 취소도 하지 않는다, 줄이 없다.
    업체를 부르지 않으므로 외부 장애로 방문 저장이 막히지 않는다(N13·N14). 같은 방문·종류의 대기 줄이 이미 있으면
    저장소의 MessageAlreadyPendingError 를 그대로 올린다(report·next_visit) — 발행 쪽의 중복 호출이 드러나게 둔다.

    가족 묶음(같은 보호자·같은 시작 시각의 방문들)은 한 통이다 — confirm·reminder·change·cancel 은 같은 보호자·시각·종류의
    대기 줄이 이미 있으면 만들지 않고, 만들 때 variables 의 pet_ids 에 묶음의 아이들을 싣는다(디스패처가 `#{대상}` 에
    이름을 나열한다). 취소는 방문 ID 로 하므로 한 마리만 취소하면 그 방문의 줄만 거둔다.
    """

    def __init__(
        self, channels: ChannelRepository, settings: SettingsRepository, templates: TemplateRepository,
        messages: MessageRepository, now: Callable[[], datetime],
    ) -> None:
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._messages = messages
        self._now = now

    async def handle_visit_event(self, command: HandleVisitEventCommand) -> None:
        event, ctx = command.event, command.event.ctx
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            return
        settings = await self._settings.get(ctx)
        if settings is None:
            return
        now = self._now()
        if isinstance(event, VisitReserved):
            await self._reserved(ctx, settings, event, now)
        elif isinstance(event, VisitRescheduled):
            await self._rescheduled(ctx, settings, event, now)
        elif isinstance(event, VisitCanceled):
            await self._canceled(ctx, settings, event, now)
        elif isinstance(event, VisitClosed):
            await self._closed(ctx, settings, event)
        elif isinstance(event, VisitReportIssued):
            await self._report_issued(ctx, settings, event, now)
        elif isinstance(event, VisitReportRevoked):
            await self._messages.cancel_pending(ctx, "report_revoked", event.visit_id, kinds=(REPORT,))

    async def _reserved(self, ctx: ShopContext, settings: NotificationSettings, event: VisitReserved, now: datetime):
        # 되돌린 예약은 접수 안내를 다시 보내지 않는다 — 리마인드만.
        if not event.revived and await self._allowed(ctx, settings, CONFIRM, event.visit_id):
            await self._create_for_group(ctx, event, CONFIRM, now)
        at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
        if at is not None and await self._allowed(ctx, settings, REMINDER, event.visit_id):
            await self._create_for_group(ctx, event, REMINDER, at)

    async def _rescheduled(
        self, ctx: ShopContext, settings: NotificationSettings, event: VisitRescheduled, now: datetime
    ) -> None:
        # 옛 시각의 리마인드와 아직 안 나간 변경 안내를 거둔다(N16). 바뀐 일정의 리마인드·변경 안내는 앞서 보냈어도
        # 다시 간다 — 보호자에게 마지막 시각이 가야 한다. 연달아 바꾸면 마지막 변경 안내 한 통만 남는다.
        await self._messages.cancel_pending(ctx, "rescheduled", event.visit_id, kinds=(REMINDER, CHANGE))
        at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
        if at is not None and await self._allowed(ctx, settings, REMINDER):
            await self._create_for_group(ctx, event, REMINDER, at)
        if await self._allowed(ctx, settings, CHANGE):
            await self._create_for_group(ctx, event, CHANGE, now, previous_starts_at=_iso(event.previous_starts_at))

    async def _canceled(self, ctx: ShopContext, settings: NotificationSettings, event: VisitCanceled, now: datetime):
        await self._messages.cancel_pending(ctx, "visit_canceled", event.visit_id)   # N17
        if event.reason == "shop_reason" and await self._allowed(ctx, settings, CANCEL, event.visit_id):
            await self._create_for_group(ctx, event, CANCEL, now)

    async def _closed(self, ctx: ShopContext, settings: NotificationSettings, event: VisitClosed) -> None:
        if event.outcome == "no_show":
            await self._messages.cancel_pending(ctx, "no_show", event.visit_id)   # N17
            return
        # 완료는 대기 줄을 건드리지 않는다. 주 수는 설정값, 없으면 앞선 완료와의 간격(없으면 4주).
        if not await self._allowed(ctx, settings, NEXT_VISIT, event.visit_id):
            return
        weeks = settings.next_visit_after_weeks
        if weeks is None:
            weeks = interval_weeks(event.previous_completed_at, event.occurred_at, ctx.timezone)
        at = next_visit_at(event.occurred_at, weeks, settings.reminder_time, ctx.timezone)
        await self._create(ctx, event, NEXT_VISIT, at, completed_at=_iso(event.occurred_at), interval_weeks=str(weeks))

    async def _report_issued(
        self, ctx: ShopContext, settings: NotificationSettings, event: VisitReportIssued, now: datetime
    ) -> None:
        # 같은 주소를 이미 보냈으면 다시 보내지 않는다. 끊고 새로 보낸 링크(주소가 다름)는 다시 간다.
        if await self._allowed(ctx, settings, REPORT, event.visit_id, url=event.url):
            expires_at = _iso(event.expires_at) if event.expires_at is not None else ""
            await self._create(ctx, event, REPORT, now, url=event.url, expires_at=expires_at)

    async def _allowed(
        self, ctx: ShopContext, settings: NotificationSettings, kind: str, delivered_visit_id: int | None = None,
        url: str | None = None,
    ) -> bool:
        """설정이 켜져 있고 템플릿이 approved 이고, delivered_visit_id 를 주면 그 방문에 같은 종류를 보낸 적이 없다."""
        if not settings.enabled_for(kind):
            return False
        template = await self._templates.get(ctx, kind)
        if template is None or template.status != APPROVED:
            return False
        if delivered_visit_id is None:
            return True
        return not await self._messages.has_delivered(ctx, delivered_visit_id, kind, url=url)

    async def _create_for_group(
        self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
    ) -> None:
        """가족 묶음의 둘째 방문이면 만들지 않는다 — 같은 보호자·같은 시작 시각·같은 종류의 대기 줄이 한 통을 맡는다."""
        if await self._messages.has_pending_for_group(ctx, event.customer_id, kind, _iso(event.starts_at)):
            return
        await self._create(ctx, event, kind, scheduled_at, **variables)

    async def _create(
        self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
    ) -> None:
        # starts_at 은 모든 종류에 넣는다 — 디스패처가 #{일시} 와 too_late 판정에 쓴다. pet_ids 는 #{대상} 의 아이들
        # (묶음이 비면 자기 아이, 보호자만의 방문이면 빈 문자열).
        pet_ids = event.family_pet_ids or ((event.pet_id,) if event.pet_id is not None else ())
        await self._messages.create(ctx, NewMessage(
            shop_id=ctx.shop_id, visit_id=event.visit_id, customer_id=event.customer_id, pet_id=event.pet_id,
            kind=kind, scheduled_at=scheduled_at,
            variables={"starts_at": _iso(event.starts_at), **variables, "pet_ids": ",".join(map(str, pet_ids))},
        ))
