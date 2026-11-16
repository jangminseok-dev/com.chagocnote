"""가족과 함께 보기(⑫ 설계 3.5·8절) — 초대·잇기·목록·끊기, 기본 연결과 함께 끝나기, 매장이 정하는 가족 수.

초대 코드는 헤더(`X-Family-Invite`)로만 간다. 테스트도 코드를 출력하지 않는다.
"""
import asyncio

import pytest
from sqlalchemy import text

from tests.integration.support import bearer, error_of
from tests.integration.test_guardian_wiring import _customer_id, linked, web_login

pytestmark = pytest.mark.integration

LINKS = "/v1/me/guardian/links"
JOIN = "/v1/me/guardian/family-links"


async def invite(wired, guardian, link_id):
    return await wired.api.post(f"{LINKS}/{link_id}/family-invites", headers=guardian)


async def code_of(wired, guardian, link_id) -> str:
    made = await invite(wired, guardian, link_id)
    assert made.status_code == 201, made.text
    return made.json()["code"]


async def join(wired, user, code):
    return await wired.api.post(JOIN, headers={**user, **({"X-Family-Invite": code} if code else {})})


async def joined(wired, primary, link_id, name):
    """가족 한 명을 이어 (가족의 인증 헤더, 가족 연결 ID)를 준다."""
    family = await web_login(wired, name)
    made = await join(wired, family, await code_of(wired, primary, link_id))
    assert made.status_code == 201, made.text
    return family, made.json()["link_id"]


async def my_links(wired, user):
    return {item["link_id"]: item for item in (await wired.api.get(LINKS, headers=user)).json()["items"]}


async def reports(wired, user, link_id):
    return await wired.api.get(f"{LINKS}/{link_id}/reports", headers=user)


async def settings(wired, shop_id, headers, **body):
    path = f"/v1/shops/{shop_id}/guardian-settings"
    return await (wired.api.put(path, headers=headers, json=body) if body else wired.api.get(path, headers=headers))


async def test_초대를_받은_가족이_로그인해_이으면_같은_기록을_본다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)

    made = await invite(wired, primary, link_id)
    assert made.status_code == 201 and set(made.json()) == {"code", "expires_at"}
    assert len(made.json()["code"]) == 43
    family = await web_login(wired, "가족한명")
    joined_ = await join(wired, family, made.json()["code"])

    assert joined_.status_code == 201, joined_.text
    family_link = joined_.json()["link_id"]
    assert (await reports(wired, family, family_link)).json()["items"] == (await reports(wired, primary, link_id)).json()["items"]
    mine, theirs = (await my_links(wired, primary))[link_id], (await my_links(wired, family))[family_link]
    assert (mine["role"], mine["family_count"], mine["family_max"]) == ("primary", 1, 3)
    assert (theirs["role"], theirs["family_count"]) == ("family", 0)


async def test_초대는_한_번만_쓰이고_다시_만들면_앞의_것은_죽는다_틀린_코드는_모두_404(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    first = await code_of(wired, primary, link_id)
    second = await code_of(wired, primary, link_id)
    a, b = await web_login(wired, "가족에이"), await web_login(wired, "가족비")

    assert error_of(await join(wired, a, first)) == (404, "GUARDIAN_INVITE_NOT_FOUND")       # 다시 만들어 죽었다
    assert (await join(wired, a, second)).status_code == 201
    assert error_of(await join(wired, b, second)) == (404, "GUARDIAN_INVITE_NOT_FOUND")      # 한 번만
    assert (await join(wired, a, second)).status_code == 200                                  # 이미 가족이면 그 연결
    for bad in (None, "x" * 43, "short"):
        assert error_of(await join(wired, b, bad)) == (404, "GUARDIAN_INVITE_NOT_FOUND")


async def test_기간이_지난_초대는_404_이고_기본_보호자가_자기_초대를_열면_자기_연결이다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    code = await code_of(wired, primary, link_id)

    mine = await join(wired, primary, code)
    assert (mine.status_code, mine.json()["link_id"]) == (200, link_id)                        # 초대는 쓰이지 않는다
    async with wired.engine.begin() as conn:
        await conn.execute(text("UPDATE guardian_family_invites SET expires_at = now() - interval '1 minute'"))

    assert error_of(await join(wired, await web_login(wired, "늦은가족"), code)) == (404, "GUARDIAN_INVITE_NOT_FOUND")


async def test_가족은_초대하지_못하고_가족_목록과_끊기도_404_다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    family, family_link = await joined(wired, primary, link_id, "가족한명")

    assert error_of(await invite(wired, family, family_link)) == (404, "GUARDIAN_LINK_NOT_FOUND")
    assert error_of(await wired.api.get(f"{LINKS}/{family_link}/family", headers=family))[0] == 404
    assert error_of(await wired.api.delete(f"{LINKS}/{family_link}/family", headers=family))[0] == 404
    assert error_of(await invite(wired, family, link_id))[0] == 404                             # 남의 연결


async def test_함께_보는_가족은_한_사람에_한_줄이고_새로_이은_줄은_한_번만_새것이다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    _, first = await joined(wired, primary, link_id, "가족한명")
    _, second = await joined(wired, primary, link_id, "가족두명")

    listed = (await wired.api.get(f"{LINKS}/{link_id}/family", headers=primary)).json()["items"]
    again = (await wired.api.get(f"{LINKS}/{link_id}/family", headers=primary)).json()["items"]

    assert [(i["family_id"], i["unseen"]) for i in listed] == [(first, True), (second, True)]
    assert set(listed[0]) == {"family_id", "linked_at", "unseen"}                              # 이름·계정 없음
    assert [i["unseen"] for i in again] == [False, False]


async def test_기본_보호자는_한_명만_끊거나_모두_끊고_가족은_스스로_끊는다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    one, one_link = await joined(wired, primary, link_id, "가족한명")
    two, two_link = await joined(wired, primary, link_id, "가족두명")
    three, three_link = await joined(wired, primary, link_id, "가족세명")

    assert (await wired.api.delete(f"{LINKS}/{link_id}/family/{one_link}", headers=primary)).status_code == 204
    assert error_of(await reports(wired, one, one_link)) == (404, "GUARDIAN_LINK_NOT_FOUND")
    assert (await reports(wired, two, two_link)).status_code == 200
    assert error_of(await wired.api.delete(f"{LINKS}/{link_id}/family/{one_link}", headers=primary))[0] == 404

    assert (await wired.api.delete(f"{LINKS}/{three_link}", headers=three)).status_code == 204    # 스스로
    assert (await reports(wired, primary, link_id)).status_code == 200
    leftover = await code_of(wired, primary, link_id)
    assert (await wired.api.delete(f"{LINKS}/{link_id}/family", headers=primary)).status_code == 204
    assert error_of(await reports(wired, two, two_link))[0] == 404
    assert error_of(await join(wired, await web_login(wired, "늦은가족"), leftover))[0] == 404   # 안 쓴 초대도 죽었다
    assert (await reports(wired, primary, link_id)).status_code == 200


@pytest.mark.parametrize("how", ["guardian", "shop", "anonymized", "withdrawn"])
async def test_기본_연결이_끝나면_가족도_함께_끝난다(wired, how):
    primary, link_id, shop_id, headers, visit, _ = await linked(wired)
    family, family_link = await joined(wired, primary, link_id, "가족한명")
    leftover = await code_of(wired, primary, link_id)
    customer_id = _customer_id((await wired.api.get(visit, headers=headers)).json())

    if how == "guardian":
        done = await wired.api.delete(f"{LINKS}/{link_id}", headers=primary)
    elif how == "shop":
        done = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}/guardian-link", headers=headers)
    elif how == "anonymized":
        done = await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    else:
        app_login = await wired.login("두부보호자")
        done = await wired.auth.request("DELETE", "/v1/auth/account", headers=bearer(app_login["access_token"]),
                                        json={"confirm_close_shops": False})
    assert done.status_code in (200, 204), done.text

    assert error_of(await reports(wired, family, family_link))[0] == 404
    async with wired.engine.connect() as conn:
        ended = (await conn.execute(text("SELECT ended_by FROM guardian_links WHERE id = :id"), {"id": family_link})).scalar()
    assert ended == how
    assert error_of(await join(wired, await web_login(wired, "늦은가족"), leftover))[0] == 404


