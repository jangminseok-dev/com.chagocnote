"""core.config 기본값 — APP_ENV 를 명시하지 않으면 운영으로 간주해야 한다. 알림장 링크의 키는 짧으면 기동하지 않는다."""
from __future__ import annotations

import base64
import importlib

import pytest

import core.config


class _StubSecretManager:
    def __init__(self, **values: str) -> None:
        self._values = {
            "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
            "JWT_PUBLIC_KEY_B64": base64.b64encode(b"test-public-key").decode(),
            "REPORT_LINK_KEY_B64": base64.b64encode(bytes(32)).decode(),
            **values,
        }

    def get(self, name: str, default: str | None = None) -> str | None:
        return self._values.get(name, default)

    def require(self, name: str) -> str:
        return self._values[name]


@pytest.fixture
def load_config(monkeypatch):
    """비밀값 관리자를 스텁으로 바꿔 core.config 를 다시 읽는다. 끝나면 원래 값으로 되돌린다."""
    def load(**values: str):
        monkeypatch.setattr(
            "core.singleton.secret_manager.get_secret_manager", lambda: _StubSecretManager(**values)
        )
        return importlib.reload(core.config)

    yield load
    monkeypatch.undo()
    importlib.reload(core.config)


def test_APP_ENV_가_없으면_운영으로_간주한다(load_config):
    assert load_config().APP_ENV == "prod"


def test_알림장_링크의_키는_base64_를_푼_바이트다(load_config):
    key = bytes(range(40))
    assert load_config(REPORT_LINK_KEY_B64=base64.b64encode(key).decode()).REPORT_LINK_KEY == key


@pytest.mark.parametrize("size", [0, 16, 31])
def test_알림장_링크의_키가_32바이트보다_짧으면_기동하지_않는다(load_config, size):
    with pytest.raises(RuntimeError, match="REPORT_LINK_KEY_B64"):
        load_config(REPORT_LINK_KEY_B64=base64.b64encode(bytes(size)).decode())


def test_알림장_웹_주소는_끝의_빗금을_떼고_비밀값은_없으면_빈_문자열이다(load_config):
    assert (load_config().REPORT_WEB_BASE_URL, load_config().REPORT_WEB_SECRET) == ("http://127.0.0.1:3010", "")
    config = load_config(REPORT_WEB_BASE_URL="https://r.chagocnote.com/", REPORT_WEB_SECRET="web-secret")
    assert (config.REPORT_WEB_BASE_URL, config.REPORT_WEB_SECRET) == ("https://r.chagocnote.com", "web-secret")
