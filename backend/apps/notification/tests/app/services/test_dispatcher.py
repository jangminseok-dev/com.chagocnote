"""디스패처 — 집은 줄을 검사하고(설계 5.3) 보내고 결과를 적는다(스텁). 시각은 모두 kst() 로 만든다.

journal 에 저장소·게이트웨이·commit 호출이 순서대로 남는다 — "집고 → 커밋 → 보내기"(N14)를 그 순서로 본다.
"""
import logging
from dataclasses import replace
from datetime import timedelta

import pytest

from hub.app.dtos.shop_profile import ShopProfile
from notification.app.ports.output.message_gateway_port import (
    DeliveryState,
    FallbackText,
    GatewayPermanentError,
    GatewayTransientError,
)
from notification.app.services.dispatcher import DispatchReport, Dispatcher
from notification.domain.value_objects.channel_status import UNLINKED
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    DEFAULT_KINDS,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
)
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
from notification.tests.helpers.builders import TZ, channel, kst, message, settings, template
from notification.tests.helpers.fakes import (
    FakeChannels,
    FakeDirectory,
    FakeLedger,
    FakeMessages,
    FakeSettings,
    FakeShopProfile,
    FakeTemplates,
    Journal,
    SpyGateway,
)

NOW = kst(10, 14, 11)          # 14일(수) 11:00
STARTS = kst(10, 16, 14)       # 16일(금) 14:00
URL = "https://a/" + "t" * 43
SEC, MIN, HOUR, DAY = timedelta(seconds=1), timedelta(minutes=1), timedelta(hours=1), timedelta(days=1)
PHONE, NAME = "01012345678", "김민지"


def _iso(at):
    return at.isoformat()


def _profile(shop_id=1, name="두부네", tz=TZ, open=True):
    return ShopProfile(shop_id=shop_id, name=name, phone=None, address=None, timezone=tz, open=open)


class _World:
    """연동된 매장 1(채널 linked, 설정 next_visit 켜짐, 템플릿 6종 approved)과 고객 1·반려동물 101. 테스트가 필요한 것만 바꾼다."""

    def __init__(self, now=NOW, daily_cap=300, balance=100000, **settings_overrides) -> None:
        self.now = now
        self.journal = Journal()
        self.channels, self.settings = FakeChannels(self.journal), FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.gateway = SpyGateway(self.journal, balance=balance)
        self.shops = FakeShopProfile({1: _profile()})
        self.directory = FakeDirectory()
        self.directory.family()
        self.ledger = FakeLedger()
        self.channels.rows[1] = channel()
        self.settings.rows[1] = settings(**{"next_visit_enabled": True, **settings_overrides})
        for i, kind in enumerate(KINDS, start=1):
            self.templates.rows[(1, kind)] = template(id=i, kind=kind, provider_template_id=f"KA01TP000{i}")
        self.dispatcher = Dispatcher(
            queue=self.messages, channels=self.channels, settings=self.settings, templates=self.templates,
            messages=self.messages, gateway=self.gateway, shops=self.shops, directory=self.directory,
            ledger=self.ledger, commit=self._commit, now=lambda: self.now, daily_cap=daily_cap,
            balance_warn_krw=30000,
        )

    async def _commit(self) -> None:
        self.journal.append(("commit",))

    def queue(self, kind=CONFIRM, scheduled_at=NOW, starts_at=STARTS, **overrides):
        """시각이 된 줄 하나. variables 는 구독자(T5)가 넣는 모양 그대로."""
        variables = {"starts_at": _iso(starts_at)}
        if kind == CHANGE:
            variables["previous_starts_at"] = _iso(kst(10, 15, 14))
        if kind == REPORT:
            variables.update(url=URL, expires_at=_iso(kst(11, 2, 0)))
        if kind == NEXT_VISIT:
            variables.update(completed_at=_iso(kst(9, 16, 14)), interval_weeks="4")
        fields = dict(id=len(self.messages.rows) + 1, kind=kind, scheduled_at=scheduled_at, pet_id=101,
                      variables=variables)
        fields.update(overrides)
        row = message(**fields)
        self.messages.rows[row.id] = row
        return row

    def row(self, message_id=1):
        return self.messages.rows[message_id]

    async def run(self) -> DispatchReport:
        return await self.dispatcher.run_once()

    async def run_at(self, at) -> DispatchReport:
        self.now = at
        return await self.dispatcher.run_once()

    def sent(self):
        return self.gateway.sent_messages


# --- 보내기 ----------------------------------------------------------------------------------------------------

