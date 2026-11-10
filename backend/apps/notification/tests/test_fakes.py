"""알림 저장소 스텁이 pg 구현과 같은 규칙을 지키는지 — 뒤 작업의 구독자·디스패처 테스트가 이 스텁에 기댄다."""
from dataclasses import replace
from datetime import timedelta

import pytest

from notification.domain.entities.notification_settings import DEFAULT_NOTIFICATION_SETTINGS
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import LINKED, UNLINKED
from notification.domain.value_objects.message_kind import CONFIRM, NEXT_VISIT, REMINDER, REPORT
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED, SENDING, SENT
from notification.domain.value_objects.template_status import PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, new_message, settings
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates

A, B = ctx(shop_id=1), ctx(shop_id=2)
NOW = kst(10, 14, 11)


async def test_같은_방문_같은_종류의_대기_줄이_둘이면_예외다():
    messages = FakeMessages()
    first = await messages.create(A, new_message())
    with pytest.raises(MessageAlreadyPendingError):
        await messages.create(A, new_message())
    assert await messages.cancel_pending(A, "rescheduled", visit_id=1, kinds=[CONFIRM]) == 1
    assert (await messages.get(A, first.id)).canceled_reason == "rescheduled"
    second = await messages.create(A, new_message())
    await messages.save(A, replace(second, status=SENDING))
    with pytest.raises(MessageAlreadyPendingError):
        await messages.create(A, new_message())
    assert [m.id for m in await messages.list_for_visit(A, 1)] == [second.id, first.id]
    assert await messages.list_for_visit(B, 1) == []


async def test_큐는_시각이_된_줄만_순서대로_집어_sending_으로_바꾸고_멈춘_것은_되돌린다():
    messages = FakeMessages()
    late = await messages.create(A, new_message(visit_id=1, scheduled_at=NOW - timedelta(hours=1)))
    early = await messages.create(A, new_message(visit_id=2, scheduled_at=NOW - timedelta(hours=2)))
    await messages.create(A, new_message(visit_id=3, scheduled_at=NOW + timedelta(hours=1)))
    assert [m.id for m in await messages.claim_due(NOW, 1)] == [early.id]
    assert (await messages.get(A, early.id)).status == SENDING
    assert [m.id for m in await messages.claim_due(NOW, 5)] == [late.id]
    assert await messages.claim_due(NOW, 5) == []
    assert await messages.recover_stuck(NOW) == 0
    assert await messages.recover_stuck(NOW + timedelta(minutes=5)) == 2
    recovered = await messages.get(A, early.id)
    assert (recovered.status, recovered.attempts) == (SCHEDULED, 1)


async def test_보낸_줄_판정은_상태와_주소로_하고_매장을_거른다():
    messages = FakeMessages()
    report = await messages.create(A, new_message(kind=REPORT, variables={"url": "https://a/1"}))
    assert await messages.has_delivered(A, 1, REPORT) is False
    await messages.save(A, replace(report, status=SENT, sent_at=NOW))
    assert await messages.has_delivered(A, 1, REPORT) is True
    assert await messages.has_delivered(A, 1, REPORT, url="https://a/1") is True
    assert await messages.has_delivered(A, 1, REPORT, url="https://a/2") is False
    assert await messages.has_delivered(B, 1, REPORT) is False
    assert await messages.last_delivered_at(A, 1, REPORT) == NOW
    assert await messages.last_delivered_at(A, 1, NEXT_VISIT) is None


async def test_취소는_대기_줄만_범위대로_덮는다():
    messages = FakeMessages()
    await messages.create(A, new_message(visit_id=1, kind=CONFIRM))
    await messages.create(A, new_message(visit_id=1, kind=REMINDER))
    await messages.create(A, new_message(visit_id=2, kind=CONFIRM))
    await messages.create(B, new_message(shop_id=2, visit_id=9, kind=CONFIRM))
    assert await messages.cancel_pending(A, "rescheduled", visit_id=1, kinds=[REMINDER]) == 1
    assert await messages.cancel_pending(A, "channel_unlinked") == 2
    assert await messages.cancel_pending(A, "channel_unlinked") == 0
    assert [m.status for m in await messages.list_for_visit(B, 9)] == [SCHEDULED]
    assert {m.canceled_reason for m in await messages.list_for_visit(A, 1)} == {"rescheduled", "channel_unlinked"}
    assert all(m.status == CANCELED for m in await messages.list_for_visit(A, 1))


