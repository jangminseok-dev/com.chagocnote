# ⑦-1 보호자 회원 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 보호자가 받은 알림장 링크로 자기 계정과 매장의 고객 카드를 잇고, 로그인해서 매장이 보낸 지난 알림장을 읽을 수 있게 하는 백엔드를 만든다.

**Architecture:** 새 스포크 `guardian` 이 연결(`guardian_links`)과 잇기·끊기를 소유한다. 알림장 읽기는 `visit` 이 소유한 채 보호자용 경로를 더한다. 둘은 허브 포트 셋(`ReportLinkPort`·`GuardianAccessPort`·`GuardianLifecyclePort`)으로만 만난다. 웹 로그인을 위해 `auth` 의 소셜 로그인에 "웹 세션"(30분 액세스 토큰, 리프레시 없음)을 더한다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0 asyncio · Alembic · Redis · pytest. 전부 `infra/` 에서 docker compose 로 돌린다.

**Spec:** `docs/superpowers/specs/2026-11-13-guardian-design.md` (바탕: `2026-09-20-foundation-design.md` 4~5절, `2026-09-28-report-design.md`, `_docs/decisions/008-report.md`). 폴더·슬라이스 규칙은 `_docs/architecture.md`, 새 스포크의 본보기는 `backend/apps/notification`.

## Global Constraints

- 주석·문서·테스트 이름·커밋 메시지는 한국어. 테스트를 먼저 쓰고 떨어지는 것을 본 뒤 구현한다.
- 스포크끼리 import 하지 않는다. `guardian` ↔ `visit`·`customer`·`auth` 는 허브 포트로만 만나고, 구현은 진입점(`main.py`·`auth_main.py`)이 꽂는다. 스포크의 `dependencies/hub_ports.py` 에 빈 자리를 둔다.
- 슬라이스는 1:1 이다(유스케이스마다 라우터·프로바이더·인터랙터·입력 포트·DTO·스키마). 새 스포크는 `/myself` 경로를 둔다(기존 스포크와 같은 모양).
- **`guardian` 은 `ShopContext` 를 만들지 않고 고객·반려동물을 읽지 않는다.** 보호자용 읽기(`visit`)는 `visit/app/services/public_context.py` 를 쓴다. 가드 없이 `ShopContext` 를 만드는 곳은 여전히 둘뿐이다.
- 알림장 토큰은 헤더 `X-Report-Token` 으로만 받고 로그·오류 본문·테스트 출력에 남기지 않는다.
- 보호자용 응답은 공개 알림장과 **같은 스키마**다. 새 알림장 스키마를 만들지 않는다. 매장용 응답은 연결 여부와 날짜뿐이다(보호자가 누구인지 주지 않는다).
- 로그인 없이 열리는 경로는 늘지 않는다(`tests/route_inspection.py` 의 허용 목록 불변).
- 매장 앱의 로그인(액세스 15분 + 리프레시 30일)은 바뀌지 않는다.
- 잠금 순서: 유저 행 → 매장 행 → 멤버 행 → 초대 행 → **보호자 연결 행**, 고객 행 → 방문 행 → 알림 행 / 고객 행 → **보호자 연결 행**. 잠금을 쥔 채 외부 HTTP 를 부르지 않는다.
- 커밋은 `feat/guardian-7-1-backend` 브랜치에 작업마다 하나. 푸시·병합은 사용자가 요청할 때. 외부 서비스에 붙지 않는다(로컬 Docker 만).
- 명령(`infra/` 에서): 단위 `docker compose run --rm backend pytest <경로> -q -p no:cacheprovider -m "not integration and not network"`, 통합은 `-m integration`. 통합 테스트 두 세션을 동시에 돌리지 않는다.

## 이 계획이 정한 것

1. 웹 세션 표시는 소셜 로그인 본문의 `session: "web"` 이다. 그때 응답의 `refresh_token` 은 `null`, `expires_in` 은 1800. `WEB_ACCESS_TOKEN_TTL_SECONDS = 30 * 60` 은 `core/config.py` 에 둔다.
2. 지난 알림장 목록의 쪽 나눔은 `cursor`(불투명 글자 — 마지막 줄의 방문 시작 시각과 방문 ID), 한 쪽 20개, 응답 `{items, next_cursor}`.
3. `report_id` 는 `visit_reports.id` 다.
4. 잇기 횟수 제한은 계정당 시간당 10회(Redis, `notification` 의 온보딩 제한기와 같은 방식 — Redis 에 닿지 못하면 통과).
5. 매장이 끊기(`DELETE …/guardian-link`)는 `customer:write`, 보호자가 끊은 뒤 같은 링크로 다시 이을 수 있다(새 줄).
6. 정지·폐업한 매장의 연결은 목록에서 빼고(`ShopProfilePort.public_profile` 의 `open`), 그 연결의 읽기는 빈 목록·404 다.