async def test_시각이_된_줄을_집어_보내면_accepted_가_되고_업체_ID_와_다음_확인_시각이_적힌다():
    world = _World()
    world.queue()
    world.queue(kind=REMINDER, scheduled_at=NOW + HOUR)      # 아직 아니다

    report = await world.run()

    assert report == DispatchReport(recovered=0, claimed=1, sent=1, deferred=0, canceled=0, failed=0, polled=0)
    row = world.row()
    assert (row.status, row.provider_message_id, row.attempts, row.next_attempt_at) == (ACCEPTED, "fake-1", 1, NOW + 5 * SEC)
    assert world.row(2).status == SCHEDULED
    [outgoing] = world.sent()
    assert (outgoing.to, outgoing.provider_channel_id, outgoing.provider_template_id) == (PHONE, "KA01PF0001", "KA01TP0001")


async def test_집고_커밋한_뒤에_보내고_결과를_적은_뒤_다시_커밋한다():
    """N14 — 잠금(집기)을 쥔 채 업체를 부르지 않는다. 회수 → 커밋 → 집기 → 커밋 → 보내기 → 저장 → 커밋."""
    world = _World()
    world.queue()

    await world.run()

    names = [entry[0] for entry in world.journal]
    assert names[:7] == ["recover_stuck", "commit", "claim_due", "commit", "send", "save_message", "commit"]


async def test_변수는_반려동물_이름과_매장_시간대의_일시로_채우고_문안_변수_이름_그대로_넘긴다():
    world = _World()
    world.queue()

    await world.run()

    [outgoing] = world.sent()
    assert outgoing.variables == {"매장명": "두부네", "대상": "콩이", "일시": "10월 16일(금) 14:00"}
    assert outgoing.button_url is None


async def test_반려동물이_없거나_이름이_없으면_보호자_이름님이다():
    world = _World()
    world.queue(pet_id=None)
    world.queue(kind=CANCEL, pet_id=999)

    await world.run()

    assert [m.variables["대상"] for m in world.sent()] == [f"{NAME}님", f"{NAME}님"]


async def test_알림장은_주소가_버튼에_가고_다음_예약_제안은_지난일과_간격을_넣는다():
    world = _World()
    world.queue(kind=REPORT)
    world.queue(kind=NEXT_VISIT, id=2)
    world.queue(kind=CHANGE, id=3)

    await world.run()

    report, next_visit, change = world.sent()
    assert report.button_url == URL
    assert report.variables == {"매장명": "두부네", "대상": "콩이", "기간안내": "11월 2일까지 열려요.", "링크": URL}
    assert next_visit.variables == {"매장명": "두부네", "대상": "콩이", "지난일": "9월 16일(수)", "간격": "4"}
    assert change.variables["이전일시"] == "10월 15일(목) 14:00"


async def test_문자_대체는_발신번호_인증까지_마친_매장만_붙인다():
    world = _World()
    world.queue()
    await world.run()
    assert world.sent()[0].fallback is None

    world.channels.rows[1] = channel(sender_number="01099990000", sender_number_verified_at=NOW,
                                     sms_fallback_enabled=True)
    world.queue(id=2)
    await world.run()
    assert world.sent()[1].fallback == FallbackText(
        from_number="01099990000", text="[두부네] 10월 16일(금) 14:00 예약이 접수되었어요.", channel="sms")


# --- 보내기 전 검사(설계 5.3) ---------------------------------------------------------------------------------------

async def test_매장이_없거나_열려_있지_않으면_shop_closed():
    world = _World()
    world.shops.shops[1] = _profile(open=False)
    world.queue()
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "shop_closed")

    del world.shops.shops[1]
    world.queue(id=2)
    await world.run()
    assert world.row(2).canceled_reason == "shop_closed"
    assert world.sent() == []


@pytest.mark.parametrize("break_world, reason", [
    (lambda w: w.channels.rows.pop(1), "channel_unlinked"),
    (lambda w: w.channels.rows.__setitem__(1, channel(status=UNLINKED, unlinked_at=NOW)), "channel_unlinked"),
    (lambda w: w.settings.rows.pop(1), "setting_off"),
    (lambda w: w.settings.rows.__setitem__(1, settings(confirm_enabled=False)), "setting_off"),
    (lambda w: w.templates.rows.pop((1, CONFIRM)), "template_rejected"),
    (lambda w: w.templates.rows.__setitem__((1, CONFIRM), template(status=REJECTED, rejected_reason="x")),
     "template_rejected"),
    (lambda w: w.directory.contacts.pop(1), "anonymized"),
    (lambda w: w.directory.family(phone="0212345678"), "bad_phone"),
], ids=["채널 없음", "채널 끊김", "설정 없음", "설정 꺼짐", "템플릿 없음", "템플릿 반려", "익명화", "휴대폰 번호 아님"])
async def test_보내기_전_검사에_걸리면_이유를_적고_취소한다(break_world, reason):
    world = _World()
    break_world(world)
    world.queue()

    report = await world.run()

    assert (world.row().status, world.row().canceled_reason, world.row().attempts) == (CANCELED, reason, 0)
    assert report.canceled == 1 and world.sent() == []


