"""방문별 발송 내역·다시 보내기·단건 조회를 실제 배선(프로바이더·DB·매장 접근 확인·main.py 가 꽂은 허브 포트)으로 돌린다.

채널·설정·템플릿은 온보딩 API 로 만들고 템플릿만 SQL 로 approved. 디스패처는 FakeGateway 로 run_once 를 직접 돈다.
첫 테스트는 테넌트 격리다(하네스 규칙). 응답 어디에도 번호·variables·업체 메시지 ID 가 없어야 한다(N12).
알림장 주소는 변수로 들지 않는다 — share_text 에 "/r/" 가 있는지만 본다.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from notification.adapter.outbound.strategy.fake_gateway import FakeGateway
from notification.dependencies.dispatcher_provider import build_dispatcher
from notification.dependencies.notification_wiring import get_message_gateway
from notification.domain.services.templates import format_when
from tests.integration.support import accept_invite, bearer, error_of, make_operator, shop_with_owner, staff_invite

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
SHOP_NAME = "Hiss Haus"
TOKEN = {"search_id": "hisshaus", "admin_phone": "01012345678", "category_code": "003001"}
LINK = {**TOKEN, "token": "000000"}
PHONE_OK, PHONE_BAD = "010-1234-5678", "010-1234-0000"     # 끝 0000 은 FakeGateway 가 영구 실패로 답한다
CUSTOMER = {"name": "김민지", "phone": PHONE_OK, "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
SECRETS = ("variables", "provider_message_id", "fake-", "starts_at", "error_code", "3104", "customer_id", "pet_id",
           "01012340000", "1234-0000", "01012345678", "1234-5678")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _at(days: int, hour: int) -> datetime:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL)


@pytest.fixture
def gateway(wired):
    import main

    fake = FakeGateway()
    main.app.dependency_overrides[get_message_gateway] = lambda: fake
    yield fake
    main.app.dependency_overrides.pop(get_message_gateway, None)


async def _linked_shop(wired, name=SHOP_NAME, owner_name="사장님"):
    """연동을 마치고 기본 5종 템플릿을 approved 로 둔 매장. (shop_id, owner 로그인, 헤더)"""
    operator = await make_operator(wired, f"운영자-{name}")
    shop_id, owner = await shop_with_owner(wired, operator, name, owner_name)
    headers = bearer(owner["access_token"])
    assert (await wired.api.post(f"/v1/shops/{shop_id}/notification/channel/token", json=TOKEN,
                                 headers=headers)).status_code == 202
    linked = await wired.api.post(f"/v1/shops/{shop_id}/notification/channel", json=LINK, headers=headers)
    assert linked.status_code == 200, linked.text
    await wired.execute("UPDATE notification_templates SET status = 'approved' WHERE shop_id = :shop_id",
                        shop_id=shop_id)
    return shop_id, owner, headers


async def _family(wired, shop_id, headers, phone=PHONE_OK) -> tuple[int, int]:
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                    json={"customer": {**CUSTOMER, "phone": phone}, "pet": PET})
    assert response.status_code == 201, response.text
    body = response.json()
    return body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _booked(wired, shop_id, headers, starts_at: datetime, phone=PHONE_OK) -> int:
    customer_id, pet_id = await _family(wired, shop_id, headers, phone)
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": [pet_id],
                                        "starts_at": starts_at.isoformat()})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _reported(wired, shop_id, headers, phone=PHONE_OK) -> int:
    """어제 방문을 시작·기록·완료하고 알림장을 보낸다 — report 줄이 생긴다. 방문 ID."""
    visit_id = await _booked(wired, shop_id, headers, _at(-1, 11), phone)
    await _transition(wired, shop_id, headers, visit_id, "start")
    written = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", headers=headers,
                                  json={"care_note": "눈물 자국을 닦았어요", "media": []})
    assert written.status_code == 200, written.text
    await _transition(wired, shop_id, headers, visit_id, "complete")
    sent = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/report", headers=headers,
                               json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    return visit_id


async def _transition(wired, shop_id, headers, visit_id, action) -> None:
    response = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                    json={"visit_ids": [visit_id], "action": action})
    assert response.status_code == 200, response.text


async def _run_twice(wired, gateway: FakeGateway) -> None:
    """집어 보내고(accepted) 6초 뒤 상태를 물어 최종 상태로."""
    sessions = async_sessionmaker(wired.engine, expire_on_commit=False, autoflush=False)
    for now in (_now(), _now() + timedelta(seconds=6)):
        async with sessions() as session:
            await build_dispatcher(session, gateway=gateway, now=lambda: now).run_once()


async def _items(wired, shop_id, visit_id, headers) -> list[dict]:
    response = await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications", headers=headers)
    assert response.status_code == 200, response.text
    for secret in SECRETS:
        assert secret not in response.text, secret
    return response.json()["items"]


def _brief(items: list[dict]) -> list[tuple]:
    return [(i["kind"], i["status"]) for i in items]


async def test_다른_매장의_세_경로는_403_이고_다른_매장의_message_id_는_404_visit_id_는_빈_목록이다(wired, gateway):
    """N1·N2"""
    a_shop, _, a = await _linked_shop(wired, "A 매장", "A사장")
    b_shop, _, b = await _linked_shop(wired, "B 매장", "B사장")
    b_visit = await _booked(wired, b_shop, b, _at(3, 14))
    [_, b_confirm] = await _items(wired, b_shop, b_visit, b)

    responses = [
        await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_visit}/notifications", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits/{b_visit}/notifications/confirm/resend", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/notifications/{b_confirm['message_id']}", headers=a),
    ]
    assert [error_of(r) for r in responses] == [(403, "NOT_A_MEMBER")] * 3

    assert error_of(await wired.api.get(f"/v1/shops/{a_shop}/notifications/{b_confirm['message_id']}",
                                        headers=a)) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")
    assert await _items(wired, a_shop, b_visit, a) == []
    assert error_of(await wired.api.post(f"/v1/shops/{a_shop}/visits/{b_visit}/notifications/confirm/resend",
                                         headers=a)) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")
    assert _brief(await _items(wired, b_shop, b_visit, b)) == [("reminder", "scheduled"), ("confirm", "scheduled")]


async def test_예약하면_confirm_reminder_가_보이고_디스패처가_돌면_confirm_은_sent_이며_단건_조회와_같다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    visit_id = await _booked(wired, shop_id, o, _at(3, 14))

    before = await _items(wired, shop_id, visit_id, o)
    assert _brief(before) == [("reminder", "scheduled"), ("confirm", "scheduled")]
    reminder, confirm = before
    assert reminder["scheduled_at"] == _at(2, 18).isoformat()
    assert all(i["share_text"] is None and i["sent_at"] is None for i in before)

    await _run_twice(wired, gateway)

    after = await _items(wired, shop_id, visit_id, o)
    assert _brief(after) == [("reminder", "scheduled"), ("confirm", "sent")]
    assert (after[1]["channel_used"], after[1]["share_text"]) == ("alimtalk", None)
    assert after[1]["sent_at"].endswith("+09:00")
    single = await wired.api.get(f"/v1/shops/{shop_id}/notifications/{confirm['message_id']}", headers=o)
    assert single.status_code == 200 and single.json() == after[1]


async def test_영구_실패_줄은_share_text_가_있고_직원이_다시_보내면_새_줄이_생기며_두_번째는_409_다(wired, gateway):
    """N5·N12"""
    shop_id, owner, o = await _linked_shop(wired)
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])
    starts_at = _at(3, 14)
    visit_id = await _booked(wired, shop_id, o, starts_at, PHONE_BAD)
    await _run_twice(wired, gateway)

    [reminder, failed] = await _items(wired, shop_id, visit_id, s)
    assert (failed["kind"], failed["status"], failed["error_kind"]) == ("confirm", "failed", "permanent")
    assert failed["share_text"] == f"[{SHOP_NAME}] {format_when(starts_at, 'Asia/Seoul')} 예약이 접수되었어요."
    assert reminder["share_text"] is None

    resent = await wired.api.post(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications/confirm/resend", headers=s)
    assert resent.status_code == 201, resent.text
    message_id = resent.json()["message_id"]
    items = await _items(wired, shop_id, visit_id, s)
    assert _brief(items) == [("confirm", "scheduled"), ("reminder", "scheduled"), ("confirm", "failed")]
    new = items[0]
    assert (new["message_id"], new["requested_by_member_id"] is not None, new["share_text"]) == (message_id, True, None)
    assert error_of(await wired.api.post(f"/v1/shops/{shop_id}/visits/{visit_id}/notifications/confirm/resend",
                                         headers=s)) == (409, "NOTIFICATION_ALREADY_PENDING")
    assert len(await _items(wired, shop_id, visit_id, s)) == 3


async def test_알림장은_보내면_report_줄이_생겨_sent_가_되고_실패_줄의_share_text_에는_주소가_있다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    ok_visit = await _reported(wired, shop_id, o)
    bad_visit = await _reported(wired, shop_id, o, PHONE_BAD)
    assert _brief(await _items(wired, shop_id, ok_visit, o))[0] == ("report", "scheduled")

    await _run_twice(wired, gateway)

    ok = await _items(wired, shop_id, ok_visit, o)
    assert _brief(ok) == [("report", "sent"), ("confirm", "sent")]
    assert all(i["share_text"] is None for i in ok)
    bad = await _items(wired, shop_id, bad_visit, o)
    assert _brief(bad) == [("report", "failed"), ("confirm", "failed")]
    assert bad[0]["share_text"].startswith(f"[{SHOP_NAME}] 알림장 ") and "/r/" in bad[0]["share_text"]
    assert "/r/" not in bad[1]["share_text"]


async def test_없는_종류는_422_이고_줄이_없는_종류는_404_다(wired, gateway):
    shop_id, _, o = await _linked_shop(wired)
    visit_id = await _booked(wired, shop_id, o, _at(3, 14))
    base = f"/v1/shops/{shop_id}/visits/{visit_id}/notifications"

    assert error_of(await wired.api.post(f"{base}/sms/resend", headers=o)) == (422, "VALIDATION_ERROR")
    assert error_of(await wired.api.post(f"{base}/cancel/resend", headers=o)) == (404, "NOTIFICATION_MESSAGE_NOT_FOUND")
    assert error_of(await wired.api.post(f"{base}/confirm/resend", headers=o)) == (409, "NOTIFICATION_ALREADY_PENDING")
    assert len(await _items(wired, shop_id, visit_id, o)) == 2
