"""구독자 인터랙터 — visit 이벤트마다 설계 5.2 표의 줄을 만들고 취소한다(스텁). 시각은 모두 kst() 로 만든다."""
from dataclasses import replace
from datetime import datetime

import pytest

from hub.app.dtos.visit_events import (
    VisitCanceled,
    VisitClosed,
    VisitReportIssued,
    VisitReportRevoked,
    VisitRescheduled,
    VisitReserved,
)
from notification.app.dtos.handle_visit_event_dto import HandleVisitEventCommand
from notification.app.use_cases.handle_visit_event_interactor import HandleVisitEventInteractor
from notification.domain.errors import MessageAlreadyPendingError
from notification.domain.value_objects.channel_status import TOKEN_REQUESTED, UNLINKED
from notification.domain.value_objects.message_kind import (
    CANCEL,
    CHANGE,
    CONFIRM,
    KINDS,
    NEXT_VISIT,
    REMINDER,
    REPORT,
)
from notification.domain.value_objects.message_status import CANCELED, SCHEDULED, SENDING, SENT
from notification.domain.value_objects.template_status import PENDING, REJECTED
from notification.tests.helpers.builders import channel, ctx, kst, message, settings, template
from notification.tests.helpers.fakes import FakeChannels, FakeMessages, FakeSettings, FakeTemplates, Journal

NOW = kst(10, 14, 11)          # 14일(수) 11:00
STARTS = kst(10, 16, 14)       # 16일(금) 14:00 → 리마인드는 15일 18:00
MOVED = kst(10, 20, 14)        # 20일(화) 14:00 → 리마인드는 19일 18:00
URL, OTHER_URL = "https://a/1", "https://a/2"


def _iso(at: datetime) -> str:
    return at.isoformat()


def _event(cls, **overrides):
    fields = dict(ctx=ctx(), visit_id=7, customer_id=1, pet_id=101, starts_at=STARTS, occurred_at=NOW)
    fields.update(overrides)
    return cls(**fields)


class _World:
    """연동된 매장(채널 linked, 설정 있음, 템플릿 6종 approved). 테스트가 필요한 것만 끈다."""

    def __init__(self, **settings_overrides) -> None:
        self.journal = Journal()
        self.channels, self.settings = FakeChannels(self.journal), FakeSettings(self.journal)
        self.templates = FakeTemplates(self.journal)
        self.messages = FakeMessages(self.journal, self.templates, self.channels)
        self.channels.rows[1] = channel()
        self.settings.rows[1] = settings(**{"next_visit_enabled": True, **settings_overrides})
        for i, kind in enumerate(KINDS, start=1):
            self.templates.rows[(1, kind)] = template(id=i, kind=kind)
        self.interactor = HandleVisitEventInteractor(
            channels=self.channels, settings=self.settings, templates=self.templates, messages=self.messages,
            now=lambda: NOW,
        )

    async def handle(self, event) -> None:
        await self.interactor.handle_visit_event(HandleVisitEventCommand(event=event))

    def rows(self, visit_id=7):
        return [(m.kind, m.status, m.scheduled_at, m.canceled_reason)
                for m in self.messages.rows.values() if m.visit_id == visit_id]

    def pending(self, visit_id=7):
        return [(m.kind, m.scheduled_at) for m in self.messages.rows.values()
                if m.visit_id == visit_id and m.status == SCHEDULED]

    def only(self, kind, status=SCHEDULED):
        [found] = [m for m in self.messages.rows.values() if m.kind == kind and m.status == status]
        return found

    def delivered(self, kind, **variables):
        """같은 방문·종류를 이미 보낸 줄."""
        self.messages.rows[90 + KINDS.index(kind)] = message(
            id=90 + KINDS.index(kind), visit_id=7, kind=kind, status=SENT, sent_at=kst(10, 13, 9),
            variables=variables)


# --- 공통 문지기 ---------------------------------------------------------------------------------------------------

async def test_채널이_없으면_아무_줄도_만들지_않는다():
    world = _World()
    del world.channels.rows[1]
    await world.handle(_event(VisitReserved))
    assert world.rows() == []


@pytest.mark.parametrize("status", [UNLINKED, TOKEN_REQUESTED])
async def test_채널이_linked_가_아니면_아무_줄도_만들지_않는다(status):
    world = _World()
    world.channels.rows[1] = channel(status=status)
    await world.handle(_event(VisitReserved))
    assert world.rows() == []


async def test_연동_안_된_매장은_취소도_하지_않는다():
    world = _World()
    await world.handle(_event(VisitReserved))
    world.channels.rows[1] = channel(status=UNLINKED)
    await world.handle(_event(VisitCanceled, reason="shop_reason"))
    assert [r[1] for r in world.rows()] == [SCHEDULED, SCHEDULED]
    assert ("cancel_pending", 7, "visit_canceled") not in world.journal


async def test_설정이_없으면_아무_줄도_만들지_않는다():
    world = _World()
    del world.settings.rows[1]
    await world.handle(_event(VisitReserved))
    assert world.rows() == []


# --- 예약됨 ---------------------------------------------------------------------------------------------------------

