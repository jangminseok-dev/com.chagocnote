"""카톡 예약 초안(POST /visit-drafts)을 실제 배선(허브 포트 조립·DB·매장 접근 확인)으로 확인한다. 첫 테스트는 테넌트 격리다."""
import logging
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
PET = {
    "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True,
}
TEXT = "안녕하세요 내일 오후 2시 콩이 목욕 가능할까요?"


async def _family(wired, shop_id, headers, name="김민지", phone="010-1234-5678", pets=("콩이", "두부")):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers",
        json={"customer": {"name": name, "phone": phone, "marketing_consent": True}, "pet": {**PET, "name": pets[0]}},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    customer_id = response.json()["customer"]["customer_id"]
    pet_ids = [response.json()["pets"][0]["pet_id"]]
    for pet_name in pets[1:]:
        added = await wired.api.post(
            f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": pet_name}, headers=headers
        )
        assert added.status_code == 201, added.text
        pet_ids.append(added.json()["pet"]["pet_id"])
    return customer_id, pet_ids


async def _draft(wired, shop_id, headers, text=TEXT):
    return await wired.api.post(f"/v1/shops/{shop_id}/visit-drafts", json={"text": text}, headers=headers)


async def test_다른_매장의_가족은_후보에_오르지_않는다(wired):
    """V1 — B매장에 콩이가 있어도 A매장의 초안에는 없다. B매장 경로는 403."""
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    await _family(wired, b_shop, b)

    mine = await _draft(wired, a_shop, a)
    assert mine.status_code == 200, mine.text
    assert (mine.json()["customer_candidates"], mine.json()["pet_ids"], mine.json()["guessed"]["who"]) == ([], [], True)
    assert error_of(await _draft(wired, b_shop, a)) == (403, "NOT_A_MEMBER")


async def test_실제_배선으로_후보_메뉴_날짜_시각을_채운다(wired, caplog):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, (kong, dubu) = await _family(wired, shop_id, headers)
    await _family(wired, shop_id, headers, name="박서준", phone="010-9876-5678", pets=("보리",))
    menus = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"]
    bath = next(m["menu_id"] for m in menus if m["name"] == "목욕")
    tomorrow = (datetime.now(SEOUL).date() + timedelta(days=1)).isoformat()

    with caplog.at_level(logging.DEBUG):
        response = await _draft(wired, shop_id, headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["date"], body["time"], body["menu_ids"]) == (tomorrow, "14:00", [bath])
    assert body["customer_candidates"] == [{
        "customer_id": customer_id, "name": "김민지", "phone_masked": "010-12··-5678",
        "pets": [{"pet_id": kong, "name": "콩이"}, {"pet_id": dubu, "name": "두부"}], "matched_pet_ids": [kong],
    }]
    assert (body["pet_ids"], body["guessed"]) == ([kong], {"date": False, "time": False, "who": False, "menu": False})
    # V9 — 글의 낱말이 어느 로그에도 남지 않는다.
    assert not any("콩이" in record.getMessage() for record in caplog.records)
    assert "콩이" not in caplog.text


async def test_직원도_초안을_받고_초안은_아무것도_저장하지_않는다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    await _family(wired, shop_id, headers)
    tomorrow = (datetime.now(SEOUL).date() + timedelta(days=1)).isoformat()

    response = await _draft(wired, shop_id, bearer(staff["access_token"]))
    assert response.status_code == 200, response.text
    assert len(response.json()["customer_candidates"]) == 1
    day = await wired.api.get(f"/v1/shops/{shop_id}/visits?date={tomorrow}", headers=headers)
    assert day.json()["items"] == []