## Review Focus

1. 같은 계정이 이미 이은 카드를 다시 잇는다 / 끊은 뒤 다시 잇는다 — 앞은 200 으로 같은 `link_id`, 뒤는 201 로 새 `link_id` 이고 옛 줄은 끝난 채 남는다. → 작업 4.
2. 보호자만의 방문(반려동물 없음)의 알림장 — 목록에 `pet_id: null` 로 나오고 `…/pets` 에는 없으며 `?pet_id=` 로 거르면 빠진다. → 작업 8.
3. 매장이 알림장을 끊고 새로 보낸 방문 — 목록에 한 장(새 것)만 있고 옛 `report_id` 는 404. → 작업 8.
4. 탈퇴 직후 아직 살아 있는 웹 토큰(30분)으로 읽는다 — 연결이 끝나 404. 그 고객 카드는 다른 계정이 다시 이을 수 있다. → 작업 7.
5. 웹 세션으로 받은 응답의 `refresh_token` 이 null 인데 매장 앱 클라이언트가 같은 엔드포인트를 표시 없이 부른다 — 지금과 똑같은 응답(리프레시 포함, 900초). → 작업 1.

## File Structure

| 위치 | 일 |
|---|---|
| `backend/apps/hub/app/dtos/guardian.py`, `hub/app/ports/{report_link_port,guardian_access_port,guardian_lifecycle_port}.py` | 허브 DTO(`ReportLinkTarget`·`GuardianContext`)와 포트 셋 |
| `backend/apps/guardian/` (`domain`·`app`·`adapter`·`dependencies`·`tests`·`_docs/CLAUDE.md`) | 연결 엔티티, 잇기·목록·끊기(보호자·매장)·`/myself`, pg 저장소, Redis 제한기, 허브 포트 구현 둘 |
| `backend/alembic/versions/0014_guardian_links.py` | 표·CHECK·부분 유일 색인 |
| `backend/core/guardian_guard.py` | `get_guardian_context` 의존성 |
| `backend/apps/visit/…` | `ReportLinkPort` 구현, 보호자용 읽기 셋(반려동물·목록·한 장), 저장소 메서드 |
| `backend/apps/auth/…` | 웹 세션 로그인, 탈퇴가 `end_for_user` 를 부른다 |
| `backend/apps/customer/…` | 익명화가 `end_for_customer` 를 부른다 |
| `backend/main.py`, `auth_main.py`, `.importlinter`, `core/orm_registry.py`, `tests/…` | 조립과 구조 계약 |
| `backend/scripts/check_guardian_flow.sh`, 문서 | 흐름 확인, 결정 기록 010 |

---

### Task 0: 브랜치

- [ ] `git checkout -b feat/guardian-7-1-backend`. 설계서와 이 계획서를 `docs: ⑦ 보호자 회원 설계와 ⑦-1 백엔드 계획` 으로 커밋한다.

---

### Task 1: auth — 웹 세션 로그인

**Files:** `core/config.py`, `apps/auth/adapter/inbound/api/schemas/social_login_schema.py`, 소셜 로그인 라우터·DTO·인터랙터, `apps/auth/app/services/session_issuer.py`, `apps/auth/app/ports/output/token_issuer_port.py` 와 그 구현(`JwtTokenIssuer`), 해당 테스트 파일들.

**Interfaces — Produces:**

- 요청 `SocialLoginRequestSchema.session: Literal["web"] | None = None`.
- 응답 `TokenResponseSchema.refresh_token: str | None`.
- `TokenIssuerPort.issue_access(user_id, *, auth_time=None, fresh_login=False, ttl_seconds: int | None = None) -> AccessToken` — `ttl_seconds` 가 있으면 그 수명으로.
- `SessionIssuer.issue_web(user_id) -> TokenPair` — 액세스 토큰만(수명 `WEB_ACCESS_TOKEN_TTL_SECONDS`, `fresh_login=True`), `refresh_token=None`, 리프레시 저장소를 건드리지 않는다. `TokenPair.refresh_token: str | None`.

