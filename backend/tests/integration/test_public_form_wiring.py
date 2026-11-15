"""로그인 없는 동의서 읽기와 서명을 실제 배선으로 확인한다(⑪-A). 토큰은 헤더로만 간다."""
import logging

import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import (
    PNG_B64, SENIOR_YEAR, add_pet, count, document, send, sign_here,
)
from tests.integration.test_visit_checks_wiring import ALLERGY, HEART, _day, _family, _pet, _shop

pytestmark = pytest.mark.integration

OPEN_KEYS = {"kind", "state", "shop", "previous_consent_on", "pets", "texts", "doc_digest"}
SUBMITTED_KEYS = {"kind", "state", "shop", "submitted_on"}


def _with(token: str) -> dict:
    return {"X-Form-Token": token}


async def _sent(wired, pet=None):
    shop_id, headers, operator = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, pet or _pet(birth_year=SENIOR_YEAR, conditions=[HEART]))
    sent = (await send(wired, shop_id, headers, pet_id)).json()
    return shop_id, headers, customer_id, pet_id, sent["url"].rsplit("/", 1)[1], sent, operator


async def _read(wired, token):
    return await wired.api.get("/v1/public/form", headers=_with(token))


async def _submit(wired, token, digest=None, name="김민지", image=PNG_B64):
    if digest is None:
        digest = (await _read(wired, token)).json()["doc_digest"]
    return await wired.api.post("/v1/public/form/consent", headers=_with(token),
                                json={"doc_digest": digest, "signer_name": name, "signature_png": image})


async def test_링크로_읽고_서명하면_받은_날이_찍히고_다시_열면_submitted_다(wired):
    shop_id, headers, _, pet_id, token, _, _ = await _sent(wired)

    opened = await _read(wired, token)
    assert opened.status_code == 200 and set(opened.json()) == OPEN_KEYS
    body = opened.json()
    assert (body["kind"], body["state"], body["shop"], body["previous_consent_on"]) == (
        "consent", "open", {"name": "Hiss Haus"}, None)
    assert body["pets"] == [{"name": "콩이", "conditions": ["심장 질환"], "parts": ["basic", "senior", "condition"]}]
    assert set(body["texts"]) == {"basic", "senior", "condition"}
    assert opened.headers["cache-control"] == "private, no-store" and "noindex" in opened.headers["x-robots-tag"]

    assert (await _submit(wired, token, digest=body["doc_digest"])).status_code == 204

    again = await _read(wired, token)
    assert again.status_code == 200 and set(again.json()) == SUBMITTED_KEYS
    assert (again.json()["state"], again.json()["submitted_on"]) == ("submitted", _day(0).isoformat())
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["grooming_consent_on"] == _day(0).isoformat()
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}/consent-signatures", headers=headers)).json()
    assert [(i["channel"], i["signer_name"]) for i in listed["items"]] == [("link", "김민지")]
    assert (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json() == {"items": []}
    # 받은 멤버는 링크를 보낸 멤버다.
    assert await count(wired, "pets", "grooming_consent_by_member_id IS NOT NULL AND grooming_consent_by_member_id > 0") == 1


async def test_지병이_하나_더해진_뒤_옛_지문으로_내면_409_이고_서명이_없다(wired):
    shop_id, headers, _, pet_id, token, _, _ = await _sent(wired, _pet(conditions=[HEART]))
    stale = (await _read(wired, token)).json()["doc_digest"]
    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json=_pet(conditions=[HEART, ALLERGY]))
    assert updated.status_code == 200, updated.text

    assert error_of(await _submit(wired, token, digest=stale)) == (409, "CONSENT_DOCUMENT_CHANGED")
    assert await count(wired, "consent_signatures") == 0
    assert await count(wired, "customer_forms", "submitted_at IS NOT NULL") == 0

    # 다시 읽으면 더해진 지병이 보이고, 그 지문으로는 받는다.
    fresh = (await _read(wired, token)).json()
    assert fresh["pets"][0]["conditions"] == ["심장 질환", "알레르기"] and fresh["doc_digest"] != stale
    assert (await _submit(wired, token, digest=fresh["doc_digest"])).status_code == 204


