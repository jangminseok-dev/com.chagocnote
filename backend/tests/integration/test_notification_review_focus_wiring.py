"""사람이 먼저 부딪힐 다섯을 실제 배선(구독자·디스패처·테스트 DB)으로 고정한다 — 가족 묶음은 한 통, 링크를 끊으면
알림장 알림톡 취소, 바뀐 번호로 간다, 멈췄다 돌아온 디스패처, 연달아 두 번 바꾼 예약.

채널·설정·템플릿은 SQL 로 넣고 디스패처는 FakeGateway 로 run_once 를 직접 돈다. 번호는 끝 네 자리만 비교하고 찍지 않는다.
"""
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.pg.template_pg_repository import TemplatePgRepository
from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.ports.output.message_gateway_port import TemplateState
from notification.app.services.system_context import system_context
from notification.dependencies.dispatcher_provider import build_dispatcher
from notification.domain.services.templates import format_when
from notification.domain.value_objects.message_kind import KINDS
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
TEMPLATE = {kind: f"KA01TP000{i}" for i, kind in enumerate(KINDS, start=1)}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _at(days: int, hour: int, minute: int = 0) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=SEOUL)


def _utc_iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


async def _link(wired, shop_id: int) -> None:
    await wired.execute(
        "INSERT INTO notification_channels (shop_id, status, provider, provider_channel_id, linked_at) "
        "VALUES (:shop_id, 'linked', 'solapi', 'KA01PF0001', now())", shop_id=shop_id)
    await wired.execute("INSERT INTO notification_settings (shop_id) VALUES (:shop_id)", shop_id=shop_id)
    for kind, template_id in TEMPLATE.items():
        await wired.execute(
            "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, "
            "requested_at) VALUES (:shop_id, :kind, 1, :template_id, 'approved', now())",
            shop_id=shop_id, kind=kind, template_id=template_id)


