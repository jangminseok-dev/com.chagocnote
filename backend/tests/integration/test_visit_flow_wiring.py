"""방문·예약을 실제 배선(프로바이더·허브 포트 조립·DB 커밋·매장 접근 확인)으로 확인한다. 첫 테스트는 테넌트 격리다."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

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
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {
    "name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True,
}


def _at(days: int, hour: int) -> str:
    """오늘(한국 시각)에서 days 날 뒤의 hour 시 — 시간대가 붙은 문자열."""
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


async def _family(wired, shop_id, headers, phone="010-1234-5678", pets=("콩이", "두부")):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers",
        json={"customer": {**CUSTOMER, "phone": phone}, "pet": {**PET, "name": pets[0]}}, headers=headers,
    )
    assert response.status_code == 201, response.text
    customer_id = response.json()["customer"]["customer_id"]
    pet_ids = [response.json()["pets"][0]["pet_id"]]
    for name in pets[1:]:
        added = await wired.api.post(
            f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": name}, headers=headers
        )
        assert added.status_code == 201, added.text
        pet_ids.append(added.json()["pet"]["pet_id"])
    return customer_id, pet_ids


async def _book(wired, shop_id, headers, customer_id, pet_ids, starts_at, **extra):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/visits",
        json={"customer_id": customer_id, "pet_ids": pet_ids, "starts_at": starts_at, **extra}, headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _act(wired, shop_id, headers, visit_ids, action, reason=None):
    body = {"visit_ids": visit_ids, "action": action}
    if reason:
        body["cancel_reason"] = reason
    return await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", json=body, headers=headers)


async def test_다른_매장의_방문과_메뉴에는_손댈_수_없다(wired):
    """V1 — B매장 경로는 403 NOT_A_MEMBER, 내 매장 경로에 B매장의 ID 를 넣으면 404(본문의 메뉴는 422)다."""
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    b_customer, b_pets = await _family(wired, b_shop, b)
    b_menu = (await wired.api.get(f"/v1/shops/{b_shop}/menus", headers=b)).json()["items"][0]["menu_id"]
    b_visit = (await _book(wired, b_shop, b, b_customer, b_pets[:1], _at(3, 14), memo="B 메모"))["visits"][0]
    b_id = b_visit["visit_id"]

    their_shop = [
        await wired.api.get(f"/v1/shops/{b_shop}/visits?date=2026-10-02", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/calendar?month=2026-10", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/slots?date=2026-10-02", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/defaults?pet_id={b_pets[0]}", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/myself", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits", json={"customer_id": b_customer, "walk_in": True},
                             headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_id}", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_id}", json={}, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits/transitions",
                             json={"visit_ids": [b_id], "action": "cancel", "cancel_reason": "shop_reason"}, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits/reschedule",
                             json={"visit_ids": [b_id], "starts_at": _at(4, 14)}, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_id}/next-draft", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visit-settings", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/visit-settings", json={}, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/closed-dates?from=2026-10-01&to=2026-10-31", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/closed-dates", json={"date": "2026-10-09"}, headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/closed-dates/2026-10-09", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/menus", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/menus", json={"name": "침입"}, headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/menus/{b_menu}", json={}, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/menus/{b_menu}/archive", headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * len(their_shop)

    # 경로의 매장은 내 매장이라 소속 확인은 통과한다. 대상은 컨텍스트의 매장 안에서만 찾는다.
    update_body = {"starts_at": _at(5, 11), "pet_id": None, "duration_minutes": 60, "menu_ids": [], "memo": "침입"}
    own_shop = [
        (await wired.api.get(f"/v1/shops/{a_shop}/visits/{b_id}", headers=a), (404, "VISIT_NOT_FOUND")),
        (await wired.api.put(f"/v1/shops/{a_shop}/visits/{b_id}", json=update_body, headers=a),
         (404, "VISIT_NOT_FOUND")),
        (await _act(wired, a_shop, a, [b_id], "cancel", "shop_reason"), (404, "VISIT_NOT_FOUND")),
        (await wired.api.post(f"/v1/shops/{a_shop}/visits/reschedule",
                              json={"visit_ids": [b_id], "starts_at": _at(4, 14)}, headers=a),
         (404, "VISIT_NOT_FOUND")),
        (await wired.api.get(f"/v1/shops/{a_shop}/visits/{b_id}/next-draft", headers=a), (404, "VISIT_NOT_FOUND")),
        (await wired.api.put(f"/v1/shops/{a_shop}/menus/{b_menu}",
                             json={"name": "침입", "default_duration_minutes": 10, "sort_order": 1}, headers=a),
         (404, "MENU_NOT_FOUND")),
        (await wired.api.post(f"/v1/shops/{a_shop}/menus/{b_menu}/archive", headers=a), (404, "MENU_NOT_FOUND")),
        # V2 — 남의 매장 보호자로 예약을 잡으면 customer 가 404 로 막는다(허브 포트 너머의 오류도 같은 형식).
        (await wired.api.post(f"/v1/shops/{a_shop}/visits",
                              json={"customer_id": b_customer, "pet_ids": b_pets[:1], "starts_at": _at(3, 15)},
                              headers=a), (404, "CUSTOMER_NOT_FOUND")),
    ]
    assert [error_of(r) for r, _ in own_shop] == [expected for _, expected in own_shop]
    a_customer, a_pets = await _family(wired, a_shop, a, phone="010-9999-0000", pets=("보리",))
    borrowed_menu = await wired.api.post(
        f"/v1/shops/{a_shop}/visits",
        json={"customer_id": a_customer, "pet_ids": a_pets, "starts_at": _at(3, 15), "menu_ids": [b_menu]}, headers=a,
    )
    assert error_of(borrowed_menu) == (422, "MENU_NOT_FOUND")
    borrowed_pet = await wired.api.post(
        f"/v1/shops/{a_shop}/visits",
        json={"customer_id": a_customer, "pet_ids": b_pets[:1], "starts_at": _at(3, 15)}, headers=a,
    )
    assert error_of(borrowed_pet) == (404, "PET_NOT_FOUND")
    defaults = await wired.api.get(f"/v1/shops/{a_shop}/visits/defaults?pet_id={b_pets[0]}", headers=a)
    assert defaults.json()["source_visit_id"] is None

    # B 매장의 방문과 메뉴는 그대로다.
    detail = (await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_id}", headers=b)).json()["visit"]
    assert (detail["status"], detail["memo"], detail["starts_at"]) == ("reserved", "B 메모", b_visit["starts_at"])
    menus = (await wired.api.get(f"/v1/shops/{b_shop}/menus", headers=b)).json()["items"]
    assert (menus[0]["menu_id"], menus[0]["archived"]) == (b_menu, False)


async def test_예약부터_완료_다음_예약_취소_노쇼_되돌리기까지_돈다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, (kong, dubu) = await _family(wired, shop_id, headers)
    menus = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"]
    assert [m["name"] for m in menus] == ["목욕", "위생", "부분 미용", "전체 미용", "스포팅"]
    bath = menus[0]["menu_id"]

    # 두 마리를 오늘 13시에 — 방문 둘, 메뉴 기본 소요(목욕 60분).
    booked = await _book(wired, shop_id, headers, customer_id, [kong, dubu], _at(0, 13), menu_ids=[bath])
    visit_ids = [v["visit_id"] for v in booked["visits"]]
    assert [(v["pet"]["name"], v["duration_minutes"], v["status"]) for v in booked["visits"]] == [
        ("콩이", 60, "reserved"), ("두부", 60, "reserved")]
    assert booked["visits"][0]["customer"]["phone_masked"] == "010-12··-5678"
    again = await wired.api.post(
        f"/v1/shops/{shop_id}/visits",
        json={"customer_id": customer_id, "pet_ids": [kong], "starts_at": _at(0, 13)}, headers=headers,
    )
    assert error_of(again) == (409, "VISIT_DUPLICATE")   # V5

    today = datetime.now(SEOUL).date().isoformat()
    day = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={today}", headers=headers)).json()
    assert (day["counts"]["visit_count"], len({i["group_key"] for i in day["items"]})) == (2, 1)
    slots = (await wired.api.get(f"/v1/shops/{shop_id}/visits/slots?date={today}&duration=60", headers=headers)).json()
    assert [s["warnings"] for s in slots["slots"] if s["starts_at"].startswith(f"{today}T13")] == [["overlap"]]

    # 가족 묶음을 한 번에 시작 → 완료. 고객 목록의 최근 방문순 맨 앞에 온다.
    assert (await _act(wired, shop_id, headers, visit_ids, "start")).status_code == 200
    done = await _act(wired, shop_id, headers, visit_ids, "complete")
    assert [v["status"] for v in done.json()["visits"]] == ["completed", "completed"]
    other_id, _ = await _family(wired, shop_id, headers, phone="010-5555-0000", pets=("보리",))
    order = (await wired.api.get(f"/v1/shops/{shop_id}/customers?sort=last_visit", headers=headers)).json()
    assert [c["customer_id"] for c in order["items"]] == [customer_id, other_id]

    # 다음 예약 초안 — 처음 완료했으니 4주 뒤 같은 시각, 같은 메뉴, 가족 전체.
    draft = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_ids[0]}/next-draft", headers=headers)).json()
    assert (draft["pet_ids"], draft["interval_weeks"], draft["starts_at"]) == ([kong, dubu], 4, _at(28, 13))
    assert [m["menu_id"] for m in draft["menus"]] == [bath]
    defaults = (await wired.api.get(f"/v1/shops/{shop_id}/visits/defaults?pet_id={kong}", headers=headers)).json()
    assert (defaults["source_visit_id"], defaults["duration_minutes"]) == (visit_ids[0], 60)

    # 다음 예약을 잡고, 취소(사유)·되돌리기, 지난 예약은 노쇼.
    next_visits = await _book(wired, shop_id, headers, customer_id, draft["pet_ids"], draft["starts_at"],
                              menu_ids=[bath])
    next_ids = [v["visit_id"] for v in next_visits["visits"]]
    canceled = await _act(wired, shop_id, headers, next_ids, "cancel", "customer_request")
    assert {v["cancel_reason"] for v in canceled.json()["visits"]} == {"customer_request"}
    assert (await _act(wired, shop_id, headers, next_ids, "revert")).status_code == 200
    past = await _book(wired, shop_id, headers, customer_id, [kong], _at(-2, 10))
    past_id = past["visits"][0]["visit_id"]
    calendar_month = _at(-2, 10)[:7]
    calendar = (await wired.api.get(f"/v1/shops/{shop_id}/visits/calendar?month={calendar_month}",
                                    headers=headers)).json()
    assert calendar["unresolved_total"] == 1   # 지난 날인데 아직 예약됨
    assert (await _act(wired, shop_id, headers, [past_id], "no_show")).status_code == 200

    overview = (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).json()
    assert overview["no_show_count"] == 1
    assert [u["visit_id"] for u in overview["upcoming_visits"]] == next_ids


async def test_customer_의_규칙이_방문을_본다(wired):
    """V7·V11 — 방문 있는 아이는 지우지 않고, 예약 남은 아이·고객은 무지개다리·익명화를 막는다.
    익명화하면 방문 메모도 비우고, 하루 목록에는 이름 없이 틀만 남는다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, (kong, dubu) = await _family(wired, shop_id, headers)
    booked = await _book(wired, shop_id, headers, customer_id, [kong], _at(2, 14), memo="010-1234-5678 로 연락")
    visit_id = booked["visits"][0]["visit_id"]

    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/pets/{kong}", headers=headers)) == (
        409, "PET_HAS_VISITS")
    assert error_of(await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)) == (
        409, "PET_HAS_UPCOMING_VISITS")
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)) == (
        409, "CUSTOMER_HAS_UPCOMING_VISITS")
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{dubu}", headers=headers)).status_code == 204

    assert (await _act(wired, shop_id, headers, [visit_id], "cancel", "customer_request")).status_code == 200
    passed = await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)
    assert passed.status_code == 200
    # 무지개다리 아이의 취소를 되돌려 다시 앞으로의 예약을 만들 수 없다.
    assert error_of(await _act(wired, shop_id, headers, [visit_id], "revert")) == (422, "PET_PASSED_AWAY")
    assert error_of(await wired.api.post(
        f"/v1/shops/{shop_id}/visits",
        json={"customer_id": customer_id, "pet_ids": [kong], "starts_at": _at(5, 14)}, headers=headers,
    )) == (422, "PET_PASSED_AWAY")

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204
    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=headers)).json()["visit"]
    assert (detail["memo"], detail["customer"]["name"], detail["customer"]["phone_masked"], detail["pet"]["name"]) == (
        None, None, None, None)
    day = _at(2, 14)[:10]
    day_list = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={day}", headers=headers)).json()
    day_visit = next(i["visit"] for i in day_list["items"] if i["visit"]["visit_id"] == visit_id)
    assert (day_visit["memo"], day_visit["customer"]["name"], day_visit["customer"]["phone_masked"],
            day_visit["pet"]["name"]) == (None, None, None, None)


