"""디스패처를 실제 저장소·실제 허브 포트(main.py 가 꽂은 것)·테스트 DB 로 돌린다. 게이트웨이는 Fake.

매장·고객·반려동물·방문은 API 로, 채널·설정·템플릿과 직접 넣는 메시지 줄은 SQL 로. 번호·이름·주소는 로그에 없어야 한다.
"""
import asyncio
import logging
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.services import dispatcher_wakeup
from notification.dependencies import dispatcher_provider as provider
from notification.dependencies.dispatcher_provider import build_dispatcher
from notification.domain.value_objects.message_kind import KINDS
from tests.integration.support import bearer, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
NAME, PHONE = "김민지", "01012345678"
CUSTOMER = {"name": NAME, "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


async def _link(wired, shop_id: int) -> None:
    await wired.execute(
        "INSERT INTO notification_channels (shop_id, status, provider, provider_channel_id, linked_at) "
        "VALUES (:shop_id, 'linked', 'solapi', 'KA01PF0001', now())", shop_id=shop_id)
    await wired.execute("INSERT INTO notification_settings (shop_id) VALUES (:shop_id)", shop_id=shop_id)
    for i, kind in enumerate(KINDS, start=1):
        await wired.execute(
            "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, "
            "requested_at) VALUES (:shop_id, :kind, 1, :template_id, 'approved', now())",
            shop_id=shop_id, kind=kind, template_id=f"KA01TP000{i}")


async def _shop(wired, customer=CUSTOMER):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await _link(wired, shop_id)
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": customer, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    return shop_id, headers, body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _booked(wired, shop_id, headers, customer_id, pet_id, starts_at: datetime) -> int:
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _insert(wired, shop_id, customer_id, visit_id, kind="confirm", status="scheduled", **columns) -> None:
    """줄을 직접 넣는다. starts_at 은 내일 14시."""
    values = {"shop_id": shop_id, "customer_id": customer_id, "visit_id": visit_id, "kind": kind, "status": status,
              "scheduled_at": _now() - timedelta(seconds=1), "starts_at": _at(1, 14).isoformat(), **columns}
    columns_sql = ", ".join(k for k in values if k != "starts_at")
    params_sql = ", ".join(f":{k}" for k in values if k != "starts_at")
    await wired.execute(
        f"INSERT INTO notification_messages ({columns_sql}, variables) "
        f"VALUES ({params_sql}, jsonb_build_object('starts_at', CAST(:starts_at AS text)))", **values)


async def _rows(wired, shop_id: int) -> list[SimpleNamespace]:
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT id, kind, status, attempts, canceled_reason, provider_message_id, channel_used, error_code, "
            "error_kind, scheduled_at FROM notification_messages WHERE shop_id = :shop_id ORDER BY id"),
            {"shop_id": shop_id})
        return [SimpleNamespace(**row._mapping) for row in rows]


def _sessions(wired):
    return async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)


async def _run_once(wired, gateway: FakeGateway, now: datetime):
    async with _sessions(wired)() as session:
        return await build_dispatcher(session, gateway=gateway, now=lambda: now).run_once()


async def test_예약_접수_줄은_accepted_가_되고_다음_루프에서_sent_가_된다(wired, caplog):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit_id = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    gateway = FakeGateway()

    with caplog.at_level(logging.INFO, logger="notification.dispatcher"):
        first = await _run_once(wired, gateway, _now())
        confirm, reminder = await _rows(wired, shop_id)
        assert (first.claimed, first.sent) == (1, 1)
        assert (confirm.kind, confirm.status, confirm.provider_message_id, confirm.attempts) == (
            "confirm", "accepted", "fake-1", 1)
        assert (reminder.kind, reminder.status) == ("reminder", "scheduled")

        second = await _run_once(wired, gateway, _now() + timedelta(seconds=6))
        confirm, _ = await _rows(wired, shop_id)
        assert (second.polled, confirm.status, confirm.channel_used) == (1, "sent", "alimtalk")

    [outgoing] = gateway.sent_messages
    assert (outgoing.to, outgoing.provider_channel_id, outgoing.provider_template_id) == (PHONE, "KA01PF0001", "KA01TP0001")
    assert outgoing.variables["대상"] == "콩이" and outgoing.variables["매장명"] == "Hiss Haus"
    assert outgoing.fallback is None
    assert any("accepted" in r.getMessage() for r in caplog.records)
    for secret in (PHONE, "1234-5678", NAME, "콩이"):
        assert secret not in caplog.text


