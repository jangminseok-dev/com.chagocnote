"""core.config 기본값 — APP_ENV 를 명시하지 않으면 운영으로 간주해야 한다."""
from __future__ import annotations

import base64
import importlib

import core.config


class _StubSecretManager:
    def __init__(self) -> None:
        self._require_values = {
            "DATABASE_URL": "postgresql+asyncpg://u:p@h/db",
            "JWT_PUBLIC_KEY_B64": base64.b64encode(b"test-public-key").decode(),
        }

    def get(self, name: str, default: str | None = None) -> str | None:
        return default

    def require(self, name: str) -> str:
        return self._require_values[name]


def test_APP_ENV_가_없으면_운영으로_간주한다(monkeypatch):
    monkeypatch.setattr(
        "core.singleton.secret_manager.get_secret_manager", lambda: _StubSecretManager()
    )
    try:
        importlib.reload(core.config)
        assert core.config.APP_ENV == "prod"
    finally:
        monkeypatch.undo()
        importlib.reload(core.config)
