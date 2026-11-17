"""예약의 보낼 것 묶음을 실제 배선으로 확인한다(⑪-B) — 예약 안내와 동의서 링크를 한 번에."""
import logging

import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import SENIOR_YEAR, add_pet, count, send, sign_here
from tests.integration.test_visit_checks_wiring import (
    HEART, _at, _book, _day, _family, _move, _pet, _shop, _staff,
)

pytestmark = pytest.mark.integration


async def bundle(wired, shop_id, headers, visit_id):
    return await wired.api.post(f"/v1/shops/{shop_id}/visits/{visit_id}/send-bundle", headers=headers)


def kinds(response) -> list[str]:
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"parts", "created_form_id"}
    assert all(set(part) == {"kind", "text"} for part in response.json()["parts"])
    return [part["kind"] for part in response.json()["parts"]]


async def test_노령_아이의_예약은_예약_안내와_동의서_링크이고_링크는_다시_불러도_같다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id, days=3, hour=14)

    first = await bundle(wired, shop_id, headers, visit_id)
    again = await bundle(wired, shop_id, headers, visit_id)

    assert kinds(first) == ["reservation", "consent"] and again.json()["parts"] == first.json()["parts"]
    # 이번에 새로 만든 링크만 알려 준다 — 보내지 않고 닫으면 앱이 그것만 끊는다.
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert first.json()["created_form_id"] == listed[0]["form_id"] and again.json()["created_form_id"] is None
    reservation, consent = (part["text"] for part in first.json()["parts"])
    day = _day(3)
    assert "Hiss Haus" in reservation and f"{day.month}월 {day.day}일" in reservation and "오후 2:00" in reservation
    assert "콩이" in reservation and "{" not in reservation + consent
    sent = (await send(wired, shop_id, headers, pet_id, for_date=day)).json()        # 살아 있는 요청과 같은 링크다
    assert sent["url"] in consent
    assert await count(wired, "customer_forms") == 1


async def test_동의가_필요_없는_아이의_예약은_예약_안내뿐이고_링크를_만들지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, young = await _family(wired, shop_id, headers, _pet())
    _, signed = await _family(wired, shop_id, headers, _pet(name="보리", birth_year=SENIOR_YEAR), phone="010-2222-3333")
    assert (await sign_here(wired, shop_id, headers, signed)).status_code == 201
    signed_owner = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{signed}", headers=headers)).json()["pet"]["customer_id"]

    young_visit = await _book(wired, shop_id, headers, customer_id, young)
    signed_visit = await _book(wired, shop_id, headers, signed_owner, signed, hour=15)

    assert kinds(await bundle(wired, shop_id, headers, young_visit)) == ["reservation"]
    assert (await bundle(wired, shop_id, headers, young_visit)).json()["created_form_id"] is None
    assert kinds(await bundle(wired, shop_id, headers, signed_visit)) == ["reservation"]
    assert await count(wired, "customer_forms") == 0


async def test_가족이_함께_잡은_예약은_한_묶음이고_동의서는_필요한_아이만_담는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리"))
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [kong, bori], "starts_at": _at(2, 11)})
    assert booked.status_code == 201, booked.text
    first, second = (v["visit_id"] for v in booked.json()["visits"])

    one = await bundle(wired, shop_id, headers, first)
    other = await bundle(wired, shop_id, headers, second)

    assert kinds(one) == ["reservation", "consent"] and other.json()["parts"] == one.json()["parts"]
    assert "콩이 · 보리" in one.json()["parts"][0]["text"]
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert [[p["pet_id"] for p in item["pets"]] for item in listed] == [[kong]]


async def test_매장이_고친_글로_나간다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    changed = await wired.api.put(f"/v1/shops/{shop_id}/form-settings", headers=headers, json={
        "link_days": 14, "senior_age": 10, "consent_days": 365,
        "reservation_text": "{아이} 예약 확인했어요 ({날짜} {시간})", "consent_text": "서명 부탁드려요 → {링크}"})
    assert changed.status_code == 200, changed.text

    reservation, consent = (part["text"] for part in (await bundle(wired, shop_id, headers, visit_id)).json()["parts"])

    assert reservation.startswith("콩이 예약 확인했어요 (") and consent.startswith("서명 부탁드려요 → http")


