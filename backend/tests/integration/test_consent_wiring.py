"""동의서 보내기·끊기·현장 서명·서명 보기를 실제 배선(프로바이더·DB)으로 확인한다(⑪-A).

날짜는 오늘을 기준으로 만든다 — 실행 시각과 상관없이 돈다.
"""
import asyncio
import base64
import logging
import struct

import pytest
from sqlalchemy import text

from tests.integration.support import bearer, error_of
from tests.integration.test_visit_checks_wiring import (
    ALLERGY, HEART, _book, _checks, _day, _family, _pet, _shop, _staff,
)

pytestmark = pytest.mark.integration

SENIOR_YEAR = _day(0).year - 10      # 태어난 해만 알면 해의 차이로 본다 — 올해 10살


def png(width=600, height=240) -> bytes:
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", width, height)
            + b"\x08\x06\x00\x00\x00" + b"\x00" * 30)


PNG_B64 = base64.b64encode(png()).decode()


async def send(wired, shop_id, headers, *pet_ids):
    return await wired.api.post(f"/v1/shops/{shop_id}/consent-forms", headers=headers, json={"pet_ids": list(pet_ids)})


async def document(wired, shop_id, headers, *pet_ids):
    return await wired.api.get(
        f"/v1/shops/{shop_id}/consent-document", headers=headers, params=[("pet_ids", p) for p in pet_ids])


async def sign_here(wired, shop_id, headers, *pet_ids, digest=None, name="김민지", image=PNG_B64):
    if digest is None:
        digest = (await document(wired, shop_id, headers, *pet_ids)).json()["doc_digest"]
    return await wired.api.post(
        f"/v1/shops/{shop_id}/consent-signatures", headers=headers,
        json={"pet_ids": list(pet_ids), "doc_digest": digest, "signer_name": name, "signature_png": image})


async def add_pet(wired, shop_id, headers, customer_id, pet):
    added = await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", headers=headers, json=pet)
    assert added.status_code == 201, added.text
    return added.json()["pet"]["pet_id"]


async def count(wired, table: str, where: str = "true") -> int:
    async with wired.engine.connect() as conn:
        return (await conn.execute(text(f"SELECT count(*) FROM {table} WHERE {where}"))).scalar_one()


# --- 보내기 --------------------------------------------------------------------------------------------------------

async def test_같은_아이에게_두_번_보내면_같은_링크다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))

    first = await send(wired, shop_id, headers, pet_id)
    again = await send(wired, shop_id, headers, pet_id)

    assert (first.status_code, again.status_code) == (201, 200)
    assert set(first.json()) == {"form_id", "url", "expires_on", "sent_on"}
    assert again.json() == first.json()
    assert first.json()["url"].rsplit("/f/", 1)[0].startswith("http") and len(first.json()["url"].rsplit("/", 1)[1]) == 43
    assert first.json()["expires_on"] == _day(14).isoformat() and first.json()["sent_on"] == _day(0).isoformat()
    assert await count(wired, "customer_forms") == 1


async def test_동시에_두_번_보내도_살아_있는_요청은_하나다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))

    one, two = await asyncio.gather(send(wired, shop_id, headers, pet_id), send(wired, shop_id, headers, pet_id))

    assert sorted([one.status_code, two.status_code]) == [200, 201]
    assert one.json()["form_id"] == two.json()["form_id"]
    assert await count(wired, "customer_forms", "revoked_at IS NULL") == 1


async def test_가족_두_마리를_한_요청에_담고_한_마리만_다시_보내면_옛_요청에서_빠진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))

    both = (await send(wired, shop_id, headers, kong, bori)).json()
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert [(i["form_id"], i["kind"], [p["name"] for p in i["pets"]]) for i in listed] == [
        (both["form_id"], "consent", ["콩이", "보리"])]
    assert listed[0]["customer"] == {"customer_id": customer_id, "name": "김민지"} and listed[0]["url"] == both["url"]

    alone = (await send(wired, shop_id, headers, bori)).json()
    assert alone["form_id"] != both["form_id"]
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert {i["form_id"]: [p["pet_id"] for p in i["pets"]] for i in listed} == {
        both["form_id"]: [kong], alone["form_id"]: [bori]}


