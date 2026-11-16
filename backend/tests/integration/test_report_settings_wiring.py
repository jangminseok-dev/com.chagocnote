"""알림장 설정을 실제 배선(프로바이더·DB 커밋·매장 접근 확인)으로 확인한다."""
import pytest

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

DEFAULT = {"link_days": 30, "show_menus": True, "show_shop_info": True, "show_weight": False, "show_amount": False}
CHANGED = {"link_days": None, "show_menus": False, "show_shop_info": True, "show_weight": True, "show_amount": True}
# 응답에는 리뷰 남기기 줄의 칸이 함께 온다(⑫) — 보내지 않았으니 없음이고 기본 문구가 곁에 있다.
REVIEW = {"review_url": None, "review_text": None, "review_text_default": "미용이 마음에 드셨다면 후기를 남겨 주세요"}


async def test_사장이_바꾼_알림장_설정을_직원도_보지만_직원은_바꾸지_못한다(wired):
    """R16. 사장의 PUT 이 이 매장의 첫 요청이다 — 설정 행이 없는 매장에서도 바뀐다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    o, s = bearer(owner["access_token"]), bearer(staff["access_token"])
    path = f"/v1/shops/{shop_id}/report-settings"

    changed = await wired.api.put(path, json=CHANGED, headers=o)
    assert (changed.status_code, changed.json()) == (200, {**CHANGED, **REVIEW})

    assert error_of(await wired.api.put(path, json=DEFAULT, headers=s)) == (403, "PERMISSION_DENIED")
    seen = await wired.api.get(path, headers=s)
    assert (seen.status_code, seen.json()) == (200, {**CHANGED, **REVIEW})
    assert error_of(await wired.api.put(path, json={**CHANGED, "link_days": 8}, headers=o)) == (
        422, "VALIDATION_ERROR")
    assert (await wired.api.get(path, headers=o)).json() == {**CHANGED, **REVIEW}


async def test_다른_매장의_알림장_설정은_보지도_바꾸지도_못한다(wired):
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    assert (await wired.api.put(f"/v1/shops/{a_shop}/report-settings", json=CHANGED, headers=a)).status_code == 200

    their_shop = [
        await wired.api.get(f"/v1/shops/{b_shop}/report-settings", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/report-settings", json=CHANGED, headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * 2
    # 설정을 정한 적이 없는 B 매장은 기본값이고, 조회만으로는 설정 행이 생기지 않는다.
    assert (await wired.api.get(f"/v1/shops/{b_shop}/report-settings", headers=b)).json() == {**DEFAULT, **REVIEW}
    async with wired.engine.connect() as conn:
        shops = (await conn.exec_driver_sql("SELECT shop_id FROM visit_shop_settings")).scalars().all()
    assert shops == [a_shop]
