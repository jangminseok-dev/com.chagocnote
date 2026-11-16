"""매출 통계를 실제 배선(프로바이더·허브 포트 조립·DB)으로 확인한다. 첫 테스트는 테넌트 격리다.

방문은 어제 날짜로 만든다 — 요약은 그 날짜를 anchor 로 읽으므로 실행 시각(달의 첫날, 월요일)과 상관없이 돈다.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from tests.integration.support import accept_invite, bearer, error_of, make_operator, shop_with_owner

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}
SUMMARY_KEYS = {
    "span", "period", "revenue", "visit_count", "priced_count", "average", "compare", "goal", "pets", "buckets",
    "payments", "menus", "regulars", "bookings", "weekdays", "report", "unrecorded_count", "due_pet_count",
}


def _day(days: int):
    return datetime.now(SEOUL).date() + timedelta(days=days)


def _at(days: int, hour: int) -> str:
    day = _day(days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


YESTERDAY = _day(-1).isoformat()


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


async def _staff(wired, shop_id, owner_headers):
    staff = await wired.login("직원")
    code = (await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=owner_headers)).json()["code"]
    assert (await accept_invite(wired, staff, code)).status_code == 200
    return bearer(staff["access_token"])


async def _family(wired, shop_id, headers, phone="010-1234-5678", pet_name="콩이"):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers", headers=headers,
        json={"customer": {"name": "김민지", "phone": phone, "marketing_consent": True}, "pet": {**PET, "name": pet_name}})
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _visit(wired, shop_id, headers, customer_id, pet_id, hour=11, days=-1):
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(days, hour)})
    assert booked.status_code == 201, booked.text
    return booked.json()["visits"][0]["visit_id"]


async def _move(wired, shop_id, headers, visit_id, action, **extra):
    moved = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                 json={"visit_ids": [visit_id], "action": action, **extra})
    assert moved.status_code == 200, moved.text


async def _done(wired, shop_id, headers, customer_id, pet_id, hour, record: dict | None):
    """어제 그 시각의 완료 방문. record 가 있으면 기록을 적는다."""
    visit_id = await _visit(wired, shop_id, headers, customer_id, pet_id, hour)
    await _move(wired, shop_id, headers, visit_id, "start")
    if record is not None:
        saved = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", json=record, headers=headers)
        assert saved.status_code == 200, saved.text
    await _move(wired, shop_id, headers, visit_id, "complete")
    return visit_id


async def _summary(wired, shop_id, headers, span="month", anchor=YESTERDAY):
    response = await wired.api.get(f"/v1/shops/{shop_id}/sales/summary?span={span}&anchor={anchor}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def _three_visits(wired, shop_id, o):
    """카드 30,000(항목 30,000) · 현금 50,000(항목 45,000) · 금액 없음. (고객, 아이 둘, 메뉴, 방문 셋)"""
    customer_id, kong = await _family(wired, shop_id, o)
    dubu_customer, dubu = await _family(wired, shop_id, o, phone="010-2222-3333", pet_name="두부")
    bath = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=o)).json()["items"][0]["menu_id"]
    first = await _done(wired, shop_id, o, customer_id, kong, 10, {
        "payment_method": "card", "total_amount": 30_000, "items": [{"menu_id": bath, "amount": 30_000}]})
    second = await _done(wired, shop_id, o, dubu_customer, dubu, 12, {
        "payment_method": "cash", "total_amount": 50_000, "items": [{"menu_id": bath, "amount": 45_000}]})
    third = await _done(wired, shop_id, o, customer_id, kong, 15, {"care_note": "금액은 아직"})
    return customer_id, kong, dubu, bath, (first, second, third)


async def test_다른_매장의_매출은_볼_수_없고_섞이지_않는다(wired):
    a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
    b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
    customer_id, pet_id = await _family(wired, b_shop, b)
    await _done(wired, b_shop, b, customer_id, pet_id, 11, {"payment_method": "card", "total_amount": 70_000})

    for path in ("summary?span=month", "visits?span=month&filter=unrecorded", "goal"):
        assert error_of(await wired.api.get(f"/v1/shops/{b_shop}/sales/{path}", headers=a)) == (403, "NOT_A_MEMBER")
    assert error_of(await wired.api.put(f"/v1/shops/{b_shop}/sales/goal", headers=a,
                                        json={"monthly_amount": 1})) == (403, "NOT_A_MEMBER")
    mine = await _summary(wired, a_shop, a)
    assert (mine["revenue"], mine["visit_count"], mine["pets"]["count"], mine["buckets"][0]["pets"]) == (0, 0, 0, [])
    assert (await _summary(wired, b_shop, b))["revenue"] == 70_000


async def test_직원은_매출의_어느_경로도_쓰지_못하고_로그인_없이는_401_이다(wired):
    shop_id, o, _ = await _shop(wired)
    staff = await _staff(wired, shop_id, o)
    base = f"/v1/shops/{shop_id}/sales"
    reads = ("summary?span=month", "visits?span=month&filter=unrecorded", "goal")
    for path in reads:
        assert error_of(await wired.api.get(f"{base}/{path}", headers=staff)) == (403, "PERMISSION_DENIED")
        assert (await wired.api.get(f"{base}/{path}")).status_code == 401
    assert error_of(await wired.api.put(f"{base}/goal", headers=staff, json={"monthly_amount": 1})) == (
        403, "PERMISSION_DENIED")
    assert (await wired.api.put(f"{base}/goal", json={"monthly_amount": 1})).status_code == 401
    assert (await wired.api.get(f"{base}/goal", headers=o)).json() == {"monthly_amount": None}   # 직원의 쓰기는 닿지 않았다


async def test_방문_셋의_요약은_손으로_센_값과_같고_합이_서로_맞는다(wired):
    shop_id, o, _ = await _shop(wired)
    _, kong, dubu, bath, visits = await _three_visits(wired, shop_id, o)

    s = await _summary(wired, shop_id, o)
    assert set(s) == SUMMARY_KEYS
    assert (s["revenue"], s["visit_count"], s["priced_count"], s["average"], s["unrecorded_count"]) == (
        80_000, 3, 2, 40_000, 1)
    assert s["payments"] == [{"method": "card", "amount": 30_000}, {"method": "cash", "amount": 50_000}]
    assert [(m["menu_id"], m["amount"], m["count"]) for m in s["menus"]] == [(bath, 75_000, 2), (None, 5_000, 0)]
    assert s["menus"][1]["name"] == "조정"
    assert sum(p["amount"] for p in s["payments"]) == sum(m["amount"] for m in s["menus"]) \
        == sum(b["revenue"] for b in s["buckets"]) == sum(s["weekdays"]) == s["revenue"]
    assert (s["pets"]["count"], s["pets"]["new_count"], s["pets"]["returning_count"]) == (2, 2, 0)
    assert sorted(p["name"] for p in s["pets"]["faces"]) == ["두부", "콩이"]
    assert [(r["pet"]["name"], r["visit_count"]) for r in s["regulars"]] == [("콩이", 2), ("두부", 1)]
    day = next(b for b in s["buckets"] if b["key"] == YESTERDAY)
    assert (day["revenue"], day["visit_count"], [p["name"] for p in day["pets"]]) == (80_000, 3, ["콩이", "두부"])
    assert s["report"] == {"completed": 3, "sent": 0, "opened": 0}
    assert (s["bookings"]["no_show"], s["bookings"]["canceled"]) == (0, 0)

    # 하루·주·연으로 봐도 같은 돈이다.
    for span in ("day", "week", "year"):
        assert (await _summary(wired, shop_id, o, span))["revenue"] == 80_000
    # 그날이 아닌 날은 비어 있다.
    assert (await _summary(wired, shop_id, o, "day", _day(-2).isoformat()))["revenue"] == 0

    blank = await wired.api.get(
        f"/v1/shops/{shop_id}/sales/visits?span=day&anchor={YESTERDAY}&filter=unrecorded", headers=o)
    assert [(i["visit_id"], i["pet"]["name"], i["amount"]) for i in blank.json()["items"]] == [(visits[2], "콩이", None)]
    by_menu = await wired.api.get(
        f"/v1/shops/{shop_id}/sales/visits?span=day&anchor={YESTERDAY}&filter=menu&menu_id={bath}", headers=o)
    assert [(i["visit_id"], i["amount"]) for i in by_menu.json()["items"]] == [(visits[1], 50_000), (visits[0], 30_000)]


async def test_금액을_채우면_매출이_늘고_노쇼와_취소와_남은_예약이_세어진다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, kong, _, bath, visits = await _three_visits(wired, shop_id, o)

    record_path = f"/v1/shops/{shop_id}/visits/{visits[2]}/record"
    version = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visits[2]}", headers=o)).json()["record"]["version"]
    filled = await wired.api.put(record_path, headers=o, json={
        "version": version, "payment_method": "transfer", "total_amount": 20_000,
        "items": [{"menu_id": bath, "amount": 20_000}]})
    assert filled.status_code == 200, filled.text
    s = await _summary(wired, shop_id, o)
    assert (s["revenue"], s["priced_count"], s["unrecorded_count"]) == (100_000, 3, 0)
    assert s["payments"][-1] == {"method": "transfer", "amount": 20_000}

    no_show = await _visit(wired, shop_id, o, customer_id, kong, 17)
    await _move(wired, shop_id, o, no_show, "no_show")
    canceled = await _visit(wired, shop_id, o, customer_id, kong, 18)
    await _move(wired, shop_id, o, canceled, "cancel", cancel_reason="customer_request")
    priced = await wired.api.put(f"/v1/shops/{shop_id}/menus/{bath}", headers=o, json={
        "name": "매출 확인 메뉴", "default_duration_minutes": 60, "sort_order": 0, "price": 25_000})
    assert priced.status_code == 200, priced.text
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=o, json={
        "customer_id": customer_id, "pet_ids": [kong], "starts_at": _at(1, 11), "menu_ids": [bath]})
    assert booked.status_code == 201, booked.text

    # 노쇼·취소는 어제의 것이라 어제로 읽는다 — 오늘이 1월 1일이면 올해의 요약에는 없다.
    yesterday = await _summary(wired, shop_id, o, "day")
    assert (yesterday["bookings"]["no_show"], yesterday["bookings"]["canceled"]) == (1, 1)
    today = await _summary(wired, shop_id, o, "year", _day(0).isoformat())
    # 내일이 해를 넘기면(12월 31일) 올해의 남은 예약이 아니다 — 그날만 0 이다.
    expected = (1, 25_000) if _day(1).year == _day(0).year else (0, None)
    assert (today["bookings"]["remaining"], today["bookings"]["expected_amount"]) == expected
    listed = await wired.api.get(
        f"/v1/shops/{shop_id}/sales/visits?span=day&anchor={YESTERDAY}&filter=no_show", headers=o)
    assert [i["visit_id"] for i in listed.json()["items"]] == [no_show]


async def test_익명화한_고객의_방문은_매출에는_남고_얼굴에는_없다(wired):
    shop_id, o, _ = await _shop(wired)
    customer_id, kong, dubu, bath, _ = await _three_visits(wired, shop_id, o)

    deleted = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=o)   # 콩이의 보호자
    assert deleted.status_code == 204, deleted.text
    s = await _summary(wired, shop_id, o)
    assert (s["revenue"], s["visit_count"], s["pets"]["count"]) == (80_000, 3, 2)                 # 돈과 수는 남는다
    assert [p["name"] for p in s["pets"]["faces"]] == ["두부"]
    assert [r["pet"]["name"] for r in s["regulars"]] == ["두부"]
    day = next(b for b in s["buckets"] if b["key"] == YESTERDAY)
    assert [p["name"] for p in day["pets"]] == ["두부"]
    assert "콩이" not in str(s) and "김민지" not in str(s)
    blank = await wired.api.get(
        f"/v1/shops/{shop_id}/sales/visits?span=day&anchor={YESTERDAY}&filter=unrecorded", headers=o)
    assert [i["pet"] for i in blank.json()["items"]] == [None]                                    # 방문은 보이고 이름은 없다


async def test_목표는_이번_달_요약에만_보이고_지우면_사라진다(wired):
    shop_id, o, _ = await _shop(wired)
    goal = f"/v1/shops/{shop_id}/sales/goal"
    today = _day(0).isoformat()
    assert (await _summary(wired, shop_id, o, "month", today))["goal"] is None

    assert (await wired.api.put(goal, headers=o, json={"monthly_amount": 5_000_000})).json() == {
        "monthly_amount": 5_000_000}
    assert (await wired.api.get(goal, headers=o)).json() == {"monthly_amount": 5_000_000}
    assert (await _summary(wired, shop_id, o, "month", today))["goal"] == {"monthly_amount": 5_000_000}
    last_month = (_day(0).replace(day=1) - timedelta(days=1)).isoformat()
    assert (await _summary(wired, shop_id, o, "month", last_month))["goal"] is None
    assert (await _summary(wired, shop_id, o, "year", today))["goal"] is None

    assert (await wired.api.put(goal, headers=o, json={"monthly_amount": 0})).json() == {"monthly_amount": None}
    assert (await _summary(wired, shop_id, o, "month", today))["goal"] is None
    # 목표를 정하면서 일정 설정 행과 기본 메뉴가 생겼다(알림장 설정과 같은 방식).
    assert len((await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=o)).json()["items"]) > 0


async def test_범위_끝의_입력은_어느_것도_500_이_아니다(wired):
    shop_id, o, _ = await _shop(wired)
    base = f"/v1/shops/{shop_id}/sales"
    for query in ("span=week&anchor=2100-12-31", "span=year&anchor=2100-12-31", "span=month&anchor=2000-01-01",
                  "span=day&anchor=2000-01-01", "span=month&anchor=2099-06-15"):
        response = await wired.api.get(f"{base}/summary?{query}", headers=o)
        assert response.status_code == 200, (query, response.text)
        assert response.json()["revenue"] == 0
    future = (await wired.api.get(f"{base}/summary?span=month&anchor=2099-06-15", headers=o)).json()
    assert (future["compare"], future["period"]["elapsed_end"]) == ({"previous": None, "year_ago": None}, None)

    bad = (
        "summary?span=month&anchor=1999-12-31", "summary?span=month&anchor=2101-01-01", "summary?span=decade",
        "visits?span=month&filter=menu", "visits?span=month&filter=menu&menu_id=9223372036854775808",
        "visits?span=month&filter=no_show&cursor=!!!!", "visits?span=month&filter=no_show&cursor=YWJj",
    )
    for path in bad:
        assert error_of(await wired.api.get(f"{base}/{path}", headers=o)) == (422, "VALIDATION_ERROR"), path
    huge = await wired.api.get(f"{base}/visits?span=month&filter=menu&menu_id=9223372036854775807", headers=o)
    assert (huge.status_code, huge.json()) == (200, {"items": [], "next_cursor": None})   # 없는(남의) 메뉴는 빈 목록
    revisits = await wired.api.get(f"/v1/shops/{shop_id}/revisits", params={"bucket": "due", "cursor": "YWJj"},
                                   headers=o)
    assert error_of(revisits) == (422, "VALIDATION_ERROR")   # 다시 올 때가 된 아이(⑬)의 깨진 커서