- [ ] **Step 1: 테스트**
  - 단위 `session_issuer`: `issue_web` 은 리프레시 저장소의 `save` 를 부르지 않고 `refresh_token is None`, `expires_in == 1800`.
  - 단위 `jwt_token_issuer`: `ttl_seconds=1800` 이면 `exp - iat == 1800`, 없으면 지금 값(900).
  - 단위 `social_login_interactor`: `session="web"` 이면 `issue_web`, 아니면 `issue`.
  - 라우터: `{"provider":"dev","token":"a","session":"web"}` → 200, `refresh_token is None`, `expires_in == 1800`. `session` 없이 → `refresh_token` 이 글자, `expires_in == 900`(Review Focus 5). `session: "app"` → 422.
  - 통합: 웹 세션 토큰으로 `GET /v1/me` 200.
- [ ] **Step 2~4:** 실패 확인 → 구현 → auth 단위·통합 전체 통과.
- [ ] **Step 5:** 커밋 `feat(auth): 웹 세션 로그인 — 30분 액세스 토큰, 리프레시 없음`

---

### Task 2: 허브 포트와 guardian 스포크의 뼈대

**Files:** 위 File Structure 의 hub·guardian(도메인·ORM·매퍼·저장소·`/myself`)·0014·`.importlinter`·`core/orm_registry.py`.

**Interfaces — Produces:**

```python
# hub/app/dtos/guardian.py
@dataclass(frozen=True)
class ReportLinkTarget: shop_id: int; customer_id: int; live: bool
@dataclass(frozen=True)
class GuardianContext: link_id: int; user_id: int; shop_id: int; customer_id: int

# hub/app/ports
class ReportLinkPort(ABC):
    async def resolve(self, token: str | None) -> ReportLinkTarget | None   # 우리가 만든 토큰이 아니면 None
class GuardianAccessPort(ABC):
    async def resolve(self, user_id: int, link_id: int) -> GuardianContext  # 아니면 GuardianLinkNotFoundError(허브 오류)
class GuardianLifecyclePort(ABC):
    async def end_for_user(self, user_id: int) -> int
    async def end_for_customer(self, shop_id: int, customer_id: int) -> int

# guardian/domain
VERIFIED_BY = ("report_link",); ENDED_BY = ("guardian", "shop", "withdrawn", "anonymized")
@dataclass(frozen=True)
class GuardianLink: id; user_id; shop_id; customer_id; verified_by; created_at; ended_at; ended_by   # is_live 속성

# guardian/app/ports/output/guardian_link_repository.py
class GuardianLinkRepository(ABC):
    async def create(self, user_id, shop_id, customer_id, verified_by, now) -> GuardianLink   # 살아 있는 연결이 있으면 GuardianAlreadyLinkedError(세이브포인트)
    async def find_live_for_customer(self, shop_id, customer_id) -> GuardianLink | None
    async def get_live(self, user_id, link_id) -> GuardianLink | None
    async def list_live_for_user(self, user_id) -> list[GuardianLink]                         # created_at 순
    async def end(self, link_id, ended_by, now) -> bool                                       # 살아 있을 때만
    async def end_all_for_user(self, user_id, now) -> int                                     # withdrawn
    async def end_all_for_customer(self, shop_id, customer_id, now) -> int                    # anonymized
```

표 `guardian_links`: 설계 4.2 그대로. CHECK `ck_guardian_links_verified_by`·`ck_guardian_links_ended_by`·`ck_guardian_links_ended`(`(ended_at IS NULL) = (ended_by IS NULL)`), 부분 유일 색인 `uq_guardian_links_live(shop_id, customer_id) WHERE ended_at IS NULL`, 색인 `ix_guardian_links_user(user_id) WHERE ended_at IS NULL`.

