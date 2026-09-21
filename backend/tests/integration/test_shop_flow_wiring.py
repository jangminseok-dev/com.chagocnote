"""매장 개설부터 내보내기까지, 그리고 매장 사이의 벽을 실제 배선으로 확인한다."""
import pytest

from tests.integration.support import (
    accept_invite as _accept,
    bearer,
    error_of as _code,
    make_operator as _operator,
    open_shop as _open_shop,
    shop_with_owner as _shop_with_owner,
    staff_invite as _staff_invite,
)

pytestmark = pytest.mark.integration


async def test_매장_개설부터_내보내기까지_돈다(wired):
    operator = await _operator(wired)
    shop = await _open_shop(wired, operator)
    shop_id = shop["shop_id"]
    assert len(shop["owner_invite_code"]) == 8

    owner = await wired.login("사장님")
    joined = await _accept(wired, owner, shop["owner_invite_code"])
    assert joined.status_code == 200
    assert (joined.json()["shop_id"], joined.json()["role"]) == (shop_id, "owner")
    me = await wired.api.get("/v1/me", headers=bearer(owner["access_token"]))
    assert me.json()["shops"] == [{"shop_id": shop_id, "shop_name": "Hiss Haus", "role": "owner"}]

    staff = await wired.login("직원")
    staff_joined = await _accept(wired, staff, await _staff_invite(wired, shop_id, owner))
    assert staff_joined.json()["role"] == "staff"
    staff_member_id = staff_joined.json()["member_id"]

    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(staff["access_token"]))
    assert members.status_code == 200
    assert [(m["display_name"], m["role"]) for m in members.json()] == [("사장님", "owner"), ("직원", "staff")]

    # 권한 없는 직원은 초대도 매장 정보 수정도 할 수 없다.
    assert _code(await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=bearer(staff["access_token"]))) == (403, "PERMISSION_DENIED")
    assert _code(await wired.api.put(f"/v1/shops/{shop_id}/settings", json={"name": "직원이 바꾼 이름"}, headers=bearer(staff["access_token"]))) == (403, "PERMISSION_DENIED")

    updated = await wired.api.put(
        f"/v1/shops/{shop_id}/settings",
        json={"name": "히스 하우스", "phone": "02-000-0000", "address": "서울"},
        headers=bearer(owner["access_token"]),
    )
    assert updated.status_code == 200
    seen_by_staff = await wired.api.get(f"/v1/shops/{shop_id}/settings", headers=bearer(staff["access_token"]))
    assert (seen_by_staff.json()["name"], seen_by_staff.json()["phone"]) == ("히스 하우스", "02-000-0000")

    # 역할을 올리면 다음 요청부터 권한이 생기고, 낮추면 다시 사라진다.
    member_path = f"/v1/shops/{shop_id}/members/{staff_member_id}"
    promoted = await wired.api.patch(member_path, json={"role": "owner"}, headers=bearer(owner["access_token"]))
    assert (promoted.status_code, promoted.json()["role"]) == (200, "owner")
    assert (await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=bearer(staff["access_token"]))).status_code == 201
    demoted = await wired.api.patch(member_path, json={"role": "staff"}, headers=bearer(owner["access_token"]))
    assert demoted.json()["role"] == "staff"

    # 내보낸 직원은 이미 받은 토큰으로도 바로 403 이다.
    assert (await wired.api.delete(member_path, headers=bearer(owner["access_token"]))).status_code == 204
    assert _code(await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(staff["access_token"]))) == (403, "NOT_A_MEMBER")
    staff_me = await wired.api.get("/v1/me", headers=bearer(staff["access_token"]))
    assert staff_me.json()["shops"] == []


async def test_마지막_사장은_낮추거나_내보낼_수_없다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    owner_path = f"/v1/shops/{shop_id}/members/{members.json()[0]['member_id']}"

    assert _code(await wired.api.patch(owner_path, json={"role": "staff"}, headers=bearer(owner["access_token"]))) == (409, "LAST_OWNER")
    assert _code(await wired.api.delete(owner_path, headers=bearer(owner["access_token"]))) == (409, "LAST_OWNER")


