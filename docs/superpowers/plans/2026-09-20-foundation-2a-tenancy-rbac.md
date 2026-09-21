# 차곡노트 ① 기반 — 계획 2-1: 매장과 매장별 RBAC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 운영자가 매장을 개설하고, 사장과 직원이 초대 코드로 합류하며, 매 요청마다 소속·역할·권한을 DB에서 확인하는 매장별 RBAC를 백엔드에 만든다. `GET /v1/me`가 소속 매장 목록을 돌려준다.

**Architecture:** 스포크 `tenancy`(매장·역할·소속·초대)와 `platform_admin`(운영자 표면)을 더한다. 스포크 사이의 협력은 허브 포트로만 한다. 포트 구현은 각 스포크가 HTTP 표면이 없는 슬라이스로 제공하고, **진입점(`main.py`)이 소비하는 쪽의 "허브 포트 자리"에 꽂는다.** 매장 범위의 모든 경로는 `core/shop_guard.py`의 `require_permission`을 거치며, 그 안에서 `ShopAccessPort`가 소속과 권한을 조회한다. 통합 테스트 DB는 `create_all` 대신 Alembic 마이그레이션으로 만들어 시드와 수기 마이그레이션을 함께 검증한다.

**Tech Stack:** Python 3.13 · FastAPI 0.141 · SQLAlchemy 2.0(asyncio) + asyncpg · Alembic 1.20 · Pydantic 2 · redis-py 8(asyncio) · import-linter 2 · pytest 9 + pytest-asyncio 1.4 · PostgreSQL 17(pgvector) · Redis 7 · Docker Compose

**Spec:** `docs/superpowers/specs/2026-09-20-foundation-design.md` — 이 계획은 그중 4.4절(tenancy·platform_admin), 4.5절, 4.6절(`MembershipLifecyclePort` 제외), 4.7절의 다섯 번째 계약, 5.1·5.2·5.5절, 7절, 8.1절(테넌트 격리·API 테스트)을 구현한다. 실행자는 설계 문서와 `_docs/decisions/001-plan1-review-carryover.md`도 함께 읽는다.

**계획의 위치:** ① 기반의 구현 계획은 네 개다. 1(백엔드 골격과 로그인, 완료) → **2-1(이 문서)** → 2-2(계정 연결·해제, 회원 탈퇴, 제공자 연결 끊기, 리프레시 토큰 세대 번호) → 3(Flutter 앱). 원래 계획 2 하나였으나 분량 때문에 2026-09-20에 둘로 나눴다.

**이 계획이 다루지 않는 것 (계획 2-2에서 다룬다):** `link_identity`·`unlink_identity`·`withdraw` 슬라이스, `MembershipLifecyclePort`, `SocialProviderPort.revoke`, 리프레시 토큰 세대 번호(넘김 항목 5), `IDENTITY_TOKEN_ENC_KEY` 이동(6), 동시 가입 `IntegrityError`(7), `is_deleted` 로그인 차단(8), Apple 리프레시 토큰 보완(9), 공용 HTTP 클라이언트 정리(10), 작은 것 18~23.

## Global Constraints

- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준 상대 경로다. 절대 경로를 코드나 설정에 쓰지 않는다.
- 작업 브랜치는 `main`에서 딴 `feat/foundation-2a-tenancy-rbac`다. `main`에서 직접 작업하지 않는다.
- **커밋은 사용자가 작업 단위 커밋을 허용한 경우에만 한다.** 허용하지 않았으면 각 작업의 마지막 "커밋" 단계를 건너뛰고 바뀐 파일 목록만 보고한다. 푸시는 하지 않는다.
- Python 3.13. 의존성은 `backend/requirements.txt`에만 추가한다. 이 계획은 새 의존성을 추가하지 않는다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이다.
- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 코드·테스트 데이터·문서에서 플랫폼 이름으로 쓰지 않는다. 테스트의 매장 이름으로 쓰는 것은 괜찮다.
- 수직 슬라이스 1:1: 유스케이스마다 router, schema, dto, input port, output port, interactor, provider, test 파일을 하나씩 둔다. 한 파일에 여러 슬라이스를 넣지 않는다. HTTP 표면이 없는 슬라이스는 schema와 router를 생략한다. DTO와 리포지토리는 도메인 말로 이름 지을 수 있다. entity·VO·mapper는 로직이 있을 때만 만든다.
- **허브 포트를 구현하는 슬라이스는 그 허브 포트를 입력 포트로 삼는다.** 인터랙터가 허브 포트 ABC를 직접 상속하며, 따로 입력 포트 파일을 만들지 않는다.
- **스포크끼리 import하지 않는다. `dependencies/`도 예외가 아니다.** 다른 스포크가 구현한 허브 포트가 필요하면 소비하는 쪽 `dependencies/hub_ports.py`에 "자리" 함수(호출하면 `RuntimeError`)를 두고, `backend/main.py`가 `app.dependency_overrides[자리] = 구현 프로바이더`로 채운다. 매장 접근 확인 자리만은 모든 매장 범위 스포크가 함께 쓰므로 `core/shop_guard.py`에 있다.
- **매장 범위의 리포지토리 메서드는 `ShopContext`를 필수 첫 인자로 받는다.** 예외는 아직 컨텍스트가 없는 경로(소속 확인 자체, 초대 수락, 매장 개설, 유저 기준 소속 목록)뿐이다.
- **스포크를 넘는 외래 키를 걸지 않는다.** `shop_members.user_id`는 인덱스만 있는 정수 컬럼이다.
- 새 라우터 묶음에는 `GET <prefix>/myself`를 두고 실제 기능을 설명한다. 배역이나 은유를 쓰지 않는다.
- 유스케이스는 어댑터 스키마가 아니라 app DTO(frozen dataclass)를 받는다. 스키마와 DTO 사이의 변환은 라우터가 한다.
- 아웃바운드 포트는 빈 껍데기를 만들지 않는다. 인터랙터가 실제로 호출하는 메서드만 정의한다.
- `app`·`domain` 계층에서 `fastapi`, `sqlalchemy`, `redis`, `httpx`, `jose`, `cryptography`를 import하지 않는다. `domain`은 `pydantic`과 `core`도 import하지 않는다.
- 엔티티(ORM)는 `int` 단일 PK `id`, `created_at`, `updated_at`을 가지며 SQLAlchemy 2.0 `Mapped` 스타일이다. 새 ORM 모듈은 `backend/orm_registry.py`에 한 줄을 더한다.
- I/O 작업은 `async def`, CPU 작업은 `def`다. 포트와 구현체의 `def`/`async def`를 일치시킨다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `backend/core/singleton/secret_manager.py`에서만 쓴다. 테스트에서 환경 변수를 바꿀 때는 `monkeypatch.setenv`를 쓴다.
- JWT 개인키는 인증 프로세스만 가진다. `core/auth_config.py`를 API 프로세스 경로(`main.py`가 import하는 모듈의 최상단)에서 import하지 않는다.
- 테스트는 mock 프레임워크 대신 스텁 구현을 쓴다. 실제 DB·Redis에 붙는 테스트는 `integration` 마커를 단다.
- 오류 응답 본문은 `{"code": "...", "message": "..."}` 형식이다. 도메인 규칙 위반은 도메인 예외로 던지고 `error_map.py`가 HTTP 상태로 바꾼다. 유스케이스는 HTTP를 모른다.
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.
- 백엔드 검증 명령은 전부 `infra/` 디렉터리에서 `docker compose run --rm backend …` 형태로 실행한다. 맥에 파이썬 환경을 만들지 않는다. 볼륨 삭제와 `docker compose down -v`는 실행하지 않는다.
- 이 문서에서 쓰는 검증 명령의 줄임말:
  - **단위 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"`
  - **통합 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`
  - **구조 계약**: `docker compose run --rm --no-deps backend lint-imports --config .importlinter`

## 시작 전 기준선

계획 1이 끝난 `main`의 상태다. 작업을 시작하기 전에 한 번 확인한다.

- 단위 테스트와 통합 테스트를 합쳐 83개가 통과한다.
- 구조 계약 4종이 통과한다(`Contracts: 4 kept, 0 broken.`).
- `docker compose ps`에서 여섯 서비스가 모두 `running`이다. 아니면 `docker compose up -d`를 먼저 한다.

## 파일 지도

```
_docs/architecture.md · _docs/harness.md          # 조립 규칙·검증 명령 갱신
_docs/decisions/002-hub-port-assembly.md          # 이 계획에서 내린 결정
README.md                                         # 새로 만든다
backend/
├── orm_registry.py                 # ORM 모듈 등록 목록 (alembic·스키마 불일치 테스트가 쓴다)
├── conftest.py                     # 테스트 DB 를 마이그레이션으로 준비
├── main.py                         # 라우터 장착 + 허브 포트 자리 채우기
├── .importlinter                   # 계약 5종 (스포크 상호 독립 추가)
├── alembic/env.py                  # -x db_url 지원
├── alembic/versions/0002_tenancy_tables_and_seed.py · 0003_platform_operators.py
├── scripts/prepare_test_db.py · grant_operator.py · check_shop_flow.sh
├── core/shop_guard.py              # 매장 접근 확인 자리, get_shop_context, require_permission
├── tests/
│   ├── test_schema_drift.py · test_shop_guard.py · test_hub_port_binding.py
│   └── integration/{conftest,test_auth_flow_wiring,test_shop_flow_wiring}.py
└── apps/
    ├── hub/app/
    │   ├── dtos/{shop_context,provisioned_shop,user_profile,membership_summary}.py
    │   └── ports/{shop_access,operator_directory,shop_provisioning,user_directory,membership_directory}_port.py
    ├── auth/                       # 더하는 것만
    │   ├── adapter/outbound/orm/operator_orm.py · pg/operator_pg_repository.py
    │   ├── app/ports/output/operator_repository.py
    │   ├── 슬라이스(HTTP 없음): check_operator · grant_operator · get_user_profiles
    │   ├── dependencies/hub_ports.py               # get_membership_directory 자리
    │   └── get_me 슬라이스에 shops 추가
    ├── tenancy/
    │   ├── domain/entities/{shop,member,invite}.py · value_objects/role_code.py
    │   ├── domain/services/{invite_code,owner_guard}.py · domain/errors.py
    │   ├── app/dtos/ · app/ports/{input,output}/ · app/use_cases/
    │   ├── adapter/inbound/api/{schemas,v1}/ · adapter/inbound/api/error_map.py
    │   ├── adapter/outbound/{orm,pg,mappers,redis}/ · log_tenancy_myself_record_adapter.py
    │   ├── dependencies/{tenancy_wiring,hub_ports,…_provider}.py
    │   └── tests/{domain,app/use_cases,adapter}/
    └── platform_admin/
        ├── domain/errors.py
        ├── app/dtos/ · app/ports/{input,output}/ · app/use_cases/
        ├── adapter/inbound/api/{schemas,v1}/ · error_map.py · adapter/outbound/log_platform_myself_record_adapter.py
        ├── dependencies/{hub_ports,…_provider}.py
        └── tests/{app/use_cases,adapter}/
```

슬라이스와 경로:

| 스포크 | 슬라이스 | 표면 | 인증 |
|---|---|---|---|
| tenancy | `tenancy_myself` | `GET /v1/shops/myself` | 없음 |
| tenancy | `resolve_shop_access` | 없음 (`ShopAccessPort` 구현) | — |
| tenancy | `provision_shop` | 없음 (`ShopProvisioningPort` 구현) | — |
| tenancy | `list_memberships` | 없음 (`MembershipDirectoryPort` 구현) | — |
| tenancy | `accept_invite` | `POST /v1/invites/accept` | 액세스 토큰 |
| tenancy | `create_invite` | `POST /v1/shops/{shop_id}/invites` | `member:manage` |
| tenancy | `list_members` | `GET /v1/shops/{shop_id}/members` | 소속 |
| tenancy | `change_member_role` | `PATCH /v1/shops/{shop_id}/members/{member_id}` | `member:manage` |
| tenancy | `remove_member` | `DELETE /v1/shops/{shop_id}/members/{member_id}` | `member:manage` |
| tenancy | `get_shop` | `GET /v1/shops/{shop_id}/settings` | 소속 |
| tenancy | `update_shop` | `PUT /v1/shops/{shop_id}/settings` | `shop:update` |
| platform_admin | `platform_myself` | `GET /v1/platform/myself` | 운영자 |
| platform_admin | `create_shop` | `POST /v1/platform/shops` | 운영자 |
| auth | `check_operator` | 없음 (`OperatorDirectoryPort` 구현) | — |
| auth | `grant_operator` | 없음 (`scripts/grant_operator.py`가 부른다) | — |
| auth | `get_user_profiles` | 없음 (`UserDirectoryPort` 구현) | — |

전부 API 프로세스(`main.py`)에 장착한다. 인증 프로세스(`auth_main.py`)와 게이트웨이 설정은 이 계획에서 바뀌지 않는다.

---

### Task 1: 테스트 DB를 마이그레이션으로 준비한다

넘김 항목 2·4다. 지금 `db_session` 픽스처는 `Base.metadata.create_all`로 테이블을 만든다. 역할·권한은 Alembic 시드로 넣을 것이므로, 그대로 두면 통합 테스트 DB에 시드가 없다. 테스트 DB를 `alembic upgrade head`로 만들고, 테스트 사이에는 시드 표를 뺀 나머지를 비운다. 마이그레이션이 수기 작성이므로 ORM과 어긋나는지 확인하는 테스트도 함께 둔다.

**Files:**
- Create: `backend/orm_registry.py`
- Create: `backend/scripts/prepare_test_db.py`
- Create: `backend/tests/test_schema_drift.py`
- Modify: `backend/alembic/env.py`
- Modify: `backend/conftest.py` (전체 교체)
- Modify: `_docs/harness.md`

**Interfaces:**
- Consumes: `core.config.DATABASE_URL`, `core.database.Base`
- Produces:
  - `orm_registry` 모듈 — import하면 모든 ORM 모듈이 `Base.metadata`에 등록된다.
  - `scripts.prepare_test_db.TEST_DATABASE_URL: str`, `scripts.prepare_test_db.main() -> None`
  - 픽스처 `migrated_test_db -> str`(세션 범위, 테스트 DB 주소), `db_engine -> AsyncEngine`(테스트마다, 시드 표를 뺀 모든 표를 비운 상태), `db_session -> AsyncSession`(기존과 같은 이름·같은 쓰임새)

- [ ] **Step 1: 작업 브랜치를 만든다**

Run (저장소 루트에서): `git switch -c feat/foundation-2a-tenancy-rbac`
Expected: `Switched to a new branch 'feat/foundation-2a-tenancy-rbac'`

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/tests/test_schema_drift.py`:
```python
"""수기로 쓴 마이그레이션과 ORM 이 같은 스키마를 말하는지 확인한다."""
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

import orm_registry  # noqa: F401 — 모든 ORM 을 메타데이터에 올린다
from core.database import Base

pytestmark = pytest.mark.integration


async def test_마이그레이션과_ORM_이_같은_스키마를_말한다(db_engine):
    async with db_engine.connect() as conn:
        diffs = await conn.run_sync(
            lambda sync_conn: compare_metadata(MigrationContext.configure(sync_conn), Base.metadata)
        )
    assert diffs == []
```

- [ ] **Step 3: 실패를 확인한다**

Run (`infra/`에서): `docker compose run --rm backend pytest tests/test_schema_drift.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'orm_registry'`

- [ ] **Step 4: ORM 등록 목록을 만든다**

`backend/orm_registry.py`:
```python
"""ORM 모듈 등록 목록 — import 하면 모든 테이블이 Base.metadata 에 올라간다.

스포크의 ORM 을 한꺼번에 import 하는 곳은 여기 하나다. alembic/env.py 와 스키마 불일치 테스트가 쓴다.
core 는 스포크를 import 할 수 없어서 core 밖에 둔다. 새 ORM 모듈을 만들면 여기에 한 줄을 더한다.
"""
import auth.adapter.outbound.orm.user_orm  # noqa: F401
```

- [ ] **Step 5: Alembic이 대상 DB를 바꿀 수 있게 한다**

`backend/alembic/env.py` 전체:
```python
"""Alembic 환경 — 비동기 엔진으로 마이그레이션을 실행한다. 오프라인 모드는 쓰지 않는다."""
import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

import orm_registry  # noqa: F401 — 메타데이터 등록
from core.config import DATABASE_URL
from core.database import Base

target_metadata = Base.metadata


def _database_url() -> str:
    """테스트 DB 준비 스크립트는 `-x db_url=…` 로 대상을 바꾼다. 없으면 개발 DB 다."""
    return context.get_x_argument(as_dictionary=True).get("db_url", DATABASE_URL)


def _run(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def _run_async() -> None:
    engine = create_async_engine(_database_url())
    async with engine.connect() as connection:
        await connection.run_sync(_run)
    await engine.dispose()


asyncio.run(_run_async())
```

- [ ] **Step 6: 테스트 DB 준비 스크립트를 쓴다**

`backend/scripts/prepare_test_db.py`:
```python
"""통합 테스트용 데이터베이스 chagocnote_test 를 비우고 마이그레이션으로 다시 만든다.

pytest 가 세션에 한 번 하위 프로세스로 실행한다 (conftest.py 의 migrated_test_db).
하위 프로세스로 돌리는 이유: alembic/env.py 가 asyncio.run 을 쓰므로 pytest 의 이벤트 루프와 섞이면 안 된다.
직접 돌릴 수도 있다: cd infra && docker compose run --rm backend python scripts/prepare_test_db.py
"""
from __future__ import annotations

import asyncio

from alembic.config import main as alembic_main
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import DATABASE_URL

TEST_DB = "chagocnote_test"
TEST_DATABASE_URL = DATABASE_URL.rsplit("/", 1)[0] + "/" + TEST_DB


async def _reset() -> None:
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

    engine = create_async_engine(TEST_DATABASE_URL, isolation_level="AUTOCOMMIT")
    async with engine.connect() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


def main() -> None:
    asyncio.run(_reset())
    alembic_main(["-x", f"db_url={TEST_DATABASE_URL}", "upgrade", "head"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: 공용 픽스처를 바꾼다**

`backend/conftest.py` 전체:
```python
"""pytest 루트 설정 — 통합 테스트용 공용 픽스처."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

# 마이그레이션이 넣은 시드(역할·권한)와 버전 표는 테스트 사이에 비우지 않는다.
_KEEP_TABLES = {"alembic_version", "roles", "permissions", "role_permissions"}


@pytest.fixture(scope="session")
def migrated_test_db() -> str:
    """별도 데이터베이스 chagocnote_test 를 alembic upgrade head 로 다시 만든다. 세션에 한 번."""
    from scripts.prepare_test_db import TEST_DATABASE_URL

    subprocess.run(
        [sys.executable, "scripts/prepare_test_db.py"], check=True, cwd=Path(__file__).parent
    )
    return TEST_DATABASE_URL


@pytest.fixture
async def db_engine(migrated_test_db):
    """테스트 DB 에 붙은 엔진. 테스트마다 시드 표를 뺀 모든 표를 비운다."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(migrated_test_db)
    async with engine.begin() as conn:
        names = (
            await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        ).scalars()
        targets = [f'"{name}"' for name in names if name not in _KEEP_TABLES]
        if targets:
            await conn.execute(
                text("TRUNCATE " + ", ".join(targets) + " RESTART IDENTITY CASCADE")
            )
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    async with async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)() as session:
        yield session
```

- [ ] **Step 8: 새 테스트와 기존 통합 테스트가 통과하는지 확인한다**

Run: `docker compose run --rm backend pytest tests/test_schema_drift.py -q -p no:cacheprovider`
Expected: `1 passed`

Run: 통합 테스트 전체
Expected: 전부 통과한다. 기존 `test_user_pg_repository.py`의 테스트들이 같은 `kakao-100` 신원을 테스트마다 새로 만드는데, 표를 비우지 못했다면 유일 제약 위반으로 실패한다. 통과하면 비우기가 동작하는 것이다.

Run: 단위 테스트 전체
Expected: 전부 통과한다.

- [ ] **Step 9: 하네스 문서를 고친다**

`_docs/harness.md`에서 아래 줄을
```markdown
- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 만들어 쓴다. 개발 데이터를 건드리지 않는다.
```
다음으로 바꾼다.
```markdown
- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`)를 뺀 모든 표를 비운다.
- 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 마이그레이션 결과와 ORM이 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다.
```

- [ ] **Step 10: 커밋**

```bash
git add backend/orm_registry.py backend/scripts/prepare_test_db.py backend/tests/test_schema_drift.py backend/alembic/env.py backend/conftest.py _docs/harness.md
git commit -m "test(harness): 통합 테스트 DB를 마이그레이션으로 만들고 스키마 불일치를 검사한다"
```

---

### Task 2: 실제 배선을 통과하는 통합 테스트

넘김 항목 1이다. 지금까지 프로바이더 → `auth_wiring` → `get_db` 커밋 → Redis 구간은 `check_auth_flow.sh` 수동 실행으로만 확인했다. 두 프로세스의 실제 앱 객체(`auth_main.app`, `main.app`)에 붙어 흐름을 도는 테스트를 둔다. 이후 작업의 매장 흐름 테스트도 이 픽스처를 쓴다.

인증 프로세스는 import 시점에 개인키를 요구한다. 테스트는 개발용 실제 키를 쓰지 않고 매번 새 키 쌍을 만들어 넣는다(`monkeypatch.setenv`로 개인키를, `core.security.JWT_PUBLIC_KEY`를 바꿔 공개키를 넣는다). DB는 테스트 DB로, Redis는 15번 DB로 돌린다.

**이 작업은 이미 있는 동작을 고정하는 테스트다. 프로덕션 코드를 바꾸지 않으며, 테스트는 쓰자마자 통과해야 한다.** 실패한다면 실제 배선 결함을 찾은 것이다. 테스트를 고쳐서 통과시키지 말고 원인을 조사해 보고한다.

**Files:**
- Create: `backend/tests/integration/__init__.py` (빈 파일)
- Create: `backend/tests/integration/support.py`
- Create: `backend/tests/integration/conftest.py`
- Create: `backend/tests/integration/test_auth_flow_wiring.py`

**Interfaces:**
- Consumes: Task 1의 `db_engine`, `auth.tests.helpers.keys.make_rsa_keypair() -> tuple[str, str, dict]`(개인키 PEM, 공개키 PEM, JWK), `auth_main.app`, `main.app`
- Produces (`backend/tests/integration/support.py`와 `conftest.py`):
  - `class Wired` — 필드 `auth: httpx.AsyncClient`(인증 프로세스), `api: httpx.AsyncClient`(API 프로세스), `engine: AsyncEngine`. 메서드 `async login(name: str) -> dict`(dev 로그인 응답 본문), `async execute(sql: str, **params) -> None`(테스트 DB에 SQL 한 줄 실행 후 커밋)
  - `bearer(token: str) -> dict[str, str]`
  - 픽스처 `wired -> Wired` (`conftest.py`)

- [ ] **Step 1: 픽스처를 쓴다**

`backend/tests/integration/support.py`:
```python
"""실제 배선 통합 테스트가 함께 쓰는 도우미."""
from __future__ import annotations

from dataclasses import dataclass

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class Wired:
    auth: AsyncClient   # 인증 프로세스 (auth_main.app)
    api: AsyncClient    # API 프로세스 (main.app)
    engine: AsyncEngine

    async def login(self, name: str) -> dict:
        response = await self.auth.post("/v1/auth/social", json={"provider": "dev", "token": name})
        assert response.status_code == 200, response.text
        return response.json()

    async def execute(self, sql: str, **params) -> None:
        async with self.engine.begin() as conn:
            await conn.execute(text(sql), params)
```

`backend/tests/integration/conftest.py`:
```python
"""두 프로세스의 실제 앱 객체에 붙는 픽스처 — 프로바이더·DB 커밋·Redis 까지 실제 배선을 통과한다."""
from __future__ import annotations

import base64

import pytest
from httpx import ASGITransport, AsyncClient
from redis.asyncio import from_url
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.tests.helpers.keys import make_rsa_keypair
from tests.integration.support import Wired


@pytest.fixture
async def wired(db_engine, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    # auth_main 은 import 시점에 개인키를 요구한다. 개발용 실제 키 대신 매번 새로 만든 키를 넣는다.
    monkeypatch.setenv("JWT_PRIVATE_KEY_B64", base64.b64encode(private_pem.encode()).decode())

    import core.auth_config
    import core.config
    import core.database
    import core.redis
    import core.security
    from auth.dependencies import auth_wiring

    monkeypatch.setattr(core.auth_config, "JWT_PRIVATE_KEY", private_pem)
    monkeypatch.setattr(core.security, "JWT_PUBLIC_KEY", public_pem)
    monkeypatch.setattr(core.config, "APP_ENV", "dev")
    monkeypatch.setattr(auth_wiring, "_resolver", None)  # APP_ENV 를 바꿨으니 제공자 목록을 다시 만들게 한다
    monkeypatch.setattr(core.database, "engine", db_engine)
    monkeypatch.setattr(
        core.database,
        "_session_factory",
        async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False),
    )
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    redis = from_url(core.config.REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await redis.flushdb()
    monkeypatch.setattr(core.redis, "_client", redis)

    import auth_main
    import main

    async with (
        AsyncClient(transport=ASGITransport(app=auth_main.app), base_url="http://auth") as auth,
        AsyncClient(transport=ASGITransport(app=main.app), base_url="http://api") as api,
    ):
        yield Wired(auth=auth, api=api, engine=db_engine)
    await redis.flushdb()
    await redis.aclose()
```

- [ ] **Step 2: 인증 흐름 테스트를 쓴다**

`backend/tests/integration/test_auth_flow_wiring.py`:
```python
import pytest

from tests.integration.support import bearer

pytestmark = pytest.mark.integration


async def _refresh(wired, token):
    return await wired.auth.post("/v1/auth/refresh", json={"refresh_token": token})


async def test_로그인부터_로그아웃까지_실제_배선으로_돈다(wired):
    login = await wired.login("두부보호자")
    assert login["is_new_user"] is True

    me = await wired.api.get("/v1/me", headers=bearer(login["access_token"]))
    assert me.status_code == 200
    assert me.json()["display_name"] == "두부보호자"
    assert me.json()["identities"] == ["dev"]

    rotated = await _refresh(wired, login["refresh_token"])
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != login["refresh_token"]

    reused = await _refresh(wired, login["refresh_token"])
    assert (reused.status_code, reused.json()["code"]) == (401, "UNAUTHENTICATED")
    # 재사용이 감지되면 새로 받은 토큰도 함께 폐기된다.
    assert (await _refresh(wired, rotated.json()["refresh_token"])).status_code == 401

    again = await wired.login("두부보호자")
    assert again["is_new_user"] is False
    logout = await wired.auth.post("/v1/auth/logout", json={"refresh_token": again["refresh_token"]})
    assert logout.status_code == 204
    assert (await _refresh(wired, again["refresh_token"])).status_code == 401


async def test_토큰_없이_내_정보를_부르면_401_이다(wired):
    response = await wired.api.get("/v1/me")
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


async def test_지원하지_않는_제공자는_400_이다(wired):
    response = await wired.auth.post("/v1/auth/social", json={"provider": "naver", "token": "x"})
    assert (response.status_code, response.json()["code"]) == (400, "PROVIDER_NOT_SUPPORTED")


async def test_요청_형식이_틀리면_422_와_통일된_본문이다(wired):
    response = await wired.auth.post("/v1/auth/social", json={"provider": "dev"})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_모르는_리프레시_토큰은_401_이다(wired):
    response = await _refresh(wired, "never-issued")
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")


async def test_정지된_유저는_갱신도_내_정보도_403_이다(wired):
    login = await wired.login("정지될유저")
    await wired.execute("UPDATE users SET suspended_at = now() WHERE id = :id", id=login["user_id"])

    refreshed = await _refresh(wired, login["refresh_token"])
    assert (refreshed.status_code, refreshed.json()["code"]) == (403, "ACCOUNT_SUSPENDED")
    me = await wired.api.get("/v1/me", headers=bearer(login["access_token"]))
    assert (me.status_code, me.json()["code"]) == (403, "ACCOUNT_SUSPENDED")
```

- [ ] **Step 3: 통과를 확인한다**

Run: `docker compose run --rm backend pytest tests/integration -q -p no:cacheprovider`
Expected: `6 passed`. 실패하면 테스트를 고치지 말고 원인을 조사해 보고한다.

Run: 단위 테스트 전체 (`-m "not integration and not network"`가 새 테스트를 빼는지 확인)
Expected: 통과하고, 테스트 수가 Task 1 이후와 같다.

- [ ] **Step 4: 커밋**

```bash
git add backend/tests/integration
git commit -m "test(auth): 두 프로세스의 실제 배선을 통과하는 인증 흐름 통합 테스트"
```

---

### Task 3: tenancy 스포크 골격, 다섯 번째 구조 계약, 조립 규칙

두 번째 스포크가 생기므로 "스포크 상호 독립" 계약을 더한다. 넘김 항목 3(스포크 간 조립 위치)과 12(Factory 표기)의 결정을 문서로 남긴다. 슬라이스는 자기소개 하나만 만든다.

**Files:**
- Create: `backend/apps/tenancy/` 아래 패키지 뼈대 (Step 1의 명령)
- Create: `backend/apps/tenancy/app/dtos/tenancy_myself_dto.py`
- Create: `backend/apps/tenancy/app/ports/input/tenancy_myself_use_case.py`
- Create: `backend/apps/tenancy/app/ports/output/tenancy_myself_record_port.py`
- Create: `backend/apps/tenancy/app/use_cases/tenancy_myself_interactor.py`
- Create: `backend/apps/tenancy/adapter/outbound/log_tenancy_myself_record_adapter.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/schemas/tenancy_myself_schema.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/v1/tenancy_myself_router.py`
- Create: `backend/apps/tenancy/dependencies/tenancy_myself_provider.py`
- Create: `backend/apps/tenancy/_docs/CLAUDE.md`, 심볼릭 링크 `backend/apps/tenancy/CLAUDE.md`
- Create: `_docs/decisions/002-hub-port-assembly.md`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_tenancy_myself_interactor.py`, `backend/apps/tenancy/tests/adapter/test_tenancy_myself_router.py`
- Modify: `backend/.importlinter` (전체 교체), `backend/main.py`, `_docs/architecture.md`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `tenancy.adapter.inbound.api.v1.tenancy_myself_router.tenancy_myself_router` (`GET /v1/shops/myself`)
  - 구조 계약 5종이 통과하는 상태. 이후 모든 작업은 이 계약을 지켜야 한다.

- [ ] **Step 1: 패키지 뼈대를 만든다**

Run (저장소 루트에서):
```bash
cd backend/apps
mkdir -p tenancy/domain/{entities,value_objects,services} \
  tenancy/app/{dtos,use_cases} tenancy/app/ports/{input,output} \
  tenancy/adapter/inbound/api/{schemas,v1} \
  tenancy/adapter/outbound/{orm,pg,mappers,redis} \
  tenancy/dependencies tenancy/tests/app/use_cases tenancy/tests/adapter tenancy/tests/domain tenancy/_docs
find tenancy -type d -not -name _docs -exec touch {}/__init__.py \;
find tenancy -name __init__.py | wc -l
cd ../..
```
Expected: `27`

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_tenancy_myself_interactor.py`:
```python
from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery
from tenancy.app.use_cases.tenancy_myself_interactor import TenancyMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await TenancyMyselfInteractor(record=record).introduce_myself(
        TenancyMyselfQuery(id=2, name="매장 (tenancy)")
    )
    assert result.id == 2
    assert "/v1/invites/accept" in result.introduction
    assert "/v1/shops/{shop_id}/members" in result.introduction
    assert "사장" in result.introduction
    assert record.records[0][0] == "introduce_myself"
```

`backend/apps/tenancy/tests/adapter/test_tenancy_myself_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router


async def test_myself_는_인증_없이_200과_자기소개를_돌려준다():
    app = FastAPI()
    app.include_router(tenancy_myself_router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/shops/myself")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "매장 (tenancy)"
    assert "/v1/invites/accept" in body["introduction"]
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.dtos.tenancy_myself_dto'`

- [ ] **Step 4: 슬라이스를 구현한다**

`backend/apps/tenancy/app/dtos/tenancy_myself_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class TenancyMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class TenancyMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/tenancy/app/ports/input/tenancy_myself_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery, TenancyMyselfResponse


class TenancyMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: TenancyMyselfQuery) -> TenancyMyselfResponse: ...
```

