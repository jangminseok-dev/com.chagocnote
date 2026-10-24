"""notification 저장소 넷을 실제 DB 로 본다 — 매장 범위, DB CHECK, 같은 방문·종류의 대기 줄 하나, 큐의 SKIP LOCKED."""
import asyncio
from dataclasses import replace
from datetime import datetime, time, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.pg.channel_pg_repository import ChannelPgRepository
from notification.adapter.outbound.pg.message_pg_repository import MessagePgRepository
from notification.adapter.outbound.pg.settings_pg_repository import SettingsPgRepository
from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED, UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.message_status import (
    ACCEPTED,
    CANCELED,
    FAILED,
    FALLBACK_SENT,
    SCHEDULED,
    SENDING,
    SENT,
)
from notification.domain.value_objects.template_status import APPROVED, PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, new_message, settings

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(10, 14, 11)
HOUR, MINUTE = timedelta(hours=1), timedelta(minutes=1)
BLOCKED = 0.5


# --- 채널 -------------------------------------------------------------------------------------------------------

async def test_채널은_매장당_한_줄이고_다시_저장하면_덮는다(db_session):
    repo = ChannelPgRepository(db_session)
    assert await repo.get(A) is None
    saved = await repo.save(A, channel())
    assert saved == channel() and await repo.get(A) == saved
    again = await repo.save(A, channel(status=UNLINKED, unlinked_at=NOW, sender_number="01012345678"))
    assert (again.status, again.unlinked_at, again.sender_number) == (UNLINKED, NOW, "01012345678")
    assert await repo.get(A) == again
    assert await repo.get(B) is None


async def test_채널의_매장이_컨텍스트와_다르면_ValueError_다(db_session):
    with pytest.raises(ValueError):
        await ChannelPgRepository(db_session).save(A, channel(shop_id=2))


async def test_발신번호_인증_없이_문자_대체를_켜면_DB_가_거절한다(db_session):
    repo = ChannelPgRepository(db_session)
    verified = await repo.save(A, channel(sender_number="01012345678", sender_number_verified_at=NOW,
                                          sms_fallback_enabled=True))
    assert verified.can_fallback is True
    with pytest.raises(IntegrityError):
        await repo.save(B, channel(shop_id=2, sms_fallback_enabled=True))


# --- 설정 -------------------------------------------------------------------------------------------------------

async def test_설정은_연동_전엔_없고_ensure_가_기본값으로_만든다(db_session):
    repo = SettingsPgRepository(db_session)
    assert await repo.get(A) is None
    assert await repo.ensure(A) == DEFAULT_NOTIFICATION_SETTINGS
    assert await repo.ensure(A) == DEFAULT_NOTIFICATION_SETTINGS
    changed = settings(reminder_time=time(9, 0), next_visit_enabled=True, next_visit_after_weeks=6,
                       next_visit_cooldown_days=45, confirm_enabled=False)
    assert await repo.update(A, changed) == changed
    assert await repo.get(A) == changed
    assert await repo.ensure(A) == changed   # 있는 행은 기본값으로 덮지 않는다
    assert await repo.get(B) is None
    assert await repo.ensure(B) == DEFAULT_NOTIFICATION_SETTINGS
    assert await repo.get(A) == changed


async def test_리마인드_시각_22시는_DB_가_거절한다(db_session):
    repo = SettingsPgRepository(db_session)
    await repo.ensure(A)
    with pytest.raises(IntegrityError):
        await repo.update(A, settings(reminder_time=time(22, 0)))


# --- 템플릿 -----------------------------------------------------------------------------------------------------