async def test_두_번_내면_410(wired):
    *_, token, _, _ = await _sent(wired)
    digest = (await _read(wired, token)).json()["doc_digest"]

    assert (await _submit(wired, token, digest=digest)).status_code == 204
    assert error_of(await _submit(wired, token, digest=digest)) == (410, "FORM_CLOSED")
    assert await count(wired, "consent_signatures") == 1


async def test_끊은_링크와_기간이_지난_링크는_410_틀린_토큰은_404(wired):
    shop_id, headers, _, _, token, sent, _ = await _sent(wired)

    assert error_of(await _read(wired, "a" * 43)) == (404, "FORM_NOT_FOUND")
    assert error_of(await wired.api.get("/v1/public/form")) == (404, "FORM_NOT_FOUND")
    assert error_of(await wired.api.post("/v1/public/form/consent", json={
        "doc_digest": "0" * 64, "signer_name": "김민지", "signature_png": PNG_B64})) == (404, "FORM_NOT_FOUND")

    await wired.execute("UPDATE customer_forms SET expires_at = now() - interval '1 second'")
    assert error_of(await _read(wired, token)) == (410, "FORM_CLOSED")
    assert error_of(await _submit(wired, token, digest="0" * 64)) == (410, "FORM_CLOSED")

    await wired.execute("UPDATE customer_forms SET expires_at = now() + interval '1 day'")
    assert (await _read(wired, token)).status_code == 200
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/forms/{sent['form_id']}", headers=headers)).status_code == 204
    assert error_of(await _read(wired, token)) == (410, "FORM_CLOSED")
    assert await count(wired, "consent_signatures") == 0


async def test_알림장_토큰은_서류_경로에서_404_서류_토큰은_알림장_경로에서_404(wired):
    from core.config import REPORT_LINK_KEY
    from core.link_token import make_token

    *_, token, _, _ = await _sent(wired)
    async with wired.engine.connect() as conn:
        from sqlalchemy import text
        public_id = bytes((await conn.execute(text("SELECT public_id FROM customer_forms"))).scalar_one())
    as_report = make_token(public_id, REPORT_LINK_KEY)        # 같은 public_id 를 알림장 용도로 서명한 것

    assert make_token(public_id, REPORT_LINK_KEY, b"form:") == token
    assert error_of(await _read(wired, as_report)) == (404, "FORM_NOT_FOUND")
    assert (await wired.api.get("/v1/public/report", headers={"X-Report-Token": token})).status_code == 404


async def test_열한_번째_제출은_429(wired):
    *_, token, _, _ = await _sent(wired)

    codes = [(await _submit(wired, token, digest="0" * 64)).status_code for _ in range(11)]

    assert codes == [409] * 10 + [429]
    assert error_of(await _submit(wired, token, digest="0" * 64)) == (429, "TOO_MANY_ATTEMPTS")
    assert (await _read(wired, token)).status_code == 200      # 읽기는 다른 통이다


async def test_공개_응답에_매장용_칸이_없다(wired):
    shop_id, headers, customer_id, pet_id, token, sent, _ = await _sent(wired)

    raw = (await _read(wired, token)).text

    assert set((await _read(wired, token)).json()["pets"][0]) == {"name", "conditions", "parts"}
    for leaked in ("pet_id", "customer_id", "shop_id", "form_id", "010", "약 복용 중", "phone", "memo"):
        assert leaked not in raw, leaked


async def test_닫힌_매장과_익명화한_고객의_링크는_410(wired):
    shop_id, headers, customer_id, _, token, _, _ = await _sent(wired)

    await wired.execute("UPDATE shops SET suspended_at = now() WHERE id = :id", id=shop_id)
    assert error_of(await _read(wired, token)) == (410, "FORM_CLOSED")
    assert error_of(await _submit(wired, token, digest="0" * 64)) == (410, "FORM_CLOSED")
    await wired.execute("UPDATE shops SET suspended_at = NULL WHERE id = :id", id=shop_id)
    assert (await _read(wired, token)).status_code == 200

    removed = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert removed.status_code == 204, removed.text
    assert error_of(await _read(wired, token)) == (410, "FORM_CLOSED")
    assert error_of(await _submit(wired, token, digest="0" * 64)) == (410, "FORM_CLOSED")