async def _shop(wired):
    """연동한 매장과 두 마리(콩이·두부)를 둔 보호자. (shop_id, headers, customer_id, [pet_ids])"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await _link(wired, shop_id)
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    customer_id, kong = body["customer"]["customer_id"], body["pets"][0]["pet_id"]
    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers,
                                 json={**PET, "name": "두부"})
    assert added.status_code == 201, added.text
    return shop_id, headers, customer_id, [kong, added.json()["pet"]["pet_id"]]


async def _booked(wired, shop_id, headers, customer_id, pet_ids, starts_at: datetime) -> list[int]:
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": customer_id, "pet_ids": pet_ids, "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return [v["visit_id"] for v in booked.json()["visits"]]


async def _transition(wired, shop_id, headers, visit_ids, action, **extra) -> None:
    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                    json={"visit_ids": visit_ids, "action": action, **extra})
    assert response.status_code == 200, response.text


async def _rows(wired, visit_id: int) -> list[tuple]:
    """(종류, 상태, 취소 이유, pet_ids 변수) — id 순. 주소는 고르지 않는다."""
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, canceled_reason, variables->>'pet_ids' AS pet_ids "
            "FROM notification_messages WHERE visit_id = :visit_id ORDER BY id"), {"visit_id": visit_id})
        return [tuple(row) for row in rows]


async def _run_once(wired, gateway: FakeGateway, now: datetime | None = None):
    sessions = async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)
    at = now if now is not None else _now()
    async with sessions() as session:
        return await build_dispatcher(session, gateway=gateway, now=lambda: at).run_once()


def _targets(gateway: FakeGateway, kind: str) -> list[str]:
    return [m.variables["대상"] for m in gateway.sent_messages if m.provider_template_id == TEMPLATE[kind]]


# --- 1. 가족 묶음은 한 통 ----------------------------------------------------------------------------------------------

async def test_두_마리_예약은_confirm_reminder_change_가_한_통이고_대상은_두_이름이며_한_마리만_취소하면_그_아이_이름이다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    kong, dubu = await _booked(wired, shop_id, headers, customer_id, pet_ids, _at(3, 14))
    gateway = FakeGateway()
    both = ",".join(str(p) for p in sorted(pet_ids))

    assert await _rows(wired, kong) == [("confirm", "scheduled", None, both), ("reminder", "scheduled", None, both)]
    assert await _rows(wired, dubu) == []
    await _run_once(wired, gateway)
    assert _targets(gateway, "confirm") == ["콩이·두부"]

    moved = await wired.api.post(f"/v1/shops/{shop_id}/visits/reschedule", headers=headers,
                                 json={"visit_ids": [kong, dubu], "starts_at": _at(4, 15).isoformat()})
    assert moved.status_code == 200, moved.text
    changes = [r for v in (kong, dubu) for r in await _rows(wired, v) if r[0] == "change"]
    assert changes == [("change", "scheduled", None, both)]
    await _run_once(wired, gateway)
    assert _targets(gateway, "change") == ["콩이·두부"]

    await _transition(wired, shop_id, headers, [dubu], "cancel", cancel_reason="shop_reason")
    assert [r for r in await _rows(wired, dubu) if r[0] == "cancel"] == [("cancel", "scheduled", None, str(pet_ids[1]))]
    await _run_once(wired, gateway)
    assert _targets(gateway, "cancel") == ["두부"]
    assert len(gateway.sent_messages) == 3


# --- 2. 링크를 끊으면 아직 안 나간 알림장 알림톡을 취소한다 ------------------------------------------------------------

async def _reported(wired, shop_id, headers, customer_id, pet_ids) -> int:
    """어제 방문(한 마리)을 시작·기록·완료하고 알림장을 보낸다 — report 줄이 생긴다. 방문 ID."""
    [visit_id] = await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(-1, 11))
    await _transition(wired, shop_id, headers, [visit_id], "start")
    written = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                  json={"care_note": "눈물 자국을 닦았어요", "media": []})
    assert written.status_code == 200, written.text
    await _transition(wired, shop_id, headers, [visit_id], "complete")
    sent = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/report", headers=headers,
                               json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    return visit_id


async def test_디스패처가_돌기_전에_링크를_끊으면_report_는_report_revoked_로_취소되고_다시_보내면_새_줄만_나간다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    visit_id = await _reported(wired, shop_id, headers, customer_id, pet_ids)
    gateway = FakeGateway()
    report = f"/v1/shops/{shop_id}/visits/{visit_id}/report"

    revoked = await wired.api.delete(report, headers=headers)
    assert revoked.status_code == 204, revoked.text
    assert [r[:3] for r in await _rows(wired, visit_id)] == [
        ("confirm", "scheduled", None), ("report", "canceled", "report_revoked")]
    await _run_once(wired, gateway)
    assert _targets(gateway, "report") == []

    again = await wired.api.put(report, headers=headers, json={"hidden_media_ids": []})
    assert again.status_code == 200, again.text
    assert [r[:3] for r in await _rows(wired, visit_id) if r[0] == "report"] == [
        ("report", "canceled", "report_revoked"), ("report", "scheduled", None)]
    await _run_once(wired, gateway)
    assert _targets(gateway, "report") == ["콩이"]


# --- 3. 바뀐 번호로 간다 ------------------------------------------------------------------------------------------------

async def test_예약_뒤에_보호자_번호를_바꾸면_접수_안내는_바뀐_번호로_간다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(3, 14))
    changed = await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers,
                                  json={**CUSTOMER, "phone": "010-1234-4321"})
    assert changed.status_code == 200, changed.text
    gateway = FakeGateway()

    report = await _run_once(wired, gateway)

    assert report.sent == 1
    assert gateway.sent_messages[-1].to[-4:] == "4321"   # 끝 네 자리만 비교한다 — 번호를 찍지 않는다


# --- 4. 멈췄다 돌아온 디스패처 -----------------------------------------------------------------------------------------

async def _insert(wired, shop_id, customer_id, pet_id, visit_id, kind, scheduled_at, **variables) -> None:
    """줄을 직접 넣는다 — 시각을 마음대로 두려고 구독자를 거치지 않는다."""
    await wired.execute(
        "INSERT INTO notification_messages (shop_id, customer_id, pet_id, visit_id, kind, status, scheduled_at, variables) "
        "VALUES (:shop_id, :customer_id, :pet_id, :visit_id, :kind, 'scheduled', :scheduled_at, CAST(:variables AS jsonb))",
        shop_id=shop_id, customer_id=customer_id, pet_id=pet_id, visit_id=visit_id, kind=kind, scheduled_at=scheduled_at,
        variables=json.dumps({"pet_ids": str(pet_id), **variables}))


async def _status(wired, shop_id: int) -> list[tuple]:
    """(종류, 상태, 취소 이유, scheduled_at) — id 순."""
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, canceled_reason, scheduled_at FROM notification_messages "
            "WHERE shop_id = :shop_id ORDER BY id"), {"shop_id": shop_id})
        return [tuple(row) for row in rows]


async def _paused_queue(wired):
    """내일 14:00 예약의 reminder(오늘 18:00)와 완료 방문의 next_visit(4주 뒤 18:00)이 대기 중인 매장."""
    shop_id, _, customer_id, pet_ids = await _shop(wired)
    await _insert(wired, shop_id, customer_id, pet_ids[0], 1, "reminder", _at(0, 18), starts_at=_utc_iso(_at(1, 14)))
    await _insert(wired, shop_id, customer_id, pet_ids[0], 2, "next_visit", _at(28, 18),
                  starts_at=_utc_iso(_at(-1, 14)), completed_at=_utc_iso(_at(0, 11)), interval_weeks="4")
    return shop_id


async def test_멈췄다가_예약_1시간_전을_넘겨_돌아오면_reminder_는_too_late_다(wired):
    shop_id = await _paused_queue(wired)
    gateway = FakeGateway()

    await _run_once(wired, gateway, _at(1, 13, 30))

    assert await _status(wired, shop_id) == [
        ("reminder", "canceled", "too_late", _at(0, 18)), ("next_visit", "scheduled", None, _at(28, 18))]
    assert gateway.sent_messages == []


async def test_멈췄다가_밤에_돌아오면_reminder_는_다음_날_08시로_미루고_next_visit_은_그대로이며_아침에_나간다(wired):
    shop_id = await _paused_queue(wired)
    gateway = FakeGateway()

    night = await _run_once(wired, gateway, _at(0, 23))
    assert (night.claimed, night.deferred) == (1, 1)
    assert await _status(wired, shop_id) == [
        ("reminder", "scheduled", None, _at(1, 8)), ("next_visit", "scheduled", None, _at(28, 18))]

    morning = await _run_once(wired, gateway, _at(1, 8))
    assert (morning.claimed, morning.sent) == (1, 1)
    assert [r[:2] for r in await _status(wired, shop_id)] == [("reminder", "accepted"), ("next_visit", "scheduled")]
    [outgoing] = gateway.sent_messages
    assert (outgoing.provider_template_id, outgoing.variables["대상"], outgoing.variables["시각"]) == (
        TEMPLATE["reminder"], "콩이", "14:00")


# --- 5. 연달아 두 번 바꾼 예약 -----------------------------------------------------------------------------------------

async def test_연달아_두_번_바꾸면_change_는_마지막_한_통만_대기하고_이전_시각은_첫_변경_뒤_시각이다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    first, second, third = _at(3, 14), _at(4, 15), _at(5, 16)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": pet_ids[:1], "starts_at": first.isoformat()})
    assert booked.status_code == 201, booked.text
    visit = booked.json()["visits"][0]
    for starts_at in (second, third):
        moved = await wired.api.put(
            f"/v1/shops/{shop_id}/visits/{visit['visit_id']}", headers=headers,
            json={"starts_at": starts_at.isoformat(), "pet_id": pet_ids[0], "duration_minutes": visit["duration_minutes"],
                  "menu_ids": [], "memo": None})
        assert moved.status_code == 200, moved.text

    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, canceled_reason, scheduled_at, variables->>'starts_at' AS starts_at, "
            "variables->>'previous_starts_at' AS previous_starts_at "
            "FROM notification_messages WHERE visit_id = :visit_id ORDER BY id"), {"visit_id": visit["visit_id"]})
        rows = [dict(r._mapping) for r in rows]
    assert [(r["kind"], r["status"], r["canceled_reason"]) for r in rows] == [
        ("confirm", "scheduled", None),
        ("reminder", "canceled", "rescheduled"), ("reminder", "canceled", "rescheduled"), ("change", "canceled", "rescheduled"),
        ("reminder", "scheduled", None), ("change", "scheduled", None),
    ]
    reminder, change = rows[4], rows[5]
    assert (reminder["scheduled_at"], reminder["starts_at"]) == (_at(4, 18), _utc_iso(third))
    assert (change["previous_starts_at"], change["starts_at"]) == (_utc_iso(second), _utc_iso(third))

    gateway = FakeGateway()
    await _run_once(wired, gateway)

    [change_sent] = [m for m in gateway.sent_messages if m.provider_template_id == TEMPLATE["change"]]
    assert (change_sent.variables["이전일시"], change_sent.variables["일시"]) == (
        format_when(second, "Asia/Seoul"), format_when(third, "Asia/Seoul"))


# --- 6. 묶음의 아직 안 나간 알림톡은 지금 그 시각에 오는 아이들을 따라간다 (설계 2026-11-10 3.1) ---------------------

async def _listed(wired, shop_id, headers, visit_id) -> list[tuple]:
    response = await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications", headers=headers)
    assert response.status_code == 200, response.text
    return [(item["kind"], item["status"]) for item in response.json()["items"]]


async def test_묶음에서_줄이_달린_아이만_취소하면_reminder_는_남은_아이_이름으로_그_아이_방문의_내역에_있다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    kong, dubu = await _booked(wired, shop_id, headers, customer_id, pet_ids, _at(3, 14))
    gateway = FakeGateway()
    await _run_once(wired, gateway)                                   # 접수 안내가 나간다
    assert ("reminder", "scheduled") in await _listed(wired, shop_id, headers, kong)

    await _transition(wired, shop_id, headers, [kong], "cancel", cancel_reason="customer_request")

    assert ("reminder", "scheduled") in await _listed(wired, shop_id, headers, dubu)
    assert not [row for row in await _listed(wired, shop_id, headers, kong) if row[0] == "reminder"]
    assert [r for r in await _rows(wired, dubu) if r[0] == "reminder"] == [
        ("reminder", "scheduled", None, str(pet_ids[1]))]
    await _run_once(wired, gateway, now=_at(2, 18, 1))                # 전날 18:00 이 지났다
    assert _targets(gateway, "reminder") == ["두부"]


async def test_나중에_같은_시각에_따로_예약한_아이도_reminder_한_통에_실린다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    [kong] = await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(3, 14))
    gateway = FakeGateway()
    await _run_once(wired, gateway)
    [dubu] = await _booked(wired, shop_id, headers, customer_id, pet_ids[1:], _at(3, 14))

    assert [r for v in (kong, dubu) for r in await _rows(wired, v) if r[0] == "reminder"] == [
        ("reminder", "scheduled", None, ",".join(str(p) for p in sorted(pet_ids)))]
    await _run_once(wired, gateway)                                   # 두부의 접수 안내
    await _run_once(wired, gateway, now=_at(2, 18, 1))
    assert _targets(gateway, "confirm") == ["콩이", "두부"]
    assert _targets(gateway, "reminder") == ["콩이·두부"]


# --- 7. 새 판 심사 중에는 옛 판으로 계속 나간다 (설계 2026-11-10 3.2) ----------------------------------------------

class _ReviewingGateway(FakeGateway):
    """새 판(tpl-new)의 심사를 테스트가 끝낼 때까지 '심사 중'으로 답한다."""

    def __init__(self) -> None:
        super().__init__()
        self.decided = False

    async def template_state(self, provider_template_id: str) -> TemplateState:
        if provider_template_id == "tpl-new" and not self.decided:
            return TemplateState(status="pending", rejected_reason=None)
        return await super().template_state(provider_template_id)


async def test_승인된_종류를_새_판으로_재등록해도_심사_중에는_옛_판으로_나가고_승인_뒤에는_새_판으로_나간다(wired):
    shop_id, headers, customer_id, pet_ids = await _shop(wired)
    sessions = async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)
    async with sessions() as session:
        await TemplatePgRepository(session).upsert(system_context(shop_id), "confirm", 2, "tpl-new", _now())
        await session.commit()
    gateway = _ReviewingGateway()

    await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(3, 14))
    async with sessions() as session:
        await build_dispatcher(session, gateway=gateway, now=_now).refresh_templates()   # 아직 심사 중
    await _run_once(wired, gateway)
    assert [m.provider_template_id for m in gateway.sent_messages] == [TEMPLATE["confirm"]]

    gateway.decided = True
    async with sessions() as session:
        await build_dispatcher(session, gateway=gateway, now=_now).refresh_templates()
    await _booked(wired, shop_id, headers, customer_id, pet_ids[:1], _at(4, 14))
    await _run_once(wired, gateway)
    assert [m.provider_template_id for m in gateway.sent_messages] == [TEMPLATE["confirm"], "tpl-new"]
