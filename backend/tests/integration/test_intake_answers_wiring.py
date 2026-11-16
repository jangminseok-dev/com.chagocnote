"""받은 문진표와 등록을 실제 배선으로 확인한다(⑪-C) — 목록·한 장·지우기, 등록이 답을 지운다, 기한."""
import logging

import pytest
from sqlalchemy import text

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import count
from tests.integration.test_form_settings_wiring import put
from tests.integration.test_intake_forms_wiring import issue, token_of
from tests.integration.test_intake_settings_wiring import q, save
from tests.integration.test_public_intake_wiring import read, signed, submit
from tests.integration.test_visit_checks_wiring import _day, _family, _pet, _shop, _staff

pytestmark = pytest.mark.integration

ITEM_KEYS = {"answer_id", "mode", "pet_name", "guardian_name", "submitted_on", "matched_customer", "pet_id"}
DETAIL_KEYS = ITEM_KEYS | {
    "guardian_phone", "species", "breed", "sex", "neutered", "birth_date", "birth_year", "birth_unknown",
    "weight_kg", "no_known_conditions", "conditions", "dislikes", "style", "extras", "missing", "memo_draft",
    "memo_over", "consent"}


async def listed(wired, shop_id, headers):
    response = await wired.api.get(f"/v1/shops/{shop_id}/intake-answers", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["items"]


async def one(wired, shop_id, headers, answer_id):
    return await wired.api.get(f"/v1/shops/{shop_id}/intake-answers/{answer_id}", headers=headers)


async def received(wired, shop_id, headers, sign=None, **change):
    """새 손님용 링크를 보내고 답 하나를 받는다. 답의 ID 를 돌려준다. sign 은 끝의 동의서에서 읽은 토막(⑪-C1b)."""
    token = token_of(await issue(wired, shop_id, headers))
    if sign is not None:
        change["consent"] = signed((await read(wired, token)).json(), sign)
    sent = await submit(wired, token, **change)
    assert sent.status_code == 204, sent.text
    return (await listed(wired, shop_id, headers))[0]["answer_id"]


def pet_body(**change):
    return {"name": "모카", "species": "dog", "breed": "푸들", "sex": "male", "neutered": False,
            "birth_year": 2022, "weight_kg": 4.5, "no_known_conditions": True, "conditions": []} | change


async def test_받은_문진표의_목록과_한_장(wired):
    shop_id, headers, _ = await _shop(wired)
    must = (await save(wired, shop_id, headers, q("산책은 얼마나 하나요?", required=True))).json()["items"][0]
    answer_id = await received(
        wired, shop_id, headers, sign=["basic", "condition"], no_known_conditions=False,
        conditions=[{"type_code": "heart_disease", "custom_label": None, "note": "약 복용 중"}],
        extras=[{"question_id": must["question_id"], "body": "하루 한 번"}])

    (item,) = await listed(wired, shop_id, headers)
    assert set(item) == ITEM_KEYS
    assert (item["mode"], item["pet_name"], item["guardian_name"], item["submitted_on"], item["matched_customer"],
            item["pet_id"]) == ("new", "모카", "박새롬", _day(0).isoformat(), None, None)

    detail = (await one(wired, shop_id, headers, answer_id)).json()
    assert set(detail) == DETAIL_KEYS
    assert (detail["guardian_phone"], detail["species"], detail["breed"], detail["birth_year"], detail["weight_kg"]) == (
        "010-9999-0000", "dog", "푸들", 2022, 4.5)
    assert detail["conditions"] == [
        {"type_code": "heart_disease", "label": "심장 질환", "custom_label": None, "note": "약 복용 중"}]
    assert detail["extras"] == [{"label": "산책은 얼마나 하나요?", "body": "하루 한 번"}]
    assert detail["missing"] == []
    assert detail["memo_draft"] == "조심할 것: 드라이기 소리\n원하는 스타일: 곰돌이 컷\n산책은 얼마나 하나요?: 하루 한 번"
    assert detail["memo_over"] == 0


async def test_끈_칸과_모르겠어요는_빈_필수_칸으로_알려_준다(wired):
    shop_id, headers, _ = await _shop(wired)
    await put(wired, shop_id, headers, intake_hidden=["breed", "sex"])
    answer_id = await received(wired, shop_id, headers, weight_kg=None, weight_unknown=True)

    detail = (await one(wired, shop_id, headers, answer_id)).json()

    assert detail["missing"] == ["breed", "sex", "weight"]
    assert (detail["breed"], detail["sex"], detail["weight_kg"]) == (None, None, None)


async def test_새_고객으로_등록하면_답이_사라지고_같은_답으로_두_번_등록되지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    answer_id = await received(wired, shop_id, headers)
    body = {"customer": {"name": "박새롬", "phone": "010-9999-0000", "marketing_consent": False},
            "pet": pet_body(memo="조심할 것: 드라이기 소리"), "intake_answer_id": answer_id}

    first = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers, json=body)
    again = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers,
                                 json=body | {"customer": body["customer"] | {"phone": "010-8888-0000"}})

    assert first.status_code == 201, first.text
    assert error_of(again) == (404, "INTAKE_ANSWER_NOT_FOUND")
    assert await listed(wired, shop_id, headers) == []
    assert await count(wired, "intake_answers") == 0 and await count(wired, "customers") == 1
    assert error_of(await one(wired, shop_id, headers, answer_id)) == (404, "INTAKE_ANSWER_NOT_FOUND")


