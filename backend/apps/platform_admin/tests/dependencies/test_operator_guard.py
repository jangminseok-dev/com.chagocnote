from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.dependencies.hub_ports import get_operator_directory
from platform_admin.dependencies.operator_guard import require_operator


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)
        self.calls = []

    async def is_operator(self, user_id):
        self.calls.append(user_id)
        return user_id in self.operator_ids


async def _no_db():
    yield None


def _app(stub, user_id=5):
    app = FastAPI()
    install_error_handlers(app, PLATFORM_ADMIN_ERROR_STATUS)

    @app.get("/guarded")
    async def guarded(operator_id: int = Depends(require_operator)) -> dict:
        return {"user_id": operator_id}

    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_operator_directory] = lambda: stub
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _get(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/guarded")


async def test_운영자는_통과하고_유저_ID_를_받는다():
    stub = _StubOperators([5])
    response = await _get(_app(stub))
    assert (response.status_code, response.json()) == (200, {"user_id": 5})
    assert stub.calls == [5]


async def test_운영자가_아니면_403_PERMISSION_DENIED_다():
    response = await _get(_app(_StubOperators([5]), user_id=6))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")


async def test_토큰이_없으면_401_이고_운영자_확인도_하지_않는다():
    stub = _StubOperators([5])
    response = await _get(_app(stub, user_id=None))
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
    assert stub.calls == []
