"""디스패처 — 시각이 된 줄을 집어 검사하고(설계 5.3) 게이트웨이로 보내고 결과를 적는다. 템플릿 상태·잔액도 주기적으로 본다.

집고 → 커밋 → 검사 → 보내기 → 접수 기록. 잠금(집기)을 쥔 채 업체를 부르지 않는다(N14). 요청 밖이라 ShopContext 는
system_context 로 만든다. 로그에는 message_id·shop_id·종류·결과만 — 번호·이름·주소·변수·업체 응답은 찍지 않는다(N12).
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from hub.app.dtos.shop_context import system_context
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import (
    DeliveryState,
    FallbackText,
    GatewayError,
    GatewayPermanentError,
    GatewayTransientError,
    MessageGatewayPort,
    OutgoingMessage,
)
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.app.services.message_text import message_pet_ids, message_target, message_variables
from notification.app.services.template_registration import REJECTED_NEW_VERSION, record_template_state
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.services.schedule_rules import (
    ACCEPTED_TIMEOUT,
    STUCK_AFTER,
    deferred_for_daytime,
    is_mobile_number,
    is_too_late,
    retry_at,
)
from notification.domain.services.templates import TEMPLATES, TEXT_VERSION, render, sms_channel
from notification.domain.value_objects.message_kind import DEFAULT_KINDS, NEXT_VISIT, REMINDER, SCHEDULED_KINDS
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENT,
)
from notification.domain.value_objects.template_status import PENDING, REJECTED

logger = logging.getLogger("notification.dispatcher")

TEMPLATE_REFRESH_EVERY = timedelta(minutes=10)
BALANCE_CHECK_EVERY = timedelta(hours=24)
PENDING_TEMPLATE_DEFER = timedelta(minutes=10)
DAILY_CAP_DEFER = timedelta(hours=1)
POLL_SOON, POLL_LATER, POLL_SOON_WINDOW = timedelta(seconds=5), timedelta(seconds=60), timedelta(minutes=1)
ALIMTALK = "alimtalk"


@dataclass
class PeriodicState:
    """템플릿 상태·잔액을 마지막으로 본 시각. 루프는 run_once 마다 새 Dispatcher 를 만들므로 프로세스에 하나를 두고 넘긴다."""

    templates_refreshed_at: datetime | None = None
    balance_checked_at: datetime | None = None


@dataclass
class DispatchReport:
    recovered: int = 0
    claimed: int = 0
    sent: int = 0        # 업체가 접수한 줄
    deferred: int = 0    # scheduled 로 되돌린 줄(검수 중·야간·상한·일시 오류 재시도)
    canceled: int = 0
    failed: int = 0
    polled: int = 0      # 상태를 물은 accepted 줄


class Dispatcher:
    def __init__(
        self, *, queue: NotificationQueueRepository, channels: ChannelRepository, settings: SettingsRepository,
        templates: TemplateRepository, messages: MessageRepository, gateway: MessageGatewayPort,
        shops: ShopProfilePort, directory: CustomerDirectoryPort, ledger: VisitLedgerPort,
        commit: Callable[[], Awaitable[None]], rollback: Callable[[], Awaitable[None]],
        now: Callable[[], datetime], daily_cap: int, balance_warn_krw: int, claim_limit: int = 50,
        periodic: PeriodicState | None = None,
    ) -> None:
        self._queue = queue
        self._channels = channels
        self._settings = settings
        self._templates = templates
        self._messages = messages
        self._gateway = gateway
        self._shops = shops
        self._directory = directory
        self._ledger = ledger
        self._commit = commit
        self._rollback = rollback
        self._now = now
        self._daily_cap = daily_cap
        self._balance_warn_krw = balance_warn_krw
        self._claim_limit = claim_limit
        self._periodic = periodic if periodic is not None else PeriodicState()

    async def run_once(self) -> DispatchReport:
        report = DispatchReport()
        now = self._now()
        report.recovered = await self._queue.recover_stuck(now - STUCK_AFTER)
        await self._commit()
        claimed = await self._queue.claim_due(now, self._claim_limit)
        await self._commit()      # 여기서 잠금이 풀린다 — 업체는 이 뒤에 부른다(N14)
        report.claimed = len(claimed)
        for m in claimed:
            try:
                updated = await self._process(m, now)
            except Exception as exc:   # 한 줄의 문제가 다음 줄을 막지 않는다
                logger.warning("알림 %s(매장 %s, %s) 처리 실패 %s — 일시 오류로 적습니다.",
                               m.id, m.shop_id, m.kind, type(exc).__name__)
                updated = self._retry(m, now, type(exc).__name__[:20])
            updated = await self._save(m, updated)
            logger.info("알림 %s(매장 %s, %s) → %s", m.id, m.shop_id, m.kind, _outcome(updated))
            self._count(report, updated)
        for m in await self._queue.list_accepted(now):
            try:
                state = await self._gateway.delivery_state(m.provider_message_id)
            except GatewayError:
                updated = self._still_pending(m, now, POLL_LATER)
            else:
                updated = self._polled(m, state, now)
            await self._messages.save(system_context(m.shop_id), updated)
            await self._commit()
            logger.info("알림 %s(매장 %s, %s) 상태 → %s", m.id, m.shop_id, m.kind, _outcome(updated))
            report.polled += 1
            if updated.status == FAILED:
                report.failed += 1
        refreshed, checked = self._periodic.templates_refreshed_at, self._periodic.balance_checked_at
        if refreshed is None or now - refreshed >= TEMPLATE_REFRESH_EVERY:
            await self.refresh_templates()
        if checked is None or now - checked >= BALANCE_CHECK_EVERY:
            self._periodic.balance_checked_at = now
            await self.check_balance()
        return report

    async def _save(self, before: NotificationMessage, updated: NotificationMessage) -> NotificationMessage:
        """결과를 적고 커밋한다. 저장이 던지면(업체 값이 칸에 안 맞는 등) 롤백하고 그 줄만 영구 실패로 적는다 — 한 줄이
        세션을 깨뜨려 같은 배치의 뒤 줄을 막고 5분마다 되살아나 업체를 다시 부르지 않게(독이 든 줄)."""
        try:
            await self._messages.save(system_context(before.shop_id), updated)
            await self._commit()
            return updated
        except Exception as exc:
            await self._rollback()
            logger.warning("알림 %s(매장 %s, %s) 결과 저장 실패 %s — 영구 실패로 적습니다.",
                           before.id, before.shop_id, before.kind, type(exc).__name__)
            failed = replace(before, status=FAILED, attempts=before.attempts + 1, error_kind="permanent",
                             error_code="SAVE_ERROR", canceled_reason=None)
            await self._messages.save(system_context(before.shop_id), failed)
            await self._commit()
            return failed

    @staticmethod
    def _count(report: DispatchReport, updated: NotificationMessage) -> None:
        if updated.status == ACCEPTED:
            report.sent += 1
        elif updated.status == SCHEDULED:
            report.deferred += 1
        elif updated.status == CANCELED:
            report.canceled += 1
        elif updated.status == FAILED:
            report.failed += 1

    # --- 집은 줄 하나 ---------------------------------------------------------------------------------------------

    async def _process(self, m: NotificationMessage, now: datetime) -> NotificationMessage:
        """검사(설계 5.3 순서)를 다 지나면 보낸다. 걸리면 취소하거나 미룬 줄을 돌려준다."""
        profile = await self._shops.public_profile(m.shop_id)
        if profile is None or not profile.open:
            return self._cancel(m, "shop_closed")
        ctx, tz = system_context(m.shop_id, profile.timezone), profile.timezone
        channel = await self._channels.get(ctx)
        if channel is None or not channel.is_linked:
            return self._cancel(m, "channel_unlinked")
        settings = await self._settings.get(ctx)
        if settings is None or (not settings.enabled_for(m.kind) and m.requested_by_member_id is None):
            return self._cancel(m, "setting_off")   # 매장이 직접 누른 재발송은 설정과 무관하게 간다
        template = await self._templates.get(ctx, m.kind)
        if template is None or template.status == REJECTED:
            return self._cancel(m, "template_rejected")
        if template.status == PENDING:
            return replace(m, status=SCHEDULED, scheduled_at=now + PENDING_TEMPLATE_DEFER)   # 재등록 중이다
        contact = await self._directory.contact(ctx, m.customer_id)
        if contact is None:
            return self._cancel(m, "anonymized")
        if not is_mobile_number(contact.phone):
            return self._cancel(m, "bad_phone")
        if m.kind in SCHEDULED_KINDS:
            send_at = deferred_for_daytime(now, tz)
            if m.kind == REMINDER and is_too_late(send_at, datetime.fromisoformat(m.variables["starts_at"])):
                return self._cancel(m, "too_late")
            if send_at > now:
                return replace(m, status=SCHEDULED, scheduled_at=send_at)
        if m.kind == NEXT_VISIT:
            if not contact.marketing_consent:
                return self._cancel(m, "no_consent")
            pets = (await self._directory.briefs(ctx, [], message_pet_ids(m))).pets
            if any(p.passed_away for p in pets.values()):
                return self._cancel(m, "passed_away")
            if await self._ledger.customer_has_upcoming(ctx, m.customer_id):
                return self._cancel(m, "has_upcoming")
            last = await self._messages.last_delivered_at(ctx, m.customer_id, NEXT_VISIT)
            if last is not None and last > now - timedelta(days=settings.next_visit_cooldown_days):
                return self._cancel(m, "cooldown")
        sent_today = await self._messages.count_sent_since(ctx, _day_start(now, tz))
        if sent_today >= self._daily_cap:
            logger.warning("매장 %s 의 오늘 발송 %s건이 하루 상한 %s에 닿아 1시간 미룹니다.",
                           m.shop_id, sent_today, self._daily_cap)
            return replace(m, status=SCHEDULED, scheduled_at=now + DAILY_CAP_DEFER)

        target = await message_target(ctx, self._directory, m, contact)
        variables = message_variables(m.kind, shop_name=profile.name, target=target, tz=tz, variables=m.variables)
        rendered = render(m.kind, variables)
        fallback = None
        if channel.can_fallback:
            fallback = FallbackText(channel.sender_number, rendered.sms_text, sms_channel(rendered.sms_text))
        outgoing = OutgoingMessage(
            to=contact.phone, provider_channel_id=channel.provider_channel_id,
            provider_template_id=template.provider_template_id, variables=variables,
            button_url=rendered.button_url, fallback=fallback,
        )
        try:
            accepted = await self._gateway.send(outgoing)
        except GatewayTransientError as exc:
            return self._retry(m, now, exc.code)
        except GatewayPermanentError as exc:
            return replace(m, status=FAILED, attempts=m.attempts + 1, error_kind="permanent", error_code=exc.code)
        return replace(m, status=ACCEPTED, attempts=m.attempts + 1, provider_message_id=accepted.provider_message_id,
                       next_attempt_at=now + POLL_SOON, error_code=None, error_kind=None)

    @staticmethod
    def _cancel(m: NotificationMessage, reason: str) -> NotificationMessage:
        return replace(m, status=CANCELED, canceled_reason=reason)

    @staticmethod
    def _retry(m: NotificationMessage, now: datetime, code: str) -> NotificationMessage:
        """일시 오류 — attempts 를 올리기 전 값으로 다음 시각을 정한다(0·1·2 → 1·5·30분). 네 번째 실패에서 멈춘다."""
        at = retry_at(m.attempts, now)
        if at is None:
            return replace(m, status=FAILED, attempts=m.attempts + 1, error_kind="transient", error_code=code)
        return replace(m, status=SCHEDULED, scheduled_at=at, attempts=m.attempts + 1, error_kind="transient",
                       error_code=code)

    # --- 접수 뒤 상태 조회 -----------------------------------------------------------------------------------------

    def _polled(self, m: NotificationMessage, state: DeliveryState, now: datetime) -> NotificationMessage:
        if state.status == "sent":
            status = SENT if state.channel_used == ALIMTALK else FALLBACK_SENT
            return replace(m, status=status, channel_used=state.channel_used, sent_at=now)
        if state.status == "failed":
            if state.error_kind == "transient":
                # 접수 뒤 일시 실패(단말 꺼짐·전송 시간 초과)도 같은 1·5·30분 규칙으로 다시 보낸다(설계 5.3-5).
                # 접수가 곧 시도라 attempts 는 올리지 않는다 — _retry 가 올리는 만큼 미리 뺀다.
                return self._retry(replace(m, attempts=m.attempts - 1), now, state.error_code or "")
            return replace(m, status=FAILED, error_code=state.error_code, error_kind=state.error_kind)
        return self._still_pending(m, now)

    @staticmethod
    def _still_pending(m: NotificationMessage, now: datetime, wait: timedelta | None = None) -> NotificationMessage:
        """처음 1분은 5초마다, 그 뒤 1분마다(조회가 실패했으면 1분). 24시간이 지나면 일시 실패."""
        if now - m.scheduled_at > ACCEPTED_TIMEOUT:
            return replace(m, status=FAILED, error_kind="transient", error_code="TIMEOUT")
        if wait is None:
            wait = POLL_SOON if now - m.scheduled_at < POLL_SOON_WINDOW else POLL_LATER
        return replace(m, next_attempt_at=now + wait)

    # --- 주기 작업 -------------------------------------------------------------------------------------------------

    async def refresh_templates(self) -> int:
        """검수 중인 템플릿의 업체 상태를 적고, 연동한 매장의 빠진 종류를 다시 등록한다(설계 9.5). 바꾼 수."""
        now = self._now()
        profiles: dict[int, ShopProfile | None] = {}
        changed = 0
        for t in await self._queue.list_pending_templates():
            profile = await self._profile(t.shop_id, profiles)
            if profile is None:
                continue
            try:
                state = await self._gateway.template_state(t.review_provider_template_id)
            except GatewayError as exc:
                logger.warning("매장 %s 의 %s 템플릿 상태 조회 실패 (%s)", t.shop_id, t.kind, exc.code)
                continue
            recorded = await record_template_state(self._templates, system_context(t.shop_id, profile.timezone), t,
                                                   state, now)
            if recorded is None:
                continue
            await self._commit()
            changed += 1
            if recorded == REJECTED_NEW_VERSION:
                logger.warning("매장 %s 의 %s 템플릿 새 판(%s)이 반려됐습니다 — 옛 판으로 계속 보냅니다.",
                               t.shop_id, t.kind, t.pending_text_version)
        channels = await self._queue.list_linked_channels()
        existing = await self._queue.list_templates_for_shops([c.shop_id for c in channels])
        for c in channels:
            profile = await self._profile(c.shop_id, profiles)
            if profile is None:
                continue
            ctx = system_context(c.shop_id, profile.timezone)
            settings = await self._settings.get(ctx)
            wanted = list(DEFAULT_KINDS)
            if settings is not None and settings.next_visit_enabled:
                wanted.append(NEXT_VISIT)
            have = {t.kind for t in existing[c.shop_id]}
            for kind in wanted:
                if kind in have:
                    continue
                try:
                    provider_id = await self._gateway.register_template(c.provider_channel_id, TEMPLATES[kind],
                                                                        TEXT_VERSION)
                except GatewayError as exc:
                    logger.warning("매장 %s 의 %s 템플릿 등록 실패 (%s) — 다음 주기에 다시 합니다.", c.shop_id, kind, exc.code)
                    continue
                await self._templates.upsert(ctx, kind, TEXT_VERSION, provider_id, now)
                await self._commit()
                changed += 1
        self._periodic.templates_refreshed_at = now
        return changed

    async def _profile(self, shop_id: int, cache: dict[int, ShopProfile | None]) -> ShopProfile | None:
        if shop_id not in cache:
            cache[shop_id] = await self._shops.public_profile(shop_id)
        return cache[shop_id]

    async def check_balance(self) -> int:
        """잔액(원). 기준 아래면 WARNING — 금액만 적는다."""
        balance = await self._gateway.balance()
        if balance < self._balance_warn_krw:
            logger.warning("발송 잔액 %s원이 기준 %s원 아래입니다. 충전이 필요합니다.", balance, self._balance_warn_krw)
        return balance


def _outcome(m: NotificationMessage) -> str:
    """로그용 — 상태와 취소 이유·오류 코드만."""
    detail = m.canceled_reason or m.error_code
    return f"{m.status}({detail})" if detail else m.status


def _day_start(now: datetime, tz: str) -> datetime:
    """매장 시간대의 오늘 00:00 을 UTC 로."""
    return datetime.combine(now.astimezone(ZoneInfo(tz)).date(), time(0), tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
