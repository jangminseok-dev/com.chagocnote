"""공용 HTTP 클라이언트 수명 — dispose_http() 뒤에 캐시된 제공자 목록이 닫힌 클라이언트를 붙들지 않는지 확인한다."""
from __future__ import annotations

import base64

import pytest

from auth.dependencies import auth_wiring


@pytest.fixture(autouse=True)
def _reset_wiring_state(monkeypatch):
    monkeypatch.setattr(auth_wiring, "_http", None)
    monkeypatch.setattr(auth_wiring, "_resolver", None)


async def test_dispose_한_뒤_새로_만든_클라이언트는_열려_있다():
    first = auth_wiring.get_http()
    await auth_wiring.dispose_http()
    assert first.is_closed

    second = auth_wiring.get_http()
    assert second is not first
    assert not second.is_closed
    await auth_wiring.dispose_http()


async def test_dispose_하면_캐시된_제공자_목록도_비운다(monkeypatch):
    # build_provider_resolver() 가 어드민 키를 읽으려고 core.auth_config 를 불러온다.
    # 이 모듈은 인증 프로세스 전용 비밀값을 요구하므로, 이 테스트에서만 임시 값을 넣어 둔다.
    monkeypatch.setenv("JWT_PRIVATE_KEY_B64", base64.b64encode(b"dummy").decode())
    monkeypatch.setenv("IDENTITY_TOKEN_ENC_KEY", "dummy")
    auth_wiring.build_provider_resolver()
    assert auth_wiring._resolver is not None

    await auth_wiring.dispose_http()

    assert auth_wiring._resolver is None