`backend/apps/tenancy/app/ports/output/tenancy_myself_record_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class TenancyMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/tenancy/app/use_cases/tenancy_myself_interactor.py`:
```python
from __future__ import annotations

from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery, TenancyMyselfResponse
from tenancy.app.ports.input.tenancy_myself_use_case import TenancyMyselfUseCase
from tenancy.app.ports.output.tenancy_myself_record_port import TenancyMyselfRecordPort


class TenancyMyselfInteractor(TenancyMyselfUseCase):
    def __init__(self, record: TenancyMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: TenancyMyselfQuery) -> TenancyMyselfResponse:
        await self._record.record(
            subject="introduce_myself", note=f"{query.name} 자기소개 조회"
        )
        return TenancyMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장과 매장별 역할·권한, 소속, 초대를 관리합니다. "
                "플랫폼 운영자가 매장을 개설하면 사장용 초대 코드가 나오고, "
                "POST /v1/invites/accept 에 코드를 넣은 유저가 그 매장의 멤버가 됩니다. "
                "GET /v1/shops/{shop_id}/members 는 멤버 목록을, "
                "POST /v1/shops/{shop_id}/invites 는 직원용 초대 코드를 돌려줍니다. "
                "PATCH·DELETE /v1/shops/{shop_id}/members/{member_id} 는 역할 변경과 내보내기입니다. "
                "GET·PUT /v1/shops/{shop_id}/settings 는 매장 정보 조회와 수정입니다. "
                "매장 경로는 매 요청마다 소속과 권한을 DB 에서 확인하며 소속이 아니면 403 입니다. "
                "초대 코드는 8자리이고 해시만 저장하며 7일 뒤 만료되고 입력 시도는 유저당 분당 5회입니다. "
                "매장에는 사장이 항상 한 명 이상 있어야 합니다."
            ),
        )
```

`backend/apps/tenancy/adapter/outbound/log_tenancy_myself_record_adapter.py`:
```python
from __future__ import annotations

import logging

from tenancy.app.ports.output.tenancy_myself_record_port import TenancyMyselfRecordPort

logger = logging.getLogger(__name__)


class LogTenancyMyselfRecordAdapter(TenancyMyselfRecordPort):
    """기록을 로그로 남기는 구현. 영속 기록이 필요해지면 PG 어댑터로 바꾼다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[tenancy-myself-record] %s | %s", subject, note)
```

`backend/apps/tenancy/adapter/inbound/api/schemas/tenancy_myself_schema.py`:
```python
from pydantic import BaseModel


class TenancyMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/tenancy/dependencies/tenancy_myself_provider.py`:
```python
from __future__ import annotations

from tenancy.adapter.outbound.log_tenancy_myself_record_adapter import (
    LogTenancyMyselfRecordAdapter,
)
from tenancy.app.ports.input.tenancy_myself_use_case import TenancyMyselfUseCase
from tenancy.app.use_cases.tenancy_myself_interactor import TenancyMyselfInteractor


def get_tenancy_myself_use_case() -> TenancyMyselfUseCase:
    return TenancyMyselfInteractor(record=LogTenancyMyselfRecordAdapter())
```

`backend/apps/tenancy/adapter/inbound/api/v1/tenancy_myself_router.py`:
```python
from fastapi import APIRouter, Depends

from tenancy.adapter.inbound.api.schemas.tenancy_myself_schema import TenancyMyselfResponseSchema
from tenancy.app.dtos.tenancy_myself_dto import TenancyMyselfQuery
from tenancy.app.ports.input.tenancy_myself_use_case import TenancyMyselfUseCase
from tenancy.dependencies.tenancy_myself_provider import get_tenancy_myself_use_case

tenancy_myself_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@tenancy_myself_router.get("/myself", response_model=TenancyMyselfResponseSchema)
async def introduce_myself(
    use_case: TenancyMyselfUseCase = Depends(get_tenancy_myself_use_case),
) -> TenancyMyselfResponseSchema:
    result = await use_case.introduce_myself(TenancyMyselfQuery(id=2, name="매장 (tenancy)"))
    return TenancyMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
```

- [ ] **Step 5: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy -q -p no:cacheprovider`
Expected: `2 passed`

- [ ] **Step 6: API 프로세스에 장착한다**

`backend/main.py`에서 아래 import 줄 다음에
```python
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
```
한 줄을 더한다.
```python
from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router
```
그리고 `app.include_router(get_me_router)` 다음 줄에 더한다.
```python
app.include_router(tenancy_myself_router)
```

- [ ] **Step 7: 구조 계약을 5종으로 늘린다**

`backend/.importlinter` 전체:
```ini
# =============================================================================
# import-linter — 차곡노트 백엔드 구조 계약
# =============================================================================
# (1) 앱 내부  — 헥사고날: adapter → app → domain (역방향 금지)
# (2) 앱 사이  — 허브-스포크: 스포크끼리 직접 참조 금지, 허브는 스포크를 모른다
#
# 실행: cd infra && docker compose run --rm --no-deps backend lint-imports --config .importlinter
#
# 스포크를 새로 만들면 root_packages 와 다섯 계약 모두에 이름을 더한다.
# 스포크 사이의 조립은 진입점(main.py, auth_main.py)이 한다. dependencies/ 도 다른 스포크를 import 하지 않는다.
# =============================================================================

[importlinter]
root_packages =
    hub
    auth
    tenancy
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
    tenancy

[importlinter:contract:spoke-independence]
name = 스포크 상호 독립 (스포크끼리 import 하지 않는다)
type = independence
modules =
    auth
    tenancy

[importlinter:contract:framework-isolation]
name = 프레임워크 격리 (app·domain 은 웹·DB·외부 통신 라이브러리를 모른다)
type = forbidden
source_modules =
    hub.app
    auth.app
    auth.domain
    tenancy.app
    tenancy.domain
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
    tenancy.domain
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
    tenancy
```

Run: 구조 계약
Expected: `Contracts: 5 kept, 0 broken.`

- [ ] **Step 8: 앱 문서와 심볼릭 링크를 만든다**

`backend/apps/tenancy/_docs/CLAUDE.md`:
```markdown
# tenancy — 매장, 역할·권한, 소속, 초대

소유 데이터: `shops`, `roles`, `permissions`, `role_permissions`, `shop_members`, `shop_invites`, Redis의 초대 코드 입력 횟수.

- 사장·직원은 계정 종류가 아니라 `shop_members`의 행이다. 같은 유저가 여러 매장에 속할 수 있다.
- `shop_members.user_id`는 auth의 유저 ID지만 외래 키를 걸지 않는다. 이름과 사진은 허브의 `UserDirectoryPort`로 받는다.
- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 컨텍스트가 없는 경로(소속 확인, 초대 수락, 매장 개설, 유저 기준 소속 목록)만 예외다.
- 역할과 권한은 마이그레이션 시드다. 코드에서 만들거나 고치지 않는다.
- 매장에는 사장이 한 명 이상 있어야 한다. 사장을 낮추거나 내보내기 전에 `count_owners`로 사장 행을 잠그고 센다.
- 초대 코드는 원문을 저장하지 않는다. 8자리(헷갈리는 글자 I·O·0·1 제외), SHA-256 해시 저장, 7일 만료, 1회 사용.
- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `resolve_shop_access`, `provision_shop`, `list_memberships`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
```

Run (저장소 루트에서): `cd backend/apps/tenancy && ln -s _docs/CLAUDE.md CLAUDE.md && cd ../../.. && ls -l backend/apps/tenancy/CLAUDE.md`
Expected: `… backend/apps/tenancy/CLAUDE.md -> _docs/CLAUDE.md`

- [ ] **Step 9: 결정 기록을 남긴다**

`_docs/decisions/002-hub-port-assembly.md`:
```markdown
# 002 — 허브 포트 조립 위치, Factory 표기, 계획 2 분할

- 날짜: 2026-09-20
- 근거: `001-plan1-review-carryover.md`의 3번·12번 항목, 계획 2 작성 중 사용자 결정

## 허브 포트 구현은 진입점이 꽂는다

`get_me`는 tenancy가 구현한 `MembershipDirectoryPort`가, tenancy의 멤버 목록은 auth가 구현한 `UserDirectoryPort`가 필요하다. `auth/dependencies/`가 `tenancy.adapter…`를 import하면 "스포크 상호 독립" 계약을 어긴다.

검토한 안은 셋이다. ① 진입점에서 조립 ② 허브에 레지스트리 ③ `*.dependencies`를 계약의 예외로 둔다. **①로 정했다.**

- 소비하는 스포크는 `dependencies/hub_ports.py`에 "자리" 함수를 둔다. 자리는 호출되면 `RuntimeError`를 던진다.
- `backend/main.py`(필요해지면 `auth_main.py`)가 `app.dependency_overrides[자리] = 구현 프로바이더`로 채운다. 진입점은 이미 모든 스포크를 import하는 유일한 곳이다.
- 구현 프로바이더가 `DbSession`을 받으면 같은 요청의 세션을 공유한다. 스포크를 넘는 작업도 한 트랜잭션으로 묶인다.
- 매장 접근 확인(`ShopAccessPort`) 자리는 모든 매장 범위 스포크가 쓰므로 `core/shop_guard.py`에 둔다. core가 허브의 추상(ABC·DTO)을 import하는 것은 허용한다. core가 스포크를 import하는 것은 여전히 금지다.
- 자리를 채우지 않은 실수는 `tests/test_hub_port_binding.py`와 실제 배선 통합 테스트가 잡는다.

②를 버린 이유: 허브가 "포트와 DTO만 가진다"는 규칙에서 벗어나 상태를 갖게 되고, 요청 단위 DB 세션을 넘길 방법을 따로 만들어야 한다. ③을 버린 이유: 스포크 간 결합이 조립 코드에 숨고 계약이 그만큼 약해진다.

## `factory/` 폴더의 패턴 표기를 "Factory"로 완화한다

`auth/adapter/outbound/factory/`의 `SocialProviderFactory`는 제공자별 인스턴스를 담아 두고 이름으로 골라 주는 객체이고, `build_social_provider_factory`는 설정을 보고 그 객체를 만드는 단순 팩토리다. GoF의 Factory Method(하위 클래스가 생성을 결정)와는 다르다. 폴더 이름과 코드는 그대로 두고 대응표의 패턴 칸만 "Factory"로 고친다. 제공자마다 Creator 클래스를 두는 구조로 바꾸면 클래스만 늘고 얻는 기능이 없다.

## 계획 2를 둘로 나눈다

계획 2(매장·RBAC·계정 연결·탈퇴)를 2-1(매장과 매장별 RBAC)과 2-2(계정 연결·해제, 회원 탈퇴, 제공자 연결 끊기, 리프레시 토큰 세대 번호)로 나눴다. 2-2는 2-1을 구현한 뒤 실제 코드를 보고 쓴다. `MembershipLifecyclePort`는 첫 소비자(`withdraw`)가 생기는 2-2에서 만든다.
```

- [ ] **Step 10: 아키텍처 문서를 고친다**

`_docs/architecture.md`에서 세 곳을 고친다.

(1) "허브-스포크" 절의 마지막 항목(`core/`는 인프라 공유…로 시작하는 줄) 다음에 두 항목을 더한다.
```markdown
- `core/`는 허브의 추상(포트 ABC와 DTO)을 import할 수 있다. 스포크는 import할 수 없다.
- 허브 포트를 구현하는 슬라이스는 그 포트를 입력 포트로 삼는다. 인터랙터가 허브 포트 ABC를 직접 상속하고, HTTP 표면이 없으므로 schema와 router를 생략한다.
```

(2) "프로세스 배치" 절 앞에 새 절을 넣는다.
```markdown
## 허브 포트 조립

스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트가 필요하면 다음과 같이 한다.

1. 소비하는 스포크의 `dependencies/hub_ports.py`에 "자리" 함수를 둔다. 반환 타입은 허브 포트이고, 호출되면 `RuntimeError`를 던진다.
2. 프로바이더는 `Depends(자리)`로 포트를 받는다.
3. 진입점(`main.py`, `auth_main.py`)이 `app.dependency_overrides[자리] = 구현 스포크의 프로바이더`로 채운다.

매장 접근 확인(`ShopAccessPort`) 자리는 모든 매장 범위 스포크가 쓰므로 `core/shop_guard.py`에 있다. 매장 범위의 라우터는 `Depends(get_shop_context)`(소속만 확인) 또는 `Depends(require_permission("…"))`(권한까지 확인)로 `ShopContext`를 받는다. 결정 경위는 `_docs/decisions/002-hub-port-assembly.md`에 있다.
```

(3) GoF 대응표의 `factory/` 줄을 바꾼다.
```markdown
| `auth/adapter/outbound/factory/` | Factory | 설정에 따라 제공자 구현을 만들어 담아 두고 이름으로 골라 준다 |
```

- [ ] **Step 11: 전체 검증**

Run: 단위 테스트 전체 → 통과. 구조 계약 → `Contracts: 5 kept, 0 broken.`

Run (uvicorn 이 `--reload` 로 돌고 있어 재기동은 필요 없다): `curl -sf --retry 5 --retry-delay 1 --retry-all-errors http://127.0.0.1:8080/v1/shops/myself | head -c 120`
Expected: `{"id":2,"name":"매장 (tenancy)","introduction":"매장과 매장별 역할·권한…` 으로 시작하는 본문

- [ ] **Step 12: 커밋**

```bash
git add backend/apps/tenancy backend/.importlinter backend/main.py _docs/architecture.md _docs/decisions/002-hub-port-assembly.md
git commit -m "feat(tenancy): 스포크 골격과 자기소개 슬라이스, 스포크 상호 독립 계약"
```

---

### Task 4: tenancy 도메인, 테이블, 역할·권한 시드

**Files:**
- Create: `backend/apps/tenancy/domain/errors.py`
- Create: `backend/apps/tenancy/domain/value_objects/role_code.py`
- Create: `backend/apps/tenancy/domain/entities/shop.py`, `member.py`, `invite.py`
- Create: `backend/apps/tenancy/domain/services/invite_code.py`, `owner_guard.py`
- Create: `backend/apps/tenancy/adapter/outbound/orm/tenancy_orm.py`
- Create: `backend/alembic/versions/0002_tenancy_tables_and_seed.py`
- Modify: `backend/orm_registry.py`
- Test: `backend/apps/tenancy/tests/domain/test_invite.py`, `test_invite_code.py`, `test_owner_guard.py`, `backend/apps/tenancy/tests/adapter/test_tenancy_seed.py`

**Interfaces:**
- Consumes: Task 1의 `db_session`, `orm_registry`, 스키마 불일치 테스트
- Produces:
  - `tenancy.domain.value_objects.role_code.RoleCode` — `OWNER = "owner"`, `STAFF = "staff"` (`str, Enum`)
  - `tenancy.domain.entities.shop.Shop(id, name, business_type, phone, address, timezone, suspended_at, closed_at)` + `is_closed: bool`
  - `tenancy.domain.entities.member.Member(id, shop_id, user_id, role: RoleCode, joined_at: datetime)`
  - `tenancy.domain.entities.invite.Invite(id, shop_id, role: RoleCode, expires_at, max_uses, used_count, revoked_at)` + `ensure_usable(now: datetime) -> None`
  - `tenancy.domain.services.invite_code`: `INVITE_TTL = timedelta(days=7)`, `generate_invite_code() -> str`, `normalize_invite_code(raw: str) -> str`, `hash_invite_code(code: str) -> str`
  - `tenancy.domain.services.owner_guard.ensure_owner_remains(owner_count: int) -> None`
  - `tenancy.domain.errors`: `TenancyError`(바탕, `code` 속성), `NotAMemberError`, `ShopClosedError`, `ShopSuspendedError`, `LastOwnerError`, `MemberNotFoundError`, `AlreadyMemberError`, `InviteInvalidError`, `InviteExpiredError`, `InviteExhaustedError`, `TooManyAttemptsError`
  - ORM `tenancy.adapter.outbound.orm.tenancy_orm`: `ShopOrm`, `RoleOrm`, `PermissionOrm`, `RolePermissionOrm`, `ShopMemberOrm`, `ShopInviteOrm`
  - 마이그레이션 `0002` — 테이블 6개와 시드(역할 2, 권한 9, 사장 9개·직원 4개 연결)

- [ ] **Step 1: 실패하는 도메인 테스트를 쓴다**

`backend/apps/tenancy/tests/domain/test_invite.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest

from tenancy.domain.entities.invite import Invite
from tenancy.domain.errors import InviteExhaustedError, InviteExpiredError, InviteInvalidError
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


def _invite(**overrides):
    base = dict(id=1, shop_id=1, role=RoleCode.STAFF, expires_at=NOW + timedelta(days=7),
                max_uses=1, used_count=0, revoked_at=None)
    return Invite(**{**base, **overrides})


def test_기한_안이고_횟수가_남았으면_쓸_수_있다():
    _invite().ensure_usable(NOW)


def test_만료_시각이_되면_INVITE_EXPIRED_다():
    with pytest.raises(InviteExpiredError):
        _invite(expires_at=NOW).ensure_usable(NOW)


def test_사용_횟수를_다_쓰면_INVITE_EXHAUSTED_다():
    with pytest.raises(InviteExhaustedError):
        _invite(used_count=1).ensure_usable(NOW)


def test_무효화된_초대는_INVITE_INVALID_다():
    with pytest.raises(InviteInvalidError):
        _invite(revoked_at=NOW - timedelta(hours=1)).ensure_usable(NOW)
```

`backend/apps/tenancy/tests/domain/test_invite_code.py`:
```python
from tenancy.domain.services.invite_code import (
    generate_invite_code,
    hash_invite_code,
    normalize_invite_code,
)


def test_코드는_8자리이고_헷갈리는_글자가_없다():
    for _ in range(200):
        code = generate_invite_code()
        assert len(code) == 8
        assert not set(code) & set("IO01")
        assert code.isalnum() and code == code.upper()


def test_입력한_코드는_공백과_하이픈을_빼고_대문자로_맞춘다():
    assert normalize_invite_code("  abcd-2345 ") == "ABCD2345"


def test_해시는_입력_모양이_달라도_같고_원문을_담지_않는다():
    digest = hash_invite_code("ABCD2345")
    assert digest == hash_invite_code(" abcd-2345")
    assert len(digest) == 64 and "ABCD2345" not in digest
```

`backend/apps/tenancy/tests/domain/test_owner_guard.py`:
```python
import pytest

from tenancy.domain.errors import LastOwnerError
from tenancy.domain.services.owner_guard import ensure_owner_remains


def test_사장이_한_명뿐이면_LAST_OWNER_다():
    with pytest.raises(LastOwnerError):
        ensure_owner_remains(owner_count=1)


def test_사장이_둘_이상이면_통과한다():
    ensure_owner_remains(owner_count=2)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/domain -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.domain.entities.invite'`

- [ ] **Step 3: 도메인을 구현한다**

`backend/apps/tenancy/domain/errors.py`:
```python
class TenancyError(Exception):
    """tenancy 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "TENANCY_ERROR"


class NotAMemberError(TenancyError):
    code = "NOT_A_MEMBER"


class ShopClosedError(TenancyError):
    code = "SHOP_CLOSED"


class ShopSuspendedError(TenancyError):
    code = "SHOP_SUSPENDED"


class LastOwnerError(TenancyError):
    code = "LAST_OWNER"


class MemberNotFoundError(TenancyError):
    code = "MEMBER_NOT_FOUND"


class AlreadyMemberError(TenancyError):
    code = "ALREADY_A_MEMBER"


class InviteInvalidError(TenancyError):
    code = "INVITE_INVALID"


class InviteExpiredError(TenancyError):
    code = "INVITE_EXPIRED"


class InviteExhaustedError(TenancyError):
    code = "INVITE_EXHAUSTED"


class TooManyAttemptsError(TenancyError):
    code = "TOO_MANY_ATTEMPTS"
```

`backend/apps/tenancy/domain/value_objects/role_code.py`:
```python
from enum import Enum


class RoleCode(str, Enum):
    OWNER = "owner"
    STAFF = "staff"
```

`backend/apps/tenancy/domain/entities/shop.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Shop:
    id: int
    name: str
    business_type: str
    phone: str | None
    address: str | None
    timezone: str
    suspended_at: datetime | None
    closed_at: datetime | None

    @property
    def is_closed(self) -> bool:
        return self.closed_at is not None
```

`backend/apps/tenancy/domain/entities/member.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tenancy.domain.value_objects.role_code import RoleCode


@dataclass(frozen=True)
class Member:
    """매장에 지금 속해 있는 멤버. 내보낸 멤버는 이 타입으로 나오지 않는다."""

    id: int
    shop_id: int
    user_id: int
    role: RoleCode
    joined_at: datetime
```

`backend/apps/tenancy/domain/entities/invite.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tenancy.domain.errors import InviteExhaustedError, InviteExpiredError, InviteInvalidError
from tenancy.domain.value_objects.role_code import RoleCode


@dataclass(frozen=True)
class Invite:
    id: int
    shop_id: int
    role: RoleCode
    expires_at: datetime
    max_uses: int
    used_count: int
    revoked_at: datetime | None

    def ensure_usable(self, now: datetime) -> None:
        if self.revoked_at is not None:
            raise InviteInvalidError("사용할 수 없는 초대 코드입니다.")
        if now >= self.expires_at:
            raise InviteExpiredError("만료된 초대 코드입니다. 새 코드를 받아 주세요.")
        if self.used_count >= self.max_uses:
            raise InviteExhaustedError("이미 사용된 초대 코드입니다.")
```

`backend/apps/tenancy/domain/services/invite_code.py`:
```python
"""초대 코드 — 사람이 보고 입력하는 8자리. DB 에는 해시만 둔다."""
from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # 헷갈리는 I·O·0·1 을 뺐다
_LENGTH = 8
INVITE_TTL = timedelta(days=7)


def generate_invite_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))


def normalize_invite_code(raw: str) -> str:
    """사람이 입력한 모양(소문자, 공백, 하이픈)을 저장할 때의 모양으로 맞춘다."""
    return "".join(ch for ch in raw.upper() if ch.isalnum())


def hash_invite_code(code: str) -> str:
    return hashlib.sha256(normalize_invite_code(code).encode()).hexdigest()
```

`backend/apps/tenancy/domain/services/owner_guard.py`:
```python
from __future__ import annotations

from tenancy.domain.errors import LastOwnerError


def ensure_owner_remains(owner_count: int) -> None:
    """사장 한 명이 자리에서 빠지기 직전(역할 낮춤·내보내기)에 부른다. owner_count 는 빠지기 전의 사장 수다."""
    if owner_count <= 1:
        raise LastOwnerError(
            "매장에는 사장이 한 명 이상 있어야 합니다. 다른 멤버를 먼저 사장으로 지정해 주세요."
        )
```

- [ ] **Step 4: 도메인 테스트 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/domain -q -p no:cacheprovider`
Expected: `9 passed`

- [ ] **Step 5: 실패하는 시드 테스트를 쓴다**

`backend/apps/tenancy/tests/adapter/test_tenancy_seed.py`:
```python
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration

_STAFF = {"reservation:write", "customer:write", "record:write", "sales:write"}
_OWNER_ONLY = {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}


async def test_역할과_권한_시드가_설계대로_들어_있다(db_session):
    rows = (
        await db_session.execute(
            text(
                "SELECT r.code, p.code FROM role_permissions rp "
                "JOIN roles r ON r.id = rp.role_id JOIN permissions p ON p.id = rp.permission_id"
            )
        )
    ).all()
    assert {p for r, p in rows if r == "owner"} == _STAFF | _OWNER_ONLY
    assert {p for r, p in rows if r == "staff"} == _STAFF
```

Run: `docker compose run --rm backend pytest apps/tenancy/tests/adapter/test_tenancy_seed.py -q -p no:cacheprovider`
Expected: FAIL — `relation "role_permissions" does not exist`

- [ ] **Step 6: ORM을 쓴다**

`backend/apps/tenancy/adapter/outbound/orm/tenancy_orm.py`:
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class ShopOrm(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    business_type: Mapped[str] = mapped_column(String(30), server_default="pet_grooming")
    phone: Mapped[str | None] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(255))
    timezone: Mapped[str] = mapped_column(String(50), server_default="Asia/Seoul")
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RoleOrm(Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("code", name="uq_roles_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PermissionOrm(Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("code", name="uq_permissions_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class RolePermissionOrm(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShopMemberOrm(Base):
    __tablename__ = "shop_members"
    __table_args__ = (
        # 내보낸 멤버의 행은 남긴다. 유일해야 하는 것은 지금 속해 있는 행뿐이다.
        Index(
            "uq_shop_members_active", "shop_id", "user_id",
            unique=True, postgresql_where=text("removed_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    # auth 스포크의 유저 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ShopInviteOrm(Base):
    __tablename__ = "shop_invites"
    __table_args__ = (UniqueConstraint("code_hash", name="uq_shop_invites_code_hash"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    code_hash: Mapped[str] = mapped_column(String(64))
    # 운영자가 매장을 개설하며 만든 사장용 첫 초대는 만든 멤버가 없다.
    created_by_member_id: Mapped[int | None] = mapped_column(ForeignKey("shop_members.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int] = mapped_column(Integer, server_default="1")
    used_count: Mapped[int] = mapped_column(Integer, server_default="0")
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

`backend/orm_registry.py`의 마지막 줄 다음에 더한다.
```python
import tenancy.adapter.outbound.orm.tenancy_orm  # noqa: F401
```

- [ ] **Step 7: 마이그레이션을 쓴다**

`backend/alembic/versions/0002_tenancy_tables_and_seed.py`:
```python
"""매장, 역할·권한, 소속, 초대 + 역할·권한 시드

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.create_table(
        "shops",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("business_type", sa.String(30), server_default="pet_grooming", nullable=False),
        sa.Column("phone", sa.String(20)),
        sa.Column("address", sa.String(255)),
        sa.Column("timezone", sa.String(50), server_default="Asia/Seoul", nullable=False),
        sa.Column("suspended_at", sa.DateTime(timezone=True)),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    roles = op.create_table(
        "roles",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(20), nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    permissions = op.create_table(
        "permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("description", sa.String(200), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("permission_id", sa.Integer, sa.ForeignKey("permissions.id"), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )
    op.create_table(
        "shop_members",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),  # auth 의 유저 ID — 스포크를 넘는 외래 키는 걸지 않는다
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        *_timestamps(),
    )
    op.create_index("ix_shop_members_shop_id", "shop_members", ["shop_id"])
    op.create_index("ix_shop_members_user_id", "shop_members", ["user_id"])
    op.create_index(
        "uq_shop_members_active", "shop_members", ["shop_id", "user_id"],
        unique=True, postgresql_where=sa.text("removed_at IS NULL"),
    )
    op.create_table(
        "shop_invites",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("shop_id", sa.Integer, sa.ForeignKey("shops.id"), nullable=False),
        sa.Column("role_id", sa.Integer, sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("created_by_member_id", sa.Integer, sa.ForeignKey("shop_members.id")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer, server_default="1", nullable=False),
        sa.Column("used_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.UniqueConstraint("code_hash", name="uq_shop_invites_code_hash"),
    )
    op.create_index("ix_shop_invites_shop_id", "shop_invites", ["shop_id"])

    op.bulk_insert(roles, [{"code": "owner", "name": "사장"}, {"code": "staff", "name": "직원"}])
    op.bulk_insert(
        permissions,
        [
            {"code": "reservation:write", "description": "예약 등록·수정"},
            {"code": "customer:write", "description": "고객·반려동물 등록·수정"},
            {"code": "record:write", "description": "미용 기록·사진 업로드"},
            {"code": "sales:write", "description": "기록할 때 매출 금액 입력"},
            {"code": "sales:read", "description": "매출 통계·합계 열람"},
            {"code": "record:delete", "description": "기록 삭제"},
            {"code": "customer:delete", "description": "고객 삭제"},
            {"code": "member:manage", "description": "직원 초대·내보내기·역할 변경"},
            {"code": "shop:update", "description": "매장 정보 수정"},
        ],
    )
    # 사장은 전부, 직원은 입력 권한 네 가지.
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id FROM roles r CROSS JOIN permissions p
        WHERE r.code = 'owner'
           OR (r.code = 'staff' AND p.code IN
               ('reservation:write', 'customer:write', 'record:write', 'sales:write'))
        """
    )


def downgrade() -> None:
    op.drop_index("ix_shop_invites_shop_id", table_name="shop_invites")
    op.drop_table("shop_invites")
    op.drop_index("uq_shop_members_active", table_name="shop_members")
    op.drop_index("ix_shop_members_user_id", table_name="shop_members")
    op.drop_index("ix_shop_members_shop_id", table_name="shop_members")
    op.drop_table("shop_members")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("shops")
```

- [ ] **Step 8: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/adapter/test_tenancy_seed.py tests/test_schema_drift.py -q -p no:cacheprovider`
Expected: `2 passed` — 시드가 맞고, 마이그레이션과 ORM이 어긋나지 않는다.

- [ ] **Step 9: 개발 DB에 적용하고, 되돌리기는 테스트 DB에서 확인한다**

`downgrade`는 테이블을 지운다. **개발 DB에서는 돌리지 않는다.** 테스트 DB(`chagocnote_test`)에서만 확인한다.

Run:
```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend sh -c 'URL=$(python -c "from scripts.prepare_test_db import TEST_DATABASE_URL as u; print(u)") && alembic -x db_url="$URL" downgrade 0001 && alembic -x db_url="$URL" upgrade head && alembic -x db_url="$URL" current'
```
Expected: 오류 없이 끝나고 마지막 줄이 `0002 (head)`다.

- [ ] **Step 10: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/tenancy backend/alembic/versions/0002_tenancy_tables_and_seed.py backend/orm_registry.py
git commit -m "feat(tenancy): 매장·역할·소속·초대 도메인과 테이블, 역할·권한 시드"
```

---

### Task 5: 매장·멤버 리포지토리와 `ShopContext`

**Files:**
- Create: `backend/apps/hub/app/dtos/shop_context.py`
- Create: `backend/apps/tenancy/app/dtos/shop_access_record.py`
- Create: `backend/apps/tenancy/app/ports/output/shop_repository.py`, `member_repository.py`
- Create: `backend/apps/tenancy/adapter/outbound/mappers/tenancy_mapper.py`
- Create: `backend/apps/tenancy/adapter/outbound/pg/shop_pg_repository.py`, `member_pg_repository.py`
- Test: `backend/apps/tenancy/tests/adapter/test_shop_pg_repository.py`, `test_member_pg_repository.py`

**Interfaces:**
- Consumes: Task 4의 도메인과 ORM, Task 1의 `db_session`
- Produces:
  - `hub.app.dtos.shop_context.ShopContext(shop_id: int, member_id: int, role: str, permissions: frozenset[str])` (frozen dataclass)
  - `tenancy.app.dtos.shop_access_record.ShopAccessRecord(member_id: int, role: str, permissions: frozenset[str], shop_suspended: bool, shop_closed: bool)`
  - `tenancy.app.ports.output.shop_repository.ShopRepository`:
    - `async create(name: str, business_type: str) -> Shop`
    - `async get_by_id(shop_id: int) -> Shop` — 컨텍스트가 아직 없는 경로(초대 수락)용
    - `async get(ctx: ShopContext) -> Shop`
    - `async update(ctx: ShopContext, name: str, phone: str | None, address: str | None) -> Shop`
  - `tenancy.app.ports.output.member_repository.MemberRepository`:
    - `async find_access(shop_id: int, user_id: int) -> ShopAccessRecord | None`
    - `async add(shop_id: int, user_id: int, role: RoleCode) -> Member` — 이미 속해 있으면 `AlreadyMemberError`
    - `async list_active(ctx: ShopContext) -> list[Member]`
    - `async get_active(ctx: ShopContext, member_id: int) -> Member | None`
    - `async count_owners(ctx: ShopContext) -> int` — 사장 행을 잠그고 센다
    - `async change_role(ctx: ShopContext, member_id: int, role: RoleCode) -> None`
    - `async remove(ctx: ShopContext, member_id: int) -> None`
  - 구현 `ShopPgRepository(session)`, `MemberPgRepository(session)`

- [ ] **Step 1: `ShopContext`를 만든다**

`backend/apps/hub/app/dtos/shop_context.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopContext:
    """매장 범위 요청의 컨텍스트 — 누가(member_id) 어느 매장(shop_id)에서 어떤 권한으로 행동하는가.

    매장 범위의 리포지토리 메서드는 이 값을 필수 첫 인자로 받는다.
    컨텍스트 없이는 조회할 수 없게 해서 다른 매장의 데이터가 섞이는 사고를 구조로 막는다.
    """

    shop_id: int
    member_id: int
    role: str
    permissions: frozenset[str]