async def test_내보낸_멤버가_미리_만들어_둔_초대는_쓸_수_없다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    other = await wired.login("다른사람")
    other_joined = await _accept(wired, other, await _staff_invite(wired, shop_id, owner))
    other_member_id = other_joined.json()["member_id"]
    # 사장으로 올려서 초대를 만들게 한 뒤, 그 코드를 쥔 채로 내보낸다.
    member_path = f"/v1/shops/{shop_id}/members/{other_member_id}"
    assert (await wired.api.patch(member_path, json={"role": "owner"}, headers=bearer(owner["access_token"]))).status_code == 200
    stashed = await _staff_invite(wired, shop_id, other)
    assert (await wired.api.delete(member_path, headers=bearer(owner["access_token"]))).status_code == 204

    comeback = await wired.login("되돌아온사람")
    assert _code(await _accept(wired, comeback, stashed)) == (400, "INVITE_INVALID")


async def test_사장에서_직원으로_낮춘_멤버의_초대도_쓸_수_없다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    other = await wired.login("다른사람")
    other_joined = await _accept(wired, other, await _staff_invite(wired, shop_id, owner))
    member_path = f"/v1/shops/{shop_id}/members/{other_joined.json()['member_id']}"
    assert (await wired.api.patch(member_path, json={"role": "owner"}, headers=bearer(owner["access_token"]))).status_code == 200
    stashed = await _staff_invite(wired, shop_id, other)
    assert (await wired.api.patch(member_path, json={"role": "staff"}, headers=bearer(owner["access_token"]))).status_code == 200

    comeback = await wired.login("초대받은사람")
    assert _code(await _accept(wired, comeback, stashed)) == (400, "INVITE_INVALID")


async def test_다른_매장의_멤버_초대_설정에는_손댈_수_없다(wired):
    """테넌트 격리 — A매장 사장이 B매장의 경로를 부르면 전부 403 NOT_A_MEMBER 다."""
    operator = await _operator(wired)
    _, a_owner = await _shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop_id, b_owner = await _shop_with_owner(wired, operator, "B 매장", "B사장")
    b_members = await wired.api.get(f"/v1/shops/{b_shop_id}/members", headers=bearer(b_owner["access_token"]))
    b_owner_path = f"/v1/shops/{b_shop_id}/members/{b_members.json()[0]['member_id']}"
    a = bearer(a_owner["access_token"])

    attempts = [
        await wired.api.get(f"/v1/shops/{b_shop_id}/members", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop_id}/invites", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop_id}/settings", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop_id}/settings", json={"name": "빼앗은 매장"}, headers=a),
        await wired.api.patch(b_owner_path, json={"role": "staff"}, headers=a),
        await wired.api.delete(b_owner_path, headers=a),
    ]
    assert [_code(r) for r in attempts] == [(403, "NOT_A_MEMBER")] * 6

    # 없는 매장도 같은 답이다 (매장이 있는지조차 알려 주지 않는다).
    assert _code(await wired.api.get("/v1/shops/999999/members", headers=a)) == (403, "NOT_A_MEMBER")
    # B 매장은 그대로다.
    settings = await wired.api.get(f"/v1/shops/{b_shop_id}/settings", headers=bearer(b_owner["access_token"]))
    assert settings.json()["name"] == "B 매장"


async def test_정지된_매장은_멤버도_쓸_수_없다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await wired.execute("UPDATE shops SET suspended_at = now() WHERE id = :id", id=shop_id)

    headers = bearer(owner["access_token"])
    assert _code(await wired.api.get(f"/v1/shops/{shop_id}/members", headers=headers)) == (403, "SHOP_SUSPENDED")
    assert _code(await wired.api.get(f"/v1/shops/{shop_id}/settings", headers=headers)) == (403, "SHOP_SUSPENDED")


async def test_자기_매장_경로로_다른_매장의_멤버_ID_를_부르면_404_다(wired):
    """경로의 매장은 내 매장이라 소속 확인은 통과한다. 컨텍스트가 대상을 그 매장 안에서만 찾는다."""
    operator = await _operator(wired)
    a_shop_id, a_owner = await _shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop_id, b_owner = await _shop_with_owner(wired, operator, "B 매장", "B사장")
    b_members = await wired.api.get(f"/v1/shops/{b_shop_id}/members", headers=bearer(b_owner["access_token"]))
    b_owner_id = b_members.json()[0]["member_id"]

    a = bearer(a_owner["access_token"])
    stolen_path = f"/v1/shops/{a_shop_id}/members/{b_owner_id}"
    assert _code(await wired.api.patch(stolen_path, json={"role": "staff"}, headers=a)) == (404, "MEMBER_NOT_FOUND")
    assert _code(await wired.api.delete(stolen_path, headers=a)) == (404, "MEMBER_NOT_FOUND")

    still_there = await wired.api.get(f"/v1/shops/{b_shop_id}/members", headers=bearer(b_owner["access_token"]))
    assert [(m["member_id"], m["role"]) for m in still_there.json()] == [(b_owner_id, "owner")]