async def test_등록이_실패하면_답은_그대로_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    await _family(wired, shop_id, headers, _pet(), phone="010-9999-0000")
    answer_id = await received(wired, shop_id, headers)

    # 번호가 같은 고객이 이미 있다 — 새 고객으로는 등록되지 않는다(조용히 덮어쓰지 않는다).
    taken = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers, json={
        "customer": {"name": "박새롬", "phone": "010-9999-0000", "marketing_consent": False},
        "pet": pet_body(), "intake_answer_id": answer_id})

    assert taken.status_code == 409
    (item,) = await listed(wired, shop_id, headers)
    assert item["answer_id"] == answer_id and item["matched_customer"]["name"] == "김민지"
    assert await count(wired, "pets") == 1


async def test_새_아이로_더하기와_다시_받은_답을_반영하기도_답을_지운다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet())
    add_token = token_of(await issue(wired, shop_id, headers, customer_id=customer_id))
    update_token = token_of(await issue(wired, shop_id, headers, pet_id=pet_id))
    assert (await submit(wired, add_token, guardian=None)).status_code == 204
    assert (await wired.api.post("/v1/public/form/intake", headers={"X-Form-Token": update_token}, json={
        "guardian": None, "pet": {"weight_kg": 5.1}, "extras": [], "privacy_agreed": True})).status_code == 204
    by_mode = {item["mode"]: item for item in await listed(wired, shop_id, headers)}
    assert (by_mode["add_pet"]["matched_customer"], by_mode["update"]["pet_id"], by_mode["update"]["pet_name"]) == (
        {"customer_id": customer_id, "name": "김민지"}, pet_id, "콩이")

    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers,
                                 json=pet_body() | {"intake_answer_id": by_mode["add_pet"]["answer_id"]})
    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json=_pet() | {"weight_kg": 5.1, "intake_answer_id": by_mode["update"]["answer_id"]})

    assert (added.status_code, updated.status_code) == (201, 200), (added.text, updated.text)
    assert updated.json()["pet"]["weight_kg"] == 5.1
    assert await listed(wired, shop_id, headers) == [] and await count(wired, "intake_answers") == 0


async def test_지우기와_권한과_다른_매장(wired):
    shop_id, owner, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)
    other_shop, other, _ = await _shop(wired, "다른 매장", "다른 사장", operator)
    answer_id = await received(wired, shop_id, staff)

    assert await listed(wired, other_shop, other) == []
    assert error_of(await one(wired, other_shop, other, answer_id)) == (404, "INTAKE_ANSWER_NOT_FOUND")
    assert error_of(await wired.api.delete(f"/v1/shops/{other_shop}/intake-answers/{answer_id}", headers=other)) == (
        404, "INTAKE_ANSWER_NOT_FOUND")
    stolen = await wired.api.post(f"/v1/shops/{other_shop}/customers", headers=other, json={
        "customer": {"name": "남", "phone": "010-7777-0000", "marketing_consent": False},
        "pet": pet_body(), "intake_answer_id": answer_id})
    assert error_of(stolen) == (404, "INTAKE_ANSWER_NOT_FOUND") and await count(wired, "customers") == 0

    assert (await one(wired, shop_id, staff, answer_id)).status_code == 200
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/intake-answers/{answer_id}", headers=staff)).status_code == 204
    assert await listed(wired, shop_id, owner) == [] and await count(wired, "intake_answers") == 0


async def test_보관_기간이_지난_답은_없는_것으로_치고_주기_작업이_지우며_수만_로그에_적는다(wired, caplog):
    from customer.dependencies.form_sweeper_provider import sweep_forms_once

    shop_id, headers, _ = await _shop(wired)
    await put(wired, shop_id, headers, intake_keep_days=7)
    old = await received(wired, shop_id, headers)
    fresh = await received(wired, shop_id, headers, name="라떼")
    async with wired.engine.begin() as conn:
        await conn.execute(text("UPDATE intake_answers SET submitted_at = now() - interval '8 days' WHERE id = :id"),
                           {"id": old})

    assert [item["answer_id"] for item in await listed(wired, shop_id, headers)] == [fresh]
    assert error_of(await one(wired, shop_id, headers, old)) == (404, "INTAKE_ANSWER_NOT_FOUND")
    assert await count(wired, "intake_answers") == 2

    with caplog.at_level(logging.INFO):
        removed = await sweep_forms_once()

    assert removed == 1 and await count(wired, "intake_answers") == 1
    assert "박새롬" not in caplog.text and "모카" not in caplog.text