async def test_예약되면_confirm_은_지금_reminder_는_전날_설정_시각의_줄이_생긴다():
    world = _World()
    await world.handle(_event(VisitReserved))
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 15, 18))]
    confirm = world.only(CONFIRM)
    assert (confirm.shop_id, confirm.visit_id, confirm.customer_id, confirm.pet_id) == (1, 7, 1, 101)
    assert confirm.requested_by_member_id is None
    assert confirm.variables == {"starts_at": _iso(STARTS), "pet_ids": "101", "pet_visits": "101:7"}
    assert world.only(REMINDER).variables == {"starts_at": _iso(STARTS), "pet_ids": "101", "pet_visits": "101:7"}


async def test_매장의_리마인드_시각을_따른다():
    from datetime import time

    world = _World(reminder_time=time(9, 30))
    await world.handle(_event(VisitReserved))
    assert world.only(REMINDER).scheduled_at == kst(10, 15, 9, 30)


async def test_전날은_매장_시간대의_날짜로_센다():
    world = _World()
    await world.handle(_event(VisitReserved, starts_at=kst(10, 17, 0, 30)))   # UTC 로는 16일 15:30
    assert world.only(REMINDER).scheduled_at == kst(10, 16, 18)


async def test_리마인드_시각이_이미_지났으면_confirm_만_생긴다():
    world = _World()
    await world.handle(_event(VisitReserved, starts_at=kst(10, 14, 15)))   # 오늘 15:00 — 전날 18:00 은 지났다
    assert world.pending() == [(CONFIRM, NOW)]


@pytest.mark.parametrize("flag, left", [("confirm_enabled", REMINDER), ("reminder_enabled", CONFIRM)])
async def test_설정이_꺼진_종류만_빠진다(flag, left):
    world = _World(**{flag: False})
    await world.handle(_event(VisitReserved))
    assert [k for k, _ in world.pending()] == [left]


@pytest.mark.parametrize("status", [PENDING, REJECTED, None])
async def test_템플릿이_approved_가_아니면_그_종류만_빠진다(status):
    world = _World()
    if status is None:
        del world.templates.rows[(1, CONFIRM)]
    else:
        world.templates.rows[(1, CONFIRM)] = template(kind=CONFIRM, status=status)
    await world.handle(_event(VisitReserved))
    assert [k for k, _ in world.pending()] == [REMINDER]


@pytest.mark.parametrize("kind, left", [(CONFIRM, REMINDER), (REMINDER, CONFIRM)])
async def test_이미_보낸_종류는_다시_만들지_않는다(kind, left):
    world = _World()
    world.delivered(kind)
    await world.handle(_event(VisitReserved))
    assert [k for k, _ in world.pending()] == [left]


async def test_되돌린_예약은_reminder_만_만든다():
    world = _World()
    await world.handle(_event(VisitReserved, revived=True))
    assert world.pending() == [(REMINDER, kst(10, 15, 18))]


async def test_반복의_둘째_회차부터는_접수_안내_없이_리마인드만():
    world = _World()
    await world.handle(_event(VisitReserved, series_followup=True))
    assert world.pending() == [(REMINDER, kst(10, 15, 18))]


async def test_조용한_일정_변경은_변경_안내_없이_리마인드만_옮긴다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitRescheduled, starts_at=kst(10, 20, 14), previous_starts_at=STARTS, quiet=True))
    kinds = [k for k, _ in world.pending()]
    assert kinds.count(CHANGE) == 0 and kinds.count(REMINDER) == 1


async def test_조용한_취소는_취소_안내_없이_대기_줄만_거둔다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitCanceled, reason="shop_reason", quiet=True))
    assert world.pending() == []
    assert [r for r in world.rows() if r[0] == CANCEL] == []


async def test_같은_예약이_두_번_오면_둘째는_묶음의_줄로_보아_아무것도_만들지_않는다():
    """같은 보호자·같은 시각·같은 종류의 대기 줄이 있으면 만들지 않는 묶음 규칙이 중복 발행도 삼킨다 — 색인 위반까지 가지 않는다."""
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitReserved))
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 15, 18))]


async def test_같은_알림장이_두_번_오면_MessageAlreadyPendingError_가_그대로_올라온다():
    world = _World()
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    with pytest.raises(MessageAlreadyPendingError):
        await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))


# --- 일정 바뀜 ------------------------------------------------------------------------------------------------------

async def _reserved_then_moved(world, **overrides):
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitRescheduled, previous_starts_at=STARTS, starts_at=MOVED, **overrides))


async def test_일정이_바뀌면_옛_reminder_는_rescheduled_로_취소되고_새_시각의_reminder_와_change_가_생긴다():
    world = _World()
    await _reserved_then_moved(world)
    assert world.rows() == [
        (CONFIRM, SCHEDULED, NOW, None),
        (REMINDER, CANCELED, kst(10, 15, 18), "rescheduled"),
        (REMINDER, SCHEDULED, kst(10, 19, 18), None),
        (CHANGE, SCHEDULED, NOW, None),
    ]
    assert world.only(CHANGE).variables == {"starts_at": _iso(MOVED), "previous_starts_at": _iso(STARTS),
                                            "pet_ids": "101", "pet_visits": "101:7"}
    assert world.only(REMINDER).variables == {"starts_at": _iso(MOVED), "pet_ids": "101", "pet_visits": "101:7"}
    assert ("cancel_pending", 7, "rescheduled") in world.journal


