"""미디어 발급·확인을 실제 배선(프로바이더·DB 커밋·매장 접근 확인·MinIO)으로 확인한다. 첫 테스트는 테넌트 격리다."""
import asyncio

import pytest

from tests.integration.support import (
    PHOTO,
    accept_invite,
    bearer,
    error_of,
    issue_media,
    make_operator,
    shop_with_owner,
    staff_invite,
    upload_media,
)

pytestmark = pytest.mark.integration

async def test_다른_매장의_미디어에는_손댈_수_없다(wired, media_storage):
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    b_media = (await issue_media(wired, b_shop, b))["media_id"]

    their_shop = [
        await wired.api.post(f"/v1/shops/{b_shop}/media/uploads", json=PHOTO, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/media/{b_media}/confirm", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/media/myself", headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * 3
    own_shop = await wired.api.post(f"/v1/shops/{a_shop}/media/{b_media}/confirm", headers=a)
    assert error_of(own_shop) == (404, "MEDIA_NOT_FOUND")


async def test_직원이_발급받아_올리고_확인하면_ready_다(wired, media_storage):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])

    issued = await issue_media(wired, shop_id, s)
    early = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=s)
    assert error_of(early) == (409, "MEDIA_NOT_UPLOADED")
    await upload_media(issued)
    confirmed = await wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm",
                                     headers=bearer(owner["access_token"]))   # 발급자가 아니어도 된다
    assert (confirmed.status_code, confirmed.json()["status"], confirmed.json()["size_bytes"]) == (200, "ready", 3000)


async def test_동시에_두_번_확인해도_결과가_같다(wired, media_storage):
    """M13 — 두 요청 모두 200 ready, 크기는 원본의 것 하나."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    o = bearer(owner["access_token"])
    issued = await issue_media(wired, shop_id, o)
    await upload_media(issued)
    first, second = await asyncio.gather(
        wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=o),
        wired.api.post(f"/v1/shops/{shop_id}/media/{issued['media_id']}/confirm", headers=o),
    )
    assert [(r.status_code, r.json()["status"], r.json()["size_bytes"]) for r in (first, second)] == [
        (200, "ready", 3000)] * 2