async def test_채널_설정_템플릿_스텁은_매장당_한_줄이고_컨텍스트의_매장만_본다():
    channels, store, templates = FakeChannels(), FakeSettings(), FakeTemplates()
    assert await channels.save(A, channel()) == channel()
    assert (await channels.save(A, channel(status=UNLINKED))).status == UNLINKED
    assert (await channels.get(A)).status == UNLINKED and await channels.get(B) is None
    with pytest.raises(ValueError):
        await channels.save(A, channel(shop_id=2))

    assert await store.get(A) is None
    assert await store.ensure(A) == DEFAULT_NOTIFICATION_SETTINGS
    changed = await store.update(A, settings(next_visit_enabled=True))
    assert await store.ensure(A) == changed and await store.get(B) is None

    first = await templates.upsert(A, NEXT_VISIT, 1, "KA01TP0002", NOW)
    await templates.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    await templates.set_status(A, NEXT_VISIT, REJECTED, "사유", NOW)
    again = await templates.upsert(A, NEXT_VISIT, 2, "KA01TP0003", NOW)
    assert (again.id, again.status, again.rejected_reason, again.text_version) == (first.id, PENDING, None, 2)
    assert [t.kind for t in await templates.list_for_shop(A)] == [CONFIRM, NEXT_VISIT]
    assert await templates.get(B, CONFIRM) is None and await templates.list_for_shop(B) == []
    assert await templates.delete_all(A) == 2 and await templates.list_for_shop(A) == []


async def test_큐의_전_매장_조회는_같이_넘긴_채널_템플릿_스텁을_본다():
    channels, templates = FakeChannels(), FakeTemplates()
    messages = FakeMessages(templates=templates, channels=channels)
    await channels.save(A, channel(shop_id=1, status=LINKED))
    await channels.save(B, channel(shop_id=2, status=UNLINKED))
    pending = await templates.upsert(A, CONFIRM, 1, "KA01TP0001", NOW)
    await templates.upsert(B, CONFIRM, 1, "KA01TP0009", NOW)
    await templates.set_status(B, CONFIRM, "approved", None, NOW)
    assert [c.shop_id for c in await messages.list_linked_channels()] == [1]
    assert await messages.list_pending_templates() == [pending]
    assert {s: [t.kind for t in ts] for s, ts in (await messages.list_templates_for_shops([1, 2, 3])).items()} == {
        1: [CONFIRM], 2: [CONFIRM], 3: []}


async def test_묶음_줄_고치기는_scheduled_줄만_건드리고_다른_매장은_False_다():
    messages = FakeMessages()
    starts = {"starts_at": "S", "pet_ids": "101,102"}
    row = await messages.create(A, new_message(visit_id=7, kind=REMINDER, variables=starts))
    sending = await messages.create(A, new_message(visit_id=8, kind=REMINDER, variables=starts))
    await messages.save(A, replace(sending, status=SENDING))
    assert [m.id for m in await messages.list_scheduled_for_group(A, 1, "S", (REMINDER,))] == [row.id]
    assert await messages.list_scheduled_for_group(A, 1, "S", (CONFIRM,)) == []
    assert await messages.rewrite_scheduled(B, row.id, {"pet_ids": "102"}, 9, 102) is False
    assert await messages.rewrite_scheduled(A, sending.id, {"pet_ids": "102"}, 9, 102) is False
    assert await messages.cancel_scheduled(A, sending.id, "visit_canceled") is False
    assert await messages.rewrite_scheduled(A, row.id, {"starts_at": "S", "pet_ids": "102"}, 9, 102) is True
    after = await messages.get(A, row.id)
    assert (after.visit_id, after.pet_id, after.variables["pet_ids"], after.status) == (9, 102, "102", SCHEDULED)
    assert await messages.cancel_pending(A, "no_show", except_ids=[row.id]) == 1
    assert await messages.cancel_scheduled(A, row.id, "visit_canceled") is True
    assert (await messages.get(A, row.id)).canceled_reason == "visit_canceled"


async def test_옮길_방문에_같은_종류의_대기_줄이_있으면_스텁도_예외다():
    messages = FakeMessages()
    row = await messages.create(A, new_message(visit_id=7, kind=REMINDER))
    await messages.create(A, new_message(visit_id=8, kind=REMINDER))
    with pytest.raises(MessageAlreadyPendingError):
        await messages.rewrite_scheduled(A, row.id, {}, 8, 102)
    assert await messages.rewrite_scheduled(A, row.id, {"pet_ids": "101"}, 7, 101) is True   # 제자리는 된다