- [ ] **Step 1: 테스트**
  - 통합 `guardian/tests/adapter/test_guardian_pg_repositories.py`: 만들고 읽기 / 같은 카드에 둘째는 `GuardianAlreadyLinkedError` 이고 트랜잭션은 계속 쓸 수 있다 / 끝낸 뒤에는 다시 만들 수 있고 옛 줄이 남는다 / `get_live` 는 남의 계정·끝난 연결이면 None / `end` 는 살아 있을 때만 True / `end_all_for_user`·`end_all_for_customer` 의 범위와 `ended_by`.
  - 통합 `tests/integration/test_guardian_schema.py`: CHECK 둘이 도메인 튜플과 같은 값·순서, 부분 색인의 조건, `ended_at`·`ended_by` 짝.
  - 단위: 엔티티 `is_live`, 스텁(`guardian/tests/helpers/fakes.py`)이 포트 ABC 를 상속한다.
  - `/myself` 라우터 테스트(기존 스포크와 같은 모양).
- [ ] **Step 2~4:** 실패 확인 → 구현(`.importlinter` 의 모든 계약에 `guardian`, `orm_registry` 등록) → 통과, `lint-imports` kept, `tests/test_schema_drift.py` 통과.
- [ ] **Step 5:** 커밋 `feat(guardian): 허브 포트와 보호자 연결 스포크의 뼈대(0014)`

---

### Task 3: visit — 토큰을 연결 대상으로 푼다

**Files:** `apps/visit/app/use_cases/resolve_report_link_interactor.py`(+입력 포트·DTO·프로바이더), `main.py`(자리 꽂기), 테스트.

**Interfaces:** Produces `ReportLinkPort` 의 구현. 서명 확인(`read_token`) → `PublicReportRepository.find` → `ReportLinkTarget(shop_id, customer_id=target.visit.customer_id, live=…)`. `live` 는 공개 관문과 같은 뜻 — 링크가 `is_live(now)` 이고 매장이 `open` 이고 기록이 있다. **접속 주소 제한기는 쓰지 않는다**(잇기는 로그인한 계정 단위로 센다 — 작업 4).

- [ ] **Step 1: 테스트** — 단위: 서명 틀림·없는 public_id → None / 열린 링크 → `live=True` 와 고객 / 끊음·기간 지남·매장 정지·기록 없음 → `live=False`. 통합: 실제 알림장을 보내 받은 토큰으로 `resolve` 가 그 고객을 준다, 익명화한 고객의 토큰은 `live=False`.
- [ ] **Step 2~4:** 실패 확인 → 구현 → visit 단위·통합 통과.
- [ ] **Step 5:** 커밋 `feat(visit): 알림장 토큰을 매장·고객으로 푸는 허브 포트 구현`

---

### Task 4: guardian — 잇기

**Files:** `apps/guardian/…` 의 `claim_guardian_link` 슬라이스, `adapter/outbound/redis/claim_redis_limiter.py`, `adapter/inbound/api/error_map.py`, `domain/errors.py`, `dependencies/hub_ports.py`, `main.py`.

**Interfaces:** Consumes `ReportLinkPort`, `ActiveUserGuardPort.lock_active`, 저장소. Produces `POST /v1/me/guardian/links`(헤더 `X-Report-Token`, 본문 없음) → 201 `{"link_id": int}` / 200 같은 모양.

순서: 횟수 제한(계정) → 유저 행 잠금(`lock_active`) → `ReportLinkPort.resolve` → None 이면 404 `REPORT_NOT_FOUND`, `live` 가 아니면 410 `REPORT_CLOSED` → 그 카드의 살아 있는 연결이 내 것이면 200, 남의 것이면 409 `GUARDIAN_ALREADY_LINKED` → 없으면 만든다(`verified_by="report_link"`, 동시에 온 둘째는 저장소가 409).

- [ ] **Step 1: 테스트**
  - 단위(스텁): 열린 링크 → 201·줄 하나 / 이미 내 것 → 200 같은 ID, 줄이 늘지 않는다 / 남의 것 → 409 / 닫힌 링크 → 410 / 없는 토큰·헤더 없음 → 404 / 열한 번째 → 429 `GUARDIAN_RATE_LIMITED`(저장소·포트를 부르지 않는다) / 끊은 뒤 다시 → 201 새 ID(Review Focus 1) / `lock_active` 가 먼저 불린다(journal 순서).
  - 라우터: 상태 코드와 오류 본문 `{code, message}`, 로그인 없으면 401, 응답·오류에 토큰 글자가 없다.
  - 통합: 실제 토큰으로 잇기 201 → 같은 요청 200 → 다른 계정 409. 두 계정이 동시에(`asyncio.gather`) → 하나 201·하나 409. 로그(caplog)에 토큰이 없다.
