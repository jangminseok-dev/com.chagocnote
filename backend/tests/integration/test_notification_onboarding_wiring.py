"""온보딩·설정 API 를 실제 배선(프로바이더·DB 커밋·Redis db 15·매장 접근 확인)으로 돌린다. 게이트웨이는 FakeGateway 를 꽂는다.

첫 테스트는 테넌트 격리다(하네스 규칙). 응답 어디에도 업체 ID·관리자 번호가 없어야 한다(N12).
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.app.ports.output.message_gateway_port import GatewayTransientError
from notification.dependencies.notification_wiring import get_message_gateway
from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
ADMIN_PHONE, SENDER = "01012345678", "0212345678"
TOKEN = {"search_id": "hisshaus", "admin_phone": ADMIN_PHONE, "category_code": "003001"}
LINK = {**TOKEN, "token": "000000"}
SETTINGS = {"confirm_enabled": True, "reminder_enabled": True, "report_enabled": True, "change_enabled": True,
            "next_visit_enabled": False, "reminder_time": "18:00", "next_visit_after_weeks": None,
            "next_visit_cooldown_days": 30, "sms_fallback_enabled": False}
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _install(fake: FakeGateway) -> FakeGateway:
    import main

    main.app.dependency_overrides[get_message_gateway] = lambda: fake
    return fake


@pytest.fixture
def gateway(wired):
    import main

    yield _install(FakeGateway())
    main.app.dependency_overrides.pop(get_message_gateway, None)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


def _path(shop_id: int, tail: str = "") -> str:
    return f"/v1/shops/{shop_id}/notification{tail}"


async def _owner_shop(wired, name="Hiss Haus", owner_name="사장님"):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, name, owner_name)
    return shop_id, owner, bearer(owner["access_token"])


async def _linked_shop(wired):
    shop_id, owner, headers = await _owner_shop(wired)
    assert (await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=headers)).status_code == 202
    linked = await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=headers)
    assert linked.status_code == 200, linked.text
    return shop_id, owner, headers


async def _verify_sender(wired, shop_id, headers) -> None:
    assert (await wired.api.post(_path(shop_id, "/sender/verification"), json={"phone": SENDER},
                                 headers=headers)).status_code == 202
    confirmed = await wired.api.post(_path(shop_id, "/sender"), json={"phone": SENDER, "code": "000000"},
                                     headers=headers)
    assert confirmed.status_code == 200, confirmed.text


async def _approve_templates(wired, shop_id) -> None:
    await wired.execute("UPDATE notification_templates SET status = 'approved' WHERE shop_id = :shop_id",
                        shop_id=shop_id)


async def _booked_reminder(wired, shop_id, headers, starts_at: datetime) -> int:
    """고객·반려동물을 만들고 예약해 reminder 줄을 만든다(템플릿은 approved 여야 한다). 방문 ID."""
    customer = await wired.api.post(f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET},
                                    headers=headers)
    assert customer.status_code == 201, customer.text
    body = customer.json()
    booked = await wired.api.post(
        f"/v1/shops/{shop_id}/visits", headers=headers,
        json={"customer_id": body["customer"]["customer_id"], "pet_ids": [body["pets"][0]["pet_id"]],
              "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _messages(wired, shop_id: int) -> list[tuple]:
    async with wired.engine.connect() as conn:
        rows = await conn.execute(text(
            "SELECT kind, status, canceled_reason, scheduled_at FROM notification_messages "
            "WHERE shop_id = :shop_id ORDER BY id"), {"shop_id": shop_id})
        return [tuple(row) for row in rows]


async def _channel_row(wired, shop_id: int):
    async with wired.engine.connect() as conn:
        return (await conn.execute(text(
            "SELECT status, provider_channel_id, sender_number, sms_fallback_enabled FROM notification_channels "
            "WHERE shop_id = :shop_id"), {"shop_id": shop_id})).one_or_none()


async def test_다른_매장의_여덟_경로는_전부_403_NOT_A_MEMBER_다(wired, gateway):
    """N1·N2 — A 매장 사장이 B 매장의 경로를 부른다. 업체에도 DB 에도 닿지 않는다."""
    a_shop, _, a = await _owner_shop(wired, "A 매장", "A사장")
    operator = await make_operator(wired, "운영자2")
    b_shop, _ = await shop_with_owner(wired, operator, "B 매장", "B사장")

    calls = [
        ("GET", "", None), ("GET", "/myself", None), ("POST", "/channel/token", TOKEN), ("POST", "/channel", LINK),
        ("DELETE", "/channel", None), ("PUT", "/settings", SETTINGS),
        ("POST", "/sender/verification", {"phone": SENDER}), ("POST", "/sender", {"phone": SENDER, "code": "000000"}),
    ]
    responses = [await wired.api.request(method, _path(b_shop, tail), json=body, headers=a)
                 for method, tail, body in calls]
    assert [error_of(r) for r in responses] == [(403, "NOT_A_MEMBER")] * 8
    assert gateway.calls == [] and await _channel_row(wired, b_shop) is None
    assert (await wired.api.get(_path(a_shop), headers=a)).status_code == 200


async def test_온보딩_흐름_토큰_신청_틀린_토큰_연동_직원은_읽기만(wired, gateway):
    shop_id, owner, o = await _owner_shop(wired)
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])

    before = await wired.api.get(_path(shop_id), headers=o)
    assert before.status_code == 200
    assert (before.json()["channel"]["status"], before.json()["settings"], before.json()["templates"]) == (
        "none", None, [])

    requested = await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)
    assert (requested.status_code, requested.json()) == (202, {"status": "token_requested"})
    assert (await wired.api.get(_path(shop_id), headers=o)).json()["channel"]["status"] == "token_requested"

    wrong = await wired.api.post(_path(shop_id, "/channel"), json={**TOKEN, "token": "123456"}, headers=o)
    assert error_of(wrong) == (400, "NOTIFICATION_TOKEN_INVALID")

    linked = await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=o)
    assert linked.status_code == 200, linked.text
    body = linked.json()
    assert body["channel"]["status"] == "linked" and body["channel"]["linked_at"].endswith("+09:00")
    assert body["settings"] == {k: v for k, v in SETTINGS.items() if k != "sms_fallback_enabled"}
    assert [(t["kind"], t["status"]) for t in body["templates"]] == [
        (k, "pending") for k in ("confirm", "reminder", "report", "change", "cancel")]
    assert gateway.calls[-5:][0][0] == "register_template"

    assert (await wired.api.get(_path(shop_id), headers=s)).json() == body
    assert error_of(await wired.api.put(_path(shop_id, "/settings"), json=SETTINGS, headers=s)) == (
        403, "PERMISSION_DENIED")
    assert error_of(await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)) == (
        409, "NOTIFICATION_CHANNEL_LINKED")


async def test_설정_문자_대체는_인증_뒤에만_다음_예약_제안은_템플릿_등록_리마인드_시각은_재계산(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    path = _path(shop_id, "/settings")

    assert error_of(await wired.api.put(path, json={**SETTINGS, "sms_fallback_enabled": True}, headers=o)) == (
        409, "NOTIFICATION_SENDER_NOT_VERIFIED")
    await _verify_sender(wired, shop_id, o)
    enabled = await wired.api.put(path, json={**SETTINGS, "sms_fallback_enabled": True}, headers=o)
    assert enabled.status_code == 200, enabled.text
    assert (enabled.json()["channel"]["sender_verified"], enabled.json()["channel"]["sms_fallback_enabled"]) == (
        True, True)
    assert (await _channel_row(wired, shop_id)).sms_fallback_enabled is True

    with_next = await wired.api.put(path, json={**SETTINGS, "next_visit_enabled": True}, headers=o)
    assert [t["kind"] for t in with_next.json()["templates"]] == [
        "confirm", "reminder", "report", "change", "cancel", "next_visit"]
    assert with_next.json()["channel"]["sms_fallback_enabled"] is False

    await _approve_templates(wired, shop_id)
    await _booked_reminder(wired, shop_id, o, _at(3, 14))
    assert [(k, s, at) for k, s, _, at in await _messages(wired, shop_id)][1] == ("reminder", "scheduled", _at(2, 18))

    moved = await wired.api.put(path, json={**SETTINGS, "reminder_time": "10:00"}, headers=o)
    assert moved.status_code == 200 and moved.json()["settings"]["reminder_time"] == "10:00"
    assert [(k, s, at) for k, s, _, at in await _messages(wired, shop_id)][1] == ("reminder", "scheduled", _at(2, 10))

    off = await wired.api.put(path, json={**SETTINGS, "reminder_time": "10:00", "reminder_enabled": False}, headers=o)
    assert off.status_code == 200
    assert [(k, s, r) for k, s, r, _ in await _messages(wired, shop_id)] == [
        ("confirm", "scheduled", None), ("reminder", "canceled", "setting_off")]
    assert error_of(await wired.api.put(path, json={**SETTINGS, "next_visit_after_weeks": 53}, headers=o)) == (
        422, "VALIDATION_ERROR")


async def test_횟수_제한_토큰_신청_6번째와_틀린_토큰_6번째는_429_다(wired, gateway):
    """N3·N4"""
    shop_id, _, o = await _owner_shop(wired)
    assert (await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)).status_code == 202

    wrong = [await wired.api.post(_path(shop_id, "/channel"), json={**TOKEN, "token": "123456"}, headers=o)
             for _ in range(6)]
    assert [error_of(r) for r in wrong] == [(400, "NOTIFICATION_TOKEN_INVALID")] * 5 + [
        (429, "NOTIFICATION_RATE_LIMITED")]
    assert error_of(await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=o)) == (
        429, "NOTIFICATION_RATE_LIMITED")

    more = [await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o) for _ in range(5)]
    assert [r.status_code for r in more[:4]] == [202] * 4
    assert error_of(more[4]) == (429, "NOTIFICATION_RATE_LIMITED")
    assert sum(1 for c in gateway.calls if c[0] == "request_channel_token") == 5


async def test_해제하면_템플릿은_비고_대기_줄은_취소되며_다시_연동해도_발신번호가_남는다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    await _verify_sender(wired, shop_id, o)
    await _approve_templates(wired, shop_id)
    await _booked_reminder(wired, shop_id, o, _at(3, 14))

    unlinked = await wired.api.delete(_path(shop_id, "/channel"), headers=o)
    assert (unlinked.status_code, unlinked.content) == (204, b"")
    after = (await wired.api.get(_path(shop_id), headers=o)).json()
    assert (after["channel"]["status"], after["channel"]["sender_number"], after["templates"]) == (
        "unlinked", SENDER, [])
    assert [(k, s, r) for k, s, r, _ in await _messages(wired, shop_id)] == [
        ("confirm", "canceled", "channel_unlinked"), ("reminder", "canceled", "channel_unlinked")]
    assert error_of(await wired.api.delete(_path(shop_id, "/channel"), headers=o)) == (
        409, "NOTIFICATION_CHANNEL_NOT_LINKED")
    assert error_of(await wired.api.put(_path(shop_id, "/settings"), json=SETTINGS, headers=o)) == (
        409, "NOTIFICATION_CHANNEL_NOT_LINKED")

    assert (await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)).status_code == 202
    relinked = await wired.api.post(_path(shop_id, "/channel"), json=LINK, headers=o)
    assert relinked.status_code == 200, relinked.text
    channel = relinked.json()["channel"]
    assert (channel["status"], channel["sender_number"], channel["sender_verified"]) == ("linked", SENDER, True)
    assert len(relinked.json()["templates"]) == 5


class _DownGateway(FakeGateway):
    async def request_channel_token(self, search_id, admin_phone, category_code):
        raise GatewayTransientError("timeout")


async def test_업체_장애면_502_이고_채널_줄이_생기지_않는다(wired, gateway):
    _install(_DownGateway())
    shop_id, _, o = await _owner_shop(wired)
    response = await wired.api.post(_path(shop_id, "/channel/token"), json=TOKEN, headers=o)
    assert error_of(response) == (502, "NOTIFICATION_PROVIDER_UNAVAILABLE")
    assert await _channel_row(wired, shop_id) is None
    assert (await wired.api.get(_path(shop_id), headers=o)).json()["channel"]["status"] == "none"


async def test_응답_어디에도_업체_ID_와_관리자_번호가_없다(wired, gateway):
    """N12"""
    shop_id, _, o = await _linked_shop(wired)
    await _verify_sender(wired, shop_id, o)
    texts = [
        (await wired.api.get(_path(shop_id), headers=o)).text,
        (await wired.api.put(_path(shop_id, "/settings"), json={**SETTINGS, "next_visit_enabled": True},
                             headers=o)).text,
    ]
    assert all(SENDER in t for t in texts)
    for secret in ("provider_channel_id", "provider_template_id", "admin_phone", "pf-", "tpl-", ADMIN_PHONE,
                   "search_id", "hisshaus"):
        assert all(secret not in t for t in texts), secret