async def test_템플릿_upsert_는_같은_종류를_한_줄로_두고_pending_으로_되돌린다(db_session):
    repo = TemplatePgRepository(db_session)
    first = await repo.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    assert (first.shop_id, first.kind, first.text_version, first.provider_template_id) == (1, CONFIRM, 1, "KA01TP0001")
    assert (first.status, first.rejected_reason, first.requested_at, first.decided_at) == (PENDING, None, NOW, None)
    await repo.set_status(A, CONFIRM, REJECTED, "변수 이름이 맞지 않음", NOW + HOUR)
    rejected = await repo.get(A, CONFIRM)
    assert (rejected.status, rejected.rejected_reason, rejected.decided_at) == (REJECTED, "변수 이름이 맞지 않음", NOW + HOUR)
    again = await repo.upsert(A, CONFIRM, 2, "KA01TP0002", NOW + 2 * HOUR)
    assert again == replace(first, text_version=2, provider_template_id="KA01TP0002", requested_at=NOW + 2 * HOUR)
    assert await repo.list_for_shop(A) == [again]
    await repo.set_status(A, CONFIRM, APPROVED, None, NOW + 3 * HOUR)
    assert (await repo.get(A, CONFIRM)).status == APPROVED


async def test_템플릿_목록은_종류_순이고_매장을_거르며_delete_all_은_그_매장만_지운다(db_session):
    repo = TemplatePgRepository(db_session)
    for kind, provider_id in ((NEXT_VISIT, "KA01TP0006"), (CONFIRM, "KA01TP0001"), (REPORT, "KA01TP0003")):
        await repo.upsert(A, kind, 1, provider_id, NOW)
    theirs = await repo.upsert(B, CONFIRM, 1, "KA01TP0009", NOW)
    assert [t.kind for t in await repo.list_for_shop(A)] == [CONFIRM, REPORT, NEXT_VISIT]
    assert await repo.get(B, REPORT) is None
    assert await repo.get(A, REMINDER) is None
    await repo.set_status(B, REPORT, APPROVED, None, NOW)   # 없는 줄 — 아무것도 바꾸지 않는다
    assert await repo.delete_all(A) == 3
    assert await repo.list_for_shop(A) == []
    assert await repo.list_for_shop(B) == [theirs]
    assert await repo.delete_all(A) == 0


# --- 메시지 -----------------------------------------------------------------------------------------------------

async def test_메시지를_만들고_방문별로_최신순으로_읽는다(db_session):
    repo = MessagePgRepository(db_session)
    confirm = await repo.create(A, new_message(pet_id=101, variables={"url": "https://a/1"}, requested_by_member_id=11))
    assert (confirm.shop_id, confirm.visit_id, confirm.customer_id, confirm.pet_id, confirm.kind) == (1, 1, 1, 101, CONFIRM)
    assert (confirm.status, confirm.attempts, confirm.scheduled_at, confirm.variables) == (
        SCHEDULED, 0, NOW, {"url": "https://a/1"})
    assert (confirm.requested_by_member_id, confirm.sent_at, confirm.canceled_reason) == (11, None, None)
    assert confirm.created_at.tzinfo is not None
    reminder = await repo.create(A, new_message(kind=REMINDER, scheduled_at=NOW + HOUR))
    other = await repo.create(A, new_message(visit_id=2, kind=REMINDER))
    assert await repo.list_for_visit(A, 1) == [reminder, confirm]
    assert await repo.list_for_visit(A, 2) == [other]
    assert await repo.get(A, reminder.id) == reminder


async def test_같은_방문_같은_종류의_대기_줄은_하나이고_트랜잭션은_계속_쓸_수_있다(db_session):
    repo = MessagePgRepository(db_session)
    confirm = await repo.create(A, new_message())
    with pytest.raises(MessageAlreadyPendingError):
        await repo.create(A, new_message())
    reminder = await repo.create(A, new_message(kind=REMINDER))   # 같은 트랜잭션에서 다른 INSERT 가 된다
    assert [m.id for m in await repo.list_for_visit(A, 1)] == [reminder.id, confirm.id]


async def test_취소되거나_보낸_줄이_있으면_새_대기_줄을_만들_수_있다(db_session):
    repo = MessagePgRepository(db_session)
    await repo.create(A, new_message())
    assert await repo.cancel_pending(A, "rescheduled", visit_id=1, kinds=[CONFIRM]) == 1
    second = await repo.create(A, new_message())
    await repo.save(A, replace(second, status=SENT, sent_at=NOW, channel_used="alimtalk", provider_message_id="M2"))
    third = await repo.create(A, new_message())
    await repo.save(A, replace(third, status=SENDING))
    with pytest.raises(MessageAlreadyPendingError):   # sending 도 대기다
        await repo.create(A, new_message())
    assert [m.status for m in await repo.list_for_visit(A, 1)] == [SENDING, SENT, CANCELED]