async def test_다른_고객의_아이를_섞으면_422_없는_아이는_404(wired):
    shop_id, headers, _ = await _shop(wired)
    _, mine = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    _, other = await _family(wired, shop_id, headers, _pet(name="보리", birth_year=SENIOR_YEAR), phone="010-9999-0000")

    assert (await send(wired, shop_id, headers, mine, other)).status_code == 422
    assert error_of(await send(wired, shop_id, headers, 999_999)) == (404, "PET_NOT_FOUND")
    assert (await send(wired, shop_id, headers)).status_code == 422
    assert await count(wired, "customer_forms") == 0


async def test_끊은_요청은_보낸_서류에_없고_다시_보내면_새_링크다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    sent = (await send(wired, shop_id, headers, pet_id)).json()

    cut = await wired.api.delete(f"/v1/shops/{shop_id}/forms/{sent['form_id']}", headers=headers)
    again = await wired.api.delete(f"/v1/shops/{shop_id}/forms/{sent['form_id']}", headers=headers)

    assert (cut.status_code, again.status_code) == (204, 204)
    assert (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json() == {"items": []}
    fresh = await send(wired, shop_id, headers, pet_id)
    assert fresh.status_code == 201 and fresh.json()["url"] != sent["url"]
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/forms/999999", headers=headers)) == (404, "FORM_NOT_FOUND")


# --- 현장 서명 ------------------------------------------------------------------------------------------------------

async def test_현장_서명이_받은_날을_찍고_확인할_것에서_consent_가_사라진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR, conditions=[HEART]))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    assert (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]["state"] == "missing"

    doc = (await document(wired, shop_id, headers, pet_id)).json()
    assert set(doc) == {"pets", "texts", "previous_consent_on", "doc_digest"}
    assert doc["pets"] == [{"pet_id": pet_id, "name": "콩이", "conditions": ["심장 질환"],
                            "parts": ["basic", "senior", "condition"]}]
    assert set(doc["texts"]) == {"basic", "senior", "condition"} and doc["previous_consent_on"] is None
    assert all(t["body"] and "법적" not in t["body"] for t in doc["texts"].values())

    signed = await sign_here(wired, shop_id, headers, pet_id, digest=doc["doc_digest"])

    assert signed.status_code == 201 and set(signed.json()) == {"signature_id"}
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["grooming_consent_on"] == _day(0).isoformat()
    assert error_of(await document(wired, shop_id, headers, pet_id)) == (409, "CONSENT_UP_TO_DATE")
    assert error_of(await send(wired, shop_id, headers, pet_id)) == (409, "CONSENT_UP_TO_DATE")


async def test_현장_서명을_받으면_살아_있던_링크에서_그_아이가_빠지고_비면_닫힌다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))
    form_id = (await send(wired, shop_id, headers, kong, bori)).json()["form_id"]

    assert (await sign_here(wired, shop_id, headers, kong)).status_code == 201
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert [(i["form_id"], [p["pet_id"] for p in i["pets"]]) for i in listed] == [(form_id, [bori])]

    assert (await sign_here(wired, shop_id, headers, bori)).status_code == 201
    assert (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json() == {"items": []}
    assert await count(wired, "customer_forms", "revoked_at IS NOT NULL") == 1


async def test_지문이_다르면_409_이고_서명_행이_없다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[HEART]))
    digest = (await document(wired, shop_id, headers, pet_id)).json()["doc_digest"]
    # 보호자가 읽는 사이 지병이 하나 더 적혔다.
    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                    json=_pet(conditions=[HEART, ALLERGY]))
    assert updated.status_code == 200, updated.text

    stale = await sign_here(wired, shop_id, headers, pet_id, digest=digest)

    assert error_of(stale) == (409, "CONSENT_DOCUMENT_CHANGED")
    assert await count(wired, "consent_signatures") == 0
    assert await count(wired, "pets", "grooming_consent_on IS NOT NULL") == 0


async def test_가족은_서명_한_번으로_여러_아이의_동의를_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))

    doc = (await document(wired, shop_id, headers, bori, kong)).json()
    assert [(p["name"], p["parts"]) for p in doc["pets"]] == [
        ("콩이", ["basic", "senior"]), ("보리", ["basic", "condition"])]
    signed = await sign_here(wired, shop_id, headers, kong, bori, digest=doc["doc_digest"])

    assert signed.status_code == 201
    assert await count(wired, "consent_signatures") == 1 and await count(wired, "consent_signature_pets") == 2
    assert await count(wired, "pets", f"grooming_consent_signature_id = {signed.json()['signature_id']}") == 2


