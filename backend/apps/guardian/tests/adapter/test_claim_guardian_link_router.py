import logging

import pytest

from guardian.adapter.inbound.api.v1.claim_guardian_link_router import claim_guardian_link_router
from guardian.app.dtos.claim_guardian_link_dto import ClaimGuardianLinkResult
from guardian.dependencies.claim_guardian_link_provider import get_claim_guardian_link_use_case
from guardian.domain.errors import (
    GuardianAccountInactiveError,
    GuardianAlreadyLinkedError,
    ReportLinkClosedError,
    ReportLinkNotFoundError,
    TooManyGuardianRequestsError,
)
from guardian.tests.helpers.api import USER_ID, Recorder, build_app, client

TOKEN = "t" * 43


def _app(stub, **kwargs):
    return build_app(claim_guardian_link_router, get_claim_guardian_link_use_case, stub, **kwargs)


async def test_새로_이으면_201_이고_헤더의_토큰과_로그인한_계정을_넘긴다():
    stub = Recorder(ClaimGuardianLinkResult(link_id=9, created=True))
    async with client(_app(stub)) as c:
        response = await c.post("/v1/me/guardian/links", headers={"X-Report-Token": TOKEN})
    assert (response.status_code, response.json()) == (201, {"link_id": 9})
    assert (stub.calls[0].user_id, stub.calls[0].token) == (USER_ID, TOKEN)
    assert TOKEN not in repr(stub.calls[0])


async def test_이미_내_연결이면_200_이다():
    async with client(_app(Recorder(ClaimGuardianLinkResult(link_id=9, created=False)))) as c:
        response = await c.post("/v1/me/guardian/links", headers={"X-Report-Token": TOKEN})
    assert (response.status_code, response.json()) == (200, {"link_id": 9})


async def test_헤더가_없어도_422_가_아니라_유스케이스가_판정한다():
    stub = Recorder(error=ReportLinkNotFoundError("알림장을 찾을 수 없습니다."))
    async with client(_app(stub)) as c:
        response = await c.post("/v1/me/guardian/links")
    assert (response.status_code, response.json()["code"]) == (404, "REPORT_NOT_FOUND")
    assert stub.calls[0].token is None


@pytest.mark.parametrize("error, status, code", [
    (ReportLinkClosedError("닫힌 알림장입니다."), 410, "REPORT_CLOSED"),
    (GuardianAlreadyLinkedError("이미 다른 계정에 연결된 고객입니다."), 409, "GUARDIAN_ALREADY_LINKED"),
    (TooManyGuardianRequestsError("요청이 너무 잦습니다."), 429, "GUARDIAN_RATE_LIMITED"),
    (GuardianAccountInactiveError("다시 로그인해 주세요."), 401, "UNAUTHENTICATED"),
])
async def test_오류는_코드와_문구만_담고_토큰을_싣지_않는다(error, status, code, caplog):
    with caplog.at_level(logging.DEBUG):
        async with client(_app(Recorder(error=error))) as c:
            response = await c.post("/v1/me/guardian/links", headers={"X-Report-Token": TOKEN})
    assert (response.status_code, response.json()["code"]) == (status, code)
    assert set(response.json()) == {"code", "message"}
    assert TOKEN not in response.text and TOKEN not in caplog.text


async def test_로그인이_없으면_401_이다():
    async with client(_app(Recorder(), logged_in=False)) as c:
        response = await c.post("/v1/me/guardian/links", headers={"X-Report-Token": TOKEN})
    assert response.status_code == 401