async def test_대기_줄_취소의_세_범위_방문_종류_전체(db_session):
    repo = MessagePgRepository(db_session)
    v1_confirm = await repo.create(A, new_message(visit_id=1, kind=CONFIRM))
    v1_reminder = await repo.create(A, new_message(visit_id=1, kind=REMINDER))
    v2_confirm = await repo.create(A, new_message(visit_id=2, kind=CONFIRM))
    v2_reminder = await repo.create(A, new_message(visit_id=2, kind=REMINDER))
    v3_confirm = await repo.create(A, new_message(visit_id=3, kind=CONFIRM))
    theirs = await repo.create(B, new_message(shop_id=2, visit_id=9, kind=CONFIRM))   # 방문 ID 는 전 매장에서 유일하다
    assert await repo.cancel_pending(A, "no_show", visit_id=3) == 1
    assert await repo.cancel_pending(A, "rescheduled", visit_id=1, kinds=[REMINDER]) == 1
    assert await repo.cancel_pending(A, "visit_canceled", visit_id=2) == 2
    assert await repo.cancel_pending(A, "channel_unlinked") == 1   # 남은 대기 줄은 v1_confirm 뿐
    reasons = {m.id: (await repo.get(A, m.id)).canceled_reason
               for m in (v1_confirm, v1_reminder, v2_confirm, v2_reminder, v3_confirm)}
    assert reasons == {v1_confirm.id: "channel_unlinked", v1_reminder.id: "rescheduled",
                       v2_confirm.id: "visit_canceled", v2_reminder.id: "visit_canceled", v3_confirm.id: "no_show"}
    assert (await repo.get(B, theirs.id)).status == SCHEDULED


async def test_보낸_줄_판정은_보낸_상태만_세고_주소를_주면_같은_주소만_본다(db_session):
    repo = MessagePgRepository(db_session)
    assert await repo.has_delivered(A, 1, REPORT) is False
    report = await repo.create(A, new_message(kind=REPORT, variables={"url": "https://a/1"}))
    assert await repo.has_delivered(A, 1, REPORT) is False   # scheduled 는 보낸 게 아니다
    await repo.save(A, replace(report, status=SENT, sent_at=NOW, channel_used="alimtalk", provider_message_id="M1"))
    assert await repo.has_delivered(A, 1, REPORT) is True
    assert await repo.has_delivered(A, 1, REPORT, url="https://a/1") is True
    assert await repo.has_delivered(A, 1, REPORT, url="https://a/2") is False
    assert await repo.has_delivered(B, 1, REPORT) is False
    assert await repo.has_delivered(A, 1, CONFIRM) is False
    failed = await repo.create(A, new_message(kind=CONFIRM))
    await repo.save(A, replace(failed, status=FAILED, error_code="3000", error_kind="permanent"))
    assert await repo.has_delivered(A, 1, CONFIRM) is False
    fallback = await repo.create(A, new_message(visit_id=2, kind=CONFIRM))
    await repo.save(A, replace(fallback, status=FALLBACK_SENT, sent_at=NOW, channel_used="sms"))
    assert await repo.has_delivered(A, 2, CONFIRM) is True


async def test_묶음_대기_줄_판정은_같은_고객_종류_시작_시각의_대기_줄만_본다(db_session):
    repo = MessagePgRepository(db_session)
    starts = "2026-10-16T05:00:00+00:00"
    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is False
    confirm = await repo.create(A, new_message(customer_id=1, variables={"starts_at": starts, "pet_ids": "101,102"}))
    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is True
    assert await repo.has_pending_for_group(A, 1, CONFIRM, "2026-10-17T05:00:00+00:00") is False
    assert await repo.has_pending_for_group(A, 1, REMINDER, starts) is False
    assert await repo.has_pending_for_group(A, 2, CONFIRM, starts) is False
    assert await repo.has_pending_for_group(B, 1, CONFIRM, starts) is False
    await repo.save(A, replace(confirm, status=SENDING))
    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is True   # sending 도 대기다
    await repo.save(A, replace(confirm, status=CANCELED, canceled_reason="rescheduled"))
    assert await repo.has_pending_for_group(A, 1, CONFIRM, starts) is False