async def test_매장이_직접_누른_재발송은_설정이_꺼진_종류여도_보낸다():
    """[다시 보내기]로 만든 줄(requested_by_member_id)은 setting_off 검사를 건너뛴다. 자동 줄은 그대로 취소."""
    world = _World(confirm_enabled=False)
    world.queue(id=1, requested_by_member_id=11)
    world.queue(id=2, visit_id=2)

    report = await world.run()

    assert (world.row(1).status, world.row(2).canceled_reason) == (ACCEPTED, "setting_off")
    assert (report.sent, report.canceled) == (1, 1)


async def test_템플릿이_검수_중이면_10분_뒤로_미룬다():
    world = _World()
    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
    world.queue()

    report = await world.run()

    row = world.row()
    assert (row.status, row.scheduled_at, row.attempts, row.canceled_reason) == (SCHEDULED, NOW + 10 * MIN, 0, None)
    assert report.deferred == 1 and world.sent() == []


@pytest.mark.parametrize("now, deferred_to", [
    (kst(10, 15, 22), kst(10, 16, 8)),       # 밤 10시 → 다음 날 아침 8시
    (kst(10, 16, 6), kst(10, 16, 8)),        # 새벽 6시 → 같은 날 아침 8시
], ids=["22시", "06시"])
async def test_리마인드와_다음_예약_제안은_매장_시간대의_밤이면_아침_8시로_미룬다(now, deferred_to):
    world = _World(now=now)
    world.queue(kind=REMINDER, scheduled_at=now - HOUR)
    world.queue(kind=NEXT_VISIT, scheduled_at=now - HOUR, id=2)

    await world.run()

    for row in (world.row(), world.row(2)):
        assert (row.status, row.scheduled_at, row.attempts) == (SCHEDULED, deferred_to, 0)
    assert world.sent() == []


async def test_즉시_보내는_종류는_밤에도_바로_간다():
    world = _World(now=kst(10, 15, 22))
    world.queue(kind=CONFIRM, scheduled_at=kst(10, 15, 22))
    await world.run()
    assert world.row().status == ACCEPTED


@pytest.mark.parametrize("now, starts_at", [
    (kst(10, 15, 22), kst(10, 16, 8, 30)),   # 미룬 아침 8시가 예약 1시간 전(7:30)을 넘긴다
    (kst(10, 16, 13, 30), kst(10, 16, 14)),  # 지금이 이미 1시간 전을 넘겼다
], ids=["미룬 시각이 늦다", "지금이 늦다"])
async def test_리마인드는_보낼_시각이_예약_1시간_전을_넘기면_too_late(now, starts_at):
    world = _World(now=now)
    world.queue(kind=REMINDER, scheduled_at=now - HOUR, starts_at=starts_at)

    await world.run()

    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "too_late")


async def test_정확히_1시간_전이면_리마인드가_간다():
    world = _World(now=kst(10, 16, 13))
    world.queue(kind=REMINDER, scheduled_at=kst(10, 16, 13), starts_at=kst(10, 16, 14))
    await world.run()
    assert world.row().status == ACCEPTED


async def test_다음_예약_제안은_마케팅_동의가_없으면_no_consent():
    world = _World()
    world.directory.family(marketing_consent=False)
    world.queue(kind=NEXT_VISIT)
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "no_consent")


async def test_다음_예약_제안은_앞으로의_예약이_있으면_has_upcoming():
    world = _World()
    world.ledger.upcoming.add(1)
    world.queue(kind=NEXT_VISIT)
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "has_upcoming")


