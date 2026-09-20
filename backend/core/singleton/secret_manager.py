"""비밀값 관리자 — .env 를 읽는 유일한 곳 (Singleton).

컨테이너에서는 compose 의 env_file 이 환경 변수로 주입하므로 파일이 없어도 된다.
파일 읽기는 컨테이너 밖에서 스크립트를 돌릴 때를 위한 예비 경로다.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

_REPO_ROOT = Path(__file__).resolve().parents[3]


class SecretManager:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._file_values: dict[str, str | None] = dict(dotenv_values(root / ".env"))

    def get(self, name: str, default: str | None = None) -> str | None:
        return os.environ.get(name) or self._file_values.get(name) or default

    def require(self, name: str) -> str:
        value = self.get(name)
        if not value:
            raise RuntimeError(f"필수 환경 변수 {name} 이(가) 없습니다.")
        return value

    def load_auth_env(self) -> None:
        """JWT 개인키가 든 .env.auth 를 읽는다. 인증 프로세스와 테스트만 부른다."""
        self._file_values.update(dotenv_values(self._root / ".env.auth"))


_manager: SecretManager | None = None


def get_secret_manager() -> SecretManager:
    global _manager
    if _manager is None:
        _manager = SecretManager(_REPO_ROOT)
    return _manager
