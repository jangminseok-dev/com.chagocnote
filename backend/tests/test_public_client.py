"""R17 — 웹 서버가 알려 준 접속 주소는 비밀값이 맞을 때만 믿는다."""
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from core import public_client
from core.public_client import get_public_client

SECRET = "web-secret-for-test"


@pytest.fixture
def secret(monkeypatch):
    monkeypatch.setattr(public_client, "REPORT_WEB_SECRET", SECRET)


async def _client_of(headers, peer=("198.51.100.9", 4321)) -> str:
    app = FastAPI()

    @app.get("/who")
    async def who(client: str = Depends(get_public_client)) -> dict:
        return {"client": client}

    async with AsyncClient(transport=ASGITransport(app=app, client=peer), base_url="http://t") as c:
        return (await c.get("/who", headers=headers)).json()["client"]


async def test_비밀값이_맞으면_웹_서버가_알려_준_주소다(secret):
    assert await _client_of({"X-Report-Web-Secret": SECRET, "X-Report-Client-IP": "203.0.113.7"}) == "203.0.113.7"


@pytest.mark.parametrize("headers", [
    {"X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": "", "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": SECRET + "x", "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": SECRET[:-1], "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": "비밀".encode(), "X-Report-Client-IP": "203.0.113.7"},
    {"X-Report-Web-Secret": SECRET},
    {"X-Report-Web-Secret": SECRET, "X-Report-Client-IP": ""},
    {},
], ids=["비밀값 없음", "빈 비밀값", "긴 비밀값", "짧은 비밀값", "한글 비밀값", "주소 없음", "빈 주소", "헤더 없음"])
async def test_비밀값이_틀리거나_주소가_없으면_연결된_주소다(secret, headers):
    assert await _client_of(headers) == "198.51.100.9"


async def test_비밀값을_설정하지_않았으면_빈_비밀값을_보내도_믿지_않는다(monkeypatch):
    monkeypatch.setattr(public_client, "REPORT_WEB_SECRET", "")
    assert await _client_of({"X-Report-Web-Secret": "", "X-Report-Client-IP": "203.0.113.7"}) == "198.51.100.9"
    assert await _client_of({"X-Report-Client-IP": "203.0.113.7"}) == "198.51.100.9"


async def test_연결된_주소를_모르면_unknown_이다(secret):
    assert await _client_of({}, peer=None) == "unknown"