async def test_그_사이_매장에서_받았으면_링크는_보냈어요로_읽힌다(wired):
    shop_id, headers, customer_id, kong, _, _, _ = await _sent(wired, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))
    token = (await send(wired, shop_id, headers, kong, bori)).json()["url"].rsplit("/", 1)[1]

    assert (await sign_here(wired, shop_id, headers, kong)).status_code == 201
    opened = (await _read(wired, token)).json()
    assert [p["name"] for p in opened["pets"]] == ["보리"]          # 남은 아이만

    assert (await sign_here(wired, shop_id, headers, bori)).status_code == 201
    assert error_of(await _read(wired, token)) == (410, "FORM_CLOSED")   # 아이가 남지 않아 끊겼다


async def test_가족_링크는_서명_한_번으로_둘_다_받는다(wired):
    shop_id, headers, customer_id, kong, _, _, _ = await _sent(wired, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))
    token = (await send(wired, shop_id, headers, kong, bori)).json()["url"].rsplit("/", 1)[1]

    assert (await _submit(wired, token)).status_code == 204

    assert await count(wired, "consent_signatures") == 1 and await count(wired, "consent_signature_pets") == 2
    assert await count(wired, "pets", "grooming_consent_on IS NOT NULL") == 2
    assert error_of(await document(wired, shop_id, headers, kong, bori)) == (409, "CONSENT_UP_TO_DATE")


@pytest.mark.parametrize("name,image", [("", PNG_B64), ("가" * 51, PNG_B64), ("김민지", "@@@")])
async def test_이름이나_그림이_틀리면_422_이고_링크는_열린_채다(wired, name, image):
    *_, token, _, _ = await _sent(wired)

    assert (await _submit(wired, token, name=name, image=image)).status_code == 422
    assert (await _read(wired, token)).json()["state"] == "open"


async def test_로그에_토큰과_적은_이름이_없다(wired, caplog):
    *_, token, _, _ = await _sent(wired)
    with caplog.at_level(logging.DEBUG):
        seen = [(await _read(wired, token)).status_code, (await _read(wired, "a" * 43)).status_code,
                (await _submit(wired, token, digest="0" * 64, name="서명한이름")).status_code,
                (await _submit(wired, token, name="서명한이름")).status_code,
                (await _read(wired, token)).status_code]
    assert seen == [200, 404, 409, 204, 200]
    assert token not in caplog.text and "서명한이름" not in caplog.text


async def test_링크를_보낸_뒤_손으로_받았다고_적으면_링크는_보냈어요로_읽힌다(wired):
    shop_id, headers, _, pet_id, token, _, _ = await _sent(wired)
    digest = (await _read(wired, token)).json()["doc_digest"]
    marked = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers, json={})
    assert marked.status_code == 200, marked.text

    opened = await _read(wired, token)

    assert opened.status_code == 200 and set(opened.json()) == SUBMITTED_KEYS
    assert (opened.json()["state"], opened.json()["submitted_on"]) == ("submitted", None)
    # 받을 것이 없는 링크에 내면 받지 않는다 — 서명이 남지 않고 링크도 닫히지 않는다.
    assert error_of(await _submit(wired, token, digest=digest)) == (409, "CONSENT_UP_TO_DATE")
    assert await count(wired, "consent_signatures") == 0


async def test_이미_낸_링크도_고객을_익명화하면_410_이다(wired):
    shop_id, headers, customer_id, _, token, _, _ = await _sent(wired)
    assert (await _submit(wired, token)).status_code == 204
    assert (await _read(wired, token)).json()["state"] == "submitted"

    removed = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)

    assert removed.status_code == 204, removed.text
    assert error_of(await _read(wired, token)) == (410, "FORM_CLOSED")
    assert await count(wired, "customer_forms", "revoked_at IS NULL") == 0
