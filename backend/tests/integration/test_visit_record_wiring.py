"""미용 기록을 실제 배선(프로바이더·허브 포트 조립·DB 커밋·MinIO)으로 확인한다. 첫 테스트는 테넌트 격리다."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    ready_photo,
    shop_with_owner,
)

pytestmark = pytest.mark.integration

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {"name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True, "birth_year": 2021,
       "weight_kg": 3.2, "no_known_conditions": True}


def _at(days: int, hour: int) -> str:
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


async def _family(wired, shop_id, headers):
    response = await wired.api.post(f"/v1/shops/{shop_id}/customers", json={"customer": CUSTOMER, "pet": PET},
                                    headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["customer"]["customer_id"], response.json()["pets"][0]["pet_id"]


async def _visit(wired, shop_id, headers, customer_id, pet_id, days=-1, start=True):
    """days 날 뒤 11시 예약. start 면 미용을 시작한다(어제 방문이라 자정을 넘기지 않는다 — 시각과 상관없이 돈다)."""
    booked = await wired.api.post(f"/v1/shops/{shop_id}/visits", headers=headers,
                                  json={"customer_id": customer_id, "pet_ids": [pet_id], "starts_at": _at(days, 11)})
    assert booked.status_code == 201, booked.text
    visit_id = booked.json()["visits"][0]["visit_id"]
    if start:
        started = await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", headers=headers,
                                       json={"visit_ids": [visit_id], "action": "start"})
        assert started.status_code == 200, started.text
    return visit_id


async def _shop(wired, name="Hiss Haus", owner="사장님", operator=None):
    operator = operator or await make_operator(wired)
    shop_id, login = await shop_with_owner(wired, operator, name, owner)
    return shop_id, bearer(login["access_token"]), operator


async def _staff(wired, shop_id, owner_headers):
    staff = await wired.login("직원")
    code = (await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=owner_headers)).json()["code"]
    assert (await accept_invite(wired, staff, code)).status_code == 200
    return bearer(staff["access_token"])


async def test_다른_매장의_방문과_미디어로는_기록을_쓸_수_없다(wired, media_storage):
    a_shop, a, operator = await _shop(wired, "A 매장", "A사장")
    b_shop, b, _ = await _shop(wired, "B 매장", "B사장", operator)
    a_visit = await _visit(wired, a_shop, a, *await _family(wired, a_shop, a))
    b_visit = await _visit(wired, b_shop, b, *await _family(wired, b_shop, b))
    b_photo = await ready_photo(wired, b_shop, b)

    assert error_of(await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_visit}/record", json={}, headers=a)) == (
        403, "NOT_A_MEMBER")
    assert error_of(await wired.api.put(f"/v1/shops/{a_shop}/visits/{b_visit}/record", json={}, headers=a)) == (
        404, "VISIT_NOT_FOUND")
    theirs = await wired.api.put(f"/v1/shops/{a_shop}/visits/{a_visit}/record", headers=a,
                                 json={"media": [{"media_id": b_photo, "phase": "after", "sort_order": 0}]})
    assert error_of(theirs) == (404, "MEDIA_NOT_FOUND")


async def test_기록을_쓰고_고치면_버전이_오르고_빠진_사진은_놓이고_몸무게가_현재_몸무게가_된다(wired, media_storage):
    shop_id, o, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, o)
    visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
    bath = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=o)).json()["items"][0]["menu_id"]
    before, after = await ready_photo(wired, shop_id, o), await ready_photo(wired, shop_id, o)
    body = {"weight_kg": 3.4, "care_note": "눈물 자국 관리", "internal_note": "발 만지면 예민", "payment_method": "card",
            "total_amount": 25000, "items": [{"menu_id": bath, "amount": 28000}],
            "media": [{"media_id": before, "phase": "before", "sort_order": 0},
                      {"media_id": after, "phase": "after", "sort_order": 0}]}
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/record"

    first = await wired.api.put(path, json=body, headers=o)
    assert first.status_code == 200, first.text
    saved = first.json()
    assert (saved["version"], saved["total_amount"], [i["amount"] for i in saved["items"]]) == (1, 25000, [28000])
    assert [(m["media_id"], m["phase"]) for m in saved["media"]] == [(before, "before"), (after, "after")]
    assert all(m["thumb_url"].startswith("http") for m in saved["media"])
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=o)).json()["pet"]
    assert pet["weight_kg"] == 3.4

    assert error_of(await wired.api.put(path, json=body, headers=o)) == (409, "RECORD_VERSION_CONFLICT")
    second = await wired.api.put(path, headers=o, json={**body, "version": 1, "media": body["media"][1:]})
    assert (second.status_code, second.json()["version"]) == (200, 2)
    async with wired.engine.connect() as conn:
        attached = dict((await conn.execute(text("SELECT id, attached_at IS NOT NULL FROM media_objects"))).all())
    assert attached == {before: False, after: True}

    other_visit = await _visit(wired, shop_id, o, customer_id, pet_id, days=-2)
    taken = await wired.api.put(f"/v1/shops/{shop_id}/visits/{other_visit}/record", headers=o,
                                json={"media": [{"media_id": after, "phase": "after", "sort_order": 0}]})
    assert error_of(taken) == (409, "MEDIA_ALREADY_ATTACHED")


async def test_예약만_된_방문에는_기록을_쓸_수_없다(wired, media_storage):
    shop_id, o, _ = await _shop(wired)
    visit_id = await _visit(wired, shop_id, o, *await _family(wired, shop_id, o), days=1, start=False)
    response = await wired.api.put(f"/v1/shops/{shop_id}/visits/{visit_id}/record", json={}, headers=o)
    assert error_of(response) == (409, "VISIT_NO_RECORD_YET")


async def test_덧붙이기는_기록을_만들고_다시_보내도_한_번이며_기록은_사장만_지운다(wired, media_storage):
    shop_id, o, _ = await _shop(wired)
    s = await _staff(wired, shop_id, o)
    customer_id, pet_id = await _family(wired, shop_id, o)
    visit_id = await _visit(wired, shop_id, o, customer_id, pet_id)
    first, second = await ready_photo(wired, shop_id, s), await ready_photo(wired, shop_id, s)
    path = f"/v1/shops/{shop_id}/visits/{visit_id}/record"

    appended = await wired.api.post(f"{path}/media", json={"media_id": first, "phase": "before"}, headers=s)
    again = await wired.api.post(f"{path}/media", json={"media_id": first, "phase": "before"}, headers=s)
    assert [(r.status_code, r.json()["version"], len(r.json()["media"])) for r in (appended, again)] == [(200, 1, 1)] * 2
    # 폼이 읽은 버전으로 저장하는 사이 대기열이 한 장을 더 붙이면, 폼의 저장은 409 가 된다.
    await wired.api.post(f"{path}/media", json={"media_id": second, "phase": "after"}, headers=s)
    stale = await wired.api.put(path, headers=s, json={"version": 1, "weight_kg": 3.1,
                                                         "media": [{"media_id": first, "phase": "before", "sort_order": 0}]})
    assert error_of(stale) == (409, "RECORD_VERSION_CONFLICT")

    assert error_of(await wired.api.delete(path, headers=s)) == (403, "PERMISSION_DENIED")
    assert (await wired.api.delete(path, headers=o)).status_code == 204
    assert error_of(await wired.api.delete(path, headers=o)) == (404, "RECORD_NOT_FOUND")
    async with wired.engine.connect() as conn:
        attached = (await conn.execute(text("SELECT count(*) FROM media_objects WHERE attached_at IS NOT NULL"))).scalar()
    assert attached == 0