async def test_다음_예약_제안은_쿨다운_안에_같은_종류를_받았으면_cooldown_이고_정확히_30일이면_간다():
    world = _World()
    world.queue(kind=NEXT_VISIT)
    world.queue(kind=NEXT_VISIT, id=10, status=SENT, sent_at=NOW - 30 * DAY + SEC, visit_id=90)
    await world.run()
    assert (world.row().status, world.row().canceled_reason) == (CANCELED, "cooldown")

    world.messages.rows[10] = replace(world.row(10), sent_at=NOW - 30 * DAY)
    world.queue(kind=NEXT_VISIT, id=2, visit_id=2)
    await world.run()
    assert world.row(2).status == ACCEPTED


async def test_동의_없음이_앞으로의_예약_검사보다_먼저다():
    world = _World()
    world.directory.family(marketing_consent=False)
    world.ledger.upcoming.add(1)
    world.queue(kind=NEXT_VISIT)
    await world.run()
    assert world.row().canceled_reason == "no_consent"


async def test_매장의_오늘_발송이_하루_상한에_닿으면_1시간_뒤로_미루고_경고만_남긴다(caplog):
    world = _World(daily_cap=2)
    world.queue()
    for i in (10, 11):      # 오늘(매장 시간대) 업체에 넘긴 둘
        world.queue(id=i, visit_id=i, status=SENT, provider_message_id=f"old-{i}", created_at=kst(10, 14, 0, 30))
    world.queue(id=12, visit_id=12, status=SENT, provider_message_id="old-12", created_at=kst(10, 13, 23, 30))   # 어제

    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        report = await world.run()

    row = world.row()
    assert (row.status, row.scheduled_at, row.attempts) == (SCHEDULED, NOW + HOUR, 0)
    assert report.deferred == 1 and world.sent() == []
    [record] = caplog.records
    assert record.levelno == logging.WARNING and "2" in record.getMessage()
    assert PHONE not in caplog.text and NAME not in caplog.text


async def test_하루_상한_아래면_보낸다():
    world = _World(daily_cap=2)
    world.queue()
    world.queue(id=10, visit_id=10, status=SENT, provider_message_id="old-10", created_at=kst(10, 14, 0, 30))
    await world.run()
    assert world.row().status == ACCEPTED


# --- 보내기 실패 ------------------------------------------------------------------------------------------------

async def test_일시_오류는_1분_5분_30분_뒤로_미루고_네_번째_실패에서_failed_다():
    world = _World()
    world.gateway.send_error = GatewayTransientError("3040")
    world.queue()

    await world.run()
    assert (world.row().status, world.row().scheduled_at, world.row().attempts, world.row().error_code) == (
        SCHEDULED, NOW + MIN, 1, "3040")
    await world.run_at(NOW + MIN)
    assert (world.row().status, world.row().scheduled_at, world.row().attempts) == (SCHEDULED, NOW + 6 * MIN, 2)
    await world.run_at(NOW + 6 * MIN)
    assert (world.row().status, world.row().scheduled_at, world.row().attempts) == (SCHEDULED, NOW + 36 * MIN, 3)
    report = await world.run_at(NOW + 36 * MIN)
    assert (world.row().status, world.row().attempts, world.row().error_kind, world.row().error_code) == (
        FAILED, 4, "transient", "3040")
    assert report.failed == 1 and len([e for e in world.journal if e[0] == "send"]) == 4


async def test_영구_오류는_바로_failed_다():
    world = _World()
    world.gateway.send_error = GatewayPermanentError("1062")
    world.queue()

    report = await world.run()

    row = world.row()
    assert (row.status, row.error_kind, row.error_code, row.attempts) == (FAILED, "permanent", "1062", 1)
    assert report.failed == 1


async def test_한_줄의_예외는_그_줄만_일시_실패로_적고_다음_줄을_막지_않는다(monkeypatch, caplog):
    world = _World()
    world.queue()
    world.queue(id=2, visit_id=2)
    original = world.directory.contact

    async def contact(ctx, customer_id):
        if world.row().status == SENDING and not world.sent():
            raise RuntimeError("포트가 죽었다")
        return await original(ctx, customer_id)

    monkeypatch.setattr(world.directory, "contact", contact)

    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        report = await world.run()

    first, second = world.row(), world.row(2)
    assert (first.status, first.scheduled_at, first.attempts, first.error_kind, first.error_code) == (
        SCHEDULED, NOW + MIN, 1, "transient", "RuntimeError")
    assert second.status == ACCEPTED
    assert (report.deferred, report.sent) == (1, 1)
    [record] = caplog.records
    assert "RuntimeError" in record.getMessage() and "1" in record.getMessage() and CONFIRM in record.getMessage()
    assert "포트가 죽었다" not in caplog.text