- [ ] **Step 2~4:** 실패 확인 → 구현 → 통과. 변이: 내 것 판정을 지우면 "이미 내 것 → 200" 이 떨어진다.
- [ ] **Step 5:** 커밋 `feat(guardian): 알림장 링크로 고객 카드와 계정을 잇는다`

---

### Task 5: guardian — 내 연결 목록, 보호자가 끊기, 가드

**Files:** `list_guardian_links`·`end_guardian_link`·`resolve_guardian_access` 슬라이스, `core/guardian_guard.py`.

**Interfaces — Produces:**

- `GET /v1/me/guardian/links` → `{"items": [{"link_id", "shop_name", "linked_at"}]}`(이은 순). 매장이 없거나 `open` 이 아닌 연결은 뺀다.
- `DELETE /v1/me/guardian/links/{link_id}` → 204(`ended_by="guardian"`). 없거나 남의 것 → 404 `GUARDIAN_LINK_NOT_FOUND`.
- `GuardianAccessPort` 구현 — `get_live(user_id, link_id)` 가 없으면 허브의 `GuardianLinkNotFoundError`.
- `core/guardian_guard.get_guardian_context(link_id: int, user=Depends(현재 유저), access=Depends(자리)) -> GuardianContext`. 허브 오류는 404 `GUARDIAN_LINK_NOT_FOUND` 로 바뀐다.

- [ ] **Step 1: 테스트** — 단위: 목록의 순서·매장 이름·정지 매장 제외 / 끊기의 세 갈래(내 것 204, 남의 것 404, 이미 끝난 것 404) / 접근 포트의 세 갈래. 라우터: 401, `link_id` 범위 밖 422. 통합: 남의 `link_id` 로 DELETE → 404 이고 그 연결은 살아 있다(테넌트 격리 — 이 스포크의 첫 통합 테스트). `tests/test_hub_port_binding.py` 에 새 자리들.
- [ ] **Step 2~4:** 실패 확인 → 구현 → 통과.
- [ ] **Step 5:** 커밋 `feat(guardian): 내 연결 목록과 끊기, 보호자 가드`

---

### Task 6: guardian — 매장이 보고 끊는다

**Files:** `get_customer_guardian_link`·`end_customer_guardian_link` 슬라이스.

**Interfaces — Produces:** `GET /v1/shops/{shop_id}/customers/{customer_id}/guardian-link`(소속, `get_shop_context`) → `{"linked": bool, "linked_at": datetime | null}`. `DELETE`(`require_permission("customer:write")`) → 204(`ended_by="shop"`), 살아 있는 연결이 없으면 404 `GUARDIAN_LINK_NOT_FOUND`. 저장소 호출은 `ctx.shop_id` 로 건다(이 스포크의 매장 범위 메서드는 `ShopContext` 가 첫 인자).

- [ ] **Step 1: 테스트** — 단위: 연결됨·아님, 끊기 두 갈래. 라우터: 응답의 키가 `{"linked", "linked_at"}` 뿐이다(`user_id` 없음 — G14). 통합: 다른 매장 멤버 → 403 `NOT_A_MEMBER`, 권한 없는 역할의 DELETE → 403, 다른 매장의 `customer_id` → `linked: false`(그 매장의 연결을 건드리지 않는다), 매장이 끊은 뒤 보호자의 목록에서 사라진다.
- [ ] **Step 2~4:** 실패 확인 → 구현 → 통과. `route_inspection`(새 매장 경로가 `get_shop_context` 를 거친다).
- [ ] **Step 5:** 커밋 `feat(guardian): 매장이 고객의 보호자 연결을 보고 끊는다`

---

### Task 7: 탈퇴와 익명화가 연결을 끝낸다

**Files:** `apps/guardian/app/use_cases/end_guardian_links_interactor.py`(`GuardianLifecyclePort` 구현 + 프로바이더), `apps/auth/app/use_cases/withdraw_interactor.py`·`dependencies/hub_ports.py`·`withdraw_provider.py`, `auth_main.py`, `apps/customer/app/use_cases/delete_customer_interactor.py`·`dependencies/hub_ports.py`·프로바이더, `main.py`.

