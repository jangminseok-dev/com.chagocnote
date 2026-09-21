"""로그인 수단 연결·해제와 회원 탈퇴를 실제 배선으로 확인한다. 위협 점검표의 시나리오를 그대로 돈다."""
import asyncio

import pytest
from sqlalchemy import text

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    open_shop,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration


async def _link_kakao(wired, login, kakao_name):
    return await wired.auth.post(
        "/v1/auth/identities", json={"provider": "kakao", "token": kakao_name},
        headers=bearer(login["access_token"]),
    )


async def _kakao_login(wired, kakao_name):
    response = await wired.auth.post("/v1/auth/social", json={"provider": "kakao", "token": kakao_name})
    assert response.status_code == 200, response.text
    return response.json()


async def _unlink(wired, login, provider):
    return await wired.auth.delete(f"/v1/auth/identities/{provider}", headers=bearer(login["access_token"]))


async def _withdraw(wired, login, confirm=None):
    body = None if confirm is None else {"confirm_close_shops": confirm}
    return await wired.auth.request(
        "DELETE", "/v1/auth/account", json=body, headers=bearer(login["access_token"])
    )


async def _refresh(wired, token):
    return await wired.auth.post("/v1/auth/refresh", json={"refresh_token": token})


async def _me(wired, login):
    return await wired.api.get("/v1/me", headers=bearer(login["access_token"]))


async def _scalar(wired, sql, **params):
    async with wired.engine.connect() as conn:
        return (await conn.execute(text(sql), params)).scalar()


async def _assert_account_intact(wired, login, shops, identities):
    """막힌 탈퇴가 아무것도 바꾸지 않았는지 본다 — 계정·소속·신원이 그대로이고 세션도 살아 있다.

    갱신은 리프레시 토큰을 새 토큰으로 바꾸므로 요청 하나에 한 번만 부른다.
    """
    me = await _me(wired, login)
    assert me.status_code == 200
    assert me.json()["shops"] == shops
    assert me.json()["identities"] == identities
    assert (await _refresh(wired, login["refresh_token"])).status_code == 200


async def test_수단을_붙이면_그_수단으로도_같은_계정에_로그인된다(wired, fake_kakao):
    login = await wired.login("두부보호자")
    linked = await _link_kakao(wired, login, "DubuKakao")
    assert (linked.status_code, linked.json()) == (200, {"identities": ["dev", "kakao"]})
    assert (await _me(wired, login)).json()["identities"] == ["dev", "kakao"]

    via_kakao = await _kakao_login(wired, "DubuKakao")
    assert (via_kakao["user_id"], via_kakao["is_new_user"]) == (login["user_id"], False)


async def test_남의_소셜_계정과_같은_제공자의_두_번째_계정은_붙일_수_없다(wired, fake_kakao):
    """G3·G4"""
    owner_of_kakao = await _kakao_login(wired, "TakenKakao")
    me = await wired.login("두부보호자")
    assert error_of(await _link_kakao(wired, me, "TakenKakao")) == (409, "IDENTITY_ALREADY_LINKED")
    assert (await _link_kakao(wired, me, "MyKakao")).status_code == 200
    assert error_of(await _link_kakao(wired, me, "AnotherKakao")) == (409, "PROVIDER_ALREADY_LINKED")
    # 남의 계정은 그대로다.
    assert (await _kakao_login(wired, "TakenKakao"))["user_id"] == owner_of_kakao["user_id"]


async def test_수단을_해제하면_다른_기기의_세션이_끊기고_그_수단은_새_계정이_된다(wired, fake_kakao):
    """G5"""
    phone = await wired.login("두부보호자")
    assert (await _link_kakao(wired, phone, "DubuKakao")).status_code == 200
    tablet = await _kakao_login(wired, "DubuKakao")   # 해제할 수단으로 만든 다른 기기의 세션

    unlinked = await _unlink(wired, phone, "kakao")
    assert unlinked.status_code == 200
    body = unlinked.json()
    assert body["identities"] == ["dev"]
    assert fake_kakao.revoked == ["kakao-dubukakao"]   # 커밋 뒤에 제공자 쪽 연결을 끊었다

    assert (await _refresh(wired, tablet["refresh_token"])).status_code == 401
    assert (await _refresh(wired, phone["refresh_token"])).status_code == 401
    assert (await _refresh(wired, body["refresh_token"])).status_code == 200   # 요청한 기기의 새 토큰만 산다

    again = await _kakao_login(wired, "DubuKakao")
    assert again["is_new_user"] is True and again["user_id"] != phone["user_id"]