# --- 접수 뒤 상태 조회 ------------------------------------------------------------------------------------------

async def test_접수된_줄은_다음_확인_시각이_지나면_조회해_sent_와_나간_길과_보낸_시각을_적는다():
    world = _World()
    world.queue()
    await world.run()

    report = await world.run_at(NOW + 5 * SEC)

    row = world.row()
    assert (row.status, row.channel_used, row.sent_at) == (SENT, "alimtalk", NOW + 5 * SEC)
    assert report == DispatchReport(polled=1)


async def test_문자로_대체되어_나갔으면_fallback_sent_다():
    world = _World()
    world.directory.family(phone="01012340000")
    world.channels.rows[1] = channel(sender_number="01099990000", sender_number_verified_at=NOW,
                                     sms_fallback_enabled=True)
    world.queue()
    await world.run()

    await world.run_at(NOW + 5 * SEC)

    assert (world.row().status, world.row().channel_used) == (FALLBACK_SENT, "sms")


async def test_업체가_실패로_답하면_failed_와_업체의_분류를_적는다():
    world = _World()
    world.directory.family(phone="01012349999")
    world.queue()
    await world.run()

    report = await world.run_at(NOW + 5 * SEC)

    row = world.row()
    assert (row.status, row.error_code, row.error_kind) == (FAILED, "3040", "transient")
    assert (report.polled, report.failed) == (1, 1)


async def test_아직_대기면_처음_1분은_5초마다_그_뒤는_1분마다_다시_묻는다():
    world = _World()
    world.directory.family(phone="01012348888")      # 두 번 대기 뒤 성공
    world.queue()
    await world.run()

    await world.run_at(NOW + 5 * SEC)
    assert (world.row().status, world.row().next_attempt_at) == (ACCEPTED, NOW + 10 * SEC)
    await world.run_at(NOW + 2 * MIN)
    assert (world.row().status, world.row().next_attempt_at) == (ACCEPTED, NOW + 3 * MIN)
    await world.run_at(NOW + 3 * MIN)
    assert world.row().status == SENT


async def test_다음_확인_시각이_아직이면_묻지_않는다():
    world = _World()
    world.queue()
    await world.run()
    await world.run_at(NOW + 4 * SEC)
    assert world.row().status == ACCEPTED and [e for e in world.journal if e[0] == "delivery_state"] == []


async def test_접수_뒤_24시간_안에_최종_상태가_없으면_일시_실패다():
    world = _World()
    world.queue(status=ACCEPTED, scheduled_at=NOW - 25 * HOUR, next_attempt_at=NOW - MIN, provider_message_id="late")
    world.gateway.states["late"] = DeliveryState(status="pending", channel_used=None, error_code=None, error_kind=None)

    await world.run()

    row = world.row()
    assert (row.status, row.error_kind, row.error_code) == (FAILED, "transient", "TIMEOUT")


async def test_상태_조회가_실패하면_1분_뒤에_다시_묻는다():
    world = _World()
    world.queue()
    await world.run()
    world.gateway.state_error = GatewayTransientError("504")

    await world.run_at(NOW + 5 * SEC)

    assert (world.row().status, world.row().next_attempt_at) == (ACCEPTED, NOW + 65 * SEC)


# --- 회수·주기 작업 ----------------------------------------------------------------------------------------------

async def test_5분_넘게_sending_인_줄은_되돌리고_시도를_세고_같은_루프에서_다시_보낸다():
    world = _World()
    world.queue(status=SENDING)
    world.messages.claimed_at[1] = NOW - 6 * MIN
    world.queue(id=2, visit_id=2, status=SENDING)
    world.messages.claimed_at[2] = NOW - 4 * MIN

    report = await world.run()

    assert (report.recovered, report.claimed, report.sent) == (1, 1, 1)
    assert (world.row().status, world.row().attempts) == (ACCEPTED, 2)
    assert world.row(2).status == SENDING


async def test_템플릿_상태와_잔액은_첫_루프와_10분_24시간_뒤에만_다시_본다():
    world = _World()
    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)

    await world.run()
    await world.run_at(NOW + 9 * MIN)
    assert [e for e in world.journal if e[0] in ("template_state", "balance")] == [("template_state", "KA01TP0001"), ("balance",)]
    assert world.templates.rows[(1, CONFIRM)].status == APPROVED

    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
    await world.run_at(NOW + 10 * MIN)
    await world.run_at(NOW + 24 * HOUR)
    assert [e for e in world.journal if e[0] in ("template_state", "balance")] == [
        ("template_state", "KA01TP0001"), ("balance",), ("template_state", "KA01TP0001"), ("balance",)]