**Interfaces:** `WithdrawInteractor` 는 소속 정리(`apply_withdrawal`) 뒤에 `end_for_user(user.id)` 를 부른다(같은 트랜잭션, 유저 행은 이미 잠겨 있다). `DeleteCustomerInteractor` 는 `anonymize` 뒤에 `end_for_customer(ctx.shop_id, customer_id)` 를 부른다(고객 행은 이미 잠겨 있다).

- [ ] **Step 1: 테스트** — 단위: 두 인터랙터가 포트를 그 자리에서 부른다(journal 순서), 포트 구현의 `ended_by`. 통합: 탈퇴 → 연결이 `withdrawn` 으로 끝나고, **탈퇴 전에 받은 웹 토큰으로 `GET /v1/me/guardian/links/{id}/reports` → 404**(Review Focus 4 — 작업 8 의 경로가 생긴 뒤 통과하도록 이 단언은 작업 8 에서 켠다), 다른 계정이 같은 링크로 201. 고객 익명화 → `anonymized`, 보호자 목록에서 사라진다. `auth_main.py`·`main.py` 의 자리 채움 테스트.
- [ ] **Step 2~4:** 실패 확인 → 구현 → auth·customer·guardian 단위·통합 통과.
- [ ] **Step 5:** 커밋 `feat(guardian): 탈퇴와 고객 익명화가 보호자 연결을 끝낸다`

---

### Task 8: visit — 보호자용 읽기

**Files:** `apps/visit/…` 의 `list_guardian_pets`·`list_guardian_reports`·`read_guardian_report` 슬라이스, `app/ports/output/guardian_report_repository.py` 와 pg 구현, 스키마, `dependencies/hub_ports.py`, `main.py`.

**Interfaces — Produces:**

```python
class GuardianReportRepository(ABC):   # ShopContext(public_context) 를 첫 인자로 받는다
    async def list_sent(self, ctx, customer_id, *, pet_id: int | None, before: tuple[datetime, int] | None, limit: int) -> list[SentReport]
        """그 고객의 방문 가운데 끊지 않은 알림장(revoked_at IS NULL — 기간은 보지 않는다)과 기록이 있는 것. 방문 시작 시각·방문 ID 역순."""
    async def get_sent(self, ctx, customer_id, report_id) -> SentReport | None
    async def pet_ids_with_reports(self, ctx, customer_id) -> list[int]
# SentReport: report(VisitReport), visit(Visit)
```

- `GET /v1/me/guardian/links/{link_id}/pets` → `{"items": [{"pet_id", "name"}]}` — 알림장을 받은 적 있는 아이만, 무지개다리 포함, 이름은 `CustomerDirectoryPort.briefs`.
- `GET …/reports?pet_id=&cursor=` → `{"items": [{"report_id", "visit_date", "pet_id", "pet_name", "cover": {"url","width","height"} | null, "media_count"}], "next_cursor": str | null}`. 대표 사진·수는 뺀 것을 제외한 것(`visible_media`·`report_cover_media_id`), 썸네일 주소.
- `GET …/reports/{report_id}` → **공개 알림장 응답 스키마 그대로**, `expires_at` 은 늘 null. `describe_report(…, include_hidden=False)` 를 쓴다. 열람 신호를 찍지 않는다.
- 셋 다 `get_guardian_context` 를 거치고, 매장을 `ShopProfilePort.public_profile` 로 읽어 없거나 `open` 이 아니면 목록은 빈 것·한 장은 404 `REPORT_NOT_FOUND`. `ShopContext` 는 `public_context(shop)`.

- [ ] **Step 1: 테스트**
  - 단위(스텁): 목록의 순서·쪽 나눔(21개 → 20개와 `next_cursor`, 다음 쪽 1개와 null) / `pet_id` 거르기 / 보호자만의 방문은 `pet_id: null` 이고 `pets` 에 없다(Review Focus 2) / 정지 매장 → 빈 목록·404 / 한 장의 `expires_at is None` / 깨진 `cursor` → 422.
  - 통합(pg 저장소): 끊은 알림장 제외, 기간 지난 것 포함, 끊고 새로 보낸 방문은 새 것 한 장이고 옛 `report_id` 는 None(Review Focus 3), 다른 고객의 `report_id` 는 None, 기록을 지운 방문 제외.
  - 통합(배선): 남의 `link_id` → 404 `GUARDIAN_LINK_NOT_FOUND`. 한 장 응답의 키 집합이 공개 알림장 응답의 키 집합과 같고 `internal_note`·끈 항목이 없다(G5 — 금액을 끈 매장에서 `total_amount` 가 null). 뺀 사진이 목록의 수와 한 장에 없다. 읽은 뒤 `first_viewed_at` 이 그대로 null. 가족 두 마리의 같은 날 방문 → 두 장. 작업 7 의 "탈퇴 뒤 웹 토큰 404" 단언을 켠다.
