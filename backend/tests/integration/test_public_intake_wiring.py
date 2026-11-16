"""로그인 없는 문진표 읽기와 내기를 실제 배선으로 확인한다(⑪-C). 토큰은 헤더로만 간다."""
import logging

import pytest
from sqlalchemy import text

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import count
from tests.integration.test_form_settings_wiring import put
from tests.integration.test_intake_forms_wiring import issue, token_of
from tests.integration.test_intake_settings_wiring import q, save
from tests.integration.test_visit_checks_wiring import _family, _pet, _shop

pytestmark = pytest.mark.integration

OPEN_KEYS = {"kind", "state", "shop", "mode", "pet_name", "fields", "questions", "condition_types", "answered"}
ALL_FIELDS = ["species", "breed", "sex", "neutered", "birth", "weight", "dislikes", "style"]


def _with(token):
    return {"X-Form-Token": token}


async def read(wired, token):
    return await wired.api.get("/v1/public/form", headers=_with(token))


def answer(**change):
    body = {
        "guardian": {"name": "박새롬", "phone": "010-9999-0000"},
        "pet": {"name": "모카", "species": "dog", "breed": "푸들", "sex": "male", "neutered": False,
                "birth_date": None, "birth_year": 2022, "birth_unknown": False, "weight_kg": 4.5,
                "weight_unknown": False, "no_known_conditions": True, "conditions": [],
                "dislikes": "드라이기 소리", "style": "곰돌이 컷"},
        "extras": [], "privacy_agreed": True, "done": False,
    }
    for key, value in change.items():
        if key in body["pet"]:
            body["pet"][key] = value
        else:
            body[key] = value
    return body


async def submit(wired, token, **change):
    return await wired.api.post("/v1/public/form/intake", headers=_with(token), json=answer(**change))


async def rows(wired, sql):
    async with wired.engine.connect() as conn:
        return [tuple(row) for row in await conn.execute(text(sql))]


async def test_새_손님의_문진표를_열면_켜진_칸과_지병_종류가_오고_내면_받은_문진표가_된다(wired):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))

    opened = await read(wired, token)
    assert opened.status_code == 200 and set(opened.json()) == OPEN_KEYS
    body = opened.json()
    assert (body["kind"], body["state"], body["shop"], body["mode"], body["pet_name"], body["answered"]) == (
        "intake", "open", {"name": "Hiss Haus"}, "new", None, 0)
    assert body["fields"] == ALL_FIELDS and body["questions"] == []
    assert {"code", "label"} == set(body["condition_types"][0]) and len(body["condition_types"]) > 3
    assert opened.headers["cache-control"] == "private, no-store" and "noindex" in opened.headers["x-robots-tag"]

    assert (await submit(wired, token)).status_code == 204

    assert await rows(wired, "SELECT guardian_name, guardian_phone, pet_name, species, breed, birth_year, weight_kg::float, "
                             "no_known_conditions, dislikes, style, matched_customer_id FROM intake_answers") == [
        ("박새롬", "01099990000", "모카", "dog", "푸들", 2022, pytest.approx(4.5), True, "드라이기 소리", "곰돌이 컷", None)]
    assert await count(wired, "customers") == 0 and await count(wired, "pets") == 0     # 고객 표는 건드리지 않는다
    assert (await read(wired, token)).json()["answered"] == 1                           # 다른 아이도 적을 수 있다


async def test_둘째_아이는_보호자_칸을_묻지_않고_다_적었어요를_보내면_닫힌다(wired):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))
    assert (await submit(wired, token)).status_code == 204

    second = await submit(wired, token, guardian=None, name="라떼", done=True)

    assert second.status_code == 204
    assert await rows(wired, "SELECT pet_name, guardian_name, guardian_phone FROM intake_answers ORDER BY id") == [
        ("모카", "박새롬", "01099990000"), ("라떼", "박새롬", "01099990000")]
    closed = await read(wired, token)
    assert set(closed.json()) == {"kind", "state", "shop", "submitted_on"}
    assert (closed.json()["kind"], closed.json()["state"]) == ("intake", "submitted")
    assert error_of(await submit(wired, token, name="셋째")) == (410, "FORM_CLOSED")


async def test_한_링크에_아이는_열_마리까지다(wired):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))
    for n in range(10):
        assert (await submit(wired, token, name=f"아이{n}")).status_code == 204, n

    # 열 마리째에서 링크가 닫힌다(열한 번째 제출은 접속 주소당 10분에 10번의 한도에도 걸린다).
    assert (await read(wired, token)).json()["state"] == "submitted"
    assert await count(wired, "intake_answers") == 10


async def test_번호가_같은_고객이_있으면_미리_이어_둔다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, _ = await _family(wired, shop_id, headers, _pet(), phone="010-9999-0000")
    token = token_of(await issue(wired, shop_id, headers))

    assert (await submit(wired, token)).status_code == 204

    assert await rows(wired, "SELECT matched_customer_id FROM intake_answers") == [(customer_id,)]
    assert await count(wired, "customers") == 1


