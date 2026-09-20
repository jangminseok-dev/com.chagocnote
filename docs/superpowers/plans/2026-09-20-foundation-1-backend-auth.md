# 차곡노트 ① 기반 — 계획 1/3: 백엔드 골격과 로그인 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docker compose up` 한 번으로 뜨는 백엔드 골격 위에서 소셜 로그인(개발용·카카오·구글·Apple)으로 자체 JWT를 발급·갱신·폐기하고 `GET /v1/me`로 내 정보를 조회할 수 있게 한다.

**Architecture:** 모듈러 모놀리식이다. 앱 내부는 헥사고날(`adapter → app → domain`), 앱 사이는 허브-스포크이며 `import-linter`로 강제한다. 인증 프로세스(`auth_main.py`)만 JWT 개인키를 갖고, API 프로세스(`main.py`)는 공개키로 검증만 한다. Caddy 게이트웨이가 `/v1/auth/*`를 인증 프로세스로, 나머지를 API 프로세스로 보낸다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) + asyncpg · Alembic · Pydantic 2 · redis-py(asyncio) · python-jose · cryptography · httpx · import-linter · pytest + pytest-asyncio · PostgreSQL 17(pgvector) · Redis 7 · Caddy 2 · Docker Compose

**Spec:** `docs/superpowers/specs/2026-09-20-foundation-design.md` — 이 계획은 그중 3절, 4절, 5.2~5.4절(auth 부분), 7절, 8.1절을 구현한다. 실행자는 설계 문서도 함께 읽는다.

**이 계획이 다루지 않는 것 (계획 2·3에서 다룬다):** `tenancy`·`platform_admin` 스포크, 허브 포트, 계정 연결·해제, 회원 탈퇴, `SocialProviderPort.revoke`, `GET /v1/me`의 소속 매장 목록, 스포크 상호 독립 계약(두 번째 스포크가 생길 때 추가), Flutter 앱.

## Global Constraints

- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준 상대 경로다. 절대 경로를 코드나 설정에 쓰지 않는다.
- 실행 방식은 서브에이전트 방식이고, **사용자가 작업 단위 커밋을 허용했다**(2026-09-20). 각 작업의 마지막 커밋 단계를 실행한다. 푸시는 하지 않는다.
- Python 3.13. 의존성은 `backend/requirements.txt`에만 추가한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이다.
- **커밋은 사용자가 작업 단위 커밋을 허용한 경우에만 한다.** 허용하지 않았으면 각 작업의 마지막 "커밋" 단계를 건너뛰고 바뀐 파일 목록만 보고한다.
- 수직 슬라이스 1:1: 유스케이스마다 router, schema, dto, input port, output port, interactor, provider, test 파일을 하나씩 둔다. 한 파일에 여러 슬라이스를 넣지 않는다. DTO와 리포지토리는 도메인 말로 이름 지을 수 있다. entity·VO·mapper는 로직이 있을 때만 만든다.
- 새 라우터 묶음에는 `GET <prefix>/myself`를 두고 실제 기능을 설명한다. 배역이나 은유를 쓰지 않는다.
- 유스케이스는 어댑터 스키마가 아니라 app DTO(frozen dataclass)를 받는다.
- 아웃바운드 포트는 빈 껍데기를 만들지 않는다. 인터랙터가 실제로 호출하는 메서드만 정의한다.
- `app`·`domain` 계층에서 `fastapi`, `sqlalchemy`, `redis`, `httpx`, `jose`, `cryptography`를 import하지 않는다. `domain`은 `pydantic`도 import하지 않는다.
- 엔티티(ORM)는 `int` 단일 PK `id`, SQLAlchemy 2.0 `Mapped` 스타일이다.
- I/O 작업은 `async def`, CPU 작업은 `def`다. 포트와 구현체의 `def`/`async def`를 일치시킨다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `backend/core/singleton/secret_manager.py`에서만 쓴다. 런타임 코드는 `core/config.py`의 상수를, 스크립트는 `get_secret_manager()`를 쓴다.
- 통상적인 폴더 이름 외에 새로 만드는 기능 폴더에는 그 코드가 실제로 구현하는 GoF 패턴 이름을 붙인다(`strategy/`, `factory/`, `singleton/`).
- 테스트는 mock 프레임워크 대신 스텁 구현을 쓴다. 실제 DB·Redis에 붙는 테스트는 `integration` 마커, 외부 제공자를 호출하는 테스트는 `network` 마커를 단다.
- 오류 응답 본문은 `{"code": "...", "message": "..."}` 형식이다.
- 호스트 포트는 모두 `127.0.0.1`에만 바인딩한다. 이 맥에서 도는 다른 프로젝트와 겹치지 않게 `5442`(Postgres), `6389`(Redis), `9010`·`9011`(MinIO), `8080`(게이트웨이)을 쓴다.
- 백엔드 검증 명령은 전부 `infra/` 디렉터리에서 `docker compose run --rm backend …` 형태로 실행한다. 맥에 파이썬 환경을 만들지 않는다.

## 파일 지도

```
.gitignore · .env.example · CLAUDE.md
_docs/architecture.md · _docs/harness.md
infra/docker-compose.yml · infra/docker/Dockerfile · infra/caddy/Caddyfile
backend/
├── requirements.txt · pytest.ini · conftest.py · .importlinter · alembic.ini
├── main.py                         # API 프로세스: /health, /v1/me
├── auth_main.py                    # 인증 프로세스: /v1/auth/*
├── alembic/env.py · script.py.mako · versions/0001_users_and_social_identities.py
├── scripts/generate_dev_env.py · print_routes.py
├── core/
│   ├── singleton/secret_manager.py # 비밀값 관리자 (프로세스에 하나)
│   ├── config.py                   # 런타임 상수 (개인키 없음)
│   ├── auth_config.py              # 인증 프로세스 전용 상수 (개인키)
│   ├── database.py · redis.py
│   ├── http_errors.py              # ApiError, 오류 핸들러 설치
│   └── security.py                 # 액세스 토큰 검증, get_current_user_id
├── tests/                          # core 테스트
└── apps/
    ├── hub/                        # 계약 자리 (이 계획에서는 패키지와 문서만)
    └── auth/
        ├── domain/entities/{user,social_identity}.py
        ├── domain/value_objects/{provider,social_profile,social_credentials,refresh_lookup}.py
        ├── domain/services/refresh_token_factory.py
        ├── domain/errors.py
        ├── app/dtos/ · app/ports/{input,output}/ · app/use_cases/ · app/services/session_issuer.py
        ├── adapter/inbound/api/{schemas,v1}/ · adapter/inbound/api/error_map.py
        ├── adapter/outbound/{orm,pg,mappers,redis,gateways,strategy,factory}/
        ├── adapter/outbound/log_auth_myself_record_adapter.py
        ├── dependencies/
        └── tests/
```

---

### Task 1: 저장소 골격과 개발 환경

**Files:**
- Create: `.gitignore`, `.env.example`
- Create: `infra/docker/Dockerfile`, `infra/docker-compose.yml`, `infra/caddy/Caddyfile`
- Create: `backend/requirements.txt`, `backend/pytest.ini`, `backend/conftest.py`
- Create: `backend/core/__init__.py`, `backend/core/singleton/__init__.py`, `backend/core/singleton/secret_manager.py`
- Create: `backend/core/config.py`, `backend/core/auth_config.py`, `backend/core/database.py`, `backend/core/redis.py`
- Create: `backend/scripts/generate_dev_env.py`
- Create: `backend/main.py`, `backend/auth_main.py`
- Test: `backend/tests/__init__.py`, `backend/tests/test_secret_manager.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `core.singleton.secret_manager.SecretManager(root: Path)` — `get(name: str, default: str | None = None) -> str | None`, `require(name: str) -> str`, `load_auth_env() -> None`
  - `core.singleton.secret_manager.get_secret_manager() -> SecretManager`
  - `core.config`: `APP_ENV: str`, `DATABASE_URL: str`, `REDIS_URL: str`, `JWT_PUBLIC_KEY: str`(PEM), `ACCESS_TOKEN_TTL_SECONDS = 900`, `REFRESH_TOKEN_TTL_SECONDS = 2592000`, `KAKAO_APP_ID: str`, `GOOGLE_CLIENT_IDS: tuple[str, ...]`, `APPLE_BUNDLE_ID: str`, `APPLE_TEAM_ID: str`, `APPLE_KEY_ID: str`, `APPLE_PRIVATE_KEY: str`(PEM 또는 빈 문자열), `IDENTITY_TOKEN_ENC_KEY: str`
  - `core.auth_config.JWT_PRIVATE_KEY: str`(PEM)
  - `core.database`: `Base`, `init_engine()`, `dispose_engine()`, `get_db() -> AsyncGenerator[AsyncSession, None]`(성공 시 커밋, 예외 시 롤백)
  - `core.redis`: `get_redis() -> redis.asyncio.Redis`, `dispose_redis()`
  - `main.app`, `auth_main.app` (FastAPI)

- [ ] **Step 1: 도커가 도는지 확인한다**

Run: `docker info --format '{{.ServerVersion}}' && docker compose version`
Expected: 서버 버전과 `Docker Compose version v2.24` 이상이 출력된다. 실패하면 colima 또는 Docker Desktop을 먼저 켠다.

- [ ] **Step 2: git 저장소를 만들고 `.gitignore`를 쓴다**

Run: `git init -b main`

`.gitignore`:
```gitignore
.env
.env.*
!.env.example
.superpowers/
__pycache__/
*.pyc
.pytest_cache/
.import_linter_cache/
.DS_Store
.idea/
.vscode/
app/build/
app/.dart_tool/
```

- [ ] **Step 3: `.env.example`을 쓴다**

```dotenv
# 값은 비워 둔다. 개발용 실제 값은 backend/scripts/generate_dev_env.py 가 .env 와 .env.auth 로 만든다.
APP_ENV=dev
DATABASE_URL=
REDIS_URL=
JWT_PUBLIC_KEY_B64=
# 아래 하나는 .env.auth 에만 둔다 (인증 프로세스 전용)
JWT_PRIVATE_KEY_B64=
IDENTITY_TOKEN_ENC_KEY=
# 소셜 로그인 — 제공자 콘솔에 앱을 등록한 뒤 채운다. 비어 있으면 그 제공자는 꺼진다.
KAKAO_APP_ID=
KAKAO_REST_API_KEY=
KAKAO_ADMIN_KEY=
GOOGLE_CLIENT_ID_IOS=
GOOGLE_CLIENT_ID_ANDROID=
APPLE_BUNDLE_ID=
APPLE_TEAM_ID=
APPLE_KEY_ID=
APPLE_PRIVATE_KEY_B64=
# MinIO (계획 1에서는 기동만 한다)
S3_ENDPOINT_URL=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=
```

- [ ] **Step 4: 의존성과 이미지 정의를 쓴다**

`backend/requirements.txt`:
```text
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy[asyncio]>=2.0.30
asyncpg>=0.30
alembic>=1.13
pydantic>=2.9
redis>=5.0
python-jose[cryptography]>=3.3
cryptography>=43
httpx>=0.27
python-dotenv>=1.0
import-linter>=2.0
pytest>=8.0
pytest-asyncio>=0.24
```

`infra/docker/Dockerfile`:
```dockerfile
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /work/backend
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt
```

- [ ] **Step 5: compose와 게이트웨이를 쓴다**

`infra/docker-compose.yml`:
```yaml
name: chagocnote

x-backend-base: &backend-base
  build:
    context: ..
    dockerfile: infra/docker/Dockerfile
  image: chagocnote-backend:dev
  working_dir: /work/backend
  volumes:
    - ..:/work
  environment:
    PYTHONPATH: /work/backend:/work/backend/apps
  depends_on:
    pgvector:
      condition: service_healthy
    redis:
      condition: service_started

services:
  pgvector:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: chagoc
      POSTGRES_PASSWORD: chagoc_dev   # 개발 전용. 127.0.0.1 에만 열린다. 운영 구성에 재사용하지 않는다.
      POSTGRES_DB: chagocnote
    ports:
      - "127.0.0.1:5442:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U chagoc -d chagocnote"]
      interval: 3s
      retries: 20

  redis:
    image: redis:7-alpine
    ports:
      - "127.0.0.1:6389:6379"

  minio:
    image: minio/minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: chagoc
      MINIO_ROOT_PASSWORD: chagoc_dev_minio   # 개발 전용
    ports:
      - "127.0.0.1:9010:9000"
      - "127.0.0.1:9011:9001"
    volumes:
      - miniodata:/data

  backend:
    <<: *backend-base
    env_file:
      - path: ../.env
        required: false
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  auth:
    <<: *backend-base
    env_file:
      - path: ../.env
        required: false
      - path: ../.env.auth
        required: false
    command: uvicorn auth_main:app --host 0.0.0.0 --port 9000 --reload

  gateway:
    image: caddy:2-alpine
    volumes:
      - ./caddy/Caddyfile:/etc/caddy/Caddyfile:ro
    ports:
      - "127.0.0.1:8080:8080"
    depends_on:
      - backend
      - auth

volumes:
  pgdata:
  miniodata:
```

`infra/caddy/Caddyfile`:
```caddyfile
:8080 {
	handle /v1/auth/* {
		reverse_proxy auth:9000
	}
	handle {
		reverse_proxy backend:8000
	}
}
```

- [ ] **Step 6: 이미지를 빌드한다**

Run: `cd infra && docker compose build backend`
Expected: `chagocnote-backend:dev` 이미지가 만들어진다.

- [ ] **Step 7: pytest 설정과 패키지 파일을 쓴다**

`backend/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
markers =
    integration: compose 의 실제 Postgres·Redis 에 붙는 테스트
    network: 외부 제공자(카카오·구글·Apple) 서버를 호출하는 테스트
```

`backend/conftest.py`:
```python
"""pytest 루트 설정 — 통합 테스트용 공용 픽스처는 작업 4에서 여기에 추가한다."""
```

`backend/core/__init__.py`, `backend/core/singleton/__init__.py`, `backend/tests/__init__.py`: 빈 파일.

`backend/apps/` 폴더에는 `__init__.py`를 만들지 않는다. `apps/`는 패키지가 아니라 최상위 패키지들(`auth`, `hub`)을 담는 폴더다. PYTHONPATH에 `apps/`가 올라가 있어서 `from auth.app… import …`로 import한다. `__init__.py`를 두면 pytest가 테스트 모듈을 `apps.auth.…`라는 다른 이름으로 불러와 같은 코드가 두 이름으로 import된다.

- [ ] **Step 8: 비밀값 관리자의 실패하는 테스트를 쓴다**

`backend/tests/test_secret_manager.py`:
```python
import pytest

from core.singleton.secret_manager import SecretManager, get_secret_manager


def _write(path, text):
    path.write_text(text, encoding="utf-8")


def test_환경변수가_파일값보다_우선한다(tmp_path, monkeypatch):
    _write(tmp_path / ".env", "SAMPLE_KEY=from_file\n")
    monkeypatch.setenv("SAMPLE_KEY", "from_env")
    assert SecretManager(tmp_path).get("SAMPLE_KEY") == "from_env"


def test_환경변수가_없으면_파일값을_쓴다(tmp_path, monkeypatch):
    _write(tmp_path / ".env", "SAMPLE_KEY=from_file\n")
    monkeypatch.delenv("SAMPLE_KEY", raising=False)
    assert SecretManager(tmp_path).get("SAMPLE_KEY") == "from_file"


def test_값이_없으면_기본값을_돌려준다(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    assert SecretManager(tmp_path).get("MISSING_KEY", "fallback") == "fallback"


def test_require는_값이_없으면_변수명을_담아_실패한다(tmp_path, monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MISSING_KEY"):
        SecretManager(tmp_path).require("MISSING_KEY")


def test_auth_env는_명시적으로_불러야_보인다(tmp_path, monkeypatch):
    _write(tmp_path / ".env.auth", "PRIVATE_SAMPLE=secret\n")
    monkeypatch.delenv("PRIVATE_SAMPLE", raising=False)
    manager = SecretManager(tmp_path)
    assert manager.get("PRIVATE_SAMPLE") is None
    manager.load_auth_env()
    assert manager.get("PRIVATE_SAMPLE") == "secret"


def test_get_secret_manager는_같은_인스턴스를_돌려준다():
    assert get_secret_manager() is get_secret_manager()
```

- [ ] **Step 9: 테스트가 실패하는지 확인한다**

Run: `cd infra && docker compose run --rm --no-deps backend pytest tests/test_secret_manager.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.singleton.secret_manager'`

- [ ] **Step 10: 비밀값 관리자를 구현한다**

`backend/core/singleton/secret_manager.py`:
```python
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
```

- [ ] **Step 11: 테스트가 통과하는지 확인한다**

Run: `cd infra && docker compose run --rm --no-deps backend pytest tests/test_secret_manager.py -q -p no:cacheprovider`
Expected: `6 passed`

- [ ] **Step 12: 설정 상수와 DB·Redis 연결을 쓴다**

`backend/core/config.py`:
```python
"""런타임 상수 — 앱 코드는 비밀값 관리자를 직접 부르지 않고 여기 상수만 쓴다.

JWT 개인키는 여기 두지 않는다 (core/auth_config.py). API 프로세스는 토큰을 발급할 수 없어야 한다.
"""
from __future__ import annotations

import base64

from core.singleton.secret_manager import get_secret_manager

_m = get_secret_manager()


def _b64_pem(name: str) -> str:
    raw = _m.get(name, "")
    return base64.b64decode(raw).decode() if raw else ""


APP_ENV: str = _m.get("APP_ENV", "dev") or "dev"
DATABASE_URL: str = _m.require("DATABASE_URL")
REDIS_URL: str = _m.get("REDIS_URL", "redis://redis:6379/0") or "redis://redis:6379/0"
JWT_PUBLIC_KEY: str = base64.b64decode(_m.require("JWT_PUBLIC_KEY_B64")).decode()

ACCESS_TOKEN_TTL_SECONDS = 15 * 60
REFRESH_TOKEN_TTL_SECONDS = 30 * 24 * 60 * 60

KAKAO_APP_ID: str = _m.get("KAKAO_APP_ID", "") or ""
GOOGLE_CLIENT_IDS: tuple[str, ...] = tuple(
    v for v in (_m.get("GOOGLE_CLIENT_ID_IOS", ""), _m.get("GOOGLE_CLIENT_ID_ANDROID", "")) if v
)
APPLE_BUNDLE_ID: str = _m.get("APPLE_BUNDLE_ID", "") or ""
APPLE_TEAM_ID: str = _m.get("APPLE_TEAM_ID", "") or ""
APPLE_KEY_ID: str = _m.get("APPLE_KEY_ID", "") or ""
APPLE_PRIVATE_KEY: str = _b64_pem("APPLE_PRIVATE_KEY_B64")
IDENTITY_TOKEN_ENC_KEY: str = _m.get("IDENTITY_TOKEN_ENC_KEY", "") or ""
```

`backend/core/auth_config.py`:
```python
"""인증 프로세스 전용 상수 — JWT 개인키. auth_main.py 경로에서만 import 한다."""
from __future__ import annotations

import base64

from core.singleton.secret_manager import get_secret_manager

JWT_PRIVATE_KEY: str = base64.b64decode(
    get_secret_manager().require("JWT_PRIVATE_KEY_B64")
).decode()
```

`backend/core/database.py`:
```python
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import DATABASE_URL


class Base(DeclarativeBase):
    pass


engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engine() -> None:
    global engine, _session_factory
    if engine is not None:
        return
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, echo=False)
    _session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def dispose_engine() -> None:
    global engine, _session_factory
    if engine is not None:
        await engine.dispose()
    engine = None
    _session_factory = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """요청 하나에 세션 하나. 성공하면 커밋하고 예외가 나면 롤백한다."""
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

`backend/core/redis.py`:
```python
from __future__ import annotations

from redis.asyncio import Redis, from_url

from core.config import REDIS_URL

_client: Redis | None = None


def get_redis() -> Redis:
    global _client
    if _client is None:
        _client = from_url(REDIS_URL, decode_responses=True)
    return _client


async def dispose_redis() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
    _client = None
```

- [ ] **Step 13: 개발용 `.env` 생성 스크립트를 쓰고 실행한다**

`backend/scripts/generate_dev_env.py`:
```python
"""개발용 .env · .env.auth 를 만든다. 이미 있으면 건드리지 않는다."""
from __future__ import annotations

import base64
from pathlib import Path

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    env, auth_env = ROOT / ".env", ROOT / ".env.auth"
    if env.exists() or auth_env.exists():
        print(".env 또는 .env.auth 가 이미 있어서 건너뜁니다.")
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    env.write_text(
        "APP_ENV=dev\n"
        "DATABASE_URL=postgresql+asyncpg://chagoc:chagoc_dev@pgvector:5432/chagocnote\n"
        "REDIS_URL=redis://redis:6379/0\n"
        f"JWT_PUBLIC_KEY_B64={base64.b64encode(public_pem).decode()}\n"
        f"IDENTITY_TOKEN_ENC_KEY={Fernet.generate_key().decode()}\n"
        "S3_ENDPOINT_URL=http://minio:9000\n"
        "S3_ACCESS_KEY=chagoc\n"
        "S3_SECRET_KEY=chagoc_dev_minio\n"
        "S3_BUCKET=chagocnote-dev\n",
        encoding="utf-8",
    )
    auth_env.write_text(
        f"JWT_PRIVATE_KEY_B64={base64.b64encode(private_pem).decode()}\n",
        encoding="utf-8",
    )
    print("만들었습니다:", env, auth_env)


if __name__ == "__main__":
    main()
```

Run: `cd infra && docker compose run --rm --no-deps backend python scripts/generate_dev_env.py`
Expected: `만들었습니다: /work/.env /work/.env.auth`. 저장소 루트에 두 파일이 생기고 `git status`에는 나타나지 않는다.

- [ ] **Step 14: 두 프로세스의 진입점을 쓴다**

`backend/main.py`:
```python
"""API 프로세스 — 공개키로 토큰을 검증만 한다. 토큰을 발급할 수 없다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 API", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
```

`backend/auth_main.py`:
```python
"""인증 프로세스 — JWT 개인키를 가진 유일한 프로세스. /v1/auth/* 만 맡는다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from core.singleton.secret_manager import get_secret_manager

# 컨테이너는 env_file 로 주입받는다. 이 호출은 컨테이너 밖에서 돌릴 때를 위한 것이다.
get_secret_manager().load_auth_env()

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 Auth", lifespan=lifespan)


@app.get("/v1/auth/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "auth"}
```

- [ ] **Step 15: 전체를 띄워서 게이트웨이 경로를 확인한다**

Run:
```bash
cd infra && docker compose up -d
sleep 6
curl -s http://127.0.0.1:8080/health; echo
curl -s http://127.0.0.1:8080/v1/auth/health; echo
```
Expected:
```
{"status":"ok","process":"backend"}
{"status":"ok","process":"auth"}
```

- [ ] **Step 16: 커밋 (허용된 경우)**

```bash
git add .gitignore .env.example infra backend
git commit -m "chore(infra): 저장소 골격과 compose 개발 환경"
```

---

### Task 2: 구조 계약과 하네스 문서

**Files:**
- Create: `backend/.importlinter`
- Create: `backend/apps/hub/__init__.py`, `backend/apps/hub/app/__init__.py`, `backend/apps/hub/app/ports/__init__.py`, `backend/apps/hub/app/dtos/__init__.py`
- Create: `backend/apps/auth/__init__.py`와 아래 패키지들의 `__init__.py`(모두 빈 파일): `domain`, `domain/entities`, `domain/value_objects`, `domain/services`, `app`, `app/dtos`, `app/ports`, `app/ports/input`, `app/ports/output`, `app/use_cases`, `app/services`, `adapter`, `adapter/inbound`, `adapter/inbound/api`, `adapter/inbound/api/schemas`, `adapter/inbound/api/v1`, `adapter/outbound`, `adapter/outbound/orm`, `adapter/outbound/pg`, `adapter/outbound/mappers`, `adapter/outbound/redis`, `adapter/outbound/gateways`, `adapter/outbound/strategy`, `adapter/outbound/factory`, `dependencies`, `tests`, `tests/app`, `tests/app/use_cases`, `tests/adapter`, `tests/domain`, `tests/helpers`
- Create: `CLAUDE.md`, `_docs/architecture.md`, `_docs/harness.md`
- Create: `backend/apps/hub/_docs/CLAUDE.md`, `backend/apps/auth/_docs/CLAUDE.md`와 각 앱 루트의 심볼릭 링크 `CLAUDE.md`

**Interfaces:**
- Consumes: Task 1의 compose 환경
- Produces: `lint-imports --config .importlinter`가 통과하는 상태. 이후 모든 작업은 이 계약을 지켜야 한다.

- [ ] **Step 1: 패키지 뼈대를 만든다**

Run:
```bash
cd backend/apps
mkdir -p hub/app/ports hub/app/dtos hub/_docs
mkdir -p auth/domain/{entities,value_objects,services} \
  auth/app/{dtos,use_cases,services} auth/app/ports/{input,output} \
  auth/adapter/inbound/api/{schemas,v1} \
  auth/adapter/outbound/{orm,pg,mappers,redis,gateways,strategy,factory} \
  auth/dependencies auth/tests/app/use_cases auth/tests/adapter auth/tests/domain auth/tests/helpers auth/_docs
find hub auth -type d -not -name _docs -exec touch {}/__init__.py \;
```
Expected: `find hub auth -name __init__.py | wc -l`이 36을 출력한다.

- [ ] **Step 2: 구조 계약을 쓴다**

`backend/.importlinter`:
```ini
# =============================================================================
# import-linter — 차곡노트 백엔드 구조 계약
# =============================================================================
# (1) 앱 내부  — 헥사고날: adapter → app → domain (역방향 금지)
# (2) 앱 사이  — 허브-스포크: 스포크끼리 직접 참조 금지, 허브는 스포크를 모른다
#
# 실행: cd infra && docker compose run --rm --no-deps backend lint-imports --config .importlinter
#
# 계약 "스포크 상호 독립"은 두 번째 스포크(tenancy)가 생기는 계획 2에서 추가한다.
# 스포크가 하나뿐일 때는 검사할 쌍이 없다.
# =============================================================================

[importlinter]
root_packages =
    hub
    auth
include_external_packages = True

[importlinter:contract:clean-architecture]
name = 클린 아키텍처 계층 (adapter > app > domain)
type = layers
layers =
    (adapter)
    app
    (domain)
containers =
    hub
    auth

[importlinter:contract:framework-isolation]
name = 프레임워크 격리 (app·domain 은 웹·DB·외부 통신 라이브러리를 모른다)
type = forbidden
source_modules =
    hub.app
    auth.app
    auth.domain
forbidden_modules =
    fastapi
    sqlalchemy
    redis
    httpx
    jose
    cryptography

[importlinter:contract:domain-purity]
name = 도메인 순수성 (domain 은 pydantic 과 core 도 모른다)
type = forbidden
source_modules =
    auth.domain
forbidden_modules =
    pydantic
    core

[importlinter:contract:hub-isolation]
name = 허브 격리 (hub 는 스포크를 import 하지 않는다)
type = forbidden
source_modules =
    hub
forbidden_modules =
    auth
```

- [ ] **Step 3: 계약이 통과하는지 확인한다**

Run: `cd infra && docker compose run --rm --no-deps backend lint-imports --config .importlinter`
Expected: `Contracts: 4 kept, 0 broken.`

- [ ] **Step 4: 계약이 실제로 위반을 잡는지 확인한다**

Run:
```bash
printf 'import fastapi  # 일부러 넣은 위반\n' > backend/apps/auth/domain/_violation_probe.py
cd infra && docker compose run --rm --no-deps backend lint-imports --config .importlinter; echo "exit=$?"
rm ../backend/apps/auth/domain/_violation_probe.py
```
Expected: `프레임워크 격리 ... BROKEN`이 출력되고 `exit=1`이다. 파일을 지운 뒤 Step 3을 다시 돌리면 `4 kept`로 돌아온다.

- [ ] **Step 5: 루트 하네스 문서를 쓴다**

`CLAUDE.md`:
```markdown
# CLAUDE.md — 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 에이전트는 코드·설정·명령을 제안하거나 실행하기 전에 이 문서를 먼저 읽는다.

## 언어

- 항상 한국어로 응답한다. 주석·문서·테스트 이름·커밋 메시지도 한국어다.

## 저장소

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · gateway) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

먼저 읽을 문서: `_docs/architecture.md`(계층·슬라이스·폴더 작명 규칙), `_docs/harness.md`(검증 명령). 앱 폴더에서 작업할 때는 그 앱의 `CLAUDE.md`도 읽는다.

## 꼭 지킬 것

- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 코드·패키지명·문서에서 플랫폼 이름으로 쓰지 않는다.
- 스포크끼리 직접 import하지 않는다. 교차 협력은 `apps/hub`의 포트를 거친다. 허브는 스포크를 모른다.
- JWT 개인키는 인증 프로세스(`auth_main.py`)만 가진다. `core/auth_config.py`를 API 프로세스 경로에서 import하지 않는다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
- 비밀값을 로그·커밋·문서에 남기지 않는다. `.env*` 파일 내용을 그대로 출력하지 않는다.
- 커밋과 푸시는 사용자가 요청할 때만 한다. CI는 없다. 검증은 로컬에서 한다.
- 볼륨 삭제, `docker compose down -v`, 스키마를 파괴하는 명령은 사용자 확인 없이 실행하지 않는다.

## 명령어

전부 `infra/`에서 실행한다. 맥에 파이썬 환경을 만들지 않는다.

    docker compose up -d                          # 전체 기동 (게이트웨이 http://127.0.0.1:8080)
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
    docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
    docker compose run --rm --no-deps backend lint-imports --config .importlinter
    docker compose run --rm --no-deps auth python scripts/print_routes.py      # 개인키가 필요해서 auth 서비스에서 돌린다
```

`_docs/architecture.md`:
```markdown
# 아키텍처 규칙

## 계층

앱 내부는 `adapter → app → domain` 방향으로만 의존한다. `dependencies/`는 조립 전용이라 어느 계층이든 import할 수 있다.

    <app>/
    ├── domain/{entities,value_objects,services}/   # 표준 라이브러리만
    ├── app/{ports/{input,output},use_cases,dtos,services}/
    ├── adapter/inbound/api/{schemas,v1}/
    ├── adapter/outbound/{orm,pg,mappers,redis,gateways, …GoF 이름 폴더}/
    ├── dependencies/
    └── tests/

## 수직 슬라이스 1:1

유스케이스마다 `<이름>_router` · `<이름>_schema` · `<이름>_dto` · `ports/input/<이름>_use_case` · 아웃바운드 포트 · `<이름>_interactor` · `<이름>_provider` · `test_<이름>_interactor`를 하나씩 둔다. 한 파일에 여러 슬라이스를 넣지 않는다.

허용하는 예외는 세 가지다.
1. HTTP 표면이 없는 슬라이스는 schema와 router를 생략한다.
2. DTO와 리포지토리는 도메인 말로 이름 지을 수 있다 (`token_dto`, `user_repository`).
3. entity·VO·mapper는 로직이 있을 때만 만든다.

새 라우터 묶음에는 `GET <prefix>/myself`를 둔다. 제공하는 엔드포인트, 다루는 데이터, 제약을 실제대로 적는다. 배역이나 은유를 쓰지 않는다.

유스케이스는 어댑터 스키마가 아니라 app DTO(frozen dataclass)를 받는다. 스키마와 DTO 사이의 변환은 라우터가 한다. 아웃바운드 포트는 인터랙터가 실제로 호출하는 메서드만 가진다.

## 허브-스포크

- 허브는 `apps/hub`다. 포트(ABC)와 DTO만 가진다.
- 스포크는 허브의 추상에만 의존한다. 스포크끼리 import하지 않고, 허브는 스포크를 import하지 않는다.
- 스포크를 넘는 외래 키는 걸지 않는다. 다른 스포크의 ID는 인덱스만 있는 정수 컬럼이다.
- `core/`는 인프라 공유(DB 세션, 설정, 토큰 검증)만 맡는다. `core/security.py`가 `users` 테이블을 원시 SQL로 조회하는 것은 의도한 예외다. core가 스포크의 ORM을 import할 수 없기 때문이다.

## 프로세스 배치

`/v1/auth/*` 경로의 라우터는 인증 프로세스(`auth_main.py`)에, 나머지는 전부 API 프로세스(`main.py`)에 장착한다. 게이트웨이도 같은 규칙으로 경로를 나눈다.

## GoF 폴더 작명 규칙

통상적인 폴더 이름은 그대로 쓴다. 그 밖에 기능을 묶으려고 새로 만드는 폴더에는 GoF 패턴 이름을 붙인다. 조건은 두 가지다.
1. 폴더의 코드가 실제로 그 패턴을 구현할 때만 붙인다. 맞는 패턴이 없으면 평범한 도메인 단어를 쓴다.
2. 스포크 이름은 도메인의 말을 유지한다. `hub`도 그대로 둔다.

| 위치 | 패턴 | 내용 |
|---|---|---|
| `core/singleton/` | Singleton | 비밀값 관리자처럼 프로세스에 하나만 있는 객체 |
| `auth/adapter/outbound/strategy/` | Strategy | 제공자별 `SocialProviderPort` 구현 |
| `auth/adapter/outbound/factory/` | Factory Method | 제공자 이름으로 구현을 골라 돌려준다 |
| `visit/domain/state/` (예정) | State | 방문 상태 전이 |
| `core/observer/`, `<app>/adapter/inbound/observer/` (예정) | Observer | 도메인 이벤트 발행과 구독 |
| `visit/domain/chain/` (예정) | Chain of Responsibility | 예약 체크리스트 규칙 |
| `search/adapter/outbound/decorator/` (예정) | Decorator | LLM 포트를 감싼 개인정보 마스킹 |
| `visit/app/template/` (예정) | Template Method | 말로 기록하기 절차의 뼈대 |
| `search/app/facade/` (예정) | Facade | RAG 단일 입구 |
| `notification/adapter/outbound/strategy/` (예정) | Strategy | 알림 발송 수단 |
| `app/lib/core/proxy/` (예정) | Proxy | 토큰 자동 첨부·갱신 API 클라이언트 |
| `app/lib/design/bridge/` (예정) | Bridge | 글래스 구현 교체 지점 |

새 패턴 폴더를 만들면 이 표에 한 줄을 더한다.

## 도메인 이벤트 도입 계획

이벤트 발행 포트는 첫 구독자가 생길 때(미용 완료 → 통계·검색·알림) 허브에 도입한다. 처음에는 같은 프로세스 안의 단순한 구현으로 시작하고, 신뢰성이 필요해지면 아웃박스 방식으로 어댑터만 바꾼다. 그 전에는 포트를 만들지 않는다.
```

`_docs/harness.md`:
```markdown
# 검증 장치

모든 명령은 `infra/`에서 실행한다.

| 무엇을 | 명령 |
|---|---|
| 단위 테스트 | `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` |
| 통합 테스트 (실제 Postgres·Redis) | `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` |
| 구조 계약 | `docker compose run --rm --no-deps backend lint-imports --config .importlinter` |
| 라우트 표 | `docker compose run --rm --no-deps auth python scripts/print_routes.py` (인증 프로세스를 import하려면 개인키가 필요해서 `auth` 서비스에서 돌린다) |

- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 만들어 쓴다. 개발 데이터를 건드리지 않는다.
- 구조 위반은 테스트가 아니라 import-linter가 잡는다. 구조를 건드린 변경은 테스트와 구조 계약을 둘 다 돌린다.
- 라우터를 추가하거나 옮긴 변경은 라우트 표를 변경 전후로 비교한다.
- 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다.
```

- [ ] **Step 6: 앱별 문서와 심볼릭 링크를 만든다**

`backend/apps/hub/_docs/CLAUDE.md`:
```markdown
# hub — 허브

스포크 사이의 계약(포트 ABC와 DTO)만 가진다. 구현은 스포크가 제공한다.

- 어떤 스포크도 import하지 않는다 (`.importlinter`의 허브 격리 계약).
- 포트는 실제로 쓰는 스포크가 생길 때 추가한다. 빈 껍데기 포트를 미리 만들지 않는다.
- 지금은 포트가 없다. 첫 포트는 tenancy 스포크와 함께 들어온다.
```

`backend/apps/auth/_docs/CLAUDE.md`:
```markdown
# auth — 신원과 토큰

소유 데이터: `users`, `social_identities`, Redis의 리프레시 토큰.

- User는 플랫폼에 하나만 있는 신원이다. 사장·직원·보호자는 계정 종류가 아니라 매장과의 관계이며 auth는 그 관계를 모른다.
- 토큰에는 유저 ID만 담는다. 역할과 권한을 넣지 않는다.
- 리프레시 토큰은 쓸 때마다 새 토큰으로 바꾼다. 이미 쓴 토큰이 다시 들어오면 그 유저의 세션을 모두 폐기한다.
- 제공자별 검증은 `adapter/outbound/strategy/`에, 제공자를 고르는 코드는 `adapter/outbound/factory/`에 둔다.
- 개발용 제공자 `dev`는 `APP_ENV=dev`일 때만 등록된다. 이 동작은 테스트로 고정되어 있다.
- 토큰을 발급하는 코드는 `core/auth_config.py`(개인키)를 함수 안에서 import한다. 모듈 최상단에서 import하면 API 프로세스에서 모듈을 불러올 때 실패한다.
```

Run:
```bash
cd backend/apps
ln -s _docs/CLAUDE.md hub/CLAUDE.md
ln -s _docs/CLAUDE.md auth/CLAUDE.md
```
Expected: `ls -l hub/CLAUDE.md auth/CLAUDE.md`가 두 링크를 보여준다.

- [ ] **Step 7: 커밋 (허용된 경우)**

```bash
git add CLAUDE.md _docs backend/.importlinter backend/apps
git commit -m "chore(harness): 구조 계약 4종과 하네스 문서"
```

---

### Task 3: auth 자기소개 슬라이스 (`GET /v1/auth/myself`)

**Files:**
- Create: `backend/apps/auth/app/dtos/auth_myself_dto.py`
- Create: `backend/apps/auth/app/ports/input/auth_myself_use_case.py`
- Create: `backend/apps/auth/app/ports/output/auth_myself_record_port.py`
- Create: `backend/apps/auth/app/use_cases/auth_myself_interactor.py`
- Create: `backend/apps/auth/adapter/outbound/log_auth_myself_record_adapter.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/auth_myself_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/auth_myself_router.py`
- Create: `backend/apps/auth/dependencies/auth_myself_provider.py`
- Modify: `backend/auth_main.py` (라우터 장착)
- Test: `backend/apps/auth/tests/app/use_cases/test_auth_myself_interactor.py`, `backend/apps/auth/tests/adapter/test_auth_myself_router.py`

**Interfaces:**
- Consumes: Task 2의 패키지 뼈대
- Produces: `auth.adapter.inbound.api.v1.auth_myself_router.auth_myself_router` (prefix `/v1/auth`)

- [ ] **Step 1: 인터랙터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_auth_myself_interactor.py`:
```python
from auth.app.dtos.auth_myself_dto import AuthMyselfQuery
from auth.app.use_cases.auth_myself_interactor import AuthMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await AuthMyselfInteractor(record=record).introduce_myself(
        AuthMyselfQuery(id=1, name="인증 (auth)")
    )
    assert result.id == 1
    assert "/v1/auth/social" in result.introduction
    assert "/v1/auth/refresh" in result.introduction
    assert "역할" in result.introduction
    assert record.records[0][0] == "introduce_myself"
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_auth_myself_interactor.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.auth_myself_dto'`

- [ ] **Step 3: DTO·포트·인터랙터·기록 어댑터를 구현한다**

`backend/apps/auth/app/dtos/auth_myself_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AuthMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class AuthMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/auth/app/ports/input/auth_myself_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.auth_myself_dto import AuthMyselfQuery, AuthMyselfResponse


class AuthMyselfUseCase(ABC):
    """인증 (auth) 라우터 묶음의 자기소개."""

    @abstractmethod
    async def introduce_myself(self, query: AuthMyselfQuery) -> AuthMyselfResponse: ...
```

`backend/apps/auth/app/ports/output/auth_myself_record_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class AuthMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/auth/app/use_cases/auth_myself_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.auth_myself_dto import AuthMyselfQuery, AuthMyselfResponse
from auth.app.ports.input.auth_myself_use_case import AuthMyselfUseCase
from auth.app.ports.output.auth_myself_record_port import AuthMyselfRecordPort


class AuthMyselfInteractor(AuthMyselfUseCase):
    def __init__(self, record: AuthMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: AuthMyselfQuery) -> AuthMyselfResponse:
        await self._record.record(
            subject="introduce_myself", note=f"{query.name} 자기소개 조회"
        )
        return AuthMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "소셜 로그인으로 신원을 확인하고 차곡노트 자체 토큰을 발급합니다. "
                "POST /v1/auth/social 은 카카오·구글·Apple(개발 환경에서는 dev)의 토큰을 받아 "
                "제공자에게 직접 검증한 뒤 액세스 토큰(15분)과 리프레시 토큰(30일)을 돌려줍니다. "
                "POST /v1/auth/refresh 는 리프레시 토큰을 새 토큰으로 바꿉니다. 이미 쓴 토큰이 다시 오면 "
                "탈취로 보고 그 유저의 세션을 모두 폐기합니다. "
                "POST /v1/auth/logout 은 리프레시 토큰을 폐기합니다. "
                "토큰에는 유저 ID만 들어 있고 역할과 권한은 넣지 않습니다. "
                "앱이 보낸 프로필은 믿지 않으며 카카오·구글 토큰은 저장하지 않습니다."
            ),
        )
```

`backend/apps/auth/adapter/outbound/log_auth_myself_record_adapter.py`:
```python
from __future__ import annotations

import logging

from auth.app.ports.output.auth_myself_record_port import AuthMyselfRecordPort

logger = logging.getLogger(__name__)


class LogAuthMyselfRecordAdapter(AuthMyselfRecordPort):
    """기록을 로그로 남기는 구현. 영속 기록이 필요해지면 PG 어댑터로 바꾼다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[auth-myself-record] %s | %s", subject, note)
```

- [ ] **Step 4: 인터랙터 테스트가 통과하는지 확인한다**

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_auth_myself_interactor.py -q -p no:cacheprovider`
Expected: `1 passed`

- [ ] **Step 5: 라우터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_auth_myself_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.v1.auth_myself_router import auth_myself_router


async def test_myself_는_인증_없이_200과_자기소개를_돌려준다():
    app = FastAPI()
    app.include_router(auth_myself_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/auth/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "인증 (auth)"
    assert "/v1/auth/social" in body["introduction"]
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_auth_myself_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.inbound.api.v1.auth_myself_router'`

- [ ] **Step 6: 스키마·프로바이더·라우터를 구현한다**

`backend/apps/auth/adapter/inbound/api/schemas/auth_myself_schema.py`:
```python
from pydantic import BaseModel


class AuthMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/auth/dependencies/auth_myself_provider.py`:
```python
from __future__ import annotations

from auth.adapter.outbound.log_auth_myself_record_adapter import LogAuthMyselfRecordAdapter
from auth.app.ports.input.auth_myself_use_case import AuthMyselfUseCase
from auth.app.use_cases.auth_myself_interactor import AuthMyselfInteractor


def get_auth_myself_use_case() -> AuthMyselfUseCase:
    return AuthMyselfInteractor(record=LogAuthMyselfRecordAdapter())
```

`backend/apps/auth/adapter/inbound/api/v1/auth_myself_router.py`:
```python
from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.auth_myself_schema import AuthMyselfResponseSchema
from auth.app.dtos.auth_myself_dto import AuthMyselfQuery
from auth.app.ports.input.auth_myself_use_case import AuthMyselfUseCase
from auth.dependencies.auth_myself_provider import get_auth_myself_use_case

auth_myself_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@auth_myself_router.get("/myself", response_model=AuthMyselfResponseSchema)
async def introduce_myself(
    use_case: AuthMyselfUseCase = Depends(get_auth_myself_use_case),
) -> AuthMyselfResponseSchema:
    result = await use_case.introduce_myself(AuthMyselfQuery(id=1, name="인증 (auth)"))
    return AuthMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
```

- [ ] **Step 7: 인증 프로세스에 장착한다**

`backend/auth_main.py`에서 `from core.redis import dispose_redis` 아래에 추가:
```python
from auth.adapter.inbound.api.v1.auth_myself_router import auth_myself_router
```
`app = FastAPI(...)` 줄 아래에 추가:
```python
app.include_router(auth_myself_router)
```

- [ ] **Step 8: 테스트·구조 계약·실제 호출을 확인한다**

Run:
```bash
cd infra
docker compose run --rm --no-deps backend pytest apps/auth -q -p no:cacheprovider
docker compose run --rm --no-deps backend lint-imports --config .importlinter
curl -s http://127.0.0.1:8080/v1/auth/myself | head -c 120; echo
```
Expected: `2 passed`, `Contracts: 4 kept, 0 broken.`, 그리고 `{"id":1,"name":"인증 (auth)","introduction":"소셜 로그인으로 …`

- [ ] **Step 9: 커밋 (허용된 경우)**

```bash
git add backend/apps/auth backend/auth_main.py
git commit -m "feat(auth): 자기소개 슬라이스 GET /v1/auth/myself"
```

---

### Task 4: 유저와 소셜 신원의 영속 계층

**Files:**
- Create: `backend/apps/auth/domain/value_objects/provider.py`, `social_profile.py`
- Create: `backend/apps/auth/domain/entities/user.py`, `social_identity.py`
- Create: `backend/apps/auth/app/ports/output/user_repository.py`
- Create: `backend/apps/auth/adapter/outbound/orm/user_orm.py`
- Create: `backend/apps/auth/adapter/outbound/mappers/user_mapper.py`
- Create: `backend/apps/auth/adapter/outbound/gateways/fernet_cipher.py`
- Create: `backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`
- Create: `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_users_and_social_identities.py`
- Modify: `backend/conftest.py` (통합 테스트용 `db_session` 픽스처)
- Modify: `infra/docker-compose.yml` (backend 기동 시 마이그레이션)
- Test: `backend/apps/auth/tests/domain/test_user.py`, `backend/apps/auth/tests/adapter/test_user_pg_repository.py`

**Interfaces:**
- Consumes: `core.database.Base`, `core.config.DATABASE_URL`
- Produces:
  - `auth.domain.value_objects.provider.Provider` — `str` Enum: `KAKAO="kakao"`, `APPLE="apple"`, `GOOGLE="google"`, `DEV="dev"`
  - `auth.domain.value_objects.social_profile.SocialProfile(provider: Provider, provider_user_id: str, email: str | None, display_name: str | None, profile_image_url: str | None, provider_refresh_token: str | None)` — frozen dataclass
  - `auth.domain.entities.user.User(id, display_name, profile_image_url, phone, suspended_at, deleted_at)` — frozen dataclass, 프로퍼티 `is_suspended`, `is_deleted`
  - `auth.domain.entities.social_identity.SocialIdentity(id, user_id, provider: Provider, provider_user_id, email)`
  - `auth.app.ports.output.user_repository.UserRepository` — `async find_by_identity(provider: Provider, provider_user_id: str) -> User | None`, `async create_with_identity(profile: SocialProfile) -> User`, `async get(user_id: int) -> User | None`, `async list_identities(user_id: int) -> list[SocialIdentity]`
  - `auth.adapter.outbound.pg.user_pg_repository.UserPgRepository(session: AsyncSession, cipher: FernetCipher)`
  - `auth.adapter.outbound.gateways.fernet_cipher.FernetCipher(key: str)` — `encrypt(plain: str) -> str`
  - pytest 픽스처 `db_session` (`backend/conftest.py`): 테스트 DB `chagocnote_test`에 붙은 `AsyncSession`

- [ ] **Step 1: 도메인의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/domain/test_user.py`:
```python
from datetime import datetime, timezone

from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider


def _user(**overrides):
    base = dict(
        id=1, display_name="두부 보호자", profile_image_url=None, phone=None,
        suspended_at=None, deleted_at=None,
    )
    return User(**{**base, **overrides})


def test_정지_시각이_있으면_정지된_계정이다():
    assert _user().is_suspended is False
    assert _user(suspended_at=datetime.now(timezone.utc)).is_suspended is True


def test_삭제_시각이_있으면_탈퇴한_계정이다():
    assert _user().is_deleted is False
    assert _user(deleted_at=datetime.now(timezone.utc)).is_deleted is True


def test_제공자는_문자열_값으로_만들_수_있다():
    assert Provider("kakao") is Provider.KAKAO
    assert Provider.DEV.value == "dev"
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/domain/test_user.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.domain.entities.user'`

- [ ] **Step 2: 도메인 객체를 구현한다**

`backend/apps/auth/domain/value_objects/provider.py`:
```python
from enum import Enum


class Provider(str, Enum):
    KAKAO = "kakao"
    APPLE = "apple"
    GOOGLE = "google"
    DEV = "dev"
```

`backend/apps/auth/domain/value_objects/social_profile.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class SocialProfile:
    """제공자가 확인해 준 신원. 앱이 보낸 값이 아니라 제공자 응답에서만 만든다."""

    provider: Provider
    provider_user_id: str
    email: str | None
    display_name: str | None
    profile_image_url: str | None
    provider_refresh_token: str | None
```

`backend/apps/auth/domain/entities/user.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class User:
    id: int
    display_name: str
    profile_image_url: str | None
    phone: str | None
    suspended_at: datetime | None
    deleted_at: datetime | None

    @property
    def is_suspended(self) -> bool:
        return self.suspended_at is not None

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
```

`backend/apps/auth/domain/entities/social_identity.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class SocialIdentity:
    id: int
    user_id: int
    provider: Provider
    provider_user_id: str
    email: str | None
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/domain/test_user.py -q -p no:cacheprovider`
Expected: `3 passed`

- [ ] **Step 3: 리포지토리 포트를 쓴다**

`backend/apps/auth/app/ports/output/user_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserRepository(ABC):
    @abstractmethod
    async def find_by_identity(self, provider: Provider, provider_user_id: str) -> User | None: ...

    @abstractmethod
    async def create_with_identity(self, profile: SocialProfile) -> User: ...

    @abstractmethod
    async def get(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def list_identities(self, user_id: int) -> list[SocialIdentity]: ...
```

- [ ] **Step 4: 통합 테스트용 픽스처를 쓴다**

`backend/conftest.py` 전체를 아래로 바꾼다:
```python
"""pytest 루트 설정 — 통합 테스트용 공용 픽스처."""
from __future__ import annotations

import pytest

TEST_DB = "chagocnote_test"


@pytest.fixture
async def db_session():
    """별도 데이터베이스 chagocnote_test 에 붙은 세션. 테스트마다 테이블을 새로 만든다."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    import auth.adapter.outbound.orm.user_orm  # noqa: F401 — 메타데이터 등록
    from core.config import DATABASE_URL
    from core.database import Base

    admin = create_async_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with admin.connect() as conn:
        exists = (
            await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB}
            )
        ).scalar()
        if not exists:
            await conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
    await admin.dispose()

    engine = create_async_engine(DATABASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with async_sessionmaker(engine, expire_on_commit=False, autoflush=False)() as session:
        yield session
    await engine.dispose()
```

- [ ] **Step 5: 리포지토리의 실패하는 통합 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_user_pg_repository.py`:
```python
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import text

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile

pytestmark = pytest.mark.integration


def _profile(**overrides):
    base = dict(
        provider=Provider.KAKAO, provider_user_id="kakao-100", email="a@example.com",
        display_name="두부 보호자", profile_image_url=None, provider_refresh_token=None,
    )
    return SocialProfile(**{**base, **overrides})


def _repo(session):
    return UserPgRepository(session, FernetCipher(Fernet.generate_key().decode()))


async def test_신원으로_유저를_만들고_다시_찾는다(db_session):
    repo = _repo(db_session)
    created = await repo.create_with_identity(_profile())
    found = await repo.find_by_identity(Provider.KAKAO, "kakao-100")
    assert found is not None and found.id == created.id
    assert found.display_name == "두부 보호자"


async def test_없는_신원은_None_이다(db_session):
    assert await _repo(db_session).find_by_identity(Provider.GOOGLE, "nobody") is None


async def test_이름이_없는_프로필은_기본_이름으로_만든다(db_session):
    user = await _repo(db_session).create_with_identity(_profile(display_name=None))
    assert user.display_name == "이름 없음"


async def test_연결된_로그인_수단_목록을_돌려준다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    identities = await repo.list_identities(user.id)
    assert [i.provider for i in identities] == [Provider.KAKAO]


async def test_제공자_리프레시_토큰은_암호화해서_저장한다(db_session):
    repo = _repo(db_session)
    await repo.create_with_identity(
        _profile(provider=Provider.APPLE, provider_user_id="apple-1", provider_refresh_token="plain-token")
    )
    stored = (
        await db_session.execute(
            text("SELECT provider_refresh_token_enc FROM social_identities WHERE provider = 'apple'")
        )
    ).scalar_one()
    assert stored and stored != "plain-token"
```

Run: `cd infra && docker compose run --rm backend pytest apps/auth/tests/adapter/test_user_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.outbound.gateways.fernet_cipher'`

- [ ] **Step 6: ORM·매퍼·암호화·리포지토리를 구현한다**

`backend/apps/auth/adapter/outbound/orm/user_orm.py`:
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserOrm(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    display_name: Mapped[str] = mapped_column(String(50))
    profile_image_url: Mapped[str | None] = mapped_column(String(500))
    phone: Mapped[str | None] = mapped_column(String(20))
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SocialIdentityOrm(Base):
    __tablename__ = "social_identities"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_identities_provider_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    provider: Mapped[str] = mapped_column(String(10))
    provider_user_id: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    provider_refresh_token_enc: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

`backend/apps/auth/adapter/outbound/mappers/user_mapper.py`:
```python
from __future__ import annotations

from auth.adapter.outbound.orm.user_orm import SocialIdentityOrm, UserOrm
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider


def to_user(orm: UserOrm) -> User:
    return User(
        id=orm.id,
        display_name=orm.display_name,
        profile_image_url=orm.profile_image_url,
        phone=orm.phone,
        suspended_at=orm.suspended_at,
        deleted_at=orm.deleted_at,
    )


def to_identity(orm: SocialIdentityOrm) -> SocialIdentity:
    return SocialIdentity(
        id=orm.id,
        user_id=orm.user_id,
        provider=Provider(orm.provider),
        provider_user_id=orm.provider_user_id,
        email=orm.email,
    )
```

`backend/apps/auth/adapter/outbound/gateways/fernet_cipher.py`:
```python
from __future__ import annotations

from cryptography.fernet import Fernet


class FernetCipher:
    """제공자 리프레시 토큰을 DB 에 넣기 전에 암호화한다. 키는 IDENTITY_TOKEN_ENC_KEY."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(key.encode())

    def encrypt(self, plain: str) -> str:
        return self._fernet.encrypt(plain.encode()).decode()
```

`backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.mappers.user_mapper import to_identity, to_user
from auth.adapter.outbound.orm.user_orm import SocialIdentityOrm, UserOrm
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


class UserPgRepository(UserRepository):
    def __init__(self, session: AsyncSession, cipher: FernetCipher) -> None:
        self._session = session
        self._cipher = cipher

    async def find_by_identity(self, provider: Provider, provider_user_id: str) -> User | None:
        stmt = (
            select(UserOrm)
            .join(SocialIdentityOrm, SocialIdentityOrm.user_id == UserOrm.id)
            .where(
                SocialIdentityOrm.provider == provider.value,
                SocialIdentityOrm.provider_user_id == provider_user_id,
            )
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_user(row) if row else None

    async def create_with_identity(self, profile: SocialProfile) -> User:
        user = UserOrm(
            display_name=profile.display_name or "이름 없음",
            profile_image_url=profile.profile_image_url,
        )
        self._session.add(user)
        await self._session.flush()
        token = profile.provider_refresh_token
        self._session.add(
            SocialIdentityOrm(
                user_id=user.id,
                provider=profile.provider.value,
                provider_user_id=profile.provider_user_id,
                email=profile.email,
                provider_refresh_token_enc=self._cipher.encrypt(token) if token else None,
            )
        )
        await self._session.flush()
        return to_user(user)

    async def get(self, user_id: int) -> User | None:
        row = await self._session.get(UserOrm, user_id)
        return to_user(row) if row else None

    async def list_identities(self, user_id: int) -> list[SocialIdentity]:
        stmt = (
            select(SocialIdentityOrm)
            .where(SocialIdentityOrm.user_id == user_id)
            .order_by(SocialIdentityOrm.id)
        )
        return [to_identity(r) for r in (await self._session.execute(stmt)).scalars()]
```

- [ ] **Step 7: 통합 테스트가 통과하는지 확인한다**

Run: `cd infra && docker compose run --rm backend pytest apps/auth/tests/adapter/test_user_pg_repository.py -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 8: Alembic 설정과 첫 마이그레이션을 쓴다**

`backend/alembic.ini`:
```ini
[alembic]
script_location = alembic
prepend_sys_path = .
```

`backend/alembic/env.py`:
```python
"""Alembic 환경 — 비동기 엔진으로 마이그레이션을 실행한다. 오프라인 모드는 쓰지 않는다."""
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import auth.adapter.outbound.orm.user_orm  # noqa: F401 — 메타데이터 등록
from core.config import DATABASE_URL
from core.database import Base

target_metadata = Base.metadata


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_async())
```

`backend/alembic/script.py.mako`:
```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

`backend/alembic/versions/0001_users_and_social_identities.py`:
```python
"""유저와 소셜 신원

Revision ID: 0001
Revises:
Create Date: 2026-09-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("display_name", sa.String(50), nullable=False),
        sa.Column("profile_image_url", sa.String(500)),
        sa.Column("phone", sa.String(20)),
        sa.Column("suspended_at", sa.DateTime(timezone=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "social_identities",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("provider", sa.String(10), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.Column("provider_refresh_token_enc", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_social_identities_provider_user"),
    )
    op.create_index("ix_social_identities_user_id", "social_identities", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_social_identities_user_id", table_name="social_identities")
    op.drop_table("social_identities")
    op.drop_table("users")
```

- [ ] **Step 9: backend가 기동할 때 마이그레이션을 돌리게 한다**

`infra/docker-compose.yml`의 `backend` 서비스에서 `command` 줄을 아래로 바꾼다:
```yaml
    command: sh -c "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
```

Run:
```bash
cd infra && docker compose up -d backend && sleep 6
docker compose exec pgvector psql -U chagoc -d chagocnote -c "\dt"
```
Expected: 표에 `alembic_version`, `social_identities`, `users`가 보인다.

- [ ] **Step 10: 구조 계약을 확인하고 커밋한다 (허용된 경우)**

Run: `cd infra && docker compose run --rm --no-deps backend lint-imports --config .importlinter`
Expected: `Contracts: 4 kept, 0 broken.`

```bash
git add backend infra/docker-compose.yml
git commit -m "feat(auth): 유저·소셜 신원 영속 계층과 첫 마이그레이션"
```

---

### Task 5: 토큰 발급·검증과 리프레시 저장소

**Files:**
- Create: `backend/apps/auth/app/dtos/token_dto.py`
- Create: `backend/apps/auth/domain/value_objects/refresh_lookup.py`
- Create: `backend/apps/auth/domain/services/refresh_token_factory.py`
- Create: `backend/apps/auth/app/ports/output/token_issuer_port.py`, `refresh_token_store_port.py`
- Create: `backend/apps/auth/app/services/session_issuer.py`
- Create: `backend/apps/auth/adapter/outbound/gateways/jwt_token_issuer.py`
- Create: `backend/apps/auth/adapter/outbound/redis/refresh_token_redis_store.py`
- Create: `backend/core/http_errors.py`, `backend/core/security.py`
- Create: `backend/apps/auth/tests/helpers/keys.py`
- Test: `backend/apps/auth/tests/adapter/test_jwt_token_issuer.py`, `test_refresh_token_redis_store.py`, `backend/apps/auth/tests/app/test_session_issuer.py`, `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `core.config`(`JWT_PUBLIC_KEY`, `REDIS_URL`, TTL 상수), `core.database.get_db`, Task 4의 `users` 테이블과 `db_session` 픽스처
- Produces:
  - `auth.app.dtos.token_dto.AccessToken(token: str, expires_in: int)`, `TokenPair(access_token: str, refresh_token: str, expires_in: int)` — frozen dataclass
  - `auth.domain.value_objects.refresh_lookup.RefreshStatus`(Enum: `ACTIVE`, `USED`, `MISSING`), `RefreshLookup(status: RefreshStatus, user_id: int | None)`
  - `auth.domain.services.refresh_token_factory.new_refresh_token() -> str`
  - `TokenIssuerPort.issue_access(user_id: int) -> AccessToken` (동기 `def`)
  - `RefreshTokenStorePort` — `async save(token: str, user_id: int) -> None`, `async take(token: str) -> RefreshLookup`, `async revoke(token: str) -> None`, `async revoke_all(user_id: int) -> None`
  - `auth.app.services.session_issuer.SessionIssuer(token_issuer, refresh_store)` — `async issue(user_id: int) -> TokenPair`
  - `JwtTokenIssuer(private_key: str, ttl_seconds: int, now: Callable[[], datetime] = ...)`
  - `RefreshTokenRedisStore(redis: Redis, ttl_seconds: int)`
  - `core.http_errors.ApiError(status_code: int, code: str, message: str)`, `install_error_handlers(app: FastAPI, domain_errors: dict[type[Exception], int]) -> None`
  - `core.security.decode_access_token(token: str, public_key: str) -> int`(실패 시 `InvalidAccessToken`), `get_current_user_id`(FastAPI 의존성, `int` 반환)
  - 테스트 도우미 `auth.tests.helpers.keys.make_rsa_keypair(kid: str = "test-kid") -> tuple[str, str, dict]`(개인키 PEM, 공개키 PEM, 공개 JWK), `make_ec_private_pem() -> str`

- [ ] **Step 1: 테스트용 키 도우미를 쓴다**

`backend/apps/auth/tests/helpers/keys.py`:
```python
"""테스트에서 쓰는 임시 키. 실제 키를 저장소에 두지 않으려고 매번 새로 만든다."""
from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa


def _b64u(number: int) -> str:
    raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_rsa_keypair(kid: str = "test-kid") -> tuple[str, str, dict]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    numbers = key.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": kid, "alg": "RS256", "use": "sig",
           "n": _b64u(numbers.n), "e": _b64u(numbers.e)}
    return private_pem, public_pem, jwk


def make_ec_private_pem() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
```

- [ ] **Step 2: 발급기와 검증의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_jwt_token_issuer.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.tests.helpers.keys import make_rsa_keypair
from core.security import InvalidAccessToken, decode_access_token


def test_발급한_액세스_토큰은_공개키로_검증되고_유저_ID를_돌려준다():
    private_pem, public_pem, _ = make_rsa_keypair()
    access = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42)
    assert access.expires_in == 900
    assert decode_access_token(access.token, public_pem) == 42


def test_토큰에는_역할과_권한이_들어가지_않는다():
    private_pem, _, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42).token
    assert set(jwt.get_unverified_claims(token)) == {"sub", "jti", "typ", "iat", "exp"}


def test_만료된_토큰은_거절한다():
    private_pem, public_pem, _ = make_rsa_keypair()
    past = lambda: datetime.now(timezone.utc) - timedelta(hours=1)
    token = JwtTokenIssuer(private_pem, ttl_seconds=60, now=past).issue_access(42).token
    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, public_pem)


def test_다른_키로_서명한_토큰은_거절한다():
    private_pem, _, _ = make_rsa_keypair()
    _, other_public_pem, _ = make_rsa_keypair()
    token = JwtTokenIssuer(private_pem, ttl_seconds=900).issue_access(42).token
    with pytest.raises(InvalidAccessToken):
        decode_access_token(token, other_public_pem)


def test_액세스_토큰이_아닌_토큰은_거절한다():
    private_pem, public_pem, _ = make_rsa_keypair()
    forged = jwt.encode({"sub": "42", "typ": "other"}, private_pem, algorithm="RS256")
    with pytest.raises(InvalidAccessToken):
        decode_access_token(forged, public_pem)
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_jwt_token_issuer.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.outbound.gateways.jwt_token_issuer'`

- [ ] **Step 3: DTO·포트·발급기·오류 형식·검증을 구현한다**

`backend/apps/auth/app/dtos/token_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AccessToken:
    token: str
    expires_in: int


@dataclass(frozen=True)
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int
```

`backend/apps/auth/app/ports/output/token_issuer_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.token_dto import AccessToken


class TokenIssuerPort(ABC):
    @abstractmethod
    def issue_access(self, user_id: int) -> AccessToken: ...
```

`backend/apps/auth/adapter/outbound/gateways/jwt_token_issuer.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from jose import jwt

from auth.app.dtos.token_dto import AccessToken
from auth.app.ports.output.token_issuer_port import TokenIssuerPort


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JwtTokenIssuer(TokenIssuerPort):
    """RS256 액세스 토큰 발급. 유저 ID만 담는다 — 역할과 권한은 매 요청 DB 에서 조회한다."""

    def __init__(
        self, private_key: str, ttl_seconds: int, now: Callable[[], datetime] = _utcnow
    ) -> None:
        self._private_key = private_key
        self._ttl_seconds = ttl_seconds
        self._now = now

    def issue_access(self, user_id: int) -> AccessToken:
        issued_at = self._now()
        claims = {
            "sub": str(user_id),
            "jti": uuid4().hex,
            "typ": "access",
            "iat": int(issued_at.timestamp()),
            "exp": int((issued_at + timedelta(seconds=self._ttl_seconds)).timestamp()),
        }
        return AccessToken(
            token=jwt.encode(claims, self._private_key, algorithm="RS256"),
            expires_in=self._ttl_seconds,
        )
```

`backend/core/http_errors.py`:
```python
"""오류 응답을 {"code", "message"} 한 가지 형식으로 통일한다."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def install_error_handlers(app: FastAPI, domain_errors: dict[type[Exception], int]) -> None:
    """ApiError 와 스포크의 도메인 오류를 같은 형식의 응답으로 바꾼다.

    domain_errors 는 {도메인 예외 클래스: HTTP 상태 코드}. 예외는 code 속성을 가져야 한다.
    """

    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )

    def _make(status_code: int):
        async def _handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(
                status_code=status_code,
                content={"code": getattr(exc, "code"), "message": str(exc)},
            )

        return _handler

    for exc_type, status_code in domain_errors.items():
        app.add_exception_handler(exc_type, _make(status_code))
```

`backend/core/security.py`:
```python
"""액세스 토큰 검증 — 모든 라우터가 쓰는 인증 가드.

발급은 auth 스포크 몫이고 여기는 서명 검증과 계정 상태 확인만 한다.
스포크가 auth 를 import 하면 허브-스포크 위반이라 순수 인프라(core)에 둔다.
users 를 원시 SQL 로 조회하는 이유는 core 가 스포크의 ORM 을 import 할 수 없어서다.
"""
from __future__ import annotations

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import JWT_PUBLIC_KEY
from core.database import get_db
from core.http_errors import ApiError

_bearer = HTTPBearer(auto_error=False)


class InvalidAccessToken(Exception):
    pass


def decode_access_token(token: str, public_key: str) -> int:
    try:
        # 허용 알고리즘은 RS256 리터럴로 고정한다 (알고리즘 혼동 공격 방지).
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        if payload.get("typ") != "access":
            raise ValueError("typ")
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise InvalidAccessToken() from exc


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> int:
    """서명 검증 + 계정 상태 확인. 정지·탈퇴는 이미 발급된 토큰도 즉시 막는다."""
    if credentials is None:
        raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다.")
    try:
        user_id = decode_access_token(credentials.credentials, JWT_PUBLIC_KEY)
    except InvalidAccessToken:
        raise ApiError(401, "UNAUTHENTICATED", "토큰이 유효하지 않습니다.")
    row = (
        await db.execute(
            text("SELECT suspended_at, deleted_at FROM users WHERE id = :uid"), {"uid": user_id}
        )
    ).first()
    if row is None or row[1] is not None:
        raise ApiError(401, "UNAUTHENTICATED", "유효하지 않은 계정입니다.")
    if row[0] is not None:
        raise ApiError(403, "ACCOUNT_SUSPENDED", "정지된 계정입니다.")
    return user_id
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_jwt_token_issuer.py -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 4: 인증 가드의 통합 테스트를 쓰고 통과시킨다**

`backend/tests/test_security.py`:
```python
from datetime import datetime, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text

import core.security as security
from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.tests.helpers.keys import make_rsa_keypair
from core.http_errors import ApiError

pytestmark = pytest.mark.integration


async def _insert_user(session, **columns):
    await session.execute(
        text(
            "INSERT INTO users (id, display_name, suspended_at, deleted_at) "
            "VALUES (:id, '테스트', :suspended_at, :deleted_at)"
        ),
        {"suspended_at": None, "deleted_at": None, **columns},
    )


def _bearer(token):
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.fixture
def issuer(monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    return JwtTokenIssuer(private_pem, ttl_seconds=900)


async def test_정상_계정은_유저_ID를_돌려준다(db_session, issuer):
    await _insert_user(db_session, id=1)
    token = issuer.issue_access(1).token
    assert await security.get_current_user_id(_bearer(token), db_session) == 1


async def test_토큰이_없으면_401이다(db_session, issuer):
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(None, db_session)
    assert (exc.value.status_code, exc.value.code) == (401, "UNAUTHENTICATED")


async def test_정지된_계정은_이미_발급된_토큰으로도_403이다(db_session, issuer):
    await _insert_user(db_session, id=2, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(_bearer(issuer.issue_access(2).token), db_session)
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_401이다(db_session, issuer):
    await _insert_user(db_session, id=3, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await security.get_current_user_id(_bearer(issuer.issue_access(3).token), db_session)
    assert exc.value.status_code == 401
```

Run: `cd infra && docker compose run --rm backend pytest tests/test_security.py -q -p no:cacheprovider`
Expected: `4 passed`

- [ ] **Step 5: 리프레시 저장소의 실패하는 통합 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_refresh_token_redis_store.py`:
```python
import pytest
from redis.asyncio import from_url

from auth.adapter.outbound.redis.refresh_token_redis_store import RefreshTokenRedisStore
from auth.domain.value_objects.refresh_lookup import RefreshStatus
from core.config import REDIS_URL

pytestmark = pytest.mark.integration


@pytest.fixture
async def store():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    redis = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await redis.flushdb()
    yield RefreshTokenRedisStore(redis, ttl_seconds=60)
    await redis.flushdb()
    await redis.aclose()


async def test_저장한_토큰은_한_번만_꺼낼_수_있다(store):
    await store.save("token-a", user_id=7)
    first = await store.take("token-a")
    assert (first.status, first.user_id) == (RefreshStatus.ACTIVE, 7)
    second = await store.take("token-a")
    assert (second.status, second.user_id) == (RefreshStatus.USED, 7)


async def test_모르는_토큰은_MISSING_이다(store):
    lookup = await store.take("never-issued")
    assert (lookup.status, lookup.user_id) == (RefreshStatus.MISSING, None)


async def test_폐기한_토큰은_MISSING_이다(store):
    await store.save("token-b", user_id=7)
    await store.revoke("token-b")
    assert (await store.take("token-b")).status is RefreshStatus.MISSING


async def test_유저의_모든_세션을_폐기한다(store):
    await store.save("token-c", user_id=7)
    await store.save("token-d", user_id=7)
    await store.save("token-e", user_id=8)
    await store.revoke_all(7)
    assert (await store.take("token-c")).status is RefreshStatus.MISSING
    assert (await store.take("token-d")).status is RefreshStatus.MISSING
    assert (await store.take("token-e")).status is RefreshStatus.ACTIVE


async def test_토큰_원문은_Redis_키에_남지_않는다(store):
    await store.save("plain-token-value", user_id=7)
    keys = [k async for k in store._redis.scan_iter("*")]
    assert keys and all("plain-token-value" not in k for k in keys)
```

Run: `cd infra && docker compose run --rm backend pytest apps/auth/tests/adapter/test_refresh_token_redis_store.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.outbound.redis.refresh_token_redis_store'`

- [ ] **Step 6: 조회 결과 VO·포트·Redis 저장소를 구현한다**

`backend/apps/auth/domain/value_objects/refresh_lookup.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RefreshStatus(Enum):
    ACTIVE = "active"    # 유효하고 아직 쓰지 않았다
    USED = "used"        # 이미 새 토큰으로 바뀌었다 — 다시 오면 탈취 신호
    MISSING = "missing"  # 모르는 토큰이거나 만료·폐기되었다


@dataclass(frozen=True)
class RefreshLookup:
    status: RefreshStatus
    user_id: int | None
```

`backend/apps/auth/app/ports/output/refresh_token_store_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.refresh_lookup import RefreshLookup


class RefreshTokenStorePort(ABC):
    @abstractmethod
    async def save(self, token: str, user_id: int) -> None: ...

    @abstractmethod
    async def take(self, token: str) -> RefreshLookup:
        """토큰을 꺼내면서 '사용됨'으로 바꾼다. 같은 토큰은 한 번만 ACTIVE 로 나온다."""

    @abstractmethod
    async def revoke(self, token: str) -> None: ...

    @abstractmethod
    async def revoke_all(self, user_id: int) -> None: ...
```

`backend/apps/auth/adapter/outbound/redis/refresh_token_redis_store.py`:
```python
from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRedisStore(RefreshTokenStorePort):
    """키 구성
    auth:refresh:{해시}        → user_id   (유효한 토큰)
    auth:refresh:used:{해시}   → user_id   (이미 쓴 토큰의 흔적 — 재사용 감지용)
    auth:refresh:user:{id}     → 해시 집합 (유저의 모든 세션 폐기용)
    토큰 원문은 저장하지 않는다.
    """

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def save(self, token: str, user_id: int) -> None:
        digest = _digest(token)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(f"auth:refresh:{digest}", user_id, ex=self._ttl)
            pipe.sadd(f"auth:refresh:user:{user_id}", digest)
            pipe.expire(f"auth:refresh:user:{user_id}", self._ttl)
            await pipe.execute()

    async def take(self, token: str) -> RefreshLookup:
        digest = _digest(token)
        value = await self._redis.getdel(f"auth:refresh:{digest}")
        if value is not None:
            user_id = int(value)
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.set(f"auth:refresh:used:{digest}", user_id, ex=self._ttl)
                pipe.srem(f"auth:refresh:user:{user_id}", digest)
                await pipe.execute()
            return RefreshLookup(RefreshStatus.ACTIVE, user_id)
        used = await self._redis.get(f"auth:refresh:used:{digest}")
        if used is not None:
            return RefreshLookup(RefreshStatus.USED, int(used))
        return RefreshLookup(RefreshStatus.MISSING, None)

    async def revoke(self, token: str) -> None:
        digest = _digest(token)
        value = await self._redis.getdel(f"auth:refresh:{digest}")
        if value is not None:
            await self._redis.srem(f"auth:refresh:user:{int(value)}", digest)

    async def revoke_all(self, user_id: int) -> None:
        digests = await self._redis.smembers(f"auth:refresh:user:{user_id}")
        keys = [f"auth:refresh:{d}" for d in digests] + [f"auth:refresh:user:{user_id}"]
        await self._redis.delete(*keys)
```

Run: `cd infra && docker compose run --rm backend pytest apps/auth/tests/adapter/test_refresh_token_redis_store.py -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 7: 세션 발급기의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/test_session_issuer.py`:
```python
from auth.app.dtos.token_dto import AccessToken
from auth.app.services.session_issuer import SessionIssuer


class _StubIssuer:
    def issue_access(self, user_id):
        return AccessToken(token=f"access-for-{user_id}", expires_in=900)


class _StubStore:
    def __init__(self):
        self.saved = []

    async def save(self, token, user_id):
        self.saved.append((token, user_id))


async def test_액세스_토큰과_새_리프레시_토큰을_함께_발급하고_리프레시를_저장한다():
    store = _StubStore()
    pair = await SessionIssuer(_StubIssuer(), store).issue(5)
    assert pair.access_token == "access-for-5"
    assert pair.expires_in == 900
    assert store.saved == [(pair.refresh_token, 5)]
    assert len(pair.refresh_token) >= 43


async def test_리프레시_토큰은_매번_다르다():
    issuer = SessionIssuer(_StubIssuer(), _StubStore())
    assert (await issuer.issue(5)).refresh_token != (await issuer.issue(5)).refresh_token
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/test_session_issuer.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.services.session_issuer'`

- [ ] **Step 8: 리프레시 토큰 생성과 세션 발급기를 구현한다**

`backend/apps/auth/domain/services/refresh_token_factory.py`:
```python
import secrets


def new_refresh_token() -> str:
    """추측할 수 없는 불투명 문자열. JWT 가 아니다 — 서버 저장소에 있어야만 유효하다."""
    return secrets.token_urlsafe(48)
```

`backend/apps/auth/app/services/session_issuer.py`:
```python
from __future__ import annotations

from auth.app.dtos.token_dto import TokenPair
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.token_issuer_port import TokenIssuerPort
from auth.domain.services.refresh_token_factory import new_refresh_token


class SessionIssuer:
    """로그인과 토큰 갱신이 함께 쓰는 발급 절차."""

    def __init__(self, token_issuer: TokenIssuerPort, refresh_store: RefreshTokenStorePort) -> None:
        self._token_issuer = token_issuer
        self._refresh_store = refresh_store

    async def issue(self, user_id: int) -> TokenPair:
        access = self._token_issuer.issue_access(user_id)
        refresh = new_refresh_token()
        await self._refresh_store.save(refresh, user_id)
        return TokenPair(
            access_token=access.token, refresh_token=refresh, expires_in=access.expires_in
        )
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/test_session_issuer.py -q -p no:cacheprovider`
Expected: `2 passed`

- [ ] **Step 9: 전체 테스트와 구조 계약을 확인하고 커밋한다 (허용된 경우)**

Run:
```bash
cd infra
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 실패 0건, `Contracts: 4 kept, 0 broken.`

```bash
git add backend
git commit -m "feat(auth): 액세스 토큰 발급·검증과 리프레시 토큰 저장소"
```

---

### Task 6: 소셜 제공자 전략과 팩토리

**Files:**
- Create: `backend/apps/auth/domain/errors.py`
- Create: `backend/apps/auth/domain/value_objects/social_credentials.py`
- Create: `backend/apps/auth/app/ports/output/social_provider_port.py`, `social_provider_resolver_port.py`
- Create: `backend/apps/auth/adapter/outbound/strategy/dev_identity_strategy.py`, `kakao_identity_strategy.py`, `google_identity_strategy.py`, `apple_identity_strategy.py`, `jwks_verifier.py`
- Create: `backend/apps/auth/adapter/outbound/factory/social_provider_factory.py`
- Test: `backend/apps/auth/tests/adapter/test_dev_identity_strategy.py`, `test_kakao_identity_strategy.py`, `test_google_identity_strategy.py`, `test_apple_identity_strategy.py`, `test_social_provider_factory.py`

**Interfaces:**
- Consumes: Task 4의 `Provider`, `SocialProfile`. Task 5의 `make_rsa_keypair`, `make_ec_private_pem`
- Produces:
  - `auth.domain.errors`: `AuthError(Exception)`(클래스 속성 `code: str`), `UnsupportedProviderError`(`PROVIDER_NOT_SUPPORTED`), `ProviderVerificationError`(`PROVIDER_VERIFICATION_FAILED`), `AccountSuspendedError`(`ACCOUNT_SUSPENDED`), `InvalidRefreshTokenError`(`UNAUTHENTICATED`), `RefreshTokenReuseError`(`UNAUTHENTICATED`)
  - `auth.domain.value_objects.social_credentials.SocialCredentials(token: str, authorization_code: str | None = None, nonce: str | None = None, display_name: str | None = None)`
  - `SocialProviderPort.verify(credentials: SocialCredentials) -> SocialProfile` (async)
  - `SocialProviderResolverPort.resolve(provider: Provider) -> SocialProviderPort` (동기)
  - `auth.adapter.outbound.strategy.jwks_verifier`: `async verify_with_jwks(token, fetch_jwks, issuers: tuple[str, ...], audiences: tuple[str, ...]) -> dict`, `http_jwks_fetcher(http: httpx.AsyncClient, url: str, ttl_seconds: int = 3600) -> Callable[[], Awaitable[dict]]`
  - `DevIdentityStrategy()`, `KakaoIdentityStrategy(app_id: str, http)`, `GoogleIdentityStrategy(client_ids: tuple[str, ...], fetch_jwks)`, `AppleIdentityStrategy(bundle_id, team_id, key_id, private_key_pem, http, fetch_jwks, now=time.time)`
  - `auth.adapter.outbound.factory.social_provider_factory`: `SocialProviderFactory(strategies: dict[Provider, SocialProviderPort])`, `AppleSettings(bundle_id, team_id, key_id, private_key_pem)`, `build_social_provider_factory(*, app_env: str, kakao_app_id: str, google_client_ids: tuple[str, ...], apple: AppleSettings | None, http: httpx.AsyncClient) -> SocialProviderFactory`

- [ ] **Step 1: 도메인 오류·자격 증명 VO·포트를 쓴다**

`backend/apps/auth/domain/errors.py`:
```python
class AuthError(Exception):
    """auth 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "AUTH_ERROR"


class UnsupportedProviderError(AuthError):
    code = "PROVIDER_NOT_SUPPORTED"


class ProviderVerificationError(AuthError):
    code = "PROVIDER_VERIFICATION_FAILED"


class AccountSuspendedError(AuthError):
    code = "ACCOUNT_SUSPENDED"


class InvalidRefreshTokenError(AuthError):
    code = "UNAUTHENTICATED"


class RefreshTokenReuseError(AuthError):
    code = "UNAUTHENTICATED"
```

`backend/apps/auth/domain/value_objects/social_credentials.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SocialCredentials:
    """앱이 제공자 SDK 에서 받아 서버로 넘긴 값. 서버는 이것을 제공자에게 직접 확인한다."""

    token: str
    authorization_code: str | None = None  # Apple 전용 — 리프레시 토큰으로 교환한다
    nonce: str | None = None               # Apple 전용 — 앱이 만든 원본 nonce
    display_name: str | None = None        # Apple 은 첫 로그인 때만 이름을 앱에 준다
```

`backend/apps/auth/app/ports/output/social_provider_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile


class SocialProviderPort(ABC):
    @abstractmethod
    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        """제공자에게 직접 확인한 신원을 돌려준다. 확인할 수 없으면 ProviderVerificationError."""
```

`backend/apps/auth/app/ports/output/social_provider_resolver_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.value_objects.provider import Provider


class SocialProviderResolverPort(ABC):
    @abstractmethod
    def resolve(self, provider: Provider) -> SocialProviderPort:
        """등록되지 않은 제공자면 UnsupportedProviderError."""
```

- [ ] **Step 2: 개발용·카카오 전략의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_dev_identity_strategy.py`:
```python
import pytest

from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


async def test_입력한_이름이_곧_신원이다():
    profile = await DevIdentityStrategy().verify(SocialCredentials(token=" Owner "))
    assert profile.provider is Provider.DEV
    assert profile.provider_user_id == "owner"
    assert profile.display_name == "Owner"


async def test_이름이_비어_있으면_거절한다():
    with pytest.raises(ProviderVerificationError):
        await DevIdentityStrategy().verify(SocialCredentials(token="   "))
```

`backend/apps/auth/tests/adapter/test_kakao_identity_strategy.py`:
```python
import httpx
import pytest

from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


def _http(app_id=1234, me_status=200):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer kakao-token"
        if request.url.path == "/v1/user/access_token_info":
            return httpx.Response(200, json={"id": 99, "app_id": app_id})
        if request.url.path == "/v2/user/me":
            return httpx.Response(me_status, json={
                "id": 99,
                "kakao_account": {
                    "email": "a@example.com",
                    "profile": {"nickname": "두부 보호자", "profile_image_url": "https://img/1.jpg"},
                },
            })
        return httpx.Response(404)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_카카오가_확인해_준_프로필을_돌려준다():
    profile = await KakaoIdentityStrategy("1234", _http()).verify(SocialCredentials(token="kakao-token"))
    assert profile.provider is Provider.KAKAO
    assert profile.provider_user_id == "99"
    assert profile.display_name == "두부 보호자"
    assert profile.email == "a@example.com"
    assert profile.provider_refresh_token is None


async def test_다른_앱에서_발급된_토큰은_거절한다():
    with pytest.raises(ProviderVerificationError):
        await KakaoIdentityStrategy("1234", _http(app_id=5678)).verify(SocialCredentials(token="kakao-token"))


async def test_카카오가_사용자_조회를_거절하면_실패한다():
    with pytest.raises(ProviderVerificationError):
        await KakaoIdentityStrategy("1234", _http(me_status=401)).verify(SocialCredentials(token="kakao-token"))
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_dev_identity_strategy.py apps/auth/tests/adapter/test_kakao_identity_strategy.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: 개발용·카카오 전략을 구현한다**

`backend/apps/auth/adapter/outbound/strategy/dev_identity_strategy.py`:
```python
from __future__ import annotations

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile


class DevIdentityStrategy(SocialProviderPort):
    """개발 환경 전용 — 입력한 이름으로 바로 로그인된다. 팩토리가 APP_ENV=dev 일 때만 등록한다."""

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        name = credentials.token.strip()
        if not name:
            raise ProviderVerificationError("개발용 로그인에는 이름이 필요합니다.")
        return SocialProfile(
            provider=Provider.DEV,
            provider_user_id=name.lower(),
            email=None,
            display_name=name,
            profile_image_url=None,
            provider_refresh_token=None,
        )
```

`backend/apps/auth/adapter/outbound/strategy/kakao_identity_strategy.py`:
```python
from __future__ import annotations

import httpx

from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

_TOKEN_INFO_URL = "https://kapi.kakao.com/v1/user/access_token_info"
_ME_URL = "https://kapi.kakao.com/v2/user/me"


class KakaoIdentityStrategy(SocialProviderPort):
    """카카오 액세스 토큰을 카카오에 직접 확인한다.

    토큰이 우리 앱에서 발급된 것인지(app_id) 먼저 본다. 이 확인이 없으면
    다른 서비스에서 받은 카카오 토큰으로 우리 서비스에 로그인할 수 있다.
    """

    def __init__(self, app_id: str, http: httpx.AsyncClient) -> None:
        self._app_id = app_id
        self._http = http

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        headers = {"Authorization": f"Bearer {credentials.token}"}
        info = await self._http.get(_TOKEN_INFO_URL, headers=headers)
        if info.status_code != 200 or str(info.json().get("app_id")) != self._app_id:
            raise ProviderVerificationError("카카오 토큰을 확인할 수 없습니다.")
        me = await self._http.get(_ME_URL, headers=headers)
        if me.status_code != 200:
            raise ProviderVerificationError("카카오 사용자 정보를 가져올 수 없습니다.")
        body = me.json()
        account = body.get("kakao_account") or {}
        profile = account.get("profile") or {}
        return SocialProfile(
            provider=Provider.KAKAO,
            provider_user_id=str(body["id"]),
            email=account.get("email"),
            display_name=profile.get("nickname"),
            profile_image_url=profile.get("profile_image_url"),
            provider_refresh_token=None,
        )
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_dev_identity_strategy.py apps/auth/tests/adapter/test_kakao_identity_strategy.py -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 4: 구글·Apple 전략의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_google_identity_strategy.py`:
```python
import time

import pytest
from jose import jwt

from auth.adapter.outbound.strategy.google_identity_strategy import GoogleIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.tests.helpers.keys import make_rsa_keypair

PRIVATE_PEM, _, JWK = make_rsa_keypair(kid="google-kid")


async def _jwks():
    return {"keys": [JWK]}


def _id_token(**overrides):
    claims = {
        "iss": "https://accounts.google.com", "aud": "ios-client-id", "sub": "google-7",
        "email": "a@example.com", "name": "두부 보호자", "picture": "https://img/g.jpg",
        "exp": int(time.time()) + 600, **overrides,
    }
    return jwt.encode(claims, PRIVATE_PEM, algorithm="RS256", headers={"kid": "google-kid"})


def _strategy():
    return GoogleIdentityStrategy(("ios-client-id", "android-client-id"), _jwks)


async def test_서명과_대상_앱이_맞으면_프로필을_돌려준다():
    profile = await _strategy().verify(SocialCredentials(token=_id_token()))
    assert profile.provider is Provider.GOOGLE
    assert profile.provider_user_id == "google-7"
    assert profile.display_name == "두부 보호자"
    assert profile.profile_image_url == "https://img/g.jpg"


async def test_안드로이드_클라이언트_ID_도_받아들인다():
    profile = await _strategy().verify(SocialCredentials(token=_id_token(aud="android-client-id")))
    assert profile.provider_user_id == "google-7"


async def test_다른_앱을_대상으로_한_토큰은_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(aud="someone-else")))


async def test_발급자가_구글이_아니면_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(iss="https://evil.example")))


async def test_다른_키로_서명한_토큰은_거절한다():
    other_private, _, _ = make_rsa_keypair(kid="google-kid")
    forged = jwt.encode(
        {"iss": "https://accounts.google.com", "aud": "ios-client-id", "sub": "x",
         "exp": int(time.time()) + 600},
        other_private, algorithm="RS256", headers={"kid": "google-kid"},
    )
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=forged))
```

`backend/apps/auth/tests/adapter/test_apple_identity_strategy.py`:
```python
import hashlib
import time

import httpx
import pytest
from jose import jwt

from auth.adapter.outbound.strategy.apple_identity_strategy import AppleIdentityStrategy
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.tests.helpers.keys import make_ec_private_pem, make_rsa_keypair

APPLE_PRIVATE_PEM, _, APPLE_JWK = make_rsa_keypair(kid="apple-kid")
RAW_NONCE = "raw-nonce-from-app"


async def _jwks():
    return {"keys": [APPLE_JWK]}


def _id_token(**overrides):
    claims = {
        "iss": "https://appleid.apple.com", "aud": "com.chagocnote.app", "sub": "apple-1",
        "email": "relay@privaterelay.appleid.com",
        "nonce": hashlib.sha256(RAW_NONCE.encode()).hexdigest(),
        "exp": int(time.time()) + 600, **overrides,
    }
    return jwt.encode(claims, APPLE_PRIVATE_PEM, algorithm="RS256", headers={"kid": "apple-kid"})


def _strategy(exchange_status=200, seen=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(dict(httpx.QueryParams(request.content.decode())))
        return httpx.Response(exchange_status, json={"refresh_token": "apple-refresh"})

    return AppleIdentityStrategy(
        bundle_id="com.chagocnote.app", team_id="TEAM123456", key_id="KEY1234567",
        private_key_pem=make_ec_private_pem(),
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        fetch_jwks=_jwks,
    )


async def test_ID_토큰을_검증하고_인가_코드를_리프레시_토큰으로_바꾼다():
    seen = []
    profile = await _strategy(seen=seen).verify(SocialCredentials(
        token=_id_token(), authorization_code="auth-code", nonce=RAW_NONCE, display_name="두부 보호자",
    ))
    assert profile.provider is Provider.APPLE
    assert profile.provider_user_id == "apple-1"
    assert profile.display_name == "두부 보호자"
    assert profile.provider_refresh_token == "apple-refresh"
    assert seen[0]["code"] == "auth-code"
    assert seen[0]["client_id"] == "com.chagocnote.app"
    assert seen[0]["grant_type"] == "authorization_code"
    header = jwt.get_unverified_header(seen[0]["client_secret"])
    assert (header["alg"], header["kid"]) == ("ES256", "KEY1234567")


async def test_인가_코드가_없으면_교환하지_않는다():
    profile = await _strategy().verify(SocialCredentials(token=_id_token(), nonce=RAW_NONCE))
    assert profile.provider_refresh_token is None


async def test_nonce_가_다르면_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(), nonce="another-nonce"))


async def test_다른_앱을_대상으로_한_토큰은_거절한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=_id_token(aud="com.other.app"), nonce=RAW_NONCE))


async def test_코드_교환이_실패하면_로그인도_실패한다():
    with pytest.raises(ProviderVerificationError):
        await _strategy(exchange_status=400).verify(
            SocialCredentials(token=_id_token(), authorization_code="bad", nonce=RAW_NONCE)
        )
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_google_identity_strategy.py apps/auth/tests/adapter/test_apple_identity_strategy.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 5: 공개키 검증 도우미와 구글·Apple 전략을 구현한다**

`backend/apps/auth/adapter/outbound/strategy/jwks_verifier.py`:
```python
"""구글·Apple 전략이 함께 쓰는 ID 토큰 서명 검증."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import httpx
from jose import JWTError, jwt

from auth.domain.errors import ProviderVerificationError

JwksFetcher = Callable[[], Awaitable[dict]]


async def verify_with_jwks(
    token: str, fetch_jwks: JwksFetcher, issuers: tuple[str, ...], audiences: tuple[str, ...]
) -> dict:
    try:
        kid = jwt.get_unverified_header(token)["kid"]
        keys = (await fetch_jwks())["keys"]
        key = next(k for k in keys if k.get("kid") == kid)
        # 대상 앱(aud)은 여러 값 중 하나일 수 있어서 아래에서 직접 확인한다.
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            options={"verify_aud": False, "verify_at_hash": False},
        )
    except (JWTError, KeyError, StopIteration) as exc:
        raise ProviderVerificationError("ID 토큰의 서명을 확인할 수 없습니다.") from exc
    if claims.get("iss") not in issuers or claims.get("aud") not in audiences:
        raise ProviderVerificationError("발급자 또는 대상 앱이 일치하지 않습니다.")
    return claims


def http_jwks_fetcher(http: httpx.AsyncClient, url: str, ttl_seconds: int = 3600) -> JwksFetcher:
    """제공자의 공개키 목록을 가져온다. ttl_seconds 동안은 메모리에 둔 값을 쓴다."""
    cache: dict = {"at": 0.0, "value": None}

    async def _fetch() -> dict:
        if cache["value"] is None or time.monotonic() - cache["at"] > ttl_seconds:
            response = await http.get(url)
            response.raise_for_status()
            cache["value"], cache["at"] = response.json(), time.monotonic()
        return cache["value"]

    return _fetch
```

`backend/apps/auth/adapter/outbound/strategy/google_identity_strategy.py`:
```python
from __future__ import annotations

from auth.adapter.outbound.strategy.jwks_verifier import JwksFetcher, verify_with_jwks
from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
_ISSUERS = ("https://accounts.google.com", "accounts.google.com")


class GoogleIdentityStrategy(SocialProviderPort):
    def __init__(self, client_ids: tuple[str, ...], fetch_jwks: JwksFetcher) -> None:
        self._client_ids = client_ids
        self._fetch_jwks = fetch_jwks

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        claims = await verify_with_jwks(
            credentials.token, self._fetch_jwks, _ISSUERS, self._client_ids
        )
        return SocialProfile(
            provider=Provider.GOOGLE,
            provider_user_id=str(claims["sub"]),
            email=claims.get("email"),
            display_name=claims.get("name"),
            profile_image_url=claims.get("picture"),
            provider_refresh_token=None,
        )
```

`backend/apps/auth/adapter/outbound/strategy/apple_identity_strategy.py`:
```python
from __future__ import annotations

import hashlib
import time
from collections.abc import Callable

import httpx
from jose import jwt

from auth.adapter.outbound.strategy.jwks_verifier import JwksFetcher, verify_with_jwks
from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.domain.errors import ProviderVerificationError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials
from auth.domain.value_objects.social_profile import SocialProfile

APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
_ISSUER = "https://appleid.apple.com"
_TOKEN_URL = "https://appleid.apple.com/auth/token"


class AppleIdentityStrategy(SocialProviderPort):
    """Apple ID 토큰을 검증하고, 인가 코드를 Apple 리프레시 토큰으로 바꾼다.

    리프레시 토큰은 회원 탈퇴 때 Apple 쪽 연결을 끊는 데 쓴다 (App Store 요구 사항).
    """

    def __init__(
        self, bundle_id: str, team_id: str, key_id: str, private_key_pem: str,
        http: httpx.AsyncClient, fetch_jwks: JwksFetcher,
        now: Callable[[], float] = time.time,
    ) -> None:
        self._bundle_id = bundle_id
        self._team_id = team_id
        self._key_id = key_id
        self._private_key_pem = private_key_pem
        self._http = http
        self._fetch_jwks = fetch_jwks
        self._now = now

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        claims = await verify_with_jwks(
            credentials.token, self._fetch_jwks, (_ISSUER,), (self._bundle_id,)
        )
        expected = hashlib.sha256((credentials.nonce or "").encode()).hexdigest()
        if credentials.nonce is None or claims.get("nonce") != expected:
            raise ProviderVerificationError("Apple 로그인 요청을 확인할 수 없습니다.")
        refresh = None
        if credentials.authorization_code:
            refresh = await self._exchange(credentials.authorization_code)
        return SocialProfile(
            provider=Provider.APPLE,
            provider_user_id=str(claims["sub"]),
            email=claims.get("email"),
            display_name=credentials.display_name,
            profile_image_url=None,
            provider_refresh_token=refresh,
        )

    def _client_secret(self) -> str:
        issued_at = int(self._now())
        return jwt.encode(
            {"iss": self._team_id, "iat": issued_at, "exp": issued_at + 300,
             "aud": _ISSUER, "sub": self._bundle_id},
            self._private_key_pem, algorithm="ES256", headers={"kid": self._key_id},
        )

    async def _exchange(self, authorization_code: str) -> str | None:
        response = await self._http.post(_TOKEN_URL, data={
            "client_id": self._bundle_id,
            "client_secret": self._client_secret(),
            "code": authorization_code,
            "grant_type": "authorization_code",
        })
        if response.status_code != 200:
            raise ProviderVerificationError("Apple 인가 코드를 확인할 수 없습니다.")
        return response.json().get("refresh_token")
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_google_identity_strategy.py apps/auth/tests/adapter/test_apple_identity_strategy.py -q -p no:cacheprovider`
Expected: `10 passed`

- [ ] **Step 6: 팩토리의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_social_provider_factory.py`:
```python
import httpx
import pytest

from auth.adapter.outbound.factory.social_provider_factory import (
    AppleSettings,
    build_social_provider_factory,
)
from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.domain.errors import UnsupportedProviderError
from auth.domain.value_objects.provider import Provider
from auth.tests.helpers.keys import make_ec_private_pem


def _build(**overrides):
    base = dict(app_env="dev", kakao_app_id="", google_client_ids=(), apple=None,
                http=httpx.AsyncClient())
    return build_social_provider_factory(**{**base, **overrides})


def test_개발_환경에서는_dev_제공자가_등록된다():
    assert isinstance(_build(app_env="dev").resolve(Provider.DEV), DevIdentityStrategy)


def test_운영_환경에서는_dev_제공자가_등록되지_않는다():
    with pytest.raises(UnsupportedProviderError):
        _build(app_env="prod").resolve(Provider.DEV)


def test_설정값이_있는_제공자만_등록된다():
    factory = _build(kakao_app_id="1234")
    assert isinstance(factory.resolve(Provider.KAKAO), KakaoIdentityStrategy)
    with pytest.raises(UnsupportedProviderError):
        factory.resolve(Provider.GOOGLE)
    with pytest.raises(UnsupportedProviderError):
        factory.resolve(Provider.APPLE)


def test_Apple_설정이_모두_있으면_Apple_제공자가_등록된다():
    apple = AppleSettings("com.chagocnote.app", "TEAM123456", "KEY1234567", make_ec_private_pem())
    assert _build(apple=apple).resolve(Provider.APPLE) is not None
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_social_provider_factory.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 7: 팩토리를 구현한다**

`backend/apps/auth/adapter/outbound/factory/social_provider_factory.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

import httpx

from auth.adapter.outbound.strategy.apple_identity_strategy import (
    APPLE_JWKS_URL,
    AppleIdentityStrategy,
)
from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.adapter.outbound.strategy.google_identity_strategy import (
    GOOGLE_JWKS_URL,
    GoogleIdentityStrategy,
)
from auth.adapter.outbound.strategy.jwks_verifier import http_jwks_fetcher
from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.app.ports.output.social_provider_port import SocialProviderPort
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.domain.errors import UnsupportedProviderError
from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True)
class AppleSettings:
    bundle_id: str
    team_id: str
    key_id: str
    private_key_pem: str


class SocialProviderFactory(SocialProviderResolverPort):
    def __init__(self, strategies: dict[Provider, SocialProviderPort]) -> None:
        self._strategies = strategies

    def resolve(self, provider: Provider) -> SocialProviderPort:
        try:
            return self._strategies[provider]
        except KeyError:
            raise UnsupportedProviderError(f"{provider.value} 로그인은 지금 사용할 수 없습니다.")


def build_social_provider_factory(
    *, app_env: str, kakao_app_id: str, google_client_ids: tuple[str, ...],
    apple: AppleSettings | None, http: httpx.AsyncClient,
) -> SocialProviderFactory:
    """설정값이 있는 제공자만 등록한다. dev 제공자는 개발 환경에서만 등록한다."""
    strategies: dict[Provider, SocialProviderPort] = {}
    if app_env == "dev":
        strategies[Provider.DEV] = DevIdentityStrategy()
    if kakao_app_id:
        strategies[Provider.KAKAO] = KakaoIdentityStrategy(kakao_app_id, http)
    if google_client_ids:
        strategies[Provider.GOOGLE] = GoogleIdentityStrategy(
            google_client_ids, http_jwks_fetcher(http, GOOGLE_JWKS_URL)
        )
    if apple is not None:
        strategies[Provider.APPLE] = AppleIdentityStrategy(
            apple.bundle_id, apple.team_id, apple.key_id, apple.private_key_pem,
            http, http_jwks_fetcher(http, APPLE_JWKS_URL),
        )
    return SocialProviderFactory(strategies)
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_social_provider_factory.py -q -p no:cacheprovider`
Expected: `4 passed`

- [ ] **Step 8: 구조 계약을 확인하고 커밋한다 (허용된 경우)**

Run: `cd infra && docker compose run --rm --no-deps backend lint-imports --config .importlinter`
Expected: `Contracts: 4 kept, 0 broken.`

```bash
git add backend/apps/auth
git commit -m "feat(auth): 소셜 제공자 전략 4종과 팩토리"
```

---

### Task 7: 소셜 로그인 슬라이스 (`POST /v1/auth/social`)

**Files:**
- Create: `backend/apps/auth/app/dtos/social_login_dto.py`
- Create: `backend/apps/auth/app/ports/input/social_login_use_case.py`
- Create: `backend/apps/auth/app/use_cases/social_login_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/social_login_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/social_login_router.py`
- Create: `backend/apps/auth/adapter/inbound/api/error_map.py`
- Create: `backend/apps/auth/dependencies/auth_wiring.py`, `social_login_provider.py`
- Modify: `backend/auth_main.py` (라우터 장착, 오류 핸들러 설치)
- Test: `backend/apps/auth/tests/app/use_cases/test_social_login_interactor.py`, `backend/apps/auth/tests/adapter/test_social_login_router.py`

**Interfaces:**
- Consumes: Task 4 `UserRepository`, Task 5 `SessionIssuer`·`TokenPair`·`install_error_handlers`, Task 6 `SocialProviderResolverPort`·`SocialCredentials`·도메인 오류
- Produces:
  - `SocialLoginCommand(provider: str, token: str, authorization_code: str | None, nonce: str | None, display_name: str | None)`, `SocialLoginResult(user_id: int, is_new_user: bool, tokens: TokenPair)`
  - `SocialLoginUseCase.login(command: SocialLoginCommand) -> SocialLoginResult` (async)
  - `auth.adapter.inbound.api.error_map.AUTH_ERROR_STATUS: dict[type[Exception], int]`
  - `auth.dependencies.auth_wiring`: `build_user_repository(db: AsyncSession) -> UserRepository`, `build_refresh_store() -> RefreshTokenStorePort`, `build_session_issuer() -> SessionIssuer`, `build_provider_resolver() -> SocialProviderResolverPort`
  - `auth.dependencies.social_login_provider.get_social_login_use_case`
  - `social_login_router` (prefix `/v1/auth`), 응답 스키마 `TokenResponseSchema(access_token, refresh_token, token_type, expires_in, user_id, is_new_user)`

- [ ] **Step 1: 인터랙터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_social_login_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.domain.entities.user import User
from auth.domain.errors import AccountSuspendedError, UnsupportedProviderError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def _user(user_id=1, suspended=False):
    return User(
        id=user_id, display_name="두부 보호자", profile_image_url=None, phone=None,
        suspended_at=datetime.now(timezone.utc) if suspended else None, deleted_at=None,
    )


class _StubProvider:
    def __init__(self):
        self.seen = []

    async def verify(self, credentials):
        self.seen.append(credentials)
        return SocialProfile(Provider.KAKAO, "kakao-100", None, "두부 보호자", None, None)


class _StubResolver:
    def __init__(self, provider):
        self._provider = provider

    def resolve(self, provider):
        return self._provider


class _StubUsers:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = []

    async def find_by_identity(self, provider, provider_user_id):
        return self.existing

    async def create_with_identity(self, profile):
        self.created.append(profile)
        return _user(user_id=77)


class _StubSessions:
    def __init__(self):
        self.issued_for = []

    async def issue(self, user_id):
        self.issued_for.append(user_id)
        return TokenPair("access", "refresh", 900)


def _command(provider="kakao"):
    return SocialLoginCommand(provider=provider, token="provider-token",
                              authorization_code=None, nonce=None, display_name=None)


async def test_처음_보는_신원이면_유저를_만들고_토큰을_발급한다():
    users, sessions = _StubUsers(existing=None), _StubSessions()
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (77, True)
    assert len(users.created) == 1
    assert sessions.issued_for == [77]
    assert result.tokens.refresh_token == "refresh"


async def test_이미_있는_신원이면_새로_만들지_않는다():
    users, sessions = _StubUsers(existing=_user(user_id=5)), _StubSessions()
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (5, False)
    assert users.created == []


async def test_앱이_보낸_토큰을_제공자_검증에_그대로_넘긴다():
    provider = _StubProvider()
    await SocialLoginInteractor(_StubResolver(provider), _StubUsers(), _StubSessions()).login(_command())
    assert provider.seen[0].token == "provider-token"


async def test_정지된_계정에는_토큰을_발급하지_않는다():
    users, sessions = _StubUsers(existing=_user(suspended=True)), _StubSessions()
    with pytest.raises(AccountSuspendedError):
        await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert sessions.issued_for == []


async def test_모르는_제공자_이름은_거절한다():
    with pytest.raises(UnsupportedProviderError):
        await SocialLoginInteractor(
            _StubResolver(_StubProvider()), _StubUsers(), _StubSessions()
        ).login(_command(provider="naver"))
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_social_login_interactor.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.social_login_dto'`

- [ ] **Step 2: DTO·입력 포트·인터랙터를 구현한다**

`backend/apps/auth/app/dtos/social_login_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from auth.app.dtos.token_dto import TokenPair


@dataclass(frozen=True)
class SocialLoginCommand:
    provider: str
    token: str
    authorization_code: str | None
    nonce: str | None
    display_name: str | None


@dataclass(frozen=True)
class SocialLoginResult:
    user_id: int
    is_new_user: bool
    tokens: TokenPair
```

`backend/apps/auth/app/ports/input/social_login_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.social_login_dto import SocialLoginCommand, SocialLoginResult


class SocialLoginUseCase(ABC):
    @abstractmethod
    async def login(self, command: SocialLoginCommand) -> SocialLoginResult: ...
```

`backend/apps/auth/app/use_cases/social_login_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.social_login_dto import SocialLoginCommand, SocialLoginResult
from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import AccountSuspendedError, UnsupportedProviderError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


class SocialLoginInteractor(SocialLoginUseCase):
    def __init__(
        self, providers: SocialProviderResolverPort, users: UserRepository, sessions: SessionIssuer
    ) -> None:
        self._providers = providers
        self._users = users
        self._sessions = sessions

    async def login(self, command: SocialLoginCommand) -> SocialLoginResult:
        try:
            provider = Provider(command.provider)
        except ValueError:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.")
        profile = await self._providers.resolve(provider).verify(
            SocialCredentials(
                token=command.token,
                authorization_code=command.authorization_code,
                nonce=command.nonce,
                display_name=command.display_name,
            )
        )
        user = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
        is_new_user = user is None
        if user is None:
            user = await self._users.create_with_identity(profile)
        if user.is_suspended:
            raise AccountSuspendedError("정지된 계정입니다.")
        tokens = await self._sessions.issue(user.id)
        return SocialLoginResult(user_id=user.id, is_new_user=is_new_user, tokens=tokens)
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_social_login_interactor.py -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 3: 라우터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_social_login_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.social_login_router import social_login_router
from auth.app.dtos.social_login_dto import SocialLoginResult
from auth.app.dtos.token_dto import TokenPair
from auth.dependencies.social_login_provider import get_social_login_use_case
from auth.domain.errors import AccountSuspendedError, ProviderVerificationError
from core.http_errors import install_error_handlers


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def login(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return SocialLoginResult(user_id=7, is_new_user=True, tokens=TokenPair("access", "refresh", 900))


def _client(stub):
    app = FastAPI()
    app.include_router(social_login_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_social_login_use_case] = lambda: stub
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_로그인에_성공하면_토큰_한_쌍을_돌려준다():
    stub = _StubUseCase()
    async with _client(stub) as client:
        response = await client.post("/v1/auth/social", json={"provider": "dev", "token": "owner"})
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "access", "refresh_token": "refresh", "token_type": "Bearer",
        "expires_in": 900, "user_id": 7, "is_new_user": True,
    }
    assert stub.commands[0].provider == "dev"
    assert stub.commands[0].authorization_code is None


async def test_정지된_계정은_403과_오류_코드를_돌려준다():
    async with _client(_StubUseCase(AccountSuspendedError("정지된 계정입니다."))) as client:
        response = await client.post("/v1/auth/social", json={"provider": "dev", "token": "x"})
    assert response.status_code == 403
    assert response.json() == {"code": "ACCOUNT_SUSPENDED", "message": "정지된 계정입니다."}


async def test_제공자_검증에_실패하면_401이다():
    async with _client(_StubUseCase(ProviderVerificationError("확인할 수 없습니다."))) as client:
        response = await client.post("/v1/auth/social", json={"provider": "kakao", "token": "bad"})
    assert response.status_code == 401
    assert response.json()["code"] == "PROVIDER_VERIFICATION_FAILED"


async def test_token_이_없으면_422이다():
    async with _client(_StubUseCase()) as client:
        response = await client.post("/v1/auth/social", json={"provider": "dev"})
    assert response.status_code == 422
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_social_login_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.inbound.api.error_map'`

- [ ] **Step 4: 오류 표·스키마·조립·프로바이더·라우터를 구현한다**

`backend/apps/auth/adapter/inbound/api/error_map.py`:
```python
"""auth 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from auth.domain.errors import (
    AccountSuspendedError,
    InvalidRefreshTokenError,
    ProviderVerificationError,
    RefreshTokenReuseError,
    UnsupportedProviderError,
)

AUTH_ERROR_STATUS: dict[type[Exception], int] = {
    UnsupportedProviderError: 400,
    ProviderVerificationError: 401,
    InvalidRefreshTokenError: 401,
    RefreshTokenReuseError: 401,
    AccountSuspendedError: 403,
}
```

`backend/apps/auth/adapter/inbound/api/schemas/social_login_schema.py`:
```python
from pydantic import BaseModel, Field


class SocialLoginRequestSchema(BaseModel):
    provider: str = Field(description="kakao · apple · google (개발 환경에서는 dev)")
    token: str = Field(min_length=1, description="제공자 SDK 가 준 토큰. dev 는 로그인할 이름")
    authorization_code: str | None = Field(None, description="Apple 전용")
    nonce: str | None = Field(None, description="Apple 전용 — 앱이 만든 원본 nonce")
    display_name: str | None = Field(None, description="Apple 첫 로그인 때 앱이 받은 이름")


class TokenResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user_id: int
    is_new_user: bool
```

`backend/apps/auth/dependencies/auth_wiring.py`:
```python
"""auth 슬라이스 프로바이더들이 함께 쓰는 조립 함수.

개인키가 필요한 조립(build_session_issuer)은 core.auth_config 를 함수 안에서 import 한다.
모듈 최상단에서 import 하면 개인키가 없는 API 프로세스에서 이 모듈을 불러올 때 실패한다.
"""
from __future__ import annotations

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.factory.social_provider_factory import (
    AppleSettings,
    build_social_provider_factory,
)
from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher
from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.adapter.outbound.redis.refresh_token_redis_store import RefreshTokenRedisStore
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from core import config
from core.redis import get_redis

_http = httpx.AsyncClient(timeout=5.0)
_resolver: SocialProviderResolverPort | None = None


def build_user_repository(db: AsyncSession) -> UserRepository:
    return UserPgRepository(db, FernetCipher(config.IDENTITY_TOKEN_ENC_KEY))


def build_refresh_store() -> RefreshTokenStorePort:
    return RefreshTokenRedisStore(get_redis(), config.REFRESH_TOKEN_TTL_SECONDS)


def build_session_issuer() -> SessionIssuer:
    from core.auth_config import JWT_PRIVATE_KEY

    return SessionIssuer(
        JwtTokenIssuer(JWT_PRIVATE_KEY, config.ACCESS_TOKEN_TTL_SECONDS), build_refresh_store()
    )


def build_provider_resolver() -> SocialProviderResolverPort:
    """공개키 캐시를 유지하려고 프로세스에 하나만 만든다."""
    global _resolver
    if _resolver is None:
        apple = None
        if config.APPLE_BUNDLE_ID and config.APPLE_PRIVATE_KEY:
            apple = AppleSettings(
                config.APPLE_BUNDLE_ID, config.APPLE_TEAM_ID,
                config.APPLE_KEY_ID, config.APPLE_PRIVATE_KEY,
            )
        _resolver = build_social_provider_factory(
            app_env=config.APP_ENV,
            kakao_app_id=config.KAKAO_APP_ID,
            google_client_ids=config.GOOGLE_CLIENT_IDS,
            apple=apple,
            http=_http,
        )
    return _resolver
```

`backend/apps/auth/dependencies/social_login_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.app.use_cases.social_login_interactor import SocialLoginInteractor
from auth.dependencies.auth_wiring import (
    build_provider_resolver,
    build_session_issuer,
    build_user_repository,
)
from core.database import get_db


def get_social_login_use_case(db: AsyncSession = Depends(get_db)) -> SocialLoginUseCase:
    return SocialLoginInteractor(
        providers=build_provider_resolver(),
        users=build_user_repository(db),
        sessions=build_session_issuer(),
    )
```

`backend/apps/auth/adapter/inbound/api/v1/social_login_router.py`:
```python
from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.social_login_schema import (
    SocialLoginRequestSchema,
    TokenResponseSchema,
)
from auth.app.dtos.social_login_dto import SocialLoginCommand
from auth.app.ports.input.social_login_use_case import SocialLoginUseCase
from auth.dependencies.social_login_provider import get_social_login_use_case

social_login_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@social_login_router.post("/social", response_model=TokenResponseSchema)
async def social_login(
    body: SocialLoginRequestSchema,
    use_case: SocialLoginUseCase = Depends(get_social_login_use_case),
) -> TokenResponseSchema:
    result = await use_case.login(
        SocialLoginCommand(
            provider=body.provider,
            token=body.token,
            authorization_code=body.authorization_code,
            nonce=body.nonce,
            display_name=body.display_name,
        )
    )
    return TokenResponseSchema(
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
        user_id=result.user_id,
        is_new_user=result.is_new_user,
    )
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_social_login_router.py -q -p no:cacheprovider`
Expected: `4 passed`

- [ ] **Step 5: 인증 프로세스에 장착하고 오류 핸들러를 설치한다**

`backend/auth_main.py`의 import 묶음에 추가:
```python
from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.social_login_router import social_login_router
from core.http_errors import install_error_handlers
```
`app.include_router(auth_myself_router)` 아래에 추가:
```python
app.include_router(social_login_router)
install_error_handlers(app, AUTH_ERROR_STATUS)
```

- [ ] **Step 6: 실제로 로그인해 본다**

Run:
```bash
cd infra && docker compose up -d && sleep 5
curl -s -X POST http://127.0.0.1:8080/v1/auth/social \
  -H 'Content-Type: application/json' -d '{"provider":"dev","token":"Owner"}'; echo
curl -s -X POST http://127.0.0.1:8080/v1/auth/social \
  -H 'Content-Type: application/json' -d '{"provider":"naver","token":"x"}'; echo
```
Expected: 첫 응답은 `"token_type":"Bearer"`, `"expires_in":900`, `"is_new_user":true`가 든 JSON이다. 같은 요청을 다시 보내면 `"is_new_user":false`다. 둘째 응답은 `{"code":"PROVIDER_NOT_SUPPORTED","message":"naver 로그인은 지원하지 않습니다."}`다.

- [ ] **Step 7: 전체 테스트와 구조 계약을 확인하고 커밋한다 (허용된 경우)**

Run:
```bash
cd infra
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 실패 0건, `Contracts: 4 kept, 0 broken.`

```bash
git add backend
git commit -m "feat(auth): 소셜 로그인 슬라이스 POST /v1/auth/social"
```

---

### Task 8: 토큰 갱신 슬라이스 (`POST /v1/auth/refresh`)

**Files:**
- Create: `backend/apps/auth/app/dtos/refresh_token_dto.py`
- Create: `backend/apps/auth/app/ports/input/refresh_token_use_case.py`
- Create: `backend/apps/auth/app/use_cases/refresh_token_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/refresh_token_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/refresh_token_router.py`
- Create: `backend/apps/auth/dependencies/refresh_token_provider.py`
- Modify: `backend/auth_main.py` (라우터 장착)
- Test: `backend/apps/auth/tests/app/use_cases/test_refresh_token_interactor.py`, `backend/apps/auth/tests/adapter/test_refresh_token_router.py`

**Interfaces:**
- Consumes: Task 5 `RefreshTokenStorePort`·`RefreshLookup`·`RefreshStatus`·`SessionIssuer`·`TokenPair`, Task 4 `UserRepository`, Task 6 도메인 오류, Task 7 `AUTH_ERROR_STATUS`·`auth_wiring`
- Produces:
  - `RefreshTokenCommand(refresh_token: str)`
  - `RefreshTokenUseCase.refresh(command: RefreshTokenCommand) -> TokenPair` (async)
  - `refresh_token_router` (prefix `/v1/auth`), `get_refresh_token_use_case`
  - 응답 스키마 `RefreshResponseSchema(access_token, refresh_token, token_type, expires_in)`

- [ ] **Step 1: 인터랙터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_refresh_token_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.use_cases.refresh_token_interactor import RefreshTokenInteractor
from auth.domain.entities.user import User
from auth.domain.errors import (
    AccountSuspendedError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
)
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _user(suspended=False, deleted=False):
    now = datetime.now(timezone.utc)
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=now if suspended else None, deleted_at=now if deleted else None)


class _StubStore:
    def __init__(self, lookup):
        self.lookup = lookup
        self.revoked_all = []

    async def take(self, token):
        return self.lookup

    async def revoke_all(self, user_id):
        self.revoked_all.append(user_id)


class _StubUsers:
    def __init__(self, user):
        self.user = user

    async def get(self, user_id):
        return self.user


class _StubSessions:
    def __init__(self):
        self.issued_for = []

    async def issue(self, user_id):
        self.issued_for.append(user_id)
        return TokenPair("new-access", "new-refresh", 900)


def _run(lookup, user=None):
    store, sessions = _StubStore(lookup), _StubSessions()
    interactor = RefreshTokenInteractor(store, _StubUsers(user), sessions)
    return interactor, store, sessions


async def test_유효한_토큰이면_새_토큰_한_쌍을_발급한다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5), _user())
    pair = await interactor.refresh(RefreshTokenCommand("old-refresh"))
    assert pair.refresh_token == "new-refresh"
    assert sessions.issued_for == [5]


async def test_모르는_토큰은_거절한다():
    interactor, store, sessions = _run(RefreshLookup(RefreshStatus.MISSING, None))
    with pytest.raises(InvalidRefreshTokenError):
        await interactor.refresh(RefreshTokenCommand("unknown"))
    assert store.revoked_all == [] and sessions.issued_for == []


async def test_이미_쓴_토큰이_다시_오면_그_유저의_세션을_모두_폐기한다():
    interactor, store, sessions = _run(RefreshLookup(RefreshStatus.USED, 5), _user())
    with pytest.raises(RefreshTokenReuseError):
        await interactor.refresh(RefreshTokenCommand("stolen"))
    assert store.revoked_all == [5]
    assert sessions.issued_for == []


async def test_탈퇴했거나_없는_유저에게는_발급하지_않는다():
    for user in (None, _user(deleted=True)):
        interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5), user)
        with pytest.raises(InvalidRefreshTokenError):
            await interactor.refresh(RefreshTokenCommand("old-refresh"))
        assert sessions.issued_for == []


async def test_정지된_유저에게는_발급하지_않는다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5), _user(suspended=True))
    with pytest.raises(AccountSuspendedError):
        await interactor.refresh(RefreshTokenCommand("old-refresh"))
    assert sessions.issued_for == []
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_refresh_token_interactor.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.refresh_token_dto'`

- [ ] **Step 2: DTO·입력 포트·인터랙터를 구현한다**

`backend/apps/auth/app/dtos/refresh_token_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class RefreshTokenCommand:
    refresh_token: str
```

`backend/apps/auth/app/ports/input/refresh_token_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.token_dto import TokenPair


class RefreshTokenUseCase(ABC):
    @abstractmethod
    async def refresh(self, command: RefreshTokenCommand) -> TokenPair: ...
```

`backend/apps/auth/app/use_cases/refresh_token_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.dtos.token_dto import TokenPair
from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import (
    AccountSuspendedError,
    InvalidRefreshTokenError,
    RefreshTokenReuseError,
)
from auth.domain.value_objects.refresh_lookup import RefreshStatus


class RefreshTokenInteractor(RefreshTokenUseCase):
    def __init__(
        self, store: RefreshTokenStorePort, users: UserRepository, sessions: SessionIssuer
    ) -> None:
        self._store = store
        self._users = users
        self._sessions = sessions

    async def refresh(self, command: RefreshTokenCommand) -> TokenPair:
        lookup = await self._store.take(command.refresh_token)
        if lookup.status is RefreshStatus.USED and lookup.user_id is not None:
            # 이미 새 토큰으로 바뀐 토큰이 다시 왔다 — 탈취로 보고 모든 세션을 끊는다.
            await self._store.revoke_all(lookup.user_id)
            raise RefreshTokenReuseError("다시 로그인해 주세요.")
        if lookup.status is not RefreshStatus.ACTIVE or lookup.user_id is None:
            raise InvalidRefreshTokenError("다시 로그인해 주세요.")
        user = await self._users.get(lookup.user_id)
        if user is None or user.is_deleted:
            raise InvalidRefreshTokenError("다시 로그인해 주세요.")
        if user.is_suspended:
            raise AccountSuspendedError("정지된 계정입니다.")
        return await self._sessions.issue(user.id)
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_refresh_token_interactor.py -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 3: 라우터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_refresh_token_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.refresh_token_router import refresh_token_router
from auth.app.dtos.token_dto import TokenPair
from auth.dependencies.refresh_token_provider import get_refresh_token_use_case
from auth.domain.errors import RefreshTokenReuseError
from core.http_errors import install_error_handlers


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def refresh(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return TokenPair("new-access", "new-refresh", 900)


def _client(stub):
    app = FastAPI()
    app.include_router(refresh_token_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_refresh_token_use_case] = lambda: stub
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_새_토큰_한_쌍을_돌려준다():
    stub = _StubUseCase()
    async with _client(stub) as client:
        response = await client.post("/v1/auth/refresh", json={"refresh_token": "old"})
    assert response.status_code == 200
    assert response.json() == {
        "access_token": "new-access", "refresh_token": "new-refresh",
        "token_type": "Bearer", "expires_in": 900,
    }
    assert stub.commands[0].refresh_token == "old"


async def test_재사용된_토큰은_401과_UNAUTHENTICATED_를_돌려준다():
    async with _client(_StubUseCase(RefreshTokenReuseError("다시 로그인해 주세요."))) as client:
        response = await client.post("/v1/auth/refresh", json={"refresh_token": "stolen"})
    assert response.status_code == 401
    assert response.json() == {"code": "UNAUTHENTICATED", "message": "다시 로그인해 주세요."}
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_refresh_token_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.inbound.api.v1.refresh_token_router'`

- [ ] **Step 4: 스키마·프로바이더·라우터를 구현한다**

`backend/apps/auth/adapter/inbound/api/schemas/refresh_token_schema.py`:
```python
from pydantic import BaseModel, Field


class RefreshRequestSchema(BaseModel):
    refresh_token: str = Field(min_length=1)


class RefreshResponseSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
```

`backend/apps/auth/dependencies/refresh_token_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.app.use_cases.refresh_token_interactor import RefreshTokenInteractor
from auth.dependencies.auth_wiring import (
    build_refresh_store,
    build_session_issuer,
    build_user_repository,
)
from core.database import get_db


def get_refresh_token_use_case(db: AsyncSession = Depends(get_db)) -> RefreshTokenUseCase:
    return RefreshTokenInteractor(
        store=build_refresh_store(),
        users=build_user_repository(db),
        sessions=build_session_issuer(),
    )
```

`backend/apps/auth/adapter/inbound/api/v1/refresh_token_router.py`:
```python
from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.refresh_token_schema import (
    RefreshRequestSchema,
    RefreshResponseSchema,
)
from auth.app.dtos.refresh_token_dto import RefreshTokenCommand
from auth.app.ports.input.refresh_token_use_case import RefreshTokenUseCase
from auth.dependencies.refresh_token_provider import get_refresh_token_use_case

refresh_token_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@refresh_token_router.post("/refresh", response_model=RefreshResponseSchema)
async def refresh_token(
    body: RefreshRequestSchema,
    use_case: RefreshTokenUseCase = Depends(get_refresh_token_use_case),
) -> RefreshResponseSchema:
    pair = await use_case.refresh(RefreshTokenCommand(refresh_token=body.refresh_token))
    return RefreshResponseSchema(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        expires_in=pair.expires_in,
    )
```

- [ ] **Step 5: 인증 프로세스에 장착하고 확인한다**

`backend/auth_main.py`의 import 묶음에 추가:
```python
from auth.adapter.inbound.api.v1.refresh_token_router import refresh_token_router
```
`app.include_router(social_login_router)` 아래에 추가:
```python
app.include_router(refresh_token_router)
```

Run:
```bash
cd infra
docker compose run --rm --no-deps backend pytest apps/auth -q -p no:cacheprovider -m "not integration"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 실패 0건, `Contracts: 4 kept, 0 broken.`

- [ ] **Step 6: 커밋 (허용된 경우)**

```bash
git add backend
git commit -m "feat(auth): 토큰 갱신 슬라이스와 재사용 감지"
```

---

### Task 9: 로그아웃 슬라이스 (`POST /v1/auth/logout`)

**Files:**
- Create: `backend/apps/auth/app/dtos/logout_dto.py`
- Create: `backend/apps/auth/app/ports/input/logout_use_case.py`
- Create: `backend/apps/auth/app/use_cases/logout_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/logout_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/logout_router.py`
- Create: `backend/apps/auth/dependencies/logout_provider.py`
- Modify: `backend/auth_main.py` (라우터 장착)
- Test: `backend/apps/auth/tests/app/use_cases/test_logout_interactor.py`, `backend/apps/auth/tests/adapter/test_logout_router.py`

**Interfaces:**
- Consumes: Task 5 `RefreshTokenStorePort.revoke`, Task 7 `auth_wiring.build_refresh_store`
- Produces: `LogoutCommand(refresh_token: str)`, `LogoutUseCase.logout(command: LogoutCommand) -> None` (async), `logout_router` (prefix `/v1/auth`), `get_logout_use_case`

- [ ] **Step 1: 인터랙터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_logout_interactor.py`:
```python
from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.use_cases.logout_interactor import LogoutInteractor


class _StubStore:
    def __init__(self):
        self.revoked = []

    async def revoke(self, token):
        self.revoked.append(token)


async def test_리프레시_토큰을_폐기한다():
    store = _StubStore()
    await LogoutInteractor(store).logout(LogoutCommand("my-refresh"))
    assert store.revoked == ["my-refresh"]


async def test_같은_토큰으로_두_번_로그아웃해도_실패하지_않는다():
    store = _StubStore()
    interactor = LogoutInteractor(store)
    await interactor.logout(LogoutCommand("my-refresh"))
    await interactor.logout(LogoutCommand("my-refresh"))
    assert store.revoked == ["my-refresh", "my-refresh"]
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_logout_interactor.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.logout_dto'`

- [ ] **Step 2: DTO·입력 포트·인터랙터를 구현한다**

`backend/apps/auth/app/dtos/logout_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class LogoutCommand:
    refresh_token: str
```

`backend/apps/auth/app/ports/input/logout_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.logout_dto import LogoutCommand


class LogoutUseCase(ABC):
    @abstractmethod
    async def logout(self, command: LogoutCommand) -> None: ...
```

`backend/apps/auth/app/use_cases/logout_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.ports.input.logout_use_case import LogoutUseCase
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort


class LogoutInteractor(LogoutUseCase):
    """이 기기의 세션만 끊는다. 액세스 토큰은 15분 뒤 저절로 만료된다."""

    def __init__(self, store: RefreshTokenStorePort) -> None:
        self._store = store

    async def logout(self, command: LogoutCommand) -> None:
        await self._store.revoke(command.refresh_token)
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_logout_interactor.py -q -p no:cacheprovider`
Expected: `2 passed`

- [ ] **Step 3: 라우터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_logout_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.v1.logout_router import logout_router
from auth.dependencies.logout_provider import get_logout_use_case


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def logout(self, command):
        self.commands.append(command)


async def test_로그아웃은_본문_없이_204를_돌려준다():
    stub = _StubUseCase()
    app = FastAPI()
    app.include_router(logout_router)
    app.dependency_overrides[get_logout_use_case] = lambda: stub
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.post("/v1/auth/logout", json={"refresh_token": "my-refresh"})
    assert response.status_code == 204
    assert response.content == b""
    assert stub.commands[0].refresh_token == "my-refresh"
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_logout_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.inbound.api.v1.logout_router'`

- [ ] **Step 4: 스키마·프로바이더·라우터를 구현한다**

`backend/apps/auth/adapter/inbound/api/schemas/logout_schema.py`:
```python
from pydantic import BaseModel, Field


class LogoutRequestSchema(BaseModel):
    refresh_token: str = Field(min_length=1)
```

`backend/apps/auth/dependencies/logout_provider.py`:
```python
from __future__ import annotations

from auth.app.ports.input.logout_use_case import LogoutUseCase
from auth.app.use_cases.logout_interactor import LogoutInteractor
from auth.dependencies.auth_wiring import build_refresh_store


def get_logout_use_case() -> LogoutUseCase:
    return LogoutInteractor(store=build_refresh_store())
```

`backend/apps/auth/adapter/inbound/api/v1/logout_router.py`:
```python
from fastapi import APIRouter, Depends, Response, status

from auth.adapter.inbound.api.schemas.logout_schema import LogoutRequestSchema
from auth.app.dtos.logout_dto import LogoutCommand
from auth.app.ports.input.logout_use_case import LogoutUseCase
from auth.dependencies.logout_provider import get_logout_use_case

logout_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@logout_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequestSchema,
    use_case: LogoutUseCase = Depends(get_logout_use_case),
) -> Response:
    await use_case.logout(LogoutCommand(refresh_token=body.refresh_token))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 5: 인증 프로세스에 장착하고 확인한다**

`backend/auth_main.py`의 import 묶음에 추가:
```python
from auth.adapter.inbound.api.v1.logout_router import logout_router
```
`app.include_router(refresh_token_router)` 아래에 추가:
```python
app.include_router(logout_router)
```

Run:
```bash
cd infra
docker compose run --rm --no-deps backend pytest apps/auth -q -p no:cacheprovider -m "not integration"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 실패 0건, `Contracts: 4 kept, 0 broken.`

- [ ] **Step 6: 커밋 (허용된 경우)**

```bash
git add backend
git commit -m "feat(auth): 로그아웃 슬라이스"
```

---

### Task 10: 내 정보 조회 슬라이스 (`GET /v1/me`)

**Files:**
- Create: `backend/apps/auth/app/dtos/get_me_dto.py`
- Create: `backend/apps/auth/app/ports/input/get_me_use_case.py`
- Create: `backend/apps/auth/app/use_cases/get_me_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/get_me_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/get_me_router.py`
- Create: `backend/apps/auth/dependencies/get_me_provider.py`
- Modify: `backend/apps/auth/domain/errors.py` (`UserNotFoundError` 추가)
- Modify: `backend/apps/auth/adapter/inbound/api/error_map.py` (`UserNotFoundError: 401` 추가)
- Modify: `backend/main.py` (라우터 장착, 오류 핸들러 설치)
- Test: `backend/apps/auth/tests/app/use_cases/test_get_me_interactor.py`, `backend/apps/auth/tests/adapter/test_get_me_router.py`

**Interfaces:**
- Consumes: Task 4 `UserRepository.get`·`list_identities`, Task 5 `core.security.get_current_user_id`·`install_error_handlers`, Task 7 `auth_wiring.build_user_repository`·`AUTH_ERROR_STATUS`
- Produces:
  - `GetMeQuery(user_id: int)`, `MeResponse(id: int, display_name: str, profile_image_url: str | None, identities: tuple[str, ...])`
  - `GetMeUseCase.get_me(query: GetMeQuery) -> MeResponse` (async)
  - `auth.domain.errors.UserNotFoundError` (`code = "UNAUTHENTICATED"`)
  - `get_me_router` (prefix `/v1`), `get_get_me_use_case`
  - 계획 2는 `MeResponse`와 `MeResponseSchema`에 `memberships` 필드를 더한다.

이 슬라이스는 auth 앱에 속하지만 토큰을 발급하지 않으므로 API 프로세스(`main.py`)에 장착한다.

- [ ] **Step 1: 인터랙터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_get_me_interactor.py`:
```python
import pytest

from auth.app.dtos.get_me_dto import GetMeQuery
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.provider import Provider


class _StubUsers:
    def __init__(self, user, identities=()):
        self.user = user
        self.identities = list(identities)

    async def get(self, user_id):
        return self.user

    async def list_identities(self, user_id):
        return self.identities


def _user():
    return User(id=5, display_name="두부 보호자", profile_image_url="https://img/1.jpg",
                phone=None, suspended_at=None, deleted_at=None)


async def test_프로필과_연결된_로그인_수단을_돌려준다():
    identities = [
        SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
        SocialIdentity(2, 5, Provider.APPLE, "apple-1", None),
    ]
    me = await GetMeInteractor(_StubUsers(_user(), identities)).get_me(GetMeQuery(user_id=5))
    assert (me.id, me.display_name, me.profile_image_url) == (5, "두부 보호자", "https://img/1.jpg")
    assert me.identities == ("kakao", "apple")


async def test_유저가_없으면_UserNotFoundError_다():
    with pytest.raises(UserNotFoundError):
        await GetMeInteractor(_StubUsers(None)).get_me(GetMeQuery(user_id=404))
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_get_me_interactor.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.get_me_dto'`

- [ ] **Step 2: 도메인 오류·DTO·입력 포트·인터랙터를 구현한다**

`backend/apps/auth/domain/errors.py` 맨 아래에 추가:
```python


class UserNotFoundError(AuthError):
    code = "UNAUTHENTICATED"
```

`backend/apps/auth/adapter/inbound/api/error_map.py`를 아래 전체로 바꾼다:
```python
"""auth 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from auth.domain.errors import (
    AccountSuspendedError,
    InvalidRefreshTokenError,
    ProviderVerificationError,
    RefreshTokenReuseError,
    UnsupportedProviderError,
    UserNotFoundError,
)

AUTH_ERROR_STATUS: dict[type[Exception], int] = {
    UnsupportedProviderError: 400,
    ProviderVerificationError: 401,
    InvalidRefreshTokenError: 401,
    RefreshTokenReuseError: 401,
    UserNotFoundError: 401,
    AccountSuspendedError: 403,
}
```

`backend/apps/auth/app/dtos/get_me_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GetMeQuery:
    user_id: int


@dataclass(frozen=True)
class MeResponse:
    id: int
    display_name: str
    profile_image_url: str | None
    identities: tuple[str, ...]
```

`backend/apps/auth/app/ports/input/get_me_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.get_me_dto import GetMeQuery, MeResponse


class GetMeUseCase(ABC):
    @abstractmethod
    async def get_me(self, query: GetMeQuery) -> MeResponse: ...
```

`backend/apps/auth/app/use_cases/get_me_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.get_me_dto import GetMeQuery, MeResponse
from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UserNotFoundError


class GetMeInteractor(GetMeUseCase):
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get_me(self, query: GetMeQuery) -> MeResponse:
        user = await self._users.get(query.user_id)
        if user is None:
            raise UserNotFoundError("다시 로그인해 주세요.")
        identities = await self._users.list_identities(user.id)
        return MeResponse(
            id=user.id,
            display_name=user.display_name,
            profile_image_url=user.profile_image_url,
            identities=tuple(i.provider.value for i in identities),
        )
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/app/use_cases/test_get_me_interactor.py -q -p no:cacheprovider`
Expected: `2 passed`

- [ ] **Step 3: 라우터의 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_get_me_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from auth.app.dtos.get_me_dto import MeResponse
from auth.dependencies.get_me_provider import get_get_me_use_case
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def get_me(self, query):
        self.queries.append(query)
        return MeResponse(id=query.user_id, display_name="두부 보호자",
                          profile_image_url=None, identities=("kakao",))


async def _no_db():
    yield None


def _app(stub):
    app = FastAPI()
    app.include_router(get_me_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_get_me_use_case] = lambda: stub
    app.dependency_overrides[get_db] = _no_db
    return app


async def test_로그인한_유저의_정보를_돌려준다():
    stub = _StubUseCase()
    app = _app(stub)
    app.dependency_overrides[get_current_user_id] = lambda: 5
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/me")
    assert response.status_code == 200
    assert response.json() == {
        "id": 5, "display_name": "두부 보호자", "profile_image_url": None, "identities": ["kakao"],
    }
    assert stub.queries[0].user_id == 5


async def test_토큰이_없으면_401과_UNAUTHENTICATED_다():
    async with AsyncClient(transport=ASGITransport(app=_app(_StubUseCase())), base_url="http://t") as client:
        response = await client.get("/v1/me")
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_get_me_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.adapter.inbound.api.v1.get_me_router'`

- [ ] **Step 4: 스키마·프로바이더·라우터를 구현한다**

`backend/apps/auth/adapter/inbound/api/schemas/get_me_schema.py`:
```python
from pydantic import BaseModel


class MeResponseSchema(BaseModel):
    id: int
    display_name: str
    profile_image_url: str | None
    identities: list[str]
```

`backend/apps/auth/dependencies/get_me_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.dependencies.auth_wiring import build_user_repository
from core.database import get_db


def get_get_me_use_case(db: AsyncSession = Depends(get_db)) -> GetMeUseCase:
    return GetMeInteractor(users=build_user_repository(db))
```

`backend/apps/auth/adapter/inbound/api/v1/get_me_router.py`:
```python
from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.get_me_schema import MeResponseSchema
from auth.app.dtos.get_me_dto import GetMeQuery
from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.dependencies.get_me_provider import get_get_me_use_case
from core.security import get_current_user_id

get_me_router = APIRouter(prefix="/v1", tags=["me"])


@get_me_router.get("/me", response_model=MeResponseSchema)
async def get_me(
    user_id: int = Depends(get_current_user_id),
    use_case: GetMeUseCase = Depends(get_get_me_use_case),
) -> MeResponseSchema:
    me = await use_case.get_me(GetMeQuery(user_id=user_id))
    return MeResponseSchema(
        id=me.id,
        display_name=me.display_name,
        profile_image_url=me.profile_image_url,
        identities=list(me.identities),
    )
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest apps/auth/tests/adapter/test_get_me_router.py -q -p no:cacheprovider`
Expected: `2 passed`

- [ ] **Step 5: API 프로세스에 장착한다**

`backend/main.py`에서 `from core.redis import dispose_redis` 아래에 추가:
```python
from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from core.http_errors import install_error_handlers
```
`app = FastAPI(...)` 줄 아래에 추가:
```python
app.include_router(get_me_router)
install_error_handlers(app, AUTH_ERROR_STATUS)
```

- [ ] **Step 6: API 프로세스가 개인키 없이 뜨는지 확인한다**

Run:
```bash
cd infra && docker compose up -d backend && sleep 5
docker compose exec backend python -c "import core.auth_config" ; echo "exit=$?"
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/v1/me
```
Expected: 첫 명령은 `RuntimeError: 필수 환경 변수 JWT_PRIVATE_KEY_B64 이(가) 없습니다.`와 `exit=1`이다. API 프로세스에는 개인키가 없다는 뜻이다. 둘째 명령은 `401`이다.

- [ ] **Step 7: 전체 테스트와 구조 계약을 확인하고 커밋한다 (허용된 경우)**

Run:
```bash
cd infra
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 실패 0건, `Contracts: 4 kept, 0 broken.`

```bash
git add backend
git commit -m "feat(auth): 내 정보 조회 슬라이스 GET /v1/me"
```

---

### Task 11: 라우트 표와 전체 흐름 확인

**Files:**
- Create: `backend/scripts/__init__.py` (빈 파일 — 테스트에서 `scripts.print_routes`로 import하기 위해서다)
- Create: `backend/scripts/print_routes.py`
- Create: `backend/scripts/check_auth_flow.sh`
- Test: `backend/tests/test_print_routes.py`

**Interfaces:**
- Consumes: `main.app`, `auth_main.app`
- Produces: `scripts.print_routes.collect_routes(apps: dict[str, FastAPI]) -> list[tuple[str, str, str, str]]` — (프로세스, 메서드, 경로, 함수 이름), 경로와 메서드 순으로 정렬

- [ ] **Step 1: 라우트 수집의 실패하는 테스트를 쓴다**

`backend/tests/test_print_routes.py`:
```python
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
```

`backend/scripts/__init__.py`: 빈 파일을 만든다.

Run: `cd infra && docker compose run --rm --no-deps backend pytest tests/test_print_routes.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.print_routes'`

- [ ] **Step 2: 라우트 표 스크립트를 구현한다**

`backend/scripts/print_routes.py`:
```python
"""두 프로세스의 라우트 표를 출력한다. 라우터를 추가하거나 옮긴 변경은 전후를 비교한다.

auth_main 을 import 하려면 JWT 개인키가 필요하므로 auth 서비스 컨테이너에서 실행한다:
    cd infra && docker compose run --rm --no-deps auth python scripts/print_routes.py
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.routing import APIRoute

_HIDDEN = ("/docs", "/redoc", "/openapi")


def collect_routes(apps: dict[str, FastAPI]) -> list[tuple[str, str, str, str]]:
    rows = [
        (process, method, route.path, route.name)
        for process, app in apps.items()
        for route in app.routes
        if isinstance(route, APIRoute) and not route.path.startswith(_HIDDEN)
        for method in sorted(route.methods)
    ]
    return sorted(rows, key=lambda row: (row[2], row[1]))


def run() -> None:
    import auth_main
    import main as api_main

    for process, method, path, name in collect_routes(
        {"auth": auth_main.app, "backend": api_main.app}
    ):
        print(f"{process:8} {method:7} {path:28} {name}")


if __name__ == "__main__":
    run()
```

Run: `cd infra && docker compose run --rm --no-deps backend pytest tests/test_print_routes.py -q -p no:cacheprovider`
Expected: `2 passed`

- [ ] **Step 3: 실제 라우트 표를 출력해서 설계와 맞는지 확인한다**

Run: `cd infra && docker compose run --rm --no-deps auth python scripts/print_routes.py`
Expected:
```
backend  GET     /health                      health
auth     GET     /v1/auth/health              health
auth     POST    /v1/auth/logout              logout
auth     GET     /v1/auth/myself              introduce_myself
auth     POST    /v1/auth/refresh             refresh_token
auth     POST    /v1/auth/social              social_login
backend  GET     /v1/me                       get_me
```
`/v1/auth/*`는 전부 `auth`, 나머지는 전부 `backend`여야 한다. 하나라도 어긋나면 프로세스 배치 규칙을 어긴 것이다.

- [ ] **Step 4: 전체 흐름 확인 스크립트를 쓴다**

`backend/scripts/check_auth_flow.sh`:
```bash
#!/usr/bin/env bash
# 개발 환경에서 로그인 → 내 정보 → 갱신 → 재사용 감지 → 로그아웃을 끝까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_auth_flow.sh
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
NAME="flow-check-$(date +%s)"

field() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
status() { curl -s -o /dev/null -w '%{http_code}' "$@"; }
post() { curl -s -X POST "$BASE$1" -H 'Content-Type: application/json' -d "$2"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }

login=$(post /v1/auth/social "{\"provider\":\"dev\",\"token\":\"$NAME\"}")
access=$(echo "$login" | field access_token)
refresh1=$(echo "$login" | field refresh_token)
expect "처음 로그인하면 새 유저다" "$(echo "$login" | field is_new_user)" "True"

me=$(curl -s "$BASE/v1/me" -H "Authorization: Bearer $access")
expect "내 정보에 이름이 나온다" "$(echo "$me" | field display_name)" "$NAME"
expect "토큰 없이 내 정보를 부르면 401" "$(status "$BASE/v1/me")" "401"

rotated=$(post /v1/auth/refresh "{\"refresh_token\":\"$refresh1\"}")
refresh2=$(echo "$rotated" | field refresh_token)
if [ "$refresh1" = "$refresh2" ]; then echo "실패  갱신하면 리프레시 토큰이 바뀌어야 한다"; exit 1; fi
echo "통과  갱신하면 리프레시 토큰이 바뀐다"

expect "이미 쓴 리프레시 토큰은 401" \
  "$(status -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh1\"}")" "401"
expect "재사용이 감지되면 새 토큰도 함께 폐기된다" \
  "$(status -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh2\"}")" "401"

again=$(post /v1/auth/social "{\"provider\":\"dev\",\"token\":\"$NAME\"}")
expect "다시 로그인하면 기존 유저다" "$(echo "$again" | field is_new_user)" "False"
refresh3=$(echo "$again" | field refresh_token)
expect "로그아웃은 204" \
  "$(status -X POST "$BASE/v1/auth/logout" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh3\"}")" "204"
expect "로그아웃한 리프레시 토큰은 401" \
  "$(status -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh3\"}")" "401"

echo "전체 흐름 확인 완료"
```

- [ ] **Step 5: 전체 흐름을 실제로 돌린다**

Run: `cd infra && docker compose up -d && sleep 6 && bash ../backend/scripts/check_auth_flow.sh`
Expected: `통과`로 시작하는 줄 9개와 마지막 줄 `전체 흐름 확인 완료`. `실패` 줄이 하나라도 있으면 그 단계의 슬라이스로 돌아가 고친다.

- [ ] **Step 6: 최종 검증을 한 번에 돌린다**

Run:
```bash
cd infra
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: `76 passed`, `Contracts: 4 kept, 0 broken.`

- [ ] **Step 7: 커밋 (허용된 경우)**

```bash
git add backend
git commit -m "chore(harness): 라우트 표 스크립트와 인증 흐름 확인 스크립트"
```

---

## 계획 2로 넘기는 것

이 계획이 끝나면 아래가 남는다. 계획 2는 이 계획의 실제 코드를 본 뒤에 쓴다.

- `tenancy` 스포크: 매장, 역할·권한 시드, 소속, 초대 코드(해시 저장, 8자리, 7일, 1회, 분당 5회 시도 제한), 마지막 사장 보호
- `platform_admin` 스포크와 `platform_operators` 테이블, `scripts/grant_operator.py`
- 허브 포트 6개: `ShopAccessPort`, `MembershipDirectoryPort`, `MembershipLifecyclePort`, `UserDirectoryPort`, `ShopProvisioningPort`, `OperatorDirectoryPort`. `ShopContext` 값 객체와 `require_permission`
- import-linter의 다섯 번째 계약 "스포크 상호 독립" 추가, 기존 계약의 컨테이너 목록에 새 스포크 추가
- `auth`의 남은 슬라이스: `link_identity`, `unlink_identity`, `withdraw`. `SocialProviderPort.revoke`와 제공자별 연결 끊기, `FernetCipher.decrypt`
- `GET /v1/me` 응답에 소속 매장 목록 추가
- 테넌트 격리 테스트
- 계획 3: Flutter 앱 골격과 디자인 시스템