async def test_익명화하면_그_고객에_이어_둔_답이_지워진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(), phone="010-9999-0000")
    await received(wired, shop_id, headers)                                    # 번호로 이어진 답
    update_token = token_of(await issue(wired, shop_id, headers, pet_id=pet_id))
    assert (await wired.api.post("/v1/public/form/intake", headers={"X-Form-Token": update_token}, json={
        "guardian": None, "pet": {"weight_kg": 5.1}, "extras": [], "privacy_agreed": True})).status_code == 204
    assert await count(wired, "intake_answers") == 2

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204

    assert await count(wired, "intake_answers") == 0


# --- 최종 검토 ------------------------------------------------------------------------------------------------------

async def test_답은_그_답을_받은_대상에게만_쓸_수_있다_어긋나면_404_이고_답이_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    one_customer, one_pet = await _family(wired, shop_id, headers, _pet())
    two_customer, two_pet = await _family(wired, shop_id, headers, _pet(name="보리"), phone="010-2222-3333")
    add_token = token_of(await issue(wired, shop_id, headers, customer_id=one_customer))
    update_token = token_of(await issue(wired, shop_id, headers, pet_id=one_pet))
    assert (await submit(wired, add_token, guardian=None)).status_code == 204
    assert (await wired.api.post("/v1/public/form/intake", headers={"X-Form-Token": update_token}, json={
        "guardian": None, "pet": {"weight_kg": 5.1}, "extras": [], "privacy_agreed": True})).status_code == 204
    guest = await received(wired, shop_id, headers, guardian={"name": "박새롬", "phone": "010-9999-0000"})
    by_mode = {item["mode"]: item["answer_id"] for item in await listed(wired, shop_id, headers)}

    wrong = [
        # 고객 1에게 보낸 링크의 답으로 고객 2의 아이를 더한다
        await wired.api.post(f"/v1/shops/{shop_id}/customers/{two_customer}/pets", headers=headers,
                             json=pet_body() | {"intake_answer_id": by_mode["add_pet"]}),
        # 아이 1의 다시 받기 답으로 아이 2를 고친다
        await wired.api.put(f"/v1/shops/{shop_id}/pets/{two_pet}", headers=headers,
                            json=_pet(name="보리") | {"intake_answer_id": by_mode["update"]}),
        # 새 손님의 답으로 있는 아이를 고친다
        await wired.api.put(f"/v1/shops/{shop_id}/pets/{one_pet}", headers=headers,
                            json=_pet() | {"intake_answer_id": guest}),
        # 등록된 고객의 새 아이용 답으로 새 고객을 등록한다
        await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers, json={
            "customer": {"name": "남", "phone": "010-7777-0000", "marketing_consent": False},
            "pet": pet_body(), "intake_answer_id": by_mode["add_pet"]}),
    ]

    assert [error_of(response) for response in wrong] == [(404, "INTAKE_ANSWER_NOT_FOUND")] * 4
    assert await count(wired, "intake_answers") == 3 and await count(wired, "pets") == 2
    # 새 손님의 답은 등록된 고객의 새 아이로 더할 수 있다(번호가 같은 고객이 뒤에 등록됐을 때).
    ok = await wired.api.post(f"/v1/shops/{shop_id}/customers/{one_customer}/pets", headers=headers,
                              json=pet_body() | {"intake_answer_id": guest})
    assert ok.status_code == 201, ok.text


async def test_익명화하면_그_고객의_번호로_낸_답도_지워진다_낼_때는_고객이_없었어도(wired):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))
    assert (await submit(wired, token)).status_code == 204
    assert (await submit(wired, token, guardian=None, name="라떼")).status_code == 204
    first = (await listed(wired, shop_id, headers))[1]["answer_id"]
    registered = await wired.api.post(f"/v1/shops/{shop_id}/customers", headers=headers, json={
        "customer": {"name": "박새롬", "phone": "010-9999-0000", "marketing_consent": False},
        "pet": pet_body(), "intake_answer_id": first})
    customer_id = registered.json()["customer"]["customer_id"]
    await received(wired, shop_id, headers, guardian={"name": "다른 손님", "phone": "010-5555-0000"})
    assert await count(wired, "intake_answers") == 2          # 같은 번호의 둘째 답, 다른 손님의 답

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204

    assert [item["guardian_name"] for item in await listed(wired, shop_id, headers)] == ["다른 손님"]