async def test_토큰_없는_요청은_표면마다_401_이다(wired):
    requests = [
        ("GET", "/v1/me"), ("POST", "/v1/invites/accept"),
        ("GET", "/v1/shops/1/members"), ("POST", "/v1/shops/1/invites"),
        ("PATCH", "/v1/shops/1/members/1"), ("DELETE", "/v1/shops/1/members/1"),
        ("GET", "/v1/shops/1/settings"), ("PUT", "/v1/shops/1/settings"),
        ("GET", "/v1/platform/myself"), ("POST", "/v1/platform/shops"),
    ]
    for method, path in requests:
        response = await wired.api.request(method, path, json={"code": "X", "name": "X", "role": "staff"})
        assert _code(response) == (401, "UNAUTHENTICATED"), f"{method} {path}"


async def test_매장_자기소개는_토큰_없이_응답한다(wired):
    response = await wired.api.get("/v1/shops/myself")
    assert response.status_code == 200
    assert "/v1/invites/accept" in response.json()["introduction"]


async def test_운영자가_아니면_운영자_표면을_쓸_수_없다(wired):
    user = await wired.login("보통유저")
    headers = bearer(user["access_token"])
    assert _code(await wired.api.post("/v1/platform/shops", json={"name": "몰래 만든 매장"}, headers=headers)) == (403, "PERMISSION_DENIED")
    assert _code(await wired.api.get("/v1/platform/myself", headers=headers)) == (403, "PERMISSION_DENIED")

    operator = await _operator(wired)
    myself = await wired.api.get("/v1/platform/myself", headers=bearer(operator["access_token"]))
    assert myself.status_code == 200


async def test_초대_코드는_한_번만_쓸_수_있고_이미_멤버면_409_다(wired):
    operator = await _operator(wired)
    shop = await _open_shop(wired, operator)
    owner = await wired.login("사장님")
    assert (await _accept(wired, owner, shop["owner_invite_code"])).status_code == 200

    latecomer = await wired.login("늦은사람")
    assert _code(await _accept(wired, latecomer, shop["owner_invite_code"])) == (400, "INVITE_EXHAUSTED")
    assert _code(await _accept(wired, latecomer, "ZZZZ9999")) == (400, "INVITE_INVALID")

    staff_code = await _staff_invite(wired, shop["shop_id"], owner)
    assert _code(await _accept(wired, owner, staff_code)) == (409, "ALREADY_A_MEMBER")
    # 실패한 수락은 초대를 쓰지 않는다. 다른 사람이 그 코드로 합류할 수 있다.
    assert (await _accept(wired, latecomer, staff_code.lower())).status_code == 200


async def test_만료된_초대_코드는_400_INVITE_EXPIRED_다(wired):
    operator = await _operator(wired)
    shop = await _open_shop(wired, operator)
    await wired.execute("UPDATE shop_invites SET expires_at = now() - interval '1 minute'")
    owner = await wired.login("사장님")
    assert _code(await _accept(wired, owner, shop["owner_invite_code"])) == (400, "INVITE_EXPIRED")


async def test_초대_코드_입력은_분당_다섯_번까지다(wired):
    user = await wired.login("마구넣는사람")
    for _ in range(5):
        assert _code(await _accept(wired, user, "ZZZZ9999")) == (400, "INVITE_INVALID")
    assert _code(await _accept(wired, user, "ZZZZ9999")) == (429, "TOO_MANY_ATTEMPTS")


async def test_닫힌_매장은_접근할_수_없고_내_매장_목록에서_빠진다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await wired.execute("UPDATE shops SET closed_at = now() WHERE id = :id", id=shop_id)

    headers = bearer(owner["access_token"])
    assert _code(await wired.api.get(f"/v1/shops/{shop_id}/settings", headers=headers)) == (403, "SHOP_CLOSED")
    assert (await wired.api.get("/v1/me", headers=headers)).json()["shops"] == []
