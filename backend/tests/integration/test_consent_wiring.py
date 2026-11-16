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


async def send(wired, shop_id, headers, *pet_ids, for_date=None):
    body = {"pet_ids": list(pet_ids)} | ({} if for_date is None else {"for_date": for_date.isoformat()})
    return await wired.api.post(f"/v1/shops/{shop_id}/consent-forms", headers=headers, json=body)


async def document(wired, shop_id, headers, *pet_ids, for_date=None):
    params = [("pet_ids", p) for p in pet_ids] + ([] if for_date is None else [("for_date", for_date.isoformat())])
    return await wired.api.get(f"/v1/shops/{shop_id}/consent-document", headers=headers, params=params)


async def sign_here(wired, shop_id, headers, *pet_ids, digest=None, name="김민지", image=PNG_B64, for_date=None):
    if digest is None:
        digest = (await document(wired, shop_id, headers, *pet_ids, for_date=for_date)).json()["doc_digest"]
    body = {"pet_ids": list(pet_ids), "doc_digest": digest, "signer_name": name, "signature_png": image}
    if for_date is not None:
        body["for_date"] = for_date.isoformat()
    return await wired.api.post(f"/v1/shops/{shop_id}/consent-signatures", headers=headers, json=body)


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


async def test_가족_두_마리를_한_요청에_담고_그중_한_마리만_다시_보내도_같은_링크다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))

    both = (await send(wired, shop_id, headers, kong, bori)).json()
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert [(i["form_id"], i["kind"], [p["name"] for p in i["pets"]]) for i in listed] == [
        (both["form_id"], "consent", ["콩이", "보리"])]
    assert listed[0]["customer"] == {"customer_id": customer_id, "name": "김민지"} and listed[0]["url"] == both["url"]

    # 가족 링크가 이미 그 아이를 담고 있으면 한 마리만 다시 보내도 같은 링크다 — 가족 링크가 쪼개지지 않는다.
    alone = await send(wired, shop_id, headers, bori)
    assert (alone.status_code, alone.json()) == (200, both)
    assert await count(wired, "customer_forms") == 1

    # 새 아이가 더해지면 새 링크이고, 옛 링크는 새 링크가 담은 아이를 덜어 낸다.
    nabi = await add_pet(wired, shop_id, headers, customer_id, _pet(name="나비", conditions=[ALLERGY]))
    wider = (await send(wired, shop_id, headers, bori, nabi)).json()
    assert wider["form_id"] != both["form_id"]
    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert {i["form_id"]: [p["pet_id"] for p in i["pets"]] for i in listed} == {
        both["form_id"]: [kong], wider["form_id"]: [bori, nabi]}


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


# --- 지금 있는 것과 잇기 ---------------------------------------------------------------------------------------------

async def _pet_row(wired, pet_id) -> tuple:
    async with wired.engine.connect() as conn:
        return tuple((await conn.execute(text(
            "SELECT grooming_consent_on, grooming_consent_signature_id FROM pets WHERE id = :id"), {"id": pet_id})).one())


async def test_서명_뒤에_지병을_더하면_받은_날은_남고_바뀐_토막만_다시_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[HEART]))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    first = (await sign_here(wired, shop_id, headers, pet_id)).json()["signature_id"]
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)

    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json=_pet(conditions=[HEART, ALLERGY]))
    assert updated.status_code == 200 and updated.json()["pet"]["grooming_consent_on"] == _day(0).isoformat()

    consent = (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]
    assert (consent["state"], consent["parts"], consent["received_on"]) == ("partial", ["condition"], _day(0).isoformat())
    doc = (await document(wired, shop_id, headers, pet_id)).json()
    assert (doc["pets"][0]["parts"], doc["previous_consent_on"]) == (["condition"], _day(0).isoformat())
    assert set(doc["texts"]) == {"condition"} and doc["pets"][0]["conditions"] == ["심장 질환", "알레르기"]

    # 부분 서명은 받은 날과 그날을 찍은 서명을 옮기지 않는다.
    await wired.execute("UPDATE pets SET grooming_consent_on = grooming_consent_on - 30 WHERE id = :id", id=pet_id)
    await wired.execute("UPDATE consent_signatures SET signed_at = signed_at - interval '30 days'")
    second = (await sign_here(wired, shop_id, headers, pet_id)).json()["signature_id"]
    assert await _pet_row(wired, pet_id) == (_day(-30), first) and second != first
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)
    assert error_of(await document(wired, shop_id, headers, pet_id)) == (409, "CONSENT_UP_TO_DATE")


