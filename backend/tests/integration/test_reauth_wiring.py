"""재인증(최근 로그인 확인)이 실제 배선에서 도는지 본다."""
import pytest
from jose import jwt

from tests.integration.support import bearer, error_of

pytestmark = pytest.mark.integration


async def _refresh(wired, login):
    response = await wired.auth.post("/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert response.status_code == 200, response.text
    return response.json()


async def test_방금_로그인한_토큰으로는_수단을_연결할_수_있다(wired):
    login = await wired.login("두부")
    response = await wired.auth.post(
        "/v1/auth/identities", json={"provider": "dev", "token": "두부"},
        headers=bearer(login["access_token"]),
    )
    # dev 수단은 이미 있으므로 409 다 — 403 REAUTH_REQUIRED 가 아니라는 것이 요점이다.
    assert error_of(response) == (409, "PROVIDER_ALREADY_LINKED")


async def test_갱신으로_받은_토큰은_연결_해제_탈퇴_모두_REAUTH_REQUIRED_다(wired):
    login = await wired.login("두부")
    refreshed = await _refresh(wired, login)
    headers = bearer(refreshed["access_token"])
    link = await wired.auth.post("/v1/auth/identities", json={"provider": "dev", "token": "두부"}, headers=headers)
    unlink = await wired.auth.delete("/v1/auth/identities/dev", headers=headers)
    withdraw = await wired.auth.delete("/v1/auth/account", headers=headers)
    assert [error_of(r) for r in (link, unlink, withdraw)] == [(403, "REAUTH_REQUIRED")] * 3
    # 아무것도 바뀌지 않았다: 같은 토큰으로 내 정보가 그대로 나온다.
    me = await wired.api.get("/v1/me", headers=headers)
    assert me.status_code == 200 and me.json()["identities"] == ["dev"]


async def test_다시_로그인하면_탈퇴할_수_있다(wired):
    login = await wired.login("두부")
    await _refresh(wired, login)
    again = await wired.login("두부")   # 재인증 = 소셜 로그인을 한 번 더
    response = await wired.auth.delete("/v1/auth/account", headers=bearer(again["access_token"]))
    assert response.status_code == 204


async def test_해제가_준_토큰은_원래_로그인_시각을_물려받는다(wired, fake_kakao):
    login = await wired.login("두부")
    headers = bearer(login["access_token"])
    linked = await wired.auth.post(
        "/v1/auth/identities", json={"provider": "kakao", "token": "kakao-token-for-dubu"}, headers=headers
    )
    assert linked.status_code == 200, linked.text
    unlinked = await wired.auth.delete("/v1/auth/identities/kakao", headers=headers)
    assert unlinked.status_code == 200, unlinked.text
    before = jwt.get_unverified_claims(login["access_token"])["auth_time"]
    after = jwt.get_unverified_claims(unlinked.json()["access_token"])["auth_time"]
    same = before == after          # 토큰 값이 단언 메시지에 찍히지 않게 불리언으로 비교한다
    assert same