async def test_연달아_두_번_바꾸면_아직_안_나간_change_는_취소되고_마지막_한_통만_남는다():
    world = _World()
    await _reserved_then_moved(world)
    await world.handle(_event(VisitRescheduled, previous_starts_at=MOVED, starts_at=kst(10, 22, 10)))
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 21, 18)), (CHANGE, NOW)]
    assert world.only(CHANGE).variables["previous_starts_at"] == _iso(MOVED)


async def test_바뀐_일정의_reminder_와_change_는_이미_보냈어도_다시_간다():
    world = _World()
    world.delivered(REMINDER)
    world.delivered(CHANGE)
    await world.handle(_event(VisitRescheduled, previous_starts_at=STARTS, starts_at=MOVED))
    assert world.pending() == [(REMINDER, kst(10, 19, 18)), (CHANGE, NOW)]


async def test_바뀐_일정의_리마인드_시각이_지났으면_change_만_생긴다():
    world = _World()
    await world.handle(_event(VisitRescheduled, previous_starts_at=STARTS, starts_at=kst(10, 14, 16)))
    assert world.pending() == [(CHANGE, NOW)]


@pytest.mark.parametrize("how", ["setting_off", "template_pending"])
async def test_변경_안내가_꺼졌거나_템플릿이_미승인이면_reminder_만_다시_만든다(how):
    world = _World(change_enabled=False) if how == "setting_off" else _World()
    if how == "template_pending":
        world.templates.rows[(1, CHANGE)] = template(kind=CHANGE, status=PENDING)
    await _reserved_then_moved(world)
    assert world.pending() == [(CONFIRM, NOW), (REMINDER, kst(10, 19, 18))]


# --- 취소됨·노쇼 ----------------------------------------------------------------------------------------------------

async def test_매장_사정_취소는_대기_줄을_전부_취소하고_cancel_줄을_만든다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitCanceled, reason="shop_reason"))
    assert world.rows() == [
        (CONFIRM, CANCELED, NOW, "visit_canceled"),
        (REMINDER, CANCELED, kst(10, 15, 18), "visit_canceled"),
        (CANCEL, SCHEDULED, NOW, None),
    ]
    assert world.only(CANCEL).variables == {"starts_at": _iso(STARTS), "pet_ids": "101", "pet_visits": "101:7"}


async def test_고객_요청_취소는_대기_줄만_취소하고_cancel_줄은_없다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitCanceled, reason="customer_request"))
    assert [r[1] for r in world.rows()] == [CANCELED, CANCELED]


@pytest.mark.parametrize("how", ["setting_off", "template_rejected", "delivered"])
async def test_취소_안내는_변경_설정_템플릿_보낸_적을_본다(how):
    world = _World(change_enabled=False) if how == "setting_off" else _World()
    if how == "template_rejected":
        world.templates.rows[(1, CANCEL)] = template(kind=CANCEL, status=REJECTED)
    if how == "delivered":
        world.delivered(CANCEL)
    await world.handle(_event(VisitCanceled, reason="shop_reason"))
    assert world.pending() == []


async def test_노쇼는_대기_줄을_no_show_로_취소만_한다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitClosed, outcome="no_show", previous_completed_at=None))
    assert [(r[1], r[3]) for r in world.rows()] == [(CANCELED, "no_show"), (CANCELED, "no_show")]


# --- 완료 -----------------------------------------------------------------------------------------------------------

def _completed(previous=None, **overrides):
    return _event(VisitClosed, outcome="completed", previous_completed_at=previous, starts_at=kst(10, 14, 9),
                  **overrides)


async def test_완료는_대기_줄을_건드리지_않고_앞선_완료가_없으면_4주_뒤_설정_시각에_next_visit_을_만든다():
    world = _World()
    await world.handle(_event(VisitReserved, starts_at=kst(10, 14, 9)))
    await world.handle(_completed())
    assert world.pending() == [(CONFIRM, NOW), (NEXT_VISIT, kst(11, 11, 18))]
    assert world.only(NEXT_VISIT).variables == {
        "starts_at": _iso(kst(10, 14, 9)), "completed_at": _iso(NOW), "interval_weeks": "4", "pet_ids": "101", "pet_visits": "101:7"}


# 주 수의 순서(⑬ 설계 3.4): 아이에게 직접 정한 값 → 매장 알림 설정의 고정 주 수 → 계산한 값(간격 둘 이상)
# → 매장의 기본 간격. 간격 하나(single)는 쓰지 않는다 — 앞선 완료와의 간격 하나로 주기를 정하지 않는다.