async def test_마지막_수단과_연결되지_않은_수단은_해제할_수_없다(wired, fake_kakao):
    login = await wired.login("두부보호자")
    assert error_of(await _unlink(wired, login, "dev")) == (409, "LAST_IDENTITY")
    assert error_of(await _unlink(wired, login, "kakao")) == (404, "IDENTITY_NOT_FOUND")
    assert error_of(await _unlink(wired, login, "naver")) == (400, "PROVIDER_NOT_SUPPORTED")


async def test_동시에_서로_다른_수단을_해제해도_하나는_남는다(wired, fake_kakao):
    """G1 — 유저 행 잠금이 없으면 둘 다 "수단이 둘"이라고 보고 둘 다 지운다."""
    login = await wired.login("두부보호자")
    assert (await _link_kakao(wired, login, "DubuKakao")).status_code == 200
    first, second = await asyncio.gather(_unlink(wired, login, "dev"), _unlink(wired, login, "kakao"))
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    count = await _scalar(wired, "SELECT count(*) FROM social_identities WHERE user_id = :id", id=login["user_id"])
    assert count == 1


async def test_직원이_탈퇴하면_소속과_세션이_사라지고_같은_계정으로_새로_가입된다(wired, fake_kakao):
    """H3"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    assert (await _link_kakao(wired, staff, "StaffKakao")).status_code == 200

    assert (await _withdraw(wired, staff)).status_code == 204

    assert (await _me(wired, staff)).status_code == 401              # 이미 받은 액세스 토큰도 막힌다
    assert (await _refresh(wired, staff["refresh_token"])).status_code == 401
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    assert [m["display_name"] for m in members.json()] == ["사장님"]
    name = await _scalar(wired, "SELECT display_name FROM users WHERE id = :id", id=staff["user_id"])
    assert name == "탈퇴한 사용자"
    assert fake_kakao.revoked == ["kakao-staffkakao"]

    again = await wired.login("직원")
    assert again["is_new_user"] is True and again["user_id"] != staff["user_id"]
    assert (await _me(wired, again)).json()["shops"] == []


async def test_막힌_탈퇴는_아무것도_바꾸지_않는다(wired, fake_kakao):
    """H1 — 혼자 사장인 매장에 다른 멤버가 있으면 409 이고, 계정·소속·세션이 그대로다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200

    blocked = await _withdraw(wired, owner, confirm=True)
    assert error_of(blocked) == (409, "OWNERSHIP_TRANSFER_REQUIRED")
    assert "Hiss Haus" in blocked.json()["message"]

    await _assert_account_intact(
        wired, owner,
        shops=[{"shop_id": shop_id, "shop_name": "Hiss Haus", "role": "owner"}],
        identities=["dev"],
    )
    assert fake_kakao.revoked == []

    # 사장 권한을 넘기면 풀린다.
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    staff_member_id = next(m["member_id"] for m in members.json() if m["role"] == "staff")
    promoted = await wired.api.patch(
        f"/v1/shops/{shop_id}/members/{staff_member_id}", json={"role": "owner"},
        headers=bearer(owner["access_token"]),
    )
    assert promoted.status_code == 200
    assert (await _withdraw(wired, owner)).status_code == 204


async def test_혼자뿐인_매장은_확인을_받고_함께_닫는다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")

    for confirm in (None, False):
        blocked = await _withdraw(wired, owner, confirm=confirm)
        assert error_of(blocked) == (409, "SHOP_CLOSE_CONFIRM_REQUIRED")
    assert await _scalar(wired, "SELECT closed_at FROM shops WHERE id = :id", id=shop_id) is None
    # H1 — 두 번 막힌 뒤에도 계정·소속·신원과 세션이 그대로다.
    await _assert_account_intact(
        wired, owner,
        shops=[{"shop_id": shop_id, "shop_name": "Hiss Haus", "role": "owner"}],
        identities=["dev"],
    )

    assert (await _withdraw(wired, owner, confirm=True)).status_code == 204
    assert await _scalar(wired, "SELECT closed_at FROM shops WHERE id = :id", id=shop_id) is not None


