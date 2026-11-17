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
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.services.family_group import PET_IDS, PET_VISITS, pet_visits_of, with_pets, without_pets
from notification.domain.services.schedule_rules import next_visit_at, next_visit_weeks, reminder_at
from notification.domain.value_objects.message_kind import CANCEL, CHANGE, CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.new_message import NewMessage
from notification.domain.value_objects.template_status import APPROVED


# 취소·노쇼가 묶음에서 아이를 빼는 종류 — cancel 은 뺀다(통째 취소에서 첫 이벤트가 만든 취소 안내를 둘째가 지우면 안 된다).
_GROUP_KINDS = (CONFIRM, REMINDER, CHANGE, NEXT_VISIT)


def _iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


class HandleVisitEventInteractor(HandleVisitEventUseCase):
    """visit 이벤트를 받아 같은 트랜잭션에서 알림 줄을 만들고 취소한다(설계 5.2 표).

    연동되지 않은 매장(채널이 linked 가 아니거나 설정이 없음)은 아무것도 하지 않는다 — 취소도 하지 않는다, 줄이 없다.
    업체를 부르지 않으므로 외부 장애로 방문 저장이 막히지 않는다(N13·N14). 같은 방문·종류의 대기 줄이 이미 있으면
    저장소의 MessageAlreadyPendingError 를 그대로 올린다(report·next_visit) — 발행 쪽의 중복 호출이 드러나게 둔다.

    가족 묶음(같은 보호자·같은 시작 시각의 방문들)은 한 통이다 — confirm·reminder·change·cancel 은 같은 보호자·시각·종류의
    대기 줄이 이미 있으면 만들지 않고, 만들 때 variables 의 pet_ids 에 묶음의 아이들을 싣는다(디스패처가 `#{대상}` 에
    이름을 나열한다). 아직 안 나간(scheduled) 묶음 줄은 지금 그 시각에 오는 아이들을 따라간다(설계 2026-11-10 3.1) —
    뒤늦게 같은 시각에 온 아이는 더하고(_create_for_group), 취소·노쇼·시각 변경·완료 되돌리기로 빠진 아이는 뺀다
    (_leave_group). 줄이 달린 아이가 빠지면 남은 아이의 방문으로 옮기고, 남는 아이가 없으면 취소한다.
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
        # 되돌린 예약은 접수 안내를 다시 보내지 않는다 — 리마인드만. 완료를 되돌렸으면 그 완료가 만든 다음 예약 제안도
        # 거둔다(다시 완료할 때 같은 방문·종류의 대기 줄 하나 규칙에 막히지 않게).
        if event.revived:
            kept = await self._leave_group(ctx, event, event.starts_at, "reverted", (NEXT_VISIT,), keep_stranded=True)
            await self._messages.cancel_pending(ctx, "reverted", event.visit_id, kinds=(NEXT_VISIT,), except_ids=kept)
        # 반복 예약의 둘째 회차부터(⑭)도 접수 안내 없이 리마인드만 — 접수 안내는 첫 회차 한 통이다.
        if not event.revived and not event.series_followup and await self._allowed(
                ctx, settings, CONFIRM, event.visit_id):
            await self._create_for_group(ctx, event, CONFIRM, now)
        at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
        if at is not None and await self._allowed(ctx, settings, REMINDER, event.visit_id):
            await self._create_for_group(ctx, event, REMINDER, at)

    async def _rescheduled(
        self, ctx: ShopContext, settings: NotificationSettings, event: VisitRescheduled, now: datetime
    ) -> None:
        # 옛 시각의 리마인드와 아직 안 나간 변경 안내를 거둔다(N16). 바뀐 일정의 리마인드·변경 안내는 앞서 보냈어도
        # 다시 간다 — 보호자에게 마지막 시각이 가야 한다. 연달아 바꾸면 마지막 변경 안내 한 통만 남는다.
        # 옮길 수 없는 묶음 줄은 제자리에 두지 않고 거둔다 — 이 방문에 새 시각의 같은 종류 줄을 달 자리가 필요하다.
        kept = await self._leave_group(ctx, event, event.previous_starts_at, "rescheduled", (REMINDER, CHANGE),
                                       keep_stranded=False)
        await self._messages.cancel_pending(ctx, "rescheduled", event.visit_id, kinds=(REMINDER, CHANGE),
                                            except_ids=kept)
        at = reminder_at(event.starts_at, settings.reminder_time, ctx.timezone, now)
        if at is not None and await self._allowed(ctx, settings, REMINDER):
            await self._create_for_group(ctx, event, REMINDER, at)
        if await self._allowed(ctx, settings, CHANGE):
            await self._create_for_group(ctx, event, CHANGE, now, previous_starts_at=_iso(event.previous_starts_at))

    async def _canceled(self, ctx: ShopContext, settings: NotificationSettings, event: VisitCanceled, now: datetime):
        kept = await self._leave_group(ctx, event, event.starts_at, "visit_canceled", _GROUP_KINDS, keep_stranded=True)
        await self._messages.cancel_pending(ctx, "visit_canceled", event.visit_id, except_ids=kept)   # N17
        if event.reason == "shop_reason" and await self._allowed(ctx, settings, CANCEL, event.visit_id):
            await self._create_for_group(ctx, event, CANCEL, now)

    async def _closed(self, ctx: ShopContext, settings: NotificationSettings, event: VisitClosed) -> None:
        if event.outcome == "no_show":
            kept = await self._leave_group(ctx, event, event.starts_at, "no_show", _GROUP_KINDS, keep_stranded=True)
            await self._messages.cancel_pending(ctx, "no_show", event.visit_id, except_ids=kept)   # N17
            return
        # 완료는 대기 줄을 건드리지 않는다.
        if not await self._allowed(ctx, settings, NEXT_VISIT, event.visit_id):
            return
        weeks = next_visit_weeks(event.cycle_weeks, event.cycle_source, event.default_cycle_weeks,
                                 settings.next_visit_after_weeks)
        at = next_visit_at(event.occurred_at, weeks, settings.reminder_time, ctx.timezone)
        # 가족 묶음을 함께 완료하면 제안도 한 통 — 둘째 방문은 묶음의 줄(같은 보호자·시작 시각)이 맡는다.
        # 묶음의 주 수는 아이들 가운데 짧은 쪽이다(둘째가 더 짧으면 줄을 당긴다).
        await self._create_for_group(ctx, event, NEXT_VISIT, at, completed_at=_iso(event.occurred_at),
                                     interval_weeks=str(weeks))

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

    async def _leave_group(
        self, ctx: ShopContext, event: VisitEvent, starts_at: datetime, reason: str, kinds: tuple[str, ...],
        keep_stranded: bool,
    ) -> list[int]:
        """이 명령이 함께 다룬 아이들을 그 시각의 scheduled 묶음 줄에서 뺀다. 남는 아이가 없는 줄은 취소하고, 줄이 달린
        아이가 빠졌으면 남은 아이의 방문으로 옮긴다. 옮길 수 없으면(방문 짝을 모르는 옛 줄, 옮길 방문에 같은 종류의 대기
        줄이 있음) keep_stranded 일 때 이름만 빼고 제자리에 두고, 아니면 취소한다. 이 이벤트의 방문에 남긴 줄의 id 를
        돌려준다 — 뒤따르는 방문 단위 취소가 건드리지 않게.

        떠나는 아이는 이벤트의 아이들에 더해 그 줄이 이 방문의 것으로 적어 둔 아이다(pet_visits 의 짝, 줄이 이 방문에
        달려 있으면 줄의 pet_id) — 수정 화면에서 반려동물을 바꾼 방문은 이벤트가 새 아이를 싣고 오므로 이벤트만 보면
        원래 아이가 줄에 남는다."""
        pets = self._pets(event)
        kept = []
        for m in await self._messages.list_scheduled_for_group(ctx, event.customer_id, _iso(starts_at), kinds):
            leaving = set(pets) | {p for p, v in pet_visits_of(m.variables).items() if v == event.visit_id}
            if m.visit_id == event.visit_id and m.pet_id is not None:
                leaving.add(m.pet_id)
            edit = without_pets(m, leaving)
            if edit is None:
                continue
            if edit.emptied:
                await self._messages.cancel_scheduled(ctx, m.id, reason)
                continue
            moved = not edit.stranded
            if moved and edit.visit_id != m.visit_id:
                try:
                    await self._messages.rewrite_scheduled(ctx, m.id, edit.variables, edit.visit_id, edit.pet_id)
                except MessageAlreadyPendingError:
                    moved = False
            elif moved:
                await self._messages.rewrite_scheduled(ctx, m.id, edit.variables, m.visit_id, m.pet_id)
            if not moved:
                if not keep_stranded:
                    await self._messages.cancel_scheduled(ctx, m.id, reason)
                    continue
                await self._messages.rewrite_scheduled(ctx, m.id, edit.variables, m.visit_id, m.pet_id)
                kept.append(m.id)
        return kept

    async def _create_for_group(
        self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
    ) -> None:
        """가족 묶음은 한 통이다 — 같은 보호자·같은 시작 시각·같은 종류의 scheduled 줄이 있으면 새로 만들지 않고 그 줄에
        이 이벤트의 아이들과 방문 짝을 더한다(설계 2026-11-10 3.1). 변경 안내는 옛 시각까지 같은 줄에만 더한다 — 다른
        시각에서 옮겨 온 아이는 "변경 전" 이 달라 자기 줄을 만든다. 보호자만의 방문에 달린 줄과 지금 나가는(sending)
        줄에는 더하지 않고 건너뛴다."""
        starts_at = _iso(event.starts_at)
        rows = await self._messages.list_scheduled_for_group(ctx, event.customer_id, starts_at, (kind,))
        if kind == CHANGE:
            rows = [m for m in rows if m.variables.get("previous_starts_at") == variables["previous_starts_at"]]
        if not rows:
            if kind != CHANGE and await self._messages.has_pending_for_group(ctx, event.customer_id, kind, starts_at):
                return
            await self._create(ctx, event, kind, scheduled_at, **variables)
            return
        host = next((m for m in rows if m.pet_id is not None), None)
        if host is None:
            return
        joined = with_pets(host, self._pets(event), event.pet_id, event.visit_id)
        sooner = kind == NEXT_VISIT and int(variables["interval_weeks"]) < int(host.variables.get("interval_weeks", "0"))
        if sooner:
            joined = {**(joined or host.variables), "interval_weeks": variables["interval_weeks"]}
        if joined is not None:
            await self._messages.rewrite_scheduled(ctx, host.id, joined, host.visit_id, host.pet_id,
                                                   scheduled_at=scheduled_at if sooner else None)

    @staticmethod
    def _pets(event: VisitEvent) -> tuple[int, ...]:
        """이 명령이 함께 다룬 아이들 — 묶음이 비면 자기 아이, 보호자만의 방문이면 없음."""
        return event.family_pet_ids or ((event.pet_id,) if event.pet_id is not None else ())

    async def _create(
        self, ctx: ShopContext, event: VisitEvent, kind: str, scheduled_at: datetime, **variables: str
    ) -> None:
        # starts_at 은 모든 종류에 넣는다 — 디스패처가 #{일시} 와 too_late 판정에 쓴다. pet_ids 는 #{대상} 의 아이들
        # (묶음이 비면 자기 아이, 보호자만의 방문이면 빈 문자열), pet_visits 는 아이별 방문(자기 짝만 — 묶음의 다른
        # 방문은 각자의 이벤트가 채운다).
        own = f"{event.pet_id}:{event.visit_id}" if event.pet_id is not None else ""
        await self._messages.create(ctx, NewMessage(
            shop_id=ctx.shop_id, visit_id=event.visit_id, customer_id=event.customer_id, pet_id=event.pet_id,
            kind=kind, scheduled_at=scheduled_at,
            variables={"starts_at": _iso(event.starts_at), **variables,
                       PET_IDS: ",".join(map(str, self._pets(event))), PET_VISITS: own},
        ))
