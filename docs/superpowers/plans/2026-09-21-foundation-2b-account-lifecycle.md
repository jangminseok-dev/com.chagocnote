# 차곡노트 ① 기반 — 계획 2-2: 계정 연결·해제와 회원 탈퇴 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로그인한 유저가 소셜 로그인 수단을 더 붙이고 뗄 수 있고, 회원 탈퇴를 하면 소속 해제·매장 닫기·익명화·신원 삭제·세션 폐기·제공자 연결 끊기가 한 번에 일어나게 한다. 그 바탕으로 리프레시 토큰의 "모든 세션 폐기"를 경합 없이 만든다.

**Architecture:** 세 슬라이스(`link_identity`, `unlink_identity`, `withdraw`)는 auth 스포크에 있고 인증 프로세스(`/v1/auth/*`)에 장착한다. 탈퇴가 소속을 정리할 때는 허브의 `MembershipLifecyclePort`를 쓰고, tenancy가 HTTP 표면이 없는 슬라이스 `apply_withdrawal`로 구현하며, `auth_main.py`가 자리에 꽂는다. DB 변경은 요청 하나의 트랜잭션 안에서 끝내고, 제공자 쪽 연결 끊기(외부 HTTP)는 커밋이 끝난 뒤 백그라운드 작업으로 한다. 리프레시 토큰은 `{user_id}.{난수}` 모양으로 바꾸고 값에 발급 시점의 "세대"를 찍어, "모든 세션 폐기"를 세대 증가 한 번으로 만든다.

**Tech Stack:** Python 3.13 · FastAPI 0.141 · SQLAlchemy 2.0(asyncio) + asyncpg · Alembic · Pydantic 2 · redis-py 8(asyncio, Redis 7 Lua) · httpx · python-jose · cryptography(Fernet) · import-linter 2 · pytest 9 + pytest-asyncio 1.4 · Docker Compose

**Spec:** `docs/superpowers/specs/2026-09-20-foundation-design.md` — 이 계획은 그중 4.4절(auth의 `link_identity`·`unlink_identity`·`withdraw`), 4.5절(`/v1/auth/identities`, `/v1/auth/account`), 4.6절(`MembershipLifecyclePort`), 5.3절(토큰), 5.6절, 5.7절, 7절을 구현한다. 실행자는 설계 문서와 `_docs/decisions/001-plan1-review-carryover.md`(5~10번, 18~23번), `_docs/decisions/002-hub-port-assembly.md`("계획 2-1에서 새로 미룬 것")도 함께 읽는다.

**계획의 위치:** ① 기반의 구현 계획 네 개 가운데 세 번째다. 1(완료) → 2-1(완료) → **2-2(이 문서)** → 3(Flutter 앱). 이 계획이 끝나면 설계 8.4절 완료 기준의 백엔드 몫이 모두 채워진다.

**설계 문서와 다르게 가는 것 (이유와 함께 Task 12에서 설계 문서를 고친다):**
1. **구글 연결 끊기는 서버가 하지 않는다 (사용자 결정 2026-09-21).** 서버는 구글 ID 토큰만 검증하고 구글 토큰을 저장하지 않으므로 폐기할 토큰이 없다. 구글 공식 문서가 모바일 앱에 안내하는 경로대로 앱이 탈퇴·해제 성공 뒤 `google_sign_in`의 `disconnect()`를 부른다(계획 3). Apple은 서버가 REST로 폐기하고(App Store 5.1.1(v) 필수), 카카오는 서버가 어드민 키로 연결을 끊는다.
2. **`MembershipLifecyclePort`는 `apply_withdrawal` 하나만 가진다.** 설계의 `check_withdrawal`(미리 조회)은 만들지 않는다. 조회와 적용 사이에 다른 요청이 사장 수를 바꿀 수 있으므로, 적용이 잠금 안에서 스스로 확인하고 막는다. 앱은 확인 없이 먼저 부르고 `409 SHOP_CLOSE_CONFIRM_REQUIRED`를 받으면 확인을 받아 다시 부른다.
3. **유저 한 명은 제공자마다 신원을 하나만 가진다.** `DELETE /v1/auth/identities/{provider}`가 성립하려면 필요하다. 유일 제약 `(user_id, provider)`를 더한다.
4. **로그인 수단을 해제하면 모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다.** 해제한 수단으로 만든 세션이 다른 기기에 남지 않게 한다.
5. **Redis 키 구성이 바뀐다.** 유저별 토큰 집합(`auth:refresh:user:{id}`)을 없애고 세대 키(`auth:refresh:gen:{id}`)를 둔다.

## Global Constraints

- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준 상대 경로다. 절대 경로를 코드나 설정에 쓰지 않는다.
- 작업 브랜치는 `main`에서 딴 `feat/foundation-2b-account-lifecycle`이다. `main`에서 직접 작업하지 않는다.
- **커밋은 사용자가 작업 단위 커밋을 허용한 경우에만 한다.** 허용하지 않았으면 각 작업의 마지막 "커밋" 단계를 건너뛰고 바뀐 파일 목록만 보고한다. 푸시는 하지 않는다.
- Python 3.13. 의존성은 `backend/requirements.txt`에만 추가한다. 이 계획은 새 의존성을 추가하지 않는다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이다.
- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 테스트의 매장 이름으로 쓰는 것은 괜찮다.
- 수직 슬라이스 1:1: 유스케이스마다 router, schema, dto, input port, output port, interactor, provider, test 파일을 하나씩 둔다. HTTP 표면이 없는 슬라이스는 schema와 router를 생략한다. 허브 포트를 구현하는 슬라이스는 인터랙터가 허브 포트 ABC를 직접 상속한다.
- **스포크끼리 import하지 않는다. `dependencies/`도 예외가 아니다.** 다른 스포크가 구현한 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고 진입점이 `app.dependency_overrides`로 꽂는다. 빈 자리와 빠진 가드는 `tests/route_inspection.py`의 구조 테스트가 두 앱 모두에서 잡는다.
- **잠금 순서는 언제나 유저 행 → 매장 행(매장 ID 오름차순) → 멤버 행 → 초대 행이다.** 멤버십을 바꾸는 유스케이스는 맨 앞에서 `lock_membership_changes`로 매장 행을 잠근 뒤 대상을 읽는다. 계정을 바꾸는 유스케이스(`link_identity`·`unlink_identity`·`withdraw`)는 맨 앞에서 유저 행을 잠근 뒤 다시 읽는다.
- **잠금을 쥔 채 외부 HTTP를 부르지 않는다.** 제공자 검증은 잠금 전에, 제공자 연결 끊기는 커밋 뒤(백그라운드 작업)에 한다.
- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 예외는 컨텍스트가 없는 경로(소속 확인, 초대 수락, 매장 개설, 유저 기준 조회·탈퇴)뿐이다.
- 스포크를 넘는 외래 키를 걸지 않는다.
- 유스케이스는 app DTO(frozen dataclass)를 받는다. 스키마와 DTO 사이의 변환은 라우터가 한다. 아웃바운드 포트는 인터랙터가 실제로 호출하는 메서드만 가진다.
- `app`·`domain` 계층에서 `fastapi`, `sqlalchemy`, `redis`, `httpx`, `jose`, `cryptography`를 import하지 않는다. `domain`은 `pydantic`과 `core`도 import하지 않는다. `core`는 스포크를 import하지 않는다(구조 계약 6종).
- 엔티티(ORM)는 `int` 단일 PK `id`, `created_at`, `updated_at`을 가진다. 마이그레이션은 손으로 쓰고 `tests/test_schema_drift.py`가 ORM과 어긋나면 실패한다.
- I/O 작업은 `async def`, CPU 작업은 `def`다. 포트와 구현체의 `def`/`async def`를 일치시킨다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `backend/core/singleton/secret_manager.py`에서만 쓴다. 테스트에서 환경 변수를 바꿀 때는 `monkeypatch.setenv`를 쓴다.
- **인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 둔다.** 이 모듈은 함수 안에서만 import한다. 모듈 최상단에서 import하면 API 프로세스가 그 모듈을 불러올 때 실패한다.
- 비밀값과 토큰 원문을 로그·테스트 출력·문서에 남기지 않는다. `.env*` 파일 내용을 출력하지 않는다.
- 테스트는 mock 프레임워크 대신 스텁 구현을 쓴다. 실제 DB·Redis에 붙는 테스트는 `integration` 마커를 단다. 외부 제공자는 `httpx.MockTransport`로 대신한다.
- 오류 응답 본문은 `{"code": "...", "message": "..."}` 형식이다. 도메인 규칙 위반은 도메인 예외로 던지고 `error_map.py`가 HTTP 상태로 바꾼다.
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.
- 백엔드 검증 명령은 전부 `infra/`에서 `docker compose run --rm backend …` 형태로 실행한다. 볼륨 삭제, `docker compose down -v`, **개발 DB에서의 `alembic downgrade`는 실행하지 않는다.**
- 검증 명령의 줄임말:
  - **단위 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"`
  - **통합 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`
  - **구조 계약**: `docker compose run --rm --no-deps backend lint-imports --config .importlinter`

## 위협 점검표

계획 2-1에서는 작업별 검토가 "계획서 코드와 일치하는가"만 확인하는 바람에 계획서 자체의 구멍 두 개(내보낸 멤버의 재합류, 읽기와 잠금 사이의 경합)가 최종 검토까지 통과했다. 이번에는 권한과 불변식이 걸린 슬라이스마다 악의적이거나 운 나쁜 시나리오를 먼저 적고, 각각을 막는 코드와 테스트를 작업에 넣었다. **구현자와 검토자는 이 표를 코드와 대조한다. 표에 없는 시나리오를 찾으면 보고한다.**

| # | 시나리오 | 막는 것 | 확인하는 테스트 |
|---|---|---|---|
| A1 | 같은 리프레시 토큰이 동시에 두 번 온다. 재사용을 감지한 쪽의 "모든 세션 폐기"가 끝난 **뒤에** 다른 쪽이 새 토큰을 저장한다 | 토큰 값에 세대를 찍고, 꺼낼 때 현재 세대와 다르면 무효 | Task 1 `test_세션_폐기와_경합한_새_토큰은_쓸_수_없다` |
| A2 | 폐기된 세대의 옛 토큰을 계속 다시 보내 재로그인한 유저의 세션을 매번 끊는다 | 옛 세대의 used 흔적은 재사용 신호로 보지 않는다 | Task 1 `test_폐기된_세대의_옛_토큰은_재사용_신호가_아니다` |
| A3 | 토큰 앞의 유저 ID를 바꿔 다른 유저의 세대로 검사받는다 | 키가 토큰 전체의 해시라 앞을 바꾸면 저장된 키와 어긋난다 | Task 1 `test_앞의_유저_ID_를_바꾼_토큰은_MISSING_이다` |
| B1 | API 프로세스가 암호화 키나 개인키를 읽는다 | 두 값은 `core/auth_config.py`에만 있고 API 경로는 그 모듈을 import하지 않는다 | Task 2 `test_API_프로세스는_인증_전용_설정을_불러오지_않는다` |
| C1 | 같은 소셜 계정의 첫 로그인이 동시에 두 번 온다 | 유일 제약 + 세이브포인트, 진 쪽은 다시 조회해 같은 유저로 로그인 | Task 3 리포지토리·인터랙터 테스트 |
| D1 | 모르는 `kid`를 담은 토큰을 쏟아부어 제공자 공개키를 끝없이 다시 받게 만든다 | 강제 재조회는 60초에 한 번 | Task 4 `test_강제_재조회는_간격_안에서는_한_번만_한다` |
| E1 | 내보내기·강등·탈퇴와 초대 수락이 서로 다른 순서로 잠가 교착한다 | 수락도 맨 앞에서 매장 행을 잠근다 (매장 → 멤버 → 초대) | Task 6 두 세션 테스트 |
| F1 | 탈퇴 직전에 다른 사장이 낮춰져서, 확인 때는 사장이 둘이었는데 적용 때는 혼자다 | 미리 조회하지 않는다. 적용이 매장 행을 잠근 뒤 다시 읽고 판단한다 | Task 7 `test_잠근_뒤에_다시_읽은_역할로_판단한다` |
| F2 | 탈퇴한 사장이 미리 만들어 둔 초대 코드가 살아 있다 | 소속 해제와 같은 트랜잭션에서 그 멤버의 초대를 무효화 | Task 7, Task 12 통합 테스트 |
| F3 | 두 유저가 서로 다른 순서로 매장을 잠가 교착한다 | 매장 ID 오름차순으로 잠근다 | Task 7 `test_매장을_ID_순서로_잠근다` |
| F4 | 탈퇴와 겹친 초대 수락이 소속을 되살린다 — 수락은 `users`를 보지도 잠그지도 않아, 탈퇴가 쥔 매장 잠금 뒤에서 기다리다 커밋 직후 합류한다 (Task 7 검토에서 발견) | 수락이 맨 앞에서 `ActiveUserGuardPort.lock_active`로 유저 행을 잠그고 활동 중인지 다시 본다 | Task 8b `test_탈퇴가_유저_행을_쥔_동안_수락은_기다리고_탈퇴한_뒤에는_거절된다` |
| G1 | 로그인 수단이 둘일 때 서로 다른 수단의 해제가 동시에 와서 0개가 된다 | 유저 행을 먼저 잠그고 다시 센다 | Task 12 `test_동시에_서로_다른_수단을_해제해도_하나는_남는다` |
| G2 | 탈퇴와 연결이 겹쳐, 탈퇴한 유저에 신원이 붙는다 (그 신원으로 로그인하면 탈퇴한 유저가 나온다) | 연결도 유저 행을 잠근 뒤 탈퇴 여부를 다시 본다 | Task 9 `test_잠근_뒤에_탈퇴한_유저면_붙이지_않는다` |
| G3 | 남의 소셜 계정을 내 계정에 붙인다 | 제공자에게 직접 검증한 신원만 붙이고, `(provider, provider_user_id)` 유일 제약으로 409 | Task 8·9, Task 12 |
| G4 | 한 유저에 같은 제공자의 신원이 둘 붙어 `DELETE /identities/{provider}`가 모호해진다 | `(user_id, provider)` 유일 제약으로 409 | Task 8·9 |
| G5 | 해제한 로그인 수단으로 만든 세션이 다른 기기에 30일 남는다 | 해제하면 모든 세션 폐기 + 요청한 기기에만 새 토큰 | Task 10, Task 12 |
| H1 | 탈퇴가 중간에 실패해 "익명화는 됐는데 신원은 남은" 상태가 된다 (로그인은 되는데 모든 요청이 401) | DB 변경 전체가 요청 하나의 트랜잭션이다. 실패하면 전부 되돌아간다 | Task 12 `test_막힌_탈퇴는_아무것도_바꾸지_않는다` |
| H2 | 제공자 연결 끊기가 느리거나 실패해 매장 행 잠금을 오래 쥐거나 탈퇴가 실패한다 | 커밋 뒤 백그라운드에서 끊고, 실패는 로그만 남긴다 | Task 5·10·11 |
| H3 | 탈퇴한 유저가 이미 받은 액세스 토큰(15분)이나 리프레시 토큰으로 계속 쓴다 | 매 요청의 `deleted_at` 확인(기존) + 세대 증가 | Task 12 |
| H4 | 탈퇴한 운영자의 지정이 남는다 | 탈퇴가 `platform_operators` 행을 지운다 | Task 8·11 |
| H5 | 같은 유저의 탈퇴가 동시에 두 번 온다 | 유저 행 잠금 뒤 다시 읽어 이미 탈퇴했으면 아무것도 하지 않는다 | Task 11 |

**이 계획으로도 남는 것 (Task 12에서 결정 기록에 적는다):** 세션을 훔친 공격자가 자기 소셜 계정을 피해자 계정에 붙이는 것은 막지 못한다. 막으려면 계정 연결·해제·탈퇴 앞에 재인증(방금 로그인했는지 확인)을 두어야 하며, 앱 흐름과 함께 계획 3 이후에 정한다.

## 시작 전 기준선

`main`(715cb81)의 상태다. 시작 전에 한 번 확인한다.

- 단위 166개, 통합 70개가 통과한다. 구조 계약 6종이 통과한다(`Contracts: 6 kept, 0 broken.`). `alembic current`는 `0003 (head)`.
- `docker compose ps`에서 여섯 서비스가 모두 `running`이다. 아니면 `docker compose up -d`를 먼저 한다.

## 파일 지도

```
_docs/decisions/003-account-lifecycle.md            # 이 계획의 결정과 미룬 것
_docs/harness.md · README.md · CLAUDE.md            # 확인 스크립트·비밀값 규칙 갱신
docs/superpowers/specs/2026-09-20-foundation-design.md   # 3.3·4.6·5.2·5.6·5.7·7절 정정
.env.example
backend/
├── auth_main.py                    # 새 라우터 3개, MembershipLifecyclePort 자리 채우기, HTTP 클라이언트 정리
├── core/auth_config.py · config.py · security.py
├── alembic/versions/0004_social_identities_user_provider_unique.py
├── scripts/generate_dev_env.py · check_account_flow.sh
├── tests/test_config_boundary.py · tests/integration/{support,conftest,test_account_flow_wiring}.py
└── apps/
    ├── hub/app/ports/membership_lifecycle_port.py
    ├── tenancy/
    │   ├── app/use_cases/apply_withdrawal_interactor.py · dependencies/apply_withdrawal_provider.py
    │   ├── 포트·PG: lock_membership_changes(shop_id) · list_active_for_user · count_active · ShopRepository.close · find_shop_id_by_code_hash
    │   └── accept_invite: 매장 행을 먼저 잠근다
    └── auth/
        ├── domain/services/refresh_token_factory.py · identity_guard.py
        ├── domain/value_objects/{refresh_lookup,identity_revocation}.py · domain/errors.py
        ├── app/services/{session_issuer,provider_revoker}.py
        ├── app/ports/output/{refresh_token_store_port,social_provider_port,user_repository,operator_repository}.py
        ├── adapter/outbound/redis/refresh_token_redis_store.py      # 세대 번호
        ├── adapter/outbound/gateways/fernet_cipher.py               # decrypt
        ├── adapter/outbound/strategy/*.py · factory/                # revoke, JWKS 재조회
        ├── adapter/outbound/pg/{user,operator}_pg_repository.py · orm/user_orm.py
        ├── 슬라이스: link_identity · unlink_identity · withdraw (router·schema·dto·port·interactor·provider·test)
        └── dependencies/{auth_wiring,hub_ports}.py
```

| 슬라이스 | 표면 | 프로세스 | 인증 |
|---|---|---|---|
| auth `link_identity` | `POST /v1/auth/identities` | auth | 액세스 토큰 |
| auth `unlink_identity` | `DELETE /v1/auth/identities/{provider}` | auth | 액세스 토큰 |
| auth `withdraw` | `DELETE /v1/auth/account` | auth | 액세스 토큰 |
| tenancy `apply_withdrawal` | 없음 (`MembershipLifecyclePort` 구현) | auth에 꽂힌다 | — |

---

### Task 1: 리프레시 토큰 세대 번호

넘김 항목 5·20이다. 지금은 같은 리프레시 토큰이 동시에 두 번 오면, 재사용을 감지한 쪽의 `revoke_all`이 끝난 뒤에 다른 쪽이 새 토큰을 저장해서 그 토큰이 살아남는다. 같은 "모든 세션 폐기"를 탈퇴와 로그인 수단 해제가 쓰게 되므로 먼저 고친다.

설계는 다음과 같다(실험으로 확인함).
- 토큰은 `{user_id}.{난수}` 모양이다. 서버는 토큰만 보고 유저를 알 수 있어서 Lua 스크립트의 모든 키를 미리 `KEYS`로 넘길 수 있다.
- `auth:refresh:{해시}` → 발급 시점의 세대, `auth:refresh:used:{해시}` → 쓸 때의 세대, `auth:refresh:gen:{user_id}` → 현재 세대.
- 꺼낼 때 저장된 세대가 현재 세대와 다르면 무효다. **"모든 세션 폐기"는 세대를 하나 올리는 것(`INCR`)이 전부다.** 유저별 토큰 집합은 없앤다.
- 갱신은 꺼낼 때 받은 세대로 새 토큰을 저장한다. 그 사이 세대가 올랐으면 새 토큰은 태어나면서 무효다.

개발 Redis에 남아 있던 옛 모양의 토큰은 모두 무효가 된다(다시 로그인하면 된다).

**Files:**
- Modify: `backend/apps/auth/domain/services/refresh_token_factory.py`
- Modify: `backend/apps/auth/domain/value_objects/refresh_lookup.py`
- Modify: `backend/apps/auth/app/ports/output/refresh_token_store_port.py`
- Modify: `backend/apps/auth/adapter/outbound/redis/refresh_token_redis_store.py` (전체 교체)
- Modify: `backend/apps/auth/app/services/session_issuer.py`
- Modify: `backend/apps/auth/app/use_cases/refresh_token_interactor.py`
- Modify: `backend/apps/auth/_docs/CLAUDE.md`
- Test: `backend/apps/auth/tests/domain/test_refresh_token_factory.py` (새로), `backend/apps/auth/tests/adapter/test_refresh_token_redis_store.py` (전체 교체), `backend/apps/auth/tests/app/test_session_issuer.py` (전체 교체), `backend/apps/auth/tests/app/use_cases/test_refresh_token_interactor.py` (수정)

**Interfaces:**
- Consumes: `core.redis.get_redis`(`decode_responses=True`)
- Produces:
  - `auth.domain.services.refresh_token_factory`: `new_refresh_token(user_id: int) -> str`, `refresh_token_user_id(token: str) -> int | None`
  - `auth.domain.value_objects.refresh_lookup.RefreshLookup(status: RefreshStatus, user_id: int | None, generation: int | None = None)`
  - `RefreshTokenStorePort`: `async current_generation(user_id: int) -> int`, `async save(token: str, user_id: int, generation: int) -> None`, `async take(token: str) -> RefreshLookup`, `async revoke(token: str) -> None`, `async revoke_all(user_id: int) -> None`
  - `SessionIssuer.issue(user_id: int, generation: int | None = None) -> TokenPair` — `generation`이 없으면 현재 세대를 읽어 쓴다(로그인). 갱신은 꺼낼 때 받은 세대를 넘긴다.

- [ ] **Step 1: 작업 브랜치를 만든다**

Run (저장소 루트에서): `git switch -c feat/foundation-2b-account-lifecycle`

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/domain/test_refresh_token_factory.py`:
```python
from auth.domain.services.refresh_token_factory import new_refresh_token, refresh_token_user_id


def test_토큰은_유저_ID_로_시작하고_매번_다르다():
    first, second = new_refresh_token(7), new_refresh_token(7)
    assert first.startswith("7.") and second.startswith("7.")
    assert first != second
    assert len(first.split(".", 1)[1]) >= 43


def test_토큰에서_유저_ID_를_읽는다():
    assert refresh_token_user_id(new_refresh_token(1234)) == 1234


def test_모양이_다른_토큰은_None_이다():
    for token in ("", "no-dot", ".abc", "abc.def", "-1.abc", "７.abc"):
        assert refresh_token_user_id(token) is None
```

`backend/apps/auth/tests/adapter/test_refresh_token_redis_store.py` 전체:
```python
import asyncio

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


async def _save(store, token, user_id):
    await store.save(token, user_id, await store.current_generation(user_id))


async def test_저장한_토큰은_한_번만_꺼낼_수_있다(store):
    await _save(store, "7.token-a", 7)
    first = await store.take("7.token-a")
    assert (first.status, first.user_id, first.generation) == (RefreshStatus.ACTIVE, 7, 0)
    second = await store.take("7.token-a")
    assert (second.status, second.user_id) == (RefreshStatus.USED, 7)


async def test_모르는_토큰과_모양이_다른_토큰은_MISSING_이다(store):
    for token in ("7.never-issued", "no-user-prefix"):
        lookup = await store.take(token)
        assert (lookup.status, lookup.user_id) == (RefreshStatus.MISSING, None)


async def test_폐기한_토큰은_MISSING_이다(store):
    await _save(store, "7.token-b", 7)
    await store.revoke("7.token-b")
    assert (await store.take("7.token-b")).status is RefreshStatus.MISSING


async def test_유저의_모든_세션을_폐기하면_세대가_오른다(store):
    await _save(store, "7.token-c", 7)
    await _save(store, "7.token-d", 7)
    await _save(store, "8.token-e", 8)
    await store.revoke_all(7)
    assert await store.current_generation(7) == 1
    assert (await store.take("7.token-c")).status is RefreshStatus.MISSING
    assert (await store.take("7.token-d")).status is RefreshStatus.MISSING
    assert (await store.take("8.token-e")).status is RefreshStatus.ACTIVE


async def test_폐기한_뒤에_새로_저장한_토큰은_쓸_수_있다(store):
    await store.revoke_all(7)
    await _save(store, "7.token-f", 7)
    lookup = await store.take("7.token-f")
    assert (lookup.status, lookup.generation) == (RefreshStatus.ACTIVE, 1)


async def test_세션_폐기와_경합한_새_토큰은_쓸_수_없다(store):
    """A1 — 갱신이 토큰을 꺼낸 뒤, 새 토큰을 저장하기 전에 모든 세션 폐기가 끼어든다."""
    await _save(store, "7.old", 7)
    taken = await store.take("7.old")          # 갱신 요청이 세대 0 으로 꺼냈다
    await store.revoke_all(7)                  # 그 사이 재사용 감지(또는 탈퇴)가 세션을 모두 끊었다
    await store.save("7.new", 7, taken.generation)   # 갱신 요청이 뒤늦게 새 토큰을 저장한다
    assert (await store.take("7.new")).status is RefreshStatus.MISSING


async def test_폐기된_세대의_옛_토큰은_재사용_신호가_아니다(store):
    """A2 — 옛 세대의 used 토큰을 다시 보내도 재로그인한 세션을 또 끊지 않는다."""
    await _save(store, "7.stolen", 7)
    await store.take("7.stolen")
    await store.revoke_all(7)
    assert (await store.take("7.stolen")).status is RefreshStatus.MISSING


async def test_앞의_유저_ID_를_바꾼_토큰은_MISSING_이다(store):
    """A3 — 키가 토큰 전체의 해시라, 앞을 바꾸면 저장된 키와 어긋난다."""
    await _save(store, "7.token-g", 7)
    assert (await store.take("8.token-g")).status is RefreshStatus.MISSING
    assert (await store.take("7.token-g")).status is RefreshStatus.ACTIVE


async def test_토큰_원문은_Redis_키에도_값에도_남지_않는다(store):
    await _save(store, "7.plain-token-value", 7)
    keys = [k async for k in store._redis.scan_iter("*")]
    values = [await store._redis.get(k) for k in keys]
    assert keys and all("plain-token-value" not in item for item in keys + values)


async def test_동시에_같은_토큰을_꺼내면_하나는_ACTIVE_다른_하나는_USED_다(store):
    await _save(store, "7.token-h", 7)
    first, second = await asyncio.gather(store.take("7.token-h"), store.take("7.token-h"))
    assert sorted((first.status, second.status), key=lambda s: s.value) == [
        RefreshStatus.ACTIVE,
        RefreshStatus.USED,
    ]
```

`backend/apps/auth/tests/app/test_session_issuer.py` 전체:
```python
from auth.app.dtos.token_dto import AccessToken
from auth.app.services.session_issuer import SessionIssuer


class _StubIssuer:
    def issue_access(self, user_id):
        return AccessToken(token=f"access-for-{user_id}", expires_in=900)


class _StubStore:
    def __init__(self, generation=0):
        self.generation = generation
        self.saved = []

    async def current_generation(self, user_id):
        return self.generation

    async def save(self, token, user_id, generation):
        self.saved.append((token, user_id, generation))


async def test_로그인은_현재_세대로_리프레시_토큰을_저장한다():
    store = _StubStore(generation=3)
    pair = await SessionIssuer(_StubIssuer(), store).issue(5)
    assert (pair.access_token, pair.expires_in) == ("access-for-5", 900)
    assert store.saved == [(pair.refresh_token, 5, 3)]
    assert pair.refresh_token.startswith("5.")


async def test_갱신은_꺼낼_때_받은_세대로_저장한다():
    store = _StubStore(generation=9)
    pair = await SessionIssuer(_StubIssuer(), store).issue(5, generation=2)
    assert store.saved == [(pair.refresh_token, 5, 2)]


async def test_리프레시_토큰은_매번_다르다():
    issuer = SessionIssuer(_StubIssuer(), _StubStore())
    assert (await issuer.issue(5)).refresh_token != (await issuer.issue(5)).refresh_token
```

`backend/apps/auth/tests/app/use_cases/test_refresh_token_interactor.py`에서 두 곳을 고친다.

(1) `_StubSessions.issue`를 바꾼다.
```python
    async def issue(self, user_id, generation=None):
        self.issued_for.append((user_id, generation))
        return TokenPair("new-access", "new-refresh", 900)
```
(2) 첫 테스트를 바꾼다.
```python
async def test_유효한_토큰이면_꺼낼_때의_세대로_새_토큰_한_쌍을_발급한다():
    interactor, _, sessions = _run(RefreshLookup(RefreshStatus.ACTIVE, 5, 4), _user())
    pair = await interactor.refresh(RefreshTokenCommand("5.old-refresh"))
    assert pair.refresh_token == "new-refresh"
    assert sessions.issued_for == [(5, 4)]
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/domain/test_refresh_token_factory.py apps/auth/tests/adapter/test_refresh_token_redis_store.py apps/auth/tests/app -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'refresh_token_user_id'`, `AttributeError: … 'current_generation'` 등

- [ ] **Step 4: 도메인을 고친다**

`backend/apps/auth/domain/services/refresh_token_factory.py` 전체:
```python
import secrets


def new_refresh_token(user_id: int) -> str:
    """추측할 수 없는 불투명 문자열. JWT 가 아니다 — 서버 저장소에 있어야만 유효하다.

    앞에 유저 ID 를 붙인다. 서버가 토큰만 보고 그 유저의 세대 키를 알 수 있어야
    Redis 스크립트의 모든 키를 미리 넘길 수 있다. 유저 ID 는 액세스 토큰에도 있는 값이라 숨길 것이 아니다.
    """
    return f"{user_id}.{secrets.token_urlsafe(48)}"


def refresh_token_user_id(token: str) -> int | None:
    head, dot, _ = token.partition(".")
    return int(head) if dot and head.isascii() and head.isdigit() else None
```

`backend/apps/auth/domain/value_objects/refresh_lookup.py`의 `RefreshLookup`에 필드 하나를 더한다.
```python
@dataclass(frozen=True)
class RefreshLookup:
    status: RefreshStatus
    user_id: int | None
    generation: int | None = None  # ACTIVE 일 때만 의미가 있다 — 새 토큰을 이 세대로 저장한다
```

- [ ] **Step 5: 포트와 저장소를 고친다**

`backend/apps/auth/app/ports/output/refresh_token_store_port.py` 전체:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.domain.value_objects.refresh_lookup import RefreshLookup


class RefreshTokenStorePort(ABC):
    @abstractmethod
    async def current_generation(self, user_id: int) -> int:
        """유저의 현재 세대. "모든 세션 폐기"가 일어날 때마다 하나씩 오른다."""

    @abstractmethod
    async def save(self, token: str, user_id: int, generation: int) -> None:
        """generation 은 발급 시점의 세대다. 그 뒤 세대가 오르면 이 토큰은 무효가 된다."""

    @abstractmethod
    async def take(self, token: str) -> RefreshLookup:
        """토큰을 꺼내면서 '사용됨'으로 바꾼다. 같은 토큰은 한 번만 ACTIVE 로 나온다."""

    @abstractmethod
    async def revoke(self, token: str) -> None: ...

    @abstractmethod
    async def revoke_all(self, user_id: int) -> None:
        """세대를 올린다. 이미 발급된 토큰도, 지금 발급 중인 토큰도 모두 무효가 된다."""
```

`backend/apps/auth/adapter/outbound/redis/refresh_token_redis_store.py` 전체:
```python
from __future__ import annotations

import hashlib

from redis.asyncio import Redis

from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.domain.services.refresh_token_factory import refresh_token_user_id
from auth.domain.value_objects.refresh_lookup import RefreshLookup, RefreshStatus


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# take() 는 "활성 키를 읽고 지우고, 세대를 확인하고, 사용됨 흔적을 쓰는" 일을 한 번에 해야 한다.
# 두 요청이 같은 토큰으로 동시에 들어와도 하나만 active 를 받는다.
# 키는 전부 KEYS 로 받는다 (토큰 앞의 유저 ID 덕분에 미리 알 수 있다).
_TAKE_SCRIPT = """
local stored = redis.call("GETDEL", KEYS[1])
local current = redis.call("GET", KEYS[3]) or "0"
if stored then
    if stored ~= current then
        return {"missing"}
    end
    redis.call("SET", KEYS[2], stored, "EX", ARGV[1])
    return {"active", stored}
end
local used = redis.call("GET", KEYS[2])
if used and used == current then
    return {"used"}
end
return {"missing"}
"""


class RefreshTokenRedisStore(RefreshTokenStorePort):
    """키 구성
    auth:refresh:{해시}        → 발급 시점의 세대   (유효한 토큰)
    auth:refresh:used:{해시}   → 쓸 때의 세대       (이미 쓴 토큰의 흔적 — 재사용 감지용)
    auth:refresh:gen:{user_id} → 현재 세대          ("모든 세션 폐기"마다 하나씩 오른다. 만료가 없다)
    토큰 원문은 저장하지 않는다. 유저 ID 는 토큰 앞부분에서 읽는다.
    이 클래스는 decode_responses=True 인 클라이언트(core.redis.get_redis)를 전제로 한다.
    """

    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def current_generation(self, user_id: int) -> int:
        return int(await self._redis.get(f"auth:refresh:gen:{user_id}") or 0)

    async def save(self, token: str, user_id: int, generation: int) -> None:
        await self._redis.set(f"auth:refresh:{_digest(token)}", generation, ex=self._ttl)

    async def take(self, token: str) -> RefreshLookup:
        user_id = refresh_token_user_id(token)
        if user_id is None:
            return RefreshLookup(RefreshStatus.MISSING, None)
        digest = _digest(token)
        result = await self._redis.eval(
            _TAKE_SCRIPT,
            3,
            f"auth:refresh:{digest}",
            f"auth:refresh:used:{digest}",
            f"auth:refresh:gen:{user_id}",
            self._ttl,
        )
        if result[0] == "active":
            return RefreshLookup(RefreshStatus.ACTIVE, user_id, int(result[1]))
        if result[0] == "used":
            return RefreshLookup(RefreshStatus.USED, user_id)
        return RefreshLookup(RefreshStatus.MISSING, None)

    async def revoke(self, token: str) -> None:
        await self._redis.delete(f"auth:refresh:{_digest(token)}")

    async def revoke_all(self, user_id: int) -> None:
        await self._redis.incr(f"auth:refresh:gen:{user_id}")
```

- [ ] **Step 6: 발급 절차와 갱신 유스케이스를 고친다**

`backend/apps/auth/app/services/session_issuer.py`의 `issue`를 바꾼다.
```python
    async def issue(self, user_id: int, generation: int | None = None) -> TokenPair:
        """generation 이 없으면 현재 세대로 발급한다(로그인). 갱신은 꺼낼 때 받은 세대를 넘긴다 —
        그 사이 모든 세션 폐기가 끼어들었다면 새 토큰도 함께 무효가 되어야 하기 때문이다."""
        access = self._token_issuer.issue_access(user_id)
        refresh = new_refresh_token(user_id)
        if generation is None:
            generation = await self._refresh_store.current_generation(user_id)
        await self._refresh_store.save(refresh, user_id, generation)
        return TokenPair(
            access_token=access.token, refresh_token=refresh, expires_in=access.expires_in
        )
```

`backend/apps/auth/app/use_cases/refresh_token_interactor.py`의 마지막 줄을 바꾼다.
```python
        return await self._sessions.issue(user.id, lookup.generation)
```

- [ ] **Step 7: 통과를 확인한다**

Run: Step 3의 명령
Expected: 전부 통과한다.

Run: `docker compose run --rm backend pytest tests/integration/test_auth_flow_wiring.py -q -p no:cacheprovider`
Expected: `6 passed` — 갱신·재사용 감지·로그아웃의 HTTP 동작은 그대로다.

- [ ] **Step 8: auth 문서를 고친다**

`backend/apps/auth/_docs/CLAUDE.md`에서 아래 줄을
```markdown
- 리프레시 토큰은 쓸 때마다 새 토큰으로 바꾼다. 이미 쓴 토큰이 다시 들어오면 그 유저의 세션을 모두 폐기한다.
```
다음으로 바꾼다.
```markdown
- 리프레시 토큰은 `{user_id}.{난수}` 모양이고 쓸 때마다 새 토큰으로 바꾼다. 이미 쓴 토큰이 다시 들어오면 그 유저의 세션을 모두 폐기한다.
- "모든 세션 폐기"는 유저의 세대(`auth:refresh:gen:{user_id}`)를 하나 올리는 것이다. 토큰 값에 발급 시점의 세대가 찍혀 있고, 꺼낼 때 현재 세대와 다르면 무효다. 갱신은 꺼낼 때 받은 세대로 새 토큰을 저장하므로, 그 사이 폐기가 끼어들면 새 토큰도 무효가 된다.
```

- [ ] **Step 9: 전체 검증과 커밋**

Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.
Run: `bash ../backend/scripts/check_auth_flow.sh` → 마지막 줄 `전체 흐름 확인 완료`.

```bash
git add backend/apps/auth
git commit -m "fix(auth): 리프레시 토큰에 세대를 찍어 모든 세션 폐기의 경합을 없앤다"
```

---

### Task 2: 인증 프로세스 전용 비밀값과 HTTP 클라이언트 수명

넘김 항목 6·10이다. 제공자 토큰을 암호화·복호화하는 것은 인증 프로세스뿐인데 `IDENTITY_TOKEN_ENC_KEY`가 API 프로세스에도 필수값으로 걸려 있다. 키를 `core/auth_config.py`로 옮기고, 읽기만 하는 경로(`get_me` 등)의 리포지토리는 암호화 도구 없이 조립한다. 제공자 연결 끊기로 HTTP 호출이 늘기 전에 공용 `httpx.AsyncClient`를 필요할 때 만들고 종료 때 닫게 한다. 카카오 어드민 키(Task 5에서 쓴다)도 여기서 자리를 잡는다.

**기존 개발 환경은 손댈 필요가 없다.** `.env`에 남은 `IDENTITY_TOKEN_ENC_KEY`는 compose가 auth 서비스에 `.env`와 `.env.auth`를 둘 다 넣어 주므로 그대로 읽힌다. 새로 만드는 개발 환경부터 `.env.auth`에 들어간다.

**Files:**
- Modify: `backend/core/auth_config.py`, `backend/core/config.py`
- Modify: `backend/apps/auth/adapter/outbound/gateways/fernet_cipher.py`
- Modify: `backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`
- Modify: `backend/apps/auth/dependencies/auth_wiring.py`, `backend/apps/auth/dependencies/social_login_provider.py`
- Modify: `backend/auth_main.py`
- Modify: `backend/scripts/generate_dev_env.py`, `.env.example`
- Modify: `backend/tests/test_config_defaults.py`, `backend/tests/integration/conftest.py`
- Test: `backend/tests/test_config_boundary.py` (새로), `backend/apps/auth/tests/adapter/test_fernet_cipher.py` (새로), `backend/apps/auth/tests/adapter/test_user_pg_repository.py` (추가)

**Interfaces:**
- Consumes: `core.singleton.secret_manager.get_secret_manager()`
- Produces:
  - `core.auth_config`: `JWT_PRIVATE_KEY: str`, `IDENTITY_TOKEN_ENC_KEY: str`(필수), `KAKAO_ADMIN_KEY: str`(없으면 빈 문자열)
  - `core.config`에는 `IDENTITY_TOKEN_ENC_KEY`가 없다.
  - `FernetCipher.decrypt(encrypted: str) -> str`
  - `UserPgRepository(session, cipher: FernetCipher | None = None)` — 암호화 도구 없이 조립하면 제공자 토큰을 저장·복호화할 때 `RuntimeError`
  - `auth.dependencies.auth_wiring`: `build_user_repository(db)`(암호화 도구 없음 — 읽기 경로), `build_user_repository_with_cipher(db)`(인증 프로세스 전용), `get_http() -> httpx.AsyncClient`, `async dispose_http() -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_config_boundary.py`:
```python
"""인증 프로세스 전용 비밀값이 API 프로세스로 새지 않는지 확인한다."""
import subprocess
import sys
from pathlib import Path

import core.config

_BACKEND = Path(__file__).resolve().parents[1]


def test_공용_설정에는_제공자_토큰_암호화_키가_없다():
    assert not hasattr(core.config, "IDENTITY_TOKEN_ENC_KEY")


def test_API_프로세스는_인증_전용_설정을_불러오지_않는다():
    """B1 — 다른 테스트가 먼저 불러왔을 수 있으므로 새 프로세스에서 확인한다."""
    code = "import sys, main; sys.exit(1 if 'core.auth_config' in sys.modules else 0)"
    result = subprocess.run([sys.executable, "-c", code], cwd=_BACKEND)
    assert result.returncode == 0
```

`backend/apps/auth/tests/adapter/test_fernet_cipher.py`:
```python
from cryptography.fernet import Fernet

from auth.adapter.outbound.gateways.fernet_cipher import FernetCipher


def test_암호화한_값을_같은_키로_되돌린다():
    cipher = FernetCipher(Fernet.generate_key().decode())
    encrypted = cipher.encrypt("apple-refresh-token")
    assert encrypted != "apple-refresh-token"
    assert cipher.decrypt(encrypted) == "apple-refresh-token"
```

`backend/apps/auth/tests/adapter/test_user_pg_repository.py`의 끝에 더한다.
```python


async def test_암호화_도구_없이_조립하면_제공자_토큰을_저장하지_못한다(db_session):
    repo = UserPgRepository(db_session)
    with pytest.raises(RuntimeError, match="암호화"):
        await repo.create_with_identity(
            _profile(provider=Provider.APPLE, provider_user_id="apple-2", provider_refresh_token="plain")
        )


async def test_암호화_도구_없이도_토큰_없는_프로필은_저장하고_읽는다(db_session):
    repo = UserPgRepository(db_session)
    created = await repo.create_with_identity(_profile(provider_user_id="kakao-200"))
    assert (await repo.get(created.id)).display_name == "두부 보호자"
    assert await repo.get(999999) is None
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest tests/test_config_boundary.py apps/auth/tests/adapter/test_fernet_cipher.py apps/auth/tests/adapter/test_user_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `assert not hasattr(...)`, `AttributeError: 'FernetCipher' object has no attribute 'decrypt'`, `TypeError: UserPgRepository.__init__() missing 1 required positional argument: 'cipher'`

- [ ] **Step 3: 설정을 옮긴다**

`backend/core/auth_config.py` 전체:
```python
"""인증 프로세스 전용 비밀값. auth_main.py 경로에서만, 그리고 함수 안에서만 import 한다.

API 프로세스는 토큰을 발급할 수도, 제공자 토큰을 복호화할 수도, 카카오 연결을 끊을 수도 없어야 한다.
"""
from __future__ import annotations

import base64

from core.singleton.secret_manager import get_secret_manager

_m = get_secret_manager()

JWT_PRIVATE_KEY: str = base64.b64decode(_m.require("JWT_PRIVATE_KEY_B64")).decode()
# Apple 리프레시 토큰을 DB 에 넣기 전에 암호화하는 키 (Fernet).
IDENTITY_TOKEN_ENC_KEY: str = _m.require("IDENTITY_TOKEN_ENC_KEY")
# 탈퇴·해제 때 카카오 연결을 끊는 데 쓴다. 없으면 끊지 못하고 로그만 남긴다.
KAKAO_ADMIN_KEY: str = _m.get("KAKAO_ADMIN_KEY", "") or ""
```

`backend/core/config.py`에서 마지막 줄을 지운다.
```python
IDENTITY_TOKEN_ENC_KEY: str = _m.require("IDENTITY_TOKEN_ENC_KEY")
```

`backend/tests/test_config_defaults.py`의 `_require_values`에서 `"IDENTITY_TOKEN_ENC_KEY": …` 줄을 지운다.

- [ ] **Step 4: 암호화 도구와 리포지토리를 고친다**

`backend/apps/auth/adapter/outbound/gateways/fernet_cipher.py`에 메서드를 더한다.
```python
    def decrypt(self, encrypted: str) -> str:
        return self._fernet.decrypt(encrypted.encode()).decode()
```

`backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`에서 생성자를 바꾸고 도우미를 더한다.
```python
    def __init__(self, session: AsyncSession, cipher: FernetCipher | None = None) -> None:
        """cipher 는 인증 프로세스만 넘긴다. 읽기만 하는 경로(API 프로세스)는 없이 조립한다."""
        self._session = session
        self._cipher = cipher

    def _require_cipher(self) -> FernetCipher:
        if self._cipher is None:
            raise RuntimeError("암호화 도구 없이 조립된 리포지토리는 제공자 토큰을 다룰 수 없습니다.")
        return self._cipher
```
`create_with_identity`의 암호화 줄을 바꾼다.
```python
                provider_refresh_token_enc=self._require_cipher().encrypt(token) if token else None,
```

- [ ] **Step 5: 조립 함수를 고친다**

`backend/apps/auth/dependencies/auth_wiring.py`에서 네 곳을 고친다.

(1) 모듈 머리말을 바꾼다.
```python
"""auth 슬라이스 프로바이더들이 함께 쓰는 조립 함수.

인증 프로세스 전용 비밀값이 필요한 조립은 core.auth_config 를 함수 안에서 import 한다.
모듈 최상단에서 import 하면 그 값이 없는 API 프로세스에서 이 모듈을 불러올 때 실패한다.
"""
```
(2) `_http = httpx.AsyncClient(timeout=5.0)` 줄을 바꾸고 함수 둘을 더한다.
```python
_http: httpx.AsyncClient | None = None


def get_http() -> httpx.AsyncClient:
    """제공자를 부르는 공용 클라이언트. 처음 쓸 때 만들고 프로세스가 끝날 때 닫는다."""
    global _http
    if _http is None:
        _http = httpx.AsyncClient(timeout=5.0)
    return _http


async def dispose_http() -> None:
    global _http
    if _http is not None:
        await _http.aclose()
    _http = None
```
(3) `build_user_repository`를 바꾸고 하나를 더한다.
```python
def build_user_repository(db: AsyncSession) -> UserRepository:
    """읽기만 하는 경로용. 제공자 토큰을 저장하거나 복호화할 수 없다."""
    return UserPgRepository(db)


def build_user_repository_with_cipher(db: AsyncSession) -> UserRepository:
    """인증 프로세스 전용. 로그인·연결·해제·탈퇴가 쓴다."""
    from core.auth_config import IDENTITY_TOKEN_ENC_KEY

    return UserPgRepository(db, FernetCipher(IDENTITY_TOKEN_ENC_KEY))
```
(4) `build_provider_resolver` 안의 `http=_http,`를 `http=get_http(),`로 바꾼다.

`backend/apps/auth/dependencies/social_login_provider.py`에서 `build_user_repository`를 `build_user_repository_with_cipher`로 바꾼다(import와 호출 둘 다).

`backend/auth_main.py`에서 import 한 줄을 더하고 lifespan의 `finally`를 고친다.
```python
from auth.dependencies.auth_wiring import dispose_http
```
```python
    finally:
        await dispose_http()
        await dispose_engine()
        await dispose_redis()
```

- [ ] **Step 6: 개발 환경 생성기와 예시 파일을 고친다**

`backend/scripts/generate_dev_env.py`에서 `env.write_text(…)` 안의 `f"IDENTITY_TOKEN_ENC_KEY={Fernet.generate_key().decode()}\n"` 줄을 지우고, `auth_env.write_text(…)`를 바꾼다.
```python
    auth_env.write_text(
        f"JWT_PRIVATE_KEY_B64={base64.b64encode(private_pem).decode()}\n"
        f"IDENTITY_TOKEN_ENC_KEY={Fernet.generate_key().decode()}\n",
        encoding="utf-8",
    )
```

`.env.example`에서 아래 세 줄을
```dotenv
# 아래 하나는 .env.auth 에만 둔다 (인증 프로세스 전용)
JWT_PRIVATE_KEY_B64=
IDENTITY_TOKEN_ENC_KEY=
```
다음으로 바꾸고, 소셜 로그인 묶음에서 `KAKAO_ADMIN_KEY=` 줄을 지운다.
```dotenv
# 아래 셋은 .env.auth 에만 둔다 (인증 프로세스 전용)
JWT_PRIVATE_KEY_B64=
IDENTITY_TOKEN_ENC_KEY=
KAKAO_ADMIN_KEY=
```

- [ ] **Step 7: 통합 테스트 픽스처에 키를 넣는다**

`backend/tests/integration/conftest.py`의 `wired` 픽스처에서 개인키를 넣는 `monkeypatch.setenv(…)` 다음 줄에 더한다 (import 묶음에 `from cryptography.fernet import Fernet`도 더한다).
```python
    enc_key = Fernet.generate_key().decode()
    monkeypatch.setenv("IDENTITY_TOKEN_ENC_KEY", enc_key)
```
그리고 `monkeypatch.setattr(core.auth_config, "JWT_PRIVATE_KEY", private_pem)` 다음 줄에 더한다.
```python
    monkeypatch.setattr(core.auth_config, "IDENTITY_TOKEN_ENC_KEY", enc_key)
    monkeypatch.setattr(core.auth_config, "KAKAO_ADMIN_KEY", "")
```

- [ ] **Step 8: 통과를 확인한다**

Run: Step 2의 명령 → 전부 통과.
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.
Run: `bash ../backend/scripts/check_auth_flow.sh` → `전체 흐름 확인 완료` (auth 서비스가 새 설정으로 기동했는지 확인한다. 502가 나오면 `docker compose logs --tail 30 auth`를 본다).

- [ ] **Step 9: 커밋**

```bash
git add backend/core backend/apps/auth backend/auth_main.py backend/scripts/generate_dev_env.py backend/tests .env.example
git commit -m "refactor(core): 제공자 토큰 암호화 키와 카카오 어드민 키를 인증 프로세스 전용 설정으로 옮긴다"
```

---

### Task 3: 로그인 보강 — 동시 가입과 Apple 리프레시 토큰 보완

넘김 항목 7·9다.
- 같은 소셜 계정의 첫 로그인이 동시에 두 번 오면 둘 다 "없는 신원"으로 보고 유저를 만들려다, 진 쪽이 유일 제약 위반으로 500이 난다. 진 쪽은 이긴 쪽이 만든 유저로 로그인해야 한다.
- Apple 리프레시 토큰은 가입 때만 저장한다. 첫 로그인에 인가 코드가 없었던 유저는 탈퇴 때 Apple 연결을 끊을 수 없다. 저장된 값이 비어 있으면 로그인 때 채운다(이미 있으면 덮어쓰지 않는다 — 덮어쓰면 옛 토큰이 Apple 쪽에 폐기되지 않은 채 남는다).

넘김 항목 8(`is_deleted` 로그인 차단)은 코드를 넣지 않는다. 탈퇴(Task 11)가 익명화와 신원 삭제를 한 트랜잭션으로 하므로 "탈퇴한 유저에 신원이 남은" 상태가 생기지 않는다.

**Files:**
- Modify: `backend/apps/auth/domain/errors.py`, `backend/apps/auth/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/auth/app/ports/output/user_repository.py`
- Modify: `backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`
- Modify: `backend/apps/auth/app/use_cases/social_login_interactor.py`
- Test: `backend/apps/auth/tests/app/use_cases/test_social_login_interactor.py` (수정·추가), `backend/apps/auth/tests/adapter/test_user_pg_repository.py` (추가)

**Interfaces:**
- Consumes: Task 2의 `UserPgRepository(session, cipher=None)`·`_require_cipher`
- Produces:
  - `auth.domain.errors.IdentityAlreadyLinkedError` (`code = "IDENTITY_ALREADY_LINKED"`, 409)
  - `UserRepository.create_with_identity(profile) -> User` — 그 신원이 이미 있으면 `IdentityAlreadyLinkedError`
  - `UserRepository.fill_provider_refresh_token(provider: Provider, provider_user_id: str, token: str) -> None` — 저장된 값이 비어 있을 때만 채운다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_user_pg_repository.py`의 끝에 더한다 (import 묶음에 `from auth.domain.errors import IdentityAlreadyLinkedError`도 더한다).
```python


async def test_이미_있는_신원으로_만들면_IdentityAlreadyLinkedError_이고_세션은_계속_쓸_수_있다(db_session):
    repo = _repo(db_session)
    first = await repo.create_with_identity(_profile())
    with pytest.raises(IdentityAlreadyLinkedError):
        await repo.create_with_identity(_profile(display_name="늦은 요청"))
    # 진 쪽이 만들려던 유저 행도 함께 되돌아간다.
    count = (await db_session.execute(text("SELECT count(*) FROM users"))).scalar_one()
    assert count == 1
    assert (await repo.find_by_identity(Provider.KAKAO, "kakao-100")).id == first.id


async def test_비어_있는_제공자_토큰만_채운다(db_session):
    repo = _repo(db_session)
    await repo.create_with_identity(_profile(provider=Provider.APPLE, provider_user_id="apple-9"))

    async def stored():
        return (
            await db_session.execute(
                text("SELECT provider_refresh_token_enc FROM social_identities WHERE provider_user_id = 'apple-9'")
            )
        ).scalar_one()

    assert await stored() is None
    await repo.fill_provider_refresh_token(Provider.APPLE, "apple-9", "first-token")
    filled = await stored()
    assert filled and filled != "first-token"
    await repo.fill_provider_refresh_token(Provider.APPLE, "apple-9", "second-token")
    assert await stored() == filled
```

`backend/apps/auth/tests/app/use_cases/test_social_login_interactor.py`에서 스텁을 고치고 테스트를 더한다.

(1) import 묶음에 더한다.
```python
from auth.domain.errors import IdentityAlreadyLinkedError
```
(2) `_StubProvider`가 돌려주는 프로필을 바꿀 수 있게 한다.
```python
class _StubProvider:
    def __init__(self, refresh_token=None):
        self.refresh_token = refresh_token
        self.seen = []

    async def verify(self, credentials):
        self.seen.append(credentials)
        return SocialProfile(Provider.KAKAO, "kakao-100", None, "두부 보호자", None, self.refresh_token)
```
(3) `_StubUsers` 전체를 바꾼다.
```python
class _StubUsers:
    def __init__(self, existing=None, lost_race_to=None):
        self.existing = existing
        self.lost_race_to = lost_race_to   # 동시에 온 다른 요청이 먼저 만든 유저
        self.created = []
        self.filled = []

    async def find_by_identity(self, provider, provider_user_id):
        return self.existing

    async def create_with_identity(self, profile):
        if self.lost_race_to is not None:
            self.existing = self.lost_race_to
            raise IdentityAlreadyLinkedError("이미 연결된 계정입니다.")
        self.created.append(profile)
        return _user(user_id=77)

    async def fill_provider_refresh_token(self, provider, provider_user_id, token):
        self.filled.append((provider, provider_user_id, token))
```
(4) 파일 끝에 더한다.
```python


async def test_동시에_온_첫_로그인에서_진_쪽은_먼저_만들어진_유저로_로그인한다():
    """C1"""
    users, sessions = _StubUsers(lost_race_to=_user(user_id=5)), _StubSessions()
    result = await SocialLoginInteractor(_StubResolver(_StubProvider()), users, sessions).login(_command())
    assert (result.user_id, result.is_new_user) == (5, False)
    assert sessions.issued_for == [5]


async def test_기존_유저가_제공자_토큰을_새로_받아_오면_비어_있는_자리를_채운다():
    users = _StubUsers(existing=_user(user_id=5))
    provider = _StubProvider(refresh_token="apple-refresh")
    await SocialLoginInteractor(_StubResolver(provider), users, _StubSessions()).login(_command())
    assert users.filled == [(Provider.KAKAO, "kakao-100", "apple-refresh")]


async def test_제공자_토큰이_없으면_채우지_않는다():
    users = _StubUsers(existing=_user(user_id=5))
    await SocialLoginInteractor(_StubResolver(_StubProvider()), users, _StubSessions()).login(_command())
    assert users.filled == []
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_social_login_interactor.py apps/auth/tests/adapter/test_user_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'IdentityAlreadyLinkedError'`

- [ ] **Step 3: 오류와 포트를 더한다**

`backend/apps/auth/domain/errors.py`의 끝에 더한다.
```python


class IdentityAlreadyLinkedError(AuthError):
    code = "IDENTITY_ALREADY_LINKED"
```

`backend/apps/auth/adapter/inbound/api/error_map.py`의 import와 표에 더한다.
```python
    IdentityAlreadyLinkedError: 409,
```

`backend/apps/auth/app/ports/output/user_repository.py`에서 `create_with_identity`에 docstring을 달고 메서드 하나를 더한다.
```python
    @abstractmethod
    async def create_with_identity(self, profile: SocialProfile) -> User:
        """그 신원이 이미 있으면 IdentityAlreadyLinkedError (동시에 온 다른 요청이 먼저 만들었다)."""

    @abstractmethod
    async def fill_provider_refresh_token(
        self, provider: Provider, provider_user_id: str, token: str
    ) -> None:
        """저장된 값이 비어 있을 때만 채운다. 이미 있으면 덮어쓰지 않는다."""
```

- [ ] **Step 4: 리포지토리를 고친다**

`backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`에서 import를 더하고 `create_with_identity`를 바꾸고 메서드를 더한다.
```python
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from auth.domain.errors import IdentityAlreadyLinkedError
```
```python
    async def create_with_identity(self, profile: SocialProfile) -> User:
        token = profile.provider_refresh_token
        encrypted = self._require_cipher().encrypt(token) if token else None
        user = UserOrm(
            display_name=(profile.display_name or "이름 없음")[:50],
            profile_image_url=profile.profile_image_url,
        )
        try:
            # 유저와 신원을 한 세이브포인트에 넣는다. 신원의 유일 제약에 걸리면 유저 행도 함께 되돌아간다.
            async with self._session.begin_nested():
                self._session.add(user)
                await self._session.flush()
                self._session.add(
                    SocialIdentityOrm(
                        user_id=user.id,
                        provider=profile.provider.value,
                        provider_user_id=profile.provider_user_id,
                        email=profile.email,
                        provider_refresh_token_enc=encrypted,
                    )
                )
                await self._session.flush()
        except IntegrityError as exc:
            if _constraint(exc) != "uq_social_identities_provider_user":
                raise
            raise IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다.") from exc
        return to_user(user)

    async def fill_provider_refresh_token(
        self, provider: Provider, provider_user_id: str, token: str
    ) -> None:
        await self._session.execute(
            update(SocialIdentityOrm)
            .where(
                SocialIdentityOrm.provider == provider.value,
                SocialIdentityOrm.provider_user_id == provider_user_id,
                SocialIdentityOrm.provider_refresh_token_enc.is_(None),
            )
            .values(provider_refresh_token_enc=self._require_cipher().encrypt(token))
        )
```
모듈 아래쪽(클래스 밖)에 도우미를 더한다.
```python
def _constraint(exc: IntegrityError) -> str | None:
    """asyncpg 는 제약 이름을 원인 예외에 담고, SQLAlchemy 는 그것을 __cause__ 로 감싼다."""
    return getattr(exc.orig.__cause__, "constraint_name", None)
```

- [ ] **Step 5: 로그인 유스케이스를 고친다**

`backend/apps/auth/app/use_cases/social_login_interactor.py`에서 import를 고치고 `login`의 유저 조회 부분을 바꾼다.
```python
from auth.domain.errors import (
    AccountSuspendedError,
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
)
```
```python
        user = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
        is_new_user = user is None
        if user is None:
            try:
                user = await self._users.create_with_identity(profile)
            except IdentityAlreadyLinkedError:
                # 같은 신원의 첫 로그인이 동시에 두 번 왔다. 먼저 끝난 쪽이 만든 유저로 로그인한다.
                user = await self._users.find_by_identity(profile.provider, profile.provider_user_id)
                is_new_user = False
        elif profile.provider_refresh_token:
            # 가입 때 받지 못한 제공자 토큰(Apple)을 채운다. 탈퇴 때 제공자 쪽 연결을 끊는 데 쓴다.
            await self._users.fill_provider_refresh_token(
                profile.provider, profile.provider_user_id, profile.provider_refresh_token
            )
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 2의 명령 → 전부 통과.
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/auth
git commit -m "fix(auth): 동시에 온 첫 로그인을 같은 유저로 받고 비어 있는 Apple 토큰을 로그인 때 채운다"
```

---

### Task 4: 작은 보강 — 공개키 재조회, 누락된 식별자, 만료 없는 토큰, 예외 연결

넘김 항목 18·19·21·22다. 서로 독립된 작은 수정 네 가지다.
- **18** 제공자가 서명 키를 바꾸면 캐시가 만료될 때까지(최대 1시간) 로그인이 전부 실패한다. 모르는 `kid`면 캐시를 건너뛰고 한 번 다시 받는다. 단, 모르는 `kid`를 쏟아붓는 요청이 제공자를 계속 두드리지 못하게 강제 재조회는 60초에 한 번으로 묶는다(위협 D1). 공개키를 받지 못했을 때의 네트워크 오류는 500이 아니라 `PROVIDER_VERIFICATION_FAILED`다.
- **19** 제공자 응답에 식별자(카카오 `id`, 구글·Apple `sub`)가 없으면 `KeyError`가 500으로 나간다.
- **21** 자체 액세스 토큰 검증이 `exp` 없는 토큰을 받아들인다.
- **22** `raise … from` 누락 두 곳.

**Files:**
- Modify: `backend/apps/auth/adapter/outbound/strategy/jwks_verifier.py` (전체 교체)
- Modify: `backend/apps/auth/adapter/outbound/strategy/google_identity_strategy.py`, `apple_identity_strategy.py`, `kakao_identity_strategy.py`
- Modify: `backend/apps/auth/adapter/outbound/factory/social_provider_factory.py`
- Modify: `backend/apps/auth/app/use_cases/social_login_interactor.py`
- Modify: `backend/core/security.py`
- Test: `backend/apps/auth/tests/adapter/test_jwks_verifier.py` (새로), `test_google_identity_strategy.py`·`test_kakao_identity_strategy.py`(추가), `backend/tests/test_security.py`(추가)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `jwks_verifier.verify_with_jwks(token, fetch_jwks, issuers, audiences, refetch_jwks: JwksFetcher | None = None) -> dict`
  - `jwks_verifier.http_jwks_fetchers(http, url, ttl_seconds=3600, min_refetch_seconds=60, now=time.monotonic) -> tuple[JwksFetcher, JwksFetcher]` — (캐시를 쓰는 조회, 강제 재조회). 기존 `http_jwks_fetcher`는 없앤다.
  - `GoogleIdentityStrategy(client_ids, fetch_jwks, refetch_jwks=None)`, `AppleIdentityStrategy(..., fetch_jwks, now=time.time, refetch_jwks=None)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_jwks_verifier.py`:
```python
import time

import httpx
import pytest
from jose import jwt

from auth.adapter.outbound.strategy.jwks_verifier import http_jwks_fetchers, verify_with_jwks
from auth.domain.errors import ProviderVerificationError
from auth.tests.helpers.keys import make_rsa_keypair

OLD_PEM, _, OLD_JWK = make_rsa_keypair(kid="old-kid")
NEW_PEM, _, NEW_JWK = make_rsa_keypair(kid="new-kid")


def _token(pem, kid):
    claims = {"iss": "issuer", "aud": "app", "sub": "user-1", "exp": int(time.time()) + 600}
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


def _fetchers(keysets, clock, status=200):
    """keysets 를 호출 순서대로 하나씩 돌려주는 가짜 제공자. 호출 횟수를 센다."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(status, json={"keys": keysets[min(len(calls) - 1, len(keysets) - 1)]})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    fetch, refetch = http_jwks_fetchers(http, "https://provider.test/keys", now=lambda: clock["t"])
    return fetch, refetch, calls


async def test_캐시에_없는_kid_면_한_번_다시_받아_검증한다():
    clock = {"t": 1000.0}
    fetch, refetch, calls = _fetchers([[OLD_JWK], [OLD_JWK, NEW_JWK]], clock)
    await verify_with_jwks(_token(OLD_PEM, "old-kid"), fetch, ("issuer",), ("app",), refetch)
    clock["t"] += 120   # 제공자가 키를 바꿨다
    claims = await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)
    assert claims["sub"] == "user-1"
    assert len(calls) == 2


async def test_다시_받아도_없는_kid_면_거절한다():
    clock = {"t": 1000.0}
    fetch, refetch, _ = _fetchers([[OLD_JWK]], clock)
    clock["t"] += 120
    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)


async def test_강제_재조회는_간격_안에서는_한_번만_한다():
    """D1 — 모르는 kid 를 쏟아부어도 제공자를 60초에 한 번만 두드린다."""
    clock = {"t": 1000.0}
    fetch, refetch, calls = _fetchers([[OLD_JWK]], clock)
    for _ in range(5):
        with pytest.raises(ProviderVerificationError):
            await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)
    assert len(calls) == 1   # 첫 조회가 곧 최신 값이라, 60초 안의 강제 재조회는 캐시를 돌려준다
    clock["t"] += 61
    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",), refetch)
    assert len(calls) == 2


async def test_공개키를_받지_못하면_검증_실패로_돌려준다():
    fetch, refetch, _ = _fetchers([[OLD_JWK]], {"t": 1000.0}, status=503)
    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(OLD_PEM, "old-kid"), fetch, ("issuer",), ("app",), refetch)


async def test_재조회_함수가_없으면_캐시만_본다():
    async def fetch():
        return {"keys": [OLD_JWK]}

    with pytest.raises(ProviderVerificationError):
        await verify_with_jwks(_token(NEW_PEM, "new-kid"), fetch, ("issuer",), ("app",))
```

`backend/apps/auth/tests/adapter/test_google_identity_strategy.py`의 끝에 더한다.
```python


async def test_sub_가_없는_토큰은_거절한다():
    claims = {"iss": "https://accounts.google.com", "aud": "ios-client-id", "exp": int(time.time()) + 600}
    token = jwt.encode(claims, PRIVATE_PEM, algorithm="RS256", headers={"kid": "google-kid"})
    with pytest.raises(ProviderVerificationError):
        await _strategy().verify(SocialCredentials(token=token))
```

`backend/apps/auth/tests/adapter/test_kakao_identity_strategy.py`의 끝에 더한다.
```python


async def test_사용자_ID_가_없는_응답은_거절한다():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/user/access_token_info":
            return httpx.Response(200, json={"app_id": 1234})
        return httpx.Response(200, json={"kakao_account": {}})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderVerificationError):
        await KakaoIdentityStrategy("1234", http).verify(SocialCredentials(token="kakao-token"))
```

`backend/tests/test_security.py`의 끝에 더한다 (import 묶음에 `from jose import jwt`도 더한다).
```python


def test_만료_시각이_없는_토큰은_받지_않는다():
    private_pem, public_pem, _ = make_rsa_keypair()
    token = jwt.encode({"sub": "1", "typ": "access"}, private_pem, algorithm="RS256")
    with pytest.raises(security.InvalidAccessToken):
        security.decode_access_token(token, public_pem)
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/adapter/test_jwks_verifier.py apps/auth/tests/adapter/test_google_identity_strategy.py apps/auth/tests/adapter/test_kakao_identity_strategy.py tests/test_security.py -q -p no:cacheprovider`
Expected: FAIL — `ImportError: cannot import name 'http_jwks_fetchers'`, `KeyError: 'sub'`, `KeyError: 'id'`, 만료 없는 토큰 테스트는 `DID NOT RAISE`

- [ ] **Step 3: 공개키 검증을 고친다**

`backend/apps/auth/adapter/outbound/strategy/jwks_verifier.py` 전체:
```python
"""구글·Apple 전략이 함께 쓰는 ID 토큰 서명 검증."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

import httpx
from jose import JWTError, jwt

from auth.domain.errors import ProviderVerificationError

JwksFetcher = Callable[[], Awaitable[dict]]


def _find_key(jwks: dict, kid: str) -> dict | None:
    return next((k for k in jwks["keys"] if k.get("kid") == kid), None)


async def verify_with_jwks(
    token: str, fetch_jwks: JwksFetcher, issuers: tuple[str, ...], audiences: tuple[str, ...],
    refetch_jwks: JwksFetcher | None = None,
) -> dict:
    try:
        kid = jwt.get_unverified_header(token)["kid"]
        key = _find_key(await fetch_jwks(), kid)
        if key is None and refetch_jwks is not None:
            # 제공자가 서명 키를 바꿨을 수 있다. 캐시를 건너뛰고 한 번만 다시 받아 본다.
            key = _find_key(await refetch_jwks(), kid)
        if key is None:
            raise KeyError(kid)
        # 대상 앱(aud)은 여러 값 중 하나일 수 있어서 아래에서 직접 확인한다.
        claims = jwt.decode(
            token, key, algorithms=["RS256"],
            options={"verify_aud": False, "verify_at_hash": False},
        )
    except (JWTError, KeyError) as exc:
        raise ProviderVerificationError("ID 토큰의 서명을 확인할 수 없습니다.") from exc
    if claims.get("iss") not in issuers or claims.get("aud") not in audiences:
        raise ProviderVerificationError("발급자 또는 대상 앱이 일치하지 않습니다.")
    if not claims.get("sub"):
        raise ProviderVerificationError("ID 토큰에 사용자 식별자가 없습니다.")
    return claims


def http_jwks_fetchers(
    http: httpx.AsyncClient, url: str, ttl_seconds: int = 3600, min_refetch_seconds: int = 60,
    now: Callable[[], float] = time.monotonic,
) -> tuple[JwksFetcher, JwksFetcher]:
    """(캐시를 쓰는 조회, 강제 재조회)를 돌려준다. 둘은 같은 캐시를 본다.

    강제 재조회는 min_refetch_seconds 에 한 번만 제공자를 부른다. 모르는 kid 를 쏟아붓는 요청이
    제공자를 계속 두드리게 하지 않으려는 것이다.
    """
    cache: dict = {"at": 0.0, "value": None}

    async def _load() -> dict:
        try:
            response = await http.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderVerificationError("제공자의 공개키를 가져올 수 없습니다.") from exc
        cache["value"], cache["at"] = response.json(), now()
        return cache["value"]

    async def fetch() -> dict:
        if cache["value"] is None or now() - cache["at"] > ttl_seconds:
            return await _load()
        return cache["value"]

    async def refetch() -> dict:
        if cache["value"] is not None and now() - cache["at"] < min_refetch_seconds:
            return cache["value"]
        return await _load()

    return fetch, refetch
```

- [ ] **Step 4: 전략과 팩토리를 고친다**

`backend/apps/auth/adapter/outbound/strategy/google_identity_strategy.py`에서 생성자와 검증 호출을 바꾼다.
```python
    def __init__(
        self, client_ids: tuple[str, ...], fetch_jwks: JwksFetcher,
        refetch_jwks: JwksFetcher | None = None,
    ) -> None:
        self._client_ids = client_ids
        self._fetch_jwks = fetch_jwks
        self._refetch_jwks = refetch_jwks

    async def verify(self, credentials: SocialCredentials) -> SocialProfile:
        claims = await verify_with_jwks(
            credentials.token, self._fetch_jwks, _ISSUERS, self._client_ids, self._refetch_jwks
        )
```

`backend/apps/auth/adapter/outbound/strategy/apple_identity_strategy.py`에서 생성자에 마지막 인자를 더하고(`now` 다음), 검증 호출을 바꾼다.
```python
        now: Callable[[], float] = time.time,
        refetch_jwks: JwksFetcher | None = None,
    ) -> None:
```
```python
        self._refetch_jwks = refetch_jwks
```
```python
        claims = await verify_with_jwks(
            credentials.token, self._fetch_jwks, (_ISSUER,), (self._bundle_id,), self._refetch_jwks
        )
```

`backend/apps/auth/adapter/outbound/strategy/kakao_identity_strategy.py`의 `verify`에서 `body = me.json()` 다음 줄에 더한다.
```python
        if "id" not in body:
            raise ProviderVerificationError("카카오 응답에 사용자 식별자가 없습니다.")
```

`backend/apps/auth/adapter/outbound/factory/social_provider_factory.py`에서 세 곳을 고친다.

(1) import를 바꾼다: `http_jwks_fetcher` → `http_jwks_fetchers`.
(2) `resolve`의 예외를 잇는다.
```python
        except KeyError as exc:
            raise UnsupportedProviderError(
                f"{provider.value} 로그인은 지금 사용할 수 없습니다."
            ) from exc
```
(3) 구글·Apple 등록 부분을 바꾼다.
```python
    if google_client_ids:
        fetch, refetch = http_jwks_fetchers(http, GOOGLE_JWKS_URL)
        strategies[Provider.GOOGLE] = GoogleIdentityStrategy(google_client_ids, fetch, refetch)
    if apple is not None:
        fetch, refetch = http_jwks_fetchers(http, APPLE_JWKS_URL)
        strategies[Provider.APPLE] = AppleIdentityStrategy(
            apple.bundle_id, apple.team_id, apple.key_id, apple.private_key_pem,
            http, fetch, refetch_jwks=refetch,
        )
```

`backend/apps/auth/app/use_cases/social_login_interactor.py`의 제공자 이름 변환을 바꾼다.
```python
        except ValueError as exc:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.") from exc
```

- [ ] **Step 5: 액세스 토큰 검증을 고친다**

`backend/core/security.py`의 `decode_access_token`에서 `jwt.decode` 호출을 바꾼다.
```python
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"], options={"require_exp": True}
        )
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 2의 명령 → 전부 통과.
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/auth backend/core/security.py backend/tests/test_security.py
git commit -m "fix(auth): 공개키 재조회, 식별자 없는 응답, 만료 없는 토큰, 예외 연결을 바로잡는다"
```

---

### Task 5: 제공자 쪽 연결 끊기 (`SocialProviderPort.revoke`)

탈퇴와 로그인 수단 해제가 쓴다. 제공자마다 방법이 다르다.
- **카카오:** 어드민 키로 `POST https://kapi.kakao.com/v1/user/unlink` (`target_id_type=user_id`). 어드민 키가 없으면 끊지 못한다.
- **Apple:** 저장해 둔 리프레시 토큰으로 `POST https://appleid.apple.com/auth/revoke`. App Store 심사 가이드라인 5.1.1(v)의 필수 요구다. 저장된 토큰이 없으면 끊지 못한다.
- **구글:** 서버가 하지 않는다. 서버에는 폐기할 구글 토큰이 없고, 앱이 `disconnect()`를 부른다(사용자 결정).
- **dev:** 할 일이 없다.

끊지 못하면 `ProviderRevokeError`를 던진다. 부르는 쪽은 `ProviderRevoker`를 거치며, 이 서비스는 실패를 로그로만 남기고 다음 신원으로 넘어간다(설계 5.7절 "연결 끊기가 실패해도 탈퇴는 완료한다"). 로그에 토큰을 남기지 않는다.

**Files:**
- Create: `backend/apps/auth/domain/value_objects/identity_revocation.py`
- Create: `backend/apps/auth/app/services/provider_revoker.py`
- Modify: `backend/apps/auth/domain/errors.py`
- Modify: `backend/apps/auth/app/ports/output/social_provider_port.py`
- Modify: `backend/apps/auth/adapter/outbound/strategy/kakao_identity_strategy.py`, `apple_identity_strategy.py`, `google_identity_strategy.py`, `dev_identity_strategy.py`
- Modify: `backend/apps/auth/adapter/outbound/factory/social_provider_factory.py`
- Modify: `backend/apps/auth/dependencies/auth_wiring.py`
- Test: `backend/apps/auth/tests/adapter/test_provider_revoke.py` (새로), `backend/apps/auth/tests/app/test_provider_revoker.py` (새로)

**Interfaces:**
- Consumes: Task 2의 `core.auth_config.KAKAO_ADMIN_KEY`·`get_http()`
- Produces:
  - `auth.domain.value_objects.identity_revocation.IdentityRevocation(provider: Provider, provider_user_id: str, provider_refresh_token: str | None)`
  - `auth.domain.errors.ProviderRevokeError` (`code = "PROVIDER_REVOKE_FAILED"` — HTTP로 나가지 않는다)
  - `SocialProviderPort.revoke(identity: IdentityRevocation) -> None`
  - `KakaoIdentityStrategy(app_id, http, admin_key="")`
  - `build_social_provider_factory(..., kakao_admin_key: str = "")`
  - `auth.app.services.provider_revoker.ProviderRevoker(providers: SocialProviderResolverPort)` — `async revoke_all(identities: Sequence[IdentityRevocation]) -> None`
  - `auth.dependencies.auth_wiring.build_provider_revoker() -> ProviderRevoker`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_provider_revoke.py`:
```python
import httpx
import pytest

from auth.adapter.outbound.strategy.apple_identity_strategy import AppleIdentityStrategy
from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy
from auth.adapter.outbound.strategy.google_identity_strategy import GoogleIdentityStrategy
from auth.adapter.outbound.strategy.kakao_identity_strategy import KakaoIdentityStrategy
from auth.domain.errors import ProviderRevokeError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from auth.tests.helpers.keys import make_ec_private_pem


def _recording_http(status=200):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((str(request.url), dict(request.headers), dict(httpx.QueryParams(request.content.decode()))))
        return httpx.Response(status, json={})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), seen


def _kakao(identity_id="99"):
    return IdentityRevocation(Provider.KAKAO, identity_id, None)


def _apple(token="apple-refresh"):
    return IdentityRevocation(Provider.APPLE, "apple-1", token)


async def _no_jwks():
    return {"keys": []}


def _apple_strategy(http):
    return AppleIdentityStrategy(
        bundle_id="com.chagocnote.app", team_id="TEAM123456", key_id="KEY1234567",
        private_key_pem=make_ec_private_pem(), http=http, fetch_jwks=_no_jwks,
    )


async def test_카카오는_어드민_키로_그_사용자의_연결을_끊는다():
    http, seen = _recording_http()
    await KakaoIdentityStrategy("1234", http, admin_key="admin-key").revoke(_kakao())
    url, headers, form = seen[0]
    assert url == "https://kapi.kakao.com/v1/user/unlink"
    assert headers["authorization"] == "KakaoAK admin-key"
    assert form == {"target_id_type": "user_id", "target_id": "99"}


async def test_카카오_어드민_키가_없으면_끊지_못한다():
    http, seen = _recording_http()
    with pytest.raises(ProviderRevokeError):
        await KakaoIdentityStrategy("1234", http).revoke(_kakao())
    assert seen == []


async def test_카카오가_거절하면_ProviderRevokeError_다():
    http, _ = _recording_http(status=401)
    with pytest.raises(ProviderRevokeError):
        await KakaoIdentityStrategy("1234", http, admin_key="admin-key").revoke(_kakao())


async def test_Apple_은_저장해_둔_리프레시_토큰을_폐기한다():
    http, seen = _recording_http()
    await _apple_strategy(http).revoke(_apple())
    url, _, form = seen[0]
    assert url == "https://appleid.apple.com/auth/revoke"
    assert form["client_id"] == "com.chagocnote.app"
    assert (form["token"], form["token_type_hint"]) == ("apple-refresh", "refresh_token")
    assert form["client_secret"]


async def test_Apple_토큰이_없으면_끊지_못한다():
    http, seen = _recording_http()
    with pytest.raises(ProviderRevokeError):
        await _apple_strategy(http).revoke(_apple(token=None))
    assert seen == []


async def test_Apple_이_거절하면_ProviderRevokeError_다():
    http, _ = _recording_http(status=400)
    with pytest.raises(ProviderRevokeError):
        await _apple_strategy(http).revoke(_apple())


async def test_네트워크_오류도_ProviderRevokeError_다():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("연결 실패")

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(ProviderRevokeError):
        await KakaoIdentityStrategy("1234", http, admin_key="admin-key").revoke(_kakao())


async def test_구글과_dev_는_서버에서_할_일이_없다():
    await GoogleIdentityStrategy(("client",), _no_jwks).revoke(
        IdentityRevocation(Provider.GOOGLE, "google-7", None)
    )
    await DevIdentityStrategy().revoke(IdentityRevocation(Provider.DEV, "someone", None))
```

`backend/apps/auth/tests/app/test_provider_revoker.py`:
```python
import logging

from auth.app.services.provider_revoker import ProviderRevoker
from auth.domain.errors import ProviderRevokeError, UnsupportedProviderError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider


class _StubProvider:
    def __init__(self, fail=False):
        self.fail = fail
        self.revoked = []

    async def revoke(self, identity):
        if self.fail:
            raise ProviderRevokeError("카카오가 거절했습니다.")
        self.revoked.append(identity.provider_user_id)


class _StubResolver:
    def __init__(self, providers):
        self.providers = providers

    def resolve(self, provider):
        if provider not in self.providers:
            raise UnsupportedProviderError(f"{provider.value} 로그인은 지금 사용할 수 없습니다.")
        return self.providers[provider]


async def test_신원마다_그_제공자에게_연결을_끊으라고_한다():
    kakao, apple = _StubProvider(), _StubProvider()
    revoker = ProviderRevoker(_StubResolver({Provider.KAKAO: kakao, Provider.APPLE: apple}))
    await revoker.revoke_all([
        IdentityRevocation(Provider.KAKAO, "kakao-1", None),
        IdentityRevocation(Provider.APPLE, "apple-1", "secret-refresh-token"),
    ])
    assert (kakao.revoked, apple.revoked) == (["kakao-1"], ["apple-1"])


async def test_한_제공자가_실패해도_나머지는_끊고_로그에_토큰을_남기지_않는다(caplog):
    apple = _StubProvider()
    revoker = ProviderRevoker(_StubResolver({Provider.KAKAO: _StubProvider(fail=True), Provider.APPLE: apple}))
    with caplog.at_level(logging.WARNING):
        await revoker.revoke_all([
            IdentityRevocation(Provider.KAKAO, "kakao-1", None),
            IdentityRevocation(Provider.GOOGLE, "google-1", None),   # 등록되지 않은 제공자
            IdentityRevocation(Provider.APPLE, "apple-1", "secret-refresh-token"),
        ])
    assert apple.revoked == ["apple-1"]
    assert "kakao" in caplog.text and "google" in caplog.text
    assert "secret-refresh-token" not in caplog.text
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/adapter/test_provider_revoke.py apps/auth/tests/app/test_provider_revoker.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.domain.value_objects.identity_revocation'`

- [ ] **Step 3: 도메인과 포트를 더한다**

`backend/apps/auth/domain/value_objects/identity_revocation.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.provider import Provider


@dataclass(frozen=True, repr=False)
class IdentityRevocation:
    """제공자 쪽 연결을 끊는 데 필요한 것. DB 에서 신원을 지우기 전에 읽어 두고, 커밋 뒤에 쓴다.

    provider_refresh_token 은 복호화된 원문이다. 로그에 찍히지 않게 repr 을 막아 둔다.
    """

    provider: Provider
    provider_user_id: str
    provider_refresh_token: str | None

    def __repr__(self) -> str:
        return f"IdentityRevocation(provider={self.provider.value}, provider_user_id={self.provider_user_id})"
```

`backend/apps/auth/domain/errors.py`의 끝에 더한다.
```python


class ProviderRevokeError(AuthError):
    """제공자 쪽 연결을 끊지 못했다. HTTP 응답으로 나가지 않는다 — 부르는 쪽이 로그로 남긴다."""

    code = "PROVIDER_REVOKE_FAILED"
```

`backend/apps/auth/app/ports/output/social_provider_port.py`에 import와 메서드를 더한다.
```python
from auth.domain.value_objects.identity_revocation import IdentityRevocation
```
```python
    @abstractmethod
    async def revoke(self, identity: IdentityRevocation) -> None:
        """제공자 쪽에서 우리 앱과의 연결을 끊는다. 끊지 못하면 ProviderRevokeError.

        서버가 할 일이 없는 제공자(구글, dev)는 아무것도 하지 않는다.
        """
```

- [ ] **Step 4: 전략을 고친다**

`backend/apps/auth/adapter/outbound/strategy/kakao_identity_strategy.py`에서 import와 상수를 더하고, 생성자를 바꾸고, `revoke`를 더한다.
```python
from auth.domain.errors import ProviderRevokeError, ProviderVerificationError
from auth.domain.value_objects.identity_revocation import IdentityRevocation

_UNLINK_URL = "https://kapi.kakao.com/v1/user/unlink"
```
```python
    def __init__(self, app_id: str, http: httpx.AsyncClient, admin_key: str = "") -> None:
        self._app_id = app_id
        self._http = http
        self._admin_key = admin_key
```
```python
    async def revoke(self, identity: IdentityRevocation) -> None:
        """어드민 키로 그 사용자와 우리 앱의 연결을 끊는다. 사용자의 카카오 토큰이 필요 없다."""
        if not self._admin_key:
            raise ProviderRevokeError("카카오 어드민 키가 없어 연결을 끊을 수 없습니다.")
        try:
            response = await self._http.post(
                _UNLINK_URL,
                headers={"Authorization": f"KakaoAK {self._admin_key}"},
                data={"target_id_type": "user_id", "target_id": identity.provider_user_id},
            )
        except httpx.HTTPError as exc:
            raise ProviderRevokeError("카카오에 연결할 수 없습니다.") from exc
        if response.status_code != 200:
            raise ProviderRevokeError(f"카카오가 연결 끊기를 거절했습니다 (상태 {response.status_code}).")
```

`backend/apps/auth/adapter/outbound/strategy/apple_identity_strategy.py`에서 import와 상수를 더하고 `revoke`를 더한다.
```python
from auth.domain.errors import ProviderRevokeError, ProviderVerificationError
from auth.domain.value_objects.identity_revocation import IdentityRevocation

_REVOKE_URL = "https://appleid.apple.com/auth/revoke"
```
```python
    async def revoke(self, identity: IdentityRevocation) -> None:
        """저장해 둔 Apple 리프레시 토큰을 폐기한다 (App Store 심사 가이드라인 5.1.1(v))."""
        if not identity.provider_refresh_token:
            raise ProviderRevokeError("저장된 Apple 리프레시 토큰이 없어 연결을 끊을 수 없습니다.")
        try:
            response = await self._http.post(_REVOKE_URL, data={
                "client_id": self._bundle_id,
                "client_secret": self._client_secret(),
                "token": identity.provider_refresh_token,
                "token_type_hint": "refresh_token",
            })
        except httpx.HTTPError as exc:
            raise ProviderRevokeError("Apple 에 연결할 수 없습니다.") from exc
        if response.status_code != 200:
            raise ProviderRevokeError(f"Apple 이 토큰 폐기를 거절했습니다 (상태 {response.status_code}).")
```

`backend/apps/auth/adapter/outbound/strategy/google_identity_strategy.py`에 import와 메서드를 더한다.
```python
from auth.domain.value_objects.identity_revocation import IdentityRevocation
```
```python
    async def revoke(self, identity: IdentityRevocation) -> None:
        """서버는 아무것도 하지 않는다.

        서버는 구글 ID 토큰만 검증하고 구글 액세스·리프레시 토큰을 받지도 저장하지도 않아서 폐기할 것이 없다.
        구글이 모바일 앱에 안내하는 경로대로, 앱이 탈퇴·해제 성공 뒤에 google_sign_in 의 disconnect() 를 부른다.
        """
```

`backend/apps/auth/adapter/outbound/strategy/dev_identity_strategy.py`에 import와 메서드를 더한다.
```python
from auth.domain.value_objects.identity_revocation import IdentityRevocation
```
```python
    async def revoke(self, identity: IdentityRevocation) -> None:
        """개발용 제공자는 바깥에 끊을 연결이 없다."""
```

- [ ] **Step 5: 팩토리, 서비스, 조립을 고친다**

`backend/apps/auth/adapter/outbound/factory/social_provider_factory.py`에서 `build_social_provider_factory`의 시그니처와 카카오 등록을 바꾼다.
```python
def build_social_provider_factory(
    *, app_env: str, kakao_app_id: str, google_client_ids: tuple[str, ...],
    apple: AppleSettings | None, http: httpx.AsyncClient, kakao_admin_key: str = "",
) -> SocialProviderFactory:
```
```python
    if kakao_app_id:
        strategies[Provider.KAKAO] = KakaoIdentityStrategy(kakao_app_id, http, kakao_admin_key)
```

`backend/apps/auth/app/services/provider_revoker.py`:
```python
from __future__ import annotations

import logging
from collections.abc import Sequence

from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.domain.errors import ProviderRevokeError, UnsupportedProviderError
from auth.domain.value_objects.identity_revocation import IdentityRevocation

logger = logging.getLogger(__name__)


class ProviderRevoker:
    """탈퇴와 로그인 수단 해제가 함께 쓰는 제공자 쪽 연결 끊기.

    DB 커밋이 끝난 뒤(백그라운드 작업)에 부른다. 잠금을 쥔 채 외부 HTTP 를 부르지 않으려는 것이다.
    끊지 못해도 탈퇴·해제는 이미 끝났다. 실패는 로그로만 남긴다.
    """

    def __init__(self, providers: SocialProviderResolverPort) -> None:
        self._providers = providers

    async def revoke_all(self, identities: Sequence[IdentityRevocation]) -> None:
        for identity in identities:
            try:
                await self._providers.resolve(identity.provider).revoke(identity)
            except (ProviderRevokeError, UnsupportedProviderError) as exc:
                # 토큰은 남기지 않는다. 제공자와 이유만 남긴다.
                logger.warning(
                    "제공자 연결 끊기 실패 | provider=%s | %s", identity.provider.value, exc
                )
```

`backend/apps/auth/dependencies/auth_wiring.py`에서 두 곳을 고친다.

(1) import 묶음에 더한다.
```python
from auth.app.services.provider_revoker import ProviderRevoker
```
(2) `build_provider_resolver` 안에서 어드민 키를 읽어 넘기고, 파일 끝에 함수를 더한다.
```python
    if _resolver is None:
        from core.auth_config import KAKAO_ADMIN_KEY
```
```python
            http=get_http(),
            kakao_admin_key=KAKAO_ADMIN_KEY,
        )
```
```python


def build_provider_revoker() -> ProviderRevoker:
    return ProviderRevoker(build_provider_resolver())
```

- [ ] **Step 6: 통과를 확인한다**

Run: Step 2의 명령 → `10 passed`.
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/auth
git commit -m "feat(auth): 제공자 쪽 연결 끊기 — 카카오 unlink, Apple 토큰 폐기"
```

---

### Task 6: 잠금 시그니처와 초대 수락의 잠금 순서

계획 2-1 재검토에서 남긴 이론적 교착을 없앤다(위협 E1). 내보내기·강등은 매장 행 → 멤버 행 → 초대 행 순으로 잠그는데, 초대 수락은 매장 행 없이 초대 행 → 멤버 INSERT 순이다. 수락도 맨 앞에서 매장 행을 잠그게 한다. 수락은 아직 멤버가 아니라 `ShopContext`가 없으므로 `lock_membership_changes`의 인자를 `shop_id`로 바꾼다(잠금은 데이터를 읽는 것이 아니라 직렬화 수단이므로 컨텍스트 규칙의 대상이 아니다). Task 7의 탈퇴도 이 시그니처를 쓴다.

**Files:**
- Modify: `backend/apps/tenancy/app/ports/output/member_repository.py`, `backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`
- Modify: `backend/apps/tenancy/app/ports/output/invite_repository.py`, `backend/apps/tenancy/adapter/outbound/pg/invite_pg_repository.py`
- Modify: `backend/apps/tenancy/app/use_cases/change_member_role_interactor.py`, `remove_member_interactor.py`, `accept_invite_interactor.py`
- Modify: `backend/apps/tenancy/_docs/CLAUDE.md`
- Test: `backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`, `test_invite_pg_repository.py`, `backend/apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py`, `test_change_member_role_interactor.py`, `test_remove_member_interactor.py` (수정·추가)

**Interfaces:**
- Consumes: 계획 2-1의 tenancy 리포지토리와 인터랙터
- Produces:
  - `MemberRepository.lock_membership_changes(shop_id: int) -> None` (인자가 `ctx`에서 `shop_id`로 바뀐다)
  - `InviteRepository.find_shop_id_by_code_hash(code_hash: str) -> int | None` — 잠그지 않고 매장 ID만 읽는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py`에서 스텁 둘을 고치고 테스트를 더한다.

(1) `_StubInvites`에 호출 기록과 새 메서드를 더한다.
```python
class _StubInvites:
    def __init__(self, invite, calls=None):
        self.invite = invite
        self.calls = calls if calls is not None else []
        self.lookups = []
        self.used = []

    async def find_shop_id_by_code_hash(self, code_hash):
        self.calls.append("find_shop_id")
        self.lookups.append(code_hash)
        return self.invite.shop_id if self.invite else None

    async def find_by_code_hash_for_update(self, code_hash):
        self.calls.append("find_for_update")
        return self.invite

    async def mark_used(self, invite_id):
        self.used.append(invite_id)
```
(2) `_StubMembers`에 잠금을 더한다.
```python
class _StubMembers:
    def __init__(self, already_member=False, calls=None):
        self.already_member = already_member
        self.calls = calls if calls is not None else []
        self.locked = []
        self.added = []

    async def lock_membership_changes(self, shop_id):
        self.calls.append("lock")
        self.locked.append(shop_id)
```
(`add`는 그대로 둔다.)

(3) 파일 끝에 더한다.
```python


async def test_초대_행을_잠그기_전에_매장_행을_먼저_잠근다():
    """E1 — 내보내기·강등·탈퇴와 같은 순서(매장 → 멤버 → 초대)로 잠가야 교착하지 않는다."""
    calls = []
    invites, members = _StubInvites(_invite(), calls), _StubMembers(calls=calls)
    await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ABCD2345"))
    assert calls == ["find_shop_id", "lock", "find_for_update"]
    assert members.locked == [3]


async def test_모르는_코드면_아무것도_잠그지_않는다():
    calls = []
    invites, members = _StubInvites(None, calls), _StubMembers(calls=calls)
    with pytest.raises(InviteInvalidError):
        await _interactor(invites, members).accept(AcceptInviteCommand(user_id=5, code="ZZZZ9999"))
    assert calls == ["find_shop_id"]
```

`backend/apps/tenancy/tests/app/use_cases/test_change_member_role_interactor.py`와 `test_remove_member_interactor.py`에서 스텁의 잠금 메서드를 바꾼다(두 파일 모두).
```python
    async def lock_membership_changes(self, shop_id):
        self.calls.append("lock_membership_changes")
        self.locked_shop_id = shop_id
```
그리고 각 파일에서 `assert members.calls[:2] == ["lock_membership_changes", "get_active"]` 다음 줄에 더한다.
```python
    assert members.locked_shop_id == 3
```

`backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`의 `_lock` 도우미를 바꾼다.
```python
async def _lock(session, shop_id):
    await asyncio.wait_for(
        MemberPgRepository(session).lock_membership_changes(shop_id), timeout=0.5
    )
```

`backend/apps/tenancy/tests/adapter/test_invite_pg_repository.py`의 끝에 더한다.
```python


async def test_해시로_매장_ID_만_읽는다(db_session):
    shop, ctx = await _shop_with_owner(db_session)
    repo = InvitePgRepository(db_session)
    await repo.create(ctx, RoleCode.STAFF, "hash-c", EXPIRES, max_uses=1)
    assert await repo.find_shop_id_by_code_hash("hash-c") == shop.id
    assert await repo.find_shop_id_by_code_hash("nope") is None
```

그리고 같은 파일 끝에 두 세션 테스트를 더한다 (import 묶음에 `import asyncio`, `from sqlalchemy.ext.asyncio import async_sessionmaker`, `from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand`, `from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor`, `from tenancy.domain.services.invite_code import hash_invite_code`도 더한다).
```python


class _OpenLimiter:
    async def hit(self, user_id):
        return 1


def _accept(session, user_id):
    interactor = AcceptInviteInteractor(
        invites=InvitePgRepository(session), members=MemberPgRepository(session),
        shops=ShopPgRepository(session), limiter=_OpenLimiter(), now=lambda: EXPIRES - timedelta(days=1),
    )
    return interactor.accept(AcceptInviteCommand(user_id=user_id, code="ABCD2345"))


async def test_멤버십_변경이_매장을_잠근_동안_초대_수락은_기다린다(db_engine):
    """E1 — 수락이 매장 행 잠금을 타는지 실제 두 세션으로 확인한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        shop = await ShopPgRepository(setup).create("Hiss Haus", "pet_grooming")
        await InvitePgRepository(setup).create_owner_invite(shop.id, hash_invite_code("ABCD2345"), EXPIRES)
        await setup.commit()

    async with factory() as one, factory() as two:
        await MemberPgRepository(one).lock_membership_changes(shop.id)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_accept(two, user_id=7), timeout=0.5)
        await two.rollback()

        await one.commit()
        result = await asyncio.wait_for(_accept(two, user_id=7), timeout=0.5)
        assert result.role == "owner"
        await two.rollback()
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests -q -p no:cacheprovider -k "accept_invite_interactor or change_member_role_interactor or remove_member_interactor or invite_pg_repository or member_pg_repository"`
Expected: FAIL — `AttributeError: … 'find_shop_id_by_code_hash'`, 호출 순서 단언 실패, 두 세션 테스트는 `DID NOT RAISE TimeoutError`

- [ ] **Step 3: 포트와 PG 구현을 고친다**

`backend/apps/tenancy/app/ports/output/member_repository.py`의 `lock_membership_changes`를 바꾼다.
```python
    @abstractmethod
    async def lock_membership_changes(self, shop_id: int) -> None:
        """매장 행을 잠가 같은 매장의 역할 변경·내보내기·초대 수락·탈퇴를 직렬화한다.

        마지막 사장 규칙을 지키고, 모든 경로가 매장 → 멤버 → 초대 순으로 잠가 교착하지 않게 하려는 것이다.
        대상을 읽기 **전에** 부른다. 데이터를 읽는 메서드가 아니라서 ShopContext 를 받지 않는다 —
        초대 수락과 탈퇴는 컨텍스트 없이 잠가야 한다.
        """
```

`backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`의 구현을 바꾼다.
```python
    async def lock_membership_changes(self, shop_id: int) -> None:
        await self._session.execute(
            select(ShopOrm.id).where(ShopOrm.id == shop_id).with_for_update()
        )
```

`backend/apps/tenancy/app/ports/output/invite_repository.py`에서 `find_by_code_hash_for_update` 앞에 메서드를 더한다.
```python
    @abstractmethod
    async def find_shop_id_by_code_hash(self, code_hash: str) -> int | None:
        """잠그지 않고 매장 ID 만 읽는다. 수락이 매장 행을 먼저 잠그려면 어느 매장인지 알아야 한다."""
```

`backend/apps/tenancy/adapter/outbound/pg/invite_pg_repository.py`에 구현을 더한다.
```python
    async def find_shop_id_by_code_hash(self, code_hash: str) -> int | None:
        stmt = select(ShopInviteOrm.shop_id).where(ShopInviteOrm.code_hash == code_hash)
        return (await self._session.execute(stmt)).scalar_one_or_none()
```

- [ ] **Step 4: 인터랙터를 고친다**

`backend/apps/tenancy/app/use_cases/change_member_role_interactor.py`와 `remove_member_interactor.py`에서 잠금 호출을 바꾼다(두 파일 모두).
```python
        await self._members.lock_membership_changes(command.ctx.shop_id)
```

`backend/apps/tenancy/app/use_cases/accept_invite_interactor.py`의 `accept`에서 초대를 찾는 부분을 바꾼다.
```python
        code_hash = hash_invite_code(command.code)
        shop_id = await self._invites.find_shop_id_by_code_hash(code_hash)
        if shop_id is None:
            raise InviteInvalidError("초대 코드를 확인해 주세요.")
        # 내보내기·강등·탈퇴와 같은 순서(매장 → 멤버 → 초대)로 잠근다. 순서가 다르면 서로 교착한다.
        await self._members.lock_membership_changes(shop_id)
        invite = await self._invites.find_by_code_hash_for_update(code_hash)
        invite.ensure_usable(self._now())
```
(초대는 지워지지 않으므로 잠근 뒤의 조회는 반드시 같은 행을 돌려준다. 그 아래 `shop = await self._shops.get_by_id(invite.shop_id)`부터는 그대로 둔다.)

- [ ] **Step 5: 통과를 확인한다**

Run: Step 2의 명령 → 전부 통과.
Run: 단위 테스트 전체, 통합 테스트 전체(특히 `tests/integration/test_shop_flow_wiring.py`), 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 6: tenancy 문서를 고친다**

`backend/apps/tenancy/_docs/CLAUDE.md`에서 "매장에는 사장이 한 명 이상 있어야 한다. …"로 시작하는 항목을 바꾼다.
```markdown
- 매장에는 사장이 한 명 이상 있어야 한다. 멤버십을 바꾸는 유스케이스(역할 변경, 내보내기, 초대 수락, 탈퇴)는 맨 앞에서 `lock_membership_changes(shop_id)`로 매장 행을 잠근 뒤 대상을 읽는다. 사장을 낮추거나 내보내기 전에는 `count_owners`로 사장 행을 잠그고 센다.
- 잠금 순서는 언제나 매장 행 → 멤버 행 → 초대 행이다. 여러 매장을 잠글 때는 매장 ID 오름차순으로 잠근다. 순서를 어기면 다른 경로와 교착한다.
```

- [ ] **Step 7: 커밋**

```bash
git add backend/apps/tenancy
git commit -m "fix(tenancy): 초대 수락도 매장 행을 먼저 잠가 멤버십 변경과 같은 순서로 잠근다"
```

---

### Task 7: 탈퇴의 소속 정리 — `MembershipLifecyclePort`와 `apply_withdrawal`

회원 탈퇴가 소속을 정리할 때 쓰는 허브 포트와 tenancy의 구현이다. HTTP 표면이 없다. 규칙은 설계 5.7절 2~4번이다.
- 혼자 사장인 매장에 다른 멤버가 있으면 막는다(`OWNERSHIP_TRANSFER_REQUIRED`).
- 혼자 사장이고 멤버가 본인뿐이면 `close_sole_owned`가 참일 때만 매장을 닫고 진행한다. 아니면 막는다(`SHOP_CLOSE_CONFIRM_REQUIRED`).
- 그 밖에는 소속을 해제한다. 그 멤버가 만든 미사용 초대도 무효화한다(위협 F2).

**미리 조회하는 메서드(`check_withdrawal`)는 만들지 않는다.** 조회와 적용 사이에 다른 요청이 사장 수를 바꿀 수 있다(위협 F1). 적용이 매장마다 행을 잠근 뒤 다시 읽고 판단한다. 막히면 예외가 요청의 트랜잭션을 통째로 되돌리므로 앞서 처리한 매장의 변경도 남지 않는다. 매장은 ID 오름차순으로 잠근다(위협 F3).

**Files:**
- Create: `backend/apps/hub/app/ports/membership_lifecycle_port.py`
- Create: `backend/apps/tenancy/app/use_cases/apply_withdrawal_interactor.py`
- Create: `backend/apps/tenancy/dependencies/apply_withdrawal_provider.py`
- Modify: `backend/apps/tenancy/domain/errors.py`, `backend/apps/tenancy/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/tenancy/app/ports/output/member_repository.py`, `shop_repository.py`
- Modify: `backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`, `shop_pg_repository.py`
- Test: `backend/apps/tenancy/tests/app/use_cases/test_apply_withdrawal_interactor.py` (새로), `backend/apps/tenancy/tests/adapter/test_apply_withdrawal_pg.py` (새로), `test_member_pg_repository.py`·`test_shop_pg_repository.py`(추가)

**Interfaces:**
- Consumes: Task 6의 `lock_membership_changes(shop_id)`, 계획 2-1의 `get_active`·`count_owners`·`remove`·`revoke_created_by`·`ShopRepository.get`·조립 함수들
- Produces:
  - `hub.app.ports.membership_lifecycle_port.MembershipLifecyclePort`: `async apply_withdrawal(user_id: int, close_sole_owned: bool) -> None`
  - `tenancy.domain.errors`: `OwnershipTransferRequiredError`(`OWNERSHIP_TRANSFER_REQUIRED`, 409), `ShopCloseConfirmRequiredError`(`SHOP_CLOSE_CONFIRM_REQUIRED`, 409)
  - `MemberRepository.list_active_for_user(user_id: int) -> list[Member]`(매장 ID 오름차순, 닫힌 매장의 소속도 포함), `MemberRepository.count_active(ctx: ShopContext) -> int`
  - `ShopRepository.close(ctx: ShopContext) -> None`
  - `tenancy.dependencies.apply_withdrawal_provider.get_apply_withdrawal_use_case(db: DbSession) -> MembershipLifecyclePort`

- [ ] **Step 1: 허브 포트를 쓴다**

`backend/apps/hub/app/ports/membership_lifecycle_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class MembershipLifecyclePort(ABC):
    """구현: tenancy. 사용: auth (회원 탈퇴)."""

    @abstractmethod
    async def apply_withdrawal(self, user_id: int, close_sole_owned: bool) -> None:
        """탈퇴하는 유저의 모든 소속을 해제한다. 부르는 쪽과 같은 트랜잭션 안에서 돈다.

        혼자 사장인 매장에 다른 멤버가 있으면 막고, 멤버가 본인뿐이면 close_sole_owned 가 참일 때만
        매장을 닫고 진행한다. 막힐 때는 구현 쪽 도메인 오류를 던진다 — 부르는 쪽의 트랜잭션이 통째로
        되돌아가므로 아무것도 바뀌지 않는다. 미리 조회하는 메서드를 따로 두지 않는 이유는, 조회와 적용
        사이에 다른 요청이 사장 수를 바꿀 수 있어서다.
        """
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/app/use_cases/test_apply_withdrawal_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tenancy.domain.entities.member import Member
from tenancy.domain.entities.shop import Shop
from tenancy.domain.errors import OwnershipTransferRequiredError, ShopCloseConfirmRequiredError
from tenancy.domain.value_objects.role_code import RoleCode

NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _member(member_id, shop_id, role):
    return Member(id=member_id, shop_id=shop_id, user_id=5, role=role, joined_at=NOW)


class _StubMembers:
    """memberships: 잠그기 전에 읽은 소속. under_lock: 잠근 뒤 다시 읽었을 때의 소속(기본은 같다)."""

    def __init__(self, memberships, owners=None, actives=None, under_lock=None):
        self.memberships = memberships
        self.under_lock = under_lock if under_lock is not None else {m.id: m for m in memberships}
        self.owners = owners or {}
        self.actives = actives or {}
        self.calls = []
        self.removed = []

    async def list_active_for_user(self, user_id):
        return self.memberships

    async def lock_membership_changes(self, shop_id):
        self.calls.append(("lock", shop_id))

    async def get_active(self, ctx, member_id):
        self.calls.append(("get_active", ctx.shop_id))
        return self.under_lock.get(member_id)

    async def count_owners(self, ctx):
        return self.owners.get(ctx.shop_id, 1)

    async def count_active(self, ctx):
        return self.actives.get(ctx.shop_id, 1)

    async def remove(self, ctx, member_id):
        self.removed.append((ctx.shop_id, member_id))


class _StubShops:
    def __init__(self, closed_shop_ids=()):
        self.closed_shop_ids = set(closed_shop_ids)
        self.closed = []

    async def get(self, ctx):
        return Shop(id=ctx.shop_id, name=f"매장 {ctx.shop_id}", business_type="pet_grooming",
                    phone=None, address=None, timezone="Asia/Seoul", suspended_at=None,
                    closed_at=NOW if ctx.shop_id in self.closed_shop_ids else None)

    async def close(self, ctx):
        self.closed.append(ctx.shop_id)


class _StubInvites:
    def __init__(self):
        self.revoked = []

    async def revoke_created_by(self, ctx, member_id):
        self.revoked.append((ctx.shop_id, member_id))


def _run(members, shops=None):
    shops, invites = shops or _StubShops(), _StubInvites()
    return ApplyWithdrawalInteractor(members, shops, invites), shops, invites


async def test_직원은_소속을_해제하고_만들어_둔_초대를_무효화한다():
    members = _StubMembers([_member(21, 3, RoleCode.STAFF)])
    interactor, shops, invites = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [(3, 21)]
    assert invites.revoked == [(3, 21)]   # F2
    assert shops.closed == []


async def test_다른_사장이_있으면_사장도_그냥_나간다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 2}, actives={3: 2})
    interactor, shops, _ = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [(3, 21)] and shops.closed == []


async def test_혼자_사장인_매장에_다른_멤버가_있으면_막는다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 2})
    interactor, shops, _ = _run(members)
    with pytest.raises(OwnershipTransferRequiredError) as exc:
        await interactor.apply_withdrawal(5, close_sole_owned=True)   # 확인을 줬어도 막는다
    assert "매장 3" in str(exc.value)
    assert members.removed == [] and shops.closed == []


async def test_혼자뿐인_매장은_확인_없이는_닫지_않는다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 1})
    interactor, shops, _ = _run(members)
    with pytest.raises(ShopCloseConfirmRequiredError) as exc:
        await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert "매장 3" in str(exc.value)
    assert members.removed == [] and shops.closed == []


async def test_혼자뿐인_매장은_확인이_있으면_닫고_나간다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 1})
    interactor, shops, invites = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=True)
    assert shops.closed == [3]
    assert members.removed == [(3, 21)] and invites.revoked == [(3, 21)]


async def test_이미_닫힌_매장은_규칙을_따지지_않고_나간다():
    members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 2})
    interactor, shops, _ = _run(members, _StubShops(closed_shop_ids=[3]))
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [(3, 21)] and shops.closed == []


async def test_매장을_ID_순서로_잠그고_잠근_뒤에_대상을_읽는다():
    """F3 — 리포지토리가 매장 ID 순으로 돌려준 순서 그대로, 매장마다 잠금이 먼저다."""
    members = _StubMembers([_member(21, 3, RoleCode.STAFF), _member(34, 8, RoleCode.STAFF)])
    interactor, _, _ = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.calls == [("lock", 3), ("get_active", 3), ("lock", 8), ("get_active", 8)]


async def test_잠근_뒤에_다시_읽은_역할로_판단한다():
    """F1 — 목록을 읽을 때는 직원이었지만, 잠그는 사이에 혼자 남은 사장이 되었다."""
    members = _StubMembers(
        [_member(21, 3, RoleCode.STAFF)],
        under_lock={21: _member(21, 3, RoleCode.OWNER)}, owners={3: 1}, actives={3: 2},
    )
    interactor, _, _ = _run(members)
    with pytest.raises(OwnershipTransferRequiredError):
        await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == []


async def test_잠그는_사이에_내보내졌으면_건너뛴다():
    members = _StubMembers([_member(21, 3, RoleCode.STAFF)], under_lock={})
    interactor, _, invites = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.removed == [] and invites.revoked == []


async def test_소속이_없으면_아무것도_하지_않는다():
    members = _StubMembers([])
    interactor, shops, _ = _run(members)
    await interactor.apply_withdrawal(5, close_sole_owned=False)
    assert members.calls == [] and shops.closed == []
```

`backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`의 끝에 더한다.
```python


async def test_유저의_소속을_매장_ID_순으로_돌려준다_닫힌_매장도_포함한다(db_session):
    a = await _shop(db_session, "A 매장")
    b = await _shop(db_session, "B 매장")
    c = await _shop(db_session, "C 매장")
    repo = MemberPgRepository(db_session)
    in_c = await repo.add(c.id, user_id=7, role=RoleCode.STAFF)
    in_a = await repo.add(a.id, user_id=7, role=RoleCode.OWNER)
    removed = await repo.add(b.id, user_id=7, role=RoleCode.STAFF)
    await repo.remove(_ctx(b.id), removed.id)
    await db_session.execute(text("UPDATE shops SET closed_at = now() WHERE id = :id"), {"id": c.id})
    await repo.add(a.id, user_id=8, role=RoleCode.STAFF)

    memberships = await repo.list_active_for_user(7)
    assert [(m.id, m.shop_id, m.role) for m in memberships] == [
        (in_a.id, a.id, RoleCode.OWNER), (in_c.id, c.id, RoleCode.STAFF),
    ]
    assert await repo.list_active_for_user(404) == []


async def test_지금_속해_있는_멤버_수를_센다(db_session):
    shop = await _shop(db_session)
    other = await _shop(db_session, "다른 매장")
    repo = MemberPgRepository(db_session)
    await repo.add(shop.id, user_id=1, role=RoleCode.OWNER)
    await repo.add(shop.id, user_id=2, role=RoleCode.STAFF)
    gone = await repo.add(shop.id, user_id=3, role=RoleCode.STAFF)
    await repo.remove(_ctx(shop.id), gone.id)
    await repo.add(other.id, user_id=4, role=RoleCode.OWNER)
    assert await repo.count_active(_ctx(shop.id)) == 2
```

`backend/apps/tenancy/tests/adapter/test_shop_pg_repository.py`의 끝에 더한다.
```python


async def test_매장을_닫으면_컨텍스트의_매장에만_닫은_시각이_남는다(db_session):
    repo = ShopPgRepository(db_session)
    a = await repo.create("A 매장", "pet_grooming")
    b = await repo.create("B 매장", "pet_grooming")
    await repo.close(_ctx(a.id))
    assert (await repo.get_by_id(a.id)).is_closed is True
    assert (await repo.get_by_id(b.id)).is_closed is False
```

`backend/apps/tenancy/tests/adapter/test_apply_withdrawal_pg.py`:
```python
"""실제 리포지토리로 도는 탈퇴의 소속 정리 — 막히면 요청의 트랜잭션이 통째로 되돌아가는 것까지 본다."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from hub.app.dtos.shop_context import ShopContext
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tenancy.domain.errors import OwnershipTransferRequiredError
from tenancy.domain.value_objects.role_code import RoleCode

pytestmark = pytest.mark.integration


def _interactor(session):
    return ApplyWithdrawalInteractor(
        MemberPgRepository(session), ShopPgRepository(session), InvitePgRepository(session)
    )


async def _active_user_ids(session, shop_id):
    rows = await session.execute(
        text("SELECT user_id FROM shop_members WHERE shop_id = :id AND removed_at IS NULL ORDER BY user_id"),
        {"id": shop_id},
    )
    return list(rows.scalars())


async def test_막힌_탈퇴는_앞서_처리한_매장도_되돌린다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        shops, members = ShopPgRepository(setup), MemberPgRepository(setup)
        first = await shops.create("직원으로 있는 매장", "pet_grooming")
        second = await shops.create("혼자 사장인 매장", "pet_grooming")
        await members.add(first.id, user_id=1, role=RoleCode.OWNER)
        await members.add(first.id, user_id=7, role=RoleCode.STAFF)
        await members.add(second.id, user_id=7, role=RoleCode.OWNER)
        await members.add(second.id, user_id=2, role=RoleCode.STAFF)
        await setup.commit()

    async with factory() as session:
        with pytest.raises(OwnershipTransferRequiredError):
            await _interactor(session).apply_withdrawal(7, close_sole_owned=True)
        await session.rollback()   # 요청의 get_db 가 예외에서 하는 일

    async with factory() as check:
        assert await _active_user_ids(check, first.id) == [1, 7]
        assert await _active_user_ids(check, second.id) == [2, 7]


async def test_혼자뿐인_매장을_닫고_만들어_둔_초대까지_무효화한다(db_session):
    shops, members, invites = (
        ShopPgRepository(db_session), MemberPgRepository(db_session), InvitePgRepository(db_session)
    )
    shop = await shops.create("Hiss Haus", "pet_grooming")
    owner = await members.add(shop.id, user_id=7, role=RoleCode.OWNER)
    ctx = ShopContext(shop_id=shop.id, member_id=owner.id, role="owner", permissions=frozenset())
    await invites.create(ctx, RoleCode.STAFF, "hash-left-behind",
                         datetime.now(timezone.utc) + timedelta(days=7), max_uses=1)

    await _interactor(db_session).apply_withdrawal(7, close_sole_owned=True)

    assert (await shops.get_by_id(shop.id)).is_closed is True
    assert await _active_user_ids(db_session, shop.id) == []
    assert (await invites.find_by_code_hash_for_update("hash-left-behind")).revoked_at is not None
```

- [ ] **Step 3: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/tenancy/tests -q -p no:cacheprovider -k "apply_withdrawal or list_active_for_user or 소속을_매장_ID or 멤버_수를 or 매장을_닫으면"`
Expected: FAIL — `ModuleNotFoundError: No module named 'tenancy.app.use_cases.apply_withdrawal_interactor'`, `AttributeError: … 'list_active_for_user'`

- [ ] **Step 4: 오류와 포트를 더한다**

`backend/apps/tenancy/domain/errors.py`의 끝에 더한다.
```python


class OwnershipTransferRequiredError(TenancyError):
    code = "OWNERSHIP_TRANSFER_REQUIRED"


class ShopCloseConfirmRequiredError(TenancyError):
    code = "SHOP_CLOSE_CONFIRM_REQUIRED"
```

`backend/apps/tenancy/adapter/inbound/api/error_map.py`의 import와 표(409 묶음)에 더한다.
```python
    OwnershipTransferRequiredError: 409,
    ShopCloseConfirmRequiredError: 409,
```

`backend/apps/tenancy/app/ports/output/member_repository.py`에 메서드 둘을 더한다.
```python
    @abstractmethod
    async def list_active_for_user(self, user_id: int) -> list[Member]:
        """탈퇴용. 유저가 지금 속해 있는 모든 소속을 매장 ID 오름차순으로 돌려준다 (닫힌 매장 포함).

        순서가 곧 잠금 순서다. 두 유저의 탈퇴가 서로 다른 순서로 매장을 잠그면 교착한다.
        """

    @abstractmethod
    async def count_active(self, ctx: ShopContext) -> int:
        """지금 속해 있는 멤버 수. lock_membership_changes 뒤에 부른다."""
```

`backend/apps/tenancy/app/ports/output/shop_repository.py`에 메서드를 더한다.
```python
    @abstractmethod
    async def close(self, ctx: ShopContext) -> None:
        """닫은 시각을 남긴다. 닫힌 매장은 소속 확인에서 SHOP_CLOSED 로 막힌다. 데이터는 지우지 않는다."""
```

- [ ] **Step 5: PG 구현을 더한다**

`backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`에 메서드 둘을 더한다 (`list_for_user` 다음).
```python
    async def list_active_for_user(self, user_id: int) -> list[Member]:
        stmt = (
            select(ShopMemberOrm, RoleOrm.code)
            .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
            .where(ShopMemberOrm.user_id == user_id, ShopMemberOrm.removed_at.is_(None))
            .order_by(ShopMemberOrm.shop_id)
        )
        return [to_member(m, code) for m, code in (await self._session.execute(stmt)).all()]

    async def count_active(self, ctx: ShopContext) -> int:
        stmt = select(func.count()).select_from(ShopMemberOrm).where(
            ShopMemberOrm.shop_id == ctx.shop_id, ShopMemberOrm.removed_at.is_(None)
        )
        return (await self._session.execute(stmt)).scalar_one()
```

`backend/apps/tenancy/adapter/outbound/pg/shop_pg_repository.py`에 import와 메서드를 더한다.
```python
from sqlalchemy import func, select, update
```
```python
    async def close(self, ctx: ShopContext) -> None:
        await self._session.execute(
            update(ShopOrm).where(ShopOrm.id == ctx.shop_id).values(closed_at=func.now())
        )
```

- [ ] **Step 6: 슬라이스를 구현한다**

`backend/apps/tenancy/app/use_cases/apply_withdrawal_interactor.py`:
```python
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort
from tenancy.app.ports.output.invite_repository import InviteRepository
from tenancy.app.ports.output.member_repository import MemberRepository
from tenancy.app.ports.output.shop_repository import ShopRepository
from tenancy.domain.errors import OwnershipTransferRequiredError, ShopCloseConfirmRequiredError
from tenancy.domain.value_objects.role_code import RoleCode


class ApplyWithdrawalInteractor(MembershipLifecyclePort):
    """허브의 MembershipLifecyclePort 구현. 입력 포트가 곧 허브 포트다.

    auth 의 탈퇴 요청과 같은 DB 세션·같은 트랜잭션에서 돈다. 막히면 예외를 던지고,
    요청의 트랜잭션이 통째로 되돌아가므로 앞서 처리한 매장의 변경도 남지 않는다.
    """

    def __init__(
        self, members: MemberRepository, shops: ShopRepository, invites: InviteRepository
    ) -> None:
        self._members = members
        self._shops = shops
        self._invites = invites

    async def apply_withdrawal(self, user_id: int, close_sole_owned: bool) -> None:
        # 매장 ID 오름차순으로 온다. 이 순서대로 잠가야 다른 유저의 탈퇴와 교착하지 않는다.
        for membership in await self._members.list_active_for_user(user_id):
            ctx = ShopContext(
                shop_id=membership.shop_id, member_id=membership.id,
                role=membership.role.value, permissions=frozenset(),
            )
            await self._members.lock_membership_changes(ctx.shop_id)
            # 잠근 뒤에 다시 읽는다. 목록을 읽은 뒤로 역할이 바뀌었거나 내보내졌을 수 있다.
            current = await self._members.get_active(ctx, membership.id)
            if current is None:
                continue
            shop = await self._shops.get(ctx)
            if (
                not shop.is_closed
                and current.role is RoleCode.OWNER
                and await self._members.count_owners(ctx) == 1
            ):
                if await self._members.count_active(ctx) > 1:
                    raise OwnershipTransferRequiredError(
                        f"'{shop.name}'의 사장이 회원님뿐입니다. 다른 멤버를 먼저 사장으로 지정해 주세요."
                    )
                if not close_sole_owned:
                    raise ShopCloseConfirmRequiredError(
                        f"탈퇴하면 '{shop.name}'도 함께 닫힙니다. 확인 후 다시 시도해 주세요."
                    )
                await self._shops.close(ctx)
            await self._members.remove(ctx, current.id)
            await self._invites.revoke_created_by(ctx, current.id)
```

`backend/apps/tenancy/dependencies/apply_withdrawal_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort
from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
from tenancy.dependencies.tenancy_wiring import (
    build_invite_repository,
    build_member_repository,
    build_shop_repository,
)


def get_apply_withdrawal_use_case(db: DbSession) -> MembershipLifecyclePort:
    return ApplyWithdrawalInteractor(
        members=build_member_repository(db),
        shops=build_shop_repository(db),
        invites=build_invite_repository(db),
    )
```

- [ ] **Step 7: 통과를 확인한다**

Run: Step 3의 명령 → 전부 통과.
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 8: 커밋**

```bash
git add backend/apps/hub backend/apps/tenancy
git commit -m "feat(tenancy): 탈퇴의 소속 정리 — MembershipLifecyclePort 구현"
```

---

### Task 8: 신원과 계정의 영속 계층 (auth)

연결·해제·탈퇴 세 슬라이스가 쓰는 리포지토리 메서드와 도메인 규칙을 만든다. 슬라이스는 다음 작업들에서 붙인다.

- **유저 행 잠금.** 계정을 바꾸는 유스케이스는 맨 앞에서 유저 행을 잠그고 다시 읽는다(위협 G1·G2·H5).
- **유일 제약 `(user_id, provider)`.** 한 유저는 제공자마다 신원을 하나만 가진다(위협 G4). 기존의 `(provider, provider_user_id)` 제약과 함께, 어느 제약에 걸렸는지로 오류를 가른다.
- **익명화.** 탈퇴한 유저의 행은 남긴다(매장 기록에 "탈퇴한 사용자"로 표시된다). 이름을 바꾸고 사진·전화번호를 지우고 `deleted_at`을 남긴다.

**Files:**
- Create: `backend/alembic/versions/0004_social_identities_user_provider_unique.py`
- Create: `backend/apps/auth/domain/services/identity_guard.py`
- Modify: `backend/apps/auth/adapter/outbound/orm/user_orm.py`
- Modify: `backend/apps/auth/domain/errors.py`, `backend/apps/auth/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/auth/app/ports/output/user_repository.py`, `operator_repository.py`
- Modify: `backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`, `operator_pg_repository.py`
- Test: `backend/apps/auth/tests/domain/test_identity_guard.py` (새로), `backend/apps/auth/tests/adapter/test_user_pg_repository.py`·`test_operator_pg_repository.py`(추가)

**Interfaces:**
- Consumes: Task 2의 `_require_cipher`·`FernetCipher.decrypt`, Task 3의 `_constraint(exc)`·`IdentityAlreadyLinkedError`, Task 5의 `IdentityRevocation`
- Produces:
  - 마이그레이션 `0004` — `social_identities`에 유일 제약 `uq_social_identities_user_provider (user_id, provider)`
  - `auth.domain.errors`: `ProviderAlreadyLinkedError`(`PROVIDER_ALREADY_LINKED`, 409), `LastIdentityError`(`LAST_IDENTITY`, 409), `IdentityNotFoundError`(`IDENTITY_NOT_FOUND`, 404)
  - `auth.domain.services.identity_guard.ensure_identity_remains(identity_count: int) -> None` — 하나뿐이면 `LastIdentityError`
  - `UserRepository`:
    - `async lock(user_id: int) -> User | None` — 유저 행을 잠그고 최신 값을 돌려준다
    - `async add_identity(user_id: int, profile: SocialProfile) -> None` — 다른 유저의 신원이면 `IdentityAlreadyLinkedError`, 같은 제공자를 이미 가졌으면 `ProviderAlreadyLinkedError`
    - `async list_revocations(user_id: int) -> list[IdentityRevocation]` — 신원 ID 순, 제공자 토큰은 복호화해서
    - `async delete_identity(user_id: int, provider: Provider) -> None`
    - `async delete_identities(user_id: int) -> None`
    - `async anonymize(user_id: int) -> None`
  - `OperatorRepository.revoke(user_id: int) -> None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/domain/test_identity_guard.py`:
```python
import pytest

from auth.domain.errors import LastIdentityError
from auth.domain.services.identity_guard import ensure_identity_remains


def test_로그인_수단이_하나뿐이면_해제할_수_없다():
    with pytest.raises(LastIdentityError):
        ensure_identity_remains(identity_count=1)


def test_둘_이상이면_해제할_수_있다():
    ensure_identity_remains(identity_count=2)
```

`backend/apps/auth/tests/adapter/test_user_pg_repository.py`의 끝에 더한다 (import 묶음에 `import asyncio`, `from sqlalchemy.ext.asyncio import async_sessionmaker`, `from auth.domain.errors import ProviderAlreadyLinkedError`도 더한다).
```python


async def test_로그인_수단을_더_붙이면_붙인_순서대로_나온다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    await repo.add_identity(user.id, _profile(provider=Provider.APPLE, provider_user_id="apple-1",
                                              provider_refresh_token="apple-refresh"))
    assert [i.provider for i in await repo.list_identities(user.id)] == [Provider.KAKAO, Provider.APPLE]
    found = await repo.find_by_identity(Provider.APPLE, "apple-1")
    assert found.id == user.id


async def test_다른_유저의_신원은_붙일_수_없다(db_session):
    """G3"""
    repo = _repo(db_session)
    await repo.create_with_identity(_profile(provider_user_id="kakao-owned"))
    me = await repo.create_with_identity(_profile(provider=Provider.GOOGLE, provider_user_id="google-me"))
    with pytest.raises(IdentityAlreadyLinkedError):
        await repo.add_identity(me.id, _profile(provider_user_id="kakao-owned"))
    assert [i.provider for i in await repo.list_identities(me.id)] == [Provider.GOOGLE]


async def test_같은_제공자의_신원을_둘_붙일_수_없다(db_session):
    """G4"""
    repo = _repo(db_session)
    me = await repo.create_with_identity(_profile(provider_user_id="kakao-first"))
    with pytest.raises(ProviderAlreadyLinkedError):
        await repo.add_identity(me.id, _profile(provider_user_id="kakao-second"))
    assert len(await repo.list_identities(me.id)) == 1


async def test_연결을_끊을_신원을_복호화한_토큰과_함께_돌려준다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    await repo.add_identity(user.id, _profile(provider=Provider.APPLE, provider_user_id="apple-1",
                                              provider_refresh_token="apple-refresh"))
    revocations = await repo.list_revocations(user.id)
    assert [(r.provider, r.provider_user_id, r.provider_refresh_token) for r in revocations] == [
        (Provider.KAKAO, "kakao-100", None), (Provider.APPLE, "apple-1", "apple-refresh"),
    ]
    assert "apple-refresh" not in repr(revocations[1])


async def test_신원_하나를_지우면_그_수단으로는_찾을_수_없다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile())
    await repo.add_identity(user.id, _profile(provider=Provider.GOOGLE, provider_user_id="google-1"))
    await repo.delete_identity(user.id, Provider.KAKAO)
    assert [i.provider for i in await repo.list_identities(user.id)] == [Provider.GOOGLE]
    assert await repo.find_by_identity(Provider.KAKAO, "kakao-100") is None


async def test_익명화하고_신원을_모두_지우면_같은_소셜_계정으로_새로_가입할_수_있다(db_session):
    repo = _repo(db_session)
    user = await repo.create_with_identity(_profile(profile_image_url="https://img/1.jpg"))
    await db_session.execute(text("UPDATE users SET phone = '010-0000-0000' WHERE id = :id"), {"id": user.id})
    await repo.anonymize(user.id)
    await repo.delete_identities(user.id)

    gone = await repo.lock(user.id)
    assert (gone.display_name, gone.profile_image_url, gone.phone) == ("탈퇴한 사용자", None, None)
    assert gone.is_deleted is True
    assert await repo.list_identities(user.id) == []
    again = await repo.create_with_identity(_profile())
    assert again.id != user.id


async def test_유저_행_잠금은_같은_유저의_다른_요청을_기다리게_한다(db_engine):
    """G1·G2·H5 — 계정을 바꾸는 요청들이 유저 단위로 직렬화된다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await _repo(setup).create_with_identity(_profile())
        other = await _repo(setup).create_with_identity(_profile(provider_user_id="kakao-other"))
        await setup.commit()

    async with factory() as one, factory() as two:
        assert (await _repo(one).lock(user.id)).id == user.id
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_repo(two).lock(user.id), timeout=0.5)
        await two.rollback()
        # 다른 유저는 막지 않는다.
        assert (await asyncio.wait_for(_repo(two).lock(other.id), timeout=0.5)).id == other.id
        await two.rollback()

        await _repo(one).anonymize(user.id)
        await one.commit()
        # 기다리던 쪽은 잠금을 얻은 뒤 최신 값(탈퇴함)을 본다.
        assert (await asyncio.wait_for(_repo(two).lock(user.id), timeout=0.5)).is_deleted is True
        await two.rollback()


async def test_없는_유저를_잠그면_None_이다(db_session):
    assert await _repo(db_session).lock(999999) is None
```

`backend/apps/auth/tests/adapter/test_operator_pg_repository.py`의 끝에 더한다.
```python


async def test_지정을_거두면_운영자가_아니다(db_session):
    repo = OperatorPgRepository(db_session)
    user_id = await _user_id(db_session)
    await repo.grant(user_id)
    await repo.revoke(user_id)
    assert await repo.is_operator(user_id) is False
    await repo.revoke(user_id)   # 여러 번 불러도 같다
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/domain/test_identity_guard.py apps/auth/tests/adapter/test_user_pg_repository.py apps/auth/tests/adapter/test_operator_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.domain.services.identity_guard'`, `ImportError: cannot import name 'ProviderAlreadyLinkedError'`

- [ ] **Step 3: 도메인을 더한다**

`backend/apps/auth/domain/errors.py`의 끝에 더한다.
```python


class ProviderAlreadyLinkedError(AuthError):
    code = "PROVIDER_ALREADY_LINKED"


class LastIdentityError(AuthError):
    code = "LAST_IDENTITY"


class IdentityNotFoundError(AuthError):
    code = "IDENTITY_NOT_FOUND"
```

`backend/apps/auth/adapter/inbound/api/error_map.py`의 import와 표에 더한다.
```python
    IdentityNotFoundError: 404,
    ProviderAlreadyLinkedError: 409,
    LastIdentityError: 409,
```

`backend/apps/auth/domain/services/identity_guard.py`:
```python
from __future__ import annotations

from auth.domain.errors import LastIdentityError


def ensure_identity_remains(identity_count: int) -> None:
    """로그인 수단 하나를 해제하기 직전에 부른다. identity_count 는 해제하기 전의 수다."""
    if identity_count <= 1:
        raise LastIdentityError(
            "마지막 로그인 수단은 해제할 수 없습니다. 다른 로그인 수단을 먼저 연결해 주세요."
        )
```

- [ ] **Step 4: 유일 제약을 더한다**

`backend/apps/auth/adapter/outbound/orm/user_orm.py`의 `SocialIdentityOrm.__table_args__`를 바꾼다.
```python
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_social_identities_provider_user"),
        # 한 유저는 제공자마다 신원을 하나만 가진다. DELETE /v1/auth/identities/{provider} 가 성립하려면 필요하다.
        UniqueConstraint("user_id", "provider", name="uq_social_identities_user_provider"),
    )
```

`backend/alembic/versions/0004_social_identities_user_provider_unique.py`:
```python
"""소셜 신원: 한 유저는 제공자마다 하나만

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-21
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_social_identities_user_provider", "social_identities", ["user_id", "provider"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_social_identities_user_provider", "social_identities", type_="unique")
```

- [ ] **Step 5: 포트를 더한다**

`backend/apps/auth/app/ports/output/user_repository.py`에 import와 메서드들을 더한다.
```python
from auth.domain.value_objects.identity_revocation import IdentityRevocation
```
```python
    @abstractmethod
    async def lock(self, user_id: int) -> User | None:
        """유저 행을 잠그고 최신 값을 돌려준다. 계정을 바꾸는 유스케이스가 맨 앞에서 부른다.

        같은 유저의 연결·해제·탈퇴가 겹치지 않게 직렬화한다. 잠근 뒤에는 탈퇴 여부를 다시 본다.
        """

    @abstractmethod
    async def add_identity(self, user_id: int, profile: SocialProfile) -> None:
        """다른 유저의 신원이면 IdentityAlreadyLinkedError, 같은 제공자를 이미 가졌으면 ProviderAlreadyLinkedError."""

    @abstractmethod
    async def list_revocations(self, user_id: int) -> list[IdentityRevocation]:
        """제공자 쪽 연결을 끊는 데 필요한 것을 신원 ID 순으로 돌려준다. 신원을 지우기 전에 읽어 둔다."""

    @abstractmethod
    async def delete_identity(self, user_id: int, provider: Provider) -> None: ...

    @abstractmethod
    async def delete_identities(self, user_id: int) -> None: ...

    @abstractmethod
    async def anonymize(self, user_id: int) -> None:
        """행은 남긴다. 이름을 "탈퇴한 사용자"로 바꾸고 사진·전화번호를 지우고 탈퇴 시각을 남긴다."""
```

`backend/apps/auth/app/ports/output/operator_repository.py`에 메서드를 더한다.
```python
    @abstractmethod
    async def revoke(self, user_id: int) -> None:
        """여러 번 불러도 결과가 같다."""
```

- [ ] **Step 6: PG 구현을 더한다**

`backend/apps/auth/adapter/outbound/pg/user_pg_repository.py`에서 import를 고치고 메서드들을 더한다.
```python
from sqlalchemy import delete, func, select, update

from auth.domain.errors import IdentityAlreadyLinkedError, ProviderAlreadyLinkedError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
```
```python
    async def lock(self, user_id: int) -> User | None:
        stmt = (
            select(UserOrm)
            .where(UserOrm.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)  # 기다리는 동안 바뀐 값을 읽는다
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_user(row) if row else None

    async def add_identity(self, user_id: int, profile: SocialProfile) -> None:
        token = profile.provider_refresh_token
        row = SocialIdentityOrm(
            user_id=user_id,
            provider=profile.provider.value,
            provider_user_id=profile.provider_user_id,
            email=profile.email,
            provider_refresh_token_enc=self._require_cipher().encrypt(token) if token else None,
        )
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError as exc:
            name = _constraint(exc)
            if name == "uq_social_identities_provider_user":
                raise IdentityAlreadyLinkedError(
                    "이미 다른 계정에 연결된 로그인 수단입니다. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요."
                ) from exc
            if name == "uq_social_identities_user_provider":
                raise ProviderAlreadyLinkedError(
                    f"{profile.provider.value} 로그인은 이미 연결되어 있습니다."
                ) from exc
            raise

    async def list_revocations(self, user_id: int) -> list[IdentityRevocation]:
        stmt = (
            select(SocialIdentityOrm)
            .where(SocialIdentityOrm.user_id == user_id)
            .order_by(SocialIdentityOrm.id)
        )
        return [
            IdentityRevocation(
                provider=Provider(row.provider),
                provider_user_id=row.provider_user_id,
                provider_refresh_token=(
                    self._require_cipher().decrypt(row.provider_refresh_token_enc)
                    if row.provider_refresh_token_enc else None
                ),
            )
            for row in (await self._session.execute(stmt)).scalars()
        ]

    async def delete_identity(self, user_id: int, provider: Provider) -> None:
        await self._session.execute(
            delete(SocialIdentityOrm).where(
                SocialIdentityOrm.user_id == user_id, SocialIdentityOrm.provider == provider.value
            )
        )

    async def delete_identities(self, user_id: int) -> None:
        await self._session.execute(
            delete(SocialIdentityOrm).where(SocialIdentityOrm.user_id == user_id)
        )

    async def anonymize(self, user_id: int) -> None:
        await self._session.execute(
            update(UserOrm)
            .where(UserOrm.id == user_id)
            .values(
                display_name="탈퇴한 사용자", profile_image_url=None, phone=None,
                deleted_at=func.now(),
            )
        )
```

`backend/apps/auth/adapter/outbound/pg/operator_pg_repository.py`에 import와 메서드를 더한다.
```python
from sqlalchemy import delete, select
```
```python
    async def revoke(self, user_id: int) -> None:
        await self._session.execute(
            delete(PlatformOperatorOrm).where(PlatformOperatorOrm.user_id == user_id)
        )
```

- [ ] **Step 7: 통과를 확인하고 개발 DB에 적용한다**

Run: Step 2의 명령 → 전부 통과.
Run: `docker compose run --rm backend pytest tests/test_schema_drift.py -q -p no:cacheprovider` → `1 passed`.
Run: `docker compose run --rm backend alembic upgrade head` → 오류 없이 끝난다. (개발 DB에서 `downgrade`는 돌리지 않는다. 되돌리기를 확인하려면 계획 2-1 Task 4처럼 `-x db_url=`로 테스트 DB에서 한다.)
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 8: 커밋**

```bash
git add backend/apps/auth backend/alembic/versions/0004_social_identities_user_provider_unique.py
git commit -m "feat(auth): 신원 추가·삭제, 유저 행 잠금, 익명화 — 제공자마다 신원 하나"
```

---

### Task 8b: 초대 수락이 유저 행을 잠그고 탈퇴 여부를 확인한다

Task 7의 검토에서 위협 점검표에 없던 구멍이 나왔다(새 위협 **F4**).

> **F4 — 탈퇴와 겹친 초대 수락이 소속을 되살린다.** `accept_invite`는 `users`를 보지도 잠그지도 않는다. 탈퇴(Task 11)가 유저 행과 매장 행을 잠그고 소속을 정리하는 동안, 같은 유저의 초대 수락 요청은 (요청 시작 때의 인증 확인은 이미 통과한 채) 매장 행 잠금 뒤에서 기다리다가 탈퇴가 커밋된 직후 `members.add`에 성공한다. 탈퇴한 유저의 소속이 남는다. 사장용 초대였다면 "로그인할 수 없는 사장"이 생기고 `count_owners`를 부풀려, 나중에 진짜 사장이 탈퇴할 때 마지막 사장 보호가 걸리지 않는다 → 살아 있는 사장이 없는 열린 매장.

막는 방법: 초대 수락이 **맨 앞에서 유저 행을 잠그고** 지금 활동할 수 있는 유저인지 다시 본다. 전역 잠금 순서(유저 행 → 매장 행 → 멤버 행 → 초대 행)와 일치한다. 수락이 먼저 잠그면 탈퇴가 기다렸다가 새 소속까지 정리하고, 탈퇴가 먼저 잠그면 수락이 기다렸다가 탈퇴한 것을 보고 거절한다.

tenancy는 `users`를 모르므로 허브 포트를 하나 더한다. auth가 HTTP 표면이 없는 슬라이스 `guard_active_user`로 구현하고(Task 8의 `UserRepository.lock`을 쓴다), tenancy가 자리로 받고, `main.py`가 꽂는다.

**Files:**
- Create: `backend/apps/hub/app/ports/active_user_guard_port.py`
- Create: `backend/apps/auth/app/use_cases/guard_active_user_interactor.py`, `backend/apps/auth/dependencies/guard_active_user_provider.py`
- Modify: `backend/apps/tenancy/domain/errors.py`, `backend/apps/tenancy/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/tenancy/dependencies/hub_ports.py`, `backend/apps/tenancy/dependencies/accept_invite_provider.py`
- Modify: `backend/apps/tenancy/app/use_cases/accept_invite_interactor.py`
- Modify: `backend/main.py`
- Modify: `backend/apps/tenancy/_docs/CLAUDE.md`, `backend/apps/hub/_docs/CLAUDE.md`
- Test: `backend/apps/auth/tests/app/use_cases/test_guard_active_user_interactor.py` (새로), `backend/apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py`·`test_accept_invite_locking.py` (수정), `backend/tests/integration/test_accept_vs_withdraw_locking.py` (새로)

**Interfaces:**
- Consumes: Task 8의 `UserRepository.lock(user_id) -> User | None`·`anonymize`, `auth.dependencies.auth_wiring.build_user_repository(db)`, Task 6의 수락 순서(선조회 → 매장 잠금 → 잠근 조회)
- Produces:
  - `hub.app.ports.active_user_guard_port.ActiveUserGuardPort`: `async lock_active(user_id: int) -> bool`
  - `auth.dependencies.guard_active_user_provider.get_guard_active_user_use_case(db: DbSession) -> ActiveUserGuardPort`
  - `tenancy.dependencies.hub_ports.get_active_user_guard() -> ActiveUserGuardPort` — 자리
  - `tenancy.domain.errors.AccountUnavailableError` (`code = "UNAUTHENTICATED"`, 401)
  - `AcceptInviteInteractor(invites, members, shops, limiter, users: ActiveUserGuardPort, now=_utcnow)`

- [ ] **Step 1: 허브 포트를 쓴다**

`backend/apps/hub/app/ports/active_user_guard_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class ActiveUserGuardPort(ABC):
    """구현: auth. 사용: tenancy (초대 수락)."""

    @abstractmethod
    async def lock_active(self, user_id: int) -> bool:
        """유저 행을 잠그고, 지금 활동할 수 있는 유저(있고, 탈퇴하지 않았고, 정지되지 않은)인지 돌려준다.

        잠금은 부르는 쪽의 트랜잭션이 끝날 때 풀린다. 같은 유저의 회원 탈퇴와 겹치지 않게 하려는 것이다 —
        소속을 새로 만드는 유스케이스는 매장 행을 잠그기 **전에** 이것을 부른다 (잠금 순서: 유저 → 매장).
        """
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_guard_active_user_interactor.py`:
```python
from datetime import datetime, timezone

from auth.app.use_cases.guard_active_user_interactor import GuardActiveUserInteractor
from auth.domain.entities.user import User

NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


class _StubUsers:
    def __init__(self, user):
        self.user = user
        self.locked = []

    async def lock(self, user_id):
        self.locked.append(user_id)
        return self.user


def _user(suspended=False, deleted=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None,
                suspended_at=NOW if suspended else None, deleted_at=NOW if deleted else None)


async def test_활동_중인_유저면_행을_잠그고_참을_돌려준다():
    users = _StubUsers(_user())
    assert await GuardActiveUserInteractor(users).lock_active(5) is True
    assert users.locked == [5]


async def test_탈퇴했거나_정지됐거나_없는_유저면_거짓이다():
    for user in (_user(deleted=True), _user(suspended=True), None):
        assert await GuardActiveUserInteractor(_StubUsers(user)).lock_active(5) is False
```

`backend/apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py`에서 세 곳을 고친다.

(1) 스텁을 하나 더한다 (`_StubLimiter` 다음).
```python
class _StubUserGuard:
    def __init__(self, active=True, calls=None):
        self.active = active
        self.calls = calls if calls is not None else []

    async def lock_active(self, user_id):
        self.calls.append("lock_active")
        return self.active
```
(2) `_interactor` 도우미가 `users` 인자를 받아 넘기게 한다 (기본은 활동 중인 유저).
```python
def _interactor(invites, members=None, shops=None, limiter=None, users=None):
    return AcceptInviteInteractor(
        invites=invites, members=members or _StubMembers(), shops=shops or _StubShops(),
        limiter=limiter or _StubLimiter(), users=users or _StubUserGuard(), now=lambda: NOW,
    )
```
(3) import 묶음에 `AccountUnavailableError`를 더하고, 파일 끝에 테스트를 더한다. 그리고 기존 `test_초대_행을_잠그기_전에_매장_행을_먼저_잠근다`의 호출 순서 단언은 그대로 둔다(그 테스트는 `users`에 호출 기록을 넘기지 않는다).
```python


async def test_유저_행을_매장_행보다_먼저_잠근다():
    """F4 — 잠금 순서는 유저 → 매장 → 멤버 → 초대다."""
    calls = []
    invites, members = _StubInvites(_invite(), calls), _StubMembers(calls=calls)
    await _interactor(invites, members, users=_StubUserGuard(calls=calls)).accept(
        AcceptInviteCommand(user_id=5, code="ABCD2345")
    )
    assert calls == ["lock_active", "find_shop_id", "lock", "find_for_update"]


async def test_그_사이_탈퇴했거나_정지된_유저는_합류시키지_않는다():
    """F4 — 요청 시작 때의 인증 확인은 통과했지만, 잠근 뒤에 보니 활동할 수 없는 유저다."""
    calls = []
    invites, members = _StubInvites(_invite(), calls), _StubMembers(calls=calls)
    with pytest.raises(AccountUnavailableError):
        await _interactor(invites, members, users=_StubUserGuard(active=False, calls=calls)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert calls == ["lock_active"]
    assert members.added == [] and invites.used == []


async def test_시도_횟수는_유저_행을_잠그기_전에_센다():
    calls = []
    invites = _StubInvites(_invite(), calls)
    with pytest.raises(TooManyAttemptsError):
        await _interactor(invites, limiter=_StubLimiter(count=6), users=_StubUserGuard(calls=calls)).accept(
            AcceptInviteCommand(user_id=5, code="ABCD2345")
        )
    assert calls == []
```

`backend/apps/tenancy/tests/app/use_cases/test_accept_invite_locking.py`에서 `AcceptInviteInteractor`를 만드는 곳에 `users=` 인자를 더한다. 그 파일에 활동 중인 유저로 통과시키는 작은 스텁을 둔다.
```python
class _ActiveUser:
    async def lock_active(self, user_id):
        return True
```

`backend/tests/integration/test_accept_vs_withdraw_locking.py` (두 스포크의 실제 구현을 함께 쓰므로 스포크 밖에 둔다):
```python
"""F4 — 회원 탈퇴와 겹친 초대 수락이 소속을 되살리지 못한다. 실제 두 세션으로 확인한다."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from auth.adapter.outbound.pg.user_pg_repository import UserPgRepository
from auth.app.use_cases.guard_active_user_interactor import GuardActiveUserInteractor
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile
from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
from tenancy.app.dtos.accept_invite_dto import AcceptInviteCommand
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.domain.errors import AccountUnavailableError
from tenancy.domain.services.invite_code import hash_invite_code

pytestmark = pytest.mark.integration

EXPIRES = datetime.now(timezone.utc) + timedelta(days=7)


class _OpenLimiter:
    async def hit(self, user_id):
        return 1


def _accept(session, user_id):
    interactor = AcceptInviteInteractor(
        invites=InvitePgRepository(session), members=MemberPgRepository(session),
        shops=ShopPgRepository(session), limiter=_OpenLimiter(),
        users=GuardActiveUserInteractor(UserPgRepository(session)),
    )
    return interactor.accept(AcceptInviteCommand(user_id=user_id, code="ABCD2345"))


async def test_탈퇴가_유저_행을_쥔_동안_수락은_기다리고_탈퇴한_뒤에는_거절된다(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        user = await UserPgRepository(setup).create_with_identity(
            SocialProfile(Provider.DEV, "leaving", None, "떠나는 사람", None, None)
        )
        shop = await ShopPgRepository(setup).create("Hiss Haus", "pet_grooming")
        await InvitePgRepository(setup).create_owner_invite(shop.id, hash_invite_code("ABCD2345"), EXPIRES)
        await setup.commit()

    async with factory() as withdrawing, factory() as accepting:
        users = UserPgRepository(withdrawing)
        assert (await users.lock(user.id)).id == user.id   # 탈퇴가 맨 앞에서 하는 일
        await users.anonymize(user.id)

        # 같은 유저의 수락은 유저 행에서 기다린다 — 매장 행이나 초대 행까지 가지 못한다.
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(_accept(accepting, user.id), timeout=0.5)
        await accepting.rollback()

        await withdrawing.commit()
        with pytest.raises(AccountUnavailableError):
            await asyncio.wait_for(_accept(accepting, user.id), timeout=0.5)
        await accepting.rollback()

    async with factory() as check:
        members = (await check.execute(text("SELECT count(*) FROM shop_members"))).scalar_one()
        used = (await check.execute(text("SELECT used_count FROM shop_invites"))).scalar_one()
        assert (members, used) == (0, 0)
```

- [ ] **Step 3: 실패를 확인한다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_guard_active_user_interactor.py apps/tenancy/tests/app/use_cases/test_accept_invite_interactor.py apps/tenancy/tests/app/use_cases/test_accept_invite_locking.py tests/integration/test_accept_vs_withdraw_locking.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.use_cases.guard_active_user_interactor'`, `ImportError: cannot import name 'AccountUnavailableError'`, `TypeError: … unexpected keyword argument 'users'`

**두 세션 테스트의 판별력을 따로 확인한다.** 구현을 끝낸 뒤, 작업 트리에서만 `accept_invite_interactor.py`의 `lock_active` 호출 줄을 잠깐 지우고 `test_accept_vs_withdraw_locking.py`를 돌린다. `TimeoutError`가 나지 않아 실패해야 한다(수락이 유저 행에서 기다리지 않고 끝까지 가서 멤버가 된다). 출력을 보고서에 남기고 `git checkout -- <파일>`로 되돌린다.

- [ ] **Step 4: auth 쪽 슬라이스를 구현한다**

`backend/apps/auth/app/use_cases/guard_active_user_interactor.py`:
```python
from __future__ import annotations

from auth.app.ports.output.user_repository import UserRepository
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort


class GuardActiveUserInteractor(ActiveUserGuardPort):
    """허브의 ActiveUserGuardPort 구현. 입력 포트가 곧 허브 포트다."""

    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def lock_active(self, user_id: int) -> bool:
        user = await self._users.lock(user_id)
        return user is not None and not user.is_deleted and not user.is_suspended
```

`backend/apps/auth/dependencies/guard_active_user_provider.py`:
```python
from __future__ import annotations

from auth.app.use_cases.guard_active_user_interactor import GuardActiveUserInteractor
from auth.dependencies.auth_wiring import build_user_repository
from core.database import DbSession
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort


def get_guard_active_user_use_case(db: DbSession) -> ActiveUserGuardPort:
    return GuardActiveUserInteractor(users=build_user_repository(db))
```

- [ ] **Step 5: tenancy 쪽을 고친다**

`backend/apps/tenancy/domain/errors.py`의 끝에 더한다.
```python


class AccountUnavailableError(TenancyError):
    """요청 시작 때는 인증을 통과했지만, 유저 행을 잠근 뒤에 보니 탈퇴했거나 정지된 유저다."""

    code = "UNAUTHENTICATED"
```

`backend/apps/tenancy/adapter/inbound/api/error_map.py`의 import와 표에 더한다 (맨 위에 둔다).
```python
    AccountUnavailableError: 401,
```

`backend/apps/tenancy/dependencies/hub_ports.py`에 import와 자리를 더한다.
```python
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
```
```python
def get_active_user_guard() -> ActiveUserGuardPort:
    raise RuntimeError("ActiveUserGuardPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/tenancy/app/use_cases/accept_invite_interactor.py`에서 import, 생성자, `accept`의 앞부분을 고친다.
```python
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from tenancy.domain.errors import (
    AccountUnavailableError,
    InviteInvalidError,
    ShopClosedError,
    TooManyAttemptsError,
)
```
```python
    def __init__(
        self, invites: InviteRepository, members: MemberRepository, shops: ShopRepository,
        limiter: InviteAttemptLimiterPort, users: ActiveUserGuardPort,
        now: Callable[[], datetime] = _utcnow,
    ) -> None:
        self._invites = invites
        self._members = members
        self._shops = shops
        self._limiter = limiter
        self._users = users
        self._now = now
```
`accept`에서 시도 횟수 확인 다음, 초대 선조회 앞에 넣는다.
```python
        # 같은 유저의 회원 탈퇴와 겹치지 않게 유저 행을 먼저 잠근다 (잠금 순서: 유저 → 매장 → 멤버 → 초대).
        # 탈퇴가 먼저였다면 여기서 기다렸다가 탈퇴한 것을 보고 거절한다. 수락이 먼저였다면 탈퇴가 기다렸다가
        # 새 소속까지 정리한다. 이 확인이 없으면 탈퇴한 유저의 소속이 되살아난다.
        if not await self._users.lock_active(command.user_id):
            raise AccountUnavailableError("다시 로그인해 주세요.")
```

`backend/apps/tenancy/dependencies/accept_invite_provider.py` 전체:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.active_user_guard_port import ActiveUserGuardPort
from tenancy.app.ports.input.accept_invite_use_case import AcceptInviteUseCase
from tenancy.app.use_cases.accept_invite_interactor import AcceptInviteInteractor
from tenancy.dependencies.hub_ports import get_active_user_guard
from tenancy.dependencies.tenancy_wiring import (
    build_invite_attempt_limiter,
    build_invite_repository,
    build_member_repository,
    build_shop_repository,
)


def get_accept_invite_use_case(
    db: DbSession, users: ActiveUserGuardPort = Depends(get_active_user_guard)
) -> AcceptInviteUseCase:
    return AcceptInviteInteractor(
        invites=build_invite_repository(db),
        members=build_member_repository(db),
        shops=build_shop_repository(db),
        limiter=build_invite_attempt_limiter(),
        users=users,
    )
```

- [ ] **Step 6: 진입점에서 자리를 채운다**

`backend/main.py`의 import 묶음에 더한다 (같은 스포크끼리 붙여 둔다).
```python
from auth.dependencies.guard_active_user_provider import get_guard_active_user_use_case
from tenancy.dependencies.hub_ports import get_active_user_guard, get_user_directory
```
(`get_user_directory`만 import하던 기존 줄은 위 줄로 바꾼다.) 자리 채우기 묶음의 끝에 더한다.
```python
app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
```
구조 테스트(`tests/test_hub_port_binding.py`)가 새 자리를 자동으로 본다. 자리 채우기 줄을 잠깐 빼면 그 테스트가 실패하는 것을 한 번 확인하고 되돌린다.

- [ ] **Step 7: 통과를 확인한다**

Run: Step 3의 명령 → 전부 통과.
Run: 단위 테스트 전체, 통합 테스트 전체(특히 `tests/integration/test_shop_flow_wiring.py` — 실제 배선으로 수락이 계속 되는지), 구조 계약 → 전부 통과, `6 kept`.
Run: `bash ../backend/scripts/check_shop_flow.sh` → `전체 흐름 확인 완료`.

- [ ] **Step 8: 문서를 고친다**

`backend/apps/tenancy/_docs/CLAUDE.md`의 잠금 순서 항목을 바꾼다.
```markdown
- 잠금 순서는 언제나 유저 행 → 매장 행 → 멤버 행 → 초대 행이다. 여러 매장을 잠글 때는 매장 ID 오름차순으로 잠근다. 순서를 어기면 다른 경로와 교착한다.
- 소속을 새로 만드는 유스케이스(초대 수락)는 매장 행을 잠그기 전에 허브의 `ActiveUserGuardPort.lock_active`로 유저 행을 잠그고 활동 중인 유저인지 다시 본다. 이 확인이 없으면 회원 탈퇴와 겹친 수락이 탈퇴한 유저의 소속을 되살린다.
```

`backend/apps/hub/_docs/CLAUDE.md`의 표에 한 줄을 더한다.
```markdown
| `ActiveUserGuardPort.lock_active(user_id) → bool` | auth `guard_active_user` | tenancy `accept_invite` |
```

- [ ] **Step 9: 커밋**

```bash
git add backend/apps/hub backend/apps/auth backend/apps/tenancy backend/main.py backend/tests/integration/test_accept_vs_withdraw_locking.py
git commit -m "fix(tenancy): 초대 수락이 유저 행을 먼저 잠가 탈퇴와 겹친 합류를 막는다"
```

---

### Task 9: 로그인 수단 연결 (`POST /v1/auth/identities`)

로그인한 유저에 소셜 신원을 하나 더 붙인다. 로그인과 같은 방식으로 제공자에게 직접 검증한 신원만 붙인다(위협 G3). 제공자 검증은 외부 HTTP이므로 **잠금 전에** 끝내고, 그 뒤 유저 행을 잠가 탈퇴 여부를 다시 본다(위협 G2).

**Files:**
- Create: `backend/apps/auth/app/dtos/link_identity_dto.py`
- Create: `backend/apps/auth/app/ports/input/link_identity_use_case.py`
- Create: `backend/apps/auth/app/use_cases/link_identity_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/link_identity_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/link_identity_router.py`
- Create: `backend/apps/auth/dependencies/link_identity_provider.py`
- Modify: `backend/auth_main.py`
- Test: `backend/apps/auth/tests/app/use_cases/test_link_identity_interactor.py`, `backend/apps/auth/tests/adapter/test_link_identity_router.py`

**Interfaces:**
- Consumes: Task 8의 `UserRepository.lock`·`add_identity`·`list_identities`, Task 2의 `build_user_repository_with_cipher`, `build_provider_resolver`, `core.security.get_current_user_id`
- Produces:
  - `auth.app.dtos.link_identity_dto`: `LinkIdentityCommand(user_id: int, provider: str, token: str, authorization_code: str | None, nonce: str | None)`, `LinkedIdentities(identities: tuple[str, ...])`
  - `link_identity_router` — `POST /v1/auth/identities` → 200 `{"identities": ["kakao", "apple"]}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_link_identity_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.use_cases.link_identity_interactor import LinkIdentityInteractor
from auth.domain.entities.social_identity import SocialIdentity
from auth.domain.entities.user import User
from auth.domain.errors import (
    IdentityAlreadyLinkedError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_profile import SocialProfile


def _user(deleted=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None, suspended_at=None,
                deleted_at=datetime.now(timezone.utc) if deleted else None)


class _StubProvider:
    def __init__(self, calls):
        self.calls = calls
        self.seen = []

    async def verify(self, credentials):
        self.calls.append("verify")
        self.seen.append(credentials)
        return SocialProfile(Provider.APPLE, "apple-1", None, None, None, "apple-refresh")


class _StubResolver:
    def __init__(self, provider):
        self.provider = provider

    def resolve(self, provider):
        return self.provider


class _StubUsers:
    def __init__(self, calls, user, taken=False):
        self.calls = calls
        self.user = user
        self.taken = taken
        self.added = []

    async def lock(self, user_id):
        self.calls.append("lock")
        return self.user

    async def add_identity(self, user_id, profile):
        if self.taken:
            raise IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다.")
        self.added.append((user_id, profile.provider, profile.provider_user_id))

    async def list_identities(self, user_id):
        return [SocialIdentity(1, 5, Provider.KAKAO, "kakao-100", None),
                SocialIdentity(2, 5, Provider.APPLE, "apple-1", None)]


def _command(provider="apple"):
    return LinkIdentityCommand(user_id=5, provider=provider, token="apple-id-token",
                               authorization_code="auth-code", nonce="raw-nonce")


def _run(user=None, taken=False):
    calls = []
    provider, users = _StubProvider(calls), _StubUsers(calls, user if user is not None else _user(), taken)
    return LinkIdentityInteractor(_StubResolver(provider), users), provider, users, calls


async def test_제공자가_확인해_준_신원을_붙이고_수단_목록을_돌려준다():
    interactor, provider, users, _ = _run()
    result = await interactor.link(_command())
    assert users.added == [(5, Provider.APPLE, "apple-1")]
    assert result.identities == ("kakao", "apple")
    seen = provider.seen[0]
    assert (seen.token, seen.authorization_code, seen.nonce) == ("apple-id-token", "auth-code", "raw-nonce")


async def test_제공자_검증은_유저_행을_잠그기_전에_끝낸다():
    """잠금을 쥔 채 외부 HTTP 를 부르지 않는다."""
    interactor, _, _, calls = _run()
    await interactor.link(_command())
    assert calls == ["verify", "lock"]


async def test_잠근_뒤에_탈퇴한_유저면_붙이지_않는다():
    """G2 — 탈퇴와 겹친 연결이 탈퇴한 유저에 신원을 남기지 않는다."""
    interactor, _, users, _ = _run(user=_user(deleted=True))
    with pytest.raises(UserNotFoundError):
        await interactor.link(_command())
    assert users.added == []


async def test_다른_계정에_붙어_있는_신원은_거절한다():
    """G3"""
    interactor, _, _, _ = _run(taken=True)
    with pytest.raises(IdentityAlreadyLinkedError):
        await interactor.link(_command())


async def test_모르는_제공자_이름은_거절한다():
    interactor, _, _, calls = _run()
    with pytest.raises(UnsupportedProviderError):
        await interactor.link(_command(provider="naver"))
    assert calls == []
```

`backend/apps/auth/tests/adapter/test_link_identity_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.link_identity_router import link_identity_router
from auth.app.dtos.link_identity_dto import LinkedIdentities
from auth.dependencies.link_identity_provider import get_link_identity_use_case
from auth.domain.errors import IdentityAlreadyLinkedError
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def link(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return LinkedIdentities(identities=("kakao", "apple"))


async def _no_db():
    yield None


def _app(stub, user_id=5):
    app = FastAPI()
    app.include_router(link_identity_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_link_identity_use_case] = lambda: stub
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _post(app, body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/auth/identities", json=body)


async def test_연결하면_로그인_수단_목록을_돌려준다():
    stub = _StubUseCase()
    response = await _post(_app(stub), {"provider": "apple", "token": "id-token",
                                       "authorization_code": "code", "nonce": "raw"})
    assert (response.status_code, response.json()) == (200, {"identities": ["kakao", "apple"]})
    command = stub.commands[0]
    assert (command.user_id, command.provider, command.token) == (5, "apple", "id-token")
    assert (command.authorization_code, command.nonce) == ("code", "raw")


async def test_이미_다른_계정에_붙은_신원은_409_다():
    stub = _StubUseCase(IdentityAlreadyLinkedError("이미 다른 계정에 연결된 로그인 수단입니다."))
    response = await _post(_app(stub), {"provider": "kakao", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (409, "IDENTITY_ALREADY_LINKED")


async def test_토큰이_비면_422_다():
    response = await _post(_app(_StubUseCase()), {"provider": "kakao", "token": ""})
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")


async def test_로그인하지_않으면_401_이다():
    response = await _post(_app(_StubUseCase(), user_id=None), {"provider": "kakao", "token": "t"})
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_link_identity_interactor.py apps/auth/tests/adapter/test_link_identity_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.link_identity_dto'`

- [ ] **Step 3: 슬라이스를 구현한다**

`backend/apps/auth/app/dtos/link_identity_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LinkIdentityCommand:
    user_id: int
    provider: str
    token: str
    authorization_code: str | None
    nonce: str | None


@dataclass(frozen=True)
class LinkedIdentities:
    identities: tuple[str, ...]
```

`backend/apps/auth/app/ports/input/link_identity_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.link_identity_dto import LinkedIdentities, LinkIdentityCommand


class LinkIdentityUseCase(ABC):
    @abstractmethod
    async def link(self, command: LinkIdentityCommand) -> LinkedIdentities: ...
```

`backend/apps/auth/app/use_cases/link_identity_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.link_identity_dto import LinkedIdentities, LinkIdentityCommand
from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
from auth.app.ports.output.social_provider_resolver_port import SocialProviderResolverPort
from auth.app.ports.output.user_repository import UserRepository
from auth.domain.errors import UnsupportedProviderError, UserNotFoundError
from auth.domain.value_objects.provider import Provider
from auth.domain.value_objects.social_credentials import SocialCredentials


class LinkIdentityInteractor(LinkIdentityUseCase):
    def __init__(self, providers: SocialProviderResolverPort, users: UserRepository) -> None:
        self._providers = providers
        self._users = users

    async def link(self, command: LinkIdentityCommand) -> LinkedIdentities:
        try:
            provider = Provider(command.provider)
        except ValueError as exc:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.") from exc
        # 제공자 검증은 외부 HTTP 다. 유저 행을 잠그기 전에 끝낸다.
        profile = await self._providers.resolve(provider).verify(
            SocialCredentials(
                token=command.token,
                authorization_code=command.authorization_code,
                nonce=command.nonce,
            )
        )
        # 같은 유저의 해제·탈퇴와 겹치지 않게 잠그고, 그 사이 탈퇴했는지 다시 본다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError("다시 로그인해 주세요.")
        await self._users.add_identity(user.id, profile)
        identities = await self._users.list_identities(user.id)
        return LinkedIdentities(identities=tuple(i.provider.value for i in identities))
```

`backend/apps/auth/dependencies/link_identity_provider.py`:
```python
from __future__ import annotations

from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
from auth.app.use_cases.link_identity_interactor import LinkIdentityInteractor
from auth.dependencies.auth_wiring import build_provider_resolver, build_user_repository_with_cipher
from core.database import DbSession


def get_link_identity_use_case(db: DbSession) -> LinkIdentityUseCase:
    return LinkIdentityInteractor(
        providers=build_provider_resolver(), users=build_user_repository_with_cipher(db)
    )
```

`backend/apps/auth/adapter/inbound/api/schemas/link_identity_schema.py`:
```python
from pydantic import BaseModel, Field


class LinkIdentityRequestSchema(BaseModel):
    provider: str = Field(description="kakao · apple · google (개발 환경에서는 dev)")
    token: str = Field(min_length=1, description="제공자 SDK 가 준 토큰. dev 는 붙일 이름")
    authorization_code: str | None = Field(None, description="Apple 전용")
    nonce: str | None = Field(None, description="Apple 전용 — 앱이 만든 원본 nonce")


class IdentitiesResponseSchema(BaseModel):
    identities: list[str]
```

`backend/apps/auth/adapter/inbound/api/v1/link_identity_router.py`:
```python
from fastapi import APIRouter, Depends

from auth.adapter.inbound.api.schemas.link_identity_schema import (
    IdentitiesResponseSchema,
    LinkIdentityRequestSchema,
)
from auth.app.dtos.link_identity_dto import LinkIdentityCommand
from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
from auth.dependencies.link_identity_provider import get_link_identity_use_case
from core.security import get_current_user_id

link_identity_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@link_identity_router.post("/identities", response_model=IdentitiesResponseSchema)
async def link_identity(
    body: LinkIdentityRequestSchema,
    user_id: int = Depends(get_current_user_id),
    use_case: LinkIdentityUseCase = Depends(get_link_identity_use_case),
) -> IdentitiesResponseSchema:
    result = await use_case.link(
        LinkIdentityCommand(
            user_id=user_id,
            provider=body.provider,
            token=body.token,
            authorization_code=body.authorization_code,
            nonce=body.nonce,
        )
    )
    return IdentitiesResponseSchema(identities=list(result.identities))
```

- [ ] **Step 4: 인증 프로세스에 장착한다**

`backend/auth_main.py`의 라우터 import 묶음에 더하고(`auth_myself_router` 다음), `app.include_router(logout_router)` 다음 줄에 장착한다.
```python
from auth.adapter.inbound.api.v1.link_identity_router import link_identity_router
```
```python
app.include_router(link_identity_router)
```

- [ ] **Step 5: 통과를 확인한다**

Run: Step 2의 명령 → `9 passed`.
Run: 단위 테스트 전체, 통합 테스트 전체(`tests/integration/test_route_wiring.py`가 인증 프로세스의 새 라우트도 본다), 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/auth backend/auth_main.py
git commit -m "feat(auth): 로그인 수단 연결 슬라이스 POST /v1/auth/identities"
```

---

### Task 10: 로그인 수단 해제 (`DELETE /v1/auth/identities/{provider}`)

로그인 수단이 둘 이상일 때만 하나를 해제한다. 해제하면 **모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다**(위협 G5 — 해제한 수단으로 만든 세션이 다른 기기에 남지 않는다). 제공자 쪽 연결 끊기는 커밋 뒤 백그라운드 작업으로 한다(위협 H2).

응답의 새 토큰은 앱이 즉시 저장해야 한다(계획 3). 기존 리프레시 토큰은 이 요청 뒤로 무효다.

**Files:**
- Create: `backend/apps/auth/app/dtos/unlink_identity_dto.py`
- Create: `backend/apps/auth/app/ports/input/unlink_identity_use_case.py`
- Create: `backend/apps/auth/app/use_cases/unlink_identity_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/unlink_identity_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/unlink_identity_router.py`
- Create: `backend/apps/auth/dependencies/unlink_identity_provider.py`, `provider_revoker_provider.py`
- Modify: `backend/auth_main.py`
- Test: `backend/apps/auth/tests/app/use_cases/test_unlink_identity_interactor.py`, `backend/apps/auth/tests/adapter/test_unlink_identity_router.py`

**Interfaces:**
- Consumes: Task 8의 `lock`·`list_revocations`·`delete_identity`·`ensure_identity_remains`·`IdentityNotFoundError`, Task 1의 `RefreshTokenStorePort.revoke_all`·`SessionIssuer.issue`, Task 5의 `ProviderRevoker`·`build_provider_revoker`
- Produces:
  - `auth.app.dtos.unlink_identity_dto`: `UnlinkIdentityCommand(user_id: int, provider: str)`, `UnlinkIdentityResult(identities: tuple[str, ...], tokens: TokenPair, revocation: IdentityRevocation)`
  - `auth.dependencies.provider_revoker_provider.get_provider_revoker() -> ProviderRevoker`
  - `unlink_identity_router` — `DELETE /v1/auth/identities/{provider}` → 200 `{"identities", "access_token", "refresh_token", "token_type", "expires_in"}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_unlink_identity_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from auth.app.dtos.token_dto import TokenPair
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
from auth.app.use_cases.unlink_identity_interactor import UnlinkIdentityInteractor
from auth.domain.entities.user import User
from auth.domain.errors import (
    IdentityNotFoundError,
    LastIdentityError,
    UnsupportedProviderError,
    UserNotFoundError,
)
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider

KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)
APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")


def _user(deleted=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None, suspended_at=None,
                deleted_at=datetime.now(timezone.utc) if deleted else None)


class _StubUsers:
    def __init__(self, calls, revocations, user):
        self.calls = calls
        self.revocations = list(revocations)
        self.user = user

    async def lock(self, user_id):
        self.calls.append("lock")
        return self.user

    async def list_revocations(self, user_id):
        self.calls.append("list_revocations")
        return list(self.revocations)

    async def delete_identity(self, user_id, provider):
        self.calls.append(f"delete:{provider.value}")
        self.revocations = [r for r in self.revocations if r.provider is not provider]


class _StubStore:
    def __init__(self, calls):
        self.calls = calls

    async def revoke_all(self, user_id):
        self.calls.append("revoke_all")


class _StubSessions:
    def __init__(self, calls):
        self.calls = calls

    async def issue(self, user_id, generation=None):
        self.calls.append("issue")
        return TokenPair("new-access", "5.new-refresh", 900)


def _run(revocations=(KAKAO, APPLE), user=None):
    calls = []
    users = _StubUsers(calls, revocations, user if user is not None else _user())
    return UnlinkIdentityInteractor(users, _StubStore(calls), _StubSessions(calls)), calls


async def test_수단을_해제하면_모든_세션을_끊고_새_토큰과_끊을_신원을_돌려준다():
    """G5"""
    interactor, calls = _run()
    result = await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple"))
    assert calls == ["lock", "list_revocations", "delete:apple", "revoke_all", "issue"]
    assert result.identities == ("kakao",)
    assert result.tokens.refresh_token == "5.new-refresh"
    assert result.revocation == APPLE


async def test_마지막_로그인_수단은_해제할_수_없다():
    interactor, calls = _run(revocations=(KAKAO,))
    with pytest.raises(LastIdentityError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="kakao"))
    assert calls == ["lock", "list_revocations"]


async def test_연결되지_않은_수단은_IDENTITY_NOT_FOUND_다():
    interactor, calls = _run(revocations=(KAKAO, APPLE))
    with pytest.raises(IdentityNotFoundError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="google"))
    assert calls == ["lock", "list_revocations"]


async def test_모르는_제공자_이름은_거절한다():
    interactor, calls = _run()
    with pytest.raises(UnsupportedProviderError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="naver"))
    assert calls == []


async def test_잠근_뒤에_탈퇴한_유저면_아무것도_하지_않는다():
    interactor, calls = _run(user=_user(deleted=True))
    with pytest.raises(UserNotFoundError):
        await interactor.unlink(UnlinkIdentityCommand(user_id=5, provider="apple"))
    assert calls == ["lock"]
```

`backend/apps/auth/tests/adapter/test_unlink_identity_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.unlink_identity_router import unlink_identity_router
from auth.app.dtos.token_dto import TokenPair
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityResult
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.unlink_identity_provider import get_unlink_identity_use_case
from auth.domain.errors import LastIdentityError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id

APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def unlink(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return UnlinkIdentityResult(
            identities=("kakao",), tokens=TokenPair("new-access", "5.new-refresh", 900), revocation=APPLE
        )


class _StubRevoker:
    def __init__(self):
        self.revoked = []

    async def revoke_all(self, identities):
        self.revoked.extend(identities)


async def _no_db():
    yield None


def _app(stub, revoker, user_id=5):
    app = FastAPI()
    app.include_router(unlink_identity_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_unlink_identity_use_case] = lambda: stub
    app.dependency_overrides[get_provider_revoker] = lambda: revoker
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _delete(app, provider="apple"):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete(f"/v1/auth/identities/{provider}")


async def test_해제하면_남은_수단과_새_토큰을_돌려주고_제공자_연결을_끊는다():
    stub, revoker = _StubUseCase(), _StubRevoker()
    response = await _delete(_app(stub, revoker))
    assert response.status_code == 200
    assert response.json() == {
        "identities": ["kakao"], "access_token": "new-access", "refresh_token": "5.new-refresh",
        "token_type": "Bearer", "expires_in": 900,
    }
    assert (stub.commands[0].user_id, stub.commands[0].provider) == (5, "apple")
    assert revoker.revoked == [APPLE]


async def test_마지막_수단이면_409_이고_제공자_연결을_끊지_않는다():
    revoker = _StubRevoker()
    response = await _delete(_app(_StubUseCase(LastIdentityError("마지막 로그인 수단입니다.")), revoker))
    assert (response.status_code, response.json()["code"]) == (409, "LAST_IDENTITY")
    assert revoker.revoked == []


async def test_로그인하지_않으면_401_이다():
    response = await _delete(_app(_StubUseCase(), _StubRevoker(), user_id=None))
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_unlink_identity_interactor.py apps/auth/tests/adapter/test_unlink_identity_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.unlink_identity_dto'`

- [ ] **Step 3: 슬라이스를 구현한다**

`backend/apps/auth/app/dtos/unlink_identity_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from auth.app.dtos.token_dto import TokenPair
from auth.domain.value_objects.identity_revocation import IdentityRevocation


@dataclass(frozen=True)
class UnlinkIdentityCommand:
    user_id: int
    provider: str


@dataclass(frozen=True)
class UnlinkIdentityResult:
    identities: tuple[str, ...]
    tokens: TokenPair                # 모든 세션을 끊었으므로 요청한 기기가 쓸 새 토큰
    revocation: IdentityRevocation   # 커밋 뒤에 제공자 쪽 연결을 끊을 신원
```

`backend/apps/auth/app/ports/input/unlink_identity_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand, UnlinkIdentityResult


class UnlinkIdentityUseCase(ABC):
    @abstractmethod
    async def unlink(self, command: UnlinkIdentityCommand) -> UnlinkIdentityResult: ...
```

`backend/apps/auth/app/use_cases/unlink_identity_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand, UnlinkIdentityResult
from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.user_repository import UserRepository
from auth.app.services.session_issuer import SessionIssuer
from auth.domain.errors import IdentityNotFoundError, UnsupportedProviderError, UserNotFoundError
from auth.domain.services.identity_guard import ensure_identity_remains
from auth.domain.value_objects.provider import Provider


class UnlinkIdentityInteractor(UnlinkIdentityUseCase):
    def __init__(
        self, users: UserRepository, store: RefreshTokenStorePort, sessions: SessionIssuer
    ) -> None:
        self._users = users
        self._store = store
        self._sessions = sessions

    async def unlink(self, command: UnlinkIdentityCommand) -> UnlinkIdentityResult:
        try:
            provider = Provider(command.provider)
        except ValueError as exc:
            raise UnsupportedProviderError(f"{command.provider} 로그인은 지원하지 않습니다.") from exc
        # 서로 다른 수단의 해제가 동시에 와서 0개가 되지 않게, 유저 행을 잠근 뒤에 센다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            raise UserNotFoundError("다시 로그인해 주세요.")
        revocations = await self._users.list_revocations(user.id)
        target = next((r for r in revocations if r.provider is provider), None)
        if target is None:
            raise IdentityNotFoundError(f"{provider.value} 로그인은 연결되어 있지 않습니다.")
        ensure_identity_remains(len(revocations))
        await self._users.delete_identity(user.id, provider)
        # 해제한 수단으로 만든 세션이 다른 기기에 남지 않게 전부 끊고, 요청한 기기에만 새 토큰을 준다.
        await self._store.revoke_all(user.id)
        tokens = await self._sessions.issue(user.id)
        return UnlinkIdentityResult(
            identities=tuple(r.provider.value for r in revocations if r.provider is not provider),
            tokens=tokens,
            revocation=target,
        )
```

`backend/apps/auth/dependencies/provider_revoker_provider.py`:
```python
from __future__ import annotations

from auth.app.services.provider_revoker import ProviderRevoker
from auth.dependencies.auth_wiring import build_provider_revoker


def get_provider_revoker() -> ProviderRevoker:
    return build_provider_revoker()
```

`backend/apps/auth/dependencies/unlink_identity_provider.py`:
```python
from __future__ import annotations

from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
from auth.app.use_cases.unlink_identity_interactor import UnlinkIdentityInteractor
from auth.dependencies.auth_wiring import (
    build_refresh_store,
    build_session_issuer,
    build_user_repository_with_cipher,
)
from core.database import DbSession


def get_unlink_identity_use_case(db: DbSession) -> UnlinkIdentityUseCase:
    return UnlinkIdentityInteractor(
        users=build_user_repository_with_cipher(db),
        store=build_refresh_store(),
        sessions=build_session_issuer(),
    )
```

`backend/apps/auth/adapter/inbound/api/schemas/unlink_identity_schema.py`:
```python
from pydantic import BaseModel, Field


class UnlinkIdentityResponseSchema(BaseModel):
    identities: list[str]
    access_token: str = Field(description="모든 세션을 끊었다. 이 기기는 이 토큰으로 바꿔 쓴다.")
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
```

`backend/apps/auth/adapter/inbound/api/v1/unlink_identity_router.py`:
```python
from fastapi import APIRouter, BackgroundTasks, Depends

from auth.adapter.inbound.api.schemas.unlink_identity_schema import UnlinkIdentityResponseSchema
from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
from auth.app.services.provider_revoker import ProviderRevoker
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.unlink_identity_provider import get_unlink_identity_use_case
from core.security import get_current_user_id

unlink_identity_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@unlink_identity_router.delete(
    "/identities/{provider}", response_model=UnlinkIdentityResponseSchema
)
async def unlink_identity(
    provider: str,
    tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    use_case: UnlinkIdentityUseCase = Depends(get_unlink_identity_use_case),
    revoker: ProviderRevoker = Depends(get_provider_revoker),
) -> UnlinkIdentityResponseSchema:
    result = await use_case.unlink(UnlinkIdentityCommand(user_id=user_id, provider=provider))
    # 제공자 쪽 연결 끊기는 DB 커밋이 끝난 뒤에 돈다. 잠금을 쥔 채 외부 HTTP 를 부르지 않는다.
    tasks.add_task(revoker.revoke_all, [result.revocation])
    return UnlinkIdentityResponseSchema(
        identities=list(result.identities),
        access_token=result.tokens.access_token,
        refresh_token=result.tokens.refresh_token,
        expires_in=result.tokens.expires_in,
    )
```

- [ ] **Step 4: 인증 프로세스에 장착한다**

`backend/auth_main.py`의 라우터 import 묶음에 더하고(알파벳 순서대로 `social_login_router` 다음), `app.include_router(link_identity_router)` 다음 줄에 장착한다.
```python
from auth.adapter.inbound.api.v1.unlink_identity_router import unlink_identity_router
```
```python
app.include_router(unlink_identity_router)
```

- [ ] **Step 5: 통과를 확인한다**

Run: Step 2의 명령 → `8 passed`.
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/auth backend/auth_main.py
git commit -m "feat(auth): 로그인 수단 해제 슬라이스 — 해제하면 모든 세션을 끊고 새 토큰을 준다"
```

---

### Task 11: 회원 탈퇴 (`DELETE /v1/auth/account`)

설계 5.7절이다. 요청 하나의 트랜잭션 안에서 다음을 순서대로 한다. 어디서든 실패하면 전부 되돌아간다(위협 H1).

1. 유저 행을 잠그고 다시 읽는다. 이미 탈퇴했으면 아무것도 하지 않는다(위협 H5).
2. `MembershipLifecyclePort.apply_withdrawal` — 소속 해제, 필요하면 매장 닫기. 막히면 409로 끝나고 아무것도 바뀌지 않는다.
3. 제공자 쪽 연결을 끊는 데 필요한 것(신원, 복호화한 Apple 토큰)을 읽어 둔다.
4. 운영자 지정을 거둔다(위협 H4). 익명화한다. 신원을 모두 지운다(같은 소셜 계정으로 새로 가입할 수 있다).
5. 모든 세션을 폐기한다(세대 증가).

제공자 쪽 연결 끊기는 커밋 뒤 백그라운드 작업이다(위협 H2).

잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. tenancy의 다른 경로는 유저 행을 잠그지 않으므로 서로 교착하지 않는다.

이 슬라이스는 인증 프로세스에 있으므로 **`auth_main.py`가 처음으로 허브 포트 자리를 채운다.** tenancy의 도메인 오류(409)가 인증 프로세스에서도 HTTP로 바뀌도록 오류 표를 합친다. auth의 테스트는 tenancy를 import할 수 없으므로(스포크 상호 독립) 409 경로는 Task 12의 통합 테스트가 확인한다.

**Files:**
- Create: `backend/apps/auth/app/dtos/withdraw_dto.py`
- Create: `backend/apps/auth/app/ports/input/withdraw_use_case.py`
- Create: `backend/apps/auth/app/use_cases/withdraw_interactor.py`
- Create: `backend/apps/auth/adapter/inbound/api/schemas/withdraw_schema.py`
- Create: `backend/apps/auth/adapter/inbound/api/v1/withdraw_router.py`
- Create: `backend/apps/auth/dependencies/withdraw_provider.py`
- Modify: `backend/apps/auth/dependencies/hub_ports.py`, `backend/auth_main.py`
- Test: `backend/apps/auth/tests/app/use_cases/test_withdraw_interactor.py`, `backend/apps/auth/tests/adapter/test_withdraw_router.py`

**Interfaces:**
- Consumes: Task 7의 `MembershipLifecyclePort`·`get_apply_withdrawal_use_case`·`TENANCY_ERROR_STATUS`, Task 8의 `lock`·`list_revocations`·`anonymize`·`delete_identities`·`OperatorRepository.revoke`, Task 1의 `revoke_all`, Task 10의 `get_provider_revoker`
- Produces:
  - `auth.app.dtos.withdraw_dto`: `WithdrawCommand(user_id: int, confirm_close_shops: bool)`, `WithdrawResult(revocations: tuple[IdentityRevocation, ...])`
  - `auth.dependencies.hub_ports.get_membership_lifecycle() -> MembershipLifecyclePort` — 자리
  - `withdraw_router` — `DELETE /v1/auth/account` (본문 `{"confirm_close_shops": bool}`는 선택) → 204

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/app/use_cases/test_withdraw_interactor.py`:
```python
from datetime import datetime, timezone

import pytest

from auth.app.dtos.withdraw_dto import WithdrawCommand
from auth.app.use_cases.withdraw_interactor import WithdrawInteractor
from auth.domain.entities.user import User
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider

KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)
APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")


class _Blocked(Exception):
    """소속 정리가 막혔을 때 구현 쪽(tenancy)이 던지는 오류를 대신한다."""


def _user(deleted=False):
    return User(id=5, display_name="두부 보호자", profile_image_url=None, phone=None, suspended_at=None,
                deleted_at=datetime.now(timezone.utc) if deleted else None)


class _StubUsers:
    def __init__(self, calls, user):
        self.calls = calls
        self.user = user

    async def lock(self, user_id):
        self.calls.append("lock")
        return self.user

    async def list_revocations(self, user_id):
        self.calls.append("list_revocations")
        return [KAKAO, APPLE]

    async def anonymize(self, user_id):
        self.calls.append("anonymize")

    async def delete_identities(self, user_id):
        self.calls.append("delete_identities")


class _StubOperators:
    def __init__(self, calls):
        self.calls = calls

    async def revoke(self, user_id):
        self.calls.append("revoke_operator")


class _StubLifecycle:
    def __init__(self, calls, blocked=False):
        self.calls = calls
        self.blocked = blocked
        self.seen = []

    async def apply_withdrawal(self, user_id, close_sole_owned):
        self.calls.append("apply_withdrawal")
        self.seen.append((user_id, close_sole_owned))
        if self.blocked:
            raise _Blocked()


class _StubStore:
    def __init__(self, calls):
        self.calls = calls

    async def revoke_all(self, user_id):
        self.calls.append("revoke_all")


def _run(user="default", blocked=False):
    calls = []
    lifecycle = _StubLifecycle(calls, blocked)
    interactor = WithdrawInteractor(
        _StubUsers(calls, _user() if user == "default" else user),
        _StubOperators(calls), lifecycle, _StubStore(calls),
    )
    return interactor, lifecycle, calls


async def test_잠그고_소속을_정리한_뒤에_익명화하고_신원을_지우고_세션을_끊는다():
    interactor, lifecycle, calls = _run()
    result = await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=True))
    assert calls == [
        "lock", "apply_withdrawal", "list_revocations",
        "revoke_operator", "anonymize", "delete_identities", "revoke_all",
    ]
    assert lifecycle.seen == [(5, True)]
    # 신원을 지우기 전에 읽어 둔 것을 돌려준다. 커밋 뒤에 제공자 쪽 연결을 끊는 데 쓴다.
    assert result.revocations == (KAKAO, APPLE)


async def test_소속_정리가_막히면_계정은_건드리지_않는다():
    interactor, _, calls = _run(blocked=True)
    with pytest.raises(_Blocked):
        await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=False))
    assert calls == ["lock", "apply_withdrawal"]


async def test_이미_탈퇴한_유저면_아무것도_하지_않는다():
    """H5 — 같은 유저의 탈퇴가 동시에 두 번 와도 두 번째는 잠금 뒤에 조용히 끝난다."""
    for user in (_user(deleted=True), None):
        interactor, _, calls = _run(user=user)
        result = await interactor.withdraw(WithdrawCommand(user_id=5, confirm_close_shops=True))
        assert calls == ["lock"]
        assert result.revocations == ()
```

`backend/apps/auth/tests/adapter/test_withdraw_router.py`:
```python
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
from auth.adapter.inbound.api.v1.withdraw_router import withdraw_router
from auth.app.dtos.withdraw_dto import WithdrawResult
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.withdraw_provider import get_withdraw_use_case
from auth.domain.errors import UserNotFoundError
from auth.domain.value_objects.identity_revocation import IdentityRevocation
from auth.domain.value_objects.provider import Provider
from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id

KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def withdraw(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error
        return WithdrawResult(revocations=(KAKAO,))


class _StubRevoker:
    def __init__(self):
        self.revoked = []

    async def revoke_all(self, identities):
        self.revoked.extend(identities)


async def _no_db():
    yield None


def _app(stub, revoker, user_id=5):
    app = FastAPI()
    app.include_router(withdraw_router)
    install_error_handlers(app, AUTH_ERROR_STATUS)
    app.dependency_overrides[get_withdraw_use_case] = lambda: stub
    app.dependency_overrides[get_provider_revoker] = lambda: revoker
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    return app


async def _delete(app, body=None):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        if body is None:
            return await client.delete("/v1/auth/account")
        return await client.request("DELETE", "/v1/auth/account", json=body)


async def test_탈퇴하면_204_이고_제공자_연결을_끊는다():
    stub, revoker = _StubUseCase(), _StubRevoker()
    response = await _delete(_app(stub, revoker), {"confirm_close_shops": True})
    assert response.status_code == 204
    assert (stub.commands[0].user_id, stub.commands[0].confirm_close_shops) == (5, True)
    assert revoker.revoked == [KAKAO]


async def test_본문이_없으면_매장_닫기를_확인하지_않은_것으로_본다():
    stub = _StubUseCase()
    response = await _delete(_app(stub, _StubRevoker()))
    assert response.status_code == 204
    assert stub.commands[0].confirm_close_shops is False


async def test_탈퇴가_실패하면_제공자_연결을_끊지_않는다():
    revoker = _StubRevoker()
    response = await _delete(_app(_StubUseCase(UserNotFoundError("다시 로그인해 주세요.")), revoker))
    assert response.status_code == 401
    assert revoker.revoked == []


async def test_로그인하지_않으면_401_이다():
    response = await _delete(_app(_StubUseCase(), _StubRevoker(), user_id=None))
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```

- [ ] **Step 2: 실패를 확인한다**

Run: `docker compose run --rm backend pytest apps/auth/tests/app/use_cases/test_withdraw_interactor.py apps/auth/tests/adapter/test_withdraw_router.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth.app.dtos.withdraw_dto'`

- [ ] **Step 3: 슬라이스를 구현한다**

`backend/apps/auth/app/dtos/withdraw_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from auth.domain.value_objects.identity_revocation import IdentityRevocation


@dataclass(frozen=True)
class WithdrawCommand:
    user_id: int
    confirm_close_shops: bool


@dataclass(frozen=True)
class WithdrawResult:
    revocations: tuple[IdentityRevocation, ...]   # 커밋 뒤에 제공자 쪽 연결을 끊을 신원들
```

`backend/apps/auth/app/ports/input/withdraw_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from auth.app.dtos.withdraw_dto import WithdrawCommand, WithdrawResult


class WithdrawUseCase(ABC):
    @abstractmethod
    async def withdraw(self, command: WithdrawCommand) -> WithdrawResult: ...
```

`backend/apps/auth/app/use_cases/withdraw_interactor.py`:
```python
from __future__ import annotations

from auth.app.dtos.withdraw_dto import WithdrawCommand, WithdrawResult
from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
from auth.app.ports.output.operator_repository import OperatorRepository
from auth.app.ports.output.refresh_token_store_port import RefreshTokenStorePort
from auth.app.ports.output.user_repository import UserRepository
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort


class WithdrawInteractor(WithdrawUseCase):
    """탈퇴는 즉시 처리되고 되돌릴 수 없다. DB 변경은 요청 하나의 트랜잭션이라, 어디서든 실패하면
    전부 되돌아간다 — "익명화는 됐는데 신원은 남은" 중간 상태가 생기지 않는다."""

    def __init__(
        self, users: UserRepository, operators: OperatorRepository,
        lifecycle: MembershipLifecyclePort, store: RefreshTokenStorePort,
    ) -> None:
        self._users = users
        self._operators = operators
        self._lifecycle = lifecycle
        self._store = store

    async def withdraw(self, command: WithdrawCommand) -> WithdrawResult:
        # 같은 유저의 연결·해제·다른 탈퇴 요청과 겹치지 않게 잠그고 다시 읽는다.
        user = await self._users.lock(command.user_id)
        if user is None or user.is_deleted:
            return WithdrawResult(revocations=())
        # 소속을 먼저 정리한다. 혼자 사장인 매장 때문에 막히면 여기서 오류로 끝나고 아무것도 바뀌지 않는다.
        await self._lifecycle.apply_withdrawal(user.id, command.confirm_close_shops)
        # 신원을 지우기 전에, 제공자 쪽 연결을 끊는 데 필요한 것을 읽어 둔다.
        revocations = await self._users.list_revocations(user.id)
        await self._operators.revoke(user.id)
        await self._users.anonymize(user.id)
        await self._users.delete_identities(user.id)
        await self._store.revoke_all(user.id)
        return WithdrawResult(revocations=tuple(revocations))
```

`backend/apps/auth/dependencies/hub_ports.py`에 import와 자리를 더한다.
```python
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort
```
```python
def get_membership_lifecycle() -> MembershipLifecyclePort:
    raise RuntimeError("MembershipLifecyclePort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/auth/dependencies/withdraw_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
from auth.app.use_cases.withdraw_interactor import WithdrawInteractor
from auth.dependencies.auth_wiring import (
    build_operator_repository,
    build_refresh_store,
    build_user_repository_with_cipher,
)
from auth.dependencies.hub_ports import get_membership_lifecycle
from core.database import DbSession
from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort


def get_withdraw_use_case(
    db: DbSession, lifecycle: MembershipLifecyclePort = Depends(get_membership_lifecycle)
) -> WithdrawUseCase:
    return WithdrawInteractor(
        users=build_user_repository_with_cipher(db),
        operators=build_operator_repository(db),
        lifecycle=lifecycle,
        store=build_refresh_store(),
    )
```

`backend/apps/auth/adapter/inbound/api/schemas/withdraw_schema.py`:
```python
from pydantic import BaseModel, Field


class WithdrawRequestSchema(BaseModel):
    confirm_close_shops: bool = Field(
        False, description="혼자 사장이고 멤버가 본인뿐인 매장을 함께 닫는 데 동의한다."
    )
```

`backend/apps/auth/adapter/inbound/api/v1/withdraw_router.py`:
```python
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status

from auth.adapter.inbound.api.schemas.withdraw_schema import WithdrawRequestSchema
from auth.app.dtos.withdraw_dto import WithdrawCommand
from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
from auth.app.services.provider_revoker import ProviderRevoker
from auth.dependencies.provider_revoker_provider import get_provider_revoker
from auth.dependencies.withdraw_provider import get_withdraw_use_case
from core.security import get_current_user_id

withdraw_router = APIRouter(prefix="/v1/auth", tags=["auth"])


@withdraw_router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def withdraw(
    tasks: BackgroundTasks,
    body: WithdrawRequestSchema | None = None,
    user_id: int = Depends(get_current_user_id),
    use_case: WithdrawUseCase = Depends(get_withdraw_use_case),
    revoker: ProviderRevoker = Depends(get_provider_revoker),
) -> Response:
    result = await use_case.withdraw(
        WithdrawCommand(
            user_id=user_id,
            confirm_close_shops=body.confirm_close_shops if body else False,
        )
    )
    # 제공자 쪽 연결 끊기는 DB 커밋이 끝난 뒤에 돈다. 실패해도 탈퇴는 이미 끝났다 (로그만 남는다).
    tasks.add_task(revoker.revoke_all, list(result.revocations))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

(`Response`를 직접 돌려줘도 FastAPI가 주입받은 `BackgroundTasks`를 그 응답에 붙여 준다. 본문 없는 `DELETE`와 본문 있는 `DELETE` 모두에서 백그라운드 작업이 도는 것을 실험으로 확인했다.)

- [ ] **Step 4: 인증 프로세스에 장착하고 자리를 채운다**

`backend/auth_main.py`에서 세 곳을 고친다.

(1) import 묶음에 더한다.
```python
from auth.adapter.inbound.api.v1.withdraw_router import withdraw_router
from auth.dependencies.hub_ports import get_membership_lifecycle
from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
from tenancy.dependencies.apply_withdrawal_provider import get_apply_withdrawal_use_case
```
(2) `app.include_router(unlink_identity_router)` 다음 줄에 장착하고, 오류 핸들러 설치를 바꾼다.
```python
app.include_router(withdraw_router)
# 탈퇴가 tenancy 의 소속 정리를 부른다. 그쪽 도메인 오류(409)도 이 프로세스에서 HTTP 로 바뀌어야 한다.
install_error_handlers(app, {**AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS})
```
(3) 그 아래에 자리 채우기를 더한다.
```python

# 허브 포트 조립 — 스포크끼리는 서로를 모른다. 소비하는 쪽의 "자리"에 구현하는 쪽의 프로바이더를 꽂는다.
app.dependency_overrides[get_membership_lifecycle] = get_apply_withdrawal_use_case
```
모듈 머리말의 첫 줄도 실제에 맞게 고친다.
```python
"""인증 프로세스 — JWT 개인키를 가진 유일한 프로세스. /v1/auth/* 만 맡는다.

회원 탈퇴가 소속을 정리해야 해서 tenancy 의 MembershipLifecyclePort 구현을 여기서 꽂는다.
"""
```

- [ ] **Step 5: 통과를 확인한다**

Run: Step 2의 명령 → `7 passed`.
Run: `docker compose run --rm backend pytest tests/integration/test_route_wiring.py -q -p no:cacheprovider` → `1 passed` (인증 프로세스에 빈 자리가 없다. 자리 채우기를 빼면 이 테스트가 실패하는 것을 한 번 확인하고 되돌린다.)
Run: 단위 테스트 전체, 통합 테스트 전체, 구조 계약 → 전부 통과, `6 kept`.

- [ ] **Step 6: 커밋**

```bash
git add backend/apps/auth backend/auth_main.py
git commit -m "feat(auth): 회원 탈퇴 슬라이스 DELETE /v1/auth/account"
```

---

### Task 12: 전체 흐름·위협 시나리오 통합 테스트, 확인 스크립트, 문서

위협 점검표의 시나리오를 실제 배선으로 돈다. 통합 테스트에서 쓸 수 있는 제공자는 `dev`뿐인데, 한 유저는 제공자마다 신원을 하나만 가지므로 두 번째 수단을 붙이려면 제공자가 하나 더 필요하다. 테스트용 가짜 카카오 전략을 제공자 목록에 끼워 넣는다(연결 끊기 호출도 기록한다).

**이 통합 테스트는 앞선 작업들이 만든 동작을 고정한다. 쓰자마자 통과해야 한다.** 실패하면 테스트를 고쳐서 맞추지 말고 원인을 조사한다. 앞 작업의 결함이면 그 슬라이스에서 가장 작게 고치고(그 슬라이스의 단위 테스트가 잡았어야 했다면 단위 테스트도 더한다) 보고에 적는다.

**Files:**
- Create: `backend/tests/integration/test_account_flow_wiring.py`
- Create: `backend/scripts/check_account_flow.sh`
- Create: `_docs/decisions/003-account-lifecycle.md`
- Modify: `backend/tests/integration/support.py`, `backend/tests/integration/conftest.py`, `backend/tests/integration/test_shop_flow_wiring.py`
- Modify: `backend/apps/auth/app/use_cases/auth_myself_interactor.py`, `backend/apps/auth/tests/app/use_cases/test_auth_myself_interactor.py`
- Modify: `backend/apps/auth/_docs/CLAUDE.md`, `backend/apps/hub/_docs/CLAUDE.md`, `_docs/harness.md`, `README.md`, `CLAUDE.md`
- Modify: `docs/superpowers/specs/2026-09-20-foundation-design.md`

**Interfaces:**
- Consumes: 앞선 모든 작업
- Produces (`backend/tests/integration/support.py`): `make_operator(wired, name="운영자") -> dict`, `open_shop(wired, operator, name="Hiss Haus") -> dict`, `accept_invite(wired, login, code) -> Response`, `shop_with_owner(wired, operator, shop_name, owner_name) -> tuple[int, dict]`, `staff_invite(wired, shop_id, owner) -> str`, `error_of(response) -> tuple[int, str]`, `class FakeKakaoStrategy`. 픽스처 `fake_kakao`(`conftest.py`).

- [ ] **Step 1: 통합 테스트 도우미를 한곳으로 모은다**

`backend/tests/integration/test_shop_flow_wiring.py`의 도우미(`_operator`, `_open_shop`, `_accept`, `_shop_with_owner`, `_staff_invite`, `_code`)를 새 테스트도 써야 한다. `backend/tests/integration/support.py`의 끝에 옮긴다 (import 묶음에 `from auth.app.ports.output.social_provider_port import SocialProviderPort`, `from auth.domain.value_objects.provider import Provider`, `from auth.domain.value_objects.social_profile import SocialProfile`도 더한다).
```python


async def make_operator(wired: Wired, name: str = "운영자") -> dict:
    login = await wired.login(name)
    await wired.execute("INSERT INTO platform_operators (user_id) VALUES (:id)", id=login["user_id"])
    return login


async def open_shop(wired: Wired, operator: dict, name: str = "Hiss Haus") -> dict:
    response = await wired.api.post(
        "/v1/platform/shops", json={"name": name}, headers=bearer(operator["access_token"])
    )
    assert response.status_code == 201, response.text
    return response.json()


async def accept_invite(wired: Wired, login: dict, code: str):
    return await wired.api.post(
        "/v1/invites/accept", json={"code": code}, headers=bearer(login["access_token"])
    )


async def shop_with_owner(wired: Wired, operator: dict, shop_name: str, owner_name: str):
    shop = await open_shop(wired, operator, shop_name)
    owner = await wired.login(owner_name)
    assert (await accept_invite(wired, owner, shop["owner_invite_code"])).status_code == 200
    return shop["shop_id"], owner


async def staff_invite(wired: Wired, shop_id: int, owner: dict) -> str:
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/invites", headers=bearer(owner["access_token"])
    )
    assert response.status_code == 201, response.text
    return response.json()["code"]


def error_of(response) -> tuple[int, str]:
    return (response.status_code, response.json()["code"])


class FakeKakaoStrategy(SocialProviderPort):
    """통합 테스트용 두 번째 제공자. 토큰으로 받은 이름을 그대로 카카오 신원으로 확인해 준다.

    한 유저는 제공자마다 신원을 하나만 가지므로, 연결·해제를 실제 배선으로 돌려면 dev 말고 하나가 더 필요하다.
    """

    def __init__(self) -> None:
        self.revoked: list[str] = []

    async def verify(self, credentials) -> SocialProfile:
        name = credentials.token.strip()
        return SocialProfile(Provider.KAKAO, f"kakao-{name.lower()}", None, name, None, None)

    async def revoke(self, identity) -> None:
        self.revoked.append(identity.provider_user_id)
```

`backend/tests/integration/test_shop_flow_wiring.py`에서 위 여섯 도우미의 정의를 지우고, import를 바꾼다. 테스트 본문은 고치지 않는다.
```python
from tests.integration.support import (
    accept_invite as _accept,
    bearer,
    error_of as _code,
    make_operator as _operator,
    open_shop as _open_shop,
    shop_with_owner as _shop_with_owner,
    staff_invite as _staff_invite,
)
```

`backend/tests/integration/conftest.py`의 끝에 픽스처를 더한다 (import 묶음에 `from tests.integration.support import FakeKakaoStrategy, Wired`로 고치고, `from auth.adapter.outbound.factory.social_provider_factory import SocialProviderFactory`, `from auth.adapter.outbound.strategy.dev_identity_strategy import DevIdentityStrategy`, `from auth.domain.value_objects.provider import Provider`도 더한다).
```python


@pytest.fixture
async def fake_kakao(wired, monkeypatch):
    """dev 와 가짜 카카오만 등록된 제공자 목록으로 바꾼다. 연결 끊기 호출이 fake.revoked 에 남는다."""
    from auth.dependencies import auth_wiring

    fake = FakeKakaoStrategy()
    monkeypatch.setattr(
        auth_wiring,
        "_resolver",
        SocialProviderFactory({Provider.DEV: DevIdentityStrategy(), Provider.KAKAO: fake}),
    )
    return fake
```

Run: `docker compose run --rm backend pytest tests/integration/test_shop_flow_wiring.py -q -p no:cacheprovider`
Expected: 옮기기 전과 같은 수가 통과한다.

- [ ] **Step 2: 계정 흐름 통합 테스트를 쓴다**

`backend/tests/integration/test_account_flow_wiring.py`:
```python
"""로그인 수단 연결·해제와 회원 탈퇴를 실제 배선으로 확인한다. 위협 점검표의 시나리오를 그대로 돈다."""
import asyncio

import pytest
from sqlalchemy import text

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    open_shop,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration


async def _link_kakao(wired, login, kakao_name):
    return await wired.auth.post(
        "/v1/auth/identities", json={"provider": "kakao", "token": kakao_name},
        headers=bearer(login["access_token"]),
    )


async def _kakao_login(wired, kakao_name):
    response = await wired.auth.post("/v1/auth/social", json={"provider": "kakao", "token": kakao_name})
    assert response.status_code == 200, response.text
    return response.json()


async def _unlink(wired, login, provider):
    return await wired.auth.delete(f"/v1/auth/identities/{provider}", headers=bearer(login["access_token"]))


async def _withdraw(wired, login, confirm=None):
    body = None if confirm is None else {"confirm_close_shops": confirm}
    return await wired.auth.request(
        "DELETE", "/v1/auth/account", json=body, headers=bearer(login["access_token"])
    )


async def _refresh(wired, token):
    return await wired.auth.post("/v1/auth/refresh", json={"refresh_token": token})


async def _me(wired, login):
    return await wired.api.get("/v1/me", headers=bearer(login["access_token"]))


async def _scalar(wired, sql, **params):
    async with wired.engine.connect() as conn:
        return (await conn.execute(text(sql), params)).scalar()


async def test_수단을_붙이면_그_수단으로도_같은_계정에_로그인된다(wired, fake_kakao):
    login = await wired.login("두부보호자")
    linked = await _link_kakao(wired, login, "DubuKakao")
    assert (linked.status_code, linked.json()) == (200, {"identities": ["dev", "kakao"]})
    assert (await _me(wired, login)).json()["identities"] == ["dev", "kakao"]

    via_kakao = await _kakao_login(wired, "DubuKakao")
    assert (via_kakao["user_id"], via_kakao["is_new_user"]) == (login["user_id"], False)


async def test_남의_소셜_계정과_같은_제공자의_두_번째_계정은_붙일_수_없다(wired, fake_kakao):
    """G3·G4"""
    owner_of_kakao = await _kakao_login(wired, "TakenKakao")
    me = await wired.login("두부보호자")
    assert error_of(await _link_kakao(wired, me, "TakenKakao")) == (409, "IDENTITY_ALREADY_LINKED")
    assert (await _link_kakao(wired, me, "MyKakao")).status_code == 200
    assert error_of(await _link_kakao(wired, me, "AnotherKakao")) == (409, "PROVIDER_ALREADY_LINKED")
    # 남의 계정은 그대로다.
    assert (await _kakao_login(wired, "TakenKakao"))["user_id"] == owner_of_kakao["user_id"]


async def test_수단을_해제하면_다른_기기의_세션이_끊기고_그_수단은_새_계정이_된다(wired, fake_kakao):
    """G5"""
    phone = await wired.login("두부보호자")
    assert (await _link_kakao(wired, phone, "DubuKakao")).status_code == 200
    tablet = await _kakao_login(wired, "DubuKakao")   # 해제할 수단으로 만든 다른 기기의 세션

    unlinked = await _unlink(wired, phone, "kakao")
    assert unlinked.status_code == 200
    body = unlinked.json()
    assert body["identities"] == ["dev"]
    assert fake_kakao.revoked == ["kakao-dubukakao"]   # 커밋 뒤에 제공자 쪽 연결을 끊었다

    assert (await _refresh(wired, tablet["refresh_token"])).status_code == 401
    assert (await _refresh(wired, phone["refresh_token"])).status_code == 401
    assert (await _refresh(wired, body["refresh_token"])).status_code == 200   # 요청한 기기의 새 토큰만 산다

    again = await _kakao_login(wired, "DubuKakao")
    assert again["is_new_user"] is True and again["user_id"] != phone["user_id"]


async def test_마지막_수단과_연결되지_않은_수단은_해제할_수_없다(wired, fake_kakao):
    login = await wired.login("두부보호자")
    assert error_of(await _unlink(wired, login, "dev")) == (409, "LAST_IDENTITY")
    assert error_of(await _unlink(wired, login, "kakao")) == (404, "IDENTITY_NOT_FOUND")
    assert error_of(await _unlink(wired, login, "naver")) == (400, "PROVIDER_NOT_SUPPORTED")


async def test_동시에_서로_다른_수단을_해제해도_하나는_남는다(wired, fake_kakao):
    """G1 — 유저 행 잠금이 없으면 둘 다 "수단이 둘"이라고 보고 둘 다 지운다."""
    login = await wired.login("두부보호자")
    assert (await _link_kakao(wired, login, "DubuKakao")).status_code == 200
    first, second = await asyncio.gather(_unlink(wired, login, "dev"), _unlink(wired, login, "kakao"))
    assert sorted([first.status_code, second.status_code]) == [200, 409]
    count = await _scalar(wired, "SELECT count(*) FROM social_identities WHERE user_id = :id", id=login["user_id"])
    assert count == 1


async def test_직원이_탈퇴하면_소속과_세션이_사라지고_같은_계정으로_새로_가입된다(wired, fake_kakao):
    """H3"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    assert (await _link_kakao(wired, staff, "StaffKakao")).status_code == 200

    assert (await _withdraw(wired, staff)).status_code == 204

    assert (await _me(wired, staff)).status_code == 401              # 이미 받은 액세스 토큰도 막힌다
    assert (await _refresh(wired, staff["refresh_token"])).status_code == 401
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    assert [m["display_name"] for m in members.json()] == ["사장님"]
    name = await _scalar(wired, "SELECT display_name FROM users WHERE id = :id", id=staff["user_id"])
    assert name == "탈퇴한 사용자"
    assert fake_kakao.revoked == ["kakao-staffkakao"]

    again = await wired.login("직원")
    assert again["is_new_user"] is True and again["user_id"] != staff["user_id"]
    assert (await _me(wired, again)).json()["shops"] == []


async def test_막힌_탈퇴는_아무것도_바꾸지_않는다(wired, fake_kakao):
    """H1 — 혼자 사장인 매장에 다른 멤버가 있으면 409 이고, 계정·소속·세션이 그대로다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200

    blocked = await _withdraw(wired, owner, confirm=True)
    assert error_of(blocked) == (409, "OWNERSHIP_TRANSFER_REQUIRED")
    assert "Hiss Haus" in blocked.json()["message"]

    me = await _me(wired, owner)
    assert me.status_code == 200
    assert me.json()["shops"] == [{"shop_id": shop_id, "shop_name": "Hiss Haus", "role": "owner"}]
    assert me.json()["identities"] == ["dev"]
    assert (await _refresh(wired, owner["refresh_token"])).status_code == 200
    assert fake_kakao.revoked == []

    # 사장 권한을 넘기면 풀린다.
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    staff_member_id = next(m["member_id"] for m in members.json() if m["role"] == "staff")
    promoted = await wired.api.patch(
        f"/v1/shops/{shop_id}/members/{staff_member_id}", json={"role": "owner"},
        headers=bearer(owner["access_token"]),
    )
    assert promoted.status_code == 200
    assert (await _withdraw(wired, owner)).status_code == 204


async def test_혼자뿐인_매장은_확인을_받고_함께_닫는다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")

    for confirm in (None, False):
        blocked = await _withdraw(wired, owner, confirm=confirm)
        assert error_of(blocked) == (409, "SHOP_CLOSE_CONFIRM_REQUIRED")
    assert await _scalar(wired, "SELECT closed_at FROM shops WHERE id = :id", id=shop_id) is None

    assert (await _withdraw(wired, owner, confirm=True)).status_code == 204
    assert await _scalar(wired, "SELECT closed_at FROM shops WHERE id = :id", id=shop_id) is not None


async def test_탈퇴한_사장이_만들어_둔_초대_코드는_쓸_수_없다(wired):
    """F2"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    co_owner = await wired.login("공동사장")
    assert (await accept_invite(wired, co_owner, await staff_invite(wired, shop_id, owner))).status_code == 200
    members = await wired.api.get(f"/v1/shops/{shop_id}/members", headers=bearer(owner["access_token"]))
    co_owner_member_id = next(m["member_id"] for m in members.json() if m["display_name"] == "공동사장")
    await wired.api.patch(f"/v1/shops/{shop_id}/members/{co_owner_member_id}", json={"role": "owner"},
                          headers=bearer(owner["access_token"]))
    left_behind = await staff_invite(wired, shop_id, co_owner)

    assert (await _withdraw(wired, co_owner)).status_code == 204

    newcomer = await wired.login("새사람")
    assert error_of(await accept_invite(wired, newcomer, left_behind)) == (400, "INVITE_INVALID")


async def test_탈퇴한_운영자의_지정은_남지_않는다(wired):
    """H4"""
    operator = await make_operator(wired)
    assert (await _withdraw(wired, operator)).status_code == 204
    count = await _scalar(wired, "SELECT count(*) FROM platform_operators WHERE user_id = :id", id=operator["user_id"])
    assert count == 0


async def test_같은_유저의_탈퇴가_동시에_와도_한_번만_처리된다(wired, fake_kakao):
    """H5 — 둘째 요청은 잠금 뒤에 이미 탈퇴한 것을 보고 조용히 끝나거나, 인증 단계에서 401 을 받는다."""
    login = await wired.login("두부보호자")
    assert (await _link_kakao(wired, login, "DubuKakao")).status_code == 200
    first, second = await asyncio.gather(_withdraw(wired, login), _withdraw(wired, login))
    assert {first.status_code, second.status_code} <= {204, 401}
    assert 204 in (first.status_code, second.status_code)
    assert fake_kakao.revoked == ["kakao-dubukakao"]   # 제공자 연결은 한 번만 끊는다


async def test_토큰_없는_계정_요청은_401_이다(wired):
    requests = [
        ("POST", "/v1/auth/identities", {"provider": "dev", "token": "x"}),
        ("DELETE", "/v1/auth/identities/dev", None),
        ("DELETE", "/v1/auth/account", None),
    ]
    for method, path, body in requests:
        response = await wired.auth.request(method, path, json=body)
        assert error_of(response) == (401, "UNAUTHENTICATED"), f"{method} {path}"
```

- [ ] **Step 3: 통과를 확인한다**

Run: `docker compose run --rm backend pytest tests/integration -q -p no:cacheprovider`
Expected: 전부 통과한다(새 테스트 12개 포함). 실패하면 테스트를 고치지 말고 원인을 조사한다.

- [ ] **Step 4: 게이트웨이를 거치는 확인 스크립트를 쓴다**

개발 환경에는 `dev` 제공자뿐이라 탈퇴 흐름만 확인한다.

`backend/scripts/check_account_flow.sh`:
```bash
#!/usr/bin/env bash
# 개발 환경에서 회원 탈퇴 → 접근 차단 → 같은 이름으로 새 가입을 게이트웨이를 거쳐 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_account_flow.sh
# 개발 DB 에 "탈퇴한 사용자" 행과 확인용 유저가 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
NAME="flow-account-$(date +%s)"

field() { python3 -c "import json,sys; print(json.load(sys.stdin)['$1'])"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

first=$(login "$NAME"); token=$(echo "$first" | field access_token); refresh=$(echo "$first" | field refresh_token)
first_id=$(echo "$first" | field user_id)

expect "같은 제공자를 또 붙일 수는 없다" "$(status POST /v1/auth/identities "$token" "{\"provider\":\"dev\",\"token\":\"$NAME-2\"}")" "409"
expect "마지막 로그인 수단은 해제할 수 없다" "$(status DELETE /v1/auth/identities/dev "$token")" "409"
expect "탈퇴는 204" "$(status DELETE /v1/auth/account "$token")" "204"
expect "탈퇴한 뒤에는 이미 받은 토큰으로도 내 정보를 볼 수 없다" "$(status GET /v1/me "$token")" "401"
expect "탈퇴한 뒤에는 리프레시 토큰도 쓸 수 없다" \
  "$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/v1/auth/refresh" -H 'Content-Type: application/json' -d "{\"refresh_token\":\"$refresh\"}")" "401"

again=$(login "$NAME")
expect "같은 이름으로 다시 로그인하면 새 유저다" "$(echo "$again" | field is_new_user)" "True"
if [ "$(echo "$again" | field user_id)" = "$first_id" ]; then echo "실패  탈퇴한 유저 ID 가 다시 쓰였다"; exit 1; fi
echo "통과  새 유저 ID 가 발급되었다"

echo "전체 흐름 확인 완료"
```

Run (`infra/`에서): `chmod +x ../backend/scripts/check_account_flow.sh && bash ../backend/scripts/check_auth_flow.sh && bash ../backend/scripts/check_shop_flow.sh && bash ../backend/scripts/check_account_flow.sh`
Expected: 세 스크립트 모두 마지막 줄이 `전체 흐름 확인 완료`다. (auth 서비스가 새 코드로 기동했는지 먼저 확인한다: `docker compose logs --tail 20 auth`. 개인키 외의 새 필수값 때문에 기동에 실패했다면 Task 2의 설명대로 `.env`에 `IDENTITY_TOKEN_ENC_KEY`가 남아 있는지 본다 — 파일 내용은 출력하지 않고 `grep -c`로 줄 수만 확인한다.)

- [ ] **Step 5: 라우트 표를 확인한다**

Run: `docker compose run --rm --no-deps auth python scripts/print_routes.py`
Expected: `backend` 줄은 계획 2-1과 같고, `auth` 줄에 세 개가 늘었다.
```
auth     DELETE  /v1/auth/account                             withdraw
auth     POST    /v1/auth/identities                          link_identity
auth     DELETE  /v1/auth/identities/{provider}               unlink_identity
```

- [ ] **Step 6: 자기소개와 앱 문서를 고친다**

`backend/apps/auth/app/use_cases/auth_myself_interactor.py`의 소개 문구에서 `"POST /v1/auth/logout 은 리프레시 토큰을 폐기합니다. "` 다음에 문장을 더한다.
```python
                "POST /v1/auth/identities 는 로그인한 계정에 로그인 수단을 하나 더 붙이고(제공자마다 하나), "
                "DELETE /v1/auth/identities/{provider} 는 해제하면서 모든 세션을 끊고 새 토큰을 돌려줍니다. "
                "마지막 로그인 수단은 해제할 수 없습니다. "
                "DELETE /v1/auth/account 는 회원 탈퇴입니다. 소속을 해제하고 계정을 익명화하고 신원을 지우며, "
                "혼자 사장인 매장에 다른 멤버가 있으면 409 로 막습니다. "
```
`backend/apps/auth/tests/app/use_cases/test_auth_myself_interactor.py`의 단언에 두 줄을 더한다.
```python
    assert "/v1/auth/identities" in result.introduction
    assert "/v1/auth/account" in result.introduction
```

`backend/apps/auth/_docs/CLAUDE.md`의 목록 끝에 더한다.
```markdown
- 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있다. 제공자 토큰을 저장·복호화하는 경로는 `build_user_repository_with_cipher`로, 읽기만 하는 경로는 `build_user_repository`로 조립한다.
- 한 유저는 제공자마다 신원을 하나만 가진다. 계정을 바꾸는 유스케이스(`link_identity`·`unlink_identity`·`withdraw`)는 맨 앞에서 `UserRepository.lock`으로 유저 행을 잠그고 탈퇴 여부를 다시 본다.
- 잠금을 쥔 채 외부 HTTP를 부르지 않는다. 제공자 검증은 잠금 전에, 제공자 쪽 연결 끊기는 커밋 뒤 백그라운드 작업(`ProviderRevoker`)으로 한다. 끊지 못해도 탈퇴·해제는 끝난 것이며 로그만 남긴다. 구글은 서버가 끊지 않는다(앱이 `disconnect()`를 부른다).
- 로그인 수단을 해제하면 모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다.
- 탈퇴의 DB 변경은 요청 하나의 트랜잭션이다. 소속 정리는 허브의 `MembershipLifecyclePort`(구현: tenancy)가 같은 세션에서 한다. 이 자리는 `auth_main.py`가 채운다.
```

`backend/apps/hub/_docs/CLAUDE.md`의 표에 한 줄을 더하고, 표 아래의 `MembershipLifecyclePort`(회원 탈퇴)는 계획 2-2에서 … 문장을 지운다.
```markdown
| `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy `apply_withdrawal` | auth `withdraw` (인증 프로세스) |
```

- [ ] **Step 7: 하네스 문서, README, 루트 CLAUDE.md를 고친다**

`_docs/harness.md`의 표에서 매장 흐름 줄 다음에 더한다.
```markdown
| 회원 탈퇴 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_account_flow.sh` — 개발 DB에 "탈퇴한 사용자" 행이 남는다 |
```
그리고 목록 끝에 더한다.
```markdown
- 권한이나 불변식이 걸린 슬라이스를 계획할 때는 악의적이거나 운 나쁜 시나리오(내보내진 사람이 쥔 것, 같은 요청이 동시에 두 번, 읽기와 쓰기 사이)를 먼저 표로 적고, 각각을 막는 코드와 테스트를 작업에 넣는다. 작업별 검토는 계획서와의 일치가 아니라 그 표를 기준으로 한다.
- 통합 테스트에서 두 번째 로그인 수단이 필요하면 `fake_kakao` 픽스처를 쓴다.
```

`README.md`의 "처음 띄우기" 코드 블록 끝에 한 줄을 더한다.
```
    bash ../backend/scripts/check_account_flow.sh                                   # 회원 탈퇴 흐름 확인
```

`CLAUDE.md`(루트)의 "꼭 지킬 것"에서 `JWT 개인키는 인증 프로세스(…)만 가진다. …` 줄을 바꾼다.
```markdown
- 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있고 인증 프로세스(`auth_main.py`)만 읽는다. 이 모듈은 함수 안에서만 import한다. API 프로세스 경로에서 import하지 않는다.
- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
```

- [ ] **Step 8: 설계 문서를 정정한다**

`docs/superpowers/specs/2026-09-20-foundation-design.md`에서 다음을 고친다. 다른 곳은 건드리지 않는다.

(1) 3.3절의 `.env.auth` 항목 첫 문장 `` `.env.auth`는 JWT 개인키(`JWT_PRIVATE_KEY_B64`) 전용이다. ``를 바꾼다.
```markdown
`.env.auth`는 인증 프로세스 전용 비밀값(`JWT_PRIVATE_KEY_B64`, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)을 담는다. 코드에서는 `core/auth_config.py`만 이 값들을 읽는다.
```

(2) 4.6절 표의 `MembershipLifecyclePort` 줄을 바꾼다.
```markdown
| `MembershipLifecyclePort.apply_withdrawal(user_id, close_sole_owned)` | tenancy | auth (`withdraw`, 인증 프로세스) | 소속 해제와 매장 닫기. 미리 조회하는 메서드는 두지 않는다 — 조회와 적용 사이에 사장 수가 바뀔 수 있어서, 적용이 매장 행을 잠근 뒤 스스로 확인하고 409로 막는다. |
```

(3) 5.2절 표의 `social_identities` 줄 끝 `` — (`provider`, `provider_user_id`) 유일 ``을 바꾼다.
```markdown
 — (`provider`, `provider_user_id`) 유일, (`user_id`, `provider`) 유일(한 유저는 제공자마다 하나)
```
같은 표의 Redis 줄을 바꾼다.
```markdown
| auth | Redis | `auth:refresh:{해시}` → 발급 시점의 세대 (30일), `auth:refresh:used:{해시}` → 쓸 때의 세대, `auth:refresh:gen:{user_id}` → 현재 세대. 토큰은 `{user_id}.{난수}` 모양이고 원문은 저장하지 않는다. |
```

(4) 5.3절의 리프레시 토큰 항목(`리프레시 토큰은 30일이고, …`) 끝에 문장을 더한다.
```markdown
 "모든 세션 폐기"는 유저의 세대를 하나 올리는 것이다. 토큰에 발급 시점의 세대가 찍혀 있어, 폐기와 동시에 발급되던 토큰도 함께 무효가 된다.
```

(5) 5.6절의 목록 끝에 두 항목을 더한다.
```markdown
- 한 유저는 제공자마다 신원을 하나만 가진다. 같은 제공자의 두 번째 계정은 409(`PROVIDER_ALREADY_LINKED`)다.
- 해제하면 모든 세션을 폐기하고, 요청한 기기에만 새 토큰을 응답으로 돌려준다. 해제한 수단으로 만든 세션이 다른 기기에 남지 않게 하려는 것이다.
```
같은 절의 `해제할 때 제공자 쪽 연결도 끊는다(`revoke`).`를 바꾼다.
```markdown
해제한 뒤(커밋 뒤) 제공자 쪽 연결도 끊는다(`revoke`). 구글은 서버가 끊지 않고 앱이 `disconnect()`를 부른다.
```

(6) 5.7절의 번호 목록(1~7)을 통째로 바꾼다.
```markdown
1. auth가 유저 행을 잠그고 다시 읽는다. 이미 탈퇴했으면 아무것도 하지 않는다.
2. auth가 `MembershipLifecyclePort.apply_withdrawal`을 부른다. tenancy는 매장마다 행을 잠근 뒤 판단한다.
   - **혼자 사장인 매장에 다른 멤버가 있으면** 409(`OWNERSHIP_TRANSFER_REQUIRED`)로 막고 "사장 권한을 먼저 넘겨 주세요"라고 안내한다. 역할 변경으로 다른 멤버를 사장으로 만들면 풀린다.
   - **혼자 사장인 매장에 멤버가 본인뿐이면** `confirm_close_shops`가 참일 때만 진행한다. 아니면 409(`SHOP_CLOSE_CONFIRM_REQUIRED`)다. 진행하면 매장에 `closed_at`을 기록한다.
   - 그 밖에는 소속을 해제하고, 그 멤버가 만든 미사용 초대를 무효화한다.
3. auth가 운영자 지정을 거두고, 유저를 익명화한다. `display_name`은 "탈퇴한 사용자"로 바꾸고, 사진과 전화번호를 지우고, `deleted_at`을 기록한다.
4. 소셜 신원 행을 완전히 삭제한다. 같은 소셜 계정으로 새로 가입할 수 있다.
5. 모든 세션을 폐기한다.
6. 1~5는 요청 하나의 트랜잭션이다. 어디서든 실패하면 전부 되돌아간다.
7. 커밋이 끝난 뒤 제공자 쪽 연결을 끊는다(`revoke`): Apple은 저장해 둔 리프레시 토큰을 REST API로 폐기하고(App Store 5.1.1(v)), 카카오는 어드민 키로 연결을 끊는다. 구글은 서버에 폐기할 토큰이 없어 앱이 `disconnect()`를 부른다.
```
그 아래 문단의 `각 단계는 여러 번 실행해도 결과가 같게 만들어서, 중간에 실패해도 다시 시도하면 끝까지 완료된다.`를 바꾼다.
```markdown
DB 변경이 한 트랜잭션이라 중간 상태가 남지 않는다. 같은 유저의 탈퇴가 동시에 두 번 와도 한 번만 처리된다.
```

(7) 7절의 "주요 코드"에서 `` `IDENTITY_ALREADY_LINKED`·`LAST_IDENTITY` ``를 `` `IDENTITY_ALREADY_LINKED`·`PROVIDER_ALREADY_LINKED`·`LAST_IDENTITY` ``로 바꾸고, `` `MEMBER_NOT_FOUND`(404) ``를 `` `MEMBER_NOT_FOUND`·`IDENTITY_NOT_FOUND`(404) ``로 바꾼다.

- [ ] **Step 9: 결정 기록을 남긴다**

`_docs/decisions/003-account-lifecycle.md`:
```markdown
# 003 — 계정 연결·해제와 회원 탈퇴에서 내린 결정

- 날짜: 2026-09-21
- 근거: 계획 2-2 작성 중 사용자 결정, 계획 2-1 최종 검토의 교훈

## 구글 연결 끊기는 앱이 한다 (사용자 결정)

탈퇴·해제 때 Apple은 서버가 REST API로 리프레시 토큰을 폐기하고(App Store 심사 가이드라인 5.1.1(v) 필수), 카카오는 서버가 어드민 키로 연결을 끊는다. 구글은 서버가 ID 토큰만 검증하고 구글 토큰을 저장하지 않아 폐기할 것이 없다. 구글 공식 문서가 모바일 앱에 안내하는 경로대로 앱이 `google_sign_in`의 `disconnect()`를 부른다(계획 3). 검토한 다른 안: 요청 본문으로 구글 액세스 토큰을 받아 서버가 폐기(토큰이 없으면 어차피 못 끊고 API가 제공자별로 달라진다), 구글 리프레시 토큰을 저장(로그인 흐름·구글 콘솔 설정·저장 민감 정보가 늘어난다).

## `MembershipLifecyclePort`에 미리 조회하는 메서드를 두지 않는다

설계는 `check_withdrawal`로 영향을 조회한 뒤 `apply_withdrawal`을 부르게 했다. 조회와 적용 사이에 다른 요청이 사장 수를 바꿀 수 있어서(계획 2-1 최종 검토에서 같은 모양의 경합이 실제로 재현됐다) 적용이 매장 행을 잠근 뒤 스스로 확인하고 409로 막는다. 앱은 확인 없이 먼저 부르고, `SHOP_CLOSE_CONFIRM_REQUIRED`를 받으면 메시지(매장 이름 포함)를 보여 주고 확인을 받아 다시 부른다.

## 제공자 쪽 연결 끊기는 커밋 뒤에 한다

탈퇴는 유저 행과 매장 행을 잠근다. 그 상태로 외부 HTTP(최대 5초 × 신원 수)를 부르면 같은 매장의 멤버십 변경이 그동안 멈춘다. FastAPI의 백그라운드 작업은 function 스코프의 DB 세션이 커밋된 뒤에 돈다(실험으로 확인). 끊지 못하면 로그만 남긴다. 프로세스가 커밋과 연결 끊기 사이에 죽으면 제공자 쪽 연결이 남는데, 설계가 이미 "연결 끊기가 실패해도 탈퇴는 완료한다"고 정한 범위 안이다.

## 로그인 수단을 해제하면 모든 세션을 끊는다

해제한 수단으로 만든 세션이 다른 기기에 최대 30일 남는 것을 막는다. 요청한 기기는 응답의 새 토큰으로 이어 간다.

## 한 유저는 제공자마다 신원 하나

`DELETE /v1/auth/identities/{provider}`가 성립하려면 필요하다. 유일 제약 `(user_id, provider)`로 강제한다.

## 리프레시 토큰의 세대

토큰을 `{user_id}.{난수}`로 만들고 값에 발급 시점의 세대를 찍는다. "모든 세션 폐기"는 세대 증가 한 번이다. 갱신은 꺼낼 때 받은 세대로 새 토큰을 저장하므로 그 사이 폐기가 끼어들면 새 토큰도 무효다. 폐기된 세대의 옛 토큰을 다시 보내는 것은 재사용 신호로 보지 않는다(그러지 않으면 옛 토큰 하나로 재로그인한 세션을 계속 끊을 수 있다). 유저별 토큰 집합은 없앴다.

## 001·002의 넘김 항목 처리 현황 (계획 2-2 종료 시점)

| 항목 | 처리 |
|---|---|
| 001-5 세대 번호, 001-20 `decode_responses` 전제 | Task 1 (전제는 저장소 docstring에 명시) |
| 001-6 암호화 키 이동, 001-10 HTTP 클라이언트 수명 | Task 2 |
| 001-7 동시 가입, 001-9 Apple 토큰 보완 | Task 3 |
| 001-8 `is_deleted` 로그인 차단 | 코드 없이 해소 — 탈퇴가 한 트랜잭션이라 그 상태가 생기지 않는다 |
| 001-18·19·21·22 | Task 4 |
| 001-23 테스트 보강 | Task 2(`get`), Task 8(신원 순서) |
| 002 내보내기·강등과 초대 수락의 이론적 교착 | Task 6 — 수락도 매장 행을 먼저 잠근다 |
| 002 "탈퇴는 `lock_membership_changes`를 부르고 초대를 무효화해야 한다" | Task 7 |
| 001-13~17 | 운영 전환 때 |

## 계획 2-2에서 새로 미룬 것

- **민감한 작업 앞의 재인증.** 세션을 훔친 공격자가 자기 소셜 계정을 피해자 계정에 붙이는 것은 지금 막지 못한다. 연결·해제·탈퇴 앞에 "방금 로그인했는가"를 확인하는 장치가 필요하다. 앱 흐름과 함께 정한다.
- **연결 끊기 실패의 재시도.** 지금은 로그만 남긴다. 실패가 잦으면 재시도 큐를 둔다.
- **`auth:refresh:gen:{user_id}`에는 만료가 없다.** 세션 폐기를 한 번이라도 겪은 유저마다 작은 키 하나가 남는다.
- **닫힌 매장의 데이터 파기.** 설계대로 ④ 이후의 운영자 기능이다.
```

- [ ] **Step 10: 최종 검증**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend alembic current
```
Expected: 두 pytest 실행이 모두 실패 0으로 끝난다. `Contracts: 6 kept, 0 broken.` `alembic current`는 `0004 (head)`.

- [ ] **Step 11: 커밋**

```bash
git add backend/tests/integration backend/scripts/check_account_flow.sh backend/apps/auth backend/apps/hub/_docs _docs README.md CLAUDE.md docs/superpowers/specs/2026-09-20-foundation-design.md
git commit -m "test(auth): 계정 연결·해제·탈퇴의 위협 시나리오 통합 테스트와 확인 스크립트, 문서 정리"
```

---

## 계획 3으로 넘기는 것

이 계획이 끝나면 설계 8.4절 완료 기준의 백엔드 몫(1~5번)이 모두 채워진다. Flutter 앱(계획 3)이 지켜야 할 것:

1. **구글 연결 끊기는 앱 몫이다.** 탈퇴(`204`)나 구글 수단 해제(`200`)가 성공한 뒤 `google_sign_in`의 `disconnect()`를 부른다. 실패해도 사용자에게 오류로 보이지 않는다.
2. **로그인 수단 해제의 응답에 새 토큰이 온다.** 받은 즉시 보안 저장소의 토큰을 바꾼다. 기존 리프레시 토큰은 그 요청 뒤로 무효다.
3. **탈퇴는 확인 없이 먼저 부른다.** `409 SHOP_CLOSE_CONFIRM_REQUIRED`면 응답의 `message`(매장 이름 포함)로 "매장도 함께 닫힙니다"를 확인받고 `confirm_close_shops: true`로 다시 부른다. `409 OWNERSHIP_TRANSFER_REQUIRED`면 멤버 관리 화면으로 안내한다.
4. **갱신 요청은 동시에 하나만 보내고, 응답을 받지 못한 갱신을 같은 토큰으로 자동 재시도하지 않는다**(결정 001-11). 세션이 끊기면 "보안을 위해 다시 로그인해 주세요"라고 이유를 알려 준다.
5. **리프레시 토큰의 모양(`{user_id}.{난수}`)에 기대지 않는다.** 앱에게는 불투명한 문자열이다.