async def test_손_표시_뒤에_지병을_더하면_받은_날이_지워진다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[HEART]))
    await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers, json={})

    updated = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers,
                                  json=_pet(conditions=[HEART, ALLERGY]))

    assert updated.json()["pet"]["grooming_consent_on"] is None


async def test_손으로_받았어요를_누르면_서명과의_이음이_끊기고_지우면_다시_전부_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    await sign_here(wired, shop_id, headers, pet_id)
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["grooming_consent_via"] == "signature"

    marked = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers, json={})
    assert marked.json()["pet"]["grooming_consent_via"] == "manual"
    assert (await _pet_row(wired, pet_id))[1] is None

    cleared = await wired.api.delete(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers)
    assert cleared.json()["pet"]["grooming_consent_via"] is None
    doc = (await document(wired, shop_id, headers, pet_id)).json()
    assert doc["pets"][0]["parts"] == ["basic", "senior"] and doc["previous_consent_on"] is None


async def test_익명화하면_서명과_요청의_행이_남지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR, conditions=[HEART]))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[ALLERGY]))
    signature_id = (await sign_here(wired, shop_id, headers, kong)).json()["signature_id"]
    assert (await send(wired, shop_id, headers, bori)).status_code == 201

    removed = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)

    assert removed.status_code == 204, removed.text
    for table in ("consent_signatures", "consent_signature_pets", "consent_signature_parts",
                  "consent_signature_conditions"):
        assert await count(wired, table) == 0, table
    assert await count(wired, "customer_forms", "revoked_at IS NULL") == 0
    assert await count(wired, "pets", "grooming_consent_signature_id IS NOT NULL") == 0
    assert error_of(await wired.api.get(
        f"/v1/shops/{shop_id}/consent-signatures/{signature_id}", headers=headers)) == (404, "SIGNATURE_NOT_FOUND")
    assert (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json() == {"items": []}


async def test_아이를_지우면_그_아이의_서명이_지워지고_링크에서_빠진다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))
    nabi = await add_pet(wired, shop_id, headers, customer_id, _pet(name="나비", conditions=[ALLERGY]))
    both = (await sign_here(wired, shop_id, headers, kong, bori)).json()["signature_id"]
    form_id = (await send(wired, shop_id, headers, nabi)).json()["form_id"]

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{bori}", headers=headers)).status_code == 204
    one = (await wired.api.get(f"/v1/shops/{shop_id}/consent-signatures/{both}", headers=headers)).json()
    assert [p["pet_id"] for p in one["pets"]] == [kong]            # 남은 아이의 줄은 그대로다

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{nabi}", headers=headers)).status_code == 204
    assert await count(wired, "customer_forms", f"id = {form_id} AND revoked_at IS NOT NULL") == 1


async def test_무지개다리는_링크에서만_빠지고_서명은_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리", conditions=[HEART]))
    await sign_here(wired, shop_id, headers, bori)
    await wired.execute("UPDATE pets SET grooming_consent_on = NULL, grooming_consent_by_member_id = NULL, "
                        "grooming_consent_signature_id = NULL WHERE id = :id", id=bori)
    form_id = (await send(wired, shop_id, headers, kong, bori)).json()["form_id"]

    gone = await wired.api.post(f"/v1/shops/{shop_id}/pets/{bori}/passed-away", headers=headers)
    assert gone.status_code == 200, gone.text

    listed = (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]
    assert [(i["form_id"], [p["pet_id"] for p in i["pets"]]) for i in listed] == [(form_id, [kong])]
    assert await count(wired, "consent_signature_pets", f"pet_id = {bori}") == 1


