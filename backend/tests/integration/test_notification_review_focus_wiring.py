"""사람이 먼저 부딪힐 다섯을 실제 배선(구독자·디스패처·테스트 DB)으로 고정한다 — 가족 묶음은 한 통, 링크를 끊으면
알림장 알림톡 취소, 바뀐 번호로 간다, 멈췄다 돌아온 디스패처, 연달아 두 번 바꾼 예약.

채널·설정·템플릿은 SQL 로 넣고 디스패처는 FakeGateway 로 run_once 를 직접 돈다. 번호는 끝 네 자리만 비교하고 찍지 않는다.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.dependencies.dispatcher_provider import build_dispatcher
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


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


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