async def test_매장은_가족의_수만_본다(wired):
    primary, link_id, shop_id, headers, visit, _ = await linked(wired)
    await joined(wired, primary, link_id, "가족한명")
    customer_id = _customer_id((await wired.api.get(visit, headers=headers)).json())

    seen = (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}/guardian-link", headers=headers)).json()

    assert set(seen) == {"linked", "linked_at", "family_count"} and seen["family_count"] == 1


async def test_가족_수는_매장이_정하고_줄여도_이은_가족은_그대로다(wired):
    primary, link_id, shop_id, headers, _, _ = await linked(wired)

    got = (await settings(wired, shop_id, headers)).json()
    assert (got["family_max"], got["defaults"]["family_max"]) == (3, 3)
    family, family_link = await joined(wired, primary, link_id, "가족한명")
    assert (await settings(wired, shop_id, headers, family_max=1)).json()["family_max"] == 1

    assert error_of(await invite(wired, primary, link_id)) == (409, "GUARDIAN_FAMILY_FULL")
    assert (await reports(wired, family, family_link)).status_code == 200                       # 끊지 않는다
    assert (await my_links(wired, primary))[link_id]["family_max"] == 1
    assert (await settings(wired, shop_id, headers, family_max=0)).status_code == 200
    await wired.api.delete(f"{LINKS}/{link_id}/family", headers=primary)
    assert error_of(await invite(wired, primary, link_id)) == (409, "GUARDIAN_FAMILY_FULL")      # 0 이면 초대가 없다
    for bad in (-1, 11, "3"):
        assert error_of(await settings(wired, shop_id, headers, family_max=bad))[0] == 422


async def test_초대를_만든_뒤_매장이_수를_줄였으면_잇기가_409_다(wired):
    primary, link_id, shop_id, headers, _, _ = await linked(wired)
    code = await code_of(wired, primary, link_id)
    await settings(wired, shop_id, headers, family_max=0)

    assert error_of(await join(wired, await web_login(wired, "가족한명"), code)) == (409, "GUARDIAN_FAMILY_FULL")


async def test_같은_초대로_둘이_동시에_이으면_하나만_된다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    code = await code_of(wired, primary, link_id)
    a, b = await web_login(wired, "가족에이"), await web_login(wired, "가족비")

    results = await asyncio.gather(join(wired, a, code), join(wired, b, code))

    assert sorted(r.status_code for r in results) == [201, 404]
    assert (await my_links(wired, primary))[link_id]["family_count"] == 1


async def test_초대_만들기와_잇기는_계정당_시간당_열_번까지다(wired):
    primary, link_id, _, _, _, _ = await linked(wired)
    for _ in range(10):
        assert (await invite(wired, primary, link_id)).status_code == 201

    assert error_of(await invite(wired, primary, link_id)) == (429, "GUARDIAN_RATE_LIMITED")