async def test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다(wired):
    """V8"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])
    customer_id, (kong, _) = await _family(wired, shop_id, s)

    booked = await _book(wired, shop_id, s, customer_id, [kong], _at(1, 11))
    assert (await _act(wired, shop_id, s, [booked["visits"][0]["visit_id"]], "cancel", "shop_reason")).status_code == 200
    walk_in = await wired.api.post(f"/v1/shops/{shop_id}/visits",
                                   json={"customer_id": customer_id, "pet_ids": [kong], "walk_in": True}, headers=s)
    assert walk_in.json()["visits"][0]["status"] == "in_progress"
    assert (await wired.api.get(f"/v1/shops/{shop_id}/visit-settings", headers=s)).status_code == 200

    settings = {"opens_at": "09:00", "closes_at": "18:00", "default_duration_minutes": 90, "closed_weekdays": [0]}
    menu_id = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=s)).json()["items"][0]["menu_id"]
    denied = [
        await wired.api.put(f"/v1/shops/{shop_id}/visit-settings", json=settings, headers=s),
        await wired.api.post(f"/v1/shops/{shop_id}/closed-dates", json={"date": "2026-10-09"}, headers=s),
        await wired.api.delete(f"/v1/shops/{shop_id}/closed-dates/2026-10-09", headers=s),
        await wired.api.post(f"/v1/shops/{shop_id}/menus", json={"name": "발톱"}, headers=s),
        await wired.api.put(f"/v1/shops/{shop_id}/menus/{menu_id}",
                            json={"name": "목욕", "default_duration_minutes": 60, "sort_order": 1}, headers=s),
        await wired.api.post(f"/v1/shops/{shop_id}/menus/{menu_id}/archive", headers=s),
    ]
    assert [error_of(r) for r in denied] == [(403, "PERMISSION_DENIED")] * len(denied)
    o = bearer(owner["access_token"])
    changed = await wired.api.put(f"/v1/shops/{shop_id}/visit-settings", json=settings, headers=o)
    assert changed.json()["closed_weekdays"] == [0]


async def test_자기소개와_경로_순서(wired):
    """/visits/myself·calendar·slots·defaults 가 /visits/{visit_id} 에 먼저 걸리면 422 가 된다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    myself = await wired.api.get(f"/v1/shops/{shop_id}/visits/myself", headers=headers)
    assert (myself.status_code, myself.json()["id"]) == (200, 5)
    for path in ("visits/calendar?month=2026-10", "visits/slots?date=2026-10-02",
                 "visits/defaults?pet_id=1"):
        assert (await wired.api.get(f"/v1/shops/{shop_id}/{path}", headers=headers)).status_code == 200, path