```

- [ ] **Step 2: 실패하는 통합 테스트를 쓴다**

`backend/apps/tenancy/tests/adapter/test_shop_pg_repository.py`:
```python
import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository

pytestmark = pytest.mark.integration


def _ctx(shop_id):
    return ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset())


async def test_매장을_만들면_기본값이_채워진다(db_session):
    shop = await ShopPgRepository(db_session).create("Hiss Haus", "pet_grooming")
    assert shop.id > 0
    assert (shop.name, shop.business_type, shop.timezone) == ("Hiss Haus", "pet_grooming", "Asia/Seoul")
    assert shop.phone is None and shop.is_closed is False


async def test_만든_매장을_ID_와_컨텍스트로_다시_읽는다(db_session):
    repo = ShopPgRepository(db_session)
    created = await repo.create("Hiss Haus", "pet_grooming")
    assert (await repo.get_by_id(created.id)).name == "Hiss Haus"
    assert (await repo.get(_ctx(created.id))).id == created.id


async def test_매장_정보를_고친다(db_session):
    repo = ShopPgRepository(db_session)
    shop = await repo.create("Hiss Haus", "pet_grooming")
    updated = await repo.update(_ctx(shop.id), "히스 하우스", "02-000-0000", "서울")
    assert (updated.name, updated.phone, updated.address) == ("히스 하우스", "02-000-0000", "서울")
    assert (await repo.get_by_id(shop.id)).name == "히스 하우스"


async def test_수정은_컨텍스트의_매장만_건드린다(db_session):
    repo = ShopPgRepository(db_session)
    a = await repo.create("A 매장", "pet_grooming")
    b = await repo.create("B 매장", "pet_grooming")
    await repo.update(_ctx(a.id), "A 새 이름", None, None)
    assert (await repo.get_by_id(b.id)).name == "B 매장"
```

`backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`:
```python
import pytest
from sqlalchemy import text

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.domain.errors import AlreadyMemberError
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration


def _ctx(shop_id):
    return ShopContext(shop_id=shop_id, member_id=0, role="owner", permissions=frozenset())


async def _shop(session, name="Hiss Haus"):
    return await ShopPgRepository(session).create(name, "pet_grooming")


async def test_사장의_접근_기록에는_모든_권한이_있다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    member = await repo.add(shop.id, user_id=7, role=RoleCode.OWNER)
    record = await repo.find_access(shop.id, user_id=7)
    assert (record.member_id, record.role) == (member.id, "owner")
    assert {"member:manage", "shop:update", "sales:read"} <= record.permissions
    assert (record.shop_suspended, record.shop_closed) == (False, False)


async def test_직원의_접근_기록에는_입력_권한만_있다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=8, role=RoleCode.STAFF)
    record = await repo.find_access(shop.id, user_id=8)
    assert record.permissions == {"reservation:write", "customer:write", "record:write", "sales:write"}


async def test_멤버가_아니면_접근_기록이_없다(db_session):
    shop = await _shop(db_session)
    assert await MemberPgRepository(db_session).find_access(shop.id, user_id=404) is None


async def test_닫히거나_정지된_매장은_접근_기록에_표시된다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=7, role=RoleCode.OWNER)
    await db_session.execute(
        text("UPDATE shops SET closed_at = now(), suspended_at = now() WHERE id = :id"), {"id": shop.id}
    )
    record = await repo.find_access(shop.id, user_id=7)
    assert (record.shop_suspended, record.shop_closed) == (True, True)


async def test_같은_매장에_두_번_합류할_수_없다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    with pytest.raises(AlreadyMemberError):
        await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    # 실패한 뒤에도 세션을 계속 쓸 수 있어야 한다.
    assert len(await repo.list_active(_ctx(shop.id))) == 1


async def test_내보낸_멤버는_접근할_수_없고_다시_합류할_수_있다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    member = await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    await repo.remove(_ctx(shop.id), member.id)
    assert await repo.find_access(shop.id, user_id=7) is None
    assert await repo.list_active(_ctx(shop.id)) == []
    rejoined = await repo.add(shop.id, user_id=7, role=RoleCode.STAFF)
    assert rejoined.id != member.id


async def test_멤버_목록과_단건_조회는_컨텍스트의_매장만_본다(db_session):
    a, b = await _shop(db_session, "A 매장"), await _shop(db_session, "B 매장")
    repo = MemberPgRepository(db_session)
    a_owner = await repo.add(a.id, user_id=1, role=RoleCode.OWNER)
    a_staff = await repo.add(a.id, user_id=2, role=RoleCode.STAFF)
    b_owner = await repo.add(b.id, user_id=3, role=RoleCode.OWNER)

    assert [m.id for m in await repo.list_active(_ctx(a.id))] == [a_owner.id, a_staff.id]
    assert (await repo.get_active(_ctx(a.id), a_staff.id)).role is RoleCode.STAFF
    # B 매장의 멤버 ID 를 A 매장의 컨텍스트로는 읽을 수 없다.
    assert await repo.get_active(_ctx(a.id), b_owner.id) is None


async def test_역할_변경과_내보내기는_컨텍스트의_매장만_건드린다(db_session):
    a, b = await _shop(db_session, "A 매장"), await _shop(db_session, "B 매장")
    repo = MemberPgRepository(db_session)
    b_staff = await repo.add(b.id, user_id=3, role=RoleCode.STAFF)

    await repo.change_role(_ctx(a.id), b_staff.id, RoleCode.OWNER)
    await repo.remove(_ctx(a.id), b_staff.id)
    assert (await repo.get_active(_ctx(b.id), b_staff.id)).role is RoleCode.STAFF

    await repo.change_role(_ctx(b.id), b_staff.id, RoleCode.OWNER)
    assert (await repo.get_active(_ctx(b.id), b_staff.id)).role is RoleCode.OWNER


async def test_사장_수를_센다(db_session):
    shop = await _shop(db_session)
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=1, role=RoleCode.OWNER)
    await repo.add(shop.id, user_id=2, role=RoleCode.STAFF)
    removed_owner = await repo.add(shop.id, user_id=3, role=RoleCode.OWNER)
    await repo.remove(_ctx(shop.id), removed_owner.id)
    assert await repo.count_owners(_ctx(shop.id)) == 1
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/adapter/test_shop_pg_repository.py apps/tenancy/tests/adapter/test_member_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.adapter.outbound.pg.shop_pg_repository'`

- [ ] **Step 4: DTO와 포트를 쓴다**

`backend/apps/tenancy/app/dtos/shop_access_record.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShopAccessRecord:
    """한 유저가 한 매장에 대해 가진 소속·역할·권한과 그 매장의 상태. 매 요청마다 DB 에서 읽는다."""

    member_id: int
    role: str
    permissions: frozenset[str]
    shop_suspended: bool
    shop_closed: bool
```

`backend/apps/tenancy/app/ports/output/shop_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from tenancy.domain.entities.shop import Shop


class ShopRepository(ABC):
    @abstractmethod
    async def create(self, name: str, business_type: str) -> Shop: ...

    @abstractmethod
    async def get_by_id(self, shop_id: int) -> Shop:
        """컨텍스트가 아직 없는 경로(초대 수락)에서만 쓴다."""

    @abstractmethod
    async def get(self, ctx: ShopContext) -> Shop: ...

    @abstractmethod
    async def update(
        self, ctx: ShopContext, name: str, phone: str | None, address: str | None
    ) -> Shop: ...
```

`backend/apps/tenancy/app/ports/output/member_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.domain.entities.member import Member
from tenancy.domain.value_objects.role_code import RoleCode


class MemberRepository(ABC):
    @abstractmethod
    async def find_access(self, shop_id: int, user_id: int) -> ShopAccessRecord | None:
        """지금 속해 있는 멤버만 찾는다. 내보낸 멤버는 None."""

    @abstractmethod
    async def add(self, shop_id: int, user_id: int, role: RoleCode) -> Member:
        """이미 속해 있으면 AlreadyMemberError."""

    @abstractmethod
    async def list_active(self, ctx: ShopContext) -> list[Member]: ...

    @abstractmethod
    async def get_active(self, ctx: ShopContext, member_id: int) -> Member | None: ...

    @abstractmethod
    async def count_owners(self, ctx: ShopContext) -> int:
        """사장 행을 잠그고 센다. 두 사장이 동시에 서로를 낮춰 사장이 0명이 되는 일을 막는다."""

    @abstractmethod
    async def change_role(self, ctx: ShopContext, member_id: int, role: RoleCode) -> None: ...

    @abstractmethod
    async def remove(self, ctx: ShopContext, member_id: int) -> None: ...
```

- [ ] **Step 5: 매퍼와 PG 구현을 쓴다**

`backend/apps/tenancy/adapter/outbound/mappers/tenancy_mapper.py`:
```python
from __future__ import annotations

from tenancy.adapter.outbound.orm.tenancy_orm import ShopInviteOrm, ShopMemberOrm, ShopOrm
from tenancy.domain.entities.invite import Invite
from tenancy.domain.entities.member import Member
from tenancy.domain.entities.shop import Shop
from tenancy.domain.value_objects.role_code import RoleCode


def to_shop(orm: ShopOrm) -> Shop:
    return Shop(
        id=orm.id,
        name=orm.name,
        business_type=orm.business_type,
        phone=orm.phone,
        address=orm.address,
        timezone=orm.timezone,
        suspended_at=orm.suspended_at,
        closed_at=orm.closed_at,
    )


def to_member(orm: ShopMemberOrm, role_code: str) -> Member:
    return Member(
        id=orm.id,
        shop_id=orm.shop_id,
        user_id=orm.user_id,
        role=RoleCode(role_code),
        joined_at=orm.joined_at,
    )


def to_invite(orm: ShopInviteOrm, role_code: str) -> Invite:
    return Invite(
        id=orm.id,
        shop_id=orm.shop_id,
        role=RoleCode(role_code),
        expires_at=orm.expires_at,
        max_uses=orm.max_uses,
        used_count=orm.used_count,
        revoked_at=orm.revoked_at,
    )
```

`backend/apps/tenancy/adapter/outbound/pg/shop_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.mappers.tenancy_mapper import to_shop
from tenancy.adapter.outbound.orm.tenancy_orm import ShopOrm
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.entities.shop import Shop


class ShopPgRepository(ShopRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, name: str, business_type: str) -> Shop:
        row = ShopOrm(name=name, business_type=business_type)
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)  # 서버 기본값(timezone 등)을 읽어 온다
        return to_shop(row)

    async def get_by_id(self, shop_id: int) -> Shop:
        return to_shop(await self._row(shop_id))

    async def get(self, ctx: ShopContext) -> Shop:
        return to_shop(await self._row(ctx.shop_id))

    async def update(
        self, ctx: ShopContext, name: str, phone: str | None, address: str | None
    ) -> Shop:
        row = await self._row(ctx.shop_id)
        row.name, row.phone, row.address = name, phone, address
        await self._session.flush()
        return to_shop(row)

    async def _row(self, shop_id: int) -> ShopOrm:
        return (
            await self._session.execute(select(ShopOrm).where(ShopOrm.id == shop_id))
        ).scalar_one()
```

`backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.mappers.tenancy_mapper import to_member
from tenancy.adapter.outbound.orm.tenancy_orm import (
    PermissionOrm,
    RoleOrm,
    RolePermissionOrm,
    ShopMemberOrm,
    ShopOrm,
)
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import AlreadyMemberError
from tenancy.domain.value_objects.role_code import RoleCode


class MemberPgRepository(MemberRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_access(self, shop_id: int, user_id: int) -> ShopAccessRecord | None:
        stmt = (
            select(
                ShopMemberOrm.id, RoleOrm.id, RoleOrm.code, ShopOrm.suspended_at, ShopOrm.closed_at
            )
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .join(ShopOrm, ShopOrm.id == ShopMemberOrm.shop_id)
            .where(
                ShopMemberOrm.shop_id == shop_id,
                ShopMemberOrm.user_id == user_id,
                ShopMemberOrm.removed_at.is_(None),
            )
        )
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        member_id, role_id, role_code, suspended_at, closed_at = row
        codes = (
            await self._session.execute(
                select(PermissionOrm.code)
                .join(RolePermissionOrm, RolePermissionOrm.permission_id == PermissionOrm.id)
                .where(RolePermissionOrm.role_id == role_id)
            )
        ).scalars()
        return ShopAccessRecord(
            member_id=member_id,
            role=role_code,
            permissions=frozenset(codes),
            shop_suspended=suspended_at is not None,
            shop_closed=closed_at is not None,
        )

    async def add(self, shop_id: int, user_id: int, role: RoleCode) -> Member:
        row = ShopMemberOrm(shop_id=shop_id, user_id=user_id, role_id=await self._role_id(role))
        try:
            # 세이브포인트 안에서 넣는다. 유일 제약에 걸려도 바깥 트랜잭션은 계속 쓸 수 있다.
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError as exc:
            raise AlreadyMemberError("이미 이 매장의 멤버입니다.") from exc
        await self._session.refresh(row)  # 서버 기본값 joined_at 을 읽어 온다
        return to_member(row, role.value)

    async def list_active(self, ctx: ShopContext) -> list[Member]:
        stmt = self._active(ctx).order_by(ShopMemberOrm.id)
        return [to_member(m, code) for m, code in (await self._session.execute(stmt)).all()]

    async def get_active(self, ctx: ShopContext, member_id: int) -> Member | None:
        row = (
            await self._session.execute(self._active(ctx).where(ShopMemberOrm.id == member_id))
        ).first()
        return to_member(row[0], row[1]) if row else None

    async def count_owners(self, ctx: ShopContext) -> int:
        stmt = (
            select(ShopMemberOrm.id)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(
                ShopMemberOrm.shop_id == ctx.shop_id,
                ShopMemberOrm.removed_at.is_(None),
                RoleOrm.code == RoleCode.OWNER.value,
            )
            .with_for_update(of=ShopMemberOrm)
        )
        return len((await self._session.execute(stmt)).scalars().all())

    async def change_role(self, ctx: ShopContext, member_id: int, role: RoleCode) -> None:
        await self._session.execute(
            self._update_active(ctx, member_id).values(role_id=await self._role_id(role))
        )

    async def remove(self, ctx: ShopContext, member_id: int) -> None:
        await self._session.execute(
            self._update_active(ctx, member_id).values(removed_at=func.now())
        )

    def _active(self, ctx: ShopContext):
        return (
            select(ShopMemberOrm, RoleOrm.code)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(ShopMemberOrm.shop_id == ctx.shop_id, ShopMemberOrm.removed_at.is_(None))
        )

    def _update_active(self, ctx: ShopContext, member_id: int):
        return update(ShopMemberOrm).where(
            ShopMemberOrm.id == member_id,
            ShopMemberOrm.shop_id == ctx.shop_id,
            ShopMemberOrm.removed_at.is_(None),
        )

    async def _role_id(self, role: RoleCode) -> int:
        return (
            await self._session.execute(select(RoleOrm.id).where(RoleOrm.code == role.value))
        ).scalar_one()
```

- [ ] **Step 6: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/adapter/test_shop_pg_repository.py apps/tenancy/tests/adapter/test_member_pg_repository.py -q -p no:cacheprovider`
Expected: `13 passed`

- [ ] **Step 7: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/hub backend/apps/tenancy
git commit -m "feat(tenancy): 매장·멤버 리포지토리와 ShopContext"
```

---

### Task 6: 초대 리포지토리, 입력 시도 제한기, 조립 함수

**Files:**
- Create: `backend/apps/tenancy/app/ports/output/invite_repository.py`, `invite_attempt_limiter_port.py`
- Create: `backend/apps/tenancy/adapter/outbound/pg/invite_pg_repository.py`
- Create: `backend/apps/tenancy/adapter/outbound/redis/invite_attempt_redis_limiter.py`
- Create: `backend/apps/tenancy/dependencies/tenancy_wiring.py`
- Test: `backend/apps/tenancy/tests/adapter/test_invite_pg_repository.py`, `test_invite_attempt_redis_limiter.py`

**Interfaces:**
- Consumes: Task 4의 `Invite`·`RoleCode`·ORM, Task 5의 `ShopContext`·`to_invite`·`ShopPgRepository`·`MemberPgRepository`, `core.redis.get_redis`
- Produces:
  - `tenancy.app.ports.output.invite_repository.InviteRepository`:
    - `async create(ctx: ShopContext, role: RoleCode, code_hash: str, expires_at: datetime, max_uses: int) -> Invite` — 만든 멤버는 `ctx.member_id`
    - `async create_owner_invite(shop_id: int, code_hash: str, expires_at: datetime) -> Invite` — 매장 개설 때 쓰는 사장용 첫 초대(만든 멤버 없음, 1회)
    - `async find_by_code_hash_for_update(code_hash: str) -> Invite | None` — 행을 잠근다
    - `async mark_used(invite_id: int) -> None`
  - `tenancy.app.ports.output.invite_attempt_limiter_port.InviteAttemptLimiterPort`: `async hit(user_id: int) -> int` — 이번 1분 창에서 몇 번째 시도인지 돌려준다
  - `tenancy.dependencies.tenancy_wiring`: `build_shop_repository(db) -> ShopRepository`, `build_member_repository(db) -> MemberRepository`, `build_invite_repository(db) -> InviteRepository`, `build_invite_attempt_limiter() -> InviteAttemptLimiterPort`

- [ ] **Step 1: 실패하는 통합 테스트를 쓴다**

`backend/apps/tenancy/tests/adapter/test_invite_pg_repository.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


async def _shop_with_owner(session):
    shop = await ShopPgRepository(session).create("Hiss Haus", "pet_grooming")
    owner = await MemberPgRepository(session).add(shop.id, user_id=1, role=RoleCode.OWNER)
    ctx = ShopContext(shop_id=shop.id, member_id=owner.id, role="owner", permissions=frozenset())
    return shop, ctx


async def test_직원용_초대를_만들고_해시로_다시_찾는다(db_session):
    shop, ctx = await _shop_with_owner(db_session)
    repo = InvitePgRepository(db_session)
    created = await repo.create(ctx, RoleCode.STAFF, "hash-a", EXPIRES, max_uses=1)
    found = await repo.find_by_code_hash_for_update("hash-a")
    assert found.id == created.id
    assert (found.shop_id, found.role, found.max_uses, found.used_count) == (shop.id, RoleCode.STAFF, 1, 0)
    assert found.expires_at == EXPIRES and found.revoked_at is None
    made_by = (
        await db_session.execute(text("SELECT created_by_member_id FROM shop_invites WHERE id = :id"), {"id": created.id})
    ).scalar_one()
    assert made_by == ctx.member_id


async def test_사장용_첫_초대는_만든_멤버가_없고_한_번만_쓸_수_있다(db_session):
    shop = await ShopPgRepository(db_session).create("Hiss Haus", "pet_grooming")
    repo = InvitePgRepository(db_session)
    invite = await repo.create_owner_invite(shop.id, "hash-owner", EXPIRES + timedelta(days=1))
    assert (invite.role, invite.max_uses) == (RoleCode.OWNER, 1)
    made_by = (
        await db_session.execute(text("SELECT created_by_member_id FROM shop_invites WHERE id = :id"), {"id": invite.id})
    ).scalar_one()
    assert made_by is None


async def test_모르는_해시는_None_이다(db_session):
    assert await InvitePgRepository(db_session).find_by_code_hash_for_update("nope") is None


async def test_사용하면_횟수가_오른다(db_session):
    _, ctx = await _shop_with_owner(db_session)
    repo = InvitePgRepository(db_session)
    invite = await repo.create(ctx, RoleCode.STAFF, "hash-b", EXPIRES, max_uses=1)
    await repo.mark_used(invite.id)
    assert (await repo.find_by_code_hash_for_update("hash-b")).used_count == 1
```

`backend/apps/tenancy/tests/adapter/test_invite_attempt_redis_limiter.py`:
```python
import pytest
from redis.asyncio import from_url

from core.config import REDIS_URL
from tenancy.adapter.outbound.redis.invite_attempt_redis_limiter import InviteAttemptRedisLimiter

pytestmark = pytest.mark.integration


@pytest.fixture
async def redis():
    # 개발 데이터(db 0)를 건드리지 않으려고 db 15 를 쓴다.
    client = from_url(REDIS_URL.rsplit("/", 1)[0] + "/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.aclose()


async def test_시도할_때마다_횟수가_오른다(redis):
    limiter = InviteAttemptRedisLimiter(redis)
    assert [await limiter.hit(7) for _ in range(3)] == [1, 2, 3]


async def test_유저마다_따로_센다(redis):
    limiter = InviteAttemptRedisLimiter(redis)
    await limiter.hit(7)
    assert await limiter.hit(8) == 1


async def test_창은_첫_시도에서_60초로_잡히고_이후_시도가_늘리지_않는다(redis):
    limiter = InviteAttemptRedisLimiter(redis)
    await limiter.hit(7)
    await redis.expire("tenancy:invite-attempts:7", 30)
    await limiter.hit(7)
    assert 0 < await redis.ttl("tenancy:invite-attempts:7") <= 30
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/adapter/test_invite_pg_repository.py apps/tenancy/tests/adapter/test_invite_attempt_redis_limiter.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.adapter.outbound.pg.invite_pg_repository'`

- [ ] **Step 3: 포트를 쓴다**

`backend/apps/tenancy/app/ports/output/invite_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from tenancy.domain.entities.invite import Invite
from tenancy.domain.value_objects.role_code import RoleCode


class InviteRepository(ABC):
    @abstractmethod
    async def create(
        self, ctx: ShopContext, role: RoleCode, code_hash: str, expires_at: datetime, max_uses: int
    ) -> Invite:
        """멤버가 만드는 초대. 만든 멤버는 ctx.member_id 로 남는다."""

    @abstractmethod
    async def create_owner_invite(self, shop_id: int, code_hash: str, expires_at: datetime) -> Invite:
        """운영자가 매장을 개설하며 만드는 사장용 첫 초대. 아직 멤버가 없어 컨텍스트도 없다."""

    @abstractmethod
    async def find_by_code_hash_for_update(self, code_hash: str) -> Invite | None:
        """행을 잠근다. 1회용 코드를 두 사람이 동시에 넣어도 한 사람만 통과한다."""

    @abstractmethod
    async def mark_used(self, invite_id: int) -> None: ...
```

`backend/apps/tenancy/app/ports/output/invite_attempt_limiter_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class InviteAttemptLimiterPort(ABC):
    @abstractmethod
    async def hit(self, user_id: int) -> int:
        """초대 코드 입력 시도를 하나 세고, 이번 1분 창에서 몇 번째 시도인지 돌려준다."""
```

- [ ] **Step 4: 구현을 쓴다**

`backend/apps/tenancy/adapter/outbound/pg/invite_pg_repository.py`:
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.mappers.tenancy_mapper import to_invite
from tenancy.adapter.outbound.orm.tenancy_orm import RoleOrm, ShopInviteOrm
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.domain.entities.invite import Invite
from tenancy.domain.value_objects.role_code import RoleCode


class InvitePgRepository(InviteRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, ctx: ShopContext, role: RoleCode, code_hash: str, expires_at: datetime, max_uses: int
    ) -> Invite:
        return await self._insert(ctx.shop_id, role, code_hash, ctx.member_id, expires_at, max_uses)

    async def create_owner_invite(self, shop_id: int, code_hash: str, expires_at: datetime) -> Invite:
        return await self._insert(shop_id, RoleCode.OWNER, code_hash, None, expires_at, 1)

    async def find_by_code_hash_for_update(self, code_hash: str) -> Invite | None:
        stmt = (
            select(ShopInviteOrm, RoleOrm.code)
            .join(RoleOrm, RoleOrm.id == ShopInviteOrm.role_id)
            .where(ShopInviteOrm.code_hash == code_hash)
            .with_for_update(of=ShopInviteOrm)
        )
        row = (await self._session.execute(stmt)).first()
        return to_invite(row[0], row[1]) if row else None

    async def mark_used(self, invite_id: int) -> None:
        await self._session.execute(
            update(ShopInviteOrm)
            .where(ShopInviteOrm.id == invite_id)
            .values(used_count=ShopInviteOrm.used_count + 1)
        )

    async def _insert(
        self, shop_id: int, role: RoleCode, code_hash: str,
        created_by_member_id: int | None, expires_at: datetime, max_uses: int,
    ) -> Invite:
        role_id = (
            await self._session.execute(select(RoleOrm.id).where(RoleOrm.code == role.value))
        ).scalar_one()
        row = ShopInviteOrm(
            shop_id=shop_id, role_id=role_id, code_hash=code_hash,
            created_by_member_id=created_by_member_id, expires_at=expires_at,
            max_uses=max_uses, used_count=0,
        )
        self._session.add(row)
        await self._session.flush()
        return to_invite(row, role.value)
```

`backend/apps/tenancy/adapter/outbound/redis/invite_attempt_redis_limiter.py`:
```python
from __future__ import annotations

from redis.asyncio import Redis

from tenancy.app.ports.output.invite_attempt_limiter_port import InviteAttemptLimiterPort

_WINDOW_SECONDS = 60


class InviteAttemptRedisLimiter(InviteAttemptLimiterPort):
    """키: tenancy:invite-attempts:{user_id} → 이번 1분 창의 시도 횟수."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def hit(self, user_id: int) -> int:
        key = f"tenancy:invite-attempts:{user_id}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, _WINDOW_SECONDS, nx=True)  # 창은 첫 시도에서만 잡는다
            count, _ = await pipe.execute()
        return int(count)
```

`backend/apps/tenancy/dependencies/tenancy_wiring.py`:
```python
"""tenancy 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.adapter.outbound.redis.invite_attempt_redis_limiter import InviteAttemptRedisLimiter
from tenancy.app.ports.output.invite_attempt_limiter_port import InviteAttemptLimiterPort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.app.ports.output.shop_repository import ShopRepository


def build_shop_repository(db: AsyncSession) -> ShopRepository:
    return ShopPgRepository(db)


def build_member_repository(db: AsyncSession) -> MemberRepository:
    return MemberPgRepository(db)


def build_invite_repository(db: AsyncSession) -> InviteRepository:
    return InvitePgRepository(db)


def build_invite_attempt_limiter() -> InviteAttemptLimiterPort:
    return InviteAttemptRedisLimiter(get_redis())
```

- [ ] **Step 5: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/adapter/test_invite_pg_repository.py apps/tenancy/tests/adapter/test_invite_attempt_redis_limiter.py -q -p no:cacheprovider`
Expected: `7 passed`

- [ ] **Step 6: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/tenancy
git commit -m "feat(tenancy): 초대 리포지토리와 초대 코드 입력 시도 제한기"
```

---

### Task 7: 매장 접근 확인 — `ShopAccessPort`와 `require_permission`

매장 범위의 모든 경로가 거치는 관문이다. 허브에 `ShopAccessPort`를 두고, tenancy가 HTTP 표면이 없는 슬라이스 `resolve_shop_access`로 구현하며, `core/shop_guard.py`가 FastAPI 의존성으로 감싼다. 첫 "허브 포트 자리"가 여기서 생긴다.

**Files:**
- Create: `backend/apps/hub/app/ports/shop_access_port.py`
- Create: `backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py`
- Create: `backend/apps/tenancy/dependencies/resolve_shop_access_provider.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/error_map.py`
- Create: `backend/core/shop_guard.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py`, `backend/tests/test_shop_guard.py`, `backend/tests/test_hub_port_binding.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: Task 5의 `ShopContext`·`ShopAccessRecord`·`MemberRepository.find_access`, Task 6의 `build_member_repository`, Task 4의 오류들, `core.security.get_current_user_id`, `core.http_errors.ApiError`
- Produces:
  - `hub.app.ports.shop_access_port.ShopAccessPort`: `async resolve(user_id: int, shop_id: int) -> ShopContext`
  - `tenancy.app.use_cases.resolve_shop_access_interactor.ResolveShopAccessInteractor(members: MemberRepository)` — `ShopAccessPort` 구현. 소속이 아니면 `NotAMemberError`, 닫힌 매장이면 `ShopClosedError`, 정지된 매장이면 `ShopSuspendedError`
  - `tenancy.dependencies.resolve_shop_access_provider.get_resolve_shop_access_use_case(db: DbSession) -> ShopAccessPort`
  - `tenancy.adapter.inbound.api.error_map.TENANCY_ERROR_STATUS: dict[type[Exception], int]`
  - `core.shop_guard`:
    - `get_shop_access_port() -> ShopAccessPort` — 자리. 채우지 않고 부르면 `RuntimeError`
    - `async get_shop_context(shop_id: int, user_id, access) -> ShopContext` — 소속만 확인하는 의존성. `shop_id`는 경로 변수에서 온다
    - `require_permission(permission: str)` — 권한까지 확인하는 의존성을 만들어 돌려준다. 권한이 없으면 `ApiError(403, "PERMISSION_DENIED", …)`

- [ ] **Step 1: 허브 포트를 쓴다**

`backend/apps/hub/app/ports/shop_access_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext


class ShopAccessPort(ABC):
    """구현: tenancy. 사용: 매장 범위의 모든 스포크 (core/shop_guard.py 를 거쳐서)."""

    @abstractmethod
    async def resolve(self, user_id: int, shop_id: int) -> ShopContext:
        """소속·역할·권한과 매장 상태를 매 요청마다 DB 에서 확인한다. 통과하지 못하면 구현 쪽 도메인 오류를 던진다."""
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py`:
```python
import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.shop_access_record import ShopAccessRecord
from tenancy.app.use_cases.resolve_shop_access_interactor import ResolveShopAccessInteractor
from tenancy.domain.errors import NotAMemberError, ShopClosedError, ShopSuspendedError


class _StubMembers:
    def __init__(self, record):
        self.record = record
        self.calls = []

    async def find_access(self, shop_id, user_id):
        self.calls.append((shop_id, user_id))
        return self.record


def _record(**overrides):
    base = dict(member_id=11, role="staff", permissions=frozenset({"record:write"}),
                shop_suspended=False, shop_closed=False)
    return ShopAccessRecord(**{**base, **overrides})


async def test_멤버면_컨텍스트를_돌려준다():
    members = _StubMembers(_record())
    ctx = await ResolveShopAccessInteractor(members).resolve(user_id=5, shop_id=3)
    assert ctx == ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset({"record:write"}))
    assert members.calls == [(3, 5)]


async def test_멤버가_아니면_NOT_A_MEMBER_다():
    with pytest.raises(NotAMemberError):
        await ResolveShopAccessInteractor(_StubMembers(None)).resolve(user_id=5, shop_id=3)


async def test_닫힌_매장은_SHOP_CLOSED_다():
    with pytest.raises(ShopClosedError):
        await ResolveShopAccessInteractor(_StubMembers(_record(shop_closed=True))).resolve(5, 3)


async def test_정지된_매장은_SHOP_SUSPENDED_다():
    with pytest.raises(ShopSuspendedError):
        await ResolveShopAccessInteractor(_StubMembers(_record(shop_suspended=True))).resolve(5, 3)
```

`backend/tests/test_shop_guard.py`:
```python
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient

from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port, get_shop_context, require_permission
from hub.app.dtos.shop_context import ShopContext


class _StubAccess:
    def __init__(self, permissions):
        self.permissions = frozenset(permissions)
        self.calls = []

    async def resolve(self, user_id, shop_id):
        self.calls.append((user_id, shop_id))
        return ShopContext(shop_id=shop_id, member_id=11, role="staff", permissions=self.permissions)


def _app(stub):
    app = FastAPI()
    install_error_handlers(app, {})

    @app.get("/v1/shops/{shop_id}/open")
    async def open_route(ctx: ShopContext = Depends(get_shop_context)) -> dict:
        return {"shop_id": ctx.shop_id, "member_id": ctx.member_id}

    @app.get("/v1/shops/{shop_id}/managed")
    async def managed_route(ctx: ShopContext = Depends(require_permission("member:manage"))) -> dict:
        return {"member_id": ctx.member_id}

    app.dependency_overrides[get_current_user_id] = lambda: 5
    if stub is not None:
        app.dependency_overrides[get_shop_access_port] = lambda: stub
    return app


async def _get(app, path):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_소속만_확인하는_경로는_경로의_shop_id_로_컨텍스트를_만든다():
    stub = _StubAccess([])
    response = await _get(_app(stub), "/v1/shops/3/open")
    assert (response.status_code, response.json()) == (200, {"shop_id": 3, "member_id": 11})
    assert stub.calls == [(5, 3)]


async def test_권한이_있으면_통과한다():
    response = await _get(_app(_StubAccess(["member:manage"])), "/v1/shops/3/managed")
    assert response.status_code == 200


async def test_권한이_없으면_403_PERMISSION_DENIED_다():
    response = await _get(_app(_StubAccess(["record:write"])), "/v1/shops/3/managed")
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")


async def test_자리를_채우지_않으면_바로_드러난다():
    with pytest.raises(RuntimeError, match="ShopAccessPort"):
        await _get(_app(None), "/v1/shops/3/open")
```

