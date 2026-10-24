"""visit 의 요청이 실제 배선(main.py 의 subscribe, 요청의 세션)으로 notification_messages 에 줄을 남기는지 본다.

채널·설정·템플릿 줄은 SQL 로 직접 넣는다(온보딩 API 는 작업 8). 알림장 주소는 응답·로그에 찍지 않는다 — 비어 있지
않은지만 본다.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from notification.domain.value_objects.message_kind import KINDS
from tests.integration.support import bearer, error_of, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


def _utc_iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


async def _link(wired, shop_id: int) -> None:
    """연동을 마친 매장 — 채널 linked, 설정 기본값, 템플릿 6종 approved."""
    await wired.execute(
        "INSERT INTO notification_channels (shop_id, status, provider, provider_channel_id, linked_at) "
        "VALUES (:shop_id, 'linked', 'solapi', 'KA01PF0001', now())", shop_id=shop_id)
    await wired.execute("INSERT INTO notification_settings (shop_id) VALUES (:shop_id)", shop_id=shop_id)
    for i, kind in enumerate(KINDS, start=1):
        await wired.execute(
            "INSERT INTO notification_templates (shop_id, kind, text_version, provider_template_id, status, "
            "requested_at) VALUES (:shop_id, :kind, 1, :template_id, 'approved', now())",
            shop_id=shop_id, kind=kind, template_id=f"KA01TP000{i}")


async def _shop(wired, linked=True):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    if linked:
        await _link(wired, shop_id)
    headers = bearer(owner["access_token"])
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET}, headers=headers)
    assert response.status_code == 201, response.text
    body = response.json()
    return shop_id, headers, body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _book(wired, shop_id, headers, customer_id, pet_id, starts_at: datetime):
    return await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": starts_at.isoformat()})


async def _booked(wired, shop_id, headers, customer_id, pet_id, starts_at: datetime) -> dict:
    booked = await _book(wired, shop_id, headers, customer_id, pet_id, starts_at)
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]


async def _transition(wired, shop_id, headers, visit_id, action, **extra) -> None:
    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                    json={"visit_ids": [visit_id], "action": action, **extra})
    assert response.status_code == 200, response.text


async def _messages(wired, visit_id: int) -> list[dict]:
    """id 순. 주소는 고르지 않는다 — 있는지(has_url)만."""
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, scheduled_at, canceled_reason, requested_by_member_id, "
            "variables->>'starts_at' AS starts_at, variables->>'previous_starts_at' AS previous_starts_at, "
            "length(variables->>'url') > 0 AS has_url "
            "FROM notification_messages WHERE visit_id = :visit_id ORDER BY id"), {"visit_id": visit_id})
        return [dict(row._mapping) for row in rows]


def _brief(rows: list[dict]) -> list[tuple]:
    return [(r["kind"], r["status"], r["canceled_reason"]) for r in rows]


def _near_now(at: datetime) -> bool:
    return abs(datetime.now(timezone.utc) - at) < timedelta(minutes=1)


async def test_예약을_등록하면_confirm_은_지금_reminder_는_전날_18시_KST_의_줄이_생긴다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    starts_at = _at(3, 14)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, starts_at)

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [("confirm", "scheduled", None), ("reminder", "scheduled", None)]
    assert _near_now(rows[0]["scheduled_at"])
    assert rows[1]["scheduled_at"] == _at(2, 18)
    assert all(r["starts_at"] == _utc_iso(starts_at) and r["requested_by_member_id"] is None for r in rows)


async def test_일정을_바꾸면_옛_reminder_는_rescheduled_로_취소되고_새_reminder_와_change_가_생긴다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    moved = await wired.api.put(
        f"/v1/shops/{shop_id}/visits/{visit['visit_id']}", headers=headers,
        json={"starts_at": _at(5, 16).isoformat(), "pet_id": pet_id, "duration_minutes": visit["duration_minutes"],
              "menu_ids": [], "memo": None})
    assert moved.status_code == 200, moved.text

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [
        ("confirm", "scheduled", None), ("reminder", "canceled", "rescheduled"),
        ("reminder", "scheduled", None), ("change", "scheduled", None),
    ]
    assert rows[2]["scheduled_at"] == _at(4, 18)
    assert (rows[3]["previous_starts_at"], rows[3]["starts_at"]) == (_utc_iso(_at(3, 14)), _utc_iso(_at(5, 16)))
    assert _near_now(rows[3]["scheduled_at"])


async def test_매장_사정으로_취소하면_대기_줄이_전부_취소되고_cancel_줄이_생긴다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    await _transition(wired, shop_id, headers, visit["visit_id"], "cancel", cancel_reason="shop_reason")

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [
        ("confirm", "canceled", "visit_canceled"), ("reminder", "canceled", "visit_canceled"),
        ("cancel", "scheduled", None),
    ]


async def test_같은_예약을_두_번_등록하면_둘째는_409_이고_메시지_줄은_그대로다(wired):
    """방문 저장이 롤백되면 구독자가 쓴 줄도 함께 사라진다(설계 3.2)."""
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    again = await _book(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    assert error_of(again) == (409, "VISIT_DUPLICATE")

    rows = await _messages(wired, visit["visit_id"])
    assert _brief(rows) == [("confirm", "scheduled", None), ("reminder", "scheduled", None)]
    async with wired.engine.connect() as conn:
        total = (await conn.execute(text("SELECT count(*) FROM notification_messages"))).scalar_one()
    assert total == 2


async def test_연동하지_않은_매장은_줄이_없다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired, linked=False)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(3, 14))
    await _transition(wired, shop_id, headers, visit["visit_id"], "cancel", cancel_reason="shop_reason")
    assert await _messages(wired, visit["visit_id"]) == []


async def test_알림장을_보내면_report_줄에_주소가_있고_같은_링크로_다시_보내면_줄이_늘지_않는다(wired):
    shop_id, headers, customer_id, pet_id = await _shop(wired)
    visit = await _booked(wired, shop_id, headers, customer_id, pet_id, _at(-1, 11))   # 어제 — 리마인드는 지났다
    visit_id = visit["visit_id"]
    await _transition(wired, shop_id, headers, visit_id, "start")
    written = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                  json={"care_note": "눈물 자국을 닦았어요", "media": []})
    assert written.status_code == 200, written.text
    await _transition(wired, shop_id, headers, visit_id, "complete")
    report = f"/v1/shops/{shop_id}/visits/{visit_id}/report"
    sent = await wired.api.put(report, headers=headers, json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text

    rows = await _messages(wired, visit_id)
    assert _brief(rows) == [("confirm", "scheduled", None), ("report", "scheduled", None)]
    assert rows[1]["has_url"] is True and _near_now(rows[1]["scheduled_at"])

    again = await wired.api.put(report, headers=headers, json={"hidden_media_ids": []})
    assert again.status_code == 200, again.text
    assert _brief(await _messages(wired, visit_id)) == _brief(rows)
