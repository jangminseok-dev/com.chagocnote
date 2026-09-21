import pytest

from tests.integration.support import bearer

pytestmark = pytest.mark.integration


async def _refresh(wired, token):
    return await wired.auth.post("/v1/auth/refresh", json={"refresh_token": token})


async def test_로그인부터_로그아웃까지_실제_배선으로_돈다(wired):
    login = await wired.login("두부보호자")
    assert login["is_new_user"] is True

    me = await wired.api.get("/v1/me", headers=bearer(login["access_token"]))
    assert me.status_code == 200
    assert me.json()["display_name"] == "두부보호자"
    assert me.json()["identities"] == ["dev"]
    assert me.json()["shops"] == []

    rotated = await _refresh(wired, login["refresh_token"])
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != login["refresh_token"]

    reused = await _refresh(wired, login["refresh_token"])
    assert (reused.status_code, reused.json()["code"]) == (401, "UNAUTHENTICATED")
    # 재사용이 감지되면 새로 받은 토큰도 함께 폐기된다.
    assert (await _refresh(wired, rotated.json()["refresh_token"])).status_code == 401

    again = await wired.login("두부보호자")
    assert again["is_new_user"] is False
    logout = await wired.auth.post("/v1/auth/logout", json={"refresh_token": again["refresh_token"]})
    assert logout.status_code == 204
    assert (await _refresh(wired, again["refresh_token"])).status_code == 401


async def test_토큰_없이_내_정보를_부르면_401_이다(wired):
    response = await wired.api.get("/v1/me")
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


async def test_지원하지_않는_제공자는_400_이다(wired):
    response = await wired.auth.post("/v1/auth/social", json={"provider": "naver", "token": "x"})
    assert (response.status_code, response.json()["code"]) == (400, "PROVIDER_NOT_SUPPORTED")


async def test_요청_형식이_틀리면_422_와_통일된_본문이다(wired):
    response = await wired.auth.post("/v1/auth/social", json={"provider": "dev"})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_모르는_리프레시_토큰은_401_이다(wired):
    response = await _refresh(wired, "never-issued")
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


async def test_아주_긴_숫자_접두사의_리프레시_토큰은_401_이다(wired):
    huge = "1" * 5000 + ".abc"
    refreshed = await _refresh(wired, huge)
    assert (refreshed.status_code, refreshed.json()["code"]) == (401, "UNAUTHENTICATED")
    # 로그아웃은 토큰을 파싱하지 않고 해시만 쓰므로 그대로 통과한다.
    logout = await wired.auth.post("/v1/auth/logout", json={"refresh_token": huge})
    assert logout.status_code == 204


async def test_정지된_유저는_갱신도_내_정보도_403_이다(wired):
    login = await wired.login("정지될유저")
    await wired.execute("UPDATE users SET suspended_at = now() WHERE id = :id", id=login["user_id"])

    refreshed = await _refresh(wired, login["refresh_token"])
    assert (refreshed.status_code, refreshed.json()["code"]) == (403, "ACCOUNT_SUSPENDED")
    me = await wired.api.get("/v1/me", headers=bearer(login["access_token"]))
    assert (me.status_code, me.json()["code"]) == (403, "ACCOUNT_SUSPENDED")