async def test_보낸_날은_살아_있는_요청이_있을_때만_확인할_것에_실린다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    assert "form_sent_on" not in (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]

    form_id = (await send(wired, shop_id, headers, pet_id)).json()["form_id"]
    assert (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]["form_sent_on"] == _day(0).isoformat()

    await wired.api.delete(f"/v1/shops/{shop_id}/forms/{form_id}", headers=headers)
    assert "form_sent_on" not in (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]


async def test_서명_뒤에_노령이_되면_노령_토막만_다시_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR + 1))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    assert (await sign_here(wired, shop_id, headers, pet_id)).status_code == 201      # 아홉 살 — basic 만
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)

    older = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers, json=_pet(birth_year=SENIOR_YEAR))
    assert older.status_code == 200, older.text

    consent = (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]
    assert (consent["state"], consent["parts"]) == ("partial", ["senior"])
    assert (await document(wired, shop_id, headers, pet_id)).json()["pets"][0]["parts"] == ["senior"]
    assert (await sign_here(wired, shop_id, headers, pet_id)).status_code == 201
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)



# --- 예약 날을 기준으로 (최종 검토 I1) ------------------------------------------------------------------------------

async def _age(wired, pet_id, days: int) -> None:
    """받은 동의와 그 서명을 days 일 앞으로 당긴다."""
    await wired.execute(f"UPDATE pets SET grooming_consent_on = grooming_consent_on - {int(days)} WHERE id = :id", id=pet_id)
    await wired.execute(f"UPDATE consent_signatures SET signed_at = signed_at - interval '{days} days'")


async def test_기한이_예약_날_앞에_끝나는_동의는_예약_날을_주면_지금_다시_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    await sign_here(wired, shop_id, headers, pet_id)
    await _age(wired, pet_id, 360)
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id, days=10)
    assert (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]["state"] == "expired"

    # 오늘로 보면 아직 유효하다 — 받을 것이 없다.
    assert error_of(await document(wired, shop_id, headers, pet_id)) == (409, "CONSENT_UP_TO_DATE")
    # 예약 날로 보면 기한이 지난다 — 전체를 다시 받는다.
    doc = (await document(wired, shop_id, headers, pet_id, for_date=_day(10))).json()
    assert (doc["pets"][0]["parts"], doc["previous_consent_on"]) == (["basic", "senior"], None)

    assert (await sign_here(wired, shop_id, headers, pet_id, for_date=_day(10))).status_code == 201
    pet = (await wired.api.get(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).json()["pet"]
    assert pet["grooming_consent_on"] == _day(0).isoformat()
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)


async def test_예약_날_앞에_노령이_되는_아이는_예약_날을_주면_노령_토막까지_한_번에_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    turning = _day(5).replace(year=_day(5).year - 10)          # 닷새 뒤에 열 살이 된다
    baby = _pet() | {"birth_year": None, "birth_date": turning.isoformat()}
    customer_id, pet_id = await _family(wired, shop_id, headers, baby)
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id, days=10)
    assert (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]["reasons"] == ["senior"]

    assert (await document(wired, shop_id, headers, pet_id)).json()["pets"][0]["parts"] == ["basic"]
    sent = await send(wired, shop_id, headers, pet_id, for_date=_day(10))
    token = sent.json()["url"].rsplit("/", 1)[1]
    opened = (await wired.api.get("/v1/public/form", headers={"X-Form-Token": token})).json()
    assert opened["pets"][0]["parts"] == ["basic", "senior"]

    submitted = await wired.api.post("/v1/public/form/consent", headers={"X-Form-Token": token}, json={
        "doc_digest": opened["doc_digest"], "signer_name": "김민지", "signature_png": PNG_B64})
    assert submitted.status_code == 204
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)      # 서명 한 번으로 끝난다


async def test_같은_링크를_더_먼_예약_날로_다시_보내면_그_날로_맞춰진다(wired):
    shop_id, headers, _ = await _shop(wired)
    turning = _day(5).replace(year=_day(5).year - 10)
    _, pet_id = await _family(wired, shop_id, headers, _pet() | {"birth_year": None, "birth_date": turning.isoformat()})
    first = (await send(wired, shop_id, headers, pet_id)).json()

    again = await send(wired, shop_id, headers, pet_id, for_date=_day(10))

    assert (again.status_code, again.json()["form_id"]) == (200, first["form_id"])
    opened = (await wired.api.get("/v1/public/form", headers={"X-Form-Token": first["url"].rsplit("/", 1)[1]})).json()
    assert opened["pets"][0]["parts"] == ["basic", "senior"]


