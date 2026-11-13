"""확인할 것·미용 동의·주의 표시를 실제 배선(프로바이더·허브 포트 조립·DB)으로 확인한다(③-B).

날짜는 오늘을 기준으로 만든다 — 실행 시각과 상관없이 돈다.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import accept_invite, bearer, error_of, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")


def _day(days: int):
    return datetime.now(SEOUL).date() + timedelta(days=days)


def _at(days: int, hour: int) -> str:
    day = _day(days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


def _pet(name="콩이", birth_year=2021, conditions=()):
    return {"name": name, "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
            "birth_year": birth_year, "weight_kg": 3.2, "no_known_conditions": not conditions,
            "conditions": list(conditions)}


HEART = {"type_code": "heart_disease", "custom_label": None, "note": "약 복용 중"}
ALLERGY = {"type_code": "allergy", "custom_label": None, "note": None}


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


async def _staff(wired, shop_id, owner_headers):
    staff = await wired.login("직원")
    code = (await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=owner_headers)).json()["code"]
    assert (await accept_invite(wired, staff, code)).status_code == 200
    return bearer(staff["access_token"])


async def _family(wired, shop_id, headers, pet, phone="010-1234-5678"):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", headers=headers,
        json={"customer": {"name": "김민지", "phone": phone, "marketing_consent": True}, "pet": pet})
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _book(wired, shop_id, headers, customer_id, pet_id, days=1, hour=11):
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(days, hour)})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _move(wired, shop_id, headers, visit_id, action):
    moved = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                 json={"visit_ids": [visit_id], "action": action})
    assert moved.status_code == 200, moved.text


async def _checks(wired, shop_id, headers, visit_id) -> dict:
    detail = await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    return {c["code"]: c for c in detail.json()["checks"]}


async def test_다른_매장의_고객_아이로는_쓰지도_미리_보지도_못한다(wired):
    shop_a, a, operator = await _shop(wired)
    shop_b, b, _ = await _shop(wired, "다른 매장", "다른 사장", operator)
    customer_id, pet_id = await _family(wired, shop_a, a, _pet(birth_year=2010))

    assert error_of(await wired.api.put(f"/v1/shops/{shop_b}/customers/{customer_id}/caution",
                                        json={"reason": "남의 매장"}, headers=b)) == (404, "CUSTOMER_NOT_FOUND")
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_b}/customers/{customer_id}/caution",
                                           headers=b)) == (404, "CUSTOMER_NOT_FOUND")
    assert error_of(await wired.api.put(f"/v1/shops/{shop_b}/pets/{pet_id}/grooming-consent", json={},
                                        headers=b)) == (404, "PET_NOT_FOUND")
    assert error_of(await wired.api.get(
        f"/v1/shops/{shop_b}/visit-checks?customer_id={customer_id}&pet_ids={pet_id}&date={_day(1)}",
        headers=b)) == (404, "CUSTOMER_NOT_FOUND")
    # 남의 매장 토큰으로 이 매장의 경로를 부르면 멤버가 아니다.
    assert error_of(await wired.api.put(f"/v1/shops/{shop_a}/customers/{customer_id}/caution",
                                        json={"reason": "남의 매장"}, headers=b)) == (403, "NOT_A_MEMBER")
    untouched = (await wired.api.get(f"/v1/shops/{shop_a}/customers/{customer_id}", headers=a)).json()
    assert untouched["customer"]["caution"] is None


async def test_노령_지병_아이의_예약에서_동의를_받으면_사라지고_지병을_더하면_다시_뜬다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o, _pet(birth_year=2010, conditions=[HEART]))
    visit_id = await _book(wired, shop_id, o, customer_id, pet_id)

    checks = await _checks(wired, shop_id, o, visit_id)
    assert list(checks) == ["first_visit", "consent", "conditions"]
    assert checks["consent"]["detail"] == {"reasons": ["senior", "conditions"], "state": "missing", "received_on": None}
    assert checks["conditions"]["detail"] == {"items": [{"label": "심장 질환", "note": "약 복용 중"}]}
    assert checks["consent"]["scope"] == "pet"

    received = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", json={}, headers=o)
    assert received.status_code == 200, received.text
    assert received.json()["pet"]["grooming_consent_on"] == _day(0).isoformat()
    assert list(await _checks(wired, shop_id, o, visit_id)) == ["first_visit", "conditions"]

    # 지병을 하나 더 적으면 받아 둔 동의가 비워지고 다시 뜬다.
    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o,
                                  json=_pet(birth_year=2010, conditions=[HEART, ALLERGY]))
    assert updated.status_code == 200, updated.text
    assert updated.json()["pet"]["grooming_consent_on"] is None
    again = await _checks(wired, shop_id, o, visit_id)
    assert again["consent"]["detail"]["state"] == "missing"

    # 1년 넘게 전에 받았다고 적으면 기한이 지난 것이다. 앞날은 받지 않는다.
    old = _day(-400).isoformat()
    assert (await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent",
                                json={"received_on": old}, headers=o)).status_code == 200
    expired = await _checks(wired, shop_id, o, visit_id)
    assert (expired["consent"]["detail"]["state"], expired["consent"]["detail"]["received_on"]) == ("expired", old)
    assert error_of(await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent",
                                        json={"received_on": _day(1).isoformat()}, headers=o)) == (422, "VALIDATION_ERROR")

    cleared = await wired.api.delete(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=o)
    assert (cleared.status_code, cleared.json()["pet"]["grooming_consent_on"]) == (200, None)


async def test_주의_표시와_노쇼는_다음_예약의_확인할_것과_하루_목록의_수에_실린다(wired):
    shop_id, o, _ = await _shop(wired)
    s = await _staff(wired, shop_id, o)
    customer_id, pet_id = await _family(wired, shop_id, o, _pet())
    # 어제 다녀갔고(완료), 그저께는 노쇼였다.
    done = await _book(wired, shop_id, o, customer_id, pet_id, days=-1)
    await _move(wired, shop_id, o, done, "start")
    await _move(wired, shop_id, o, done, "complete")
    missed = await _book(wired, shop_id, o, customer_id, pet_id, days=-2)
    await _move(wired, shop_id, o, missed, "no_show")
    visit_id = await _book(wired, shop_id, o, customer_id, pet_id, days=1)

    checks = await _checks(wired, shop_id, o, visit_id)
    assert list(checks) == ["no_show"]
    assert checks["no_show"] == {"code": "no_show", "scope": "customer", "detail": {"count": 1}}
    assert await _checks(wired, shop_id, o, done) == {}       # 완료한 방문에는 없다
    assert await _checks(wired, shop_id, o, missed) == {}

    # 직원이 주의 표시를 단다.
    marked = await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}/caution",
                                 json={"reason": "  노쇼가 잦아요 "}, headers=s)
    assert marked.status_code == 200, marked.text
    until = _day(365).isoformat()
    assert marked.json()["customer"]["caution"] == {"reason": "노쇼가 잦아요", "until": until}

    checks = await _checks(wired, shop_id, s, visit_id)
    assert list(checks) == ["caution", "no_show"]
    assert checks["caution"]["detail"] == {"reason": "노쇼가 잦아요", "until": until}

    day = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={_day(1)}", headers=o)).json()
    assert [(i["customer_check_count"], i["pet_check_count"]) for i in day["items"]] == [(2, 0)]
    past = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={_day(-1)}", headers=o)).json()
    assert [(i["customer_check_count"], i["pet_check_count"]) for i in past["items"]] == [(0, 0)]

    # 목록·반려동물 상세에도 보인다(목록은 사유 없이 여부만).
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=o)).json()["items"][0]
    assert listed["caution"] is True and "reason" not in listed
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o)).json()
    assert pet["caution"] == {"reason": "노쇼가 잦아요", "until": until}

    # 미리 보기 — 아직 없는 예약. 어제 다녀가서 첫 방문이 아니다.
    preview = await wired.api.get(
        f"/v1/shops/{shop_id}/visit-checks?customer_id={customer_id}&pet_ids={pet_id}&date={_day(3)}", headers=s)
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert [c["code"] for c in body["customer"]] == ["caution", "no_show"]
    assert body["pets"] == [{"pet_id": pet_id, "checks": []}]

    # 직원이 푼다. 풀고 나면 어디에도 없다.
    cleared = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}/caution", headers=s)
    assert (cleared.status_code, cleared.json()["customer"]["caution"]) == (200, None)
    assert list(await _checks(wired, shop_id, o, visit_id)) == ["no_show"]
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=o)).json()["items"][0]["caution"] is False


async def test_확인할_것은_예약도_상태_바꾸기도_막지_않는다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o, _pet(birth_year=2008, conditions=[HEART]))
    assert (await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}/caution",
                                json={"reason": "입질"}, headers=o)).status_code == 200

    visit_id = await _book(wired, shop_id, o, customer_id, pet_id, days=0, hour=10)
    assert len(await _checks(wired, shop_id, o, visit_id)) == 4   # 주의 · 첫 방문 · 동의 · 지병
    await _move(wired, shop_id, o, visit_id, "start")
    assert len(await _checks(wired, shop_id, o, visit_id)) == 4   # 미용 중에도 보인다
    await _move(wired, shop_id, o, visit_id, "complete")
    assert await _checks(wired, shop_id, o, visit_id) == {}


async def test_기한이_지난_주의는_어디에도_없고_익명화하면_칸이_비워진다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o, _pet(birth_year=2010))
    assert (await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}/caution",
                                json={"reason": "입질"}, headers=o)).status_code == 200
    assert (await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", json={},
                                headers=o)).status_code == 200
    visit_id = await _book(wired, shop_id, o, customer_id, pet_id)
    assert "caution" in await _checks(wired, shop_id, o, visit_id)

    # 끝나는 날을 어제로 돌리면 읽을 때 걸러진다(칸은 그대로 있다).
    await wired.execute("UPDATE customers SET caution_until = :d WHERE id = :id", d=_day(-1), id=customer_id)
    assert "caution" not in await _checks(wired, shop_id, o, visit_id)
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).json()["customer"]["caution"] is None
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=o)).json()["items"][0]["caution"] is False

    # 익명화 — 앞으로의 예약을 먼저 취소해야 한다.
    canceled = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=o,
                                    json={"visit_ids": [visit_id], "action": "cancel", "cancel_reason": "customer_request"})
    assert canceled.status_code == 200, canceled.text
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)).status_code == 204
    async with wired.engine.connect() as conn:
        row = (await conn.execute(text(
            "SELECT caution_reason, caution_until, caution_set_at, caution_set_by_member_id "
            "FROM customers WHERE id = :id"), {"id": customer_id})).one()
        consent = (await conn.execute(text(
            "SELECT grooming_consent_on, grooming_consent_by_member_id FROM pets WHERE id = :id"),
            {"id": pet_id})).one()
    assert tuple(row) == (None, None, None, None)
    assert tuple(consent) == (None, None)
    assert error_of(await wired.api.get(
        f"/v1/shops/{shop_id}/visit-checks?customer_id={customer_id}&date={_day(1)}", headers=o)) == (404, "CUSTOMER_NOT_FOUND")