async def test_새_아이는_보호자를_묻지_않고_다시_받기는_아이_이름만_보이고_한_번_내면_닫힌다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[]))
    add_token = token_of(await issue(wired, shop_id, headers, customer_id=customer_id))
    update_token = token_of(await issue(wired, shop_id, headers, pet_id=pet_id))

    add, update = (await read(wired, add_token)).json(), (await read(wired, update_token)).json()
    assert (add["mode"], add["pet_name"]) == ("add_pet", None)
    assert (update["mode"], update["pet_name"]) == ("update", "콩이")
    assert set(update) == OPEN_KEYS            # 지금 값(품종·몸무게·지병)은 싣지 않는다

    assert (await submit(wired, add_token, guardian=None)).status_code == 204
    only_weight = {"guardian": None, "pet": {"weight_kg": 5.1}, "extras": [], "privacy_agreed": True, "done": False}
    changed = await wired.api.post("/v1/public/form/intake", headers=_with(update_token), json=only_weight)
    assert changed.status_code == 204, changed.text

    assert await rows(wired, "SELECT pet_name, weight_kg::float, species, matched_customer_id FROM intake_answers ORDER BY id") == [
        ("모카", pytest.approx(4.5), "dog", customer_id), (None, pytest.approx(5.1), None, customer_id)]
    assert (await read(wired, update_token)).json()["state"] == "submitted"
    assert (await read(wired, add_token)).json()["state"] == "open"
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["weight_kg"] == 3.2             # 저절로 반영하지 않는다


async def test_매장이_끈_칸은_보이지_않고_받지_않으며_더한_질문은_답을_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    await put(wired, shop_id, headers, intake_hidden=["weight", "style"])
    saved = (await save(wired, shop_id, headers, q("산책은 얼마나 하나요?", required=True), q("간식은요?"))).json()["items"]
    must, optional = (item["question_id"] for item in saved)
    token = token_of(await issue(wired, shop_id, headers))

    opened = (await read(wired, token)).json()
    assert opened["fields"] == ["species", "breed", "sex", "neutered", "birth", "dislikes"]
    assert opened["questions"] == [{"question_id": must, "label": "산책은 얼마나 하나요?", "required": True},
                                   {"question_id": optional, "label": "간식은요?", "required": False}]

    assert error_of(await submit(wired, token)) == (422, "VALIDATION_ERROR")          # 필수 질문의 답이 없다
    sent = await submit(wired, token, extras=[{"question_id": must, "body": "하루 한 번"},
                                              {"question_id": 999_999, "body": "지운 질문의 답"}])
    assert sent.status_code == 204, sent.text

    assert await rows(wired, "SELECT weight_kg, style, dislikes FROM intake_answers") == [(None, None, "드라이기 소리")]
    assert await rows(wired, "SELECT question_id, body FROM intake_answer_extras") == [(must, "하루 한 번")]


async def test_지병을_고르면_한_줄씩_함께_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))

    sent = await submit(wired, token, no_known_conditions=False, conditions=[
        {"type_code": "heart_disease", "custom_label": None, "note": "약 복용 중"},
        {"type_code": "other", "custom_label": "슬개골", "note": None}])

    assert sent.status_code == 204, sent.text
    assert await rows(wired, "SELECT type_code, custom_label, note FROM intake_answer_conditions ORDER BY position") == [
        ("heart_disease", None, "약 복용 중"), ("other", "슬개골", None)]


@pytest.mark.parametrize("change", [
    {"privacy_agreed": False}, {"guardian": None}, {"name": ""}, {"species": "bird"}, {"birth_year": 1800},
    {"weight_kg": None}, {"no_known_conditions": False},
    {"no_known_conditions": False, "conditions": [{"type_code": "flu", "custom_label": None, "note": None}]},
    {"dislikes": "가" * 201}, {"name": "가" * 51},
])
async def test_틀린_답은_422_이고_아무것도_쓰지_않는다(wired, change):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))

    assert (await submit(wired, token, **change)).status_code == 422
    assert await count(wired, "intake_answers") == 0
    assert (await read(wired, token)).json()["answered"] == 0


async def test_끊은_링크와_지어낸_토큰과_다른_쓰임의_토큰(wired):
    shop_id, headers, _ = await _shop(wired)
    sent = await issue(wired, shop_id, headers)
    token = token_of(sent)
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/forms/{sent.json()['form_id']}", headers=headers)).status_code == 204

    assert error_of(await read(wired, token)) == (410, "FORM_CLOSED")
    assert error_of(await submit(wired, token)) == (410, "FORM_CLOSED")
    assert error_of(await submit(wired, "a" * 43)) == (404, "FORM_NOT_FOUND")
    assert (await wired.api.post("/v1/public/form/intake", json=answer())).status_code == 404
    # 문진표 토큰은 동의서 제출과 알림장 경로에서 읽히지 않는다.
    live = token_of(await issue(wired, shop_id, headers))
    consent = await wired.api.post("/v1/public/form/consent", headers=_with(live),
                                   json={"doc_digest": "x", "signer_name": "김", "signature_png": "AAAA"})
    assert consent.status_code in (404, 422)
    assert (await wired.api.get("/v1/public/report", headers={"X-Report-Token": live})).status_code == 404
    assert await count(wired, "intake_answers") == 0


async def test_로그에_이름과_번호와_적은_글이_없다(wired, caplog):
    shop_id, headers, _ = await _shop(wired)
    token = token_of(await issue(wired, shop_id, headers))

    with caplog.at_level(logging.DEBUG):
        assert (await submit(wired, token)).status_code == 204
        assert (await submit(wired, token, species="bird")).status_code == 422

    for secret in (token, "박새롬", "9999", "모카", "드라이기", "곰돌이"):
        assert secret not in caplog.text