async def test_예약_날이_기한보다_멀어도_받을_수_있고_지난_날은_오늘로_본다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))

    assert (await document(wired, shop_id, headers, pet_id, for_date=_day(366))).status_code == 200
    assert (await send(wired, shop_id, headers, pet_id, for_date=_day(366))).status_code == 201
    assert (await document(wired, shop_id, headers, pet_id, for_date=_day(-30))).status_code == 200
    assert (await document(wired, shop_id, headers, pet_id, for_date=_day(365))).status_code == 200


# --- 받은 날을 찍은 서명부터 센다 (최종 검토 M1) ---------------------------------------------------------------------

async def test_지우고_다시_받으면_지우기_전의_서명은_덮는_것에_들지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(conditions=[HEART, ALLERGY]))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    await sign_here(wired, shop_id, headers, pet_id)                         # 심장·알레르기를 보고 서명
    await wired.api.delete(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers)
    await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers, json=_pet(conditions=[HEART]))
    await sign_here(wired, shop_id, headers, pet_id)                         # 같은 날, 심장만 보고 다시 서명

    await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers, json=_pet(conditions=[HEART, ALLERGY]))

    # 지금의 동의는 심장만 보았다 — 알레르기는 다시 받아야 한다(지우기 전의 서명이 덮어 주지 않는다).
    consent = (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]
    assert (consent["state"], consent["parts"]) == ("partial", ["condition"])
    assert (await document(wired, shop_id, headers, pet_id)).json()["pets"][0]["parts"] == ["condition"]


# --- 동시에 (최종 검토 I4) -------------------------------------------------------------------------------------------

async def _public_submit(wired, token, digest):
    return await wired.api.post("/v1/public/form/consent", headers={"X-Form-Token": token}, json={
        "doc_digest": digest, "signer_name": "김민지", "signature_png": PNG_B64})


async def _opened(wired, shop_id, headers, pet_id):
    token = (await send(wired, shop_id, headers, pet_id)).json()["url"].rsplit("/", 1)[1]
    return token, (await wired.api.get("/v1/public/form", headers={"X-Form-Token": token})).json()["doc_digest"]


async def test_같은_링크에_동시에_두_번_내면_하나만_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    token, digest = await _opened(wired, shop_id, headers, pet_id)

    one, two = await asyncio.gather(_public_submit(wired, token, digest), _public_submit(wired, token, digest))

    assert sorted([one.status_code, two.status_code]) == [204, 410]
    assert await count(wired, "consent_signatures") == 1


async def test_현장_서명과_링크_서명이_겹치면_서명은_하나다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    token, digest = await _opened(wired, shop_id, headers, pet_id)

    here, link = await asyncio.gather(
        sign_here(wired, shop_id, headers, pet_id, digest=digest), _public_submit(wired, token, digest))

    # 먼저 받은 쪽만 남는다 — 늦은 쪽은 받을 것이 없거나(409) 링크가 닫혔다(410).
    assert sorted([here.status_code, link.status_code]) in ([201, 410], [204, 409])
    assert await count(wired, "consent_signatures") == 1
    assert await count(wired, "customer_forms", "revoked_at IS NULL AND submitted_at IS NULL") == 0


async def test_익명화와_링크_서명이_겹쳐도_서명이_남지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    token, digest = await _opened(wired, shop_id, headers, pet_id)

    removed, link = await asyncio.gather(
        wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers),
        _public_submit(wired, token, digest))

    assert removed.status_code == 204 and link.status_code in (204, 410)
    assert await count(wired, "consent_signatures") == 0
    assert await count(wired, "pets", "grooming_consent_on IS NOT NULL") == 0
    assert await count(wired, "customer_forms", "revoked_at IS NULL") == 0
