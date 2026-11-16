"""문진표 끝에서 받아 맡아 둔 서명이 등록·반영 때 그 아이에게 옮겨 붙는다(⑪-C1b)."""
import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import count, document
from tests.integration.test_form_settings_wiring import put
from tests.integration.test_intake_answers_wiring import listed, one, pet_body, received
from tests.integration.test_intake_forms_wiring import issue, token_of
from tests.integration.test_public_intake_wiring import read, rows, signed
from tests.integration.test_visit_checks_wiring import _day, _family, _pet, _shop

pytestmark = pytest.mark.integration

SENIOR = 2014        # 2026년에 12살 — 노령 토막이 붙는다


def new_customer(answer_id, phone="010-9999-0000", **pet):
    return {"customer": {"name": "박새롬", "phone": phone, "marketing_consent": False},
            "pet": pet_body(birth_year=SENIOR) | pet, "intake_answer_id": answer_id}


async def register(wired, shop_id, headers, body):
    return await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers, json=body)


async def signatures_of(wired, shop_id, headers, pet_id):
    response = await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}/consent-signatures", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def test_받은_문진표_한_장에_맡아_둔_서명이_보인다_그림과_이름은_싣지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    signed_answer = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)
    plain = await received(wired, shop_id, headers, name="라떼")

    consent = (await one(wired, shop_id, headers, signed_answer)).json()["consent"]
    assert consent == {"signed_on": _day(0).isoformat(), "parts": ["basic", "senior"]}
    assert (await one(wired, shop_id, headers, plain)).json()["consent"] is None


async def test_새_손님의_답으로_등록하면_서명이_그_아이의_동의가_된다(wired):
    shop_id, headers, _ = await _shop(wired)
    answer_id = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)

    created = await register(wired, shop_id, headers, new_customer(answer_id))

    assert created.status_code == 201, created.text
    pet_id = created.json()["pets"][0]["pet_id"]
    (item,) = await signatures_of(wired, shop_id, headers, pet_id)
    assert (item["channel"], item["signer_name"], item["parts"]) == ("intake", "박새롬", ["basic", "senior"])
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["grooming_consent_on"] == _day(0).isoformat()           # 서명한 날
    assert error_of(await document(wired, shop_id, headers, pet_id)) == (409, "CONSENT_UP_TO_DATE")
    assert await rows(wired, "SELECT intake_answer_id, customer_id IS NOT NULL FROM consent_signatures") == [
        (None, True)]
    assert await count(wired, "intake_answers") == 0


async def test_받은_날은_등록한_날이_아니라_서명한_날이다(wired):
    shop_id, headers, _ = await _shop(wired)
    answer_id = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)
    async with wired.engine.begin() as conn:
        from sqlalchemy import text
        await conn.execute(text("UPDATE consent_signatures SET signed_at = now() - interval '3 days'"))

    created = await register(wired, shop_id, headers, new_customer(answer_id))

    pet_id = created.json()["pets"][0]["pet_id"]
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["grooming_consent_on"] == _day(-3).isoformat()


async def test_등록하며_지병을_더하면_맡아_둔_서명은_자기가_보인_것만_덮고_지병_토막이_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    answer_id = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)

    created = await register(wired, shop_id, headers, new_customer(
        answer_id, no_known_conditions=False,
        conditions=[{"type_code": "heart_disease", "custom_label": None, "note": None}]))

    assert created.status_code == 201, created.text
    pet_id = created.json()["pets"][0]["pet_id"]
    doc = (await document(wired, shop_id, headers, pet_id)).json()
    assert [p["parts"] for p in doc["pets"]] == [["condition"]]          # 바뀐 토막만
    assert doc["previous_consent_on"] == _day(0).isoformat()


async def test_답에_없던_노령이_되면_노령_토막이_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    await put(wired, shop_id, headers, intake_consent_all=True)
    answer_id = await received(wired, shop_id, headers, sign=["basic"])          # 2022년생 — 노령이 아니었다

    created = await register(wired, shop_id, headers, new_customer(answer_id, birth_year=2012))

    pet_id = created.json()["pets"][0]["pet_id"]
    assert [p["parts"] for p in (await document(wired, shop_id, headers, pet_id)).json()["pets"]] == [["senior"]]


async def test_등록이_실패하면_서명은_맡아_둔_채_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    await _family(wired, shop_id, headers, _pet(), phone="010-9999-0000")
    answer_id = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)

    taken = await register(wired, shop_id, headers, new_customer(answer_id))

    assert taken.status_code == 409
    assert await rows(wired, "SELECT customer_id, intake_answer_id FROM consent_signatures") == [(None, answer_id)]
    assert (await one(wired, shop_id, headers, answer_id)).json()["consent"] is not None


async def test_번호가_같은_고객의_새_아이로_더해도_서명이_옮겨_붙는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, _ = await _family(wired, shop_id, headers, _pet(), phone="010-9999-0000")
    answer_id = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)

    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers,
                                 json=pet_body(birth_year=SENIOR) | {"intake_answer_id": answer_id})

    assert added.status_code == 201, added.text
    pet_id = added.json()["pet"]["pet_id"]
    assert [i["channel"] for i in await signatures_of(wired, shop_id, headers, pet_id)] == ["intake"]
    assert added.json()["pet"]["grooming_consent_on"] == _day(0).isoformat()


async def test_살아_있는_동의가_있는_아이의_다시_받기는_받은_날을_옮기지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    await put(wired, shop_id, headers, intake_consent_all=True)
    _, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[]))
    marked = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers,
                                 json={"received_on": _day(-10).isoformat()})
    assert marked.status_code == 200, marked.text
    token = token_of(await issue(wired, shop_id, headers, pet_id=pet_id))
    opened = (await read(wired, token)).json()
    sent = await wired.api.post("/v1/public/form/intake", headers={"X-Form-Token": token}, json={
        "guardian": None, "pet": {"weight_kg": 5.1}, "extras": [], "privacy_agreed": True,
        "consent": signed(opened, ["basic"])})
    assert sent.status_code == 204, sent.text
    (item,) = await listed(wired, shop_id, headers)

    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json=_pet(conditions=[]) | {"weight_kg": 5.1, "intake_answer_id": item["answer_id"]})

    assert updated.status_code == 200, updated.text
    assert updated.json()["pet"]["grooming_consent_on"] == _day(-10).isoformat()
    assert [i["channel"] for i in await signatures_of(wired, shop_id, headers, pet_id)] == ["intake"]


async def test_답을_지우거나_익명화하면_맡아_둔_서명도_사라진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, _ = await _family(wired, shop_id, headers, _pet(), phone="010-9999-0000")
    matched = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR)
    other = await received(wired, shop_id, headers, sign=["basic", "senior"], birth_year=SENIOR,
                           guardian={"name": "남", "phone": "010-7777-0000"})
    assert await count(wired, "consent_signatures") == 2

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/intake-answers/{other}", headers=headers)).status_code == 204
    assert await rows(wired, "SELECT intake_answer_id FROM consent_signatures") == [(matched,)]

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204
    assert await count(wired, "consent_signatures") == 0