async def test_번호_끝이_0000_이면_업체가_영구_실패로_답한다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired, {**CUSTOMER, "phone": "010-1234-0000"})
    await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    gateway = FakeGateway()

    await _run_once(wired, gateway, _now())
    await _run_once(wired, gateway, _now() + timedelta(seconds=6))

    confirm, _ = await _rows(wired, shop_id)
    assert (confirm.status, confirm.error_code, confirm.error_kind) == ("failed", "3104", "permanent")


async def test_보내는_순간_고객이_익명화되어_있으면_anonymized_로_취소한다(wired):
    shop_id, headers, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1)
    deleted = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text
    gateway = FakeGateway()

    await _run_once(wired, gateway, _now())

    [row] = await _rows(wired, shop_id)
    assert (row.status, row.canceled_reason) == ("canceled", "anonymized")
    assert gateway.sent_messages == []


async def test_두_디스패처가_동시에_돌아도_한_줄을_둘이_보내지_않는다(wired):
    shop_id, _, customer_id, _ = await _shop(wired)
    for visit_id in (1, 2, 3):
        await _insert(wired, shop_id, customer_id, visit_id)
    gateway = FakeGateway()
    now = _now()

    async with _sessions(wired)() as first, _sessions(wired)() as second:
        reports = await asyncio.gather(
            build_dispatcher(first, gateway=gateway, now=lambda: now).run_once(),
            build_dispatcher(second, gateway=gateway, now=lambda: now).run_once(),
        )

    assert sum(r.sent for r in reports) == 3 and len(gateway.sent_messages) == 3
    assert [r.status for r in await _rows(wired, shop_id)] == ["accepted"] * 3


async def test_5분_넘게_sending_인_줄은_되돌려_다시_보낸다(wired):
    shop_id, _, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1, status="sending", updated_at=_now() - timedelta(minutes=6))
    await _insert(wired, shop_id, customer_id, visit_id=2, status="sending", updated_at=_now() - timedelta(minutes=4))
    gateway = FakeGateway()

    report = await _run_once(wired, gateway, _now())

    stuck, fresh = await _rows(wired, shop_id)
    assert (report.recovered, report.claimed) == (1, 1)
    assert (stuck.status, stuck.attempts) == ("accepted", 2)
    assert (fresh.status, fresh.attempts) == ("sending", 0)


async def test_하루_상한에_닿으면_나머지는_1시간_뒤로_미룬다(wired, monkeypatch):
    monkeypatch.setattr(provider, "NOTIFICATION_DAILY_CAP", 1)
    shop_id, _, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1)
    await _insert(wired, shop_id, customer_id, visit_id=2)
    gateway = FakeGateway()
    now = _now()

    report = await _run_once(wired, gateway, now)

    first, second = await _rows(wired, shop_id)
    assert (report.sent, report.deferred) == (1, 1)
    assert first.status == "accepted"
    assert (second.status, second.scheduled_at) == ("scheduled", now + timedelta(hours=1))


async def test_예약을_등록하면_구독자가_디스패처를_깨운다(wired, monkeypatch):
    monkeypatch.setattr(dispatcher_wakeup, "_event", asyncio.Event())
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    assert not dispatcher_wakeup._event.is_set()

    await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))

    assert dispatcher_wakeup._event.is_set()


async def test_루프가_부르는_run_once_는_세션을_열어_조립하고_한_번_돈다(wired, monkeypatch):
    """core.database.session_scope 로 연 세션 + 프로세스의 게이트웨이(여기선 Fake 로 바꿈)."""
    gateway = FakeGateway()
    monkeypatch.setattr(provider, "get_message_gateway", lambda: gateway)
    shop_id, _, customer_id, _ = await _shop(wired)
    await _insert(wired, shop_id, customer_id, visit_id=1)

    report = await provider.run_once()

    [row] = await _rows(wired, shop_id)
    assert (report.sent, row.status, row.provider_message_id) == (1, "accepted", "fake-1")
