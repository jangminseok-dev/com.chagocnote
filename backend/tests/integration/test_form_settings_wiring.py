"""서류 설정을 실제 배선으로 확인한다(⑪-B) — 기본값, 바꾸기, 권한, 기준값이 매장의 값을 읽는다."""
import pytest

from tests.integration.support import error_of
from tests.integration.test_consent_wiring import count, document, send
from tests.integration.test_visit_checks_wiring import (
    _book, _checks, _day, _family, _move, _pet, _shop, _staff,
)

pytestmark = pytest.mark.integration

KEYS = {"link_days", "senior_age", "consent_days", "reservation_text", "consent_text", "defaults"}


async def read(wired, shop_id, headers):
    return await wired.api.get(f"/v1/shops/{shop_id}/form-settings", headers=headers)


async def put(wired, shop_id, headers, **change):
    body = {"link_days": 14, "senior_age": 10, "consent_days": 365, "reservation_text": None, "consent_text": None}
    return await wired.api.put(f"/v1/shops/{shop_id}/form-settings", headers=headers, json=body | change)


async def test_정한_적이_없으면_기본값이고_읽기는_행을_만들지_않는다(wired):
    shop_id, headers, _ = await _shop(wired)

    got = (await read(wired, shop_id, headers)).json()

    assert set(got) == KEYS
    assert (got["link_days"], got["senior_age"], got["consent_days"]) == (14, 10, 365)
    assert got["reservation_text"] == got["defaults"]["reservation_text"] and "{날짜}" in got["reservation_text"]
    assert got["consent_text"] == got["defaults"]["consent_text"] and "{링크}" in got["consent_text"]
    assert set(got["defaults"]) == KEYS - {"defaults"}
    assert await count(wired, "shop_form_settings") == 0


async def test_바꾸면_그대로_읽히고_글을_비우면_기본_글로_돌아간다(wired):
    shop_id, headers, _ = await _shop(wired)

    changed = await put(wired, shop_id, headers, link_days=7, senior_age=8, consent_days=180,
                        consent_text="서명 부탁드려요\n{링크}")
    assert changed.status_code == 200, changed.text
    got = (await read(wired, shop_id, headers)).json()
    assert got == changed.json()
    assert (got["link_days"], got["senior_age"], got["consent_days"]) == (7, 8, 180)
    assert got["consent_text"] == "서명 부탁드려요\n{링크}"
    assert got["defaults"]["link_days"] == 14

    back = (await put(wired, shop_id, headers)).json()
    assert back["consent_text"] == back["defaults"]["consent_text"]
    assert await count(wired, "shop_form_settings") == 1


async def test_범위_밖이면_422_이고_직원은_읽기만_한다(wired):
    shop_id, owner, _ = await _shop(wired)
    staff = await _staff(wired, shop_id, owner)

    assert error_of(await put(wired, shop_id, owner, link_days=31)) == (422, "VALIDATION_ERROR")
    assert error_of(await put(wired, shop_id, owner, consent_text="링크가 없는 글")) == (422, "VALIDATION_ERROR")
    assert (await put(wired, shop_id, staff, link_days=7)).status_code == 403
    assert (await read(wired, shop_id, staff)).status_code == 200
    assert await count(wired, "shop_form_settings") == 0


async def test_다른_매장의_값은_섞이지_않는다(wired):
    shop_a, a, operator = await _shop(wired)
    shop_b, b, _ = await _shop(wired, "다른 매장", "다른 사장", operator)

    await put(wired, shop_a, a, link_days=3)

    assert (await read(wired, shop_b, b)).json()["link_days"] == 14
    assert (await read(wired, shop_a, b)).status_code in (403, 404)


async def test_링크_기간을_바꾸면_새_링크부터이고_먼저_낸_링크는_그대로다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, kong = await _family(wired, shop_id, headers, _pet(birth_year=_day(0).year - 10))
    _, bori = await _family(wired, shop_id, headers, _pet(name="보리", birth_year=_day(0).year - 11), phone="010-2222-3333")
    first = (await send(wired, shop_id, headers, kong)).json()

    await put(wired, shop_id, headers, link_days=3)

    assert (await send(wired, shop_id, headers, bori)).json()["expires_on"] == _day(3).isoformat()
    assert (await send(wired, shop_id, headers, kong)).json() == first        # 같은 링크, 기간도 그대로
    assert first["expires_on"] == _day(14).isoformat()


async def test_노령_기준을_낮추면_그_나이의_아이_문서에_노령_토막이_붙는다(wired):
    shop_id, headers, _ = await _shop(wired)
    _, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=_day(0).year - 8))
    before = (await document(wired, shop_id, headers, pet_id)).json()["pets"][0]["parts"]

    await put(wired, shop_id, headers, senior_age=8)

    after = (await document(wired, shop_id, headers, pet_id)).json()["pets"][0]["parts"]
    assert (before, after) == (["basic"], ["basic", "senior"])


# --- 확인할 것(③-B)이 매장의 값을 읽는다 ----------------------------------------------------------------------------

async def test_노령_나이를_낮추면_그_매장의_확인할_것과_하루_목록의_수가_바뀌고_다른_매장은_그대로다(wired):
    shop_a, a, operator = await _shop(wired)
    shop_b, b, _ = await _shop(wired, "다른 매장", "다른 사장", operator)
    eight = _pet(birth_year=_day(0).year - 8)
    visits = {}
    for shop_id, headers in ((shop_a, a), (shop_b, b)):
        customer_id, pet_id = await _family(wired, shop_id, headers, eight)
        first = await _book(wired, shop_id, headers, customer_id, pet_id, days=-2)      # 첫 방문 표시를 지운다
        await _move(wired, shop_id, headers, first, "complete")
        visits[shop_id] = await _book(wired, shop_id, headers, customer_id, pet_id, days=1)
    assert "consent" not in await _checks(wired, shop_a, a, visits[shop_a])

    await put(wired, shop_a, a, senior_age=8)

    consent = (await _checks(wired, shop_a, a, visits[shop_a]))["consent"]["detail"]
    assert (consent["state"], consent["reasons"]) == ("missing", ["senior"])
    assert "consent" not in await _checks(wired, shop_b, b, visits[shop_b])

    async def counted(shop_id, headers):
        day = (await wired.api.get(f"/v1/shops/{shop_id}/visits", headers=headers,
                                   params={"date": _day(1).isoformat()})).json()
        return [i["pet_check_count"] for i in day["items"]]

    assert (await counted(shop_a, a), await counted(shop_b, b)) == ([1], [0])


async def test_동의_기한을_줄이면_그보다_오래된_동의는_다시_받는다(wired):
    shop_id, headers, _ = await _shop(wired)
    customer_id, pet_id = await _family(wired, shop_id, headers, _pet(birth_year=_day(0).year - 12))
    visit_id = await _book(wired, shop_id, headers, customer_id, pet_id, days=40)
    received = await wired.api.put(f"/v1/shops/{shop_id}/pets/{pet_id}/grooming-consent", headers=headers,
                                   json={})
    assert received.status_code == 200, received.text
    assert "consent" not in await _checks(wired, shop_id, headers, visit_id)

    await put(wired, shop_id, headers, consent_days=30)

    assert (await _checks(wired, shop_id, headers, visit_id))["consent"]["detail"]["state"] == "expired"
