from guardian.adapter.inbound.api.v1.guardian_myself_router import guardian_myself_router
from guardian.app.dtos.guardian_myself_dto import GuardianMyselfResponse
from guardian.dependencies.guardian_myself_provider import get_guardian_myself_use_case
from guardian.tests.helpers.api import Recorder, build_app, client


async def test_로그인한_계정은_자기소개를_본다():
    stub = Recorder(GuardianMyselfResponse(id=8, name="보호자 (guardian)", introduction="소개"))
    async with client(build_app(guardian_myself_router, get_guardian_myself_use_case, stub)) as c:
        response = await c.get("/v1/me/guardian/myself")
    assert response.json() == {"id": 8, "name": "보호자 (guardian)", "introduction": "소개"}
    assert stub.calls[0].id == 8


async def test_로그인이_없으면_401_이다():
    stub = Recorder(GuardianMyselfResponse(id=8, name="보호자 (guardian)", introduction="소개"))
    app = build_app(guardian_myself_router, get_guardian_myself_use_case, stub, logged_in=False)
    async with client(app) as c:
        response = await c.get("/v1/me/guardian/myself")
    assert response.status_code == 401