async def test_검수_중인_템플릿은_업체_상태대로_approved_나_rejected_가_된다():
    world = _World()
    world.gateway = SpyGateway(world.journal, reject_next_visit=True)
    world.dispatcher._gateway = world.gateway
    world.templates.rows[(1, CONFIRM)] = template(status=PENDING, decided_at=None)
    world.templates.rows[(1, NEXT_VISIT)] = template(id=6, kind=NEXT_VISIT, status=PENDING, decided_at=None,
                                                     provider_template_id="tpl-KA01PF0001-next_visit-v1")

    changed = await world.dispatcher.refresh_templates()

    confirm, next_visit = world.templates.rows[(1, CONFIRM)], world.templates.rows[(1, NEXT_VISIT)]
    assert (confirm.status, confirm.decided_at) == (APPROVED, NOW)
    assert (next_visit.status, next_visit.rejected_reason, next_visit.decided_at) == (REJECTED, "가짜 반려", NOW)
    assert changed == 2


async def test_연동한_매장의_빠진_종류를_다시_등록하고_다음_예약_제안은_켜진_매장만():
    world = _World(next_visit_enabled=False)
    for kind in KINDS[1:]:
        del world.templates.rows[(1, kind)]                 # 매장 1 은 confirm 만 남았다
    world.shops.shops[2] = _profile(shop_id=2)
    world.channels.rows[2] = channel(shop_id=2, provider_channel_id="KA01PF0002")
    world.settings.rows[2] = settings(next_visit_enabled=True)
    world.shops.shops[3] = _profile(shop_id=3)
    world.channels.rows[3] = channel(shop_id=3, status=UNLINKED, unlinked_at=NOW)   # 끊긴 매장은 건너뛴다
    world.channels.rows[4] = channel(shop_id=4)                                      # 프로필이 없는 매장도

    changed = await world.dispatcher.refresh_templates()

    assert [(e[1], e[2]) for e in world.journal if e[0] == "register_template"] == (
        [("KA01PF0001", kind) for kind in DEFAULT_KINDS[1:]] + [("KA01PF0002", kind) for kind in KINDS])
    registered = world.templates.rows[(1, REMINDER)]
    assert (registered.status, registered.provider_template_id, registered.requested_at) == (
        PENDING, "tpl-KA01PF0001-reminder-v1", NOW)
    assert (1, NEXT_VISIT) not in world.templates.rows and (2, NEXT_VISIT) in world.templates.rows
    assert changed == 4 + 6


async def test_템플릿_등록이_실패하면_그_종류만_건너뛰고_다음_주기에_다시_한다(caplog):
    world = _World()
    del world.templates.rows[(1, REMINDER)]
    world.gateway.register_error = GatewayTransientError("503")

    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        changed = await world.dispatcher.refresh_templates()

    assert changed == 0 and (1, REMINDER) not in world.templates.rows
    assert len(caplog.records) == 1


async def test_잔액이_기준_아래면_금액만_경고한다(caplog):
    world = _World(balance=1000)
    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        assert await world.dispatcher.check_balance() == 1000
    [record] = caplog.records
    assert record.levelno == logging.WARNING and "1000" in record.getMessage() and "30000" in record.getMessage()

    caplog.clear()
    world = _World(balance=30000)
    with caplog.at_level(logging.WARNING, logger="notification.dispatcher"):
        await world.dispatcher.check_balance()
    assert caplog.records == []


# --- 로그 -----------------------------------------------------------------------------------------------------

async def test_로그에는_메시지_ID_매장_종류_결과만_있고_번호_이름_주소는_없다(caplog):
    world = _World()
    world.queue(kind=REPORT)
    world.queue(id=2, visit_id=2)
    world.directory.contacts.pop(1)
    world.directory.family(customer_id=1, phone="01012349999")
    world.queue(id=3, visit_id=3, customer_id=2)        # 익명화된 고객

    with caplog.at_level(logging.INFO, logger="notification.dispatcher"):
        await world.run()
        await world.run_at(NOW + 5 * SEC)

    assert any("report" in r.getMessage() and "accepted" in r.getMessage() for r in caplog.records)
    assert any("canceled(anonymized)" in r.getMessage() for r in caplog.records)
    assert any("failed(3040)" in r.getMessage() for r in caplog.records)
    for secret in (PHONE, "01012349999", NAME, URL, "t" * 43, "콩이"):
        assert secret not in caplog.text
