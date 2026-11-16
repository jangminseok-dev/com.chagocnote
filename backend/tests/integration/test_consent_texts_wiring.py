"""매장이 고치는 동의서 글을 실제 배선으로 확인한다(⑪-B) — 판이 쌓이고, 옛 서명은 옛 글자로 보인다."""
import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import SENIOR_YEAR, count, document, send, sign_here
from tests.integration.test_public_form_wiring import _read, _submit
from tests.integration.test_visit_checks_wiring import HEART, _book, _checks, _family, _pet, _shop, _staff

pytestmark = pytest.mark.integration

NEW = "나이가 많은 아이는 쉬어 가며 미용해요.\n힘들어하면 멈출게요."


async def texts(wired, shop_id, headers):
    return await wired.api.get(f"/v1/shops/{shop_id}/consent-texts", headers=headers)


async def write(wired, shop_id, headers, part, body):
    return await wired.api.put(f"/v1/shops/{shop_id}/consent-texts/{part}", headers=headers, json={"body": body})


async def test_고치지_않았으면_토막_셋이_기본_글이다(wired):
    shop_id, headers, _ = await _shop(wired)

    parts = (await texts(wired, shop_id, headers)).json()["parts"]

    assert [p["part"] for p in parts] == ["basic", "senior", "condition"]
    assert all(set(p) == {"part", "body", "edited", "default_body"} for p in parts)
    assert all(p["body"] == p["default_body"] and p["edited"] is False and p["body"] for p in parts)
    assert await count(wired, "shop_consent_texts") == 0


async def test_고친_글이_문서와_보호자의_화면에_보이고_같은_글을_다시_저장해도_판이_쌓이지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    token = (await send(wired, shop_id, headers, pet_id)).json()["url"].rsplit("/", 1)[1]

    saved = await write(wired, shop_id, headers, "senior", NEW)
    again = await write(wired, shop_id, headers, "senior", NEW)

    assert saved.status_code == 200 and saved.json() == again.json()
    assert (saved.json()["part"], saved.json()["body"], saved.json()["edited"]) == ("senior", NEW, True)
    assert saved.json()["default_body"] != NEW
    listed = {p["part"]: p for p in (await texts(wired, shop_id, headers)).json()["parts"]}
    assert listed["senior"]["body"] == NEW and listed["basic"]["edited"] is False
    assert (await document(wired, shop_id, headers, pet_id)).json()["texts"]["senior"]["body"] == NEW
    assert (await _read(wired, token)).json()["texts"]["senior"]["body"] == NEW
    assert await count(wired, "shop_consent_texts") == 1


async def test_글을_고친_뒤_옛_글을_보던_지문으로는_서명되지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    token = (await send(wired, shop_id, headers, pet_id)).json()["url"].rsplit("/", 1)[1]
    old = (await _read(wired, token)).json()["doc_digest"]

    await write(wired, shop_id, headers, "senior", NEW)

    assert error_of(await _submit(wired, token, digest=old)) == (409, "CONSENT_DOCUMENT_CHANGED")
    assert error_of(await sign_here(wired, shop_id, headers, pet_id, digest=old)) == (409, "CONSENT_DOCUMENT_CHANGED")
    assert (await _submit(wired, token)).status_code == 204        # 다시 읽고 내면 된다


async def test_옛_서명은_그때의_글자로_보이고_새_서명은_새_글자다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, kong = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    _, bori = await _family(wired, shop_id, headers, _pet(name="보리", birth_year=SENIOR_YEAR), phone="010-2222-3333")
    default = {p["part"]: p["default_body"] for p in (await texts(wired, shop_id, headers)).json()["parts"]}

    async def senior_of(signature_id):
        one = (await wired.api.get(f"/v1/shops/{shop_id}/consent-signatures/{signature_id}", headers=headers)).json()
        return {p["part"]: p["body"] for p in one["pets"][0]["parts"]}["senior"]

    before = (await sign_here(wired, shop_id, headers, kong)).json()["signature_id"]
    await write(wired, shop_id, headers, "senior", NEW)
    after = (await sign_here(wired, shop_id, headers, bori)).json()["signature_id"]
    await write(wired, shop_id, headers, "senior", "또 고친 글")

    assert await senior_of(before) == default["senior"]
    assert await senior_of(after) == NEW


async def test_기본_글로_되돌리면_기본_글이고_판은_남는다(wired):
    shop_id, headers, _ = await _shop(wired)
    await write(wired, shop_id, headers, "basic", "우리 가게의 글")

    back = await write(wired, shop_id, headers, "basic", None)

    assert back.status_code == 200
    assert back.json()["body"] == back.json()["default_body"] and back.json()["edited"] is False
    assert await count(wired, "shop_consent_texts") == 2
    assert (await write(wired, shop_id, headers, "basic", None)).status_code == 200     # 이미 기본 글이다
    assert await count(wired, "shop_consent_texts") == 2


async def test_글을_고쳐도_이미_받은_동의를_다시_받지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR, conditions=[HEART]))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id)
    assert (await sign_here(wired, shop_id, headers, pet_id)).status_code == 201

    for part in ("basic", "senior", "condition"):
        await write(wired, shop_id, headers, part, f"{part} 를 고친 글")

    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)
    assert error_of(await document(wired, shop_id, headers, pet_id)) == (409, "CONSENT_UP_TO_DATE")


async def test_빈_글과_넘치는_글은_422_이고_직원과_다른_매장은_바꾸지_못한다(wired):
    shop_id, owner, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)
    other_shop, other, _ = await _shop(wired, "다른 매장", "다른 사장", operator)

    assert error_of(await write(wired, shop_id, owner, "basic", "  ")) == (422, "VALIDATION_ERROR")
    assert error_of(await write(wired, shop_id, owner, "basic", "가" * 2001)) == (422, "VALIDATION_ERROR")
    assert (await write(wired, shop_id, owner, "nothing", "글")).status_code == 422
    assert (await write(wired, shop_id, staff, "basic", "직원의 글")).status_code == 403
    assert (await texts(wired, shop_id, staff)).status_code == 200
    assert await count(wired, "shop_consent_texts") == 0

    await write(wired, shop_id, owner, "basic", "우리 가게의 글")
    theirs = {p["part"]: p for p in (await texts(wired, other_shop, other)).json()["parts"]}
    assert theirs["basic"]["edited"] is False


async def test_같은_토막을_동시에_저장해도_둘_다_저장되고_판이_차례로_쌓인다(wired):
    import asyncio

    from sqlalchemy import text

    shop_id, headers, _ = await _shop(wired)

    one, two = await asyncio.gather(
        write(wired, shop_id, headers, "basic", "첫째 글"), write(wired, shop_id, headers, "basic", "둘째 글"))

    assert (one.status_code, two.status_code) == (200, 200)
    async with wired.engine.connect() as conn:
        versions = (await conn.execute(text("SELECT version FROM shop_consent_texts ORDER BY version"))).scalars().all()
    assert versions == [1, 2]