async def test_confirm_close_shops는_문자열을_받지_않는다(wired):
    """StrictBool — "yes"·"1" 같은 문자열은 참으로 받아들이지 않고 422 다."""
    operator = await make_operator(wired)
    _, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")

    response = await wired.auth.request(
        "DELETE", "/v1/auth/account", json={"confirm_close_shops": "yes"},
        headers=bearer(owner["access_token"]),
    )
    assert response.status_code == 422
    # 거절된 요청은 아무것도 바꾸지 않는다. 그대로 정상적인 탈퇴를 받을 수 있다.
    assert (await _withdraw(wired, owner, confirm=True)).status_code == 204


async def test_탈퇴한_사장이_만들어_둔_초대_코드는_쓸_수_없다(wired):
    """F2"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    co_owner = await wired.login("공동사장")
    assert (await accept_invite(wired, co_owner, await staff_invite(wired, shop_id, owner))).status_code == 200
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    co_owner_member_id = next(m["member_id"] for m in members.json() if m["display_name"] == "공동사장")
    await wired.api.patch(f"/v1/shops/{shop_id}/members/{co_owner_member_id}", json={"role": "owner"},
                          headers=bearer(owner["access_token"]))
    left_behind = await staff_invite(wired, shop_id, co_owner)

    assert (await _withdraw(wired, co_owner)).status_code == 204

    newcomer = await wired.login("새사람")
    assert error_of(await accept_invite(wired, newcomer, left_behind)) == (400, "INVITE_INVALID")


async def test_탈퇴한_운영자의_지정은_남지_않는다(wired):
    """H4"""
    operator = await make_operator(wired)
    assert (await _withdraw(wired, operator)).status_code == 204
    count = await _scalar(wired, "SELECT count(*) FROM platform_operators WHERE user_id = :id", id=operator["user_id"])
    assert count == 0


async def test_같은_유저의_탈퇴가_동시에_와도_한_번만_처리된다(wired, fake_kakao):
    """H5 — 둘째 요청은 잠금 뒤에 이미 탈퇴한 것을 보고 조용히 끝나거나, 인증 단계에서 401 을 받는다.

    배선 확인용이다. DB 왕복이 너무 빨라 잠금을 빼도 대개 순차 실행처럼 끝나므로 판별력이 낮다 —
    잠금 자체는 `test_withdraw_vs_withdraw_locking.py` 의 결정적 두 세션 테스트가 본다.
    """
    login = await wired.login("두부보호자")
    assert (await _link_kakao(wired, login, "DubuKakao")).status_code == 200
    first, second = await asyncio.gather(_withdraw(wired, login), _withdraw(wired, login))
    assert {first.status_code, second.status_code} <= {204, 401}
    assert 204 in (first.status_code, second.status_code)
    assert fake_kakao.revoked == ["kakao-dubukakao"]   # 제공자 연결은 한 번만 끊는다


async def test_복호화할_수_없는_저장된_토큰이_있어도_탈퇴된다(wired, fake_kakao):
    """복호화 실패가 탈퇴를 영구히 막지 않는다 — 그 신원의 연결 끊기만 포기하고 탈퇴는 진행한다."""
    login = await wired.login("두부보호자")
    assert (await _link_kakao(wired, login, "DubuKakao")).status_code == 200
    await wired.execute(
        "UPDATE social_identities SET provider_refresh_token_enc = 'not-a-valid-fernet-token' "
        "WHERE user_id = :id AND provider = 'kakao'",
        id=login["user_id"],
    )

    assert (await _withdraw(wired, login)).status_code == 204

    name = await _scalar(wired, "SELECT display_name FROM users WHERE id = :id", id=login["user_id"])
    assert name == "탈퇴한 사용자"
    assert fake_kakao.revoked == ["kakao-dubukakao"]


async def test_토큰_없는_계정_요청은_401_이다(wired):
    requests = [
        ("POST", "/v1/auth/identities", {"provider": "dev", "token": "x"}),
        ("DELETE", "/v1/auth/identities/dev", None),
        ("DELETE", "/v1/auth/account", None),
    ]
    for method, path, body in requests:
        response = await wired.auth.request(method, path, json=body)
        assert error_of(response) == (401, "UNAUTHENTICATED"), f"{method} {path}"