@pytest.mark.parametrize("name,image", [
    ("", PNG_B64), (" " * 3, PNG_B64), ("가" * 51, PNG_B64),
    ("김민지", "not-base64!!"), ("김민지", base64.b64encode(b"\xff\xd8\xff" + b"\x00" * 40).decode()),
    ("김민지", base64.b64encode(png(width=601)).decode()),
])
async def test_이름이나_그림이_틀리면_422_이고_아무것도_쓰지_않는다(wired, name, image):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))

    assert (await sign_here(wired, shop_id, headers, pet_id, name=name, image=image)).status_code == 422
    assert await count(wired, "consent_signatures") == 0


# --- 서명 보기 ------------------------------------------------------------------------------------------------------

async def test_서명은_그때_본_글과_사실을_그대로_돌려주고_그림은_png_다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR, conditions=[HEART]))
    doc = (await document(wired, shop_id, headers, pet_id)).json()
    signature_id = (await sign_here(wired, shop_id, headers, pet_id, digest=doc["doc_digest"])).json()["signature_id"]

    listed = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}/consent-signatures", headers=headers)).json()
    assert [(i["signature_id"], i["channel"], i["signer_name"], i["parts"]) for i in listed["items"]] == [
        (signature_id, "in_shop", "김민지", ["basic", "senior", "condition"])]

    one = (await wired.api.get(f"/v1/shops/{shop_id}/consent-signatures/{signature_id}", headers=headers)).json()
    assert set(one) == {"signature_id", "signed_at", "channel", "signer_name", "by_member_id", "pets"}
    (pet,) = one["pets"]
    assert (pet["pet_id"], pet["shown_name"], pet["conditions"]) == (pet_id, "콩이", ["심장 질환"])
    assert [(p["part"], p["body"]) for p in pet["parts"]] == [
        (part, doc["texts"][part]["body"]) for part in ("basic", "senior", "condition")]

    image = await wired.api.get(f"/v1/shops/{shop_id}/consent-signatures/{signature_id}/image", headers=headers)
    assert image.status_code == 200 and image.content == png()
    assert image.headers["content-type"] == "image/png"
    assert image.headers["x-content-type-options"] == "nosniff" and image.headers["cache-control"] == "no-store"


async def test_직원은_보내고_서명받을_수_있고_다른_매장은_404(wired):
    shop_id, owner, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)
    _, pet_id = await _family(wired, shop_id, owner, _pet(birth_year=SENIOR_YEAR))
    other_shop, other_owner, _ = await _shop(wired, name="다른 매장", owner="다른 사장", operator=operator)

    form_id = (await send(wired, shop_id, staff, pet_id)).json()["form_id"]
    signature_id = (await sign_here(wired, shop_id, staff, pet_id)).json()["signature_id"]

    assert error_of(await send(wired, other_shop, other_owner, pet_id)) == (404, "PET_NOT_FOUND")
    assert error_of(await document(wired, other_shop, other_owner, pet_id)) == (404, "PET_NOT_FOUND")
    assert error_of(await wired.api.delete(
        f"/v1/shops/{other_shop}/forms/{form_id}", headers=other_owner)) == (404, "FORM_NOT_FOUND")
    for path in (f"consent-signatures/{signature_id}", f"consent-signatures/{signature_id}/image"):
        assert error_of(await wired.api.get(f"/v1/shops/{other_shop}/{path}", headers=other_owner)) == (
            404, "SIGNATURE_NOT_FOUND")
    assert error_of(await wired.api.get(
        f"/v1/shops/{other_shop}/pets/{pet_id}/consent-signatures", headers=other_owner)) == (404, "PET_NOT_FOUND")
    # 다른 매장의 사장은 이 매장의 멤버가 아니다 — 가드가 막는다.
    assert (await send(wired, shop_id, other_owner, pet_id)).status_code == 403
    assert (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=other_owner)).status_code == 403


async def test_로그에_주소와_적은_이름이_없다(wired, caplog):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    with caplog.at_level(logging.DEBUG):
        url = (await send(wired, shop_id, headers, pet_id)).json()["url"]
        assert (await sign_here(wired, shop_id, headers, pet_id, name="서명한이름")).status_code == 201
    assert url.rsplit("/", 1)[1] not in caplog.text
    assert "서명한이름" not in caplog.text and PNG_B64 not in caplog.text