`backend/tests/test_hub_port_binding.py`:
```python
"""진입점이 허브 포트 자리를 빠짐없이 채웠는지 확인한다. 자리를 새로 만들면 여기에 더한다."""
import main
from core.shop_guard import get_shop_access_port

_API_SLOTS = [get_shop_access_port]


def test_API_프로세스는_허브_포트_자리를_모두_채운다():
    missing = [slot.__name__ for slot in _API_SLOTS if slot not in main.app.dependency_overrides]
    assert missing == []
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/app tests/test_shop_guard.py tests/test_hub_port_binding.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.use_cases.resolve_shop_access_interactor'` 과 `No module named 'core.shop_guard'`

- [ ] **Step 4: 슬라이스와 가드를 구현한다**

`backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py`:
```python
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.shop_access_port import ShopAccessPort
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import NotAMemberError, ShopClosedError, ShopSuspendedError


class ResolveShopAccessInteractor(ShopAccessPort):
    """허브의 ShopAccessPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def resolve(self, user_id: int, shop_id: int) -> ShopContext:
        record = await self._members.find_access(shop_id, user_id)
        if record is None:
            # 매장이 없는 경우와 소속이 아닌 경우를 구분해 주지 않는다 (매장 존재 여부를 흘리지 않는다).
            raise NotAMemberError("이 매장의 멤버가 아닙니다.")
        if record.shop_closed:
            raise ShopClosedError("닫힌 매장입니다.")
        if record.shop_suspended:
            raise ShopSuspendedError("이용이 정지된 매장입니다.")
        return ShopContext(
            shop_id=shop_id,
            member_id=record.member_id,
            role=record.role,
            permissions=record.permissions,
        )
```

`backend/apps/tenancy/dependencies/resolve_shop_access_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from hub.app.ports.shop_access_port import ShopAccessPort
from tenancy.app.use_cases.resolve_shop_access_interactor import ResolveShopAccessInteractor
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_resolve_shop_access_use_case(db: DbSession) -> ShopAccessPort:
    return ResolveShopAccessInteractor(members=build_member_repository(db))
```

`backend/apps/tenancy/adapter/inbound/api/error_map.py`:
```python
"""tenancy 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from tenancy.domain.errors import (
    AlreadyMemberError,
    InviteExhaustedError,
    InviteExpiredError,
    InviteInvalidError,
    LastOwnerError,
    MemberNotFoundError,
    NotAMemberError,
    ShopClosedError,
    ShopSuspendedError,
    TooManyAttemptsError,
)

TENANCY_ERROR_STATUS: dict[type[Exception], int] = {
    InviteInvalidError: 400,
    InviteExpiredError: 400,
    InviteExhaustedError: 400,
    NotAMemberError: 403,
    ShopClosedError: 403,
    ShopSuspendedError: 403,
    MemberNotFoundError: 404,
    LastOwnerError: 409,
    AlreadyMemberError: 409,
    TooManyAttemptsError: 429,
}
```

`backend/core/shop_guard.py`:
```python
"""매장 범위 경로의 관문 — 소속과 권한을 매 요청마다 확인하고 ShopContext 를 돌려준다.

확인 자체는 허브의 ShopAccessPort 가 한다 (구현: tenancy). 스포크가 tenancy 를 import 하면
허브-스포크 위반이라, 모든 매장 범위 스포크가 함께 쓰는 이 의존성은 core 에 둔다.
"""
from __future__ import annotations

from fastapi import Depends

from core.http_errors import ApiError
from core.security import get_current_user_id
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.shop_access_port import ShopAccessPort


def get_shop_access_port() -> ShopAccessPort:
    """허브 포트 자리. 진입점이 app.dependency_overrides 로 tenancy 의 구현을 꽂는다."""
    raise RuntimeError("ShopAccessPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")


async def get_shop_context(
    shop_id: int,
    user_id: int = Depends(get_current_user_id),
    access: ShopAccessPort = Depends(get_shop_access_port),
) -> ShopContext:
    """소속만 확인한다. shop_id 는 경로 변수에서 온다."""
    return await access.resolve(user_id, shop_id)


def require_permission(permission: str):
    """소속에 더해 권한까지 확인하는 의존성을 만든다. 예: Depends(require_permission("member:manage"))"""

    async def _guard(ctx: ShopContext = Depends(get_shop_context)) -> ShopContext:
        if permission not in ctx.permissions:
            raise ApiError(403, "PERMISSION_DENIED", "이 작업을 할 권한이 없습니다.")
        return ctx

    return _guard
```

- [ ] **Step 5: 진입점에서 자리를 채운다**

`backend/main.py` 전체:
```python
"""API 프로세스 — 공개키로 토큰을 검증만 한다. 토큰을 발급할 수 없다."""
import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "apps"))

from fastapi import FastAPI

from core.database import dispose_engine, init_engine
from core.redis import dispose_redis

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.get_me_router import get_me_router
from core.http_errors import install_error_handlers
from core.shop_guard import get_shop_access_port
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
from tenancy.adapter.inbound.api.v1.tenancy_myself_router import tenancy_myself_router
from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_engine()
    try:
        yield
    finally:
        await dispose_engine()
        await dispose_redis()


app = FastAPI(title="차곡노트 API", lifespan=lifespan)
app.include_router(get_me_router)
app.include_router(tenancy_myself_router)
install_error_handlers(app, {**AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS})

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_shop_access_port] = get_resolve_shop_access_use_case


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "process": "backend"}
```

- [ ] **Step 6: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/app tests/test_shop_guard.py tests/test_hub_port_binding.py -q -p no:cacheprovider`
Expected: `10 passed` (tenancy 유스케이스 5 + 가드 4 + 자리 1)

- [ ] **Step 7: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/hub backend/apps/tenancy backend/core/shop_guard.py backend/main.py backend/tests/test_shop_guard.py backend/tests/test_hub_port_binding.py
git commit -m "feat(tenancy): 매장 접근 확인 포트와 require_permission 가드"
```

---

### Task 8: 플랫폼 운영자 지정 (auth)

플랫폼 운영자는 유저에 붙는 전역 지정이고 auth가 소유한다. 다른 스포크는 허브의 `OperatorDirectoryPort`로 묻는다. 지정은 스크립트로 한다(설계 5.5절 1번).

**Files:**
- Create: `backend/apps/hub/app/ports/operator_directory_port.py`
- Create: `backend/apps/auth/adapter/outbound/orm/operator_orm.py`
- Create: `backend/alembic/versions/0003_platform_operators.py`
- Create: `backend/apps/auth/app/ports/output/operator_repository.py`
- Create: `backend/apps/auth/adapter/outbound/pg/operator_pg_repository.py`
- Create: `backend/apps/auth/app/use_cases/check_operator_interactor.py`, `backend/apps/auth/dependencies/check_operator_provider.py`
- Create: `backend/apps/auth/app/dtos/grant_operator_dto.py`, `backend/apps/auth/app/ports/input/grant_operator_use_case.py`, `backend/apps/auth/app/use_cases/grant_operator_interactor.py`, `backend/apps/auth/dependencies/grant_operator_provider.py`
- Create: `backend/scripts/grant_operator.py`
- Modify: `backend/orm_registry.py`, `backend/apps/auth/dependencies/auth_wiring.py`, `backend/apps/auth/_docs/CLAUDE.md`
- Test: `backend/apps/auth/tests/app/use_cases/test_check_operator_interactor.py`, `test_grant_operator_interactor.py`, `backend/apps/auth/tests/adapter/test_operator_pg_repository.py`

**Interfaces:**
- Consumes: `auth.app.ports.output.user_repository.UserRepository.get(user_id) -> User | None`, `auth.domain.errors.UserNotFoundError`, `auth.dependencies.auth_wiring.build_user_repository(db)`
- Produces:
  - `hub.app.ports.operator_directory_port.OperatorDirectoryPort`: `async is_operator(user_id: int) -> bool`
  - `auth.app.ports.output.operator_repository.OperatorRepository`: `async is_operator(user_id: int) -> bool`, `async grant(user_id: int) -> None`(여러 번 불러도 같다)
  - `auth.dependencies.check_operator_provider.get_check_operator_use_case(db: DbSession) -> OperatorDirectoryPort`
  - `auth.app.dtos.grant_operator_dto.GrantOperatorCommand(user_id: int)`
  - `auth.dependencies.grant_operator_provider.build_grant_operator_use_case(session: AsyncSession) -> GrantOperatorUseCase` — `async grant(command) -> None`, 없는 유저·탈퇴한 유저면 `UserNotFoundError`
  - `auth.dependencies.auth_wiring.build_operator_repository(db) -> OperatorRepository`
  - 테이블 `platform_operators(id, user_id 유일, granted_at, created_at, updated_at)`, 마이그레이션 `0003`
  - `python scripts/grant_operator.py <user_id>`

- [ ] **Step 1: 허브 포트를 쓴다**

`backend/apps/hub/app/ports/operator_directory_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class OperatorDirectoryPort(ABC):
    """구현: auth. 사용: platform_admin."""

    @abstractmethod
    async def is_operator(self, user_id: int) -> bool:
        """플랫폼 운영자로 지정된 유저인가."""
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_check_operator_interactor.py`:
```python
from auth.app.use_cases.check_operator_interactor import CheckOperatorInteractor


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def is_operator(self, user_id):
        return user_id in self.operator_ids


async def test_지정된_유저는_운영자다():
    assert await CheckOperatorInteractor(_StubOperators([5])).is_operator(5) is True


async def test_지정되지_않은_유저는_운영자가_아니다():
    assert await CheckOperatorInteractor(_StubOperators([5])).is_operator(6) is False
```

`backend/apps/auth/tests/app/use_cases/test_grant_operator_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand
from auth.app.use_cases.grant_operator_interactor import GrantOperatorInteractor
from auth.domain.entities.user import User
from auth.domain.errors import UserNotFoundError


class _StubUsers:
    def __init__(self, user):
        self.user = user

    async def get(self, user_id):
        return self.user


class _StubOperators:
    def __init__(self):
        self.granted = []

    async def grant(self, user_id):
        self.granted.append(user_id)


def _user(deleted_at=None):
    return User(id=5, display_name="운영자", profile_image_url=None, phone=None,
                suspended_at=None, deleted_at=deleted_at)


async def test_있는_유저를_운영자로_지정한다():
    operators = _StubOperators()
    await GrantOperatorInteractor(_StubUsers(_user()), operators).grant(GrantOperatorCommand(user_id=5))
    assert operators.granted == [5]


async def test_없는_유저는_지정하지_않는다():
    operators = _StubOperators()
    with pytest.raises(UserNotFoundError):
        await GrantOperatorInteractor(_StubUsers(None), operators).grant(GrantOperatorCommand(user_id=404))
    assert operators.granted == []


async def test_탈퇴한_유저는_지정하지_않는다():
    operators = _StubOperators()
    deleted = _user(deleted_at=datetime(2026, 9, 20, tzinfo=timezone.utc))
    with pytest.raises(UserNotFoundError):
        await GrantOperatorInteractor(_StubUsers(deleted), operators).grant(GrantOperatorCommand(user_id=5))
    assert operators.granted == []
```

`backend/apps/auth/tests/adapter/test_operator_pg_repository.py`:
```python
import pytest
from sqlalchemy import text

from auth.adapter.outbound.pg.operator_pg_repository import OperatorPgRepository

pytestmark = pytest.mark.integration


async def _user_id(session) -> int:
    return (
        await session.execute(text("INSERT INTO users (display_name) VALUES ('운영자') RETURNING id"))
    ).scalar_one()


async def test_지정하기_전에는_운영자가_아니다(db_session):
    assert await OperatorPgRepository(db_session).is_operator(await _user_id(db_session)) is False


async def test_지정하면_운영자다(db_session):
    repo = OperatorPgRepository(db_session)
    user_id = await _user_id(db_session)
    await repo.grant(user_id)
    assert await repo.is_operator(user_id) is True


async def test_여러_번_지정해도_행은_하나다(db_session):
    repo = OperatorPgRepository(db_session)
    user_id = await _user_id(db_session)
    await repo.grant(user_id)
    await repo.grant(user_id)
    count = (await db_session.execute(text("SELECT count(*) FROM platform_operators"))).scalar_one()
    assert count == 1
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_check_operator_interactor.py apps/auth/tests/app/use_cases/test_grant_operator_interactor.py apps/auth/tests/adapter/test_operator_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.use_cases.check_operator_interactor'`

- [ ] **Step 4: 테이블을 만든다**

`backend/apps/auth/adapter/outbound/orm/operator_orm.py`:
```python
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class PlatformOperatorOrm(Base):
    __tablename__ = "platform_operators"
    __table_args__ = (UniqueConstraint("user_id", name="uq_platform_operators_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
```

`backend/orm_registry.py`의 auth 줄 다음에 더한다 (같은 스포크끼리 붙여 둔다).
```python
import auth.adapter.outbound.orm.operator_orm  # noqa: F401
```

`backend/alembic/versions/0003_platform_operators.py`:
```python
"""플랫폼 운영자

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-20
"""
import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_operators",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_platform_operators_user_id"),
    )


def downgrade() -> None:
    op.drop_table("platform_operators")
```

- [ ] **Step 5: 포트, 리포지토리, 두 슬라이스를 구현한다**

`backend/apps/auth/app/ports/output/operator_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class OperatorRepository(ABC):
    @abstractmethod
    async def is_operator(self, user_id: int) -> bool: ...

    @abstractmethod
    async def grant(self, user_id: int) -> None:
        """여러 번 불러도 결과가 같다."""
```

`backend/apps/auth/adapter/outbound/pg/operator_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from auth.adapter.outbound.orm.operator_orm import PlatformOperatorOrm
from auth.app.ports.output.operator_repository import OperatorRepository


class OperatorPgRepository(OperatorRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_operator(self, user_id: int) -> bool:
        stmt = select(PlatformOperatorOrm.id).where(PlatformOperatorOrm.user_id == user_id)
        return (await self._session.execute(stmt)).first() is not None

    async def grant(self, user_id: int) -> None:
        await self._session.execute(
            insert(PlatformOperatorOrm)
            .values(user_id=user_id)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
```

`backend/apps/auth/app/use_cases/check_operator_interactor.py`:
```python
from __future__ import annotations

from auth.app.ports.output.operator_repository import OperatorRepository
from hub.app.ports.operator_directory_port import OperatorDirectoryPort


class CheckOperatorInteractor(OperatorDirectoryPort):
    """허브의 OperatorDirectoryPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, operators: OperatorRepository) -> None:
        self._operators = operators

    async def is_operator(self, user_id: int) -> bool:
        return await self._operators.is_operator(user_id)
```

`backend/apps/auth/app/dtos/grant_operator_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class GrantOperatorCommand:
    user_id: int
```

`backend/apps/auth/app/ports/input/grant_operator_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand


class GrantOperatorUseCase(ABC):
    @abstractmethod
    async def grant(self, command: GrantOperatorCommand) -> None: ...
```

`backend/apps/auth/app/use_cases/grant_operator_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand
from auth.app.ports.input.grant_operator_use_case import GrantOperatorUseCase
from auth.app.ports.output.operator_repository import OperatorRepository
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UserNotFoundError


class GrantOperatorInteractor(GrantOperatorUseCase):
    """HTTP 표면이 없다. scripts/grant_operator.py 가 부른다."""

    def __init__(self, users: UserRepository, operators: OperatorRepository) -> None:
        self._users = users
        self._operators = operators

    async def grant(self, command: GrantOperatorCommand) -> None:
        user = await self._users.get(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError(f"유저 {command.user_id} 을(를) 찾을 수 없습니다.")
        await self._operators.grant(user.id)
```

`backend/apps/auth/dependencies/auth_wiring.py`에 두 가지를 더한다. import 묶음에:
```python
from auth.adapter.outbound.pg.operator_pg_repository import OperatorPgRepository
from auth.app.ports.output.operator_repository import OperatorRepository
```
`build_user_repository` 함수 다음에:
```python
def build_operator_repository(db: AsyncSession) -> OperatorRepository:
    return OperatorPgRepository(db)
```

`backend/apps/auth/dependencies/check_operator_provider.py`:
```python
from __future__ import annotations

from auth.app.use_cases.check_operator_interactor import CheckOperatorInteractor
from auth.dependencies.auth_wiring import build_operator_repository
from core.database import DbSession
from hub.app.ports.operator_directory_port import OperatorDirectoryPort


def get_check_operator_use_case(db: DbSession) -> OperatorDirectoryPort:
    return CheckOperatorInteractor(operators=build_operator_repository(db))
```

`backend/apps/auth/dependencies/grant_operator_provider.py`:
```python
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from auth.app.ports.input.grant_operator_use_case import GrantOperatorUseCase
from auth.app.use_cases.grant_operator_interactor import GrantOperatorInteractor
from auth.dependencies.auth_wiring import build_operator_repository, build_user_repository


def build_grant_operator_use_case(session: AsyncSession) -> GrantOperatorUseCase:
    """FastAPI 의존성이 아니다. 스크립트가 직접 만든 세션을 넘긴다."""
    return GrantOperatorInteractor(
        users=build_user_repository(session), operators=build_operator_repository(session)
    )
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 3의 명령
Expected: `8 passed`

Run: `docker compose run --rm backend pytest tests/test_schema_drift.py -q -p no:cacheprovider`
Expected: `1 passed`

- [ ] **Step 7: 스크립트를 쓴다**

`backend/scripts/grant_operator.py`:
```python
"""유저를 플랫폼 운영자로 지정한다. 여러 번 실행해도 결과가 같다.

사용: cd infra && docker compose run --rm backend python scripts/grant_operator.py <user_id>
user_id 는 GET /v1/me 응답의 id 다.
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from auth.app.dtos.grant_operator_dto import GrantOperatorCommand
from auth.dependencies.grant_operator_provider import build_grant_operator_use_case
from auth.domain.errors import UserNotFoundError
from core.config import DATABASE_URL


async def grant(user_id: int) -> None:
    engine = create_async_engine(DATABASE_URL)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await build_grant_operator_use_case(session).grant(GrantOperatorCommand(user_id=user_id))
            await session.commit()
    finally:
        await engine.dispose()


def main() -> None:
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("사용: python scripts/grant_operator.py <user_id>")
        sys.exit(2)
    user_id = int(sys.argv[1])
    try:
        asyncio.run(grant(user_id))
    except UserNotFoundError as exc:
        print(exc)
        sys.exit(1)
    print(f"유저 {user_id} 을(를) 플랫폼 운영자로 지정했습니다.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: 개발 DB에 적용하고 스크립트를 돌려 본다**

Run:
```bash
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python scripts/grant_operator.py 999999
```
Expected: 첫 명령은 오류 없이 끝난다. 둘째 명령은 `유저 999999 을(를) 찾을 수 없습니다.`를 출력하고 종료 코드 1로 끝난다(개발 DB에 그 유저가 없다).

- [ ] **Step 9: auth 문서를 고친다**

`backend/apps/auth/_docs/CLAUDE.md`의 "소유 데이터" 줄을 바꾼다.
```markdown
소유 데이터: `users`, `social_identities`, `platform_operators`, Redis의 리프레시 토큰.
```
그리고 목록 끝에 두 줄을 더한다.
```markdown
- 플랫폼 운영자는 유저에 붙는 전역 지정이다. `scripts/grant_operator.py <user_id>`로만 지정한다. 다른 스포크는 허브의 `OperatorDirectoryPort`로 묻는다.
- 허브 포트 구현은 HTTP 표면이 없는 슬라이스다: `check_operator`, `get_user_profiles`. 인터랙터가 허브 포트 ABC를 직접 상속한다.
```

- [ ] **Step 10: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/hub backend/apps/auth backend/alembic/versions/0003_platform_operators.py backend/orm_registry.py backend/scripts/grant_operator.py
git commit -m "feat(auth): 플랫폼 운영자 지정과 OperatorDirectoryPort 구현"
```

---

### Task 9: platform_admin 스포크 골격과 자기소개

운영자 표면이다. 자기 데이터가 없고 허브 포트만 쓴다. 운영자 확인은 가드 의존성이 아니라 **유스케이스 안에서** 한다. 스텁으로 검증할 수 있고, 표면이 늘어도 확인을 빠뜨린 슬라이스가 테스트에서 드러난다.

**Files:**
- Create: `backend/apps/platform_admin/` 아래 패키지 뼈대 (Step 1의 명령)
- Create: `backend/apps/platform_admin/domain/errors.py`
- Create: `backend/apps/platform_admin/app/dtos/platform_myself_dto.py`
- Create: `backend/apps/platform_admin/app/ports/input/platform_myself_use_case.py`
- Create: `backend/apps/platform_admin/app/ports/output/platform_myself_record_port.py`
- Create: `backend/apps/platform_admin/app/use_cases/platform_myself_interactor.py`
- Create: `backend/apps/platform_admin/adapter/outbound/log_platform_myself_record_adapter.py`
- Create: `backend/apps/platform_admin/adapter/inbound/api/error_map.py`
- Create: `backend/apps/platform_admin/adapter/inbound/api/schemas/platform_myself_schema.py`
- Create: `backend/apps/platform_admin/adapter/inbound/api/v1/platform_myself_router.py`
- Create: `backend/apps/platform_admin/dependencies/hub_ports.py`, `platform_myself_provider.py`
- Create: `backend/apps/platform_admin/_docs/CLAUDE.md`, 심볼릭 링크 `backend/apps/platform_admin/CLAUDE.md`
- Test: `backend/apps/platform_admin/tests/app/use_cases/test_platform_myself_interactor.py`, `backend/apps/platform_admin/tests/adapter/test_platform_myself_router.py`
- Modify: `backend/.importlinter`, `backend/main.py`, `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: Task 8의 `OperatorDirectoryPort`와 `get_check_operator_use_case`, `core.security.get_current_user_id`
- Produces:
  - `platform_admin.domain.errors.NotAnOperatorError` (`code = "PERMISSION_DENIED"`)
  - `platform_admin.adapter.inbound.api.error_map.PLATFORM_ADMIN_ERROR_STATUS`
  - `platform_admin.dependencies.hub_ports.get_operator_directory() -> OperatorDirectoryPort` — 자리
  - `platform_admin.adapter.inbound.api.v1.platform_myself_router.platform_myself_router` (`GET /v1/platform/myself`)

- [ ] **Step 1: 패키지 뼈대를 만든다**

Run (저장소 루트에서):
```bash
cd backend/apps
mkdir -p platform_admin/domain platform_admin/app/{dtos,use_cases} platform_admin/app/ports/{input,output} \
  platform_admin/adapter/inbound/api/{schemas,v1} platform_admin/adapter/outbound \
  platform_admin/dependencies platform_admin/tests/app/use_cases platform_admin/tests/adapter platform_admin/_docs
find platform_admin -type d -not -name _docs -exec touch {}/__init__.py \;
find platform_admin -name __init__.py | wc -l
cd ../..
```
Expected: `19`

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/platform_admin/tests/app/use_cases/test_platform_myself_interactor.py`:
```python
import pytest

from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery
from platform_admin.app.use_cases.platform_myself_interactor import PlatformMyselfInteractor
from platform_admin.domain.errors import NotAnOperatorError


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def is_operator(self, user_id):
        return user_id in self.operator_ids


def _query(user_id):
    return PlatformMyselfQuery(id=3, name="플랫폼 운영 (platform_admin)", user_id=user_id)


async def test_운영자에게_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await PlatformMyselfInteractor(record, _StubOperators([5])).introduce_myself(_query(5))
    assert result.id == 3
    assert "/v1/platform/shops" in result.introduction
    assert "운영자" in result.introduction
    assert record.records[0][0] == "introduce_myself"


async def test_운영자가_아니면_거절하고_기록하지_않는다():
    record = _StubRecord()
    with pytest.raises(NotAnOperatorError):
        await PlatformMyselfInteractor(record, _StubOperators([5])).introduce_myself(_query(6))
    assert record.records == []
```

`backend/apps/platform_admin/tests/adapter/test_platform_myself_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfResponse
from platform_admin.dependencies.platform_myself_provider import get_platform_myself_use_case
from platform_admin.domain.errors import NotAnOperatorError


class _StubUseCase:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def introduce_myself(self, query):
        if query.user_id not in self.operator_ids:
            raise NotAnOperatorError("플랫폼 운영자만 쓸 수 있습니다.")
        return PlatformMyselfResponse(id=query.id, name=query.name, introduction="POST /v1/platform/shops")


async def _no_db():
    yield None


def _app(user_id=None):
    app = FastAPI()
    app.include_router(platform_myself_router)
    install_error_handlers(app, PLATFORM_ADMIN_ERROR_STATUS)
    app.dependency_overrides[get_platform_myself_use_case] = lambda: _StubUseCase([5])
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _get(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/platform/myself")


async def test_운영자는_자기소개를_받는다():
    response = await _get(_app(user_id=5))
    assert response.status_code == 200
    assert response.json()["name"] == "플랫폼 운영 (platform_admin)"


async def test_운영자가_아니면_403_PERMISSION_DENIED_다():
    response = await _get(_app(user_id=6))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")


async def test_토큰이_없으면_401_이다():
    response = await _get(_app())
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/platform_admin -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'platform_admin.app.dtos.platform_myself_dto'`

- [ ] **Step 4: 슬라이스를 구현한다**

`backend/apps/platform_admin/domain/errors.py`:
```python
class PlatformAdminError(Exception):
    """platform_admin 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "PLATFORM_ADMIN_ERROR"


class NotAnOperatorError(PlatformAdminError):
    code = "PERMISSION_DENIED"
```

`backend/apps/platform_admin/adapter/inbound/api/error_map.py`:
```python
"""platform_admin 도메인 오류 → HTTP 상태 코드."""
from platform_admin.domain.errors import NotAnOperatorError

PLATFORM_ADMIN_ERROR_STATUS: dict[type[Exception], int] = {
    NotAnOperatorError: 403,
}
```

`backend/apps/platform_admin/app/dtos/platform_myself_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class PlatformMyselfQuery:
    id: int
    name: str
    user_id: int


@dataclass(frozen=True)
class PlatformMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/platform_admin/app/ports/input/platform_myself_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery, PlatformMyselfResponse


class PlatformMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: PlatformMyselfQuery) -> PlatformMyselfResponse: ...
```

`backend/apps/platform_admin/app/ports/output/platform_myself_record_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class PlatformMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/platform_admin/app/use_cases/platform_myself_interactor.py`:
```python
from __future__ import annotations

from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery, PlatformMyselfResponse
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.app.ports.output.platform_myself_record_port import PlatformMyselfRecordPort
from platform_admin.domain.errors import NotAnOperatorError


class PlatformMyselfInteractor(PlatformMyselfUseCase):
    def __init__(self, record: PlatformMyselfRecordPort, operators: OperatorDirectoryPort) -> None:
        self._record = record
        self._operators = operators

    async def introduce_myself(self, query: PlatformMyselfQuery) -> PlatformMyselfResponse:
        if not await self._operators.is_operator(query.user_id):
            raise NotAnOperatorError("플랫폼 운영자만 쓸 수 있습니다.")
        await self._record.record(
            subject="introduce_myself", note=f"{query.name} 자기소개 조회"
        )
        return PlatformMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "플랫폼 운영자가 쓰는 표면입니다. "
                "POST /v1/platform/shops 는 매장을 개설하고 사장용 초대 코드를 돌려줍니다. "
                "코드 원문은 이 응답에서 한 번만 볼 수 있고 DB 에는 해시만 남습니다. "
                "모든 경로는 액세스 토큰과 플랫폼 운영자 지정이 필요하며 운영자가 아니면 403 입니다. "
                "운영자는 scripts/grant_operator.py 로 지정합니다. "
                "이 스포크는 자기 데이터를 갖지 않고 허브 포트(운영자 확인, 매장 개설)만 씁니다."
            ),
        )
```

`backend/apps/platform_admin/adapter/outbound/log_platform_myself_record_adapter.py`:
```python
from __future__ import annotations

import logging

from platform_admin.app.ports.output.platform_myself_record_port import PlatformMyselfRecordPort

logger = logging.getLogger(__name__)


class LogPlatformMyselfRecordAdapter(PlatformMyselfRecordPort):
    """기록을 로그로 남기는 구현. 영속 기록이 필요해지면 PG 어댑터로 바꾼다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[platform-myself-record] %s | %s", subject, note)
```

`backend/apps/platform_admin/dependencies/hub_ports.py`:
```python
"""허브 포트 자리 — platform_admin 이 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.operator_directory_port import OperatorDirectoryPort


def get_operator_directory() -> OperatorDirectoryPort:
    raise RuntimeError("OperatorDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/platform_admin/dependencies/platform_myself_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from platform_admin.adapter.outbound.log_platform_myself_record_adapter import (
    LogPlatformMyselfRecordAdapter,
)
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.app.use_cases.platform_myself_interactor import PlatformMyselfInteractor
from platform_admin.dependencies.hub_ports import get_operator_directory


def get_platform_myself_use_case(
    operators: OperatorDirectoryPort = Depends(get_operator_directory),
) -> PlatformMyselfUseCase:
    return PlatformMyselfInteractor(record=LogPlatformMyselfRecordAdapter(), operators=operators)
```

`backend/apps/platform_admin/adapter/inbound/api/schemas/platform_myself_schema.py`:
```python
from pydantic import BaseModel


class PlatformMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/platform_admin/adapter/inbound/api/v1/platform_myself_router.py`:
```python
from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from platform_admin.adapter.inbound.api.schemas.platform_myself_schema import (
    PlatformMyselfResponseSchema,
)
from platform_admin.app.dtos.platform_myself_dto import PlatformMyselfQuery
from platform_admin.app.ports.input.platform_myself_use_case import PlatformMyselfUseCase
from platform_admin.dependencies.platform_myself_provider import get_platform_myself_use_case

platform_myself_router = APIRouter(prefix="/v1/platform", tags=["platform"])


@platform_myself_router.get("/myself", response_model=PlatformMyselfResponseSchema)
async def introduce_myself(
    user_id: int = Depends(get_current_user_id),
    use_case: PlatformMyselfUseCase = Depends(get_platform_myself_use_case),
) -> PlatformMyselfResponseSchema:
    result = await use_case.introduce_myself(
        PlatformMyselfQuery(id=3, name="플랫폼 운영 (platform_admin)", user_id=user_id)
    )
    return PlatformMyselfResponseSchema(
        id=result.id, name=result.name, introduction=result.introduction
    )
```

- [ ] **Step 5: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/platform_admin -q -p no:cacheprovider`
Expected: `5 passed`

- [ ] **Step 6: 구조 계약에 스포크를 더한다**

`backend/.importlinter`에서 다섯 곳에 `platform_admin`을 더한다.
- `root_packages`의 `tenancy` 다음 줄에 `    platform_admin`
- `clean-architecture`의 `containers`에서 `tenancy` 다음 줄에 `    platform_admin`
- `spoke-independence`의 `modules`에서 `tenancy` 다음 줄에 `    platform_admin`
- `framework-isolation`의 `source_modules`에서 `tenancy.domain` 다음 두 줄에 `    platform_admin.app`, `    platform_admin.domain`
- `domain-purity`의 `source_modules`에서 `tenancy.domain` 다음 줄에 `    platform_admin.domain`
- `hub-isolation`의 `forbidden_modules`에서 `tenancy` 다음 줄에 `    platform_admin`

Run: 구조 계약
Expected: `Contracts: 5 kept, 0 broken.`

- [ ] **Step 7: 진입점에 장착하고 자리를 채운다**

`backend/main.py`의 import 묶음에 더한다 (`core.shop_guard` 줄 다음).
```python
from auth.dependencies.check_operator_provider import get_check_operator_use_case
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
from platform_admin.dependencies.hub_ports import get_operator_directory
```
`app.include_router(tenancy_myself_router)` 다음 줄에 더한다.
```python
app.include_router(platform_myself_router)
```
`install_error_handlers` 호출을 바꾼다.
```python
install_error_handlers(
    app, {**AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS}
)
```
`app.dependency_overrides[get_shop_access_port] = …` 다음 줄에 더한다.
```python
app.dependency_overrides[get_operator_directory] = get_check_operator_use_case
```

