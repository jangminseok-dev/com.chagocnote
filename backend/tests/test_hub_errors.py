"""허브 포트 오류의 계약 — 모든 허브 오류가 HTTP 상태를 갖고, 두 진입점이 그 핸들러를 등록한다.

손으로 관리하는 목록을 두지 않는다. HubPortError 의 하위 클래스를 전부 돌아 `HUB_ERROR_STATUS`와 대조하므로,
허브 오류를 새로 만들고 상태를 적지 않으면 여기서 걸린다.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

import main
from core.http_errors import install_error_handlers
from core.hub_errors import HUB_ERROR_STATUS
from hub.app.errors import FamilyPetPassedAwayError, HubPortError


def _all_hub_errors(base=HubPortError) -> set[type]:
    found = set()
    for sub in base.__subclasses__():
        found.add(sub)
        found |= _all_hub_errors(sub)
    return found


def test_모든_허브_오류가_HTTP_상태를_갖는다():
    missing = sorted(e.__name__ for e in _all_hub_errors() if e not in HUB_ERROR_STATUS)
    assert missing == [], f"{missing} 가 core/hub_errors.py 의 HUB_ERROR_STATUS 에 없다"


def test_허브_오류_맵에는_허브_오류만_있다():
    stray = sorted(e.__name__ for e in HUB_ERROR_STATUS if not issubclass(e, HubPortError))
    assert stray == []


def test_허브_오류_코드는_서로_다르다():
    codes = [e.code for e in _all_hub_errors()]
    assert len(codes) == len(set(codes)), "같은 code 를 가진 허브 오류가 둘 이상이다"


def test_API_프로세스에_모든_허브_오류_핸들러가_있다():
    handlers = main.app.exception_handlers
    missing = sorted(e.__name__ for e in HUB_ERROR_STATUS if e not in handlers)
    assert missing == []


def test_스포크_맵_없이도_허브_오류가_code_message_로_나간다():
    """install_error_handlers 는 스포크 맵이 비어 있어도 허브 오류를 등록한다."""
    app = FastAPI()
    install_error_handlers(app, {})

    @app.get("/boom")
    async def boom() -> dict:
        raise FamilyPetPassedAwayError("무지개다리를 건넌 아이입니다.")

    response = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert response.status_code == 422
    assert response.json() == {"code": "PET_PASSED_AWAY", "message": "무지개다리를 건넌 아이입니다."}