async def test_마지막으로_보낸_시각은_고객_종류별로_가장_최근이다(db_session):
    repo = MessagePgRepository(db_session)
    assert await repo.last_delivered_at(A, 1, NEXT_VISIT) is None
    older = await repo.create(A, new_message(visit_id=1, kind=NEXT_VISIT))
    await repo.save(A, replace(older, status=SENT, sent_at=NOW - timedelta(days=10)))
    newer = await repo.create(A, new_message(visit_id=2, kind=NEXT_VISIT))
    await repo.save(A, replace(newer, status=FALLBACK_SENT, sent_at=NOW - timedelta(days=3)))
    unsent = await repo.create(A, new_message(visit_id=3, kind=NEXT_VISIT))
    await repo.save(A, replace(unsent, status=FAILED, sent_at=None))
    assert await repo.last_delivered_at(A, 1, NEXT_VISIT) == NOW - timedelta(days=3)
    assert await repo.last_delivered_at(A, 1, CONFIRM) is None
    assert await repo.last_delivered_at(A, 2, NEXT_VISIT) is None
    assert await repo.last_delivered_at(B, 1, NEXT_VISIT) is None


async def test_하루_상한은_업체에_넘긴_줄만_만든_시각으로_센다(db_session):
    repo = MessagePgRepository(db_session)
    since = datetime.now(timezone.utc) - timedelta(days=1)
    assert await repo.count_sent_since(A, since) == 0
    rows = [await repo.create(A, new_message(visit_id=v)) for v in (1, 2, 3)]
    await repo.save(A, replace(rows[0], status=SENT, sent_at=NOW, provider_message_id="M1"))
    await repo.save(A, replace(rows[1], status=ACCEPTED, provider_message_id="M2"))
    await repo.save(A, replace(rows[2], status=FAILED, error_code="timeout", error_kind="transient"))
    assert await repo.count_sent_since(A, since) == 2
    assert await repo.count_sent_since(A, since + timedelta(days=2)) == 0
    assert await repo.count_sent_since(B, since) == 0


async def test_save_는_바뀔_수_있는_칸만_바꾼다(db_session):
    repo = MessagePgRepository(db_session)
    created = await repo.create(A, new_message(variables={"url": "https://a/1"}))
    changed = replace(
        created, status=ACCEPTED, attempts=1, next_attempt_at=NOW + MINUTE, scheduled_at=NOW + 2 * MINUTE,
        channel_used="alimtalk", provider_message_id="M1", error_code="x", error_kind="transient", sent_at=NOW,
        # 아래는 바뀌지 않아야 하는 칸
        kind=REPORT, visit_id=99, customer_id=99, pet_id=7, variables={"url": "https://a/2"},
        requested_by_member_id=11,
    )
    await repo.save(A, changed)
    saved = await repo.get(A, created.id)
    assert saved == replace(
        created, status=ACCEPTED, attempts=1, next_attempt_at=NOW + MINUTE, scheduled_at=NOW + 2 * MINUTE,
        channel_used="alimtalk", provider_message_id="M1", error_code="x", error_kind="transient", sent_at=NOW,
    )
    await repo.save(A, replace(saved, status=CANCELED, canceled_reason="too_late"))
    assert ((await repo.get(A, created.id)).status, (await repo.get(A, created.id)).canceled_reason) == (
        CANCELED, "too_late")