`backend/tests/test_hub_port_binding.py`에서 import와 목록을 고친다.
```python
import main
from core.shop_guard import get_shop_access_port
from platform_admin.dependencies.hub_ports import get_operator_directory

_API_SLOTS = [get_shop_access_port, get_operator_directory]
```

- [ ] **Step 8: 앱 문서와 심볼릭 링크를 만든다**

`backend/apps/platform_admin/_docs/CLAUDE.md`:
```markdown
# platform_admin — 플랫폼 운영자 표면

소유 데이터: 없음. 허브 포트만 쓴다.

- 모든 유스케이스는 첫 줄에서 `OperatorDirectoryPort.is_operator`를 확인한다. 가드 의존성으로 빼지 않는다. 확인을 빠뜨린 슬라이스가 스텁 테스트에서 드러나게 하려는 것이다.
- 운영자가 아니면 `NotAnOperatorError`(403, `PERMISSION_DENIED`)다.
- 매장 개설은 tenancy가 구현한 `ShopProvisioningPort`로 한다. 이 스포크는 매장 테이블을 모른다.
- 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
```

Run (저장소 루트에서): `cd backend/apps/platform_admin && ln -s _docs/CLAUDE.md CLAUDE.md && cd ../../.. && ls -l backend/apps/platform_admin/CLAUDE.md`
Expected: `… backend/apps/platform_admin/CLAUDE.md -> _docs/CLAUDE.md`

- [ ] **Step 9: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

Run: `curl -s -o /dev/null -w '%{http_code}\n' --retry 5 --retry-delay 1 --retry-all-errors http://127.0.0.1:8080/v1/platform/myself`
Expected: `401` (토큰 없음)

```bash
git add backend/apps/platform_admin backend/.importlinter backend/main.py backend/tests/test_hub_port_binding.py
git commit -m "feat(platform_admin): 스포크 골격과 자기소개 슬라이스"
```

---

### Task 10: 매장 개설 (`POST /v1/platform/shops`)

운영자가 매장을 만들면 사장용 초대 코드가 응답으로 돌아온다. platform_admin의 `create_shop` 슬라이스가 tenancy의 `provision_shop` 슬라이스(허브 `ShopProvisioningPort` 구현)를 부른다.

**Files:**
- Create: `backend/apps/hub/app/dtos/provisioned_shop.py`, `backend/apps/hub/app/ports/shop_provisioning_port.py`
- Create: `backend/apps/tenancy/app/use_cases/provision_shop_interactor.py`, `backend/apps/tenancy/dependencies/provision_shop_provider.py`
- Create: `backend/apps/platform_admin/app/dtos/create_shop_dto.py`
- Create: `backend/apps/platform_admin/app/ports/input/create_shop_use_case.py`
- Create: `backend/apps/platform_admin/app/use_cases/create_shop_interactor.py`
- Create: `backend/apps/platform_admin/adapter/inbound/api/schemas/create_shop_schema.py`
- Create: `backend/apps/platform_admin/adapter/inbound/api/v1/create_shop_router.py`
- Create: `backend/apps/platform_admin/dependencies/create_shop_provider.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_provision_shop_interactor.py`, `backend/apps/platform_admin/tests/app/use_cases/test_create_shop_interactor.py`, `backend/apps/platform_admin/tests/adapter/test_create_shop_router.py`
- Modify: `backend/apps/platform_admin/dependencies/hub_ports.py`, `backend/main.py`, `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: Task 4의 `generate_invite_code`·`hash_invite_code`·`INVITE_TTL`, Task 5의 `ShopRepository.create`, Task 6의 `InviteRepository.create_owner_invite`·`build_shop_repository`·`build_invite_repository`, Task 9의 `get_operator_directory`·`NotAnOperatorError`
- Produces:
  - `hub.app.dtos.provisioned_shop.ProvisionedShop(shop_id: int, name: str, owner_invite_code: str, invite_expires_at: datetime)`
  - `hub.app.ports.shop_provisioning_port.ShopProvisioningPort`: `async create_shop(name: str, business_type: str) -> ProvisionedShop`
  - `tenancy.dependencies.provision_shop_provider.get_provision_shop_use_case(db: DbSession) -> ShopProvisioningPort`
  - `platform_admin.dependencies.hub_ports.get_shop_provisioning() -> ShopProvisioningPort` — 자리
  - `platform_admin.app.dtos.create_shop_dto.CreateShopCommand(user_id: int, name: str, business_type: str)`
  - `platform_admin.adapter.inbound.api.v1.create_shop_router.create_shop_router` (`POST /v1/platform/shops` → 201)

- [ ] **Step 1: 허브 계약을 쓴다**

`backend/apps/hub/app/dtos/provisioned_shop.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ProvisionedShop:
    """새로 개설한 매장과 사장용 초대 코드. 코드 원문은 여기서만 볼 수 있다 (DB 에는 해시만 남는다)."""

    shop_id: int
    name: str
    owner_invite_code: str
    invite_expires_at: datetime
```

`backend/apps/hub/app/ports/shop_provisioning_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.provisioned_shop import ProvisionedShop


class ShopProvisioningPort(ABC):
    """구현: tenancy. 사용: platform_admin."""

    @abstractmethod
    async def create_shop(self, name: str, business_type: str) -> ProvisionedShop:
        """매장을 만들고 사장용 초대 코드를 발급한다."""
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_provision_shop_interactor.py`:
```python
from datetime import datetime, timedelta, timezone

from tenancy.app.use_cases.provision_shop_interactor import ProvisionShopInteractor
from tenancy.domain.entities.shop import Shop
from tenancy.domain.services.invite_code import hash_invite_code

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class _StubShops:
    def __init__(self):
        self.created = []

    async def create(self, name, business_type):
        self.created.append((name, business_type))
        return Shop(id=3, name=name, business_type=business_type, phone=None, address=None,
                    timezone="Asia/Seoul", suspended_at=None, closed_at=None)


class _StubInvites:
    def __init__(self):
        self.owner_invites = []

    async def create_owner_invite(self, shop_id, code_hash, expires_at):
        self.owner_invites.append((shop_id, code_hash, expires_at))


async def test_매장을_만들고_사장용_초대_코드를_돌려준다():
    shops, invites = _StubShops(), _StubInvites()
    result = await ProvisionShopInteractor(shops, invites, now=lambda: NOW).create_shop(
        "Hiss Haus", "pet_grooming"
    )
    assert shops.created == [("Hiss Haus", "pet_grooming")]
    assert (result.shop_id, result.name) == (3, "Hiss Haus")
    assert len(result.owner_invite_code) == 8
    assert result.invite_expires_at == NOW + timedelta(days=7)


async def test_초대는_해시로만_저장한다():
    invites = _StubInvites()
    result = await ProvisionShopInteractor(_StubShops(), invites, now=lambda: NOW).create_shop(
        "Hiss Haus", "pet_grooming"
    )
    shop_id, code_hash, expires_at = invites.owner_invites[0]
    assert shop_id == 3
    assert code_hash == hash_invite_code(result.owner_invite_code)
    assert result.owner_invite_code not in code_hash
    assert expires_at == result.invite_expires_at
```

`backend/apps/platform_admin/tests/app/use_cases/test_create_shop_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.use_cases.create_shop_interactor import CreateShopInteractor
from platform_admin.domain.errors import NotAnOperatorError

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubOperators:
    def __init__(self, operator_ids):
        self.operator_ids = set(operator_ids)

    async def is_operator(self, user_id):
        return user_id in self.operator_ids


class _StubProvisioning:
    def __init__(self):
        self.calls = []

    async def create_shop(self, name, business_type):
        self.calls.append((name, business_type))
        return ProvisionedShop(shop_id=3, name=name, owner_invite_code="ABCD2345", invite_expires_at=EXPIRES)


async def test_운영자는_매장을_개설한다():
    provisioning = _StubProvisioning()
    result = await CreateShopInteractor(_StubOperators([5]), provisioning).create_shop(
        CreateShopCommand(user_id=5, name="Hiss Haus", business_type="pet_grooming")
    )
    assert provisioning.calls == [("Hiss Haus", "pet_grooming")]
    assert (result.shop_id, result.owner_invite_code) == (3, "ABCD2345")


async def test_운영자가_아니면_개설하지_않는다():
    provisioning = _StubProvisioning()
    with pytest.raises(NotAnOperatorError):
        await CreateShopInteractor(_StubOperators([5]), provisioning).create_shop(
            CreateShopCommand(user_id=6, name="Hiss Haus", business_type="pet_grooming")
        )
    assert provisioning.calls == []
```

`backend/apps/platform_admin/tests/adapter/test_create_shop_router.py`:
```python
from datetime import datetime, timezone

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
from platform_admin.dependencies.create_shop_provider import get_create_shop_use_case

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def create_shop(self, command):
        self.commands.append(command)
        return ProvisionedShop(shop_id=3, name=command.name, owner_invite_code="ABCD2345",
                               invite_expires_at=EXPIRES)


async def _no_db():
    yield None


def _app(stub, user_id=5):
    app = FastAPI()
    app.include_router(create_shop_router)
    install_error_handlers(app, PLATFORM_ADMIN_ERROR_STATUS)
    app.dependency_overrides[get_create_shop_use_case] = lambda: stub
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _post(app, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/platform/shops", json=body)


async def test_매장을_개설하면_201과_사장용_초대_코드를_돌려준다():
    stub = _StubUseCase()
    response = await _post(_app(stub), {"name": "  Hiss Haus  "})
    assert response.status_code == 201
    assert response.json() == {
        "shop_id": 3, "name": "Hiss Haus", "owner_invite_code": "ABCD2345",
        "invite_expires_at": "2026-09-27T12:00:00Z",
    }
    command = stub.commands[0]
    assert (command.user_id, command.name, command.business_type) == (5, "Hiss Haus", "pet_grooming")


async def test_이름이_비면_422_다():
    response = await _post(_app(_StubUseCase()), {"name": "   "})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_토큰이_없으면_401_이다():
    response = await _post(_app(_StubUseCase(), user_id=None), {"name": "Hiss Haus"})
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/app/use_cases/test_provision_shop_interactor.py apps/platform_admin -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.use_cases.provision_shop_interactor'`

- [ ] **Step 4: tenancy 쪽 슬라이스를 구현한다**

`backend/apps/tenancy/app/use_cases/provision_shop_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from hub.app.dtos.provisioned_shop import ProvisionedShop
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.services.invite_code import INVITE_TTL, generate_invite_code, hash_invite_code


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProvisionShopInteractor(ShopProvisioningPort):
    """허브의 ShopProvisioningPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(
        self, shops: ShopRepository, invites: InviteRepository,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._shops = shops
        self._invites = invites
        self._now = now

    async def create_shop(self, name: str, business_type: str) -> ProvisionedShop:
        shop = await self._shops.create(name, business_type)
        code = generate_invite_code()
        expires_at = self._now() + INVITE_TTL
        await self._invites.create_owner_invite(shop.id, hash_invite_code(code), expires_at)
        return ProvisionedShop(
            shop_id=shop.id, name=shop.name, owner_invite_code=code, invite_expires_at=expires_at
        )
```

`backend/apps/tenancy/dependencies/provision_shop_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from tenancy.app.use_cases.provision_shop_interactor import ProvisionShopInteractor
from tenancy.dependencies.tenancy_wiring import build_invite_repository, build_shop_repository


def get_provision_shop_use_case(db: DbSession) -> ShopProvisioningPort:
    return ProvisionShopInteractor(
        shops=build_shop_repository(db), invites=build_invite_repository(db)
    )
```

- [ ] **Step 5: platform_admin 쪽 슬라이스를 구현한다**

`backend/apps/platform_admin/dependencies/hub_ports.py`에 import 한 줄과 자리 하나를 더한다.
```python
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
```
```python
def get_shop_provisioning() -> ShopProvisioningPort:
    raise RuntimeError("ShopProvisioningPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/platform_admin/app/dtos/create_shop_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CreateShopCommand:
    user_id: int
    name: str
    business_type: str
```

`backend/apps/platform_admin/app/ports/input/create_shop_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.provisioned_shop import ProvisionedShop
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand


class CreateShopUseCase(ABC):
    @abstractmethod
    async def create_shop(self, command: CreateShopCommand) -> ProvisionedShop: ...
```

`backend/apps/platform_admin/app/use_cases/create_shop_interactor.py`:
```python
from __future__ import annotations

from hub.app.dtos.provisioned_shop import ProvisionedShop
from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase
from platform_admin.domain.errors import NotAnOperatorError


class CreateShopInteractor(CreateShopUseCase):
    def __init__(self, operators: OperatorDirectoryPort, provisioning: ShopProvisioningPort) -> None:
        self._operators = operators
        self._provisioning = provisioning

    async def create_shop(self, command: CreateShopCommand) -> ProvisionedShop:
        if not await self._operators.is_operator(command.user_id):
            raise NotAnOperatorError("플랫폼 운영자만 쓸 수 있습니다.")
        return await self._provisioning.create_shop(command.name, command.business_type)
```

`backend/apps/platform_admin/dependencies/create_shop_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from hub.app.ports.operator_directory_port import OperatorDirectoryPort
from hub.app.ports.shop_provisioning_port import ShopProvisioningPort
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase
from platform_admin.app.use_cases.create_shop_interactor import CreateShopInteractor
from platform_admin.dependencies.hub_ports import get_operator_directory, get_shop_provisioning


def get_create_shop_use_case(
    operators: OperatorDirectoryPort = Depends(get_operator_directory),
    provisioning: ShopProvisioningPort = Depends(get_shop_provisioning),
) -> CreateShopUseCase:
    return CreateShopInteractor(operators=operators, provisioning=provisioning)
```

`backend/apps/platform_admin/adapter/inbound/api/schemas/create_shop_schema.py`:
```python
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class CreateShopRequestSchema(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    business_type: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)
    ] = "pet_grooming"


class CreateShopResponseSchema(BaseModel):
    shop_id: int
    name: str
    owner_invite_code: str = Field(description="사장에게 전달한다. 이 응답에서 한 번만 볼 수 있다.")
    invite_expires_at: datetime
```

`backend/apps/platform_admin/adapter/inbound/api/v1/create_shop_router.py`:
```python
from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from platform_admin.adapter.inbound.api.schemas.create_shop_schema import (
    CreateShopRequestSchema,
    CreateShopResponseSchema,
)
from platform_admin.app.dtos.create_shop_dto import CreateShopCommand
from platform_admin.app.ports.input.create_shop_use_case import CreateShopUseCase
from platform_admin.dependencies.create_shop_provider import get_create_shop_use_case

create_shop_router = APIRouter(prefix="/v1/platform", tags=["platform"])


@create_shop_router.post("/shops", response_model=CreateShopResponseSchema, status_code=201)
async def create_shop(
    body: CreateShopRequestSchema,
    user_id: int = Depends(get_current_user_id),
    use_case: CreateShopUseCase = Depends(get_create_shop_use_case),
) -> CreateShopResponseSchema:
    shop = await use_case.create_shop(
        CreateShopCommand(user_id=user_id, name=body.name, business_type=body.business_type)
    )
    return CreateShopResponseSchema(
        shop_id=shop.shop_id,
        name=shop.name,
        owner_invite_code=shop.owner_invite_code,
        invite_expires_at=shop.invite_expires_at,
    )
```

- [ ] **Step 6: 진입점에 장착하고 자리를 채운다**

`backend/main.py`의 import 묶음에 더한다.
```python
from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
from platform_admin.dependencies.hub_ports import get_operator_directory, get_shop_provisioning
from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_case
```
(`get_operator_directory`만 import하던 기존 줄은 위 줄로 바꾼다.)

`app.include_router(platform_myself_router)` 다음 줄에 더한다.
```python
app.include_router(create_shop_router)
```
자리 채우기 묶음의 끝에 더한다.
```python
app.dependency_overrides[get_shop_provisioning] = get_provision_shop_use_case
```

`backend/tests/test_hub_port_binding.py`에서 import와 목록을 고친다.
```python
from platform_admin.dependencies.hub_ports import get_operator_directory, get_shop_provisioning

_API_SLOTS = [get_shop_access_port, get_operator_directory, get_shop_provisioning]
```

- [ ] **Step 7: 통과를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/app/use_cases/test_provision_shop_interactor.py apps/platform_admin tests/test_hub_port_binding.py -q -p no:cacheprovider`
Expected: `13 passed` (provision 2 + platform_admin 10 + 자리 1)

- [ ] **Step 8: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/hub backend/apps/tenancy backend/apps/platform_admin backend/main.py backend/tests/test_hub_port_binding.py
git commit -m "feat(platform_admin): 매장 개설과 사장용 초대 코드 발급"
```

---

### Task 11: 초대 수락 (`POST /v1/invites/accept`)

로그인한 유저가 초대 코드를 넣으면 그 초대의 역할로 매장에 합류한다. 입력 시도는 유저당 분당 5회다. 아직 매장 소속이 아니므로 `ShopContext`가 없는 경로다.

**Files:**
- Create: `backend/apps/tenancy/tests/helpers/__init__.py` (빈 파일), `backend/apps/tenancy/tests/helpers/api.py`
- Create: `backend/apps/tenancy/app/dtos/accept_invite_dto.py`
- Create: `backend/apps/tenancy/app/ports/input/accept_invite_use_case.py`
- Create: `backend/apps/tenancy/app/use_cases/accept_invite_interactor.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/schemas/accept_invite_schema.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/v1/accept_invite_router.py`
- Create: `backend/apps/tenancy/dependencies/accept_invite_provider.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py`, `backend/apps/tenancy/tests/adapter/test_accept_invite_router.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: Task 4의 `Invite.ensure_usable`·`hash_invite_code`·오류들, Task 5의 `ShopRepository.get_by_id`·`MemberRepository.add`, Task 6의 `InviteRepository.find_by_code_hash_for_update`·`mark_used`·`InviteAttemptLimiterPort.hit`·조립 함수들, Task 7의 `TENANCY_ERROR_STATUS`·`get_shop_access_port`
- Produces:
  - `tenancy.app.dtos.accept_invite_dto`: `AcceptInviteCommand(user_id: int, code: str)`, `AcceptInviteResult(shop_id: int, shop_name: str, role: str, member_id: int)`
  - `tenancy.app.use_cases.accept_invite_interactor.MAX_INVITE_ATTEMPTS_PER_MINUTE = 5`
  - `tenancy.adapter.inbound.api.v1.accept_invite_router.accept_invite_router`
  - 테스트 도우미 `tenancy.tests.helpers.api`: `OWNER_PERMISSIONS`, `STAFF_PERMISSIONS`, `StubShopAccess(permissions=(), role="owner", member_id=11)`(필드 `calls`), `build_app(router, provider, stub_use_case, access=None, user_id=5) -> FastAPI`. Task 12~15의 라우터 테스트가 쓴다.

- [ ] **Step 1: 라우터 테스트 도우미를 쓴다**

`backend/apps/tenancy/tests/helpers/api.py`:
```python
"""tenancy 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다."""
from __future__ import annotations

from fastapi import FastAPI

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS

STAFF_PERMISSIONS = ("reservation:write", "customer:write", "record:write", "sales:write")
OWNER_PERMISSIONS = STAFF_PERMISSIONS + (
    "sales:read", "record:delete", "customer:delete", "member:manage", "shop:update",
)


class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=(), role="owner", member_id=11):
        self.permissions = frozenset(permissions)
        self.role = role
        self.member_id = member_id
        self.calls = []

    async def resolve(self, user_id, shop_id):
        self.calls.append((user_id, shop_id))
        return ShopContext(
            shop_id=shop_id, member_id=self.member_id, role=self.role, permissions=self.permissions
        )


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None, user_id=5) -> FastAPI:
    """user_id=None 이면 토큰 없는 요청이 된다. access=None 이면 매장 접근 확인 자리를 채우지 않는다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, TENANCY_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    if access is not None:
        app.dependency_overrides[get_shop_access_port] = lambda: access
    return app
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py`:
```python
from datetime import datetime, timedelta, timezone

import pytest

from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.domain.entities.invite import Invite
from tenancy.domain.entities.member import Member
from tenancy.domain.entities.shop import Shop
from tenancy.domain.errors import (
    AlreadyMemberError,
    InviteExhaustedError,
    InviteExpiredError,
    InviteInvalidError,
    ShopClosedError,
    TooManyAttemptsError,
)
from tenancy.domain.services.invite_code import hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class _StubInvites:
    def __init__(self, invite):
        self.invite = invite
        self.lookups = []
        self.used = []

    async def find_by_code_hash_for_update(self, code_hash):
        self.lookups.append(code_hash)
        return self.invite

    async def mark_used(self, invite_id):
        self.used.append(invite_id)


class _StubMembers:
    def __init__(self, already_member=False):
        self.already_member = already_member
        self.added = []

    async def add(self, shop_id, user_id, role):
        if self.already_member:
            raise AlreadyMemberError("이미 이 매장의 멤버입니다.")
        self.added.append((shop_id, user_id, role))
        return Member(id=21, shop_id=shop_id, user_id=user_id, role=role, joined_at=NOW)


class _StubShops:
    def __init__(self, closed=False):
        self.closed = closed

    async def get_by_id(self, shop_id):
        return Shop(id=shop_id, name="Hiss Haus", business_type="pet_grooming", phone=None,
                    address=None, timezone="Asia/Seoul", suspended_at=None,
                    closed_at=NOW if self.closed else None)


class _StubLimiter:
    def __init__(self, count=1):
        self.count = count

    async def hit(self, user_id):
        return self.count


def _invite(**overrides):
    base = dict(id=9, shop_id=3, role=RoleCode.OWNER, expires_at=NOW + timedelta(days=7),
                max_uses=1, used_count=0, revoked_at=None)
    return Invite(**{**base, **overrides})


def _interactor(invites, members=None, shops=None, limiter=None):
    return AcceptInviteInteractor(
        invites=invites, members=members or _StubMembers(), shops=shops or _StubShops(),
        limiter=limiter or _StubLimiter(), now=lambda: NOW,
    )


async def test_코드가_맞으면_초대의_역할로_합류하고_초대를_쓴_것으로_표시한다():
    invites, members = _StubInvites(_invite()), _StubMembers()
    result = await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ABCD2345"))
    assert members.added == [(3, 5, RoleCode.OWNER)]
    assert invites.used == [9]
    assert (result.shop_id, result.shop_name, result.role, result.member_id) == (3, "Hiss Haus", "owner", 21)


async def test_입력한_모양이_달라도_같은_해시로_찾는다():
    invites = _StubInvites(_invite())
    await _interactor(invites).accept(AcceptInviteCommand(user_id=5, code=" abcd-2345 "))
    assert invites.lookups == [hash_invite_code("ABCD2345")]


async def test_분당_다섯_번을_넘으면_코드를_찾아보지도_않는다():
    invites = _StubInvites(_invite())
    with pytest.raises(TooManyAttemptsError):
        await _interactor(invites, limiter=_StubLimiter(count=6)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert invites.lookups == []


async def test_다섯_번째_시도까지는_받는다():
    invites = _StubInvites(_invite())
    await _interactor(invites, limiter=_StubLimiter(count=5)).accept(
        AcceptInviteCommand(user_id=5, code="ABCD2345")
    )
    assert invites.used == [9]


async def test_모르는_코드는_INVITE_INVALID_다():
    with pytest.raises(InviteInvalidError):
        await _interactor(_StubInvites(None)).accept(AcceptInviteCommand(user_id=5, code="ZZZZ9999"))


async def test_만료된_코드는_INVITE_EXPIRED_다():
    invites, members = _StubInvites(_invite(expires_at=NOW)), _StubMembers()
    with pytest.raises(InviteExpiredError):
        await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ABCD2345"))
    assert members.added == []


async def test_이미_쓴_코드는_INVITE_EXHAUSTED_다():
    with pytest.raises(InviteExhaustedError):
        await _interactor(_StubInvites(_invite(used_count=1))).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )


async def test_닫힌_매장에는_합류할_수_없다():
    invites, members = _StubInvites(_invite()), _StubMembers()
    with pytest.raises(ShopClosedError):
        await _interactor(invites, members, shops=_StubShops(closed=True)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert members.added == [] and invites.used == []


async def test_이미_멤버면_초대를_쓰지_않는다():
    invites = _StubInvites(_invite())
    with pytest.raises(AlreadyMemberError):
        await _interactor(invites, _StubMembers(already_member=True)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert invites.used == []
```

`backend/apps/tenancy/tests/adapter/test_accept_invite_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.accept_invite_router import accept_invite_router
from tenancy.app.dtos.accept_invite_dto import AcceptInviteResult
from tenancy.dependencies.accept_invite_provider import get_accept_invite_use_case
from tenancy.domain.errors import InviteExpiredError, TooManyAttemptsError
from tenancy.tests.helpers.api import build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def accept(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return AcceptInviteResult(shop_id=3, shop_name="Hiss Haus", role="owner", member_id=21)


async def _post(stub, body, user_id=5):
    app = build_app(accept_invite_router, get_accept_invite_use_case, stub, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/invites/accept", json=body)


async def test_합류하면_매장과_역할을_돌려준다():
    stub = _StubUseCase()
    response = await _post(stub, {"code": "abcd-2345"})
    assert response.status_code == 200
    assert response.json() == {"shop_id": 3, "shop_name": "Hiss Haus", "role": "owner", "member_id": 21}
    assert (stub.commands[0].user_id, stub.commands[0].code) == (5, "abcd-2345")


async def test_만료된_코드는_400_INVITE_EXPIRED_다():
    response = await _post(_StubUseCase(InviteExpiredError("만료된 초대 코드입니다.")), {"code": "ABCD2345"})
    assert (response.status_code, response.json()["code"]) == (400, "INVITE_EXPIRED")


async def test_시도가_너무_많으면_429_TOO_MANY_ATTEMPTS_다():
    response = await _post(_StubUseCase(TooManyAttemptsError("잠시 뒤에 다시 시도해 주세요.")), {"code": "ABCD2345"})
    assert (response.status_code, response.json()["code"]) == (429, "TOO_MANY_ATTEMPTS")


async def test_코드가_비면_422_다():
    response = await _post(_StubUseCase(), {"code": "  "})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_토큰이_없으면_401_이다():
    response = await _post(_StubUseCase(), {"code": "ABCD2345"}, user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py apps/tenancy/tests/adapter/test_accept_invite_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.dtos.accept_invite_dto'`

- [ ] **Step 4: 슬라이스를 구현한다**

`backend/apps/tenancy/app/dtos/accept_invite_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class AcceptInviteCommand:
    user_id: int
    code: str


@dataclass(frozen=True)
class AcceptInviteResult:
    shop_id: int
    shop_name: str
    role: str
    member_id: int
```

`backend/apps/tenancy/app/ports/input/accept_invite_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand, AcceptInviteResult


class AcceptInviteUseCase(ABC):
    @abstractmethod
    async def accept(self, command: AcceptInviteCommand) -> AcceptInviteResult: ...
```

`backend/apps/tenancy/app/use_cases/accept_invite_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand, AcceptInviteResult
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.app.ports.output.invite_attempt_limiter_port import InviteAttemptLimiterPort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.errors import InviteInvalidError, ShopClosedError, TooManyAttemptsError
from tenancy.domain.services.invite_code import hash_invite_code

MAX_INVITE_ATTEMPTS_PER_MINUTE = 5


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AcceptInviteInteractor(AcceptInviteUseCase):
    def __init__(
        self, invites: InviteRepository, members: MemberRepository, shops: ShopRepository,
        limiter: InviteAttemptLimiterPort, now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._invites = invites
        self._members = members
        self._shops = shops
        self._limiter = limiter
        self._now = now

    async def accept(self, command: AcceptInviteCommand) -> AcceptInviteResult:
        # 8자리 코드를 마구 넣어 보는 것을 막는다. 성공·실패를 가리지 않고 센다.
        if await self._limiter.hit(command.user_id) > MAX_INVITE_ATTEMPTS_PER_MINUTE:
            raise TooManyAttemptsError("초대 코드 입력이 너무 잦습니다. 1분 뒤에 다시 시도해 주세요.")
        invite = await self._invites.find_by_code_hash_for_update(hash_invite_code(command.code))
        if invite is None:
            raise InviteInvalidError("초대 코드를 확인해 주세요.")
        invite.ensure_usable(self._now())
        shop = await self._shops.get_by_id(invite.shop_id)
        if shop.is_closed:
            raise ShopClosedError("닫힌 매장입니다.")
        member = await self._members.add(invite.shop_id, command.user_id, invite.role)
        await self._invites.mark_used(invite.id)
        return AcceptInviteResult(
            shop_id=shop.id, shop_name=shop.name, role=member.role.value, member_id=member.id
        )
```

`backend/apps/tenancy/dependencies/accept_invite_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.dependencies.tenancy_wiring import (
    build_invite_attempt_limiter,
    build_invite_repository,
    build_member_repository,
    build_shop_repository,
)


def get_accept_invite_use_case(db: DbSession) -> AcceptInviteUseCase:
    return AcceptInviteInteractor(
        invites=build_invite_repository(db),
        members=build_member_repository(db),
        shops=build_shop_repository(db),
        limiter=build_invite_attempt_limiter(),
    )
```

`backend/apps/tenancy/adapter/inbound/api/schemas/accept_invite_schema.py`:
```python
from typing import Annotated

from pydantic import BaseModel, StringConstraints


class AcceptInviteRequestSchema(BaseModel):
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=32)]


class AcceptInviteResponseSchema(BaseModel):
    shop_id: int
    shop_name: str
    role: str
    member_id: int
```

`backend/apps/tenancy/adapter/inbound/api/v1/accept_invite_router.py`:
```python
from fastapi import APIRouter, Depends

from core.security import get_current_user_id
from tenancy.adapter.inbound.api.schemas.accept_invite_schema import (
    AcceptInviteRequestSchema,
    AcceptInviteResponseSchema,
)
from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.dependencies.accept_invite_provider import get_accept_invite_use_case

accept_invite_router = APIRouter(prefix="/v1/invites", tags=["invites"])


@accept_invite_router.post("/accept", response_model=AcceptInviteResponseSchema)
async def accept_invite(
    body: AcceptInviteRequestSchema,
    user_id: int = Depends(get_current_user_id),
    use_case: AcceptInviteUseCase = Depends(get_accept_invite_use_case),
) -> AcceptInviteResponseSchema:
    result = await use_case.accept(AcceptInviteCommand(user_id=user_id, code=body.code))
    return AcceptInviteResponseSchema(
        shop_id=result.shop_id, shop_name=result.shop_name,
        role=result.role, member_id=result.member_id,
    )
```

- [ ] **Step 5: 진입점에 장착한다**

`backend/main.py`의 import 묶음에 더한다.
```python
from tenancy.adapter.inbound.api.v1.accept_invite_router import accept_invite_router
```
`app.include_router(tenancy_myself_router)` 다음 줄에 더한다.
```python
app.include_router(accept_invite_router)
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 3의 명령
Expected: `14 passed`

- [ ] **Step 7: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/tenancy backend/main.py
git commit -m "feat(tenancy): 초대 수락 슬라이스 POST /v1/invites/accept"
```

---

### Task 12: 직원용 초대 코드 만들기 (`POST /v1/shops/{shop_id}/invites`)

`member:manage` 권한이 있는 멤버(사장)가 직원용 초대 코드를 만든다. 역할은 언제나 직원이다. 사장을 늘리려면 합류한 뒤 역할을 바꾼다(Task 14). `require_permission`을 쓰는 첫 경로다.

**Files:**
- Create: `backend/apps/tenancy/app/dtos/create_invite_dto.py`
- Create: `backend/apps/tenancy/app/ports/input/create_invite_use_case.py`
- Create: `backend/apps/tenancy/app/use_cases/create_invite_interactor.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/schemas/create_invite_schema.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/v1/create_invite_router.py`
- Create: `backend/apps/tenancy/dependencies/create_invite_provider.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_create_invite_interactor.py`, `backend/apps/tenancy/tests/adapter/test_create_invite_router.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: Task 4의 `generate_invite_code`·`hash_invite_code`·`INVITE_TTL`·`RoleCode`, Task 5의 `ShopContext`, Task 6의 `InviteRepository.create`·`build_invite_repository`, Task 7의 `require_permission`, Task 11의 `tenancy.tests.helpers.api`
- Produces:
  - `tenancy.app.dtos.create_invite_dto`: `CreateInviteCommand(ctx: ShopContext)`, `CreatedInvite(code: str, role: str, expires_at: datetime)`
  - `tenancy.adapter.inbound.api.v1.create_invite_router.create_invite_router` (201)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_create_invite_interactor.py`:
```python
from datetime import datetime, timedelta, timezone

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.create_invite_dto import CreateInviteCommand
from tenancy.app.use_cases.create_invite_interactor import CreateInviteInteractor
from tenancy.domain.services.invite_code import hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


class _StubInvites:
    def __init__(self):
        self.created = []

    async def create(self, ctx, role, code_hash, expires_at, max_uses):
        self.created.append((ctx, role, code_hash, expires_at, max_uses))


async def test_직원용_1회_초대를_7일_기한으로_만든다():
    invites = _StubInvites()
    result = await CreateInviteInteractor(invites, now=lambda: NOW).create(CreateInviteCommand(ctx=CTX))
    ctx, role, code_hash, expires_at, max_uses = invites.created[0]
    assert (ctx, role, max_uses) == (CTX, RoleCode.STAFF, 1)
    assert expires_at == NOW + timedelta(days=7)
    assert code_hash == hash_invite_code(result.code)
    assert (len(result.code), result.role, result.expires_at) == (8, "staff", expires_at)
```

`backend/apps/tenancy/tests/adapter/test_create_invite_router.py`:
```python
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.create_invite_router import create_invite_router
from tenancy.app.dtos.create_invite_dto import CreatedInvite
from tenancy.dependencies.create_invite_provider import get_create_invite_use_case
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app

EXPIRES = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def create(self, command):
        self.commands.append(command)
        return CreatedInvite(code="ABCD2345", role="staff", expires_at=EXPIRES)


async def _post(stub, access, user_id=5):
    app = build_app(create_invite_router, get_create_invite_use_case, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/invites")


async def test_사장은_초대_코드를_받는다():
    stub, access = _StubUseCase(), StubShopAccess(OWNER_PERMISSIONS)
    response = await _post(stub, access)
    assert response.status_code == 201
    assert response.json() == {"code": "ABCD2345", "role": "staff", "expires_at": "2026-09-27T12:00:00Z"}
    assert access.calls == [(5, 3)]
    assert stub.commands[0].ctx.shop_id == 3


async def test_권한_없는_직원은_403_이고_유스케이스를_부르지_않는다():
    stub = _StubUseCase()
    response = await _post(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_토큰이_없으면_401_이다():
    response = await _post(_StubUseCase(), StubShopAccess(OWNER_PERMISSIONS), user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests/app/use_cases/test_create_invite_interactor.py apps/tenancy/tests/adapter/test_create_invite_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.dtos.create_invite_dto'`

- [ ] **Step 3: 슬라이스를 구현한다**

`backend/apps/tenancy/app/dtos/create_invite_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class CreateInviteCommand:
    ctx: ShopContext


@dataclass(frozen=True)
class CreatedInvite:
    code: str
    role: str
    expires_at: datetime
```

`backend/apps/tenancy/app/ports/input/create_invite_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.create_invite_dto import CreatedInvite, CreateInviteCommand


class CreateInviteUseCase(ABC):
    @abstractmethod
    async def create(self, command: CreateInviteCommand) -> CreatedInvite: ...
```

`backend/apps/tenancy/app/use_cases/create_invite_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from tenancy.app.dtos.create_invite_dto import CreatedInvite, CreateInviteCommand
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.domain.services.invite_code import INVITE_TTL, generate_invite_code, hash_invite_code
from tenancy.domain.value_objects.role_code import RoleCode


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CreateInviteInteractor(CreateInviteUseCase):
    """직원용 초대만 만든다. 사장을 늘리려면 합류한 뒤 역할을 바꾼다."""

    def __init__(self, invites: InviteRepository, now: Callable[[], datetime] = _utcnow) -> None:
        self._invites = invites
        self._now = now

    async def create(self, command: CreateInviteCommand) -> CreatedInvite:
        code = generate_invite_code()
        expires_at = self._now() + INVITE_TTL
        await self._invites.create(
            command.ctx, RoleCode.STAFF, hash_invite_code(code), expires_at, max_uses=1
        )
        return CreatedInvite(code=code, role=RoleCode.STAFF.value, expires_at=expires_at)
```

`backend/apps/tenancy/dependencies/create_invite_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.app.use_cases.create_invite_interactor import CreateInviteInteractor
from tenancy.dependencies.tenancy_wiring import build_invite_repository


def get_create_invite_use_case(db: DbSession) -> CreateInviteUseCase:
    return CreateInviteInteractor(invites=build_invite_repository(db))
```

`backend/apps/tenancy/adapter/inbound/api/schemas/create_invite_schema.py`:
```python
from datetime import datetime

from pydantic import BaseModel, Field


class CreateInviteResponseSchema(BaseModel):
    code: str = Field(description="직원에게 전달한다. 이 응답에서 한 번만 볼 수 있다.")
    role: str
    expires_at: datetime
```

`backend/apps/tenancy/adapter/inbound/api/v1/create_invite_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.create_invite_schema import CreateInviteResponseSchema
from tenancy.app.dtos.create_invite_dto import CreateInviteCommand
from tenancy.app.ports.input.create_invite_use_case import CreateInviteUseCase
from tenancy.dependencies.create_invite_provider import get_create_invite_use_case

create_invite_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@create_invite_router.post(
    "/{shop_id}/invites", response_model=CreateInviteResponseSchema, status_code=201
)
async def create_invite(
    ctx: ShopContext = Depends(require_permission("member:manage")),
    use_case: CreateInviteUseCase = Depends(get_create_invite_use_case),
) -> CreateInviteResponseSchema:
    invite = await use_case.create(CreateInviteCommand(ctx=ctx))
    return CreateInviteResponseSchema(code=invite.code, role=invite.role, expires_at=invite.expires_at)
```

- [ ] **Step 4: 진입점에 장착한다**

`backend/main.py`의 import 묶음에 더한다.
```python
from tenancy.adapter.inbound.api.v1.create_invite_router import create_invite_router
```
`app.include_router(accept_invite_router)` 다음 줄에 더한다.
```python
app.include_router(create_invite_router)
```

- [ ] **Step 5: 통과를 확인한다**

Run: Step 2의 명령
Expected: `4 passed`

- [ ] **Step 6: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/tenancy backend/main.py
git commit -m "feat(tenancy): 직원용 초대 코드 만들기 슬라이스"
```

---

### Task 13: 멤버 목록 (`GET /v1/shops/{shop_id}/members`)과 `UserDirectoryPort`

tenancy는 유저의 이름과 사진을 모른다(`shop_members.user_id`만 안다). 허브의 `UserDirectoryPort`를 auth가 구현하고, tenancy는 자리로 받는다. 멤버 목록은 소속이면 누구나 볼 수 있다.

**Files:**
- Create: `backend/apps/hub/app/dtos/user_profile.py`, `backend/apps/hub/app/ports/user_directory_port.py`
- Create: `backend/apps/auth/app/use_cases/get_user_profiles_interactor.py`, `backend/apps/auth/dependencies/get_user_profiles_provider.py`
- Create: `backend/apps/tenancy/dependencies/hub_ports.py`
- Create: `backend/apps/tenancy/app/dtos/list_members_dto.py`
- Create: `backend/apps/tenancy/app/ports/input/list_members_use_case.py`
- Create: `backend/apps/tenancy/app/use_cases/list_members_interactor.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/schemas/list_members_schema.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/v1/list_members_router.py`
- Create: `backend/apps/tenancy/dependencies/list_members_provider.py`
- Test: `backend/apps/auth/tests/app/use_cases/test_get_user_profiles_interactor.py`, `backend/apps/tenancy/tests/app/use_cases/test_list_members_interactor.py`, `backend/apps/tenancy/tests/adapter/test_list_members_router.py`
- Modify: `backend/apps/auth/app/ports/output/user_repository.py`, `backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`, `backend/apps/auth/tests/adapter/test_user_pg_repository.py`, `backend/main.py`, `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: Task 5의 `MemberRepository.list_active`·`Member`, Task 6의 `build_member_repository`, Task 7의 `get_shop_context`, Task 11의 테스트 도우미, `auth.dependencies.auth_wiring.build_user_repository`
- Produces:
  - `hub.app.dtos.user_profile.UserProfile(user_id: int, display_name: str, profile_image_url: str | None)`
  - `hub.app.ports.user_directory_port.UserDirectoryPort`: `async get_profiles(user_ids: Sequence[int]) -> dict[int, UserProfile]`
  - `auth.app.ports.output.user_repository.UserRepository.list_by_ids(user_ids: Sequence[int]) -> list[User]` (새 메서드)
  - `auth.dependencies.get_user_profiles_provider.get_get_user_profiles_use_case(db: DbSession) -> UserDirectoryPort`
  - `tenancy.dependencies.hub_ports.get_user_directory() -> UserDirectoryPort` — 자리
  - `tenancy.app.dtos.list_members_dto`: `ListMembersQuery(ctx: ShopContext)`, `MemberView(member_id, user_id, display_name, profile_image_url, role: str, joined_at: datetime)`
  - `tenancy.adapter.inbound.api.v1.list_members_router.list_members_router`

- [ ] **Step 1: 허브 계약을 쓴다**

`backend/apps/hub/app/dtos/user_profile.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserProfile:
    """다른 스포크에 보여 줘도 되는 유저 정보. 전화번호와 로그인 수단은 넣지 않는다."""

    user_id: int
    display_name: str
    profile_image_url: str | None
```

`backend/apps/hub/app/ports/user_directory_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from hub.app.dtos.user_profile import UserProfile


class UserDirectoryPort(ABC):
    """구현: auth. 사용: tenancy."""

    @abstractmethod
    async def get_profiles(self, user_ids: Sequence[int]) -> dict[int, UserProfile]:
        """유저 ID → 프로필. 한 번에 묶어서 조회한다."""
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_user_pg_repository.py`의 끝에 더한다.
```python


async def test_여러_유저를_ID_로_한_번에_읽는다(db_session):
    repo = _repo(db_session)
    first = await repo.create_with_identity(_profile(provider_user_id="kakao-1", display_name="하나"))
    second = await repo.create_with_identity(_profile(provider_user_id="kakao-2", display_name="둘"))
    await repo.create_with_identity(_profile(provider_user_id="kakao-3", display_name="셋"))
    users = await repo.list_by_ids([second.id, first.id])
    assert sorted(u.display_name for u in users) == ["둘", "하나"]
    assert await repo.list_by_ids([]) == []
```

`backend/apps/auth/tests/app/use_cases/test_get_user_profiles_interactor.py`:
```python
from auth.app.use_cases.get_user_profiles_interactor import GetUserProfilesInteractor
from auth.domain.entities.user import User
from hub.app.dtos.user_profile import UserProfile


class _StubUsers:
    def __init__(self, users):
        self.users = users
        self.calls = []

    async def list_by_ids(self, user_ids):
        self.calls.append(list(user_ids))
        return self.users


def _user(user_id, name, image=None):
    return User(id=user_id, display_name=name, profile_image_url=image, phone="010-0000-0000",
                suspended_at=None, deleted_at=None)


async def test_유저_ID_로_프로필을_묶어_돌려준다():
    users = _StubUsers([_user(1, "사장님", "https://img/1.jpg"), _user(2, "직원")])
    profiles = await GetUserProfilesInteractor(users).get_profiles([1, 2])
    assert profiles == {
        1: UserProfile(user_id=1, display_name="사장님", profile_image_url="https://img/1.jpg"),
        2: UserProfile(user_id=2, display_name="직원", profile_image_url=None),
    }
    assert users.calls == [[1, 2]]
```

`backend/apps/tenancy/tests/app/use_cases/test_list_members_interactor.py`:
```python
from datetime import datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.user_profile import UserProfile
from tenancy.app.dtos.list_members_dto import ListMembersQuery
from tenancy.app.use_cases.list_members_interactor import ListMembersInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset())


class _StubMembers:
    def __init__(self, members):
        self.members = members
        self.contexts = []

    async def list_active(self, ctx):
        self.contexts.append(ctx)
        return self.members


class _StubUsers:
    def __init__(self):
        self.calls = []

    async def get_profiles(self, user_ids):
        self.calls.append(list(user_ids))
        return {
            1: UserProfile(user_id=1, display_name="사장님", profile_image_url="https://img/1.jpg"),
            2: UserProfile(user_id=2, display_name="직원", profile_image_url=None),
        }


async def test_멤버에_이름과_사진을_붙여_돌려준다():
    members = _StubMembers([
        Member(id=11, shop_id=3, user_id=1, role=RoleCode.OWNER, joined_at=JOINED),
        Member(id=12, shop_id=3, user_id=2, role=RoleCode.STAFF, joined_at=JOINED),
    ])
    users = _StubUsers()
    views = await ListMembersInteractor(members, users).list_members(ListMembersQuery(ctx=CTX))
    assert members.contexts == [CTX]
    assert users.calls == [[1, 2]]
    assert [(v.member_id, v.user_id, v.display_name, v.role) for v in views] == [
        (11, 1, "사장님", "owner"), (12, 2, "직원", "staff"),
    ]
    assert views[0].profile_image_url == "https://img/1.jpg" and views[0].joined_at == JOINED
```

`backend/apps/tenancy/tests/adapter/test_list_members_router.py`:
```python
from datetime import datetime, timezone

from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.list_members_router import list_members_router
from tenancy.app.dtos.list_members_dto import MemberView
from tenancy.dependencies.list_members_provider import get_list_members_use_case
from tenancy.tests.helpers.api import STAFF_PERMISSIONS, StubShopAccess, build_app

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def list_members(self, query):
        self.queries.append(query)
        return [MemberView(member_id=11, user_id=1, display_name="사장님",
                           profile_image_url=None, role="owner", joined_at=JOINED)]


async def _get(stub, access, user_id=5):
    app = build_app(list_members_router, get_list_members_use_case, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/shops/3/members")


async def test_직원도_멤버_목록을_본다():
    stub = _StubUseCase()
    response = await _get(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert response.status_code == 200
    assert response.json() == [{
        "member_id": 11, "user_id": 1, "display_name": "사장님", "profile_image_url": None,
        "role": "owner", "joined_at": "2026-09-20T12:00:00Z",
    }]
    assert stub.queries[0].ctx.shop_id == 3


async def test_토큰이_없으면_401_이다():
    response = await _get(_StubUseCase(), StubShopAccess(), user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_get_user_profiles_interactor.py apps/auth/tests/adapter/test_user_pg_repository.py apps/tenancy/tests/app/use_cases/test_list_members_interactor.py apps/tenancy/tests/adapter/test_list_members_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError`(새 모듈들)와 `AttributeError: 'UserPgRepository' object has no attribute 'list_by_ids'`

- [ ] **Step 4: auth 쪽을 구현한다**

`backend/apps/auth/app/ports/output/user_repository.py`에 import 한 줄과 메서드 하나를 더한다.
```python
from collections.abc import Sequence
```
```python
    @abstractmethod
    async def list_by_ids(self, user_ids: Sequence[int]) -> list[User]: ...
```

`backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`에 import 한 줄과 메서드 하나를 더한다.
```python
from collections.abc import Sequence
```
```python
    async def list_by_ids(self, user_ids: Sequence[int]) -> list[User]:
        if not user_ids:
            return []
        stmt = select(UserOrm).where(UserOrm.id.in_(user_ids))
        return [to_user(row) for row in (await self._session.execute(stmt)).scalars()]
```

`backend/apps/auth/app/use_cases/get_user_profiles_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Sequence

from auth.app.ports.output.user_repository import UserRepository
from hub.app.dtos.user_profile import UserProfile
from hub.app.ports.user_directory_port import UserDirectoryPort


class GetUserProfilesInteractor(UserDirectoryPort):
    """허브의 UserDirectoryPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def get_profiles(self, user_ids: Sequence[int]) -> dict[int, UserProfile]:
        return {
            user.id: UserProfile(
                user_id=user.id,
                display_name=user.display_name,
                profile_image_url=user.profile_image_url,
            )
            for user in await self._users.list_by_ids(user_ids)
        }
