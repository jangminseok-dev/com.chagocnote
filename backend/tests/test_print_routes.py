from fastapi import APIRouter, FastAPI

from scripts.print_routes import collect_routes


def test_프로세스별_라우트를_경로순으로_모은다():
    api, auth = FastAPI(), FastAPI()
    router = APIRouter(prefix="/v1/auth")

    @router.post("/social")
    async def social_login(): ...

    @api.get("/v1/me")
    async def get_me(): ...

    auth.include_router(router)
    rows = collect_routes({"backend": api, "auth": auth})
    assert ("auth", "POST", "/v1/auth/social", "social_login") in rows
    assert ("backend", "GET", "/v1/me", "get_me") in rows
    assert [r[2] for r in rows] == sorted(r[2] for r in rows)


def test_문서_경로는_표에서_뺀다():
    rows = collect_routes({"backend": FastAPI()})
    assert all(not r[2].startswith(("/docs", "/redoc", "/openapi")) for r in rows)