- [ ] **Step 2~4:** 실패 확인 → 구현 → visit 단위·통합 통과. 변이 둘: `revoked_at IS NULL` 조건을 지우면 "끊은 알림장 제외"가, 고객 조건을 지우면 "다른 고객의 report_id" 가 떨어진다.
- [ ] **Step 5:** 커밋 `feat(visit): 보호자가 지난 알림장을 읽는다 — 아이들, 목록, 한 장`

---

### Task 9: 구조·흐름·문서·전체 검증

**Files:** `backend/scripts/check_guardian_flow.sh`, `backend/apps/guardian/_docs/CLAUDE.md`(+심볼릭 링크 `CLAUDE.md` — 기존 스포크와 같은 방식), 루트 `CLAUDE.md`, `_docs/architecture.md`, `_docs/harness.md`, `_docs/decisions/010-guardian.md`.

- [ ] **Step 1: 흐름 스크립트**(게이트웨이 경유, `check_report_flow.sh` 의 양식 — 토큰·주소를 찍지 않는다): 매장·사장·보호자 계정(dev 로그인 `session: web`) → 알림장 보내기 → 잇기 201 → 다시 200 → 다른 계정 409 → 목록에 매장 이름 → 아이들 → 지난 알림장 목록 → 한 장(내부 메모 칸 없음) → 링크 기간이 지난 것처럼 만들 수 없으니 **링크 끊기 뒤 목록에서 사라짐**을 본다 → 다시 보내면 다시 보임 → 매장의 `guardian-link` 가 `linked: true` → 매장이 끊으면 보호자 읽기 404 → 다시 잇기 201 → 보호자가 끊기 204 → 닫힌 토큰으로 잇기 410. 판별력 한 번(기대 하나를 뒤집어 그 줄에서 멈추는지).
- [ ] **Step 2: 문서**
  - 루트 `CLAUDE.md`: 잠금 순서에 보호자 연결 행, "가드 없이 `ShopContext` 를 만드는 곳"의 첫째 설명을 "매장 멤버가 아닌 요청 경로(공개 알림장·보호자 읽기)"로, 저장소 표·명령에 흐름 스크립트.
  - `guardian/_docs/CLAUDE.md`: 소유 데이터, 잇기 규칙(카드당 하나·`verified_by`), 끝나는 네 가지, 고객을 읽지 않는다, 매장에 보호자를 알리지 않는다.
  - `_docs/architecture.md`(스포크 표·허브 포트 표), `_docs/harness.md`(흐름 스크립트).
  - `010-guardian.md`: 사용자와 정한 것, 이 계획이 정한 것, **⑦-2 웹·⑦-3 앱이 기댈 API 계약**(경로·본문·응답·오류 코드·웹 세션 로그인), 감수하는 것(G1·G13), 남는 것.
- [ ] **Step 3: 전체 검증**(결과 숫자를 적는다)
  - 단위 전체(1941 + 새 테스트)·통합 전체(507 + 새 테스트) 실패 0.
  - `lint-imports` — 계약이 모두 kept(스포크가 하나 늘었다).
  - 라우트 표 전후 비교 — 늘어난 경로가 정확히 이 계획의 것(`/v1/guardian/myself` 1, 보호자 6, 매장 2)이고 없어지거나 바뀐 줄이 없다. 로그인 없는 경로 목록 불변.
  - 개발 DB 에 0014 를 올리고(`backend` 재시작 — 칸 추가만이다) `check_guardian_flow.sh` 통과, 기존 `check_report_flow.sh`·`check_notification_flow.sh` 통과.
- [ ] **Step 4:** 커밋 `test(guardian): 보호자 흐름 스크립트` + `docs: ⑦-1 보호자 회원 백엔드 — 스포크 규칙, 아키텍처 표, 결정 기록 010`