```

`backend/apps/auth/dependencies/get_user_profiles_provider.py`:
```python
from __future__ import annotations

from auth.app.use_cases.get_user_profiles_interactor import GetUserProfilesInteractor
from auth.dependencies.auth_wiring import build_user_repository
from core.database import DbSession
from hub.app.ports.user_directory_port import UserDirectoryPort


def get_get_user_profiles_use_case(db: DbSession) -> UserDirectoryPort:
    return GetUserProfilesInteractor(users=build_user_repository(db))
```

- [ ] **Step 5: tenancy 쪽을 구현한다**

`backend/apps/tenancy/dependencies/hub_ports.py`:
```python
"""허브 포트 자리 — tenancy 가 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.user_directory_port import UserDirectoryPort


def get_user_directory() -> UserDirectoryPort:
    raise RuntimeError("UserDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/tenancy/app/dtos/list_members_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListMembersQuery:
    ctx: ShopContext


@dataclass(frozen=True)
class MemberView:
    member_id: int
    user_id: int
    display_name: str
    profile_image_url: str | None
    role: str
    joined_at: datetime
```

`backend/apps/tenancy/app/ports/input/list_members_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.list_members_dto import ListMembersQuery, MemberView


class ListMembersUseCase(ABC):
    @abstractmethod
    async def list_members(self, query: ListMembersQuery) -> list[MemberView]: ...
```

`backend/apps/tenancy/app/use_cases/list_members_interactor.py`:
```python
from __future__ import annotations

from hub.app.ports.user_directory_port import UserDirectoryPort
from tenancy.app.dtos.list_members_dto import ListMembersQuery, MemberView
from tenancy.app.ports.input.list_members_use_case import ListMembersUseCase
from tenancy.app.ports.output.member_repository import MemberRepository


class ListMembersInteractor(ListMembersUseCase):
    def __init__(self, members: MemberRepository, users: UserDirectoryPort) -> None:
        self._members = members
        self._users = users

    async def list_members(self, query: ListMembersQuery) -> list[MemberView]:
        members = await self._members.list_active(query.ctx)
        # 유저는 지워지지 않는다 (탈퇴해도 익명화된 행이 남는다). 그래서 프로필은 언제나 있다.
        profiles = await self._users.get_profiles([m.user_id for m in members])
        return [
            MemberView(
                member_id=m.id,
                user_id=m.user_id,
                display_name=profiles[m.user_id].display_name,
                profile_image_url=profiles[m.user_id].profile_image_url,
                role=m.role.value,
                joined_at=m.joined_at,
            )
            for m in members
        ]
```

`backend/apps/tenancy/dependencies/list_members_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.user_directory_port import UserDirectoryPort
from tenancy.app.ports.input.list_members_use_case import ListMembersUseCase
from tenancy.app.use_cases.list_members_interactor import ListMembersInteractor
from tenancy.dependencies.hub_ports import get_user_directory
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_list_members_use_case(
    db: DbSession, users: UserDirectoryPort = Depends(get_user_directory)
) -> ListMembersUseCase:
    return ListMembersInteractor(members=build_member_repository(db), users=users)
```

`backend/apps/tenancy/adapter/inbound/api/schemas/list_members_schema.py`:
```python
from datetime import datetime

from pydantic import BaseModel


class MemberSchema(BaseModel):
    member_id: int
    user_id: int
    display_name: str
    profile_image_url: str | None
    role: str
    joined_at: datetime
```

`backend/apps/tenancy/adapter/inbound/api/v1/list_members_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.list_members_schema import MemberSchema
from tenancy.app.dtos.list_members_dto import ListMembersQuery
from tenancy.app.ports.input.list_members_use_case import ListMembersUseCase
from tenancy.dependencies.list_members_provider import get_list_members_use_case

list_members_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@list_members_router.get("/{shop_id}/members", response_model=list[MemberSchema])
async def list_members(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListMembersUseCase = Depends(get_list_members_use_case),
) -> list[MemberSchema]:
    views = await use_case.list_members(ListMembersQuery(ctx=ctx))
    return [
        MemberSchema(
            member_id=v.member_id, user_id=v.user_id, display_name=v.display_name,
            profile_image_url=v.profile_image_url, role=v.role, joined_at=v.joined_at,
        )
        for v in views
    ]
```

- [ ] **Step 6: 진입점에 장착하고 자리를 채운다**

`backend/main.py`의 import 묶음에 더한다.
```python
from auth.dependencies.get_user_profiles_provider import get_get_user_profiles_use_case
from tenancy.adapter.inbound.api.v1.list_members_router import list_members_router
from tenancy.dependencies.hub_ports import get_user_directory
```
`app.include_router(create_invite_router)` 다음 줄에 더한다.
```python
app.include_router(list_members_router)
```
자리 채우기 묶음의 끝에 더한다.
```python
app.dependency_overrides[get_user_directory] = get_get_user_profiles_use_case
```

`backend/tests/test_hub_port_binding.py`에 import 한 줄을 더하고 목록에 자리를 더한다.
```python
from tenancy.dependencies.hub_ports import get_user_directory

_API_SLOTS = [get_shop_access_port, get_operator_directory, get_shop_provisioning, get_user_directory]
```

- [ ] **Step 7: 통과를 확인한다**

Run: Step 3의 명령과 `tests/test_hub_port_binding.py`
Expected: 전부 통과한다 (`test_user_pg_repository.py`는 기존 6개에 1개가 늘어 7개).

- [ ] **Step 8: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/hub backend/apps/auth backend/apps/tenancy backend/main.py backend/tests/test_hub_port_binding.py
git commit -m "feat(tenancy): 멤버 목록 슬라이스와 UserDirectoryPort"
```

---

### Task 14: 역할 변경과 내보내기

두 슬라이스다. 둘 다 `member:manage`가 필요하고, 둘 다 "매장에는 사장이 한 명 이상"을 지킨다. 사장 자리에서 빠지는 변경(사장 → 직원, 사장 내보내기)을 하기 전에 `count_owners`로 사장 행을 잠그고 센다. 내보낸 멤버는 다음 요청부터 `find_access`에 잡히지 않아 바로 403이다.

**Files:**
- Create: `backend/apps/tenancy/app/dtos/change_member_role_dto.py`, `remove_member_dto.py`
- Create: `backend/apps/tenancy/app/ports/input/change_member_role_use_case.py`, `remove_member_use_case.py`
- Create: `backend/apps/tenancy/app/use_cases/change_member_role_interactor.py`, `remove_member_interactor.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/schemas/change_member_role_schema.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/v1/change_member_role_router.py`, `remove_member_router.py`
- Create: `backend/apps/tenancy/dependencies/change_member_role_provider.py`, `remove_member_provider.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_change_member_role_interactor.py`, `test_remove_member_interactor.py`, `backend/apps/tenancy/tests/adapter/test_change_member_role_router.py`, `test_remove_member_router.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: Task 4의 `ensure_owner_remains`·`RoleCode`·`MemberNotFoundError`·`LastOwnerError`, Task 5의 `MemberRepository.get_active`·`count_owners`·`change_role`·`remove`, Task 6의 `build_member_repository`, Task 7의 `require_permission`, Task 11의 테스트 도우미
- Produces:
  - `tenancy.app.dtos.change_member_role_dto`: `ChangeMemberRoleCommand(ctx: ShopContext, member_id: int, role: str)`, `ChangedMember(member_id: int, user_id: int, role: str)`
  - `tenancy.app.dtos.remove_member_dto.RemoveMemberCommand(ctx: ShopContext, member_id: int)`
  - `change_member_role_router` (`PATCH /v1/shops/{shop_id}/members/{member_id}` → 200), `remove_member_router` (`DELETE …` → 204)

- [ ] **Step 1: 실패하는 유스케이스 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_change_member_role_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.change_member_role_dto import ChangeMemberRoleCommand
from tenancy.app.use_cases.change_member_role_interactor import ChangeMemberRoleInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


class _StubMembers:
    def __init__(self, target, owner_count=1):
        self.target = target
        self.owner_count = owner_count
        self.counted = 0
        self.changes = []

    async def get_active(self, ctx, member_id):
        return self.target

    async def count_owners(self, ctx):
        self.counted += 1
        return self.owner_count

    async def change_role(self, ctx, member_id, role):
        self.changes.append((ctx, member_id, role))


def _member(role):
    return Member(id=12, shop_id=3, user_id=2, role=role, joined_at=JOINED)


def _command(role):
    return ChangeMemberRoleCommand(ctx=CTX, member_id=12, role=role)


async def test_직원을_사장으로_올릴_때는_사장_수를_세지_않는다():
    members = _StubMembers(_member(RoleCode.STAFF))
    result = await ChangeMemberRoleInteractor(members).change_role(_command("owner"))
    assert members.changes == [(CTX, 12, RoleCode.OWNER)]
    assert members.counted == 0
    assert (result.member_id, result.user_id, result.role) == (12, 2, "owner")


async def test_사장이_둘이면_한_명을_직원으로_낮출_수_있다():
    members = _StubMembers(_member(RoleCode.OWNER), owner_count=2)
    result = await ChangeMemberRoleInteractor(members).change_role(_command("staff"))
    assert members.changes == [(CTX, 12, RoleCode.STAFF)]
    assert result.role == "staff"


async def test_마지막_사장은_낮출_수_없다():
    members = _StubMembers(_member(RoleCode.OWNER), owner_count=1)
    with pytest.raises(LastOwnerError):
        await ChangeMemberRoleInteractor(members).change_role(_command("staff"))
    assert members.changes == []


async def test_같은_역할로_바꾸면_아무것도_하지_않는다():
    members = _StubMembers(_member(RoleCode.STAFF))
    result = await ChangeMemberRoleInteractor(members).change_role(_command("staff"))
    assert members.changes == [] and result.role == "staff"


async def test_없는_멤버는_MEMBER_NOT_FOUND_다():
    with pytest.raises(MemberNotFoundError):
        await ChangeMemberRoleInteractor(_StubMembers(None)).change_role(_command("owner"))
```

`backend/apps/tenancy/tests/app/use_cases/test_remove_member_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.use_cases.remove_member_interactor import RemoveMemberInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError
from tenancy.domain.value_objects.role_code import RoleCode

JOINED = datetime(2026, 9, 20, 12, 0, tzinfo=timezone.utc)
CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"member:manage"}))


class _StubMembers:
    def __init__(self, target, owner_count=1):
        self.target = target
        self.owner_count = owner_count
        self.removed = []

    async def get_active(self, ctx, member_id):
        return self.target

    async def count_owners(self, ctx):
        return self.owner_count

    async def remove(self, ctx, member_id):
        self.removed.append((ctx, member_id))


def _member(role):
    return Member(id=12, shop_id=3, user_id=2, role=role, joined_at=JOINED)


async def test_직원을_내보낸다():
    members = _StubMembers(_member(RoleCode.STAFF))
    await RemoveMemberInteractor(members).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == [(CTX, 12)]


async def test_사장이_둘이면_한_명을_내보낼_수_있다():
    members = _StubMembers(_member(RoleCode.OWNER), owner_count=2)
    await RemoveMemberInteractor(members).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == [(CTX, 12)]


async def test_마지막_사장은_내보낼_수_없다():
    members = _StubMembers(_member(RoleCode.OWNER), owner_count=1)
    with pytest.raises(LastOwnerError):
        await RemoveMemberInteractor(members).remove(RemoveMemberCommand(ctx=CTX, member_id=12))
    assert members.removed == []


async def test_없는_멤버는_MEMBER_NOT_FOUND_다():
    with pytest.raises(MemberNotFoundError):
        await RemoveMemberInteractor(_StubMembers(None)).remove(RemoveMemberCommand(ctx=CTX, member_id=99))
```

- [ ] **Step 2: 실패하는 라우터 테스트를 쓴다**

`backend/apps/tenancy/tests/adapter/test_change_member_role_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.change_member_role_router import change_member_role_router
from tenancy.app.dtos.change_member_role_dto import ChangedMember
from tenancy.dependencies.change_member_role_provider import get_change_member_role_use_case
from tenancy.domain.errors import LastOwnerError, MemberNotFoundError
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def change_role(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return ChangedMember(member_id=command.member_id, user_id=2, role=command.role)


async def _patch(stub, access, body):
    app = build_app(change_member_role_router, get_change_member_role_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.patch("/v1/shops/3/members/12", json=body)


async def test_사장은_멤버의_역할을_바꾼다():
    stub = _StubUseCase()
    response = await _patch(stub, StubShopAccess(OWNER_PERMISSIONS), {"role": "owner"})
    assert response.status_code == 200
    assert response.json() == {"member_id": 12, "user_id": 2, "role": "owner"}
    command = stub.commands[0]
    assert (command.ctx.shop_id, command.member_id, command.role) == (3, 12, "owner")


async def test_권한_없는_직원은_403_이다():
    stub = _StubUseCase()
    response = await _patch(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"), {"role": "owner"})
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_모르는_역할은_422_다():
    response = await _patch(_StubUseCase(), StubShopAccess(OWNER_PERMISSIONS), {"role": "admin"})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_마지막_사장을_낮추면_409_LAST_OWNER_다():
    stub = _StubUseCase(LastOwnerError("매장에는 사장이 한 명 이상 있어야 합니다."))
    response = await _patch(stub, StubShopAccess(OWNER_PERMISSIONS), {"role": "staff"})
    assert (response.status_code, response.json()["code"]) == (409, "LAST_OWNER")


async def test_없는_멤버는_404_MEMBER_NOT_FOUND_다():
    stub = _StubUseCase(MemberNotFoundError("멤버를 찾을 수 없습니다."))
    response = await _patch(stub, StubShopAccess(OWNER_PERMISSIONS), {"role": "staff"})
    assert (response.status_code, response.json()["code"]) == (404, "MEMBER_NOT_FOUND")
```

`backend/apps/tenancy/tests/adapter/test_remove_member_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.remove_member_router import remove_member_router
from tenancy.dependencies.remove_member_provider import get_remove_member_use_case
from tenancy.domain.errors import LastOwnerError
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def remove(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error


async def _delete(stub, access):
    app = build_app(remove_member_router, get_remove_member_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/members/12")


async def test_사장은_멤버를_내보내고_204_를_받는다():
    stub = _StubUseCase()
    response = await _delete(stub, StubShopAccess(OWNER_PERMISSIONS))
    assert response.status_code == 204
    assert (stub.commands[0].ctx.shop_id, stub.commands[0].member_id) == (3, 12)


async def test_권한_없는_직원은_403_이다():
    stub = _StubUseCase()
    response = await _delete(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_마지막_사장을_내보내면_409_LAST_OWNER_다():
    stub = _StubUseCase(LastOwnerError("매장에는 사장이 한 명 이상 있어야 합니다."))
    response = await _delete(stub, StubShopAccess(OWNER_PERMISSIONS))
    assert (response.status_code, response.json()["code"]) == (409, "LAST_OWNER")
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests -q -p no:cacheprovider -m "not integration" -k "change_member_role or remove_member"`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.dtos.change_member_role_dto'`

- [ ] **Step 4: 역할 변경 슬라이스를 구현한다**

`backend/apps/tenancy/app/dtos/change_member_role_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ChangeMemberRoleCommand:
    ctx: ShopContext
    member_id: int
    role: str  # "owner" 또는 "staff" — 스키마가 걸러 준다


@dataclass(frozen=True)
class ChangedMember:
    member_id: int
    user_id: int
    role: str
```

`backend/apps/tenancy/app/ports/input/change_member_role_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.change_member_role_dto import ChangedMember, ChangeMemberRoleCommand


class ChangeMemberRoleUseCase(ABC):
    @abstractmethod
    async def change_role(self, command: ChangeMemberRoleCommand) -> ChangedMember: ...
```

`backend/apps/tenancy/app/use_cases/change_member_role_interactor.py`:
```python
from __future__ import annotations

from tenancy.app.dtos.change_member_role_dto import ChangedMember, ChangeMemberRoleCommand
from tenancy.app.ports.input.change_member_role_use_case import ChangeMemberRoleUseCase
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import MemberNotFoundError
from tenancy.domain.services.owner_guard import ensure_owner_remains
from tenancy.domain.value_objects.role_code import RoleCode


class ChangeMemberRoleInteractor(ChangeMemberRoleUseCase):
    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def change_role(self, command: ChangeMemberRoleCommand) -> ChangedMember:
        target = await self._members.get_active(command.ctx, command.member_id)
        if target is None:
            raise MemberNotFoundError("멤버를 찾을 수 없습니다.")
        new_role = RoleCode(command.role)
        if target.role is not new_role:
            if target.role is RoleCode.OWNER:
                # 사장 자리에서 빠지는 변경이다. 사장 행을 잠그고 센 뒤에 바꾼다.
                ensure_owner_remains(await self._members.count_owners(command.ctx))
            await self._members.change_role(command.ctx, target.id, new_role)
        return ChangedMember(member_id=target.id, user_id=target.user_id, role=new_role.value)
```

`backend/apps/tenancy/dependencies/change_member_role_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.change_member_role_use_case import ChangeMemberRoleUseCase
from tenancy.app.use_cases.change_member_role_interactor import ChangeMemberRoleInteractor
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_change_member_role_use_case(db: DbSession) -> ChangeMemberRoleUseCase:
    return ChangeMemberRoleInteractor(members=build_member_repository(db))
```

`backend/apps/tenancy/adapter/inbound/api/schemas/change_member_role_schema.py`:
```python
from typing import Literal

from pydantic import BaseModel


class ChangeMemberRoleRequestSchema(BaseModel):
    role: Literal["owner", "staff"]


class ChangedMemberResponseSchema(BaseModel):
    member_id: int
    user_id: int
    role: str
```

`backend/apps/tenancy/adapter/inbound/api/v1/change_member_role_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.change_member_role_schema import (
    ChangedMemberResponseSchema,
    ChangeMemberRoleRequestSchema,
)
from tenancy.app.dtos.change_member_role_dto import ChangeMemberRoleCommand
from tenancy.app.ports.input.change_member_role_use_case import ChangeMemberRoleUseCase
from tenancy.dependencies.change_member_role_provider import get_change_member_role_use_case

change_member_role_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@change_member_role_router.patch(
    "/{shop_id}/members/{member_id}", response_model=ChangedMemberResponseSchema
)
async def change_member_role(
    member_id: int,
    body: ChangeMemberRoleRequestSchema,
    ctx: ShopContext = Depends(require_permission("member:manage")),
    use_case: ChangeMemberRoleUseCase = Depends(get_change_member_role_use_case),
) -> ChangedMemberResponseSchema:
    changed = await use_case.change_role(
        ChangeMemberRoleCommand(ctx=ctx, member_id=member_id, role=body.role)
    )
    return ChangedMemberResponseSchema(
        member_id=changed.member_id, user_id=changed.user_id, role=changed.role
    )
```

- [ ] **Step 5: 내보내기 슬라이스를 구현한다**

`backend/apps/tenancy/app/dtos/remove_member_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RemoveMemberCommand:
    ctx: ShopContext
    member_id: int
```

`backend/apps/tenancy/app/ports/input/remove_member_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand


class RemoveMemberUseCase(ABC):
    @abstractmethod
    async def remove(self, command: RemoveMemberCommand) -> None: ...
```

`backend/apps/tenancy/app/use_cases/remove_member_interactor.py`:
```python
from __future__ import annotations

from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.domain.errors import MemberNotFoundError
from tenancy.domain.services.owner_guard import ensure_owner_remains
from tenancy.domain.value_objects.role_code import RoleCode


class RemoveMemberInteractor(RemoveMemberUseCase):
    """행을 지우지 않고 removed_at 을 남긴다. 내보낸 멤버는 다음 요청부터 소속 확인에서 걸린다."""

    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def remove(self, command: RemoveMemberCommand) -> None:
        target = await self._members.get_active(command.ctx, command.member_id)
        if target is None:
            raise MemberNotFoundError("멤버를 찾을 수 없습니다.")
        if target.role is RoleCode.OWNER:
            ensure_owner_remains(await self._members.count_owners(command.ctx))
        await self._members.remove(command.ctx, target.id)
```

`backend/apps/tenancy/dependencies/remove_member_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.app.use_cases.remove_member_interactor import RemoveMemberInteractor
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_remove_member_use_case(db: DbSession) -> RemoveMemberUseCase:
    return RemoveMemberInteractor(members=build_member_repository(db))
```

`backend/apps/tenancy/adapter/inbound/api/v1/remove_member_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.remove_member_dto import RemoveMemberCommand
from tenancy.app.ports.input.remove_member_use_case import RemoveMemberUseCase
from tenancy.dependencies.remove_member_provider import get_remove_member_use_case

remove_member_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@remove_member_router.delete("/{shop_id}/members/{member_id}", status_code=204)
async def remove_member(
    member_id: int,
    ctx: ShopContext = Depends(require_permission("member:manage")),
    use_case: RemoveMemberUseCase = Depends(get_remove_member_use_case),
) -> None:
    await use_case.remove(RemoveMemberCommand(ctx=ctx, member_id=member_id))
```

- [ ] **Step 6: 진입점에 장착한다**

`backend/main.py`의 import 묶음에 더한다.
```python
from tenancy.adapter.inbound.api.v1.change_member_role_router import change_member_role_router
from tenancy.adapter.inbound.api.v1.remove_member_router import remove_member_router
```
`app.include_router(list_members_router)` 다음 줄에 더한다.
```python
app.include_router(change_member_role_router)
app.include_router(remove_member_router)
```

- [ ] **Step 7: 통과를 확인한다**

Run: Step 3의 명령
Expected: `17 passed` (유스케이스 5 + 4, 라우터 5 + 3)

- [ ] **Step 8: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/tenancy backend/main.py
git commit -m "feat(tenancy): 멤버 역할 변경과 내보내기 슬라이스, 마지막 사장 보호"
```

---

### Task 15: 매장 정보 조회와 수정 (`GET`·`PUT /v1/shops/{shop_id}/settings`)

두 슬라이스다. 조회는 소속이면 되고, 수정은 `shop:update`가 필요하다. 수정은 폼 전체를 보내는 `PUT`이다(이름·전화·주소). 업종과 시간대는 ①에서 고칠 일이 없어 조회만 한다.

**Files:**
- Create: `backend/apps/tenancy/app/dtos/shop_view_dto.py`, `get_shop_dto.py`, `update_shop_dto.py`
- Create: `backend/apps/tenancy/app/ports/input/get_shop_use_case.py`, `update_shop_use_case.py`
- Create: `backend/apps/tenancy/app/use_cases/get_shop_interactor.py`, `update_shop_interactor.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/schemas/get_shop_schema.py`, `update_shop_schema.py`
- Create: `backend/apps/tenancy/adapter/inbound/api/v1/get_shop_router.py`, `update_shop_router.py`
- Create: `backend/apps/tenancy/dependencies/get_shop_provider.py`, `update_shop_provider.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_get_shop_interactor.py`, `test_update_shop_interactor.py`, `backend/apps/tenancy/tests/adapter/test_get_shop_router.py`, `test_update_shop_router.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: Task 5의 `ShopRepository.get`·`update`·`Shop`, Task 6의 `build_shop_repository`, Task 7의 `get_shop_context`·`require_permission`, Task 11의 테스트 도우미
- Produces:
  - `tenancy.app.dtos.shop_view_dto.ShopView(shop_id, name, business_type, phone, address, timezone)` + `ShopView.of(shop: Shop) -> ShopView`
  - `tenancy.app.dtos.get_shop_dto.GetShopQuery(ctx: ShopContext)`
  - `tenancy.app.dtos.update_shop_dto.UpdateShopCommand(ctx: ShopContext, name: str, phone: str | None, address: str | None)`
  - `get_shop_router`, `update_shop_router`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_get_shop_interactor.py`:
```python
from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.use_cases.get_shop_interactor import GetShopInteractor
from tenancy.domain.entities.shop import Shop

CTX = ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset())


class _StubShops:
    def __init__(self):
        self.contexts = []

    async def get(self, ctx):
        self.contexts.append(ctx)
        return Shop(id=3, name="Hiss Haus", business_type="pet_grooming", phone="02-000-0000",
                    address="서울", timezone="Asia/Seoul", suspended_at=None, closed_at=None)


async def test_컨텍스트의_매장_정보를_돌려준다():
    shops = _StubShops()
    view = await GetShopInteractor(shops).get_shop(GetShopQuery(ctx=CTX))
    assert shops.contexts == [CTX]
    assert (view.shop_id, view.name, view.business_type) == (3, "Hiss Haus", "pet_grooming")
    assert (view.phone, view.address, view.timezone) == ("02-000-0000", "서울", "Asia/Seoul")
```

`backend/apps/tenancy/tests/app/use_cases/test_update_shop_interactor.py`:
```python
from hub.app.dtos.shop_context import ShopContext
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand
from tenancy.app.use_cases.update_shop_interactor import UpdateShopInteractor
from tenancy.domain.entities.shop import Shop

CTX = ShopContext(shop_id=3, member_id=11, role="owner", permissions=frozenset({"shop:update"}))


class _StubShops:
    def __init__(self):
        self.updates = []

    async def update(self, ctx, name, phone, address):
        self.updates.append((ctx, name, phone, address))
        return Shop(id=3, name=name, business_type="pet_grooming", phone=phone, address=address,
                    timezone="Asia/Seoul", suspended_at=None, closed_at=None)


async def test_이름_전화_주소를_고치고_고친_정보를_돌려준다():
    shops = _StubShops()
    view = await UpdateShopInteractor(shops).update_shop(
        UpdateShopCommand(ctx=CTX, name="히스 하우스", phone=None, address="서울 성동구")
    )
    assert shops.updates == [(CTX, "히스 하우스", None, "서울 성동구")]
    assert (view.name, view.phone, view.address) == ("히스 하우스", None, "서울 성동구")
```

`backend/apps/tenancy/tests/adapter/test_get_shop_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.get_shop_router import get_shop_router
from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.dependencies.get_shop_provider import get_get_shop_use_case
from tenancy.tests.helpers.api import STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def get_shop(self, query):
        self.queries.append(query)
        return ShopView(shop_id=3, name="Hiss Haus", business_type="pet_grooming",
                        phone=None, address=None, timezone="Asia/Seoul")


async def _get(stub, access, user_id=5):
    app = build_app(get_shop_router, get_get_shop_use_case, stub, access=access, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/shops/3/settings")


async def test_직원도_매장_정보를_본다():
    stub = _StubUseCase()
    response = await _get(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"))
    assert response.status_code == 200
    assert response.json() == {
        "shop_id": 3, "name": "Hiss Haus", "business_type": "pet_grooming",
        "phone": None, "address": None, "timezone": "Asia/Seoul",
    }
    assert stub.queries[0].ctx.shop_id == 3


async def test_토큰이_없으면_401_이다():
    response = await _get(_StubUseCase(), StubShopAccess(), user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

`backend/apps/tenancy/tests/adapter/test_update_shop_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from tenancy.adapter.inbound.api.v1.update_shop_router import update_shop_router
from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.dependencies.update_shop_provider import get_update_shop_use_case
from tenancy.tests.helpers.api import OWNER_PERMISSIONS, STAFF_PERMISSIONS, StubShopAccess, build_app


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def update_shop(self, command):
        self.commands.append(command)
        return ShopView(shop_id=3, name=command.name, business_type="pet_grooming",
                        phone=command.phone, address=command.address, timezone="Asia/Seoul")


async def _put(stub, access, body):
    app = build_app(update_shop_router, get_update_shop_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.put("/v1/shops/3/settings", json=body)


async def test_사장은_매장_정보를_고친다():
    stub = _StubUseCase()
    response = await _put(stub, StubShopAccess(OWNER_PERMISSIONS),
                          {"name": " 히스 하우스 ", "phone": "", "address": "서울 성동구"})
    assert response.status_code == 200
    assert response.json()["name"] == "히스 하우스"
    command = stub.commands[0]
    # 빈 문자열로 온 전화번호는 "없음"으로 저장한다.
    assert (command.ctx.shop_id, command.name, command.phone, command.address) == (
        3, "히스 하우스", None, "서울 성동구",
    )


async def test_권한_없는_직원은_403_이다():
    stub = _StubUseCase()
    response = await _put(stub, StubShopAccess(STAFF_PERMISSIONS, role="staff"), {"name": "새 이름"})
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_이름이_비면_422_다():
    response = await _put(_StubUseCase(), StubShopAccess(OWNER_PERMISSIONS), {"name": "  "})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests -q -p no:cacheprovider -m "not integration" -k "get_shop or update_shop"`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.dtos.get_shop_dto'`

- [ ] **Step 3: DTO와 유스케이스를 구현한다**

`backend/apps/tenancy/app/dtos/shop_view_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from tenancy.domain.entities.shop import Shop


@dataclass(frozen=True)
class ShopView:
    """멤버에게 보여 주는 매장 정보. 정지·닫힘 시각은 넣지 않는다 (그런 매장은 소속 확인에서 이미 막힌다)."""

    shop_id: int
    name: str
    business_type: str
    phone: str | None
    address: str | None
    timezone: str

    @classmethod
    def of(cls, shop: Shop) -> ShopView:
        return cls(
            shop_id=shop.id, name=shop.name, business_type=shop.business_type,
            phone=shop.phone, address=shop.address, timezone=shop.timezone,
        )
```

`backend/apps/tenancy/app/dtos/get_shop_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetShopQuery:
    ctx: ShopContext
```

`backend/apps/tenancy/app/dtos/update_shop_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateShopCommand:
    ctx: ShopContext
    name: str
    phone: str | None
    address: str | None
```

`backend/apps/tenancy/app/ports/input/get_shop_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.dtos.shop_view_dto import ShopView


class GetShopUseCase(ABC):
    @abstractmethod
    async def get_shop(self, query: GetShopQuery) -> ShopView: ...
```

`backend/apps/tenancy/app/ports/input/update_shop_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand


class UpdateShopUseCase(ABC):
    @abstractmethod
    async def update_shop(self, command: UpdateShopCommand) -> ShopView: ...
```

`backend/apps/tenancy/app/use_cases/get_shop_interactor.py`:
```python
from __future__ import annotations

from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.app.ports.input.get_shop_use_case import GetShopUseCase
from tenancy.app.ports.output.shop_repository import ShopRepository


class GetShopInteractor(GetShopUseCase):
    def __init__(self, shops: ShopRepository) -> None:
        self._shops = shops

    async def get_shop(self, query: GetShopQuery) -> ShopView:
        return ShopView.of(await self._shops.get(query.ctx))
```

`backend/apps/tenancy/app/use_cases/update_shop_interactor.py`:
```python
from __future__ import annotations

from tenancy.app.dtos.shop_view_dto import ShopView
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand
from tenancy.app.ports.input.update_shop_use_case import UpdateShopUseCase
from tenancy.app.ports.output.shop_repository import ShopRepository


class UpdateShopInteractor(UpdateShopUseCase):
    def __init__(self, shops: ShopRepository) -> None:
        self._shops = shops

    async def update_shop(self, command: UpdateShopCommand) -> ShopView:
        shop = await self._shops.update(command.ctx, command.name, command.phone, command.address)
        return ShopView.of(shop)
```

- [ ] **Step 4: 프로바이더, 스키마, 라우터를 구현한다**

`backend/apps/tenancy/dependencies/get_shop_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.get_shop_use_case import GetShopUseCase
from tenancy.app.use_cases.get_shop_interactor import GetShopInteractor
from tenancy.dependencies.tenancy_wiring import build_shop_repository


def get_get_shop_use_case(db: DbSession) -> GetShopUseCase:
    return GetShopInteractor(shops=build_shop_repository(db))
```

`backend/apps/tenancy/dependencies/update_shop_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from tenancy.app.ports.input.update_shop_use_case import UpdateShopUseCase
from tenancy.app.use_cases.update_shop_interactor import UpdateShopInteractor
from tenancy.dependencies.tenancy_wiring import build_shop_repository


def get_update_shop_use_case(db: DbSession) -> UpdateShopUseCase:
    return UpdateShopInteractor(shops=build_shop_repository(db))
```

`backend/apps/tenancy/adapter/inbound/api/schemas/get_shop_schema.py`:
```python
from __future__ import annotations

from pydantic import BaseModel

from tenancy.app.dtos.shop_view_dto import ShopView


class ShopResponseSchema(BaseModel):
    shop_id: int
    name: str
    business_type: str
    phone: str | None
    address: str | None
    timezone: str

    @classmethod
    def of(cls, view: ShopView) -> ShopResponseSchema:
        return cls(
            shop_id=view.shop_id, name=view.name, business_type=view.business_type,
            phone=view.phone, address=view.address, timezone=view.timezone,
        )
```

`backend/apps/tenancy/adapter/inbound/api/schemas/update_shop_schema.py`:
```python
from typing import Annotated

from pydantic import BaseModel, StringConstraints


class UpdateShopRequestSchema(BaseModel):
    """설정 화면의 폼 전체를 보낸다. 전화와 주소는 비우면 '없음'이 된다."""

    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    phone: Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None = None
    address: Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)] | None = None
```

`backend/apps/tenancy/adapter/inbound/api/v1/get_shop_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.get_shop_schema import ShopResponseSchema
from tenancy.app.dtos.get_shop_dto import GetShopQuery
from tenancy.app.ports.input.get_shop_use_case import GetShopUseCase
from tenancy.dependencies.get_shop_provider import get_get_shop_use_case

get_shop_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@get_shop_router.get("/{shop_id}/settings", response_model=ShopResponseSchema)
async def get_shop(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetShopUseCase = Depends(get_get_shop_use_case),
) -> ShopResponseSchema:
    return ShopResponseSchema.of(await use_case.get_shop(GetShopQuery(ctx=ctx)))
```

`backend/apps/tenancy/adapter/inbound/api/v1/update_shop_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.inbound.api.schemas.get_shop_schema import ShopResponseSchema
from tenancy.adapter.inbound.api.schemas.update_shop_schema import UpdateShopRequestSchema
from tenancy.app.dtos.update_shop_dto import UpdateShopCommand
from tenancy.app.ports.input.update_shop_use_case import UpdateShopUseCase
from tenancy.dependencies.update_shop_provider import get_update_shop_use_case

update_shop_router = APIRouter(prefix="/v1/shops", tags=["shops"])


@update_shop_router.put("/{shop_id}/settings", response_model=ShopResponseSchema)
async def update_shop(
    body: UpdateShopRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateShopUseCase = Depends(get_update_shop_use_case),
) -> ShopResponseSchema:
    view = await use_case.update_shop(
        UpdateShopCommand(
            ctx=ctx, name=body.name, phone=body.phone or None, address=body.address or None
        )
    )
    return ShopResponseSchema.of(view)
```

- [ ] **Step 5: 진입점에 장착한다**

`backend/main.py`의 import 묶음에 더한다.
```python
from tenancy.adapter.inbound.api.v1.get_shop_router import get_shop_router
from tenancy.adapter.inbound.api.v1.update_shop_router import update_shop_router
```
`app.include_router(remove_member_router)` 다음 줄에 더한다.
```python
app.include_router(get_shop_router)
app.include_router(update_shop_router)
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 2의 명령
Expected: `7 passed`

- [ ] **Step 7: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/tenancy backend/main.py
git commit -m "feat(tenancy): 매장 정보 조회와 수정 슬라이스"
```

---

### Task 16: `GET /v1/me`에 소속 매장 목록을 넣는다

앱은 로그인 직후 `/v1/me`의 `shops`로 갈 곳을 정한다(0곳: 초대 코드 입력, 1곳: 바로 입장, 2곳 이상: 매장 선택). auth는 소속을 모르므로 허브의 `MembershipDirectoryPort`를 자리로 받고, tenancy가 `list_memberships` 슬라이스로 구현한다. 닫힌 매장은 목록에서 뺀다.

**Files:**
- Create: `backend/apps/hub/app/dtos/membership_summary.py`, `backend/apps/hub/app/ports/membership_directory_port.py`
- Create: `backend/apps/tenancy/app/use_cases/list_memberships_interactor.py`, `backend/apps/tenancy/dependencies/list_memberships_provider.py`
- Create: `backend/apps/auth/dependencies/hub_ports.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_list_memberships_interactor.py`
- Modify: `backend/apps/tenancy/app/ports/output/member_repository.py`, `backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`, `backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`
- Modify: `backend/apps/auth/app/dtos/get_me_dto.py`, `backend/apps/auth/app/use_cases/get_me_interactor.py`, `backend/apps/auth/dependencies/get_me_provider.py`, `backend/apps/auth/adapter/inbound/api/schemas/get_me_schema.py`, `backend/apps/auth/adapter/inbound/api/v1/get_me_router.py`
- Modify: `backend/apps/auth/tests/app/use_cases/test_get_me_interactor.py`, `backend/apps/auth/tests/adapter/test_get_me_router.py`, `backend/tests/integration/test_auth_flow_wiring.py`
- Modify: `backend/main.py`, `backend/tests/test_hub_port_binding.py`

**Interfaces:**
- Consumes: Task 5의 `MemberRepository`·`MemberPgRepository`, Task 6의 `build_member_repository`
- Produces:
  - `hub.app.dtos.membership_summary.MembershipSummary(shop_id: int, shop_name: str, role: str)`
  - `hub.app.ports.membership_directory_port.MembershipDirectoryPort`: `async list_for_user(user_id: int) -> list[MembershipSummary]`
  - `tenancy.app.ports.output.member_repository.MemberRepository.list_for_user(user_id: int) -> list[MembershipSummary]` (새 메서드)
  - `tenancy.dependencies.list_memberships_provider.get_list_memberships_use_case(db: DbSession) -> MembershipDirectoryPort`
  - `auth.dependencies.hub_ports.get_membership_directory() -> MembershipDirectoryPort` — 자리
  - `auth.app.dtos.get_me_dto.MeResponse`에 `shops: tuple[MembershipSummary, ...]` 추가
  - `GET /v1/me` 응답에 `"shops": [{"shop_id", "shop_name", "role"}]` 추가

- [ ] **Step 1: 허브 계약을 쓴다**

`backend/apps/hub/app/dtos/membership_summary.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MembershipSummary:
    """한 유저가 지금 속해 있는 매장 하나."""

    shop_id: int
    shop_name: str
    role: str
```

`backend/apps/hub/app/ports/membership_directory_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.membership_summary import MembershipSummary


class MembershipDirectoryPort(ABC):
    """구현: tenancy. 사용: auth (GET /v1/me)."""

    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        """유저가 지금 속해 있는 매장들. 내보내진 소속과 닫힌 매장은 빠진다."""
```

- [ ] **Step 2: 실패하는 테스트를 쓴다 (tenancy)**

`backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`의 끝에 더한다. 파일 위쪽 import 묶음에 `from hub.app.dtos.membership_summary import MembershipSummary`도 더한다.
```python


async def test_유저가_속한_매장을_매장_ID_순으로_돌려준다(db_session):
    a, b = await _shop(db_session, "A 매장"), await _shop(db_session, "B 매장")
    repo = MemberPgRepository(db_session)
    await repo.add(b.id, user_id=7, role=RoleCode.STAFF)
    await repo.add(a.id, user_id=7, role=RoleCode.OWNER)
    await repo.add(a.id, user_id=8, role=RoleCode.STAFF)
    assert await repo.list_for_user(7) == [
        MembershipSummary(shop_id=a.id, shop_name="A 매장", role="owner"),
        MembershipSummary(shop_id=b.id, shop_name="B 매장", role="staff"),
    ]
    assert await repo.list_for_user(404) == []


async def test_내보내진_소속과_닫힌_매장은_목록에서_빠진다(db_session):
    a = await _shop(db_session, "A 매장")
    b = await _shop(db_session, "B 매장")
    c = await _shop(db_session, "C 매장")
    repo = MemberPgRepository(db_session)
    removed = await repo.add(a.id, user_id=7, role=RoleCode.STAFF)
    await repo.remove(_ctx(a.id), removed.id)
    await repo.add(b.id, user_id=7, role=RoleCode.OWNER)
    await db_session.execute(text("UPDATE shops SET closed_at = now() WHERE id = :id"), {"id": b.id})
    await repo.add(c.id, user_id=7, role=RoleCode.STAFF)
    assert [m.shop_id for m in await repo.list_for_user(7)] == [c.id]
```

`backend/apps/tenancy/tests/app/use_cases/test_list_memberships_interactor.py`:
```python
from hub.app.dtos.membership_summary import MembershipSummary
from tenancy.app.use_cases.list_memberships_interactor import ListMembershipsInteractor


class _StubMembers:
    def __init__(self):
        self.calls = []

    async def list_for_user(self, user_id):
        self.calls.append(user_id)
        return [MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner")]


async def test_유저의_소속_매장을_돌려준다():
    members = _StubMembers()
    result = await ListMembershipsInteractor(members).list_for_user(5)
    assert result == [MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner")]
    assert members.calls == [5]
```

- [ ] **Step 3: 실패하는 테스트를 쓴다 (auth)**

`backend/apps/auth/tests/app/use_cases/test_get_me_interactor.py` 전체를 바꾼다.
```python
import pytest

from auth.app.dtos.get_me_dto import GetMeQuery
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.provider import Provider
from hub.app.dtos.membership_summary import MembershipSummary


class _StubUsers:
    def __init__(self, user, identities=()):
        self.user = user
        self.identities = list(identities)

    async def get(self, user_id):
        return self.user

    async def list_identities(self, user_id):
        return self.identities


class _StubMemberships:
    def __init__(self, shops=()):
        self.shops = list(shops)
        self.calls = []

    async def list_for_user(self, user_id):
        self.calls.append(user_id)
        return self.shops


def _user():
    return User(id=5, display_name="두부 보호자", profile_image_url="https://img/1.jpg",
                phone=None, suspended_at=None, deleted_at=None)


async def test_프로필과_연결된_로그인_수단과_소속_매장을_돌려준다():
    identities = [
        SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
        SocialIdentity(2, 5, Provider.APPLE, "apple-1", None),
    ]
    memberships = _StubMemberships([MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner")])
    me = await GetMeInteractor(_StubUsers(_user(), identities), memberships).get_me(GetMeQuery(user_id=5))
    assert (me.id, me.display_name, me.profile_image_url) == (5, "두부 보호자", "https://img/1.jpg")
    assert me.identities == ("kakao", "apple")
    assert me.shops == (MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner"),)
    assert memberships.calls == [5]


async def test_소속이_없으면_매장_목록이_비어_있다():
    me = await GetMeInteractor(_StubUsers(_user()), _StubMemberships()).get_me(GetMeQuery(user_id=5))
    assert me.shops == ()


async def test_유저가_없으면_UserNotFoundError_다():
    with pytest.raises(UserNotFoundError):
        await GetMeInteractor(_StubUsers(None), _StubMemberships()).get_me(GetMeQuery(user_id=404))
```

`backend/apps/auth/tests/adapter/test_get_me_router.py`에서 세 곳을 고친다.

(1) import 묶음에 더한다.
```python
from hub.app.dtos.membership_summary import MembershipSummary
```
(2) `_StubUseCase.get_me`의 반환을 바꾼다.
```python
        return MeResponse(
            id=query.user_id, display_name="두부 보호자", profile_image_url=None,
            identities=("kakao",),
            shops=(MembershipSummary(shop_id=3, shop_name="Hiss Haus", role="owner"),),
        )
```
(3) 첫 테스트의 본문 단언을 바꾼다.
```python
    assert response.json() == {
        "id": 5, "display_name": "두부 보호자", "profile_image_url": None, "identities": ["kakao"],
        "shops": [{"shop_id": 3, "shop_name": "Hiss Haus", "role": "owner"}],
    }
```

`backend/tests/integration/test_auth_flow_wiring.py`의 첫 테스트에서 `assert me.json()["identities"] == ["dev"]` 다음 줄에 더한다.
```python
    assert me.json()["shops"] == []
```

- [ ] **Step 4: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_get_me_interactor.py apps/auth/tests/adapter/test_get_me_router.py apps/tenancy/tests/app/use_cases/test_list_memberships_interactor.py apps/tenancy/tests/adapter/test_member_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `No module named 'tenancy.app.use_cases.list_memberships_interactor'`, `TypeError: GetMeInteractor.__init__() takes 2 positional arguments but 3 were given`, `'MemberPgRepository' object has no attribute 'list_for_user'`

- [ ] **Step 5: tenancy 쪽을 구현한다**

`backend/apps/tenancy/app/ports/output/member_repository.py`에 import 한 줄과 메서드 하나를 더한다.
```python
from hub.app.dtos.membership_summary import MembershipSummary
```
```python
    @abstractmethod
    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        """유저 기준 조회라 매장 컨텍스트가 없다. 내보내진 소속과 닫힌 매장은 뺀다."""
```

`backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`에 import 한 줄과 메서드 하나를 더한다 (`find_access` 다음).
```python
from hub.app.dtos.membership_summary import MembershipSummary
```
```python
    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        stmt = (
            select(ShopOrm.id, ShopOrm.name, RoleOrm.code)
            .select_from(ShopMemberOrm)
            .join(ShopOrm, ShopOrm.id == ShopMemberOrm.shop_id)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(
                ShopMemberOrm.user_id == user_id,
                ShopMemberOrm.removed_at.is_(None),
                ShopOrm.closed_at.is_(None),
            )
            .order_by(ShopOrm.id)
        )
        return [
            MembershipSummary(shop_id=shop_id, shop_name=name, role=role)
            for shop_id, name, role in (await self._session.execute(stmt)).all()
        ]
```

`backend/apps/tenancy/app/use_cases/list_memberships_interactor.py`:
```python
from __future__ import annotations

from hub.app.dtos.membership_summary import MembershipSummary
from hub.app.ports.membership_directory_port import MembershipDirectoryPort
from tenancy.app.ports.output.member_repository import MemberRepository


class ListMembershipsInteractor(MembershipDirectoryPort):
    """허브의 MembershipDirectoryPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, members: MemberRepository) -> None:
        self._members = members

    async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
        return await self._members.list_for_user(user_id)
