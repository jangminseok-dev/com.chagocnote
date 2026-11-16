"""문진표 보내기와 보낸 서류를 실제 배선으로 확인한다(⑪-C) — 새 손님·새 아이·다시 받기."""
import logging

import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import SENIOR_YEAR, add_pet, count, send
from tests.integration.test_visit_checks_wiring import _family, _pet, _shop, _staff

pytestmark = pytest.mark.integration


async def issue(wired, shop_id, headers, customer_id=None, pet_id=None):
    return await wired.api.post(f"/v1/shops/{shop_id}/intake-forms", headers=headers,
                                json={"customer_id": customer_id, "pet_id": pet_id})


async def forms(wired, shop_id, headers):
    return (await wired.api.get(f"/v1/shops/{shop_id}/forms", headers=headers)).json()["items"]


def token_of(response) -> str:
    return response.json()["url"].rsplit("/", 1)[1]


async def test_새_손님용은_누를_때마다_새_링크이고_새_아이와_다시_받기는_같은_링크다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet())

    guest, another = await issue(wired, shop_id, headers), await issue(wired, shop_id, headers)
    new_pet = await issue(wired, shop_id, headers, customer_id=customer_id)
    new_pet_again = await issue(wired, shop_id, headers, customer_id=customer_id)
    again, again_twice = await issue(wired, shop_id, headers, pet_id=pet_id), await issue(wired, shop_id, headers, pet_id=pet_id)

    assert (guest.status_code, another.status_code) == (201, 201) and guest.json()["form_id"] != another.json()["form_id"]
    assert set(guest.json()) == {"form_id", "url", "expires_on", "sent_on"}
    assert "/f/" in guest.json()["url"] and len(token_of(guest)) == 43
    assert (new_pet.status_code, new_pet_again.status_code) == (201, 200) and new_pet.json() == new_pet_again.json()
    assert (again.status_code, again_twice.status_code) == (201, 200) and again.json() == again_twice.json()
    assert len({r.json()["form_id"] for r in (guest, another, new_pet, again)}) == 4
    assert await count(wired, "customer_forms", "kind = 'intake'") == 4


async def test_보낸_서류에_동의서와_문진표가_함께_보이고_누구에게_보냈는지_적혀_있다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=SENIOR_YEAR))
    consent = (await send(wired, shop_id, headers, pet_id)).json()
    guest = (await issue(wired, shop_id, headers)).json()
    new_pet = (await issue(wired, shop_id, headers, customer_id=customer_id)).json()
    again = (await issue(wired, shop_id, headers, pet_id=pet_id)).json()

    listed = {item["form_id"]: item for item in await forms(wired, shop_id, headers)}

    assert all(set(item) == {"form_id", "kind", "mode", "customer", "pets", "sent_on", "expires_on", "url"}
               for item in listed.values())
    assert (listed[consent["form_id"]]["kind"], listed[consent["form_id"]]["mode"]) == ("consent", None)
    assert [(listed[f["form_id"]]["kind"], listed[f["form_id"]]["mode"]) for f in (guest, new_pet, again)] == [
        ("intake", "new"), ("intake", "add_pet"), ("intake", "update")]
    assert (listed[guest["form_id"]]["customer"], listed[guest["form_id"]]["pets"]) == (None, [])     # 새 손님
    assert (listed[new_pet["form_id"]]["customer"], listed[new_pet["form_id"]]["pets"]) == (
        {"customer_id": customer_id, "name": "김민지"}, [])
    assert listed[again["form_id"]]["pets"] == [{"pet_id": pet_id, "name": "콩이"}]
    assert listed[guest["form_id"]]["url"] == guest["url"]


async def test_끊으면_보낸_서류에서_사라지고_다시_보내면_새_링크다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet())
    guest = (await issue(wired, shop_id, headers)).json()
    again = (await issue(wired, shop_id, headers, pet_id=pet_id)).json()

    for form in (guest, again):
        assert (await wired.api.delete(f"/v1/shops/{shop_id}/forms/{form['form_id']}", headers=headers)).status_code == 204

    assert await forms(wired, shop_id, headers) == []
    fresh = await issue(wired, shop_id, headers, pet_id=pet_id)
    assert fresh.status_code == 201 and fresh.json()["form_id"] != again["form_id"]