async def test_다른_매장_컨텍스트로는_메시지가_없는_것이다(db_session):
    repo = MessagePgRepository(db_session)
    created = await repo.create(A, new_message(kind=REPORT, variables={"url": "https://a/1"}))
    assert await repo.get(B, created.id) is None
    assert await repo.list_for_visit(B, 1) == []
    assert await repo.list_pending(B, REPORT) == []
    await repo.save(B, replace(created, status=FAILED))
    assert await repo.cancel_pending(B, "channel_unlinked") == 0
    assert (await repo.get(A, created.id)).status == SCHEDULED
    with pytest.raises(ValueError):
        await repo.create(B, new_message(shop_id=1, visit_id=2))


async def test_설정을_바꿀_때_다시_계산할_대기_줄은_scheduled_뿐이다(db_session):
    repo = MessagePgRepository(db_session)
    late = await repo.create(A, new_message(visit_id=1, kind=REMINDER, scheduled_at=NOW + 2 * HOUR))
    early = await repo.create(A, new_message(visit_id=2, kind=REMINDER, scheduled_at=NOW + HOUR))
    sending = await repo.create(A, new_message(visit_id=3, kind=REMINDER, scheduled_at=NOW))
    await repo.save(A, replace(sending, status=SENDING))
    await repo.create(A, new_message(visit_id=4, kind=CONFIRM))
    assert await repo.list_pending(A, REMINDER) == [early, late]


# --- 큐 ---------------------------------------------------------------------------------------------------------

async def _due_rows(repo):
    """scheduled_at 순서가 id 순서와 다르게 — 집는 순서가 id 가 아니라 시각임을 본다."""
    later = await repo.create(A, new_message(visit_id=1, scheduled_at=NOW - HOUR))
    earliest = await repo.create(A, new_message(visit_id=2, scheduled_at=NOW - 2 * HOUR))
    exact = await repo.create(A, new_message(visit_id=3, scheduled_at=NOW))
    await repo.create(A, new_message(visit_id=4, scheduled_at=NOW + MINUTE))              # 아직
    canceled = await repo.create(A, new_message(visit_id=5, scheduled_at=NOW - HOUR))
    await repo.cancel_pending(A, "visit_canceled", visit_id=5)
    return earliest, later, exact, canceled


async def test_큐는_시각이_된_scheduled_줄만_시각_순으로_limit_만큼_집어_sending_으로_바꾼다(db_session):
    repo = MessagePgRepository(db_session)
    earliest, later, exact, _ = await _due_rows(repo)
    claimed = await repo.claim_due(NOW, 2)
    assert [(m.id, m.status) for m in claimed] == [(earliest.id, SENDING), (later.id, SENDING)]
    assert (await repo.get(A, earliest.id)).status == SENDING
    assert [m.id for m in await repo.claim_due(NOW, 10)] == [exact.id]
    assert await repo.claim_due(NOW, 10) == []
    assert [m.id for m in await repo.claim_due(NOW + MINUTE, 10)] == [exact.id + 1]


async def test_두_세션이_동시에_집어도_같은_줄을_둘이_집지_않는다(db_engine, db_session):
    """N6 — 잠긴 줄을 건너뛰어야(SKIP LOCKED) 둘째 세션이 기다리지 않고 남은 줄만 받는다."""
    repo = MessagePgRepository(db_session)
    earliest, later, exact, _ = await _due_rows(repo)
    await db_session.commit()

    sessions = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with sessions() as first, sessions() as second:
        mine = await MessagePgRepository(first).claim_due(NOW, 2)
        late = asyncio.create_task(MessagePgRepository(second).claim_due(NOW, 2))
        await asyncio.sleep(BLOCKED)
        returned_without_waiting = late.done()
        await first.commit()
        theirs = await late
        await second.commit()

    assert returned_without_waiting
    assert [m.id for m in mine] == [earliest.id, later.id]
    assert [m.id for m in theirs] == [exact.id]
    assert {m.status for m in await repo.list_for_visit(A, 3)} == {SENDING}


