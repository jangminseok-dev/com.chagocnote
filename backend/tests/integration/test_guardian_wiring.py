"""보호자 연결을 실제 배선(프로바이더·허브 포트 조립·DB·Redis)으로 확인한다 — 잇기·목록·끊기·매장 쪽·탈퇴·익명화.

알림장 토큰은 실제로 보낸 알림장의 것이다. 토큰은 헤더로만 넘기고 찍지 않는다.
"""
import asyncio
import logging

import pytest

from tests.integration.support import bearer, error_of
from tests.integration.test_public_report_wiring import _completed_visit, _shop, _token, _with

pytestmark = pytest.mark.integration

LINKS = "/v1/me/guardian/links"


async def web_login(wired, name: str) -> dict:
    """보호자 웹 세션(30분, 리프레시 없음)으로 로그인한 인증 헤더."""
    response = await wired.auth.post("/v1/auth/social", json={"provider": "dev", "token": name, "session": "web"})
    assert response.status_code == 200, response.text
    return bearer(response.json()["access_token"])


async def sent_report(wired, shop_name="Hiss Haus", phone="010-9876-5432"):
    """알림장을 보낸 완료 방문. (shop_id, 매장 헤더, 방문 주소, 토큰)"""
    shop_id, headers = await _shop(wired, shop_name, f"{shop_name} 사장님")
    # 사진은 올리지 않는다(저장소 준비가 필요 없다) — 케어 메모만으로 알림장을 보낼 수 있다.
    visit, _, _ = await _completed_visit(wired, shop_id, headers, phone=phone)
    sent = await wired.api.put(f"{visit}/report", headers=headers, json={"hidden_media_ids": []})
    assert sent.status_code == 200, sent.text
    return shop_id, headers, visit, _token(sent.json()["link"])


async def claim(wired, guardian: dict, token: str | None):
    return await wired.api.post(LINKS, headers={**guardian, **(_with(token) if token else {})})


async def test_받은_알림장_링크로_잇고_다시_하면_같은_연결이며_다른_계정은_409_다(wired, caplog):
    _, _, _, token = await sent_report(wired)
    mine, other = await web_login(wired, "두부보호자"), await web_login(wired, "다른사람")

    with caplog.at_level(logging.DEBUG):
        first = await claim(wired, mine, token)
        again = await claim(wired, mine, token)
        taken = await claim(wired, other, token)

    assert first.status_code == 201, first.text
    assert (again.status_code, again.json()) == (200, first.json())
    assert error_of(taken) == (409, "GUARDIAN_ALREADY_LINKED")
    assert token not in caplog.text and token not in taken.text


async def test_두_계정이_동시에_이으면_하나만_된다(wired):
    _, _, _, token = await sent_report(wired)
    a, b = await web_login(wired, "보호자A"), await web_login(wired, "보호자B")

    results = await asyncio.gather(claim(wired, a, token), claim(wired, b, token))

    assert sorted(r.status_code for r in results) == [201, 409]


async def test_없는_토큰은_404_닫힌_알림장은_410_로그인이_없으면_401_이다(wired):
    _, headers, visit, token = await sent_report(wired)
    guardian = await web_login(wired, "두부보호자")

    assert error_of(await claim(wired, guardian, None)) == (404, "REPORT_NOT_FOUND")
    assert error_of(await claim(wired, guardian, "a" * 43)) == (404, "REPORT_NOT_FOUND")
    assert (await wired.api.post(LINKS, headers=_with(token))).status_code == 401
    assert (await wired.api.delete(f"{visit}/report", headers=headers)).status_code == 204
    assert error_of(await claim(wired, guardian, token)) == (410, "REPORT_CLOSED")


async def test_잇기는_계정당_시간당_열_번까지다(wired):
    guardian = await web_login(wired, "두부보호자")
    for _ in range(10):
        assert error_of(await claim(wired, guardian, "a" * 43)) == (404, "REPORT_NOT_FOUND")
    assert error_of(await claim(wired, guardian, "a" * 43)) == (429, "GUARDIAN_RATE_LIMITED")