async def test_없는_대상과_보낼_수_없는_대상(wired):
    shop_id, headers, operator = await _shop(wired)
    other_shop, other, _ = await _shop(wired, "다른 매장", "다른 사장", operator)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet())
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리"))
    gone_customer, gone_pet = await _family(wired, shop_id, headers, _pet(name="두부"), phone="010-2222-3333")
    assert (await wired.api.post(f"/v1/shops/{shop_id}/pets/{bori}/passed-away", headers=headers)).status_code == 200
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{gone_customer}", headers=headers)).status_code == 204

    assert error_of(await issue(wired, shop_id, headers, customer_id=999_999)) == (404, "CUSTOMER_NOT_FOUND")
    assert error_of(await issue(wired, shop_id, headers, pet_id=999_999)) == (404, "PET_NOT_FOUND")
    assert error_of(await issue(wired, shop_id, headers, customer_id=gone_customer)) == (404, "CUSTOMER_NOT_FOUND")
    assert error_of(await issue(wired, shop_id, headers, pet_id=gone_pet)) == (404, "PET_NOT_FOUND")
    assert error_of(await issue(wired, shop_id, headers, pet_id=bori)) == (422, "VALIDATION_ERROR")
    assert error_of(await issue(wired, other_shop, other, pet_id=pet_id)) == (404, "PET_NOT_FOUND")
    assert error_of(await issue(wired, other_shop, other, customer_id=customer_id)) == (404, "CUSTOMER_NOT_FOUND")
    assert await count(wired, "customer_forms") == 0


async def test_익명화와_아이_지우기는_그_문진표_링크를_끊는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, kong = await _family(wired, shop_id, headers, _pet())
    bori = await add_pet(wired, shop_id, headers, customer_id, _pet(name="보리"))
    for target in ({"customer_id": customer_id}, {"pet_id": kong}, {"pet_id": bori}):
        assert (await issue(wired, shop_id, headers, **target)).status_code == 201

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{bori}", headers=headers)).status_code == 204
    assert len(await forms(wired, shop_id, headers)) == 2
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204

    assert await forms(wired, shop_id, headers) == []
    assert await count(wired, "customer_forms", "kind = 'intake' AND revoked_at IS NULL") == 0


async def test_직원도_보내고_끊을_수_있고_다른_매장의_링크는_끊지_못하며_로그에_주소가_없다(wired, caplog):
    shop_id, owner, operator = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)
    other_shop, other, _ = await _shop(wired, "다른 매장", "다른 사장", operator)

    with caplog.at_level(logging.DEBUG):
        sent = await issue(wired, shop_id, staff)
    assert sent.status_code == 201
    assert token_of(sent) not in caplog.text

    form_id = sent.json()["form_id"]
    assert error_of(await wired.api.delete(f"/v1/shops/{other_shop}/forms/{form_id}", headers=other)) == (
        404, "FORM_NOT_FOUND")
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/forms/{form_id}", headers=staff)).status_code == 204


# --- 최종 검토 ------------------------------------------------------------------------------------------------------

async def test_열지_않은_채_기간이_지난_링크가_있어도_그_대상에게_다시_보낼_수_있다(wired):
    from sqlalchemy import text

    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet())
    old_pet = (await issue(wired, shop_id, headers, pet_id=pet_id)).json()
    old_new = (await issue(wired, shop_id, headers, customer_id=customer_id)).json()
    async with wired.engine.begin() as conn:
        await conn.execute(text("UPDATE customer_forms SET expires_at = now() - interval '1 day'"))

    again_pet = await issue(wired, shop_id, headers, pet_id=pet_id)
    again_new = await issue(wired, shop_id, headers, customer_id=customer_id)

    assert (again_pet.status_code, again_new.status_code) == (201, 201), (again_pet.text, again_new.text)
    assert again_pet.json()["form_id"] != old_pet["form_id"] and again_new.json()["form_id"] != old_new["form_id"]
    assert len(await forms(wired, shop_id, headers)) == 2