async def test_계산한_주기가_있으면_그_주_수_뒤다():
    world = _World()
    await world.handle(_completed(previous=kst(9, 23, 11), cycle_weeks=3, cycle_source="computed"))
    assert world.pending() == [(NEXT_VISIT, kst(11, 4, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "3"


async def test_간격_하나뿐이면_앞선_완료와의_간격이_아니라_매장의_기본_간격이다():
    world = _World()
    await world.handle(_completed(previous=kst(9, 23, 11), cycle_source="single", default_cycle_weeks=5))
    assert world.pending() == [(NEXT_VISIT, kst(11, 18, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "5"


async def test_설정의_주_수가_있으면_계산한_주기보다_앞선다():
    world = _World(next_visit_after_weeks=6)
    await world.handle(_completed(previous=kst(9, 23, 11), cycle_weeks=3, cycle_source="computed"))
    assert world.pending() == [(NEXT_VISIT, kst(11, 25, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "6"


async def test_아이에게_직접_정한_주기는_설정의_주_수보다_앞선다():
    world = _World(next_visit_after_weeks=6)
    await world.handle(_completed(cycle_weeks=2, cycle_source="manual"))
    assert world.pending() == [(NEXT_VISIT, kst(10, 28, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "2"


@pytest.mark.parametrize("how", ["setting_off", "template_pending", "delivered"])
async def test_다음_예약_제안은_설정_템플릿_보낸_적을_본다(how):
    world = _World(next_visit_enabled=False) if how == "setting_off" else _World()
    if how == "template_pending":
        world.templates.rows[(1, NEXT_VISIT)] = template(kind=NEXT_VISIT, status=PENDING)
    if how == "delivered":
        world.delivered(NEXT_VISIT)
    await world.handle(_completed())
    assert world.pending() == []


# --- 가족 묶음 ------------------------------------------------------------------------------------------------------

FAMILY = (101, 102)


def _pair(cls, **overrides):
    """두 마리를 한 번에 다룬 명령이 낸 이벤트 둘 — 방문 7(101)·8(102), 같은 보호자·같은 시각."""
    return (_event(cls, visit_id=7, pet_id=101, family_pet_ids=FAMILY, **overrides),
            _event(cls, visit_id=8, pet_id=102, family_pet_ids=FAMILY, **overrides))


@pytest.mark.parametrize("cls, extra, kinds", [
    (VisitReserved, {}, [CONFIRM, REMINDER]),
    (VisitRescheduled, {"previous_starts_at": kst(10, 15, 14)}, [REMINDER, CHANGE]),
    (VisitCanceled, {"reason": "shop_reason"}, [CANCEL]),
])
async def test_가족_묶음은_둘째_이벤트에_줄을_만들지_않고_pet_ids_에_아이들을_싣는다(cls, extra, kinds):
    world = _World()
    for event in _pair(cls, **extra):
        await world.handle(event)
    assert [k for k, _ in world.pending(7)] == kinds and world.pending(8) == []
    assert all(world.only(kind).variables["pet_ids"] == "101,102" for kind in kinds)


async def test_묶음_가운데_한_마리만_취소하면_cancel_은_그_아이_이름으로_가고_묶음의_줄은_남는다():
    world = _World()
    for event in _pair(VisitReserved):
        await world.handle(event)
    await world.handle(_event(VisitCanceled, visit_id=8, pet_id=102, family_pet_ids=(102,), reason="shop_reason"))
    assert [k for k, _ in world.pending(7)] == [CONFIRM, REMINDER]
    assert world.pending(8) == [(CANCEL, NOW)]
    assert world.only(CANCEL).variables["pet_ids"] == "102"
    assert world.only(REMINDER).variables["pet_ids"] == "101"


async def test_pet_ids_는_묶음이_비면_자기_아이_아이가_없으면_빈_문자열이다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
    await world.handle(_event(VisitReserved, visit_id=8, pet_id=None, starts_at=MOVED))
    by_visit = {}
    for m in world.messages.rows.values():
        by_visit.setdefault(m.visit_id, []).append(m.variables["pet_ids"])
    assert by_visit == {7: ["101", "101"], 8: ["", ""]}


async def test_같은_보호자라도_시각이_다르면_따로_만든다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
    await world.handle(_event(VisitReserved, visit_id=8, pet_id=102, starts_at=MOVED))
    assert [k for k, _ in world.pending(7)] == [CONFIRM, REMINDER] == [k for k, _ in world.pending(8)]


# --- 가족 묶음: 뒤늦게 온 아이를 더한다 (설계 2026-11-10 3.1) ---------------------------------------------------------

def _set_status(world, row, status):
    world.messages.rows[row.id] = replace(row, status=status)


def _scheduled(world, kind):
    return sorted((m for m in world.messages.rows.values() if m.kind == kind and m.status == SCHEDULED),
                  key=lambda m: m.visit_id)


async def test_묶음의_둘째_이벤트는_방문_짝을_채운다():
    world = _World()
    for event in _pair(VisitReserved):
        await world.handle(event)
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"], reminder.variables["pet_visits"]) == (
        7, "101,102", "101:7,102:8")
    assert world.only(CONFIRM).variables["pet_visits"] == "101:7,102:8"


async def test_나중에_같은_시각에_따로_예약한_아이는_대기_중인_reminder_에_이름이_더해진다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
    _set_status(world, world.only(CONFIRM), SENT)
    await world.handle(_event(VisitReserved, visit_id=8, pet_id=102))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.pet_id, reminder.variables["pet_ids"], reminder.variables["pet_visits"]) == (
        7, 101, "101,102", "101:7,102:8")
    assert world.pending(8) == [(CONFIRM, NOW)]   # 자기 접수 안내는 따로 간다


async def test_다른_시각에서_옮겨_온_아이는_reminder_에_더해지고_change_는_따로_한_통이다():
    world = _World()
    for event in _pair(VisitRescheduled, previous_starts_at=kst(10, 15, 14)):
        await world.handle(event)
    await world.handle(_event(VisitRescheduled, visit_id=9, pet_id=103, previous_starts_at=kst(10, 17, 14)))
    assert world.only(REMINDER).variables["pet_ids"] == "101,102,103"
    assert [(m.visit_id, m.variables["pet_ids"], m.variables["previous_starts_at"]) for m in _scheduled(world, CHANGE)] == [
        (7, "101,102", _iso(kst(10, 15, 14))), (9, "103", _iso(kst(10, 17, 14)))]


async def test_옛_시각이_같은_change_에는_더한다():
    world = _World()
    for event in _pair(VisitRescheduled, previous_starts_at=kst(10, 15, 14)):
        await world.handle(event)
    await world.handle(_event(VisitRescheduled, visit_id=9, pet_id=103, previous_starts_at=kst(10, 15, 14)))
    assert [(m.visit_id, m.variables["pet_ids"]) for m in _scheduled(world, CHANGE)] == [(7, "101,102,103")]


async def test_보호자만의_방문에_달린_줄에는_더하지_않는다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=None))
    await world.handle(_event(VisitReserved, visit_id=8, pet_id=101))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"], reminder.variables["pet_visits"]) == (7, "", "")


async def test_보호자만의_방문이_아이_묶음에_오면_아무것도_바꾸지_않는다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
    await world.handle(_event(VisitReserved, visit_id=8, pet_id=None))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"], reminder.variables["pet_visits"]) == (7, "101", "101:7")


async def test_sending_중인_묶음_줄에는_더하지_않고_건너뛴다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
    _set_status(world, world.only(REMINDER), SENDING)
    await world.handle(_event(VisitReserved, visit_id=8, pet_id=102))
    [reminder] = [m for m in world.messages.rows.values() if m.kind == REMINDER]
    assert (reminder.status, reminder.variables["pet_ids"]) == (SENDING, "101")


async def test_다른_시각에서_온_아이는_그_시각의_reminder_에_들어간다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=101))
    await world.handle(_event(VisitRescheduled, visit_id=8, pet_id=102, previous_starts_at=MOVED))
    assert [(m.visit_id, m.variables["pet_ids"]) for m in _scheduled(world, REMINDER)] == [(7, "101,102")]


# --- 가족 묶음: 빠진 아이를 빼고 줄을 옮긴다 (설계 2026-11-10 3.1) ---------------------------------------------------

REMIND_AT = kst(10, 15, 18)


async def _booked_pair() -> _World:
    world = _World()
    for event in _pair(VisitReserved):
        await world.handle(event)
    return world


def _of(world, kind):
    return sorted((m for m in world.messages.rows.values() if m.kind == kind), key=lambda m: m.id)


def _one(cls, visit_id, pet_id, **overrides):
    """한 마리만 다룬 명령의 이벤트."""
    return _event(cls, visit_id=visit_id, pet_id=pet_id, family_pet_ids=(pet_id,), **overrides)


async def test_둘_다_취소하면_reminder_는_제자리에서_취소되고_cancel_은_두_이름_한_통이다():
    world = await _booked_pair()
    for event in _pair(VisitCanceled, reason="shop_reason"):
        await world.handle(event)
    assert [(m.visit_id, m.status, m.canceled_reason) for m in _of(world, REMINDER)] == [(7, CANCELED, "visit_canceled")]
    cancel = world.only(CANCEL)
    assert (cancel.visit_id, cancel.variables["pet_ids"]) == (7, "101,102")
    assert world.rows(8) == []


async def test_둘_다_옮기면_옛_reminder_는_제자리에서_취소되고_새_줄은_한_통씩이다():
    world = await _booked_pair()
    for event in _pair(VisitRescheduled, starts_at=MOVED, previous_starts_at=STARTS):
        await world.handle(event)
    assert [(m.visit_id, m.status, m.canceled_reason, m.variables["pet_ids"]) for m in _of(world, REMINDER)] == [
        (7, CANCELED, "rescheduled", "101,102"), (7, SCHEDULED, None, "101,102")]
    assert [(m.visit_id, m.variables["pet_ids"]) for m in _of(world, CHANGE)] == [(7, "101,102")]


async def test_줄이_달린_아이만_취소하면_reminder_는_남은_아이의_방문으로_옮겨진다():
    world = await _booked_pair()
    await world.handle(_one(VisitCanceled, 7, 101, reason="shop_reason"))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.pet_id, reminder.variables["pet_ids"], reminder.variables["pet_visits"]) == (
        8, 102, "102", "102:8")
    assert reminder.scheduled_at == REMIND_AT
    assert world.pending(7) == [(CANCEL, NOW)]
    assert world.only(CANCEL).variables["pet_ids"] == "101"


async def test_다른_아이만_취소하면_reminder_에서_그_이름만_빠진다():
    world = await _booked_pair()
    await world.handle(_one(VisitCanceled, 8, 102, reason="customer_request"))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"], reminder.variables["pet_visits"]) == (7, "101", "101:7")


async def test_한_마리만_옮기면_옛_시각_reminder_에서_빠지고_새_시각에_자기_reminder_가_생긴다():
    world = await _booked_pair()
    await world.handle(_one(VisitRescheduled, 8, 102, starts_at=MOVED, previous_starts_at=STARTS))
    assert [(m.visit_id, m.variables["pet_ids"], m.variables["starts_at"]) for m in _scheduled(world, REMINDER)] == [
        (7, "101", _iso(STARTS)), (8, "102", _iso(MOVED))]
    assert [(m.visit_id, m.variables["pet_ids"]) for m in _scheduled(world, CHANGE)] == [(8, "102")]


async def test_줄이_달린_아이만_옮기면_옛_시각_reminder_는_남은_아이의_방문으로_가고_자기_방문에_새_줄이_생긴다():
    world = await _booked_pair()
    await world.handle(_one(VisitRescheduled, 7, 101, starts_at=MOVED, previous_starts_at=STARTS))
    assert [(m.visit_id, m.variables["pet_ids"], m.variables["starts_at"]) for m in _scheduled(world, REMINDER)] == [
        (7, "101", _iso(MOVED)), (8, "102", _iso(STARTS))]


async def test_옮겼다가_원래_시각으로_돌아오면_한_통_두_이름이다():
    world = await _booked_pair()
    await world.handle(_one(VisitRescheduled, 8, 102, starts_at=MOVED, previous_starts_at=STARTS))
    await world.handle(_one(VisitRescheduled, 8, 102, starts_at=STARTS, previous_starts_at=MOVED))
    assert [(m.visit_id, m.variables["pet_ids"]) for m in _scheduled(world, REMINDER)] == [(7, "101,102")]
    assert [(m.status, m.canceled_reason) for m in _of(world, REMINDER) if m.visit_id == 8] == [
        (CANCELED, "rescheduled")]


async def test_함께_완료한_뒤_줄이_달린_아이만_되돌리면_next_visit_은_남은_아이로_옮겨진다():
    world = _World()
    for event in _pair(VisitClosed, outcome="completed", previous_completed_at=None):
        await world.handle(event)
    await world.handle(_one(VisitReserved, 7, 101, revived=True))
    proposal = world.only(NEXT_VISIT)
    assert (proposal.visit_id, proposal.pet_id, proposal.variables["pet_ids"]) == (8, 102, "102")


async def test_함께_완료한_뒤_다른_아이만_되돌리면_next_visit_에서_그_이름만_빠진다():
    world = _World()
    for event in _pair(VisitClosed, outcome="completed", previous_completed_at=None):
        await world.handle(event)
    await world.handle(_one(VisitReserved, 8, 102, revived=True))
    proposal = world.only(NEXT_VISIT)
    assert (proposal.visit_id, proposal.variables["pet_ids"]) == (7, "101")


async def test_취소한_아이를_되돌리면_reminder_에_다시_들어간다():
    world = await _booked_pair()
    await world.handle(_one(VisitCanceled, 8, 102, reason="customer_request"))
    await world.handle(_one(VisitReserved, 8, 102, revived=True))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"]) == (7, "101,102")


def _trio(cls, **overrides):
    family = (101, 102, 103)
    return [_event(cls, visit_id=7 + i, pet_id=pet, family_pet_ids=family, **overrides) for i, pet in enumerate(family)]


async def test_세_마리에서_둘을_한_명령으로_취소하면_reminder_는_남은_하나의_방문에_달린다():
    world = _World()
    for event in _trio(VisitReserved):
        await world.handle(event)
    for visit_id, pet_id in ((7, 101), (8, 102)):
        await world.handle(_event(VisitCanceled, visit_id=visit_id, pet_id=pet_id, family_pet_ids=(101, 102),
                                  reason="customer_request"))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.pet_id, reminder.variables["pet_ids"]) == (9, 103, "103")


async def test_세_마리가_한_마리씩_빠지면_마지막에_취소된다():
    world = _World()
    for event in _trio(VisitReserved):
        await world.handle(event)
    await world.handle(_one(VisitCanceled, 7, 101, reason="customer_request"))
    assert (world.only(REMINDER).visit_id, world.only(REMINDER).variables["pet_ids"]) == (8, "102,103")
    await world.handle(_one(VisitCanceled, 8, 102, reason="customer_request"))
    assert (world.only(REMINDER).visit_id, world.only(REMINDER).variables["pet_ids"]) == (9, "103")
    await world.handle(_one(VisitCanceled, 9, 103, reason="customer_request"))
    assert [(m.visit_id, m.status, m.canceled_reason) for m in _of(world, REMINDER)] == [(9, CANCELED, "visit_canceled")]


def _legacy_reminder(world):
    """pet_visits 칸이 생기기 전에 만들어진 묶음 줄 — 방문 7 에 달려 있고 둘째 아이의 방문을 모른다."""
    world.messages.rows[50] = message(
        id=50, visit_id=7, pet_id=101, kind=REMINDER, scheduled_at=REMIND_AT,
        variables={"starts_at": _iso(STARTS), "pet_ids": "101,102"})


async def test_pet_visits_가_없는_옛_줄은_취소에서는_이름만_빼고_제자리다():
    world = _World()
    _legacy_reminder(world)
    await world.handle(_one(VisitCanceled, 7, 101, reason="customer_request"))
    row = world.messages.rows[50]
    assert (row.visit_id, row.status, row.variables["pet_ids"]) == (7, SCHEDULED, "102")


async def test_pet_visits_가_없는_옛_줄은_시각_변경에서는_지금처럼_취소된다():
    world = _World()
    _legacy_reminder(world)
    await world.handle(_one(VisitRescheduled, 7, 101, starts_at=MOVED, previous_starts_at=STARTS))
    assert (world.messages.rows[50].status, world.messages.rows[50].canceled_reason) == (CANCELED, "rescheduled")
    assert [(m.visit_id, m.variables["pet_ids"], m.variables["starts_at"]) for m in _scheduled(world, REMINDER)] == [
        (7, "101", _iso(MOVED))]


async def test_옮길_방문에_재발송_줄이_대기_중이면_취소에서는_제자리에_둔다():
    world = await _booked_pair()
    bundle = world.only(REMINDER)
    world.messages.rows[60] = message(
        id=60, visit_id=8, pet_id=102, kind=REMINDER, scheduled_at=NOW, requested_by_member_id=11,
        variables={"starts_at": _iso(kst(10, 9, 14)), "pet_ids": "102"})
    await world.handle(_one(VisitCanceled, 7, 101, reason="customer_request"))
    after = world.messages.rows[bundle.id]
    assert (after.visit_id, after.status, after.variables["pet_ids"]) == (7, SCHEDULED, "102")


async def test_재발송으로_만든_묶음_줄에서도_이름이_빠진다():
    world = await _booked_pair()
    sent = world.only(REMINDER)
    _set_status(world, sent, SENT)
    world.messages.rows[61] = replace(sent, id=61, status=SCHEDULED, scheduled_at=NOW, requested_by_member_id=11)
    await world.handle(_one(VisitCanceled, 8, 102, reason="customer_request"))
    assert world.messages.rows[61].variables["pet_ids"] == "101"
    assert world.messages.rows[sent.id].variables["pet_ids"] == "101,102"   # 나간 줄은 그대로다


async def test_sending_중인_묶음_줄은_다른_아이가_빠져도_그대로다():
    world = await _booked_pair()
    reminder = world.only(REMINDER)
    _set_status(world, reminder, SENDING)
    await world.handle(_one(VisitCanceled, 8, 102, reason="customer_request"))
    after = world.messages.rows[reminder.id]
    assert (after.status, after.variables["pet_ids"]) == (SENDING, "101,102")


async def test_보호자만의_방문을_취소하면_지금처럼_그_방문의_줄을_거둔다():
    world = _World()
    await world.handle(_event(VisitReserved, visit_id=7, pet_id=None))
    await world.handle(_event(VisitCanceled, visit_id=7, pet_id=None, reason="customer_request"))
    assert [(k, s, r) for k, s, _, r in world.rows(7)] == [
        (CONFIRM, CANCELED, "visit_canceled"), (REMINDER, CANCELED, "visit_canceled")]


async def test_반려동물과_시각을_함께_바꾼_방문은_옛_시각_묶음에서_원래_아이가_빠진다():
    """수정 화면에서 아이와 시각을 한 번에 바꾸면 이벤트의 pet_id 는 새 아이다 — 떠나는 아이는 줄의 방문 짝으로 찾는다."""
    world = await _booked_pair()
    await world.handle(_one(VisitRescheduled, 8, 103, starts_at=MOVED, previous_starts_at=STARTS))
    assert [(m.visit_id, m.variables["pet_ids"], m.variables["starts_at"]) for m in _scheduled(world, REMINDER)] == [
        (7, "101", _iso(STARTS)), (8, "103", _iso(MOVED))]


async def test_줄이_달린_방문의_반려동물과_시각을_함께_바꾸면_묶음_줄은_남은_아이의_방문으로_간다():
    world = await _booked_pair()
    await world.handle(_one(VisitRescheduled, 7, 103, starts_at=MOVED, previous_starts_at=STARTS))
    assert [(m.visit_id, m.pet_id, m.variables["pet_ids"], m.variables["starts_at"])
            for m in _scheduled(world, REMINDER)] == [(7, 103, "103", _iso(MOVED)), (8, 102, "102", _iso(STARTS))]


async def test_반려동물만_바꾼_뒤_취소해도_묶음에서_그_방문의_원래_아이가_빠진다():
    world = await _booked_pair()
    await world.handle(_one(VisitCanceled, 8, 103, reason="customer_request"))   # 방문 8 의 아이가 그사이 103 으로 바뀌었다
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"]) == (7, "101")


async def test_노쇼도_묶음에서_그_아이만_뺀다():
    world = await _booked_pair()
    await world.handle(_one(VisitClosed, 7, 101, outcome="no_show", previous_completed_at=None))
    reminder = world.only(REMINDER)
    assert (reminder.visit_id, reminder.variables["pet_ids"]) == (8, "102")


# --- 알림장 발급 ----------------------------------------------------------------------------------------------------

async def test_알림장을_보내면_report_줄에_주소와_기간이_든다():
    world = _World()
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=kst(11, 13, 0)))
    assert world.pending() == [(REPORT, NOW)]
    assert world.only(REPORT).variables == {"starts_at": _iso(STARTS), "url": URL, "expires_at": _iso(kst(11, 13, 0)),
                                            "pet_ids": "101", "pet_visits": "101:7"}


async def test_무기한_링크의_expires_at_은_빈_문자열이다():
    world = _World()
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    assert world.only(REPORT).variables["expires_at"] == ""


async def test_같은_주소를_이미_보냈으면_만들지_않고_다른_주소면_다시_만든다():
    world = _World()
    world.delivered(REPORT, url=URL)
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    assert world.pending() == []
    await world.handle(_event(VisitReportIssued, url=OTHER_URL, expires_at=None))
    assert world.pending() == [(REPORT, NOW)]
    assert world.only(REPORT).variables["url"] == OTHER_URL


async def test_링크를_끊으면_아직_안_나간_report_줄만_report_revoked_로_취소한다():
    world = _World()
    await world.handle(_event(VisitReserved))
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    await world.handle(_event(VisitReportRevoked))
    assert world.rows() == [
        (CONFIRM, SCHEDULED, NOW, None), (REMINDER, SCHEDULED, kst(10, 15, 18), None),
        (REPORT, CANCELED, NOW, "report_revoked"),
    ]
    assert ("cancel_pending", 7, "report_revoked") in world.journal


async def test_끊기는_연동_안_된_매장에서는_아무것도_하지_않는다():
    world = _World()
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    world.channels.rows[1] = channel(status=UNLINKED)
    await world.handle(_event(VisitReportRevoked))
    assert world.pending() == [(REPORT, NOW)]


@pytest.mark.parametrize("how", ["setting_off", "template_pending"])
async def test_알림장_안내는_설정과_템플릿을_본다(how):
    world = _World(report_enabled=False) if how == "setting_off" else _World()
    if how == "template_pending":
        world.templates.rows[(1, REPORT)] = template(kind=REPORT, status=PENDING)
    await world.handle(_event(VisitReportIssued, url=URL, expires_at=None))
    assert world.pending() == []


async def test_되돌리면_대기_중인_next_visit_은_reverted_로_취소되고_다시_완료할_수_있다():
    """완료 → 되돌리기 → 다시 완료가 부분 유일 색인(같은 방문·종류의 대기 줄 하나)에 막혀 409 가 되지 않는다."""
    world = _World()
    await world.handle(_completed())
    assert world.pending() == [(NEXT_VISIT, kst(11, 11, 18))]

    await world.handle(_event(VisitReserved, revived=True))

    assert [(k, s, r) for k, s, _, r in world.rows()] == [(NEXT_VISIT, CANCELED, "reverted"), (REMINDER, SCHEDULED, None)]
    await world.handle(_completed())
    assert [(k, s) for k, s, *_ in world.rows() if k == NEXT_VISIT] == [(NEXT_VISIT, CANCELED), (NEXT_VISIT, SCHEDULED)]


async def test_두_마리를_함께_완료하면_next_visit_은_한_통이고_pet_ids_에_둘이_실린다():
    world = _World()
    await world.handle(_completed(visit_id=7, pet_id=101, family_pet_ids=(101, 102)))
    await world.handle(_completed(visit_id=8, pet_id=102, family_pet_ids=(101, 102)))

    rows = [m for m in world.messages.rows.values() if m.kind == NEXT_VISIT]
    assert len(rows) == 1 and (rows[0].visit_id, rows[0].variables["pet_ids"]) == (7, "101,102")


async def test_함께_완료한_둘째_아이의_주기가_더_짧으면_묶음의_한_통을_그만큼_당긴다():
    world = _World()
    await world.handle(_completed(visit_id=7, pet_id=101, family_pet_ids=(101, 102), cycle_weeks=6,
                                  cycle_source="computed"))
    await world.handle(_completed(visit_id=8, pet_id=102, family_pet_ids=(101, 102), cycle_weeks=3,
                                  cycle_source="manual"))
    assert world.pending() == [(NEXT_VISIT, kst(11, 4, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "3"


async def test_함께_완료한_둘째_아이의_주기가_더_길면_묶음의_한_통은_그대로다():
    world = _World()
    await world.handle(_completed(visit_id=7, pet_id=101, family_pet_ids=(101, 102), cycle_weeks=3,
                                  cycle_source="computed"))
    await world.handle(_completed(visit_id=8, pet_id=102, family_pet_ids=(101, 102), cycle_weeks=8,
                                  cycle_source="manual"))
    assert world.pending() == [(NEXT_VISIT, kst(11, 4, 18))]
    assert world.only(NEXT_VISIT).variables["interval_weeks"] == "3"
