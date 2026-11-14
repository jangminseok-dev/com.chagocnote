"""notification 구독자·디스패처·인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남긴다.

스텁은 포트 ABC 를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간(TypeError) 잡힌다.
`apps/notification/tests/test_fakes_are_ports.py`가 이를 확인한다. 매장 범위 메서드는 ctx.shop_id 로 거른다.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal

from hub.app.dtos.customer_contact import CustomerContact
from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
from hub.app.dtos.shop_profile import ShopProfile
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from hub.app.ports.shop_profile_port import ShopProfilePort
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.ports.output.channel_repository import ChannelRepository
from notification.app.ports.output.message_gateway_port import DeliveryState, TemplateState
from notification.app.ports.output.message_repository import MessageRepository
from notification.app.ports.output.notification_queue_repository import NotificationQueueRepository
from notification.app.ports.output.onboarding_limiter_port import OnboardingLimiterPort
from notification.app.ports.output.settings_repository import SettingsRepository
from notification.app.ports.output.template_repository import TemplateRepository
from notification.domain.entities.notification_channel import NotificationChannel
from notification.domain.entities.notification_message import NotificationMessage
from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS, NotificationSettings
from notification.domain.entities.notification_template import NotificationTemplate
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED
from notification.domain.value_objects.message_kind import KINDS
from notification.domain.services.schedule_rules import MAX_ATTEMPTS, STUCK_CODE
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    DELIVERED_STATUSES,
    PENDING_STATUSES,
    SCHEDULED,
    SENDING,
)
from notification.domain.value_objects.template_status import APPROVED, PENDING


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeChannels(ChannelRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, NotificationChannel] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id)

    async def save(self, ctx, channel):
        if channel.shop_id != ctx.shop_id:
            raise ValueError("채널의 매장이 컨텍스트의 매장과 다릅니다.")
        self.rows[ctx.shop_id] = channel
        self.journal.append(("save_channel", ctx.shop_id, channel.status))
        return channel


class FakeSettings(SettingsRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[int, NotificationSettings] = {}

    async def get(self, ctx):
        return self.rows.get(ctx.shop_id)

    async def ensure(self, ctx):
        self.journal.append(("ensure_settings", ctx.shop_id))
        return self.rows.setdefault(ctx.shop_id, DEFAULT_NOTIFICATION_SETTINGS)

    async def update(self, ctx, settings):
        self.rows[ctx.shop_id] = settings
        self.journal.append(("update_settings", ctx.shop_id))
        return settings


class FakeTemplates(TemplateRepository):
    def __init__(self, journal: Journal | None = None) -> None:
        self.journal = journal if journal is not None else Journal()
        self.rows: dict[tuple[int, str], NotificationTemplate] = {}

    async def list_for_shop(self, ctx):
        return sorted((t for t in self.rows.values() if t.shop_id == ctx.shop_id), key=lambda t: KINDS.index(t.kind))

    async def get(self, ctx, kind):
        return self.rows.get((ctx.shop_id, kind))

    async def upsert(self, ctx, kind, text_version, provider_template_id, requested_at):
        current = self.rows.get((ctx.shop_id, kind))
        if current is not None and current.status == APPROVED:
            template = replace(current, pending_text_version=text_version,
                               pending_provider_template_id=provider_template_id)
        else:
            template = NotificationTemplate(
                id=current.id if current is not None else len(self.rows) + 1, shop_id=ctx.shop_id, kind=kind,
                text_version=text_version, provider_template_id=provider_template_id, status=PENDING,
                rejected_reason=None, requested_at=requested_at, decided_at=None,
            )
        self.rows[(ctx.shop_id, kind)] = template
        self.journal.append(("upsert_template", ctx.shop_id, kind))
        return template

    async def set_status(self, ctx, kind, status, rejected_reason, decided_at):
        current = self.rows.get((ctx.shop_id, kind))
        if current is not None:
            self.rows[(ctx.shop_id, kind)] = replace(
                current, status=status, rejected_reason=rejected_reason, decided_at=decided_at)
        self.journal.append(("set_template_status", ctx.shop_id, kind, status))

    async def decide_pending(self, ctx, kind, approved, rejected_reason, decided_at):
        current = self.rows.get((ctx.shop_id, kind))
        if current is None or current.pending_provider_template_id is None:
            return
        cleared = replace(current, pending_text_version=None, pending_provider_template_id=None,
                          rejected_reason=rejected_reason)
        if approved:
            cleared = replace(cleared, text_version=current.pending_text_version,
                              provider_template_id=current.pending_provider_template_id, decided_at=decided_at,
                              rejected_reason=None)
        self.rows[(ctx.shop_id, kind)] = cleared
        self.journal.append(("decide_pending_template", ctx.shop_id, kind, approved))

    async def delete_all(self, ctx):
        mine = [key for key in self.rows if key[0] == ctx.shop_id]
        for key in mine:
            del self.rows[key]
        self.journal.append(("delete_templates", ctx.shop_id))
        return len(mine)


class FakeMessages(MessageRepository, NotificationQueueRepository):
    """notification_messages 스텁 — pg 구현처럼 두 포트를 한 객체가 낸다.

    같은 방문·종류의 대기 줄이 있으면 MessageAlreadyPendingError(부분 유일 색인). created_at 은 scheduled_at 으로 둔다
    (즉시 보낼 줄은 둘이 같다). 전 매장 조회는 함께 넘긴 templates·channels 스텁을 본다. recover_stuck 은 claim_due 로
    집은 줄만 되돌린다(집은 시각을 claimed_at 에 적는다).
    """

    def __init__(
        self, journal: Journal | None = None, templates: FakeTemplates | None = None,
        channels: FakeChannels | None = None,
    ) -> None:
        self.journal = journal if journal is not None else Journal()
        self.templates = templates if templates is not None else FakeTemplates(self.journal)
        self.channels = channels if channels is not None else FakeChannels(self.journal)
        self.rows: dict[int, NotificationMessage] = {}
        self.claimed_at: dict[int, datetime] = {}

    def _mine(self, ctx, **fields) -> list[NotificationMessage]:
        return [m for m in self.rows.values()
                if m.shop_id == ctx.shop_id and all(getattr(m, k) == v for k, v in fields.items())]

    def _put(self, message: NotificationMessage) -> None:
        self.rows[message.id] = message

    # --- 매장 범위 ----------------------------------------------------------------------------------------------

    async def create(self, ctx, new):
        if new.shop_id != ctx.shop_id:
            raise ValueError("메시지의 매장이 컨텍스트의 매장과 다릅니다.")
        # 부분 유일 색인은 (visit_id, kind) 라 매장을 가리지 않는다 — 방문 ID 는 전 매장에서 유일하다.
        if any(m.status in PENDING_STATUSES and (m.visit_id, m.kind) == (new.visit_id, new.kind)
               for m in self.rows.values()):
            raise MessageAlreadyPendingError("같은 방문·종류의 알림이 이미 대기 중입니다.")
        message = NotificationMessage(
            id=len(self.rows) + 1, shop_id=ctx.shop_id, visit_id=new.visit_id, customer_id=new.customer_id,
            pet_id=new.pet_id, kind=new.kind, scheduled_at=new.scheduled_at, status=SCHEDULED, attempts=0,
            next_attempt_at=None, channel_used=None, provider_message_id=None, error_code=None, error_kind=None,
            variables=dict(new.variables), requested_by_member_id=new.requested_by_member_id,
            created_at=new.scheduled_at, sent_at=None, canceled_reason=None,
        )
        self._put(message)
        self.journal.append(("create_message", new.visit_id, new.kind))
        return message

    async def cancel_pending(self, ctx, reason, visit_id=None, kinds=None, except_ids=()):
        kinds = None if kinds is None else set(kinds)
        kept = set(except_ids)
        targets = [
            m for m in self._mine(ctx)
            if m.status in PENDING_STATUSES and (visit_id is None or m.visit_id == visit_id)
            and (kinds is None or m.kind in kinds) and m.id not in kept
        ]
        for m in targets:
            self._put(replace(m, status=CANCELED, canceled_reason=reason))
        self.journal.append(("cancel_pending", visit_id, reason))
        return len(targets)

    async def list_scheduled_for_group(self, ctx, customer_id, starts_at_iso, kinds):
        kinds = set(kinds)
        return sorted((m for m in self._mine(ctx, customer_id=customer_id, status=SCHEDULED)
                       if m.kind in kinds and m.variables.get("starts_at") == starts_at_iso), key=lambda m: m.id)

    async def rewrite_scheduled(self, ctx, message_id, variables, visit_id, pet_id):
        current = await self.get(ctx, message_id)
        if current is None or current.status != SCHEDULED:
            return False
        if any(m.id != message_id and m.status in PENDING_STATUSES and (m.visit_id, m.kind) == (visit_id, current.kind)
               for m in self.rows.values()):
            raise MessageAlreadyPendingError("옮길 방문에 같은 종류의 알림이 이미 대기 중입니다.")
        self._put(replace(current, variables=dict(variables), visit_id=visit_id, pet_id=pet_id))
        self.journal.append(("rewrite_scheduled", message_id))
        return True

    async def cancel_scheduled(self, ctx, message_id, reason):
        current = await self.get(ctx, message_id)
        if current is None or current.status != SCHEDULED:
            return False
        self._put(replace(current, status=CANCELED, canceled_reason=reason))
        self.journal.append(("cancel_scheduled", message_id, reason))
        return True

    async def list_pending(self, ctx, kind):
        return sorted(self._mine(ctx, kind=kind, status=SCHEDULED), key=lambda m: (m.scheduled_at, m.id))

    async def has_delivered(self, ctx, visit_id, kind, url=None):
        return any(
            m.status in DELIVERED_STATUSES and (url is None or m.variables.get("url") == url)
            for m in self._mine(ctx, visit_id=visit_id, kind=kind)
        )

    async def has_pending_for_group(self, ctx, customer_id, kind, starts_at_iso):
        return any(m.status in PENDING_STATUSES and m.variables.get("starts_at") == starts_at_iso
                   for m in self._mine(ctx, customer_id=customer_id, kind=kind))

    async def last_delivered_at(self, ctx, customer_id, kind):
        sent = [m.sent_at for m in self._mine(ctx, customer_id=customer_id, kind=kind)
                if m.status in DELIVERED_STATUSES and m.sent_at is not None]
        return max(sent) if sent else None

    async def count_sent_since(self, ctx, since):
        return sum(1 for m in self._mine(ctx) if m.provider_message_id is not None and m.created_at >= since)

    async def list_for_visit(self, ctx, visit_id):
        return sorted(self._mine(ctx, visit_id=visit_id), key=lambda m: (m.created_at, m.id), reverse=True)

    async def get(self, ctx, message_id):
        current = self.rows.get(message_id)
        return current if current is not None and current.shop_id == ctx.shop_id else None

    async def save(self, ctx, message):
        current = await self.get(ctx, message.id)
        if current is None:
            return
        self._put(replace(
            current, status=message.status, attempts=message.attempts, next_attempt_at=message.next_attempt_at,
            scheduled_at=message.scheduled_at, channel_used=message.channel_used,
            provider_message_id=message.provider_message_id, error_code=message.error_code,
            error_kind=message.error_kind, sent_at=message.sent_at, canceled_reason=message.canceled_reason,
        ))
        self.journal.append(("save_message", message.id, message.status))

    # --- 전 매장(디스패처) ---------------------------------------------------------------------------------------

    async def claim_due(self, now, limit):
        due = sorted((m for m in self.rows.values() if m.status == SCHEDULED and m.scheduled_at <= now),
                     key=lambda m: (m.scheduled_at, m.id))[:limit]
        claimed = [replace(m, status=SENDING) for m in due]
        for m in claimed:
            self._put(m)
            self.claimed_at[m.id] = now
        self.journal.append(("claim_due", [m.id for m in claimed]))
        return claimed

    async def recover_stuck(self, before):
        stuck = [m for m in self.rows.values()
                 if m.status == SENDING and m.id in self.claimed_at and self.claimed_at[m.id] < before]
        for m in stuck:
            if m.attempts >= MAX_ATTEMPTS:
                self._put(replace(m, status=FAILED, attempts=m.attempts + 1, error_kind="transient",
                                  error_code=STUCK_CODE))
            else:
                self._put(replace(m, status=SCHEDULED, attempts=m.attempts + 1))
            del self.claimed_at[m.id]
        self.journal.append(("recover_stuck", [m.id for m in stuck]))
        return len(stuck)

    async def list_accepted(self, now):
        return sorted((m for m in self.rows.values()
                       if m.status == ACCEPTED and m.next_attempt_at is not None and m.next_attempt_at <= now),
                      key=lambda m: (m.next_attempt_at, m.id))

    async def list_pending_templates(self):
        return sorted((t for t in self.templates.rows.values() if t.under_review), key=lambda t: t.id)

    async def list_linked_channels(self):
        return sorted((c for c in self.channels.rows.values() if c.status == LINKED), key=lambda c: c.shop_id)

    async def list_templates_for_shops(self, shop_ids):
        return {
            shop_id: sorted((t for t in self.templates.rows.values() if t.shop_id == shop_id),
                            key=lambda t: KINDS.index(t.kind))
            for shop_id in shop_ids
        }


# --- 디스패처가 읽는 허브 포트 스텁 --------------------------------------------------------------------------------

class FakeShopProfile(ShopProfilePort):
    """ShopProfilePort 스텁 — 매장 ID → ShopProfile 사전. 없는 매장은 None."""

    def __init__(self, shops: dict[int, ShopProfile] | None = None) -> None:
        self.shops = shops if shops is not None else {}

    async def public_profile(self, shop_id):
        return self.shops.get(shop_id)


class FakeDirectory(CustomerDirectoryPort):
    """CustomerDirectoryPort 스텁 — 디스패처가 쓰는 contact·briefs 만 값을 낸다. 매장이 다르면 없는 것으로 본다.

    contacts 는 {고객 ID: CustomerContact}(익명화를 흉내 내려면 뺀다), pets 는 {반려동물 ID: PetBrief}.
    """

    def __init__(self, shop_id: int = 1) -> None:
        self.shop_id = shop_id
        self.contacts: dict[int, CustomerContact] = {}
        self.pets: dict[int, PetBrief] = {}

    def family(self, customer_id=1, pet_id=101, name="김민지", phone="01012345678", pet_name="콩이",
               marketing_consent=True) -> None:
        self.contacts[customer_id] = CustomerContact(customer_id=customer_id, name=name, phone=phone,
                                                     marketing_consent=marketing_consent)
        self.pets[pet_id] = PetBrief(pet_id=pet_id, customer_id=customer_id, name=pet_name, species="dog",
                                     breed="말티즈", weight_kg=Decimal("3.2"), passed_away=False)

    async def lock_family(self, ctx, customer_id, pet_ids):
        return None

    async def care_facts(self, ctx, customer_ids, pet_ids, today):
        raise NotImplementedError   # notification 은 쓰지 않는다

    async def first_pets(self, ctx, customer_ids):
        raise NotImplementedError   # notification 은 쓰지 않는다

    async def briefs(self, ctx, customer_ids, pet_ids):
        if ctx.shop_id != self.shop_id:
            return FamilyBriefs(customers={}, pets={})
        customers = {c: CustomerBrief(customer_id=c, name=self.contacts[c].name, phone_masked=None)
                     for c in customer_ids if c in self.contacts}
        return FamilyBriefs(customers=customers, pets={p: self.pets[p] for p in pet_ids if p in self.pets})

    async def set_last_visit(self, ctx, customer_id, at):
        return None

    async def set_pet_weight(self, ctx, pet_id, weight_kg):
        return None

    async def find_draft_candidates(self, ctx, words):
        return []

    async def contact(self, ctx, customer_id):
        return self.contacts.get(customer_id) if ctx.shop_id == self.shop_id else None


class FakeLedger(VisitLedgerPort):
    """VisitLedgerPort 스텁 — 디스패처는 customer_has_upcoming 만 쓴다. upcoming 은 앞으로의 예약이 있는 고객 ID."""

    def __init__(self) -> None:
        self.upcoming: set[int] = set()

    async def pet_has_visits(self, ctx, pet_id):
        return False

    async def pet_has_upcoming(self, ctx, pet_id):
        return False

    async def customer_has_upcoming(self, ctx, customer_id):
        return customer_id in self.upcoming

    async def no_show_count(self, ctx, customer_id):
        return 0

    async def upcoming_for_customer(self, ctx, customer_id, limit):
        return []

    async def clear_customer_memos(self, ctx, customer_id):
        return None

    async def latest_covers(self, ctx, pet_ids):
        return {}


class SpyGateway(FakeGateway):
    """FakeGateway 에 journal 과 '던질 예외'·'정해 둔 상태'를 더한 것. journal 에 번호는 남기지 않는다."""

    def __init__(self, journal: Journal | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.journal = journal if journal is not None else Journal()
        self.send_error: Exception | None = None            # 있으면 send 가 던진다
        self.state_error: Exception | None = None           # 있으면 delivery_state 가 던진다
        self.register_error: Exception | None = None        # 있으면 register_template 이 던진다
        self.states: dict[str, DeliveryState] = {}          # 업체 메시지 ID → 정해 둔 상태(없으면 번호 규칙)
        self.template_states: dict[str, TemplateState] = {}  # 업체 템플릿 ID → 정해 둔 심사 상태(없으면 가짜 규칙)
        self.template_error: Exception | None = None        # 있으면 template_state 가 던진다

    async def register_template(self, provider_channel_id, template, text_version):
        self.journal.append(("register_template", provider_channel_id, template.kind))
        if self.register_error is not None:
            raise self.register_error
        return await super().register_template(provider_channel_id, template, text_version)

    async def template_state(self, provider_template_id):
        self.journal.append(("template_state", provider_template_id))
        if self.template_error is not None:
            raise self.template_error
        if provider_template_id in self.template_states:
            return self.template_states[provider_template_id]
        return await super().template_state(provider_template_id)

    async def send(self, message):
        self.journal.append(("send", message.provider_template_id))
        if self.send_error is not None:
            raise self.send_error
        return await super().send(message)

    async def delivery_state(self, provider_message_id):
        self.journal.append(("delivery_state", provider_message_id))
        if self.state_error is not None:
            raise self.state_error
        if provider_message_id in self.states:
            return self.states[provider_message_id]
        return await super().delivery_state(provider_message_id)

    async def balance(self):
        self.journal.append(("balance",))
        return await super().balance()


class FakeOnboardingLimiter(OnboardingLimiterPort):
    """온보딩 횟수 제한 스텁 — allowed 를 False 로 두면 한도가 찬 것으로 친다. 센 (매장, 동작)이 calls 에 남는다."""

    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls: list[tuple[int, str]] = []

    async def allow(self, shop_id, action):
        self.calls.append((shop_id, action))
        return self.allowed