```

`backend/apps/tenancy/dependencies/list_memberships_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from hub.app.ports.membership_directory_port import MembershipDirectoryPort
from tenancy.app.use_cases.list_memberships_interactor import ListMembershipsInteractor
from tenancy.dependencies.tenancy_wiring import build_member_repository


def get_list_memberships_use_case(db: DbSession) -> MembershipDirectoryPort:
    return ListMembershipsInteractor(members=build_member_repository(db))
```

- [ ] **Step 6: auth 쪽을 구현한다**

`backend/apps/auth/dependencies/hub_ports.py`:
```python
"""허브 포트 자리 — auth 가 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.membership_directory_port import MembershipDirectoryPort


def get_membership_directory() -> MembershipDirectoryPort:
    raise RuntimeError("MembershipDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/auth/app/dtos/get_me_dto.py` 전체:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.membership_summary import MembershipSummary


@dataclass(frozen=True)
class GetMeQuery:
    user_id: int


@dataclass(frozen=True)
class MeResponse:
    id: int
    display_name: str
    profile_image_url: str | None
    identities: tuple[str, ...]
    shops: tuple[MembershipSummary, ...]
```

`backend/apps/auth/app/use_cases/get_me_interactor.py` 전체:
```python
from __future__ import annotations

from auth.app.dtos.get_me_dto import GetMeQuery, MeResponse
from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UserNotFoundError
from hub.app.ports.membership_directory_port import MembershipDirectoryPort


class GetMeInteractor(GetMeUseCase):
    def __init__(self, users: UserRepository, memberships: MembershipDirectoryPort) -> None:
        self._users = users
        self._memberships = memberships

    async def get_me(self, query: GetMeQuery) -> MeResponse:
        user = await self._users.get(query.user_id)
        if user is None:
            raise UserNotFoundError("다시 로그인해 주세요.")
        identities = await self._users.list_identities(user.id)
        shops = await self._memberships.list_for_user(user.id)
        return MeResponse(
            id=user.id,
            display_name=user.display_name,
            profile_image_url=user.profile_image_url,
            identities=tuple(i.provider.value for i in identities),
            shops=tuple(shops),
        )
```

`backend/apps/auth/dependencies/get_me_provider.py` 전체:
```python
from __future__ import annotations

from fastapi import Depends

from auth.app.ports.input.get_me_use_case import GetMeUseCase
from auth.app.use_cases.get_me_interactor import GetMeInteractor
from auth.dependencies.auth_wiring import build_user_repository
from auth.dependencies.hub_ports import get_membership_directory
from core.database import DbSession
from hub.app.ports.membership_directory_port import MembershipDirectoryPort


def get_get_me_use_case(
    db: DbSession, memberships: MembershipDirectoryPort = Depends(get_membership_directory)
) -> GetMeUseCase:
    return GetMeInteractor(users=build_user_repository(db), memberships=memberships)
```

`backend/apps/auth/adapter/inbound/api/schemas/get_me_schema.py` 전체:
```python
from pydantic import BaseModel


class MeShopSchema(BaseModel):
    shop_id: int
    shop_name: str
    role: str


class MeResponseSchema(BaseModel):
    id: int
    display_name: str
    profile_image_url: str | None
    identities: list[str]
    shops: list[MeShopSchema]
```

`backend/apps/auth/adapter/inbound/api/v1/get_me_router.py`에서 import를 고치고 반환에 `shops`를 더한다.
```python
from auth.adapter.inbound.api.schemas.get_me_schema import MeResponseSchema, MeShopSchema
```
```python
    return MeResponseSchema(
        id=me.id,
        display_name=me.display_name,
        profile_image_url=me.profile_image_url,
        identities=list(me.identities),
        shops=[
            MeShopSchema(shop_id=s.shop_id, shop_name=s.shop_name, role=s.role) for s in me.shops
        ],
    )
```

- [ ] **Step 7: 진입점에서 자리를 채운다**

`backend/main.py`의 import 묶음에 더한다.
```python
from auth.dependencies.hub_ports import get_membership_directory
from tenancy.dependencies.list_memberships_provider import get_list_memberships_use_case
```
자리 채우기 묶음의 끝에 더한다.
```python
app.dependency_overrides[get_membership_directory] = get_list_memberships_use_case
```

`backend/tests/test_hub_port_binding.py` 전체:
```python
"""진입점이 허브 포트 자리를 빠짐없이 채웠는지 확인한다. 자리를 새로 만들면 여기에 더한다."""
import main
from auth.dependencies.hub_ports import get_membership_directory
from core.shop_guard import get_shop_access_port
from platform_admin.dependencies.hub_ports import get_operator_directory, get_shop_provisioning
from tenancy.dependencies.hub_ports import get_user_directory

_API_SLOTS = [
    get_shop_access_port,
    get_operator_directory,
    get_shop_provisioning,
    get_user_directory,
    get_membership_directory,
]


def test_API_프로세스는_허브_포트_자리를_모두_채운다():
    missing = [slot.__name__ for slot in _API_SLOTS if slot not in main.app.dependency_overrides]
    assert missing == []
```

- [ ] **Step 8: 통과를 확인한다**

Run: Step 4의 명령에 `tests/test_hub_port_binding.py tests/integration/test_auth_flow_wiring.py`를 더해 실행
Expected: 전부 통과한다.

- [ ] **Step 9: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `5 kept`.

```bash
git add backend/apps/hub backend/apps/auth backend/apps/tenancy backend/main.py backend/tests
git commit -m "feat(auth): 내 정보에 소속 매장 목록을 넣는다 (MembershipDirectoryPort)"
```

---

### Task 17: 전체 흐름·테넌트 격리 통합 테스트, 확인 스크립트, 문서

설계 8.1절의 API 테스트(토큰 없음 401, 소속 아님 403, 권한 없는 직원 403, 내보낸 직원 즉시 403)와 테넌트 격리 테스트를 실제 배선으로 돈다. 설계 8.4절 완료 기준 3번의 흐름을 게이트웨이를 거쳐 확인하는 스크립트를 두고, 문서를 맞춘다.

**통합 테스트는 앞선 작업들이 만든 동작을 실제 배선으로 고정한다. 쓰자마자 통과해야 한다.** 실패하면 테스트를 고쳐서 맞추지 말고 원인을 조사한다(superpowers:systematic-debugging). 앞 작업의 결함이면 그 슬라이스에서 고치고, 고친 내용을 보고에 적는다.

**Files:**
- Create: `backend/tests/integration/test_shop_flow_wiring.py`
- Create: `backend/scripts/check_shop_flow.sh`
- Create: `README.md`
- Modify: `backend/scripts/print_routes.py`, `_docs/harness.md`, `CLAUDE.md`, `backend/apps/hub/_docs/CLAUDE.md`, `_docs/decisions/002-hub-port-assembly.md`, `docs/superpowers/specs/2026-09-20-foundation-design.md`
- Modify: `backend/apps/auth/domain/value_objects/social_profile.py`, `backend/apps/auth/app/use_cases/auth_myself_interactor.py` (문구만)

**Interfaces:**
- Consumes: Task 2의 `wired` 픽스처·`Wired`·`bearer`, 앞선 모든 작업의 경로
- Produces: 없음 (검증과 문서)

- [ ] **Step 1: 매장 흐름 통합 테스트를 쓴다**

`backend/tests/integration/test_shop_flow_wiring.py`:
```python
"""매장 개설부터 내보내기까지, 그리고 매장 사이의 벽을 실제 배선으로 확인한다."""
import pytest

from tests.integration.support import bearer

pytestmark = pytest.mark.integration


async def _operator(wired, name="운영자"):
    login = await wired.login(name)
    await wired.execute("INSERT INTO platform_operators (user_id) VALUES (:id)", id=login["user_id"])
    return login


async def _open_shop(wired, operator, name="Hiss Haus"):
    response = await wired.api.post(
        "/v1/platform/shops", json={"name": name}, headers=bearer(operator["access_token"])
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _accept(wired, login, code):
    return await wired.api.post(
        "/v1/invites/accept", json={"code": code}, headers=bearer(login["access_token"])
    )


async def _shop_with_owner(wired, operator, shop_name, owner_name):
    shop = await _open_shop(wired, operator, shop_name)
    owner = await wired.login(owner_name)
    assert (await _accept(wired, owner, shop["owner_invite_code"])).status_code == 200
    return shop["shop_id"], owner


async def _staff_invite(wired, shop_id, owner):
    response = await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=bearer(owner["access_token"]))
    assert response.status_code == 201, response.text
    return response.json()["code"]


def _code(response):
    return (response.status_code, response.json()["code"])


async def test_매장_개설부터_내보내기까지_돈다(wired):
    operator = await _operator(wired)
    shop = await _open_shop(wired, operator)
    shop_id = shop["shop_id"]
    assert len(shop["owner_invite_code"]) == 8

    owner = await wired.login("사장님")
    joined = await _accept(wired, owner, shop["owner_invite_code"])
    assert joined.status_code == 200
    assert (joined.json()["shop_id"], joined.json()["role"]) == (shop_id, "owner")
    me = await wired.api.get("/v1/me", headers=bearer(owner["access_token"]))
    assert me.json()["shops"] == [{"shop_id": shop_id, "shop_name": "Hiss Haus", "role": "owner"}]

    staff = await wired.login("직원")
    staff_joined = await _accept(wired, staff, await _staff_invite(wired, shop_id, owner))
    assert staff_joined.json()["role"] == "staff"
    staff_member_id = staff_joined.json()["member_id"]

    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(staff["access_token"]))
    assert members.status_code == 200
    assert [(m["display_name"], m["role"]) for m in members.json()] == [("사장님", "owner"), ("직원", "staff")]

    # 권한 없는 직원은 초대도 매장 정보 수정도 할 수 없다.
    assert _code(await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=bearer(staff["access_token"]))) == (403, "PERMISSION_DENIED")
    assert _code(await wired.api.put(f"/v1/shops/{shop_id}/settings", json={"name": "직원이 바꾼 이름"}, headers=bearer(staff["access_token"]))) == (403, "PERMISSION_DENIED")

    updated = await wired.api.put(
        f"/v1/shops/{shop_id}/settings",
        json={"name": "히스 하우스", "phone": "02-000-0000", "address": "서울"},
        headers=bearer(owner["access_token"]),
    )
    assert updated.status_code == 200
    seen_by_staff = await wired.api.get(f"/v1/shops/{shop_id}/settings", headers=bearer(staff["access_token"]))
    assert (seen_by_staff.json()["name"], seen_by_staff.json()["phone"]) == ("히스 하우스", "02-000-0000")

    # 역할을 올리면 다음 요청부터 권한이 생기고, 낮추면 다시 사라진다.
    member_path = f"/v1/shops/{shop_id}/members/{staff_member_id}"
    promoted = await wired.api.patch(member_path, json={"role": "owner"}, headers=bearer(owner["access_token"]))
    assert (promoted.status_code, promoted.json()["role"]) == (200, "owner")
    assert (await wired.api.post(f"/v1/shops/{shop_id}/invites", headers=bearer(staff["access_token"]))).status_code == 201
    demoted = await wired.api.patch(member_path, json={"role": "staff"}, headers=bearer(owner["access_token"]))
    assert demoted.json()["role"] == "staff"

    # 내보낸 직원은 이미 받은 토큰으로도 바로 403 이다.
    assert (await wired.api.delete(member_path, headers=bearer(owner["access_token"]))).status_code == 204
    assert _code(await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(staff["access_token"]))) == (403, "NOT_A_MEMBER")
    staff_me = await wired.api.get("/v1/me", headers=bearer(staff["access_token"]))
    assert staff_me.json()["shops"] == []


async def test_마지막_사장은_낮추거나_내보낼_수_없다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    owner_path = f"/v1/shops/{shop_id}/members/{members.json()[0]['member_id']}"

    assert _code(await wired.api.patch(owner_path, json={"role": "staff"}, headers=bearer(owner["access_token"]))) == (409, "LAST_OWNER")
    assert _code(await wired.api.delete(owner_path, headers=bearer(owner["access_token"]))) == (409, "LAST_OWNER")


async def test_다른_매장의_멤버_초대_설정에는_손댈_수_없다(wired):
    """테넌트 격리 — A매장 사장이 B매장의 경로를 부르면 전부 403 NOT_A_MEMBER 다."""
    operator = await _operator(wired)
    _, a_owner = await _shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop_id, b_owner = await _shop_with_owner(wired, operator, "B 매장", "B사장")
    b_members = await wired.api.get(f"/v1/shops/{b_shop_id}/members", headers=bearer(b_owner["access_token"]))
    b_owner_path = f"/v1/shops/{b_shop_id}/members/{b_members.json()[0]['member_id']}"
    a = bearer(a_owner["access_token"])

    attempts = [
        await wired.api.get(f"/v1/shops/{b_shop_id}/members", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop_id}/invites", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop_id}/settings", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop_id}/settings", json={"name": "빼앗은 매장"}, headers=a),
        await wired.api.patch(b_owner_path, json={"role": "staff"}, headers=a),
        await wired.api.delete(b_owner_path, headers=a),
    ]
    assert [_code(r) for r in attempts] == [(403, "NOT_A_MEMBER")] * 6

    # 없는 매장도 같은 답이다 (매장이 있는지조차 알려 주지 않는다).
    assert _code(await wired.api.get("/v1/shops/999999/members", headers=a)) == (403, "NOT_A_MEMBER")
    # B 매장은 그대로다.
    settings = await wired.api.get(f"/v1/shops/{b_shop_id}/settings", headers=bearer(b_owner["access_token"]))
    assert settings.json()["name"] == "B 매장"


async def test_토큰_없는_요청은_표면마다_401_이다(wired):
    requests = [
        ("GET", "/v1/me"), ("POST", "/v1/invites/accept"),
        ("GET", "/v1/shops/1/members"), ("POST", "/v1/shops/1/invites"),
        ("PATCH", "/v1/shops/1/members/1"), ("DELETE", "/v1/shops/1/members/1"),
        ("GET", "/v1/shops/1/settings"), ("PUT", "/v1/shops/1/settings"),
        ("GET", "/v1/platform/myself"), ("POST", "/v1/platform/shops"),
    ]
    for method, path in requests:
        response = await wired.api.request(method, path, json={"code": "X", "name": "X", "role": "staff"})
        assert _code(response) == (401, "UNAUTHENTICATED"), f"{method} {path}"


async def test_매장_자기소개는_토큰_없이_응답한다(wired):
    response = await wired.api.get("/v1/shops/myself")
    assert response.status_code == 200
    assert "/v1/invites/accept" in response.json()["introduction"]


async def test_운영자가_아니면_운영자_표면을_쓸_수_없다(wired):
    user = await wired.login("보통유저")
    headers = bearer(user["access_token"])
    assert _code(await wired.api.post("/v1/platform/shops", json={"name": "몰래 만든 매장"}, headers=headers)) == (403, "PERMISSION_DENIED")
    assert _code(await wired.api.get("/v1/platform/myself", headers=headers)) == (403, "PERMISSION_DENIED")

    operator = await _operator(wired)
    myself = await wired.api.get("/v1/platform/myself", headers=bearer(operator["access_token"]))
    assert myself.status_code == 200


async def test_초대_코드는_한_번만_쓸_수_있고_이미_멤버면_409_다(wired):
    operator = await _operator(wired)
    shop = await _open_shop(wired, operator)
    owner = await wired.login("사장님")
    assert (await _accept(wired, owner, shop["owner_invite_code"])).status_code == 200

    latecomer = await wired.login("늦은사람")
    assert _code(await _accept(wired, latecomer, shop["owner_invite_code"])) == (400, "INVITE_EXHAUSTED")
    assert _code(await _accept(wired, latecomer, "ZZZZ9999")) == (400, "INVITE_INVALID")

    staff_code = await _staff_invite(wired, shop["shop_id"], owner)
    assert _code(await _accept(wired, owner, staff_code)) == (409, "ALREADY_A_MEMBER")
    # 실패한 수락은 초대를 쓰지 않는다. 다른 사람이 그 코드로 합류할 수 있다.
    assert (await _accept(wired, latecomer, staff_code.lower())).status_code == 200


async def test_만료된_초대_코드는_400_INVITE_EXPIRED_다(wired):
    operator = await _operator(wired)
    shop = await _open_shop(wired, operator)
    await wired.execute("UPDATE shop_invites SET expires_at = now() - interval '1 minute'")
    owner = await wired.login("사장님")
    assert _code(await _accept(wired, owner, shop["owner_invite_code"])) == (400, "INVITE_EXPIRED")


async def test_초대_코드_입력은_분당_다섯_번까지다(wired):
    user = await wired.login("마구넣는사람")
    for _ in range(5):
        assert _code(await _accept(wired, user, "ZZZZ9999")) == (400, "INVITE_INVALID")
    assert _code(await _accept(wired, user, "ZZZZ9999")) == (429, "TOO_MANY_ATTEMPTS")


async def test_닫힌_매장은_접근할_수_없고_내_매장_목록에서_빠진다(wired):
    operator = await _operator(wired)
    shop_id, owner = await _shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    await wired.execute("UPDATE shops SET closed_at = now() WHERE id = :id", id=shop_id)

    headers = bearer(owner["access_token"])
    assert _code(await wired.api.get(f"/v1/shops/{shop_id}/settings", headers=headers)) == (403, "SHOP_CLOSED")
    assert (await wired.api.get("/v1/me", headers=headers)).json()["shops"] == []
```

- [ ] **Step 2: 통과를 확인한다**

Run: `docker compose run --rm backend pytest tests/integration -q -p no:cacheprovider`
Expected: `16 passed` (인증 흐름 6 + 매장 흐름 10). 실패하면 테스트를 고치지 말고 원인을 조사한다.

- [ ] **Step 3: 라우트 표를 넓히고 전후를 비교한다**

경로가 길어져 표가 밀린다. `backend/scripts/print_routes.py`의 출력 줄에서 경로 폭을 바꾼다.
```python
        print(f"{process:8} {method:7} {path:44} {name}")
```

Run: `docker compose run --rm --no-deps auth python scripts/print_routes.py`
Expected: `auth` 줄은 계획 1과 같고(`/v1/auth/health`, `/v1/auth/logout`, `/v1/auth/myself`, `/v1/auth/refresh`, `/v1/auth/social`), `backend` 줄은 아래 12개다.
```
backend  GET     /health                                      health
backend  POST    /v1/invites/accept                           accept_invite
backend  GET     /v1/me                                       get_me
backend  GET     /v1/platform/myself                          introduce_myself
backend  POST    /v1/platform/shops                           create_shop
backend  GET     /v1/shops/myself                             introduce_myself
backend  POST    /v1/shops/{shop_id}/invites                  create_invite
backend  GET     /v1/shops/{shop_id}/members                  list_members
backend  DELETE  /v1/shops/{shop_id}/members/{member_id}      remove_member
backend  PATCH   /v1/shops/{shop_id}/members/{member_id}      change_member_role
backend  GET     /v1/shops/{shop_id}/settings                 get_shop
backend  PUT     /v1/shops/{shop_id}/settings                 update_shop
```

- [ ] **Step 4: 게이트웨이를 거치는 흐름 확인 스크립트를 쓴다**

`backend/scripts/check_shop_flow.sh`:
```bash
#!/usr/bin/env bash
# 개발 환경에서 매장 개설 → 사장 합류 → 직원 초대·합류 → 역할 변경 → 내보내기를 끝까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_shop_flow.sh
# infra/ 에서 실행해야 한다 (운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장과 유저가 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"

field() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
# call <메서드> <경로> <토큰> [본문] — 응답 본문을 출력한다
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# status <메서드> <경로> <토큰> [본문] — 상태 코드만 출력한다
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

op=$(login "flow-op-$STAMP"); op_token=$(echo "$op" | field access_token); op_id=$(echo "$op" | field user_id)
expect "운영자가 되기 전에는 매장을 개설할 수 없다" "$(status POST /v1/platform/shops "$op_token" '{"name":"x"}')" "403"
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"흐름확인-$STAMP\"}")
shop_id=$(echo "$shop" | field shop_id); owner_code=$(echo "$shop" | field owner_invite_code)
echo "통과  운영자가 매장 $shop_id 을(를) 개설했다"

owner_token=$(login "flow-owner-$STAMP" | field access_token)
expect "사장용 초대 코드로 합류하면 사장이다" "$(call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" | field role)" "owner"

staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field code)
staff_token=$(login "flow-staff-$STAMP" | field access_token)
joined=$(call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}")
expect "직원용 초대 코드로 합류하면 직원이다" "$(echo "$joined" | field role)" "staff"
staff_member_id=$(echo "$joined" | field member_id)

count=$(call GET "/v1/shops/$shop_id/members" "$staff_token" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")
expect "멤버 목록에 두 명이 보인다" "$count" "2"
expect "직원은 초대 코드를 만들 수 없다" "$(status POST "/v1/shops/$shop_id/invites" "$staff_token")" "403"
expect "직원을 사장으로 올린다" "$(status PATCH "/v1/shops/$shop_id/members/$staff_member_id" "$owner_token" '{"role":"owner"}')" "200"
expect "사장이 된 직원은 초대 코드를 만들 수 있다" "$(status POST "/v1/shops/$shop_id/invites" "$staff_token")" "201"
expect "다시 직원으로 낮춘다" "$(status PATCH "/v1/shops/$shop_id/members/$staff_member_id" "$owner_token" '{"role":"staff"}')" "200"
expect "직원을 내보낸다" "$(status DELETE "/v1/shops/$shop_id/members/$staff_member_id" "$owner_token")" "204"
expect "내보낸 직원은 바로 접근할 수 없다" "$(status GET "/v1/shops/$shop_id/members" "$staff_token")" "403"

echo "전체 흐름 확인 완료"
```

Run (`infra/`에서): `bash ../backend/scripts/check_auth_flow.sh && bash ../backend/scripts/check_shop_flow.sh`
Expected: 두 스크립트 모두 마지막 줄이 `전체 흐름 확인 완료`다.

- [ ] **Step 5: README를 만든다**

`README.md`:
```markdown
# 차곡노트

반려동물 미용 매장과 보호자를 잇는 플랫폼이다. 매장은 예약·고객·미용 기록을 관리하고, 보호자는 매장이 보낸 미용 알림장을 받아 본다. 이름은 기록이 "차곡차곡" 쌓인다는 뜻이다.

| 영역 | 스택 | 위치 |
|---|---|---|
| 백엔드 | Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) · Alembic | `backend/` |
| 앱 | Flutter 3.41 이상 | `app/` (아직 없음) |
| 개발 환경 | Docker Compose (pgvector · redis · minio · backend · auth · gateway) | `infra/` |
| 설계·계획 | 서브 프로젝트별 문서 | `docs/superpowers/` |

## 처음 띄우기

    cd infra
    docker compose build backend
    docker compose run --rm --no-deps backend python scripts/generate_dev_env.py   # .env 와 .env.auth 를 만든다 (이미 있으면 건너뛴다)
    docker compose up -d                                                            # 게이트웨이 http://127.0.0.1:8080
    bash ../backend/scripts/check_auth_flow.sh                                      # 로그인 흐름 확인
    bash ../backend/scripts/check_shop_flow.sh                                      # 매장 개설·합류 흐름 확인

개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.

## 더 읽을 것

- `CLAUDE.md` — 꼭 지킬 규칙과 명령어
- `_docs/architecture.md` — 계층, 수직 슬라이스, 허브-스포크, 허브 포트 조립, 폴더 작명 규칙
- `_docs/harness.md` — 검증 명령
- `_docs/decisions/` — 결정 기록
- `docs/superpowers/specs/` · `docs/superpowers/plans/` — 설계 문서와 구현 계획
```

- [ ] **Step 6: 하네스 문서와 루트 CLAUDE.md를 고친다**

`_docs/harness.md`의 표에 세 줄을 더한다 (라우트 표 줄 다음).
```markdown
| 로그인 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_auth_flow.sh` |
| 매장 개설·합류 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_shop_flow.sh` — 개발 DB에 확인용 매장과 유저가 남는다 |
| 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
```
그리고 목록 끝에 두 줄을 더한다.
```markdown
- `tests/integration/`은 두 프로세스의 실제 앱 객체에 붙어 프로바이더·DB 커밋·Redis까지 통과한다. 인증 프로세스의 개인키는 테스트마다 새로 만든 키로 바꿔 넣는다.
- 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다. 허브 포트 자리를 새로 만들면 `tests/test_hub_port_binding.py`에 더한다.
```

`CLAUDE.md`(루트)의 "꼭 지킬 것" 목록에서 `스포크끼리 직접 import하지 않는다…` 줄 다음에 두 줄을 더한다.
```markdown
- 스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
- 매장 범위의 경로는 `core/shop_guard.py`의 `get_shop_context` 또는 `require_permission`으로 `ShopContext`를 받는다. 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.
```
"명령어" 절의 코드 블록 끝에 한 줄을 더한다.
```
    docker compose run --rm backend python scripts/grant_operator.py <user_id>   # 플랫폼 운영자 지정 (user_id 는 GET /v1/me 의 id)
```

- [ ] **Step 7: 허브 문서를 고친다**

`backend/apps/hub/_docs/CLAUDE.md` 전체:
```markdown
# hub — 허브

스포크 사이의 계약(포트 ABC와 DTO)만 가진다. 구현은 스포크가 제공한다.

- 어떤 스포크도 import하지 않는다 (`.importlinter`의 허브 격리 계약).
- 포트는 실제로 쓰는 스포크가 생길 때 추가한다. 빈 껍데기 포트를 미리 만들지 않는다.
- 구현하는 스포크는 HTTP 표면이 없는 슬라이스로 만들고, 인터랙터가 포트 ABC를 직접 상속한다.
- 소비하는 스포크는 `dependencies/hub_ports.py`의 자리로 받는다. `main.py`가 구현을 꽂는다.

| 포트 | 구현 | 사용 |
|---|---|---|
| `ShopAccessPort.resolve(user_id, shop_id) → ShopContext` | tenancy `resolve_shop_access` | 매장 범위의 모든 스포크 (`core/shop_guard.py`) |
| `ShopProvisioningPort.create_shop(name, business_type) → ProvisionedShop` | tenancy `provision_shop` | platform_admin `create_shop` |
| `MembershipDirectoryPort.list_for_user(user_id) → list[MembershipSummary]` | tenancy `list_memberships` | auth `get_me` |
| `OperatorDirectoryPort.is_operator(user_id) → bool` | auth `check_operator` | platform_admin |
| `UserDirectoryPort.get_profiles(user_ids) → dict[int, UserProfile]` | auth `get_user_profiles` | tenancy `list_members` |

`MembershipLifecyclePort`(회원 탈퇴)는 계획 2-2에서 첫 소비자와 함께 들어온다.
```

- [ ] **Step 8: 설계 문서와 코드 문구를 정정한다**

넘김 항목 12·24·26이다. `docs/superpowers/specs/2026-09-20-foundation-design.md`에서 다음을 고친다.

(1) 3.3절의 `.env.auth` 항목에서 `(auth_main.py, conftest.py)`를 `(auth_main.py)`로 바꾼다.

(2) 3.3절의 "①에서 필요한 키" 목록에서 `` `KAKAO_REST_API_KEY` `` 앞에 `` `KAKAO_APP_ID`(카카오 토큰이 우리 앱에서 발급됐는지 확인한다), ``를 넣는다.

(3) 4.3절 표의 `factory/` 줄을 바꾼다.
```markdown
| `auth/adapter/outbound/factory/` | Factory | 설정에 따라 제공자 구현을 만들어 담아 두고 이름으로 골라 준다 |
```

(4) 4.4절 표 다음에 문단을 더한다.
```markdown
허브 포트를 구현하는 쪽은 HTTP 표면이 없는 슬라이스를 하나씩 더 가진다. tenancy는 `resolve_shop_access`·`provision_shop`·`list_memberships`, auth는 `check_operator`·`get_user_profiles`다. auth의 `grant_operator`도 HTTP 표면이 없고 `scripts/grant_operator.py`가 부른다. 직원용 초대의 역할은 언제나 직원이며, 사장을 늘리려면 합류한 뒤 역할을 바꾼다. 매장 정보 수정은 폼 전체를 보내는 `PUT`이다.
```

(5) 4.6절의 마지막 문단(`권한 검사는 require_permission…`)을 바꾼다.
```markdown
권한 검사는 `require_permission("member:manage")` 형태의 FastAPI 의존성으로 만들고, 안에서 `ShopAccessPort`를 호출한다. 모든 매장 범위 스포크가 함께 쓰므로 `core/shop_guard.py`에 둔다. 허브 포트의 구현은 진입점이 소비하는 쪽의 자리에 꽂는다(`_docs/decisions/002-hub-port-assembly.md`).
```

(6) 7절의 "주요 코드" 항목에서 `` `NOT_A_MEMBER`·`PERMISSION_DENIED`·`ACCOUNT_SUSPENDED`·`SHOP_CLOSED`(403) ``을 `` `NOT_A_MEMBER`·`PERMISSION_DENIED`·`ACCOUNT_SUSPENDED`·`SHOP_CLOSED`·`SHOP_SUSPENDED`(403), `MEMBER_NOT_FOUND`(404) ``로, `` `LAST_OWNER`(409) ``를 `` `LAST_OWNER`·`ALREADY_A_MEMBER`(409) ``로 바꾼다.

`backend/apps/auth/domain/value_objects/social_profile.py`의 docstring을 바꾼다.
```python
    """제공자가 확인해 준 신원. 신원을 가르는 값(provider_user_id, email)은 제공자 응답에서만 만든다.

    예외는 Apple 의 display_name 하나다. Apple 은 이름을 서버에 주지 않고 첫 로그인 때 앱에만 주므로
    앱이 보낸 값을 그대로 쓴다. 표시 이름일 뿐 신원 확인에는 쓰이지 않는다.
    """
```

`backend/apps/auth/app/use_cases/auth_myself_interactor.py`의 마지막 문장을 바꾼다.
```python
                "신원은 제공자에게 직접 확인한 값만 믿으며(Apple 의 표시 이름만 앱이 보낸 값을 씁니다) "
                "카카오·구글 토큰은 저장하지 않습니다."
```

- [ ] **Step 9: 결정 기록에 처리 현황을 더한다**

`_docs/decisions/002-hub-port-assembly.md`의 끝에 더한다.
```markdown

## 001의 넘김 항목 처리 현황 (계획 2-1 종료 시점)

| 항목 | 처리 |
|---|---|
| 1 실제 배선 통합 테스트 | 계획 2-1 Task 2·17 (`backend/tests/integration/`) |
| 2 시드와 픽스처 충돌, 4 ORM 등록 목록 | 계획 2-1 Task 1 (`scripts/prepare_test_db.py`, `orm_registry.py`, `tests/test_schema_drift.py`) |
| 3 스포크 간 조립 위치 | 이 문서. 진입점에서 조립 |
| 12 Factory 표기 | 이 문서. 표기만 완화 |
| 24·26 설계 문서·문구 정정, 25 README | 계획 2-1 Task 17 |
| 5~10, 18~23 | 계획 2-2 (계정 연결·해제, 회원 탈퇴와 함께) |
| 11 재사용 감지 유예 | 결정됨 — 두지 않는다 |
| 13~17 | 운영 전환 때 |

## 계획 2-1에서 새로 미룬 것

- **직원이 스스로 매장을 나가는 기능.** 지금은 사장이 내보내야 한다. 설계에 없어서 만들지 않았다.
- **초대 코드 목록·무효화.** `shop_invites.revoked_at` 컬럼과 도메인 검사는 있으나 무효화하는 슬라이스가 없다. 7일 만료와 1회 사용으로 충분한지 Hiss Haus 투입 뒤에 본다.
- **초대 코드 해시에 서버 비밀값(pepper)을 섞지 않았다.** DB를 읽을 수 있는 공격자는 이미 그 매장의 데이터를 읽을 수 있고, 코드는 7일·1회용이라 얻는 것이 작다.
- **닫힌 매장·정지된 매장을 만드는 기능.** `closed_at`은 회원 탈퇴(계획 2-2)가, `suspended_at`은 이후 운영자 기능이 쓴다. 지금은 읽기만 한다.
- **`/v1/me`의 매장 목록에 정지된 매장이 나온다.** 들어가면 `SHOP_SUSPENDED` 안내를 받는다. 앱(계획 3)에서 표시를 정한다.
```

- [ ] **Step 10: 최종 검증**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend alembic current
```
Expected: 두 pytest 실행이 모두 실패 0으로 끝난다. 둘을 합쳐 212개 안팎이다(시작 기준선 83개 + 이 계획 129개). `Contracts: 5 kept, 0 broken.` `alembic current`는 `0003 (head)`.

Run: `curl -s http://127.0.0.1:8080/v1/auth/myself | head -c 60; echo; curl -s http://127.0.0.1:8080/v1/shops/myself | head -c 60; echo; curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/v1/platform/myself`
Expected: 앞의 둘은 자기소개 JSON, 마지막은 `401`(설계 8.4절 완료 기준 1번 — 세 표면이 모두 응답한다).

- [ ] **Step 11: 커밋**

```bash
git add backend/tests/integration/test_shop_flow_wiring.py backend/scripts README.md CLAUDE.md _docs backend/apps/hub/_docs backend/apps/auth docs/superpowers/specs/2026-09-20-foundation-design.md
git commit -m "test(tenancy): 매장 흐름·테넌트 격리 통합 테스트와 확인 스크립트, 문서 정리"
```

---

## 계획 2-2로 넘기는 것

이 계획이 끝나면 설계 8.4절의 완료 기준 가운데 백엔드 몫은 1·2·3·5번이 채워진다(3번은 시뮬레이터 대신 `check_shop_flow.sh`로). 4번(계정 연결·해제, 탈퇴)이 계획 2-2다. 2-2는 이 계획을 구현한 뒤 실제 코드를 보고 쓴다. 쓸 때 먼저 읽을 것:

- `_docs/decisions/001-plan1-review-carryover.md`의 5~10번, 18~23번
- `_docs/decisions/002-hub-port-assembly.md`의 "계획 2-1에서 새로 미룬 것"
- 설계 문서 5.6절(계정 연결과 해제), 5.7절(회원 탈퇴)

2-2에서 정해야 할 것:

1. **`withdraw`는 인증 프로세스(`/v1/auth/account`)에 있다.** tenancy가 구현할 `MembershipLifecyclePort`를 `auth_main.py`가 자리에 꽂아야 한다. 인증 프로세스가 tenancy의 어댑터를 import하게 되는 첫 경우다. `tests/test_hub_port_binding.py`에 인증 프로세스용 자리 목록을 더한다(인증 프로세스는 개인키가 있어야 import되므로 통합 테스트 쪽에 둔다).
2. **리프레시 토큰 세대 번호(넘김 항목 5).** 검토한 방향: 토큰을 `{user_id}.{난수}`로 만들어 Lua 스크립트의 모든 키를 `KEYS`로 넘기고, 토큰 값에 발급 시점의 세대를 찍어 둔다. "모든 세션 폐기"는 세대 증가(`INCR`) 한 번이 되고 유저별 토큰 집합은 없어진다. 설계 5.2절의 Redis 키 구성이 바뀌므로 설계 문서 정정이 함께 필요하다.
3. **탈퇴와 마지막 사장 규칙의 관계.** `apply_withdrawal`은 `count_owners`와 같은 잠금을 써야 한다.