async def test_끝났거나_취소된_방문은_토막이_없고_링크도_만들지_않는다(wired):
    # 익명화는 살아 있는 예약이 있으면 막힌다(409) — 익명화한 고객의 방문은 늘 취소됐거나 끝난 방문이다.
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    canceled = await _book(wired, shop_id, headers, customer_id, pet_id, days=1)
    done = await _book(wired, shop_id, headers, customer_id, pet_id, days=-1)
    cancel = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers, json={
        "visit_ids": [canceled], "action": "cancel", "cancel_reason": "customer_request"})
    assert cancel.status_code == 200, cancel.text
    await _move(wired, shop_id, headers, done, "start")
    in_progress = kinds(await bundle(wired, shop_id, headers, done))
    await _move(wired, shop_id, headers, done, "complete")

    assert in_progress == []
    for visit_id in (canceled, done):
        assert kinds(await bundle(wired, shop_id, headers, visit_id)) == []
    assert await count(wired, "customer_forms") == 0


async def test_직원도_부를_수_있고_없는_방문과_다른_매장의_방문은_404(wired):
    shop_id, owner, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)
    other_shop, other, _ = await _shop(wired, "다른 매장", "다른 사장", operator)
    customer_id, pet_id = await _family(wired, shop_id, owner, _pet(birth_year=SENIOR_YEAR))
    visit_id = await _book(wired, shop_id, owner, customer_id, pet_id)

    assert kinds(await bundle(wired, shop_id, staff, visit_id)) == ["reservation", "consent"]
    assert error_of(await bundle(wired, shop_id, owner, 999_999_999)) == (404, "VISIT_NOT_FOUND")
    assert error_of(await bundle(wired, other_shop, other, visit_id)) == (404, "VISIT_NOT_FOUND")
    assert (await bundle(wired, shop_id, other, visit_id)).status_code in (403, 404)


async def test_로그에_주소와_보내는_글이_없다(wired, caplog):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR, conditions=[HEART]))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)

    with caplog.at_level(logging.DEBUG):
        response = await bundle(wired, shop_id, headers, visit_id)

    token = response.json()["parts"][1]["text"].rsplit("/f/", 1)[1].strip()
    assert len(token) == 43
    assert token not in caplog.text and "예약이 접수됐어요" not in caplog.text


async def test_이미_보낸_링크가_있으면_묶음은_그것을_쓰고_새로_만들었다고_하지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id, days=3)
    sent = (await send(wired, shop_id, headers, pet_id, for_date=_day(3))).json()

    got = (await bundle(wired, shop_id, headers, visit_id)).json()

    assert got["created_form_id"] is None and sent["url"] in got["parts"][1]["text"]


# --- ⑭ 반복 예약 -------------------------------------------------------------------------------------------------------

async def _series(wired, shop_id, headers, customer_id, pet_id, count=3):
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers, json={
        "customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(3, 14),
        "repeat": {"interval_weeks": 4, "count": count}})
    assert booked.status_code == 201, booked.text
    return [v["visit_id"] for v in booked.json()["visits"]]


def _series_lines(text: str) -> list[str]:
    return [line for line in text.split("\n") if line.startswith("· ")]


async def test_반복_묶음의_첫_회차로_부르면_예약_토막에_회차가_전부_있다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet())
    first, *_ = await _series(wired, shop_id, headers, customer_id, pet_id)

    response = await bundle(wired, shop_id, headers, first)
    assert kinds(response) == ["reservation"]
    text = response.json()["parts"][0]["text"]
    assert "4주마다 3번 예약했어요" in text
    assert len(_series_lines(text)) == 3


async def test_둘째_회차로_부르면_그_뒤만이고_취소한_회차는_빠진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet())
    first, second, third, fourth = await _series(wired, shop_id, headers, customer_id, pet_id, count=4)
    canceled = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers, json={
        "visit_ids": [third], "action": "cancel", "cancel_reason": "customer_request"})
    assert canceled.status_code == 200, canceled.text

    text = (await bundle(wired, shop_id, headers, second)).json()["parts"][0]["text"]
    assert "4주마다 2번 예약했어요" in text and len(_series_lines(text)) == 2
    last = (await bundle(wired, shop_id, headers, fourth)).json()["parts"][0]["text"]
    assert "주마다" not in last   # 남은 회차가 하나면 목록이 없다