async def test_멈춘_sending_줄은_시간이_지난_것만_되돌리고_시도를_센다(db_session):
    repo = MessagePgRepository(db_session)
    earliest, later, exact, _ = await _due_rows(repo)
    await repo.claim_due(NOW, 2)                       # earliest, later 를 NOW 에 집었다
    await repo.claim_due(NOW + 3 * MINUTE, 1)          # exact 를 3분 뒤에 집었다
    assert await repo.recover_stuck(NOW) == 0          # 막 집은 것은 멈춘 게 아니다
    assert await repo.recover_stuck(NOW + 2 * MINUTE) == 2
    recovered = [await repo.get(A, m.id) for m in (earliest, later)]
    assert [(m.status, m.attempts) for m in recovered] == [(SCHEDULED, 1), (SCHEDULED, 1)]
    kept = await repo.get(A, exact.id)
    assert (kept.status, kept.attempts) == (SENDING, 0)
    assert [m.id for m in await repo.claim_due(NOW, 10)] == [earliest.id, later.id]   # 다시 집힌다
    assert await repo.recover_stuck(NOW + 10 * MINUTE) == 3


async def test_accepted_줄은_다음_확인_시각이_지난_것만_모은다(db_session):
    repo = MessagePgRepository(db_session)
    due = await repo.create(A, new_message(visit_id=1))
    later = await repo.create(A, new_message(visit_id=2))
    exact = await repo.create(A, new_message(visit_id=3))
    sent = await repo.create(A, new_message(visit_id=4))
    await repo.save(A, replace(due, status=ACCEPTED, provider_message_id="M1", next_attempt_at=NOW - MINUTE))
    await repo.save(A, replace(later, status=ACCEPTED, provider_message_id="M2", next_attempt_at=NOW + MINUTE))
    await repo.save(A, replace(exact, status=ACCEPTED, provider_message_id="M3", next_attempt_at=NOW))
    await repo.save(A, replace(sent, status=SENT, provider_message_id="M4", sent_at=NOW, next_attempt_at=NOW - MINUTE))
    assert [m.id for m in await repo.list_accepted(NOW)] == [due.id, exact.id]


async def test_큐의_전_매장_조회는_매장을_가리지_않고_모은다(db_session):
    channels, templates, repo = ChannelPgRepository(db_session), TemplatePgRepository(db_session), MessagePgRepository(db_session)
    await channels.save(A, channel(shop_id=1, status=LINKED))
    await channels.save(B, channel(shop_id=2, status=UNLINKED, unlinked_at=NOW))
    await channels.save(ctx(shop_id=3), channel(shop_id=3, status=LINKED))
    a_next = await templates.upsert(A, NEXT_VISIT, 1, "KA01TP0006", NOW)
    a_confirm = await templates.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    b_confirm = await templates.upsert(B, CONFIRM, 1, "KA01TP0009", NOW)
    await templates.set_status(A, CONFIRM, APPROVED, None, NOW)
    a_confirm = await templates.get(A, CONFIRM)
    assert [c.shop_id for c in await repo.list_linked_channels()] == [1, 3]
    assert await repo.list_pending_templates() == [a_next, b_confirm]
    assert await repo.list_templates_for_shops([1, 2, 4]) == {1: [a_confirm, a_next], 2: [b_confirm], 4: []}
    assert await repo.list_templates_for_shops([]) == {}


async def test_멈춘_sending_줄이_이미_세_번_시도했으면_되돌리지_않고_failed_로_끝낸다(db_session):
    """독이 든 줄이 5분마다 업체를 다시 부르며 영영 돌지 않게 — 회수에도 원 시도 1 + 3 의 상한이 있다."""
    repo = MessagePgRepository(db_session)
    earliest, later, _, _ = await _due_rows(repo)
    await repo.save(A, replace(earliest, attempts=3))
    await repo.claim_due(NOW, 2)

    assert await repo.recover_stuck(NOW + 10 * MINUTE) == 2

    ended, recovered = await repo.get(A, earliest.id), await repo.get(A, later.id)
    assert (ended.status, ended.attempts, ended.error_kind, ended.error_code) == (FAILED, 4, "transient", "STUCK")
    assert (recovered.status, recovered.attempts) == (SCHEDULED, 1)
