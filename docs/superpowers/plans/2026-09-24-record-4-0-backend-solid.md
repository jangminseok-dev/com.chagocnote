# 차곡노트 ④ 미용 기록·피드 뷰 — 계획 ④-0 백엔드: SOLID 정리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ①~③ 백엔드 코드에서 SOLID 감사(설계 4.1절 B1~B10)가 찾은 위반을 **기능 코드 없이** 전부 고친다 — 기존 단위·통합·구조 계약이 전후로 통과하고, 라우트 표와 API 응답이 글자까지 같다.

**Architecture:** 여덟 작업이 각각 하나의 위반을 닫는다. ① 허브 포트 오류 계약(`hub/app/errors.py` + `core/hub_errors.py`) ② `VisitRepository` 20개 → 포트 다섯(찾기·잠금, 쓰기, 이력, 원장, 게시판) ③ 공용 스텁의 ABC 상속 ④ 상태 전이의 행동 축(`transition()` 디스패치)·되돌리기 확인(`pets_to_confirm`)·완료 후속 처리(`completion_effects`) ⑤ 상태의 단일 원천(`domain/state/visit_status` 표 → 집합·ORM CHECK·부분 색인·하루 집계) ⑥ 도메인 규칙 둘(소요 기본값·초안 후보 등급)을 도메인으로 ⑦ 재인증 정책을 auth 스포크로 ⑧ 결정 기록 007. 어느 작업도 표·마이그레이션·라우트·JSON 을 바꾸지 않는다. 모든 코드는 참조 작업 트리(`.superpowers/ref/wt-record-4-0-be`, 브랜치 `ref/record-4-0-be`, 커밋 f7003cd…3d76d25)에서 먼저 돌려 검증했고, 변이 17개로 판별력을 확인했다.

**Tech Stack:** Python 3.13 · FastAPI 0.141 · SQLAlchemy 2.0(asyncio) · pytest · import-linter — **새 의존성 없음, 새 마이그레이션 없음.**

**Spec:** `docs/superpowers/specs/2026-09-24-record-media-design.md` — 이 계획은 4절 "SOLID 점검 결과와 정리(④-0)"의 4.1 백엔드 표(B1~B10)와 13절 첫 줄(④-0 검증 기준), 14절의 "④-0 SOLID 정리 — 백엔드"다. B9·B10 은 "유지"이므로 작업이 없다. 실행자는 설계 문서와 함께 `_docs/architecture.md`, `_docs/harness.md`, `backend/apps/{hub,visit,customer,tenancy,auth}/_docs/CLAUDE.md`, `_docs/decisions/002-hub-port-assembly.md`(허브 포트 조립)·`006-visit-reservation.md`(잠금 순서·상태 규칙)를 읽는다.

**계획의 위치:** ④의 구현 계획 다섯 가운데 첫째다. **④-0 백엔드(이 문서)** · ④-0 앱(병렬 가능, 별도 계획) → ④-1 백엔드(media 스포크·기록) → ④-2 앱 → ④-3 영상·음성. ④-1 은 이 계획이 만든 이름(`VisitLookupRepository`·`VisitHistoryRepository`·`completion_effects.apply_completion_effects`·`HubPortError`)에 기댄다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준이다. 백엔드 명령은 `infra/`에서 돌린다. 맥에 파이썬 환경을 만들지 않는다.
- 작업 브랜치는 `feat/record-4-0-backend-solid`다(`feat/record-4-design` `726d07e`에서 딴다 — 설계 문서가 그 브랜치에 있다. 이 계획서 커밋이 첫 커밋이다). `main`에서 직접 작업하지 않는다.
- **사용자가 작업 단위 커밋을 허용했다(2026-09-22 이후 계속).** 각 작업의 마지막 단계에서 커밋한다. 푸시·머지는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이고 끝에 `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`를 단다.
- **Hiss Haus 는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.**
- **이 계획은 새 의존성·새 마이그레이션·새 라우트·새 API 필드를 추가하지 않는다.** 응답의 `code`와 상태 코드도 바꾸지 않는다. 작업 7 뒤 라우트 표는 작업 1 전과 줄 단위로 같아야 한다.
- 계획서의 코드 블록은 그대로 옮긴다. 새 파일은 전문이고, 수정 파일은 diff 다. diff 가 적용되지 않으면 멈추고 보고한다 — 손으로 "비슷하게" 고치지 않는다.
- 볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다.
- 비밀값·토큰·고객 개인정보를 로그에 남기지 않는다. 이 계획은 로그 코드를 만지지 않는다.
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`_docs/architecture.md`, 스포크 `CLAUDE.md` 그대로 — 이 계획이 문서에 더하는 규칙 포함)
- 스포크끼리 직접 import 하지 않는다. 허브는 스포크를 모른다. `core`는 허브의 추상을 import 할 수 있고 스포크는 import 할 수 없다.
- **허브 포트가 던지는 오류는 `hub/app/errors.py`의 `HubPortError` 하위 타입뿐이다**(작업 1 이 세우는 규칙). 구현 스포크는 자기 도메인 오류를 잡아 허브 오류로 바꿔 던진다. HTTP 상태는 `core/hub_errors.py`.
- 유스케이스는 자기가 부르는 포트만 생성자로 받는다(작업 2). 조회 유스케이스는 `VisitWriteRepository`를 받지 않는다.
- 도메인(`*/domain`)은 표준 라이브러리만 import 한다 — core·pydantic·hub·adapter 를 모른다(구조 계약 "도메인 순수성"). `domain/state/visit_status.py`는 아무것도 import 하지 않는다.
- 상태 이름·성질의 단일 원천은 `visit/domain/state/visit_status.py` 표다(작업 5). 상태 이름을 문자열로 다시 적지 않는다.
- 정책(재인증 창 같은 것)은 core 가 아니라 그 스포크의 도메인에 둔다(작업 7).
- 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC 를 상속한다(작업 3). 테스트 파일 안의 부분 스텁(`_Stub*`)은 상속하지 않는다.

검증 명령 (`infra/`에서)
- 단위: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` — 시작 727 → 끝 765
- 통합(실제 Postgres·Redis): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` — 시작 262 → 끝 260(재인증 테스트 8개가 auth 로 옮겨 6개가 된다)
- 구조 계약: `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken(계약 수는 늘지 않는다)
- 라우트 표: `docker compose run --rm --no-deps auth python scripts/print_routes.py` — 작업 1 전에 파일로 받아 두고 작업 7 뒤에 `diff` 한다(컨테이너 이름 두 줄만 다르다)
- 파일 몇 개만: `docker compose run --rm --no-deps backend pytest <경로들> -q -p no:cacheprovider`(통합 표시가 있는 파일은 `--no-deps` 없이 `-m integration`)
- 참조 브랜치와 대조(선택, 마지막에): `git diff ref/record-4-0-be -- backend _docs` 가 비어 있어야 한다. 비어 있지 않으면 어느 diff 를 잘못 적용했는지 찾는다.

## 이 계획에서 새로 정한 것

설계 4.1 절과 다른 것은 결정 기록 007(작업 8)에 적는다. 요약:
- 찾기·잠금 포트는 `VisitLockRepository(get_many·lock)`가 아니라 `VisitLookupRepository(get·get_many·lock)`다.
- 허브 오류는 포트 둘이 아니라 셋(가족 잠금·매장 접근·탈퇴 소속 정리)이고, 상태 맵은 소비 스포크가 아니라 `core/hub_errors.py` 한 곳이다.
- 재인증 가드는 auth 스포크의 `dependencies/recent_login_guard.py`다(라우터 셋이 모두 인증 프로세스에 있어 자리가 필요 없다). `get_current_user_id`의 서명은 그대로다.
- 스텁 ABC 상속은 공용 스텁만.
- 되돌리기가 아닌 전이도 잠그기 전 `get_many`를 한 번 읽는다(조회 하나 증가 — 알고 미룬다).

## Review Focus

설계가 말하지만 어느 작업의 테스트도 직접 겨누지 않던 입력 다섯. 각 줄의 테스트를 해당 작업에 넣었다.
1. **허브 오류를 새로 만들고 상태를 적지 않은 경우** — 500 이 아니라 정해진 상태로 나가야 한다 → 작업 1 `tests/test_hub_errors.py::test_모든_허브_오류가_HTTP_상태를_갖는다`(하위 클래스 전수).
2. **인증 프로세스에서 탈퇴가 막힌 경우** — auth_main 에도 허브 오류 핸들러가 있어야 409 가 나간다 → 작업 1 `tests/integration/test_auth_tenancy_error_wiring.py::test_모든_허브_오류가_auth_프로세스에도_등록되어_있다`.
3. **조회 유스케이스에 쓰기 포트를 넘긴 경우** — 다음 슬라이스(④-1)가 쉽게 저지르는 실수 → 작업 2 `test_visit_port_segregation.py::test_쓰기_포트는_쓰는_유스케이스_넷만_받는다`.
4. **상태를 표에 더했지만 상태 클래스·ORM 을 빠뜨린 경우** → 작업 5 `test_visit_status.py::test_상태마다_상태_클래스가_하나씩_있다`, `test_visit_orm_status.py`(CHECK·부분 색인이 표에서 만든 문자열과 같다), `tests/test_schema_drift.py`(마이그레이션 필요).
5. **로그인 시각이 정확히 300초 전, 또는 61초 미래인 토큰** → 작업 7 `apps/auth/tests/domain/test_recent_login.py`(경계 넷), 가드가 `_utcnow`를 쓰는지 `test_recent_login_guard.py::test_가드는_지금_시각으로_판정한다`.

---

### Task 1: 허브 포트 오류 계약 — `HubPortError` 하위 타입만 스포크 경계를 넘고, 상태는 `core/hub_errors.py`가 정한다 (B2)

**Files:**
- Create: `backend/apps/hub/app/errors.py`
- Create: `backend/core/hub_errors.py`
- Modify: `backend/core/http_errors.py`
- Modify: `backend/apps/hub/app/ports/customer_directory_port.py`
- Modify: `backend/apps/hub/app/ports/shop_access_port.py`
- Modify: `backend/apps/hub/app/ports/membership_lifecycle_port.py`
- Modify: `_docs/architecture.md`
- Modify: `backend/apps/customer/app/use_cases/customer_directory_interactor.py`
- Modify: `backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`
- Modify: `backend/apps/hub/_docs/CLAUDE.md`
- Modify: `backend/apps/tenancy/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/tenancy/app/use_cases/apply_withdrawal_interactor.py`
- Modify: `backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py`
- Modify: `backend/apps/tenancy/domain/errors.py`
- Modify: `backend/apps/tenancy/tests/adapter/test_apply_withdrawal_pg.py`
- Modify: `backend/apps/tenancy/tests/app/use_cases/test_apply_withdrawal_interactor.py`
- Modify: `backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/tests/integration/test_auth_tenancy_error_wiring.py`
- Modify: `backend/tests/integration/test_visit_locking.py`
- Create: `backend/tests/test_hub_errors.py`

**Interfaces:**
- Consumes: 기존 허브 포트 셋 `CustomerDirectoryPort.lock_family`(customer 구현), `ShopAccessPort.resolve`(tenancy 구현, core/shop_guard 소비), `MembershipLifecyclePort.apply_withdrawal`(tenancy 구현, auth 탈퇴 소비); `core/http_errors.install_error_handlers(app, domain_errors)`; customer 도메인 오류 `CustomerNotFoundError`(리포지토리 `lock_active`가 던진다).
- Produces: `hub.app.errors.HubPortError(code)`와 하위 8개 — `FamilyNotFoundError`(CUSTOMER_NOT_FOUND)·`FamilyPetNotFoundError`(PET_NOT_FOUND)·`FamilyPetPassedAwayError`(PET_PASSED_AWAY)·`ShopAccessDeniedError`(NOT_A_MEMBER)·`ShopAccessClosedError`(SHOP_CLOSED)·`ShopAccessSuspendedError`(SHOP_SUSPENDED)·`WithdrawalOwnershipTransferRequiredError`(OWNERSHIP_TRANSFER_REQUIRED)·`WithdrawalShopCloseConfirmRequiredError`(SHOP_CLOSE_CONFIRM_REQUIRED); `core.hub_errors.HUB_ERROR_STATUS: dict[type[Exception], int]`; `install_error_handlers`가 `{**HUB_ERROR_STATUS, **domain_errors}`를 등록; visit 스텁 `FakeDirectory.lock_family`가 같은 허브 오류를 같은 조건에서 던진다(`FamilyRejected` 삭제). tenancy 도메인 오류에서 `OwnershipTransferRequiredError`·`ShopCloseConfirmRequiredError`가 사라진다(Task 4 이후 어디서도 쓰지 않는다).

감사 결과(설계 4.1 B2): 허브 포트가 예외 타입을 계약에 넣지 않아 customer·tenancy 의 도메인 오류가 visit·core·auth 로 새어 나가고 `main.py`가 전 스포크 맵을 합쳐 동작만 맞췄다. 이 작업은 허브에 오류 바탕을 두고, 포트 구현 셋이 자기 도메인 오류를 잡아 허브 오류로 바꿔 던지게 한다. **설계와 다른 점 둘**(결정 기록 007): ① 포트 둘이 아니라 셋(매장 접근·탈퇴 소속 정리도 같은 누수였다) ② HTTP 상태 맵은 소비 스포크의 `error_map.py`가 아니라 `core/hub_errors.py` 한 곳 — core 자신이 `ShopAccessPort`를 소비하고 두 프로세스가 같은 상태로 내보내야 해서다. API 응답의 `code`·상태 코드는 전부 그대로다(통합 테스트 `test_visit_flow_wiring`의 `PET_NOT_FOUND`·`PET_PASSED_AWAY` 단언이 바뀌지 않는다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`:

```diff
@@ -4,10 +4,10 @@ from decimal import Decimal
 import pytest
 
 from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
-from customer.domain.errors import CustomerNotFoundError, PetNotFoundError, PetPassedAwayError
 from customer.tests.helpers.fakes import family
 from customer.tests.helpers.profiles import ctx
 from hub.app.dtos.family_brief import CustomerBrief, PetBrief
+from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
 
 
 class _FakeBriefs:
@@ -45,27 +45,27 @@ async def test_반려동물_없이_보호자만_잠글_수_있다():
     assert journal == [("lock_customer", customer.id)]
 
 
-async def test_다른_보호자의_반려동물이면_PET_NOT_FOUND_다():
+async def test_다른_보호자의_반려동물이면_허브_오류_PET_NOT_FOUND_다():
     """V2 — 같은 매장이라도 다른 가족의 아이를 끼워 넣을 수 없다."""
     _, customers, pets, _, directory = _directory()
     mine, theirs = customers.seed(), customers.seed(phone="01099998888")
     other_pet = pets.seed(theirs.id, "남의 아이")
-    with pytest.raises(PetNotFoundError):
+    with pytest.raises(FamilyPetNotFoundError):
         await directory.lock_family(ctx(), mine.id, (other_pet.id,))
 
 
-async def test_무지개다리_아이면_PET_PASSED_AWAY_다():
+async def test_무지개다리_아이면_허브_오류_PET_PASSED_AWAY_다():
     _, customers, pets, _, directory = _directory()
     customer = customers.seed()
     star = pets.seed(customer.id, "별이", passed_away=True)
-    with pytest.raises(PetPassedAwayError):
+    with pytest.raises(FamilyPetPassedAwayError):
         await directory.lock_family(ctx(), customer.id, (star.id,))
 
 
-async def test_다른_매장의_고객이면_CUSTOMER_NOT_FOUND_다():
+async def test_다른_매장의_고객이면_허브_오류_CUSTOMER_NOT_FOUND_다():
     _, customers, _, _, directory = _directory()
     customer = customers.seed(shop_id=2)
-    with pytest.raises(CustomerNotFoundError):
+    with pytest.raises(FamilyNotFoundError):
         await directory.lock_family(ctx(shop_id=1), customer.id, ())
```

`backend/apps/tenancy/tests/adapter/test_apply_withdrawal_pg.py`:

```diff
@@ -6,11 +6,11 @@ from sqlalchemy import text
 from sqlalchemy.ext.asyncio import async_sessionmaker
 
 from hub.app.dtos.shop_context import ShopContext
+from hub.app.errors import WithdrawalOwnershipTransferRequiredError
 from tenancy.adapter.outbound.pg.invite_pg_repository import InvitePgRepository
 from tenancy.adapter.outbound.pg.member_pg_repository import MemberPgRepository
 from tenancy.adapter.outbound.pg.shop_pg_repository import ShopPgRepository
 from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
-from tenancy.domain.errors import OwnershipTransferRequiredError
 from tenancy.domain.value_objects.role_code import RoleCode
 
 pytestmark = pytest.mark.integration
@@ -43,7 +43,7 @@ async def test_막힌_탈퇴는_앞서_처리한_매장도_되돌린다(db_engin
         await setup.commit()
 
     async with factory() as session:
-        with pytest.raises(OwnershipTransferRequiredError):
+        with pytest.raises(WithdrawalOwnershipTransferRequiredError):
             await _interactor(session).apply_withdrawal(7, close_sole_owned=True)
         # 막히기 전에 첫 매장은 이미 처리됐다. 그래서 아래의 롤백이 의미가 있다.
         assert await _active_user_ids(session, first.id) == [1]
```

`backend/apps/tenancy/tests/app/use_cases/test_apply_withdrawal_interactor.py`:

```diff
@@ -5,7 +5,10 @@ import pytest
 from tenancy.app.use_cases.apply_withdrawal_interactor import ApplyWithdrawalInteractor
 from tenancy.domain.entities.member import Member
 from tenancy.domain.entities.shop import Shop
-from tenancy.domain.errors import OwnershipTransferRequiredError, ShopCloseConfirmRequiredError
+from hub.app.errors import (
+    WithdrawalOwnershipTransferRequiredError,
+    WithdrawalShopCloseConfirmRequiredError,
+)
 from tenancy.domain.value_objects.role_code import RoleCode
 
 NOW = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
@@ -92,7 +95,7 @@ async def test_다른_사장이_있으면_사장도_그냥_나간다():
 async def test_혼자_사장인_매장에_다른_멤버가_있으면_막는다():
     members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 2})
     interactor, shops, _ = _run(members)
-    with pytest.raises(OwnershipTransferRequiredError) as exc:
+    with pytest.raises(WithdrawalOwnershipTransferRequiredError) as exc:
         await interactor.apply_withdrawal(5, close_sole_owned=True)   # 확인을 줬어도 막는다
     assert "매장 3" in str(exc.value)
     assert members.removed == [] and shops.closed == []
@@ -101,7 +104,7 @@ async def test_혼자_사장인_매장에_다른_멤버가_있으면_막는다()
 async def test_혼자뿐인_매장은_확인_없이는_닫지_않는다():
     members = _StubMembers([_member(21, 3, RoleCode.OWNER)], owners={3: 1}, actives={3: 1})
     interactor, shops, _ = _run(members)
-    with pytest.raises(ShopCloseConfirmRequiredError) as exc:
+    with pytest.raises(WithdrawalShopCloseConfirmRequiredError) as exc:
         await interactor.apply_withdrawal(5, close_sole_owned=False)
     assert "매장 3" in str(exc.value)
     assert members.removed == [] and shops.closed == []
@@ -137,7 +140,7 @@ async def test_잠근_뒤에_다시_읽은_역할로_판단한다():
         under_lock={21: _member(21, 3, RoleCode.OWNER)}, owners={3: 1}, actives={3: 2},
     )
     interactor, _, _ = _run(members)
-    with pytest.raises(OwnershipTransferRequiredError):
+    with pytest.raises(WithdrawalOwnershipTransferRequiredError):
         await interactor.apply_withdrawal(5, close_sole_owned=False)
     assert members.removed == []
```

`backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py`:

```diff
@@ -3,7 +3,7 @@ import pytest
 from hub.app.dtos.shop_context import ShopContext
 from tenancy.app.dtos.shop_access_record import ShopAccessRecord
 from tenancy.app.use_cases.resolve_shop_access_interactor import ResolveShopAccessInteractor
-from tenancy.domain.errors import NotAMemberError, ShopClosedError, ShopSuspendedError
+from hub.app.errors import ShopAccessClosedError, ShopAccessDeniedError, ShopAccessSuspendedError
 
 
 class _StubMembers:
@@ -31,15 +31,15 @@ async def test_멤버면_컨텍스트를_돌려준다():
 
 
 async def test_멤버가_아니면_NOT_A_MEMBER_다():
-    with pytest.raises(NotAMemberError):
+    with pytest.raises(ShopAccessDeniedError):
         await ResolveShopAccessInteractor(_StubMembers(None)).resolve(user_id=5, shop_id=3)
 
 
 async def test_닫힌_매장은_SHOP_CLOSED_다():
-    with pytest.raises(ShopClosedError):
+    with pytest.raises(ShopAccessClosedError):
         await ResolveShopAccessInteractor(_StubMembers(_record(shop_closed=True))).resolve(5, 3)
 
 
 async def test_정지된_매장은_SHOP_SUSPENDED_다():
-    with pytest.raises(ShopSuspendedError):
+    with pytest.raises(ShopAccessSuspendedError):
         await ResolveShopAccessInteractor(_StubMembers(_record(shop_suspended=True))).resolve(5, 3)
```

`backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`:

```diff
@@ -2,6 +2,7 @@ from datetime import date, time
 
 import pytest
 
+from hub.app.errors import FamilyPetNotFoundError
 from visit.app.dtos.register_visit_dto import RegisterVisitCommand
 from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
 from visit.domain.errors import (
@@ -18,7 +19,6 @@ from visit.tests.helpers.fakes import (
     FakeMenus,
     FakeSchedule,
     FakeVisits,
-    FamilyRejected,
     Journal,
 )
 
@@ -124,7 +124,7 @@ async def test_시각_규칙에_어긋나면_잠그지도_않는다(fields, erro
 async def test_가족_확인에서_거절되면_넣지_않는다():
     """V2 — 다른 가족·다른 매장의 반려동물, 무지개다리 아이는 customer 가 거절한다."""
     journal, *_, interactor = _setup()
-    with pytest.raises(FamilyRejected):
+    with pytest.raises(FamilyPetNotFoundError):
         await interactor.register_visit(_command(pet_ids=(999,)))
     assert "create_visits" not in [entry[0] for entry in journal]
```

`backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`:

```diff
@@ -12,7 +12,8 @@ from visit.domain.errors import (
     VisitStateConflictError,
 )
 from visit.tests.helpers.builders import ctx, kst
-from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits, FamilyRejected, Journal
+from hub.app.errors import FamilyPetPassedAwayError
+from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits, Journal
 
 NOW = kst(9, 23, 15)
 
@@ -92,7 +93,7 @@ async def test_무지개다리_아이의_방문은_되돌리지_못한다():
     _, visits, interactor = _setup()
     canceled = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 30, 14), status="canceled",
                            canceled_at=NOW, cancel_reason="shop_reason")
-    with pytest.raises(FamilyRejected):
+    with pytest.raises(FamilyPetPassedAwayError):
         await interactor.transition_visits(_act([canceled.id], "revert"))
```

`backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`:

```diff
@@ -1,5 +1,6 @@
 import pytest
 
+from hub.app.errors import FamilyPetNotFoundError
 from visit.app.dtos.update_visit_dto import UpdateVisitCommand
 from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
 from visit.domain.errors import (
@@ -15,7 +16,6 @@ from visit.tests.helpers.fakes import (
     FakeMenus,
     FakeSchedule,
     FakeVisits,
-    FamilyRejected,
     Journal,
 )
 
@@ -57,7 +57,7 @@ async def test_다른_보호자의_아이로는_바꾸지_못한다():
     """V13 — 반려동물은 같은 보호자의 아이로만. 가족 확인이 거절한다."""
     journal, visits, _, interactor = _setup()
     kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
-    with pytest.raises(FamilyRejected):
+    with pytest.raises(FamilyPetNotFoundError):
         await interactor.update_visit(_command(kong, pet_id=201))
     assert "update_visit" not in [entry[0] for entry in journal]
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -5,6 +5,7 @@ from dataclasses import replace
 from decimal import Decimal
 
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
+from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
 from visit.domain.entities.menu import Menu
 from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
 from visit.domain.errors import (
@@ -105,10 +106,6 @@ class FakeMenus:
         return self.rows[menu_id]
 
 
-class FamilyRejected(Exception):
-    """FakeDirectory 가 가족을 거절할 때 던진다 — 실제로는 customer 의 도메인 오류(404·422)다."""
-
-
 class FakeDirectory:
     """CustomerDirectoryPort 스텁. families 는 {고객 ID: (매장 ID, {반려동물 ID: 무지개다리 여부})}."""
 
@@ -123,10 +120,16 @@ class FakeDirectory:
         self.names[customer_id] = name
 
     async def lock_family(self, ctx, customer_id, pet_ids):
+        """실제 구현(customer)과 같은 허브 오류를 같은 조건에서 던진다 — 포트 계약이 곧 스텁의 계약이다."""
         self.journal.append(("lock_family", customer_id, tuple(pet_ids)))
         shop, pets = self.families.get(customer_id, (None, {}))
-        if shop != ctx.shop_id or any(p not in pets or pets[p] for p in pet_ids):
-            raise FamilyRejected(customer_id)
+        if shop != ctx.shop_id:
+            raise FamilyNotFoundError("고객을 찾을 수 없습니다.")
+        for pet_id in pet_ids:
+            if pet_id not in pets:
+                raise FamilyPetNotFoundError("반려동물을 찾을 수 없습니다.")
+            if pets[pet_id]:
+                raise FamilyPetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")
 
     async def briefs(self, ctx, customer_ids, pet_ids):
         customers = {
```

`backend/tests/integration/test_auth_tenancy_error_wiring.py`:

```diff
@@ -1,21 +1,29 @@
-"""탈퇴가 부르는 tenancy 오류가 인증 프로세스에서도 HTTP 로 바뀌는지 구조로 고정한다.
+"""탈퇴가 부르는 오류가 인증 프로세스에서도 HTTP 로 바뀌는지 구조로 고정한다.
 
-auth_main 은 tenancy 의 MembershipLifecyclePort 구현(ApplyWithdrawalInteractor)을 회원 탈퇴 경로에
-꽂는다. 그 인터랙터가 던질 수 있는 tenancy 오류의 핸들러가 auth 프로세스에 없으면, "다른 사장을 먼저
-지정하세요"가 409 대신 처리되지 않은 예외로 500 이 된다.
+auth_main 은 tenancy 의 MembershipLifecyclePort 구현(ApplyWithdrawalInteractor)을 회원 탈퇴 경로에 꽂는다.
+그 인터랙터가 막힐 때 던지는 것은 허브 오류(`hub/app/errors.py`)이고, 리포지토리가 던지는 tenancy 도메인 오류가
+같은 요청 안에서 새어 나올 수도 있다. 어느 쪽이든 핸들러가 auth 프로세스에 없으면 409 대신 500 이 된다.
 
-"어떤 오류를 던지는가"는 소속 정리 코드가 바뀔 때마다 달라지므로, 두 가지를 손으로 적어 두지 않고
-`TENANCY_ERROR_STATUS`의 키를 전부 돈다. tenancy 오류가 새로 생기면 이 테스트가 함께 따라온다.
+"어떤 오류를 던지는가"는 소속 정리 코드가 바뀔 때마다 달라지므로 손으로 적어 두지 않고, 두 맵의 키를 전부 돈다.
 
 auth_main 은 import 시점에 JWT 개인키를 요구하므로, 키를 넣어 주는 wired 픽스처를 먼저 받는다.
 """
 import pytest
 
+from core.hub_errors import HUB_ERROR_STATUS
 from tenancy.adapter.inbound.api.error_map import TENANCY_ERROR_STATUS
 
 pytestmark = pytest.mark.integration
 
 
+async def test_모든_허브_오류가_auth_프로세스에도_등록되어_있다(wired):
+    import auth_main
+
+    handlers = auth_main.app.exception_handlers
+    missing = sorted(e.__name__ for e in HUB_ERROR_STATUS if e not in handlers)
+    assert missing == [], f"{missing} 핸들러가 auth_main 에 없다"
+
+
 async def test_모든_tenancy_오류가_auth_프로세스에도_등록되어_있다(wired):
     import auth_main
```

`backend/tests/integration/test_visit_locking.py`:

```diff
@@ -16,8 +16,9 @@ from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
 from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
 from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
 from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
-from customer.domain.errors import CustomerHasUpcomingVisitsError, CustomerNotFoundError
+from customer.domain.errors import CustomerHasUpcomingVisitsError
 from customer.tests.helpers.profiles import customer_profile, pet_profile
+from hub.app.errors import FamilyNotFoundError
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
@@ -101,7 +102,7 @@ async def test_익명화가_고객을_쥔_동안_예약은_기다리고_뒤에
         assert await _still_waiting(book)
 
         await deleting.commit()
-        with pytest.raises(CustomerNotFoundError):
+        with pytest.raises(FamilyNotFoundError):   # customer 의 오류가 아니라 허브 오류로 나온다
             await book
         await booking.rollback()
```

`backend/tests/test_hub_errors.py`:

```python
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
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest tests/test_hub_errors.py apps/customer/tests/app/use_cases/test_customer_directory_interactor.py -q -p no:cacheprovider`
Expected: 두 파일 모두 수집 단계에서 `ModuleNotFoundError: No module named 'hub.app.errors'`.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/errors.py`:

```python
"""허브 포트가 던지는 오류 — 스포크 경계를 넘는 예외의 계약.

포트를 구현하는 스포크는 자기 도메인 오류를 밖으로 내보내지 않고 여기 있는 예외로 바꿔 던진다.
소비하는 스포크와 core 는 이 타입만 알면 된다(리스코프: 구현이 무엇을 던지는지 계약이 말한다).
HTTP 상태는 `core/hub_errors.py`가 정하고, 두 진입점의 오류 처리기에 자동으로 들어간다.
code 는 응답 본문의 code 로 나간다 — 구현 스포크가 자기 라우터에서 쓰는 코드와 같게 둔다.
"""
from __future__ import annotations


class HubPortError(Exception):
    """허브 포트 오류의 바탕. 새 포트가 오류를 던지게 되면 여기서 파생하고 `core/hub_errors.py`에 상태를 적는다."""

    code = "HUB_PORT_ERROR"


# --- CustomerDirectoryPort.lock_family (구현: customer) -----------------------------------------

class FamilyNotFoundError(HubPortError):
    """살아 있는 이 매장의 고객이 아니다(익명화됐거나 다른 매장)."""

    code = "CUSTOMER_NOT_FOUND"


class FamilyPetNotFoundError(HubPortError):
    """그 보호자의 아이가 아니다(다른 가족·다른 매장·지워진 아이)."""

    code = "PET_NOT_FOUND"


class FamilyPetPassedAwayError(HubPortError):
    """무지개다리를 건넌 아이다 — 새로 시간을 차지하는 예약을 잡을 수 없다."""

    code = "PET_PASSED_AWAY"


# --- ShopAccessPort.resolve (구현: tenancy, 소비: core/shop_guard) --------------------------------

class ShopAccessDeniedError(HubPortError):
    """이 매장의 멤버가 아니다. 매장이 없는 경우와 구분해 주지 않는다(매장 존재 여부를 흘리지 않는다)."""

    code = "NOT_A_MEMBER"


class ShopAccessClosedError(HubPortError):
    code = "SHOP_CLOSED"


class ShopAccessSuspendedError(HubPortError):
    code = "SHOP_SUSPENDED"


# --- MembershipLifecyclePort.apply_withdrawal (구현: tenancy, 소비: auth 탈퇴) ---------------------

class WithdrawalOwnershipTransferRequiredError(HubPortError):
    """탈퇴하려는 유저가 유일한 사장인데 다른 멤버가 남아 있다 — 사장을 먼저 넘겨야 한다."""

    code = "OWNERSHIP_TRANSFER_REQUIRED"


class WithdrawalShopCloseConfirmRequiredError(HubPortError):
    """탈퇴하면 혼자 운영하던 매장이 닫힌다 — 확인을 받아야 한다."""

    code = "SHOP_CLOSE_CONFIRM_REQUIRED"
```

`backend/core/hub_errors.py`:

```python
"""허브 포트 오류 → HTTP 상태 코드.

core 가 허브 포트(ShopAccessPort)를 직접 소비하고, 다른 포트의 오류도 어느 프로세스에서든 같은 상태로
나가야 하므로 맵을 한 곳에 둔다. `install_error_handlers`가 스포크 맵과 함께 자동으로 등록한다.
`tests/test_hub_errors.py`가 HubPortError 의 모든 하위 클래스가 여기 있는지 확인한다.
"""
from __future__ import annotations

from hub.app.errors import (
    FamilyNotFoundError,
    FamilyPetNotFoundError,
    FamilyPetPassedAwayError,
    ShopAccessClosedError,
    ShopAccessDeniedError,
    ShopAccessSuspendedError,
    WithdrawalOwnershipTransferRequiredError,
    WithdrawalShopCloseConfirmRequiredError,
)

HUB_ERROR_STATUS: dict[type[Exception], int] = {
    FamilyNotFoundError: 404,
    FamilyPetNotFoundError: 404,
    FamilyPetPassedAwayError: 422,
    ShopAccessDeniedError: 403,
    ShopAccessClosedError: 403,
    ShopAccessSuspendedError: 403,
    WithdrawalOwnershipTransferRequiredError: 409,
    WithdrawalShopCloseConfirmRequiredError: 409,
}
```

`backend/core/http_errors.py`:

```diff
@@ -6,6 +6,8 @@ from fastapi.exceptions import RequestValidationError
 from fastapi.responses import JSONResponse
 from starlette.exceptions import HTTPException as StarletteHTTPException
 
+from core.hub_errors import HUB_ERROR_STATUS
+
 
 class ApiError(Exception):
     def __init__(self, status_code: int, code: str, message: str) -> None:
@@ -16,9 +18,10 @@ class ApiError(Exception):
 
 
 def install_error_handlers(app: FastAPI, domain_errors: dict[type[Exception], int]) -> None:
-    """ApiError 와 스포크의 도메인 오류를 같은 형식의 응답으로 바꾼다.
+    """ApiError 와 스포크의 도메인 오류, 허브 포트 오류를 같은 형식의 응답으로 바꾼다.
 
     domain_errors 는 {도메인 예외 클래스: HTTP 상태 코드}. 예외는 code 속성을 가져야 한다.
+    허브 포트 오류(`core/hub_errors.py`)는 어느 프로세스에서든 같은 상태로 나가야 하므로 여기서 함께 등록한다.
     """
 
     @app.exception_handler(ApiError)
@@ -36,7 +39,7 @@ def install_error_handlers(app: FastAPI, domain_errors: dict[type[Exception], in
 
         return _handler
 
-    for exc_type, status_code in domain_errors.items():
+    for exc_type, status_code in {**HUB_ERROR_STATUS, **domain_errors}.items():
         app.add_exception_handler(exc_type, _make(status_code))
 
     @app.exception_handler(RequestValidationError)
```

`backend/apps/hub/app/ports/customer_directory_port.py`:

```diff
@@ -14,8 +14,8 @@ class CustomerDirectoryPort(ABC):
     @abstractmethod
     async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
         """고객 행을 FOR UPDATE 로 잠그고 확인한다: 살아 있는 이 매장의 고객인가, 반려동물이 모두 그 보호자의
-        아이이고 무지개다리가 아닌가. 통과하지 못하면 구현 쪽 도메인 오류(CUSTOMER_NOT_FOUND·PET_NOT_FOUND·
-        PET_PASSED_AWAY)를 던진다.
+        아이이고 무지개다리가 아닌가. 통과하지 못하면 허브 오류를 던진다: FamilyNotFoundError(익명화됐거나
+        다른 매장), FamilyPetNotFoundError(그 보호자의 아이가 아님), FamilyPetPassedAwayError(무지개다리).
 
         잠금은 부르는 쪽 트랜잭션이 끝날 때 풀린다. 방문을 쓰는 유스케이스는 방문 행을 잠그기 **전에** 부른다
         (잠금 순서: 고객 행 → 방문 행). 익명화·무지개다리·반려동물 삭제와 겹치지 않게 하려는 것이다.
```

`backend/apps/hub/app/ports/shop_access_port.py`:

```diff
@@ -10,4 +10,8 @@ class ShopAccessPort(ABC):
 
     @abstractmethod
     async def resolve(self, user_id: int, shop_id: int) -> ShopContext:
-        """소속·역할·권한과 매장 상태를 매 요청마다 DB 에서 확인한다. 통과하지 못하면 구현 쪽 도메인 오류를 던진다."""
+        """소속·역할·권한과 매장 상태를 매 요청마다 DB 에서 확인한다.
+
+        통과하지 못하면 허브 오류를 던진다: ShopAccessDeniedError(멤버가 아니거나 매장이 없음 — 둘을 구분해
+        주지 않는다), ShopAccessClosedError, ShopAccessSuspendedError.
+        """
```

`backend/apps/hub/app/ports/membership_lifecycle_port.py`:

```diff
@@ -11,7 +11,8 @@ class MembershipLifecyclePort(ABC):
         """탈퇴하는 유저의 모든 소속을 해제한다. 부르는 쪽과 같은 트랜잭션 안에서 돈다.
 
         혼자 사장인 매장에 다른 멤버가 있으면 막고, 멤버가 본인뿐이면 close_sole_owned 가 참일 때만
-        매장을 닫고 진행한다. 막힐 때는 구현 쪽 도메인 오류를 던진다 — 부르는 쪽의 트랜잭션이 통째로
-        되돌아가므로 아무것도 바뀌지 않는다. 미리 조회하는 메서드를 따로 두지 않는 이유는, 조회와 적용
+        매장을 닫고 진행한다. 막힐 때는 허브 오류를 던진다 — WithdrawalOwnershipTransferRequiredError(다른
+        멤버가 남은 매장의 유일한 사장), WithdrawalShopCloseConfirmRequiredError(확인 없이 혼자뿐인 매장).
+        부르는 쪽의 트랜잭션이 통째로 되돌아가므로 아무것도 바뀌지 않는다. 미리 조회하는 메서드를 따로 두지 않는 이유는, 조회와 적용
         사이에 다른 요청이 사장 수를 바꿀 수 있어서다.
         """
```

`_docs/architecture.md`:

```diff
@@ -33,6 +33,7 @@
 - `core/`는 인프라 공유(DB 세션, 설정, 토큰 검증)만 맡는다. `core/security.py`가 `users` 테이블을 원시 SQL로 조회하는 것은 의도한 예외다. core가 스포크의 ORM을 import할 수 없기 때문이다.
 - `core/`는 허브의 추상(포트 ABC와 DTO)을 import할 수 있다. 스포크는 import할 수 없다.
 - 허브 포트를 구현하는 슬라이스는 그 포트를 입력 포트로 삼는다. 인터랙터가 허브 포트 ABC를 직접 상속하고, HTTP 표면이 없으므로 schema와 router를 생략한다.
+- 허브 포트가 던지는 오류는 `hub/app/errors.py`의 `HubPortError` 하위 타입뿐이다. 구현 스포크는 자기 도메인 오류를 잡아 허브 오류로 바꿔 던지고, 소비 스포크와 테스트 스텁은 그 타입만 안다. HTTP 상태는 `core/hub_errors.py`에 적고 `install_error_handlers`가 두 진입점에 자동으로 등록한다(`tests/test_hub_errors.py`가 빠진 것을 잡는다).
 
 ## 허브 포트 조립
```

`backend/apps/customer/app/use_cases/customer_directory_interactor.py`:

```diff
@@ -9,12 +9,13 @@ from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
 from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
 from customer.app.ports.output.pet_repository import PetRepository
-from customer.domain.errors import PetNotFoundError, PetPassedAwayError
+from customer.domain.errors import CustomerNotFoundError
 from customer.domain.services.phone_number import mask_phone
 from customer.domain.services.search_terms import parse_query
 from hub.app.dtos.draft_candidate import DraftCandidate
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.dtos.shop_context import ShopContext
+from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 
 
@@ -32,15 +33,19 @@ class CustomerDirectoryInteractor(CustomerDirectoryPort):
 
     async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
         # 가족을 바꾸는 customer 유스케이스와 같은 잠금이다 — 익명화와 예약 생성이 서로를 기다린다.
-        await self._customers.lock_active(ctx, customer_id)
+        # 스포크 경계를 넘는 오류는 허브 오류로 바꿔 던진다 — 부르는 쪽은 customer 의 도메인 오류를 모른다.
+        try:
+            await self._customers.lock_active(ctx, customer_id)
+        except CustomerNotFoundError as exc:
+            raise FamilyNotFoundError(str(exc)) from exc
         if not pet_ids:
             return
         family = {pet.id: pet for pet in await self._pets.list_for_customers(ctx, [customer_id])}
         for pet_id in pet_ids:
             if pet_id not in family:
-                raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
+                raise FamilyPetNotFoundError("반려동물을 찾을 수 없습니다.")
             if family[pet_id].passed_away:
-                raise PetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")
+                raise FamilyPetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")
 
     async def briefs(self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]) -> FamilyBriefs:
         customers = await self._briefs.list_customer_briefs(ctx, customer_ids) if customer_ids else []
```

`backend/apps/hub/_docs/CLAUDE.md`:

```diff
@@ -6,6 +6,7 @@
 - 포트는 실제로 쓰는 스포크가 생길 때 추가한다. 빈 껍데기 포트를 미리 만들지 않는다.
 - 구현하는 스포크는 HTTP 표면이 없는 슬라이스로 만들고, 인터랙터가 포트 ABC를 직접 상속한다.
 - 소비하는 스포크는 `dependencies/hub_ports.py`의 자리로 받는다. `main.py`가 구현을 꽂는다.
+- 포트가 던지는 오류는 `app/errors.py`의 `HubPortError` 하위 타입뿐이다. 포트 docstring 이 어떤 타입을 언제 던지는지 적는다. 구현은 자기 도메인 오류를 밖으로 내보내지 않는다. 새 허브 오류는 `core/hub_errors.py`에 상태를 함께 적는다.
 
 | 포트 | 구현 | 사용 |
 |---|---|---|
```

`backend/apps/tenancy/adapter/inbound/api/error_map.py`:

```diff
@@ -8,8 +8,6 @@ from tenancy.domain.errors import (
     LastOwnerError,
     MemberNotFoundError,
     NotAMemberError,
-    OwnershipTransferRequiredError,
-    ShopCloseConfirmRequiredError,
     ShopClosedError,
     ShopSuspendedError,
     TooManyAttemptsError,
@@ -26,7 +24,5 @@ TENANCY_ERROR_STATUS: dict[type[Exception], int] = {
     MemberNotFoundError: 404,
     LastOwnerError: 409,
     AlreadyMemberError: 409,
-    OwnershipTransferRequiredError: 409,
-    ShopCloseConfirmRequiredError: 409,
     TooManyAttemptsError: 429,
 }
```

`backend/apps/tenancy/app/use_cases/apply_withdrawal_interactor.py`:

```diff
@@ -1,19 +1,22 @@
 from __future__ import annotations
 
 from hub.app.dtos.shop_context import ShopContext
+from hub.app.errors import (
+    WithdrawalOwnershipTransferRequiredError,
+    WithdrawalShopCloseConfirmRequiredError,
+)
 from hub.app.ports.membership_lifecycle_port import MembershipLifecyclePort
 from tenancy.app.ports.output.invite_repository import InviteRepository
 from tenancy.app.ports.output.member_repository import MemberRepository
 from tenancy.app.ports.output.shop_repository import ShopRepository
-from tenancy.domain.errors import OwnershipTransferRequiredError, ShopCloseConfirmRequiredError
 from tenancy.domain.value_objects.role_code import RoleCode
 
 
 class ApplyWithdrawalInteractor(MembershipLifecyclePort):
     """허브의 MembershipLifecyclePort 구현. 입력 포트가 곧 허브 포트다.
 
-    auth 의 탈퇴 요청과 같은 DB 세션·같은 트랜잭션에서 돈다. 막히면 예외를 던지고,
-    요청의 트랜잭션이 통째로 되돌아가므로 앞서 처리한 매장의 변경도 남지 않는다.
+    auth 의 탈퇴 요청과 같은 DB 세션·같은 트랜잭션에서 돈다. 막히면 허브 오류를 던지고(auth 는 tenancy 의
+    도메인 오류를 모른다), 요청의 트랜잭션이 통째로 되돌아가므로 앞서 처리한 매장의 변경도 남지 않는다.
     """
 
     def __init__(
@@ -42,11 +45,11 @@ class ApplyWithdrawalInteractor(MembershipLifecyclePort):
                 and await self._members.count_owners(ctx) == 1
             ):
                 if await self._members.count_active(ctx) > 1:
-                    raise OwnershipTransferRequiredError(
+                    raise WithdrawalOwnershipTransferRequiredError(
                         f"'{shop.name}'의 사장이 회원님뿐입니다. 다른 멤버를 먼저 사장으로 지정해 주세요."
                     )
                 if not close_sole_owned:
-                    raise ShopCloseConfirmRequiredError(
+                    raise WithdrawalShopCloseConfirmRequiredError(
                         f"탈퇴하면 '{shop.name}'도 함께 닫힙니다. 확인 후 다시 시도해 주세요."
                     )
                 await self._shops.close(ctx)
```

`backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py`:

```diff
@@ -1,13 +1,13 @@
 from __future__ import annotations
 
 from hub.app.dtos.shop_context import ShopContext
+from hub.app.errors import ShopAccessClosedError, ShopAccessDeniedError, ShopAccessSuspendedError
 from hub.app.ports.shop_access_port import ShopAccessPort
 from tenancy.app.ports.output.member_repository import MemberRepository
-from tenancy.domain.errors import NotAMemberError, ShopClosedError, ShopSuspendedError
 
 
 class ResolveShopAccessInteractor(ShopAccessPort):
-    """허브의 ShopAccessPort 구현. 입력 포트가 곧 허브 포트다."""
+    """허브의 ShopAccessPort 구현. 입력 포트가 곧 허브 포트다. 거절은 허브 오류로 던진다(core 가 소비한다)."""
 
     def __init__(self, members: MemberRepository) -> None:
         self._members = members
@@ -16,11 +16,11 @@ class ResolveShopAccessInteractor(ShopAccessPort):
         record = await self._members.find_access(shop_id, user_id)
         if record is None:
             # 매장이 없는 경우와 소속이 아닌 경우를 구분해 주지 않는다 (매장 존재 여부를 흘리지 않는다).
-            raise NotAMemberError("이 매장의 멤버가 아닙니다.")
+            raise ShopAccessDeniedError("이 매장의 멤버가 아닙니다.")
         if record.shop_closed:
-            raise ShopClosedError("닫힌 매장입니다.")
+            raise ShopAccessClosedError("닫힌 매장입니다.")
         if record.shop_suspended:
-            raise ShopSuspendedError("이용이 정지된 매장입니다.")
+            raise ShopAccessSuspendedError("이용이 정지된 매장입니다.")
         return ShopContext(
             shop_id=shop_id,
             member_id=record.member_id,
```

`backend/apps/tenancy/domain/errors.py`:

```diff
@@ -44,14 +44,6 @@ class TooManyAttemptsError(TenancyError):
     code = "TOO_MANY_ATTEMPTS"
 
 
-class OwnershipTransferRequiredError(TenancyError):
-    code = "OWNERSHIP_TRANSFER_REQUIRED"
-
-
-class ShopCloseConfirmRequiredError(TenancyError):
-    code = "SHOP_CLOSE_CONFIRM_REQUIRED"
-
-
 class AccountUnavailableError(TenancyError):
     """요청 시작 때는 인증을 통과했지만, 유저 행을 잠근 뒤에 보니 탈퇴했거나 정지된 유저다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest tests/test_hub_errors.py apps/customer/tests/app/use_cases/test_customer_directory_interactor.py apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py apps/tenancy/tests/app/use_cases/test_apply_withdrawal_interactor.py -q -p no:cacheprovider` → 전부 통과(hub_errors 5개 포함)

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 732 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 262 passed(`test_visit_locking`·`test_auth_tenancy_error_wiring`·`test_apply_withdrawal_pg` 포함)

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `customer_directory_interactor.lock_family`의 `except CustomerNotFoundError` 블록에서 `raise FamilyNotFoundError(...)`를 `raise`(그대로 전파)로 → `test_다른_매장의_고객이면_허브_오류_CUSTOMER_NOT_FOUND_다` 실패.
- `core/hub_errors.py`에서 `FamilyPetPassedAwayError: 422,` 줄을 뺀다 → `tests/test_hub_errors.py`의 `test_모든_허브_오류가_HTTP_상태를_갖는다`·`test_스포크_맵_없이도_허브_오류가_code_message_로_나간다` 실패.
- `core/http_errors.py`의 `{**HUB_ERROR_STATUS, **domain_errors}.items()`를 `domain_errors.items()`로 → 같은 두 테스트 실패(허브 오류 핸들러가 등록되지 않는다).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(hub): 허브 포트 오류 계약 — HubPortError 하위 타입만 스포크 경계를 넘고, 상태는 core/hub_errors.py 가 정한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 2: 방문 리포지토리를 포트 다섯으로 나눈다 — 찾기·잠금, 쓰기, 이력, 원장, 게시판 (B1)

**Files:**
- Create: `backend/apps/visit/app/ports/output/visit_lookup_repository.py`
- Create: `backend/apps/visit/app/ports/output/visit_write_repository.py`
- Create: `backend/apps/visit/app/ports/output/visit_history_repository.py`
- Create: `backend/apps/visit/app/ports/output/visit_ledger_repository.py`
- Create: `backend/apps/visit/app/ports/output/visit_board_repository.py`
- Delete: `backend/apps/visit/app/ports/output/visit_repository.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Modify: `backend/apps/visit/app/services/visit_locking.py`
- Modify: `backend/apps/visit/app/services/visit_warnings.py`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`
- Modify: `backend/apps/visit/app/use_cases/get_next_visit_draft_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/get_visit_defaults_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/get_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/list_day_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/list_visit_slots_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/register_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/transition_visits_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/update_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/visit_ledger_interactor.py`
- Modify: `backend/apps/visit/dependencies/get_next_visit_draft_provider.py`
- Modify: `backend/apps/visit/dependencies/get_visit_calendar_provider.py`
- Modify: `backend/apps/visit/dependencies/get_visit_defaults_provider.py`
- Modify: `backend/apps/visit/dependencies/get_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/list_day_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/list_visit_slots_provider.py`
- Modify: `backend/apps/visit/dependencies/register_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/reschedule_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/transition_visits_provider.py`
- Modify: `backend/apps/visit/dependencies/update_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/visit_ledger_provider.py`
- Create: `backend/apps/visit/tests/app/test_visit_port_segregation.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_get_next_visit_draft_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`
- Modify: `backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`
- Modify: `backend/tests/integration/test_visit_locking.py`

**Interfaces:**
- Consumes: 기존 `VisitRepository`(메서드 20개)와 그것을 받던 인터랙터 11개·서비스 둘(`visit_locking.lock_visits`·`visit_warnings.warnings_after_save`)·프로바이더 11개·`VisitPgRepository`·`FakeVisits`.
- Produces: `visit.app.ports.output.visit_lookup_repository.VisitLookupRepository`(get·get_many·lock), `visit_write_repository.VisitWriteRepository(VisitLookupRepository)`(create_many·update_details·reschedule·apply_changes), `visit_history_repository.VisitHistoryRepository`(latest_completed_start·list_group·last_completed_before·last_completed_of_pet·completed_starts), `visit_ledger_repository.VisitLedgerRepository`(pet_has_visits·customer_has_active·list_active_from·clear_memos·count_no_show), `visit_board_repository.VisitBoardRepository`(list_between·unresolved_before·list_occupied). `VisitPgRepository`는 넷(쓰기·이력·원장·게시판)을 상속한다(찾기·잠금은 쓰기가 상속). `build_visit_repository(db) -> VisitPgRepository`. 인터랙터 생성자 — `GetNextVisitDraftInteractor(visits, history, menus)`, `GetVisitCalendarInteractor(board, schedule, now)`, `GetVisitDefaultsInteractor(history, menus, schedule)`, `GetVisitInteractor(visits, history, ledger, menus, directory)`, `ListDayVisitsInteractor(board, menus, schedule, directory, now)`, `ListVisitSlotsInteractor(board, schedule)`, `RegisterVisitInteractor(visits, board, menus, schedule, directory, now)`, `RescheduleVisitsInteractor(visits, board, menus, schedule, directory, now)`, `UpdateVisitInteractor(visits, board, menus, schedule, directory, now)`, `TransitionVisitsInteractor(visits, history, menus, directory, now)`, `VisitLedgerInteractor(ledger, now)`; `lock_visits(ctx, visit_ids, visits: VisitLookupRepository, directory, pet_ids)`; `warnings_after_save(ctx, customer_id, starts_at, duration_minutes, settings, board: VisitBoardRepository, schedule)`. Task 4 는 `TransitionVisitsInteractor`의 이 서명을, ④-1 의 기록 슬라이스는 `VisitLookupRepository`·`VisitHistoryRepository`를 그대로 쓴다.

감사 결과(설계 4.1 B1): 메서드 하나만 쓰는 인터랙터도 20개짜리 포트를 받았다. 표는 하나이므로 구현(`VisitPgRepository`)은 그대로 한 클래스이고, 포트만 축별로 나눈다. **설계와 다른 점**(결정 기록 007): 찾기·잠금 포트는 `get_many`·`lock` 둘이 아니라 `get`까지 셋이다 — 상세·초안 조회가 `get`만 쓰고, 셋이 같은 축(ID 로 찾기)이기 때문이다. 프로바이더는 같은 인스턴스를 포트 인자마다 넘긴다(`visits = build_visit_repository(db)` 한 줄). 테스트는 같은 `FakeVisits`를 자리마다 넘긴다. 구조 테스트 `test_visit_port_segregation.py`가 쓰기 포트를 받는 유스케이스를 넷으로 고정하고, 인터랙터 생성자의 타입 힌트를 `typing.get_type_hints`로 읽는다(모듈이 `from __future__ import annotations` 라 문자열이기 때문).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/app/test_visit_port_segregation.py`:

```python
"""visits 표의 리포지토리 포트 다섯 — 인터페이스 분리를 구조로 고정한다.

손으로 관리하는 목록 대신 인터랙터 생성자의 타입 힌트를 읽는다. 조회 유스케이스가 쓰기 포트를 받게 되거나,
한 메서드가 두 포트에 들어가면 여기서 걸린다.
"""
from __future__ import annotations

import importlib
import inspect
import pkgutil
from typing import get_type_hints

import visit.app.use_cases as use_cases
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.tests.helpers.fakes import FakeVisits

PORTS = (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
         VisitBoardRepository)


def _interactors():
    for info in pkgutil.iter_modules(use_cases.__path__):
        module = importlib.import_module(f"{use_cases.__name__}.{info.name}")
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if name.endswith("Interactor") and cls.__module__ == module.__name__:
                yield cls


def _ports_taken(cls) -> list[type]:
    """생성자 인자의 타입 가운데 방문 포트인 것. 모듈이 `from __future__ import annotations` 라 문자열을 풀어 읽는다."""
    hints = get_type_hints(cls.__init__)
    return [hint for name, hint in hints.items() if name != "return" and hint in PORTS]


def test_pg_구현은_다섯_포트를_다_낸다():
    assert all(issubclass(VisitPgRepository, port) for port in PORTS)
    missing = sorted(set(VisitPgRepository.__abstractmethods__))
    assert missing == []


def test_스텁도_다섯_포트의_메서드를_다_가진다():
    for port in PORTS:
        for name in port.__abstractmethods__:
            assert callable(getattr(FakeVisits, name, None)), f"FakeVisits 에 {port.__name__}.{name} 이 없다"


def test_쓰기_포트는_쓰는_유스케이스_넷만_받는다():
    writers = sorted(cls.__name__ for cls in _interactors() if VisitWriteRepository in _ports_taken(cls))
    assert writers == [
        "RegisterVisitInteractor", "RescheduleVisitsInteractor", "TransitionVisitsInteractor",
        "UpdateVisitInteractor",
    ]


def test_같은_포트를_두_번_받는_인터랙터는_없다():
    for cls in _interactors():
        taken = _ports_taken(cls)
        assert len(taken) == len(set(taken)), cls.__name__


def test_포트끼리_메서드가_겹치지_않는다():
    """찾기·잠금은 쓰기가 상속하므로 그 둘만 겹친다."""
    own = {port: set(port.__dict__) & port.__abstractmethods__ for port in PORTS}
    for first in PORTS:
        for second in PORTS:
            if first is not second:
                assert own[first].isdisjoint(own[second]), (first.__name__, second.__name__)
```

`backend/apps/visit/tests/app/use_cases/test_get_next_visit_draft_interactor.py`:

```diff
@@ -9,7 +9,7 @@ from visit.tests.helpers.fakes import FakeMenus, FakeVisits
 
 def _setup():
     visits, menus = FakeVisits(), FakeMenus()
-    return visits, menus, GetNextVisitDraftInteractor(visits, menus)
+    return visits, menus, GetNextVisitDraftInteractor(visits, visits, menus)
 
 
 def _done(visits, **fields):
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`:

```diff
@@ -10,7 +10,7 @@ from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits
 def _setup():
     visits, directory = FakeVisits(), FakeDirectory()
     directory.family(1, pets=(101, 102))
-    return visits, GetVisitInteractor(visits, FakeMenus(), directory)
+    return visits, GetVisitInteractor(visits, visits, visits, FakeMenus(), directory)
 
 
 async def test_묶음_지난_방문_노쇼_횟수를_함께_준다():
```

`backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`:

```diff
@@ -30,7 +30,7 @@ def _setup(settings=None):
     schedule = FakeSchedule(journal) if settings is None else FakeSchedule(journal, settings)
     menus, visits, directory = FakeMenus(journal), FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102))
-    interactor = RegisterVisitInteractor(visits, menus, schedule, directory, now=lambda: NOW)
+    interactor = RegisterVisitInteractor(visits, visits, menus, schedule, directory, now=lambda: NOW)
     return journal, schedule, menus, visits, directory, interactor
```

`backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`:

```diff
@@ -21,7 +21,7 @@ def _setup():
     visits, directory = FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102))
     directory.family(2, pets=(201,))
-    return journal, visits, RescheduleVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory,
+    return journal, visits, RescheduleVisitsInteractor(visits, visits, FakeMenus(), FakeSchedule(), directory,
                                                        now=lambda: NOW)
```

`backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`:

```diff
@@ -23,7 +23,7 @@ def _setup():
     visits, directory = FakeVisits(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102, 103), passed=(103,))
     directory.family(2, pets=(201,))
-    return journal, visits, TransitionVisitsInteractor(visits, FakeMenus(), directory, now=lambda: NOW)
+    return journal, visits, TransitionVisitsInteractor(visits, visits, FakeMenus(), directory, now=lambda: NOW)
 
 
 def _act(ids, action, reason=None, member_id=11):
@@ -137,6 +137,6 @@ async def test_되돌리기_잠그는_사이_반려동물이_바뀌면_다시_
     canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                            canceled_at=NOW, cancel_reason="customer_request")
     visits._swap_visit_id = canceled.id
-    interactor = TransitionVisitsInteractor(visits, FakeMenus(), directory, now=lambda: NOW)
+    interactor = TransitionVisitsInteractor(visits, visits, FakeMenus(), directory, now=lambda: NOW)
     with pytest.raises(VisitStateConflictError):
         await interactor.transition_visits(_act([canceled.id], "revert"))
```

`backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`:

```diff
@@ -27,7 +27,7 @@ def _setup():
     visits, menus, directory = FakeVisits(journal), FakeMenus(journal), FakeDirectory(journal)
     directory.family(1, pets=(101, 102, 103), passed=(103,))
     directory.family(2, pets=(201,))
-    interactor = UpdateVisitInteractor(visits, menus, FakeSchedule(), directory, now=lambda: NOW)
+    interactor = UpdateVisitInteractor(visits, visits, menus, FakeSchedule(), directory, now=lambda: NOW)
     return journal, visits, menus, interactor
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -154,6 +154,8 @@ class FakeDirectory:
 
 
 class FakeVisits:
+    """visits 표 스텁 — pg 구현처럼 다섯 포트(찾기·잠금, 쓰기, 이력, 원장, 게시판)를 한 객체가 다 낸다."""
+
     def __init__(self, journal: Journal | None = None) -> None:
         self.journal = journal if journal is not None else Journal()
         self.rows: dict[int, Visit] = {}
```

`backend/tests/integration/test_visit_locking.py`:

```diff
@@ -45,8 +45,9 @@ def _directory(session):
 
 
 def _register(session, customer_id, pet_ids, starts_at=kst(10, 2, 14)):
+    visits = VisitPgRepository(session)
     interactor = RegisterVisitInteractor(
-        VisitPgRepository(session), MenuPgRepository(session), SchedulePgRepository(session),
+        visits, visits, MenuPgRepository(session), SchedulePgRepository(session),
         _directory(session), now=lambda: NOW,
     )
     return interactor.register_visit(RegisterVisitCommand(
@@ -56,8 +57,9 @@ def _register(session, customer_id, pet_ids, starts_at=kst(10, 2, 14)):
 
 
 def _transition(session, visit_ids, action, reason=None):
+    visits = VisitPgRepository(session)
     interactor = TransitionVisitsInteractor(
-        VisitPgRepository(session), MenuPgRepository(session), _directory(session), now=lambda: NOW
+        visits, visits, MenuPgRepository(session), _directory(session), now=lambda: NOW
     )
     return interactor.transition_visits(TransitionVisitsCommand(
         ctx=SHOP, visit_ids=tuple(visit_ids), action=action, cancel_reason=reason,
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/test_visit_port_segregation.py -q -p no:cacheprovider`
Expected: 수집 단계에서 `ModuleNotFoundError: No module named 'visit.app.ports.output.visit_board_repository'`.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/ports/output/visit_lookup_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitLookupRepository(ABC):
    """방문을 ID 로 찾고 잠근다. 모든 메서드가 ShopContext 의 매장으로 거른다.

    방문 리포지토리 다섯 포트 가운데 가장 작은 것 — 잠금 순서 서비스(`visit_locking.lock_visits`)와 상세·초안
    조회가 이것만 받는다. 쓰기 포트(`VisitWriteRepository`)가 이를 상속한다.
    """

    @abstractmethod
    async def get(self, ctx: ShopContext, visit_id: int) -> Visit:
        """없거나 다른 매장이면 VisitNotFoundError."""

    @abstractmethod
    async def get_many(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        """이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""

    @abstractmethod
    async def lock(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
        """방문 행을 ID 오름차순으로 FOR UPDATE 잠그고 다시 읽는다. 고객 행을 잠근 **뒤에** 부른다(설계 4.2).
        이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""
```

`backend/apps/visit/app/ports/output/visit_write_repository.py`:

```python
from __future__ import annotations

from abc import abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.domain.entities.visit import Visit
from visit.domain.state.visit_state import StatusChange
from visit.domain.value_objects.new_visit import NewVisit


class VisitWriteRepository(VisitLookupRepository):
    """방문을 만들고 고치고 상태를 바꾼다. 찾기·잠금(`VisitLookupRepository`)을 포함한다.

    쓰는 유스케이스(등록·수정·옮기기·전이)만 받는다. 조회 유스케이스는 이 포트를 받지 않는다.
    """

    @abstractmethod
    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
        VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""

    @abstractmethod
    async def update_details(
        self, ctx: ShopContext, visit_id: int, starts_at: datetime, pet_id: int | None,
        duration_minutes: int, menu_ids: tuple[int, ...], memo: str | None,
    ) -> Visit:
        """메뉴는 통째로 바꾼다. 중복 예약이 되면 VisitDuplicateError."""

    @abstractmethod
    async def reschedule(self, ctx: ShopContext, visit_ids: list[int], starts_at: datetime) -> list[Visit]:
        """여러 방문의 시작 시각을 한 번에 바꾼다. 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""

    @abstractmethod
    async def apply_changes(
        self, ctx: ShopContext, changes: list[tuple[int, StatusChange]], member_id: int
    ) -> list[Visit]:
        """상태 칸을 통째로 바꾸고 바꾼 멤버를 찍는다. 되돌리기가 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""
```

`backend/apps/visit/app/ports/output/visit_history_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitHistoryRepository(ABC):
    """한 보호자·한 아이의 지난 방문 — 완료 이력과 가족 묶음. 모든 메서드가 ShopContext 의 매장으로 거른다.

    상세·'지난번처럼'·다음 예약 초안·완료 후 최근 방문 갱신이 받는다.
    """

    @abstractmethod
    async def latest_completed_start(self, ctx: ShopContext, customer_id: int) -> datetime | None:
        """그 보호자의 마지막 완료 방문의 시작 시각 — 고객 목록 '최근 방문순'의 원본."""

    @abstractmethod
    async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
        """같은 가족 묶음(같은 보호자 + 같은 시작 시각)의 방문 — 상태와 상관없이."""

    @abstractmethod
    async def last_completed_before(
        self, ctx: ShopContext, customer_id: int, pet_id: int | None, before: datetime
    ) -> Visit | None:
        """before 전에 시작한 마지막 완료 방문. pet_id 가 있으면 그 아이의, 없으면 보호자만의 방문 가운데서."""

    @abstractmethod
    async def last_completed_of_pet(self, ctx: ShopContext, pet_id: int) -> Visit | None:
        """그 아이의 마지막 완료 방문('지난번처럼'의 원본)."""

    @abstractmethod
    async def completed_starts(
        self, ctx: ShopContext, customer_id: int, pet_id: int | None, limit: int
    ) -> list[datetime]:
        """그 아이(pet_id 가 None 이면 보호자만의 방문)의 완료 방문 시작 시각, 최근 것부터 limit 개."""
```

`backend/apps/visit/app/ports/output/visit_ledger_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitLedgerRepository(ABC):
    """고객 쪽이 묻는 원장 — 방문 유무·앞으로의 예약·노쇼 횟수·메모 비우기. 모든 메서드가 ShopContext 의 매장으로 거른다.

    허브 포트 `VisitLedgerPort` 구현(`visit_ledger_interactor`)과 방문 상세의 노쇼 횟수가 받는다.
    """

    @abstractmethod
    async def pet_has_visits(self, ctx: ShopContext, pet_id: int, active_only: bool) -> bool: ...

    @abstractmethod
    async def customer_has_active(self, ctx: ShopContext, customer_id: int) -> bool: ...

    @abstractmethod
    async def list_active_from(
        self, ctx: ShopContext, customer_id: int, since: datetime, limit: int
    ) -> list[Visit]:
        """since 이후에 시작하는 살아 있는 방문, 시작 순으로 limit 개."""

    @abstractmethod
    async def clear_memos(self, ctx: ShopContext, customer_id: int) -> None: ...

    @abstractmethod
    async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int: ...
```

`backend/apps/visit/app/ports/output/visit_board_repository.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit


class VisitBoardRepository(ABC):
    """하루·달력·시간 칸이 보는 시간 범위의 방문. 모든 메서드가 ShopContext 의 매장으로 거른다.

    하루 목록·월 달력·시간 칸 조회와 저장 뒤 경고(`visit_warnings`)가 받는다.
    """

    @abstractmethod
    async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """시작 시각이 [start, end) 인 방문 — 상태와 상관없이, 시작 순으로."""

    @abstractmethod
    async def unresolved_before(self, ctx: ShopContext, before: datetime) -> tuple[int, datetime | None]:
        """시작 시각이 before 전인데 아직 예약됨인 방문(정리 안 된 예약)의 수와 가장 이른 시작 시각."""

    @abstractmethod
    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """[start, end) 와 시간이 겹치는 살아 있는 방문(예약됨·미용 중)."""
```

`backend/apps/visit/app/ports/output/visit_repository.py`: **지운다.**

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`:

```diff
@@ -10,7 +10,10 @@ from sqlalchemy.ext.asyncio import AsyncSession
 from hub.app.dtos.shop_context import ShopContext
 from visit.adapter.outbound.mappers.visit_mapper import to_visit
 from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
+from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
+from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED, NO_SHOW, RESERVED, Visit
 from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
 from visit.domain.services.visit_schedule import MAX_DURATION
@@ -20,7 +23,9 @@ from visit.domain.value_objects.new_visit import NewVisit
 _DUPLICATE = {"uq_visits_pet_start_active", "uq_visits_customer_start_active"}
 
 
-class VisitPgRepository(VisitRepository):
+class VisitPgRepository(VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository):
+    """visits 표 하나를 다섯 포트로 내놓는다 — 유스케이스는 자기가 쓰는 포트만 받는다(ISP)."""
+
     def __init__(self, session: AsyncSession) -> None:
         self._session = session
```

`backend/apps/visit/dependencies/visit_wiring.py`:

```diff
@@ -8,7 +8,6 @@ from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepositor
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
 
 
 def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
@@ -19,5 +18,6 @@ def build_menu_repository(db: AsyncSession) -> MenuRepository:
     return MenuPgRepository(db)
 
 
-def build_visit_repository(db: AsyncSession) -> VisitRepository:
+def build_visit_repository(db: AsyncSession) -> VisitPgRepository:
+    """visits 표의 리포지토리 하나. 다섯 포트를 다 구현하므로 프로바이더가 같은 인스턴스를 포트 인자마다 넘긴다."""
     return VisitPgRepository(db)
```

`backend/apps/visit/app/services/visit_locking.py`:

```diff
@@ -3,13 +3,13 @@ from __future__ import annotations
 
 from hub.app.dtos.shop_context import ShopContext
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
 from visit.domain.entities.visit import Visit
 from visit.domain.errors import VisitGroupMismatchError, VisitNotFoundError
 
 
 async def lock_visits(
-    ctx: ShopContext, visit_ids: list[int], visits: VisitRepository, directory: CustomerDirectoryPort,
+    ctx: ShopContext, visit_ids: list[int], visits: VisitLookupRepository, directory: CustomerDirectoryPort,
     pet_ids: tuple[int, ...] = (),
 ) -> list[Visit]:
     """visit_ids 의 방문을 잠그고 다시 읽은 목록(ID 순)을 돌려준다.
```

`backend/apps/visit/app/services/visit_warnings.py`:

```diff
@@ -5,19 +5,19 @@ from datetime import datetime
 
 from hub.app.dtos.shop_context import ShopContext
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.domain.services.visit_schedule import Occupied, day_bounds, local_date, warnings_for
 from visit.domain.value_objects.schedule_settings import ScheduleSettings
 
 
 async def warnings_after_save(
     ctx: ShopContext, customer_id: int, starts_at: datetime, duration_minutes: int, settings: ScheduleSettings,
-    visits: VisitRepository, schedule: ScheduleRepository,
+    board: VisitBoardRepository, schedule: ScheduleRepository,
 ) -> list[str]:
     """방금 저장한 묶음(같은 보호자 + 같은 시작 시각)의 경고. 저장한 방문 자신은 같은 묶음이라 겹침에서 빠진다."""
     tz = ctx.timezone
     day = local_date(starts_at, tz)
     start, end = day_bounds(day, tz)
-    occupied = [Occupied(v.starts_at, v.ends_at, v.group_key) for v in await visits.list_occupied(ctx, start, end)]
+    occupied = [Occupied(v.starts_at, v.ends_at, v.group_key) for v in await board.list_occupied(ctx, start, end)]
     closed = frozenset(c.day for c in await schedule.list_closed_dates(ctx, day, day))
     return warnings_for(starts_at, duration_minutes, (customer_id, starts_at), tz, settings, closed, occupied)
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -6,6 +6,7 @@
 - `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
 - 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK).
 - **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
+- `visits` 표의 리포지토리는 포트 다섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository`), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
 - customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
 - 같은 아이(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약은 하나다(부분 유일 색인 — 409 `VISIT_DUPLICATE`, 세이브포인트라 트랜잭션은 계속 쓴다).
 - 겹침·휴무·영업시간 밖은 **막지 않는 경고**다. 판단은 `domain/services/visit_schedule.warnings_for` 한 곳에만 있다.
```

`backend/apps/visit/app/use_cases/get_next_visit_draft_interactor.py`:

```diff
@@ -6,15 +6,19 @@ from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, Next
 from visit.app.dtos.visit_view_dto import MenuBriefView
 from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
+from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
 from visit.domain.entities.visit import CANCELED, COMPLETED, NO_SHOW
 from visit.domain.errors import VisitStateConflictError
 from visit.domain.services.visit_cycle import interval_weeks, next_start
 
 
 class GetNextVisitDraftInteractor(GetNextVisitDraftUseCase):
-    def __init__(self, visits: VisitRepository, menus: MenuRepository) -> None:
+    def __init__(
+        self, visits: VisitLookupRepository, history: VisitHistoryRepository, menus: MenuRepository
+    ) -> None:
         self._visits = visits
+        self._history = history
         self._menus = menus
 
     async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView:
@@ -24,9 +28,9 @@ class GetNextVisitDraftInteractor(GetNextVisitDraftUseCase):
         # 누르기 전에 "언제로 잡히는지"를 보여야 해서다(③-A2).
         if visit.status in (CANCELED, NO_SHOW):
             raise VisitStateConflictError("취소·노쇼한 방문에서는 다음 예약을 잡을 수 없습니다.")
-        group = [v for v in await self._visits.list_group(ctx, visit.customer_id, visit.starts_at)
+        group = [v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
                  if v.status not in (CANCELED, NO_SHOW)]
-        starts = await self._visits.completed_starts(ctx, visit.customer_id, visit.pet_id, limit=2)
+        starts = await self._history.completed_starts(ctx, visit.customer_id, visit.pet_id, limit=2)
         if visit.status != COMPLETED:
             # 아직 완료 전이면 이 방문을 "이번"으로 놓고 직전 완료 방문과의 간격을 본다.
             starts = [visit.starts_at, *[s for s in starts if s < visit.starts_at][:1]]
```

`backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py`:

```diff
@@ -12,7 +12,7 @@ from visit.app.dtos.get_visit_calendar_dto import (
 )
 from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.domain.entities.visit import COMPLETED
 from visit.domain.errors import VisitInputError
 from visit.domain.services.visit_board import COUNTED, is_unresolved
@@ -23,9 +23,9 @@ class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
     """월 달력 — 날마다 마릿수·완료·예약·정리 안 됨, 휴무. 위쪽 '정리 안 된 예약 N건'은 매장 전체다."""
 
     def __init__(
-        self, visits: VisitRepository, schedule: ScheduleRepository, now: Callable[[], datetime]
+        self, board: VisitBoardRepository, schedule: ScheduleRepository, now: Callable[[], datetime]
     ) -> None:
-        self._visits = visits
+        self._board = board
         self._schedule = schedule
         self._now = now
 
@@ -41,7 +41,7 @@ class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
         today = local_date(self._now(), tz)
 
         by_day = defaultdict(list)
-        for visit in await self._visits.list_between(ctx, start, end):
+        for visit in await self._board.list_between(ctx, start, end):
             by_day[local_date(visit.starts_at, tz)].append(visit)
         closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, first_day, last_day))
         days = []
@@ -57,7 +57,7 @@ class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
                 closed_day=is_closed_day(day, settings, closed),
             ))
         today_start, _ = day_bounds(today, tz)
-        total, oldest = await self._visits.unresolved_before(ctx, today_start)
+        total, oldest = await self._board.unresolved_before(ctx, today_start)
         return VisitCalendarView(
             year=query.year, month=query.month, days=days, unresolved_total=total,
             oldest_unresolved_date=local_date(oldest, tz) if oldest else None,
```

`backend/apps/visit/app/use_cases/get_visit_defaults_interactor.py`:

```diff
@@ -5,20 +5,20 @@ from visit.app.dtos.visit_view_dto import MenuBriefView
 from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 
 
 class GetVisitDefaultsInteractor(GetVisitDefaultsUseCase):
     """다른 매장의 반려동물 ID 를 넣어도 이 매장의 방문만 보므로 빈 기본값이 된다 — 아무것도 새지 않는다."""
 
-    def __init__(self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository) -> None:
-        self._visits = visits
+    def __init__(self, history: VisitHistoryRepository, menus: MenuRepository, schedule: ScheduleRepository) -> None:
+        self._history = history
         self._menus = menus
         self._schedule = schedule
 
     async def get_visit_defaults(self, query: GetVisitDefaultsQuery) -> VisitDefaultsView:
         settings = await self._schedule.ensure(query.ctx)
-        last = await self._visits.last_completed_of_pet(query.ctx, query.pet_id)
+        last = await self._history.last_completed_of_pet(query.ctx, query.pet_id)
         if last is None:
             return VisitDefaultsView(source_visit_id=None, duration_minutes=settings.default_duration_minutes,
                                      menus=[])
```

`backend/apps/visit/app/use_cases/get_visit_interactor.py`:

```diff
@@ -6,24 +6,29 @@ from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from visit.app.dtos.get_visit_dto import GetVisitQuery, PreviousVisitView, VisitDetailView
 from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
+from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
+from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
 from visit.app.services.visit_reader import describe_visits
 
 
 class GetVisitInteractor(GetVisitUseCase):
     def __init__(
-        self, visits: VisitRepository, menus: MenuRepository, directory: CustomerDirectoryPort
+        self, visits: VisitLookupRepository, history: VisitHistoryRepository, ledger: VisitLedgerRepository,
+        menus: MenuRepository, directory: CustomerDirectoryPort,
     ) -> None:
         self._visits = visits
+        self._history = history
+        self._ledger = ledger
         self._menus = menus
         self._directory = directory
 
     async def get_visit(self, query: GetVisitQuery) -> VisitDetailView:
         ctx = query.ctx
         visit = await self._visits.get(ctx, query.visit_id)
-        group = [v for v in await self._visits.list_group(ctx, visit.customer_id, visit.starts_at)
+        group = [v for v in await self._history.list_group(ctx, visit.customer_id, visit.starts_at)
                  if v.id != visit.id]
-        previous = await self._visits.last_completed_before(ctx, visit.customer_id, visit.pet_id, visit.starts_at)
+        previous = await self._history.last_completed_before(ctx, visit.customer_id, visit.pet_id, visit.starts_at)
         [view, *group_views] = await describe_visits(ctx, [visit, *group], self._directory, self._menus)
         return VisitDetailView(
             visit=view,
@@ -31,5 +36,5 @@ class GetVisitInteractor(GetVisitUseCase):
             previous_visit=PreviousVisitView(
                 visit_id=previous.id, starts_at=previous.starts_at.astimezone(ZoneInfo(ctx.timezone))
             ) if previous else None,
-            no_show_count=await self._visits.count_no_show(ctx, visit.customer_id),
+            no_show_count=await self._ledger.count_no_show(ctx, visit.customer_id),
         )
```

`backend/apps/visit/app/use_cases/list_day_visits_interactor.py`:

```diff
@@ -13,7 +13,7 @@ from visit.app.dtos.list_day_visits_dto import (
 from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.services.visit_reader import describe_visits
 from visit.domain.entities.visit import CANCELED, COMPLETED, IN_PROGRESS, NO_SHOW, RESERVED
 from visit.domain.errors import VisitInputError
@@ -30,10 +30,10 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
     """하루 화면 — 그날 시작하는 방문 전부(취소·노쇼 포함)를 시작 순으로."""
 
     def __init__(
-        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
+        self, board: VisitBoardRepository, menus: MenuRepository, schedule: ScheduleRepository,
         directory: CustomerDirectoryPort, now: Callable[[], datetime],
     ) -> None:
-        self._visits = visits
+        self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
@@ -45,8 +45,8 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
             raise VisitInputError("날짜가 올바르지 않습니다.")
         settings = await self._schedule.ensure(ctx)
         start, end = day_bounds(day, tz)
-        visits = await self._visits.list_between(ctx, start, end)
-        occupied = await self._visits.list_occupied(ctx, start, end)   # 전날 밤에 시작한 방문도 겹칠 수 있다
+        visits = await self._board.list_between(ctx, start, end)
+        occupied = await self._board.list_occupied(ctx, start, end)   # 전날 밤에 시작한 방문도 겹칠 수 있다
         closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
         today = local_date(self._now(), tz)
         views = await describe_visits(ctx, visits, self._directory, self._menus)
```

`backend/apps/visit/app/use_cases/list_visit_slots_interactor.py`:

```diff
@@ -5,7 +5,7 @@ from zoneinfo import ZoneInfo
 from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery, SlotView, VisitSlotsView
 from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.domain.errors import VisitInputError
 from visit.domain.services.visit_schedule import (
     STEP_MINUTES,
@@ -22,8 +22,8 @@ from visit.domain.services.visit_schedule import (
 class ListVisitSlotsInteractor(ListVisitSlotsUseCase):
     """예약 ② 화면의 시간 칸. 경고 판단은 서버 한 곳에만 둔다 — 앱은 이 응답만 보고 줄을 긋는다(설계 6.3)."""
 
-    def __init__(self, visits: VisitRepository, schedule: ScheduleRepository) -> None:
-        self._visits = visits
+    def __init__(self, board: VisitBoardRepository, schedule: ScheduleRepository) -> None:
+        self._board = board
         self._schedule = schedule
 
     async def list_visit_slots(self, query: ListVisitSlotsQuery) -> VisitSlotsView:
@@ -40,7 +40,7 @@ class ListVisitSlotsInteractor(ListVisitSlotsUseCase):
         start, end = day_bounds(day, tz)
         occupied = [
             Occupied(v.starts_at, v.ends_at, v.group_key)
-            for v in await self._visits.list_occupied(ctx, start, end) if v.id not in query.exclude
+            for v in await self._board.list_occupied(ctx, start, end) if v.id not in query.exclude
         ]
         closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
         starts = [at_local(day, query.at, tz)] if query.at is not None else hourly_starts(day, settings, tz)
```

`backend/apps/visit/app/use_cases/register_visit_interactor.py`:

```diff
@@ -8,7 +8,8 @@ from visit.app.dtos.register_visit_dto import RegisteredVisitsView, RegisterVisi
 from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.app.services.visit_reader import describe_visits
 from visit.app.services.visit_warnings import warnings_after_save
 from visit.domain.entities.visit import IN_PROGRESS, RESERVED
@@ -24,10 +25,11 @@ from visit.domain.value_objects.new_visit import NewVisit
 
 class RegisterVisitInteractor(RegisterVisitUseCase):
     def __init__(
-        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
-        directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
+        schedule: ScheduleRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
+        self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
@@ -67,7 +69,7 @@ class RegisterVisitInteractor(RegisterVisitUseCase):
         )
 
         warnings = await warnings_after_save(
-            ctx, command.customer_id, starts_at, duration, settings, self._visits, self._schedule
+            ctx, command.customer_id, starts_at, duration, settings, self._board, self._schedule
         )
         return RegisteredVisitsView(
             visits=await describe_visits(ctx, created, self._directory, self._menus), warnings=warnings
```

`backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`:

```diff
@@ -8,7 +8,8 @@ from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, Reschedu
 from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.app.services.visit_locking import lock_visits
 from visit.app.services.visit_reader import describe_visits
 from visit.app.services.visit_warnings import warnings_after_save
@@ -19,10 +20,11 @@ from visit.domain.services.visit_schedule import check_same_day, check_start
 
 class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
     def __init__(
-        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
-        directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
+        schedule: ScheduleRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
+        self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
@@ -39,7 +41,7 @@ class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
         moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
         settings = await self._schedule.ensure(ctx)
         warnings = await warnings_after_save(
-            ctx, locked[0].customer_id, command.starts_at, longest, settings, self._visits, self._schedule
+            ctx, locked[0].customer_id, command.starts_at, longest, settings, self._board, self._schedule
         )
         return RescheduledVisitsView(
             visits=await describe_visits(ctx, moved, self._directory, self._menus), warnings=warnings
```

`backend/apps/visit/app/use_cases/transition_visits_interactor.py`:

```diff
@@ -7,7 +7,8 @@ from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
 from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
+from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.app.services.visit_locking import lock_visits
 from visit.app.services.visit_reader import describe_visits
 from visit.domain.entities.visit import COMPLETED
@@ -17,10 +18,11 @@ from visit.domain.state.visit_state import transition
 
 class TransitionVisitsInteractor(TransitionVisitsUseCase):
     def __init__(
-        self, visits: VisitRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
-        now: Callable[[], datetime],
+        self, visits: VisitWriteRepository, history: VisitHistoryRepository, menus: MenuRepository,
+        directory: CustomerDirectoryPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
+        self._history = history
         self._menus = menus
         self._directory = directory
         self._now = now
@@ -47,7 +49,7 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
 
         if any(v.status == COMPLETED for v in locked) or any(c.status == COMPLETED for _, c in changes):
             customer_id = locked[0].customer_id
-            latest = await self._visits.latest_completed_start(ctx, customer_id)
+            latest = await self._history.latest_completed_start(ctx, customer_id)
             await self._directory.set_last_visit(ctx, customer_id, latest)
         return TransitionedVisitsView(
             visits=await describe_visits(ctx, changed, self._directory, self._menus)
```

`backend/apps/visit/app/use_cases/update_visit_interactor.py`:

```diff
@@ -8,7 +8,8 @@ from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand
 from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.app.services.visit_locking import lock_visits
 from visit.app.services.visit_reader import describe_visits
 from visit.app.services.visit_warnings import warnings_after_save
@@ -19,10 +20,11 @@ from visit.domain.services.visit_schedule import check_duration, check_same_day,
 
 class UpdateVisitInteractor(UpdateVisitUseCase):
     def __init__(
-        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
-        directory: CustomerDirectoryPort, now: Callable[[], datetime],
+        self, visits: VisitWriteRepository, board: VisitBoardRepository, menus: MenuRepository,
+        schedule: ScheduleRepository, directory: CustomerDirectoryPort, now: Callable[[], datetime],
     ) -> None:
         self._visits = visits
+        self._board = board
         self._menus = menus
         self._schedule = schedule
         self._directory = directory
@@ -60,7 +62,7 @@ class UpdateVisitInteractor(UpdateVisitUseCase):
         if updated.is_active:
             settings = await self._schedule.ensure(ctx)
             warnings = await warnings_after_save(
-                ctx, updated.customer_id, updated.starts_at, updated.duration_minutes, settings, self._visits,
+                ctx, updated.customer_id, updated.starts_at, updated.duration_minutes, settings, self._board,
                 self._schedule,
             )
         [view] = await describe_visits(ctx, [updated], self._directory, self._menus)
```

`backend/apps/visit/app/use_cases/visit_ledger_interactor.py`:

```diff
@@ -6,33 +6,33 @@ from datetime import datetime
 from hub.app.dtos.shop_context import ShopContext
 from hub.app.dtos.upcoming_visit import UpcomingVisit
 from hub.app.ports.visit_ledger_port import VisitLedgerPort
-from visit.app.ports.output.visit_repository import VisitRepository
+from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
 from visit.domain.services.visit_schedule import day_bounds, local_date
 
 
 class VisitLedgerInteractor(VisitLedgerPort):
     """허브의 VisitLedgerPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""
 
-    def __init__(self, visits: VisitRepository, now: Callable[[], datetime]) -> None:
-        self._visits = visits
+    def __init__(self, ledger: VisitLedgerRepository, now: Callable[[], datetime]) -> None:
+        self._ledger = ledger
         self._now = now
 
     async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
-        return await self._visits.pet_has_visits(ctx, pet_id, active_only=False)
+        return await self._ledger.pet_has_visits(ctx, pet_id, active_only=False)
 
     async def pet_has_upcoming(self, ctx: ShopContext, pet_id: int) -> bool:
-        return await self._visits.pet_has_visits(ctx, pet_id, active_only=True)
+        return await self._ledger.pet_has_visits(ctx, pet_id, active_only=True)
 
     async def customer_has_upcoming(self, ctx: ShopContext, customer_id: int) -> bool:
-        return await self._visits.customer_has_active(ctx, customer_id)
+        return await self._ledger.customer_has_active(ctx, customer_id)
 
     async def no_show_count(self, ctx: ShopContext, customer_id: int) -> int:
-        return await self._visits.count_no_show(ctx, customer_id)
+        return await self._ledger.count_no_show(ctx, customer_id)
 
     async def upcoming_for_customer(self, ctx: ShopContext, customer_id: int, limit: int) -> list[UpcomingVisit]:
         today_start, _ = day_bounds(local_date(self._now(), ctx.timezone), ctx.timezone)
-        found = await self._visits.list_active_from(ctx, customer_id, today_start, limit)
+        found = await self._ledger.list_active_from(ctx, customer_id, today_start, limit)
         return [UpcomingVisit(visit_id=v.id, pet_id=v.pet_id, starts_at=v.starts_at) for v in found]
 
     async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
-        await self._visits.clear_memos(ctx, customer_id)
+        await self._ledger.clear_memos(ctx, customer_id)
```

`backend/apps/visit/dependencies/get_next_visit_draft_provider.py`:

```diff
@@ -7,4 +7,5 @@ from visit.dependencies.visit_wiring import build_menu_repository, build_visit_r
 
 
 def get_get_next_visit_draft_use_case(db: DbSession) -> GetNextVisitDraftUseCase:
-    return GetNextVisitDraftInteractor(visits=build_visit_repository(db), menus=build_menu_repository(db))
+    visits = build_visit_repository(db)
+    return GetNextVisitDraftInteractor(visits=visits, history=visits, menus=build_menu_repository(db))
```

`backend/apps/visit/dependencies/get_visit_calendar_provider.py`:

```diff
@@ -9,5 +9,5 @@ from visit.domain.services.visit_schedule import utc_now
 
 def get_get_visit_calendar_use_case(db: DbSession) -> GetVisitCalendarUseCase:
     return GetVisitCalendarInteractor(
-        visits=build_visit_repository(db), schedule=build_schedule_repository(db), now=utc_now
+        board=build_visit_repository(db), schedule=build_schedule_repository(db), now=utc_now
     )
```

`backend/apps/visit/dependencies/get_visit_defaults_provider.py`:

```diff
@@ -12,5 +12,5 @@ from visit.dependencies.visit_wiring import (
 
 def get_get_visit_defaults_use_case(db: DbSession) -> GetVisitDefaultsUseCase:
     return GetVisitDefaultsInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db), schedule=build_schedule_repository(db)
+        history=build_visit_repository(db), menus=build_menu_repository(db), schedule=build_schedule_repository(db)
     )
```

`backend/apps/visit/dependencies/get_visit_provider.py`:

```diff
@@ -13,6 +13,7 @@ from visit.dependencies.visit_wiring import build_menu_repository, build_visit_r
 def get_get_visit_use_case(
     db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
 ) -> GetVisitUseCase:
+    visits = build_visit_repository(db)
     return GetVisitInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db), directory=directory
+        visits=visits, history=visits, ledger=visits, menus=build_menu_repository(db), directory=directory
     )
```

`backend/apps/visit/dependencies/list_day_visits_provider.py`:

```diff
@@ -19,6 +19,6 @@ def get_list_day_visits_use_case(
     db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
 ) -> ListDayVisitsUseCase:
     return ListDayVisitsInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db),
+        board=build_visit_repository(db), menus=build_menu_repository(db),
         schedule=build_schedule_repository(db), directory=directory, now=utc_now,
     )
```

`backend/apps/visit/dependencies/list_visit_slots_provider.py`:

```diff
@@ -7,4 +7,4 @@ from visit.dependencies.visit_wiring import build_schedule_repository, build_vis
 
 
 def get_list_visit_slots_use_case(db: DbSession) -> ListVisitSlotsUseCase:
-    return ListVisitSlotsInteractor(visits=build_visit_repository(db), schedule=build_schedule_repository(db))
+    return ListVisitSlotsInteractor(board=build_visit_repository(db), schedule=build_schedule_repository(db))
```

`backend/apps/visit/dependencies/register_visit_provider.py`:

```diff
@@ -18,7 +18,8 @@ from visit.domain.services.visit_schedule import utc_now
 def get_register_visit_use_case(
     db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
 ) -> RegisterVisitUseCase:
+    visits = build_visit_repository(db)
     return RegisterVisitInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db),
+        visits=visits, board=visits, menus=build_menu_repository(db),
         schedule=build_schedule_repository(db), directory=directory, now=utc_now,
     )
```

`backend/apps/visit/dependencies/reschedule_visits_provider.py`:

```diff
@@ -18,7 +18,8 @@ from visit.domain.services.visit_schedule import utc_now
 def get_reschedule_visits_use_case(
     db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
 ) -> RescheduleVisitsUseCase:
+    visits = build_visit_repository(db)
     return RescheduleVisitsInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db),
+        visits=visits, board=visits, menus=build_menu_repository(db),
         schedule=build_schedule_repository(db), directory=directory, now=utc_now,
     )
```

`backend/apps/visit/dependencies/transition_visits_provider.py`:

```diff
@@ -14,6 +14,7 @@ from visit.domain.services.visit_schedule import utc_now
 def get_transition_visits_use_case(
     db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
 ) -> TransitionVisitsUseCase:
+    visits = build_visit_repository(db)
     return TransitionVisitsInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db), directory=directory, now=utc_now
+        visits=visits, history=visits, menus=build_menu_repository(db), directory=directory, now=utc_now
     )
```

`backend/apps/visit/dependencies/update_visit_provider.py`:

```diff
@@ -18,7 +18,8 @@ from visit.domain.services.visit_schedule import utc_now
 def get_update_visit_use_case(
     db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
 ) -> UpdateVisitUseCase:
+    visits = build_visit_repository(db)
     return UpdateVisitInteractor(
-        visits=build_visit_repository(db), menus=build_menu_repository(db),
+        visits=visits, board=visits, menus=build_menu_repository(db),
         schedule=build_schedule_repository(db), directory=directory, now=utc_now,
     )
```

`backend/apps/visit/dependencies/visit_ledger_provider.py`:

```diff
@@ -8,4 +8,4 @@ from visit.domain.services.visit_schedule import utc_now
 
 
 def get_visit_ledger_use_case(db: DbSession) -> VisitLedgerPort:
-    return VisitLedgerInteractor(visits=build_visit_repository(db), now=utc_now)
+    return VisitLedgerInteractor(ledger=build_visit_repository(db), now=utc_now)
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/test_visit_port_segregation.py -q -p no:cacheprovider` → 5 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 737 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 262 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `get_visit_interactor.py`의 생성자 타입을 `visits: VisitLookupRepository`에서 `visits: VisitWriteRepository`로 → `test_쓰기_포트는_쓰는_유스케이스_넷만_받는다` 실패(GetVisitInteractor 가 목록에 든다).
- `VisitPgRepository`의 바탕 클래스에서 `VisitBoardRepository`를 뺀다 → `test_pg_구현은_다섯_포트를_다_낸다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(visit): 방문 리포지토리를 포트 다섯으로 나눈다 — 찾기·잠금, 쓰기, 이력, 원장, 게시판

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 3: 공용 스텁이 포트 ABC 를 상속한다 — 메서드를 빠뜨리면 인스턴스를 만드는 순간 잡힌다 (B3)

**Files:**
- Create: `backend/apps/visit/tests/test_fakes_are_ports.py`
- Create: `backend/apps/customer/tests/test_fakes_are_ports.py`
- Modify: `_docs/harness.md`
- Modify: `backend/apps/customer/tests/helpers/fakes.py`
- Modify: `backend/apps/visit/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: Task 2 의 포트 다섯, 기존 `MenuRepository`·`ScheduleRepository`·`CustomerDirectoryPort`(visit 스텁), `ConditionTypeRepository`·`CustomerRepository`·`PetRepository`·`CustomerSearchPort`·`VisitLedgerPort`(customer 스텁).
- Produces: `visit.tests.helpers.fakes`의 `FakeSchedule(ScheduleRepository)`·`FakeMenus(MenuRepository)`·`FakeDirectory(CustomerDirectoryPort)`·`FakeVisits(VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository)`; `customer.tests.helpers.fakes`의 `FakeConditionTypes(ConditionTypeRepository)`·`FakeCustomers(CustomerRepository)`·`FakePets(PetRepository)`·`FakeSearch(CustomerSearchPort)`·`FakeLedger(VisitLedgerPort)`. 생성자·메서드는 그대로다. ④-1 이 포트에 메서드를 더하면 이 스텁들도 함께 더해야 인스턴스가 만들어진다.

감사 결과(설계 4.1 B3): 스텁이 ABC 를 상속하지 않아 포트에 메서드를 더하고 스텁을 빠뜨리면 `AttributeError`로 늦게 잡혔다. 공용 스텁(`apps/*/tests/helpers/fakes.py`)만 상속한다 — 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 그대로 둔다(하네스 문서에 적는다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/test_fakes_are_ports.py`:

```python
"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_board_repository import VisitBoardRepository
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
from visit.app.ports.output.visit_lookup_repository import VisitLookupRepository
from visit.app.ports.output.visit_write_repository import VisitWriteRepository
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, FakeVisits


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    assert isinstance(FakeSchedule(), ScheduleRepository)
    assert isinstance(FakeMenus(), MenuRepository)
    assert isinstance(FakeDirectory(), CustomerDirectoryPort)
    visits = FakeVisits()
    for port in (VisitLookupRepository, VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository,
                 VisitBoardRepository):
        assert isinstance(visits, port), port.__name__
```

`backend/apps/customer/tests/test_fakes_are_ports.py`:

```python
"""공용 스텁이 포트 ABC 를 상속하고 추상 메서드를 다 채웠는지 — 인스턴스를 만드는 것으로 확인한다."""
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.tests.helpers.fakes import (
    FakeConditionTypes,
    FakeCustomers,
    FakeLedger,
    FakePets,
    FakeSearch,
    Journal,
)
from hub.app.ports.visit_ledger_port import VisitLedgerPort


def test_스텁은_포트를_상속하고_추상_메서드가_남아_있지_않다():
    journal = Journal()
    customers = FakeCustomers(journal)
    assert isinstance(FakeConditionTypes(), ConditionTypeRepository)
    assert isinstance(customers, CustomerRepository)
    assert isinstance(FakePets(journal, customers), PetRepository)
    assert isinstance(FakeSearch(journal), CustomerSearchPort)
    assert isinstance(FakeLedger(journal), VisitLedgerPort)
```

`backend/apps/customer/tests/helpers/fakes.py`:

```diff
@@ -1,4 +1,8 @@
-"""customer 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
+"""customer 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다.
+
+스텁은 포트 ABC 를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간 잡힌다.
+`apps/customer/tests/test_fakes_are_ports.py`가 이를 확인한다.
+"""
 from __future__ import annotations
 
 from dataclasses import replace
@@ -6,10 +10,15 @@ from datetime import date, datetime, timezone
 from decimal import Decimal
 
 from customer.app.dtos.customer_search_dto import SearchPage
+from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
+from customer.app.ports.output.customer_repository import CustomerRepository
+from customer.app.ports.output.customer_search_port import CustomerSearchPort
+from customer.app.ports.output.pet_repository import PetRepository
 from customer.domain.entities.condition_type import ConditionType
 from customer.domain.entities.customer import Customer
 from customer.domain.entities.pet import Pet, PetCondition
 from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError, PetNotFoundError
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 TODAY = date(2026, 9, 22)
 NOW = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)
@@ -25,12 +34,12 @@ class Journal(list):
     """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""
 
 
-class FakeConditionTypes:
+class FakeConditionTypes(ConditionTypeRepository):
     async def list_all(self):
         return [ConditionType(code=c, label=l, sort_order=i) for i, (c, l) in enumerate(LABELS.items())]
 
 
-class FakeCustomers:
+class FakeCustomers(CustomerRepository):
     def __init__(self, journal: Journal) -> None:
         self.journal = journal
         self.rows: dict[int, Customer] = {}
@@ -86,7 +95,7 @@ class FakeCustomers:
         self.journal.append(("anonymize", customer_id))
 
 
-class FakePets:
+class FakePets(PetRepository):
     def __init__(self, journal: Journal, customers: FakeCustomers) -> None:
         self.journal = journal
         self.customers = customers
@@ -161,7 +170,7 @@ class FakePets:
         )
 
 
-class FakeSearch:
+class FakeSearch(CustomerSearchPort):
     def __init__(self, journal: Journal, page: SearchPage | None = None, pet_count: int = 0) -> None:
         self.journal = journal
         self.page = page or SearchPage(customer_ids=[], next_cursor=None)
@@ -189,7 +198,7 @@ class FakeSearch:
         return self.matches[:limit]
 
 
-class FakeLedger:
+class FakeLedger(VisitLedgerPort):
     """VisitLedgerPort 스텁. 반려동물·고객마다 방문이 있는지, 앞으로의 예약이 있는지를 정해 둔다."""
 
     def __init__(self, journal: Journal) -> None:
```

`backend/apps/visit/tests/helpers/fakes.py`:

```diff
@@ -1,4 +1,8 @@
-"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
+"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다.
+
+스텁은 포트 ABC 를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 AttributeError 로 늦게 잡히는 대신
+인스턴스를 만드는 순간(TypeError) 잡힌다. `apps/visit/tests/test_fakes_are_ports.py`가 이를 확인한다.
+"""
 from __future__ import annotations
 
 from dataclasses import replace
@@ -6,6 +10,13 @@ from decimal import Decimal
 
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
+from hub.app.ports.customer_directory_port import CustomerDirectoryPort
+from visit.app.ports.output.menu_repository import MenuRepository
+from visit.app.ports.output.schedule_repository import ScheduleRepository
+from visit.app.ports.output.visit_board_repository import VisitBoardRepository
+from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
+from visit.app.ports.output.visit_ledger_repository import VisitLedgerRepository
+from visit.app.ports.output.visit_write_repository import VisitWriteRepository
 from visit.domain.entities.menu import Menu
 from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
 from visit.domain.errors import (
@@ -23,7 +34,7 @@ class Journal(list):
     """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""
 
 
-class FakeSchedule:
+class FakeSchedule(ScheduleRepository):
     def __init__(self, journal: Journal | None = None, settings=DEFAULT_SETTINGS) -> None:
         self.journal = journal if journal is not None else Journal()
         self.settings = settings
@@ -53,7 +64,7 @@ class FakeSchedule:
         self.closed.pop((ctx.shop_id, day), None)
 
 
-class FakeMenus:
+class FakeMenus(MenuRepository):
     def __init__(self, journal: Journal | None = None) -> None:
         self.journal = journal if journal is not None else Journal()
         self.rows: dict[int, Menu] = {}
@@ -106,7 +117,7 @@ class FakeMenus:
         return self.rows[menu_id]
 
 
-class FakeDirectory:
+class FakeDirectory(CustomerDirectoryPort):
     """CustomerDirectoryPort 스텁. families 는 {고객 ID: (매장 ID, {반려동물 ID: 무지개다리 여부})}."""
 
     def __init__(self, journal: Journal | None = None) -> None:
@@ -153,7 +164,7 @@ class FakeDirectory:
         return list(self.candidates)
 
 
-class FakeVisits:
+class FakeVisits(VisitWriteRepository, VisitHistoryRepository, VisitLedgerRepository, VisitBoardRepository):
     """visits 표 스텁 — pg 구현처럼 다섯 포트(찾기·잠금, 쓰기, 이력, 원장, 게시판)를 한 객체가 다 낸다."""
 
     def __init__(self, journal: Journal | None = None) -> None:
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/test_fakes_are_ports.py apps/customer/tests/test_fakes_are_ports.py -q -p no:cacheprovider`
Expected: 두 테스트 모두 `assert isinstance(...)`에서 AssertionError(스텁이 아직 포트를 상속하지 않는다).

- [ ] **Step 3: 구현한다**

`_docs/harness.md`:

```diff
@@ -27,7 +27,7 @@
 - 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 마이그레이션 결과와 ORM이 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다.
 - 구조 위반은 테스트가 아니라 import-linter가 잡는다. 구조를 건드린 변경은 테스트와 구조 계약을 둘 다 돌린다. 계약은 6종이다 — 설계 문서가 말하는 5종에 "core는 스포크를 import하지 않는다"를 하네스에서 더했다.
 - 라우터를 추가하거나 옮긴 변경은 라우트 표를 변경 전후로 비교한다.
-- 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다.
+- 유스케이스는 스텁 포트로 검증한다. mock 프레임워크보다 스텁 구현을 쓴다. 공용 스텁(`apps/*/tests/helpers/fakes.py`)은 포트 ABC를 상속한다 — 포트에 메서드를 더하고 스텁을 빠뜨리면 인스턴스를 만드는 순간 잡힌다(`apps/*/tests/test_fakes_are_ports.py`). 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다.
 - `tests/integration/`은 두 프로세스의 실제 앱 객체에 붙어 프로바이더·DB 커밋·Redis까지 통과한다. 인증 프로세스의 개인키는 테스트마다 새로 만든 키로 바꿔 넣는다.
 - 스포크를 새로 만들면 첫 통합 테스트로 "A매장 멤버가 B매장의 경로를 부르면 403"(테넌트 격리)을 둔다.
 - 허브 포트 자리를 새로 만들어도 더할 목록은 없다. `tests/route_inspection.py`가 두 앱의 라우트 의존성 트리를 훑어 ① 채우지 않은 허브 포트 자리 ② `{shop_id}` 경로인데 `get_shop_context`를 거치지 않는 라우트 ③ `/v1/platform/` 경로인데 `require_operator`를 거치지 않는 라우트를 잡는다. API 프로세스는 `tests/test_hub_port_binding.py`가, 인증 프로세스는 `tests/integration/test_route_wiring.py`가 돌린다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/test_fakes_are_ports.py apps/customer/tests/test_fakes_are_ports.py -q -p no:cacheprovider` → 2 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 739 passed

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `visit/tests/helpers/fakes.py`의 `class FakeMenus(MenuRepository):`를 `class FakeMenus:`로 → `apps/visit/tests/test_fakes_are_ports.py` 실패.
- `customer/tests/helpers/fakes.py`의 `FakeSearch.rebuild_search_entry` 메서드 이름을 바꾼다 → `apps/customer/tests/test_fakes_are_ports.py`가 `TypeError: Can't instantiate abstract class`로 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "test: 공용 스텁이 포트 ABC 를 상속한다 — 메서드를 빠뜨리면 인스턴스를 만드는 순간 잡힌다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 4: 상태 전이의 행동 축을 닫고 완료 후속 처리를 한 곳으로 — `transition()`은 행동 이름으로 상태 메서드를 찾고, 되돌리기의 가족 확인 대상은 도메인이 정한다 (B4·B6)

**Files:**
- Modify: `backend/apps/visit/domain/state/visit_state.py`
- Create: `backend/apps/visit/app/services/completion_effects.py`
- Modify: `backend/apps/visit/app/use_cases/transition_visits_interactor.py`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`
- Create: `backend/apps/visit/tests/app/services/__init__.py`
- Create: `backend/apps/visit/tests/app/services/test_completion_effects.py`
- Modify: `backend/apps/visit/tests/domain/test_visit_state.py`

**Interfaces:**
- Consumes: Task 2 의 `TransitionVisitsInteractor(visits: VisitWriteRepository, history: VisitHistoryRepository, menus, directory, now)`, `lock_visits`, `VisitHistoryRepository.latest_completed_start`, `CustomerDirectoryPort.set_last_visit`.
- Produces: `visit.domain.state.visit_state.TransitionRequest(now, tz, cancel_reason=None)` — 모든 상태 메서드가 `(visit, request)`를 받는다; `check_action(action, cancel_reason)`; `SLOT_RECLAIMING_ACTIONS = frozenset({"revert"})`; `pets_to_confirm(action, visits: list[Visit]) -> tuple[int, ...]`; `transition(visit, action, now, tz, cancel_reason=None)` 서명 그대로. `visit.app.services.completion_effects.completion_changed(before, after) -> bool`, `apply_completion_effects(ctx, before, after, history, directory) -> None` — ④-1 의 기록 슬라이스가 몸무게 동기화를 이 함수에 더한다. `TransitionVisitsInteractor.transition_visits`의 호출 순서(journal)는 그대로: lock_family → lock_visits → apply_changes → (완료 변화 시) set_last_visit.

감사 결과(설계 4.1 B4·B6): 전이 인터랙터에 되돌리기 전용 `if` 둘과 완료 후속 동기화가 쌓여 있었고, `transition()`은 행동마다 if 체인이었다. 행동을 더할 때 고치는 곳은 이제 둘 — `ACTIONS`와 바탕 클래스의 같은 이름 메서드. 되돌리기가 가족 확인을 거쳐야 한다는 사실은 `SLOT_RECLAIMING_ACTIONS`가 말하고, 인터랙터는 행동 이름을 모른다. 완료 후속 처리는 `completion_effects.py` 한 곳이다. 남는 것(결정 기록 007): 되돌리기가 아니어도 잠그기 전에 `get_many`를 한 번 읽는다(`lock_visits`도 읽으므로 조회 하나가 늘었다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/app/services/__init__.py`:

```python

```

`backend/apps/visit/tests/app/services/test_completion_effects.py`:

```python
"""완료 후속 처리 — 완료가 생기거나 풀릴 때만 최근 방문을 다시 계산해 customer 에 넘긴다."""
from dataclasses import replace

from visit.app.services.completion_effects import apply_completion_effects, completion_changed
from visit.tests.helpers.builders import ctx, kst, visit
from visit.tests.helpers.fakes import FakeDirectory, FakeVisits, Journal


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101,))
    return journal, visits, directory


def test_완료가_생기면_바뀐_것이다():
    before = [visit(status="in_progress", started_at=kst(9, 23, 13))]
    after = [replace(before[0], status="completed", completed_at=kst(9, 23, 14))]
    assert completion_changed(before, after)


def test_완료가_풀리면_바뀐_것이다():
    before = [visit(status="completed", started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))]
    after = [replace(before[0], status="reserved", started_at=None, completed_at=None)]
    assert completion_changed(before, after)


def test_완료와_상관없는_전이는_바뀐_것이_아니다():
    before = [visit(status="reserved")]
    after = [replace(before[0], status="canceled", canceled_at=kst(9, 23, 15), cancel_reason="shop_reason")]
    assert not completion_changed(before, after)


async def test_완료가_바뀌면_그_보호자의_마지막_완료_시각을_넘긴다():
    journal, visits, directory = _setup()
    earlier = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                          started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    today = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13), status="completed",
                        started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))
    reverted = replace(today, status="reserved", started_at=None, completed_at=None)
    visits.rows[today.id] = reverted
    await apply_completion_effects(ctx(), [today], [reverted], visits, directory)
    assert journal == [("set_last_visit", 1, earlier.starts_at)]


async def test_완료가_바뀌지_않으면_아무것도_부르지_않는다():
    journal, visits, directory = _setup()
    reserved = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    started = replace(reserved, status="in_progress", started_at=kst(9, 23, 13))
    await apply_completion_effects(ctx(), [reserved], [started], visits, directory)
    assert journal == []
```

`backend/apps/visit/tests/domain/test_visit_state.py`:

```diff
@@ -104,3 +104,18 @@ def test_모르는_사유와_모르는_행동은_VALIDATION_ERROR_다():
         _apply("reserved", "cancel", reason="weather")
     with pytest.raises(VisitInputError):
         _apply("reserved", "teleport")
+
+
+def test_모든_행동은_바탕_상태의_메서드다():
+    """transition() 은 행동 이름으로 상태 객체의 메서드를 찾는다 — 이름을 ACTIONS 에만 더하면 여기서 걸린다."""
+    from visit.domain.state.visit_state import ACTIONS, VisitState
+
+    assert all(callable(getattr(VisitState, action, None)) for action in ACTIONS)
+
+
+def test_되돌리기만_반려동물을_가족_확인에_넘긴다():
+    from visit.domain.state.visit_state import pets_to_confirm
+
+    visits = [visit(id=1, pet_id=102), visit(id=2, pet_id=101), visit(id=3, pet_id=None)]
+    assert pets_to_confirm("revert", visits) == (101, 102)
+    assert all(pets_to_confirm(action, visits) == () for action in ("start", "complete", "cancel", "no_show"))
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/services/test_completion_effects.py apps/visit/tests/domain/test_visit_state.py -q -p no:cacheprovider`
Expected: `test_completion_effects.py`는 수집 단계 `ModuleNotFoundError: visit.app.services.completion_effects`; `test_visit_state.py`는 새 테스트 둘이 `ImportError: cannot import name 'pets_to_confirm'`(나머지 상태 테스트는 통과).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/state/visit_state.py`:

```diff
@@ -2,6 +2,9 @@
 
 행동은 다섯 가지다: 시작(start), 완료(complete), 취소(cancel), 노쇼(no_show), 되돌리기(revert).
 예약됨에서 바로 완료하면 "바로 완료"다(시작 시각 = 완료 시각). 미용 중인 방문의 취소는 되돌린 뒤 한다.
+
+행동을 더할 때 고치는 곳은 둘이다 — `ACTIONS`에 이름을, 바탕 클래스에 같은 이름의 메서드(기본은 거절)를.
+`transition()`은 행동 이름으로 상태 객체의 메서드를 찾아 부르므로 if 체인을 늘리지 않는다.
 """
 from __future__ import annotations
 
@@ -24,6 +27,9 @@ from visit.domain.services.visit_schedule import local_date
 
 ACTIONS = frozenset({"start", "complete", "cancel", "no_show", "revert"})
 
+# 끝난 방문을 다시 시간을 차지하는 예약으로 만드는 행동 — 가족 확인(무지개다리 아이인지)을 다시 거쳐야 한다(V7).
+SLOT_RECLAIMING_ACTIONS = frozenset({"revert"})
+
 
 @dataclass(frozen=True)
 class StatusChange:
@@ -36,22 +42,31 @@ class StatusChange:
     cancel_reason: str | None = None
 
 
+@dataclass(frozen=True)
+class TransitionRequest:
+    """행동 하나에 딸린 입력. 모든 행동이 같은 모양을 받으므로 상태 메서드의 서명이 하나다."""
+
+    now: datetime
+    tz: str
+    cancel_reason: str | None = None
+
+
 class VisitState(ABC):
     status: ClassVar[str]
 
-    def start(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
+    def start(self, visit: Visit, request: TransitionRequest) -> StatusChange:
         raise self._refuse("시작")
 
-    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
+    def complete(self, visit: Visit, request: TransitionRequest) -> StatusChange:
         raise self._refuse("완료")
 
-    def cancel(self, visit: Visit, now: datetime, reason: str) -> StatusChange:
+    def cancel(self, visit: Visit, request: TransitionRequest) -> StatusChange:
         raise self._refuse("취소")
 
-    def no_show(self, visit: Visit, now: datetime) -> StatusChange:
+    def no_show(self, visit: Visit, request: TransitionRequest) -> StatusChange:
         raise self._refuse("노쇼 처리")
 
-    def revert(self, visit: Visit) -> StatusChange:
+    def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
         # 알림장을 보낸 뒤에는 되돌릴 수 없다는 규칙이 ⑤에서 더해진다.
         return StatusChange(status=RESERVED)
 
@@ -59,39 +74,39 @@ class VisitState(ABC):
         return VisitStateConflictError(f"지금 상태({self.status})에서는 {action}할 수 없습니다.")
 
 
-def _check_day_reached(visit: Visit, now: datetime, tz: str) -> None:
-    if local_date(visit.starts_at, tz) > local_date(now, tz):
+def _check_day_reached(visit: Visit, request: TransitionRequest) -> None:
+    if local_date(visit.starts_at, request.tz) > local_date(request.now, request.tz):
         raise VisitNotYetError("예약한 날이 되어야 시작하거나 완료할 수 있습니다.")
 
 
 class ReservedState(VisitState):
     status = RESERVED
 
-    def start(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
-        _check_day_reached(visit, now, tz)
-        return StatusChange(status=IN_PROGRESS, started_at=now)
+    def start(self, visit: Visit, request: TransitionRequest) -> StatusChange:
+        _check_day_reached(visit, request)
+        return StatusChange(status=IN_PROGRESS, started_at=request.now)
 
-    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
-        _check_day_reached(visit, now, tz)
-        return StatusChange(status=COMPLETED, started_at=now, completed_at=now)   # 바로 완료
+    def complete(self, visit: Visit, request: TransitionRequest) -> StatusChange:
+        _check_day_reached(visit, request)
+        return StatusChange(status=COMPLETED, started_at=request.now, completed_at=request.now)   # 바로 완료
 
-    def cancel(self, visit: Visit, now: datetime, reason: str) -> StatusChange:
-        return StatusChange(status=CANCELED, canceled_at=now, cancel_reason=reason)
+    def cancel(self, visit: Visit, request: TransitionRequest) -> StatusChange:
+        return StatusChange(status=CANCELED, canceled_at=request.now, cancel_reason=request.cancel_reason)
 
-    def no_show(self, visit: Visit, now: datetime) -> StatusChange:
-        if visit.starts_at > now:
+    def no_show(self, visit: Visit, request: TransitionRequest) -> StatusChange:
+        if visit.starts_at > request.now:
             raise VisitNotYetError("예약 시각이 지나야 노쇼로 처리할 수 있습니다.")
         return StatusChange(status=NO_SHOW)
 
-    def revert(self, visit: Visit) -> StatusChange:
+    def revert(self, visit: Visit, request: TransitionRequest) -> StatusChange:
         raise self._refuse("되돌리기")
 
 
 class InProgressState(VisitState):
     status = IN_PROGRESS
 
-    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
-        return StatusChange(status=COMPLETED, started_at=visit.started_at, completed_at=now)
+    def complete(self, visit: Visit, request: TransitionRequest) -> StatusChange:
+        return StatusChange(status=COMPLETED, started_at=visit.started_at, completed_at=request.now)
 
 
 class CompletedState(VisitState):
@@ -112,23 +127,27 @@ _STATES: dict[str, VisitState] = {
 }
 
 
-def transition(
-    visit: Visit, action: str, now: datetime, tz: str, cancel_reason: str | None = None
-) -> StatusChange:
-    """방문 하나에 행동 하나를 적용한 결과. 취소 사유는 취소에만, 그리고 취소에는 반드시 있어야 한다."""
+def check_action(action: str, cancel_reason: str | None) -> None:
+    """행동 이름과 취소 사유의 짝을 확인한다. 취소 사유는 취소에만, 그리고 취소에는 반드시 있어야 한다."""
     if action not in ACTIONS:
         raise VisitInputError("알 수 없는 행동입니다.")
     if (action == "cancel") != (cancel_reason is not None):
         raise VisitInputError("취소 사유는 취소할 때만, 반드시 보내 주세요.")
     if cancel_reason is not None and cancel_reason not in CANCEL_REASONS:
         raise VisitInputError("취소 사유가 올바르지 않습니다.")
-    state = _STATES[visit.status]
-    if action == "start":
-        return state.start(visit, now, tz)
-    if action == "complete":
-        return state.complete(visit, now, tz)
-    if action == "cancel":
-        return state.cancel(visit, now, cancel_reason)
-    if action == "no_show":
-        return state.no_show(visit, now)
-    return state.revert(visit)
+
+
+def pets_to_confirm(action: str, visits: list[Visit]) -> tuple[int, ...]:
+    """이 행동 앞에서 가족 확인에 넘길 반려동물 — 시간을 다시 차지하는 행동이면 그 방문들의 아이, 아니면 없음."""
+    if action not in SLOT_RECLAIMING_ACTIONS:
+        return ()
+    return tuple(sorted({v.pet_id for v in visits if v.pet_id is not None}))
+
+
+def transition(
+    visit: Visit, action: str, now: datetime, tz: str, cancel_reason: str | None = None
+) -> StatusChange:
+    """방문 하나에 행동 하나를 적용한 결과."""
+    check_action(action, cancel_reason)
+    handler = getattr(_STATES[visit.status], action)
+    return handler(visit, TransitionRequest(now=now, tz=tz, cancel_reason=cancel_reason))
```

`backend/apps/visit/app/services/completion_effects.py`:

```python
"""완료가 생기거나 풀린 뒤의 후속 처리 — 같은 트랜잭션 안에서, 방문 행을 잠근 채로.

지금은 하나다: 그 보호자의 마지막 완료 방문 시작 시각을 customer 에 넘긴다(고객 목록 '최근 방문순').
④ 기록 슬라이스는 몸무게 동기화를 여기에 더한다 — 전이·기록 두 유스케이스가 같은 함수를 부르므로 후속 처리가
한 곳에 남는다(단일 책임: 전이 인터랙터는 잠금·전이·후속 호출만 한다).
"""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
from visit.domain.entities.visit import COMPLETED, Visit


def completion_changed(before: list[Visit], after: list[Visit]) -> bool:
    """완료 방문이 생겼거나 사라졌는가. 전이 전후의 같은 방문 목록을 받는다."""
    return any(v.status == COMPLETED for v in before) or any(v.status == COMPLETED for v in after)


async def apply_completion_effects(
    ctx: ShopContext, before: list[Visit], after: list[Visit],
    history: VisitHistoryRepository, directory: CustomerDirectoryPort,
) -> None:
    """완료 여부가 바뀌었으면 후속 처리를 한다. 아니면 아무것도 부르지 않는다."""
    if not completion_changed(before, after):
        return
    customer_id = after[0].customer_id
    latest = await history.latest_completed_start(ctx, customer_id)
    await directory.set_last_visit(ctx, customer_id, latest)
```

`backend/apps/visit/app/use_cases/transition_visits_interactor.py`:

```diff
@@ -9,14 +9,16 @@ from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUse
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.visit_history_repository import VisitHistoryRepository
 from visit.app.ports.output.visit_write_repository import VisitWriteRepository
+from visit.app.services.completion_effects import apply_completion_effects
 from visit.app.services.visit_locking import lock_visits
 from visit.app.services.visit_reader import describe_visits
-from visit.domain.entities.visit import COMPLETED
 from visit.domain.errors import VisitStateConflictError
-from visit.domain.state.visit_state import transition
+from visit.domain.state.visit_state import pets_to_confirm, transition
 
 
 class TransitionVisitsInteractor(TransitionVisitsUseCase):
+    """잠그고 → 전이하고 → 후속 처리를 부른다. 어느 행동이 무엇을 확인하는지는 도메인(`visit_state`)이 정한다."""
+
     def __init__(
         self, visits: VisitWriteRepository, history: VisitHistoryRepository, menus: MenuRepository,
         directory: CustomerDirectoryPort, now: Callable[[], datetime],
@@ -28,29 +30,20 @@ class TransitionVisitsInteractor(TransitionVisitsUseCase):
         self._now = now
 
     async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView:
-        ctx = command.ctx
-        # 되돌리기는 끝난 방문을 다시 시간을 차지하는 예약으로 만든다 — 그 아이가 무지개다리를 건넜으면
-        # 가족 확인이 막는다(V7). 다른 행동은 새로 시간을 차지하지 않아 보호자만 잠근다.
-        pet_ids: tuple[int, ...] = ()
-        if command.action == "revert":
-            pet_ids = tuple(sorted({
-                v.pet_id for v in await self._visits.get_many(ctx, list(command.visit_ids)) if v.pet_id is not None
-            }))
-        locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory, pet_ids)
+        ctx, ids = command.ctx, list(command.visit_ids)
+        # 시간을 다시 차지하는 행동(되돌리기)만 그 아이가 무지개다리를 건넜는지 가족 확인을 거친다(V7).
+        pet_ids = pets_to_confirm(command.action, await self._visits.get_many(ctx, ids))
+        locked = await lock_visits(ctx, ids, self._visits, self._directory, pet_ids)
         # 가족 확인은 잠그기 전 반려동물로 판단했다 — 잠근 뒤 다시 본 값이 다르면(그 사이 다른 요청이 반려동물을
         # 바꿨을 수 있다) 낡은 확인이라 다시 불러오게 한다.
-        if command.action == "revert" and {v.pet_id for v in locked if v.pet_id is not None} != set(pet_ids):
+        if pets_to_confirm(command.action, locked) != pet_ids:
             raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")
 
         now = self._now()
         # 잠근 뒤 다시 읽은 상태로 모두 판정한 다음에 쓴다 — 하나라도 안 되면 아무것도 바꾸지 않는다.
         changes = [(v.id, transition(v, command.action, now, ctx.timezone, command.cancel_reason)) for v in locked]
         changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)
-
-        if any(v.status == COMPLETED for v in locked) or any(c.status == COMPLETED for _, c in changes):
-            customer_id = locked[0].customer_id
-            latest = await self._history.latest_completed_start(ctx, customer_id)
-            await self._directory.set_last_visit(ctx, customer_id, latest)
+        await apply_completion_effects(ctx, locked, changed, self._history, self._directory)
         return TransitionedVisitsView(
             visits=await describe_visits(ctx, changed, self._directory, self._menus)
         )
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -5,6 +5,7 @@
 - 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
 - `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
 - 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK).
+- 행동(시작·완료·취소·노쇼·되돌리기)은 `visit_state.ACTIONS`와 바탕 상태 클래스의 같은 이름 메서드가 정한다. `transition()`은 행동 이름으로 메서드를 찾으므로 행동을 더할 때 if 체인을 늘리지 않는다. 시간을 다시 차지하는 행동(`SLOT_RECLAIMING_ACTIONS`)만 가족 확인에 반려동물을 넘긴다(`pets_to_confirm`). 완료가 생기거나 풀린 뒤의 후속 처리는 `app/services/completion_effects.py` 한 곳이다 — 전이·기록(④) 유스케이스가 같은 함수를 부른다.
 - **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
 - `visits` 표의 리포지토리는 포트 다섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository`), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
 - customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/app/services/test_completion_effects.py apps/visit/tests/domain/test_visit_state.py apps/visit/tests/app/use_cases/test_transition_visits_interactor.py -q -p no:cacheprovider` → 전부 통과(후속 처리 5·상태 전이 기존 + 2·인터랙터 9)

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 746 passed

Run (`infra/`): `docker compose run --rm backend pytest tests/integration/test_visit_locking.py tests/integration/test_visit_flow_wiring.py -q -p no:cacheprovider -m integration` → 9 passed

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `completion_effects.apply_completion_effects`에서 `if not completion_changed(before, after): return` 두 줄을 뺀다 → `test_완료가_바뀌지_않으면_아무것도_부르지_않는다` 실패.
- `visit_state.pets_to_confirm`이 항상 `()`를 돌려주게 한다 → `test_되돌리기만_반려동물을_가족_확인에_넘긴다`와 인터랙터의 `test_완료를_되돌리면_최근_방문을_다시_계산한다`·`test_무지개다리_아이의_방문은_되돌리지_못한다`·`test_되돌리기_잠그는_사이_반려동물이_바뀌면_다시_보고_거절한다` 실패(4개).
- 인터랙터의 `if pets_to_confirm(command.action, locked) != pet_ids: raise ...`를 `if False:`로 → `test_되돌리기_잠그는_사이_반려동물이_바뀌면_다시_보고_거절한다` 실패.

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(visit): 상태 전이의 행동 축을 닫고 완료 후속 처리를 한 곳으로 — transition() 은 행동 이름으로 상태 메서드를 찾고, 되돌리기의 가족 확인 대상은 도메인이 정한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 5: 방문 상태의 단일 원천 — `domain/state/visit_status` 표에서 살아 있음·마릿수·시작 시각 집합과 ORM CHECK·부분 색인·하루 집계 칸을 파생한다 (B5)

**Files:**
- Create: `backend/apps/visit/domain/state/visit_status.py`
- Modify: `backend/apps/visit/domain/entities/visit.py`
- Modify: `backend/apps/visit/domain/services/visit_board.py`
- Modify: `backend/apps/visit/adapter/outbound/orm/visit_orm.py`
- Modify: `backend/apps/visit/app/dtos/list_day_visits_dto.py`
- Modify: `backend/apps/visit/app/use_cases/list_day_visits_interactor.py`
- Modify: `backend/apps/visit/_docs/CLAUDE.md`
- Create: `backend/apps/visit/tests/adapter/test_visit_orm_status.py`
- Create: `backend/apps/visit/tests/domain/test_visit_status.py`

**Interfaces:**
- Consumes: `visit.domain.entities.visit`의 상태 상수·`ACTIVE_STATUSES`, `visit_board.COUNTED`, `VisitOrm.__table_args__`의 CHECK·부분 색인, `DayCountsView`, `list_day_visits_interactor`.
- Produces: `visit.domain.state.visit_status.VisitStatus(code, is_active, counts_as_visit, has_started_at)`, `STATUSES: tuple[VisitStatus, ...]`(순서 = 마이그레이션 0006 의 CHECK 순서), `ALL_STATUSES`·`ACTIVE_STATUSES`·`COUNTED_STATUSES`·`STARTED_STATUSES: frozenset[str]`, `status_list_sql(codes) -> str`(`'reserved', 'in_progress'` 꼴), 상수 `RESERVED`·`IN_PROGRESS`·`COMPLETED`·`CANCELED`·`NO_SHOW`. `visit.domain.entities.visit`은 이 이름들을 다시 내보낸다(부르는 쪽 import 는 그대로). `visit_board.COUNTED = COUNTED_STATUSES`. `DayCountsView.of(counts: Mapping[str, int], unresolved: int) -> DayCountsView`(JSON 모양 그대로). ORM 의 CHECK·부분 색인 문자열은 마이그레이션 0006 과 글자까지 같다(스키마 드리프트 없음).

감사 결과(설계 4.1 B5): 새 상태를 더하면 다섯 곳을 고쳐야 했다. 이제 표 한 줄 + 상태 클래스 하나 + `DayCountsView` 칸 하나 + 새 마이그레이션이다(`test_schema_drift`가 알려 준다). 순환 import 를 피하려고 상태 이름·성질은 `domain/state/visit_status.py`(아무것도 import 하지 않는다)에, 행동은 `visit_state.py`(entities 를 import 한다)에 둔다. ORM 은 `adapter → domain` 방향으로 표를 읽는다(계층 계약 안). 두 테스트가 지킨다: 도메인 표 = 상태 클래스 집합, ORM 문자열 = 표에서 만든 문자열.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_visit_orm_status.py`:

```python
"""ORM 의 CHECK 와 부분 색인이 도메인 상태 표에서 나온 것인지 — 상태 이름을 손으로 적은 곳이 다시 생기면 걸린다."""
from sqlalchemy import CheckConstraint, Index

from visit.adapter.outbound.orm.visit_orm import VisitOrm
from visit.domain.state.visit_status import ACTIVE_STATUSES, ALL_STATUSES, STARTED_STATUSES, status_list_sql


def _constraint(name: str) -> str:
    for arg in VisitOrm.__table_args__:
        if isinstance(arg, CheckConstraint) and arg.name == name:
            return str(arg.sqltext)
    raise AssertionError(name)


def _index_where(name: str) -> str:
    for arg in VisitOrm.__table_args__:
        if isinstance(arg, Index) and arg.name == name:
            return str(arg.dialect_options["postgresql"]["where"])
    raise AssertionError(name)


def test_상태_CHECK_는_표의_모든_상태를_담는다():
    assert _constraint("ck_visits_status") == f"status IN ({status_list_sql(ALL_STATUSES)})"


def test_시작_시각_CHECK_는_시작_시각이_있는_상태만_담는다():
    assert _constraint("ck_visits_started_at") == (
        f"(status IN ({status_list_sql(STARTED_STATUSES)})) = (started_at IS NOT NULL)"
    )


def test_중복_예약_부분_색인은_살아_있는_상태만_담는다():
    active = f"status IN ({status_list_sql(ACTIVE_STATUSES)})"
    assert _index_where("uq_visits_pet_start_active") == f"pet_id IS NOT NULL AND {active}"
    assert _index_where("uq_visits_customer_start_active") == f"pet_id IS NULL AND {active}"
```

`backend/apps/visit/tests/domain/test_visit_status.py`:

```python
"""상태의 단일 원천 — 표와 상태 클래스가 같은 집합이고, 파생 집합이 성질을 따른다."""
from visit.domain.state.visit_state import _STATES
from visit.domain.state.visit_status import (
    ACTIVE_STATUSES,
    ALL_STATUSES,
    COUNTED_STATUSES,
    STARTED_STATUSES,
    STATUSES,
    status_list_sql,
)


def test_상태마다_상태_클래스가_하나씩_있다():
    assert set(_STATES) == ALL_STATUSES


def test_상태_이름은_서로_다르다():
    assert len({s.code for s in STATUSES}) == len(STATUSES)


def test_파생_집합은_성질을_따른다():
    assert ACTIVE_STATUSES == {"reserved", "in_progress"}
    assert COUNTED_STATUSES == {"reserved", "in_progress", "completed"}
    assert STARTED_STATUSES == {"in_progress", "completed"}


def test_SQL_목록은_표의_순서를_지킨다():
    assert status_list_sql(ALL_STATUSES) == "'reserved', 'in_progress', 'completed', 'canceled', 'no_show'"
    assert status_list_sql(ACTIVE_STATUSES) == "'reserved', 'in_progress'"
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_visit_status.py apps/visit/tests/adapter/test_visit_orm_status.py -q -p no:cacheprovider`
Expected: 두 파일 모두 수집 단계 `ModuleNotFoundError: No module named 'visit.domain.state.visit_status'`.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/state/visit_status.py`:

```python
"""방문 상태의 단일 원천 — 상태 이름과 그 성질(살아 있는가, 마릿수로 세는가, 시작 시각이 있는가).

상태를 더하면 여기에 한 줄을 더하고 `visit_state.py`에 상태 클래스를 하나 더한다. 그러면 나머지는 따라온다:
- `ACTIVE_STATUSES`·`COUNTED_STATUSES`·`STARTED_STATUSES`는 성질에서 파생한다.
- ORM 의 CHECK 와 부분 색인은 `status_list_sql()`로 문자열을 만든다(마이그레이션은 손으로 쓰므로
  `tests/test_schema_drift.py`가 새 마이그레이션이 필요함을 알려 준다).
- 하루 집계(`DayCountsView.of`)는 상태 이름을 열거하지 않는다.
- `tests/domain/test_visit_status.py`가 상태 클래스와 이 표가 같은 집합인지 확인한다.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VisitStatus:
    code: str
    is_active: bool          # 시간을 차지하고 '앞으로의 예약'으로 센다
    counts_as_visit: bool    # 하루·달력의 마릿수로 센다 — 취소·노쇼는 그날 한 일이 아니다
    has_started_at: bool     # 이 상태면 started_at 이 있어야 한다(CHECK)


RESERVED = "reserved"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
CANCELED = "canceled"
NO_SHOW = "no_show"

# 순서는 ORM CHECK 문자열의 순서다(마이그레이션 0006 과 같게 둔다).
STATUSES: tuple[VisitStatus, ...] = (
    VisitStatus(RESERVED, is_active=True, counts_as_visit=True, has_started_at=False),
    VisitStatus(IN_PROGRESS, is_active=True, counts_as_visit=True, has_started_at=True),
    VisitStatus(COMPLETED, is_active=False, counts_as_visit=True, has_started_at=True),
    VisitStatus(CANCELED, is_active=False, counts_as_visit=False, has_started_at=False),
    VisitStatus(NO_SHOW, is_active=False, counts_as_visit=False, has_started_at=False),
)
ALL_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES)
ACTIVE_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES if s.is_active)
COUNTED_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES if s.counts_as_visit)
STARTED_STATUSES: frozenset[str] = frozenset(s.code for s in STATUSES if s.has_started_at)


def status_list_sql(codes: frozenset[str]) -> str:
    """CHECK·부분 색인에 넣을 `'a', 'b'` 문자열. 표의 순서를 지킨다."""
    return ", ".join(f"'{s.code}'" for s in STATUSES if s.code in codes)
```

`backend/apps/visit/domain/entities/visit.py`:

```diff
@@ -3,14 +3,15 @@ from __future__ import annotations
 from dataclasses import dataclass
 from datetime import datetime, timedelta
 
-RESERVED = "reserved"
-IN_PROGRESS = "in_progress"
-COMPLETED = "completed"
-CANCELED = "canceled"
-NO_SHOW = "no_show"
-
-# 살아 있는 방문 — 시간을 차지하고, 앞으로의 예약으로 센다.
-ACTIVE_STATUSES = frozenset({RESERVED, IN_PROGRESS})
+# 상태 이름과 집합의 원천은 domain/state/visit_status.py 다. 여기서는 부르는 쪽의 편의로 다시 내보낸다.
+from visit.domain.state.visit_status import (  # noqa: F401 — 다시 내보냄
+    ACTIVE_STATUSES,
+    CANCELED,
+    COMPLETED,
+    IN_PROGRESS,
+    NO_SHOW,
+    RESERVED,
+)
 
 CANCEL_REASONS = frozenset({"customer_request", "shop_reason"})
```

`backend/apps/visit/domain/services/visit_board.py`:

```diff
@@ -4,11 +4,12 @@ from __future__ import annotations
 from collections import Counter
 from datetime import date
 
-from visit.domain.entities.visit import COMPLETED, IN_PROGRESS, RESERVED, Visit
+from visit.domain.entities.visit import RESERVED, Visit
 from visit.domain.services.visit_schedule import local_date
+from visit.domain.state.visit_status import COUNTED_STATUSES
 
-# 마릿수로 치는 상태 — 취소·노쇼는 그날 한 일이 아니다.
-COUNTED = frozenset({RESERVED, IN_PROGRESS, COMPLETED})
+# 마릿수로 치는 상태 — 취소·노쇼는 그날 한 일이 아니다. 어느 상태가 그런지는 visit_status 의 표가 정한다.
+COUNTED = COUNTED_STATUSES
 
 
 def is_unresolved(visit: Visit, today: date, tz: str) -> bool:
```

`backend/apps/visit/adapter/outbound/orm/visit_orm.py`:

```diff
@@ -18,8 +18,19 @@ from sqlalchemy import (
 from sqlalchemy.orm import Mapped, mapped_column
 
 from core.database import Base
+from visit.domain.state.visit_status import (
+    ACTIVE_STATUSES,
+    ALL_STATUSES,
+    STARTED_STATUSES,
+    status_list_sql,
+)
 
 _DURATION_RULE = "BETWEEN 10 AND 600 AND {col} % 10 = 0"
+# 상태 이름을 여기 적지 않는다 — 도메인 표(visit_status)에서 만든다. 상태가 늘면 새 마이그레이션이 필요하고,
+# tests/test_schema_drift.py 가 그것을 알려 준다.
+_STATUS_IN = "status IN (" + status_list_sql(ALL_STATUSES) + ")"
+_ACTIVE_IN = "status IN (" + status_list_sql(ACTIVE_STATUSES) + ")"
+_STARTED_IN = "status IN (" + status_list_sql(STARTED_STATUSES) + ")"
 
 
 class VisitShopSettingsOrm(Base):
@@ -99,10 +110,7 @@ class VisitOrm(Base):
 
     __tablename__ = "visits"
     __table_args__ = (
-        CheckConstraint(
-            "status IN ('reserved', 'in_progress', 'completed', 'canceled', 'no_show')",
-            name="ck_visits_status",
-        ),
+        CheckConstraint(_STATUS_IN, name="ck_visits_status"),
         CheckConstraint(
             "duration_minutes " + _DURATION_RULE.format(col="duration_minutes"),
             name="ck_visits_duration",
@@ -120,18 +128,15 @@ class VisitOrm(Base):
         CheckConstraint(
             "(status = 'completed') = (completed_at IS NOT NULL)", name="ck_visits_completed_at"
         ),
-        CheckConstraint(
-            "(status IN ('in_progress', 'completed')) = (started_at IS NOT NULL)",
-            name="ck_visits_started_at",
-        ),
+        CheckConstraint("(" + _STARTED_IN + ") = (started_at IS NOT NULL)", name="ck_visits_started_at"),
         # 중복 예약 방지 — 저장을 두 번 눌러도 살아 있는 예약은 하나다(설계 V5).
         Index(
             "uq_visits_pet_start_active", "pet_id", "starts_at", unique=True,
-            postgresql_where=text("pet_id IS NOT NULL AND status IN ('reserved', 'in_progress')"),
+            postgresql_where=text("pet_id IS NOT NULL AND " + _ACTIVE_IN),
         ),
         Index(
             "uq_visits_customer_start_active", "customer_id", "starts_at", unique=True,
-            postgresql_where=text("pet_id IS NULL AND status IN ('reserved', 'in_progress')"),
+            postgresql_where=text("pet_id IS NULL AND " + _ACTIVE_IN),
         ),
         Index("ix_visits_shop_starts_at", "shop_id", "starts_at"),
         Index("ix_visits_shop_customer", "shop_id", "customer_id"),
```

`backend/apps/visit/app/dtos/list_day_visits_dto.py`:

```diff
@@ -1,10 +1,12 @@
 from __future__ import annotations
 
-from dataclasses import dataclass
+from collections.abc import Mapping
+from dataclasses import dataclass, fields
 from datetime import date
 
 from hub.app.dtos.shop_context import ShopContext
 from visit.app.dtos.visit_view_dto import VisitView
+from visit.domain.state.visit_status import COUNTED_STATUSES
 
 
 @dataclass(frozen=True)
@@ -15,6 +17,8 @@ class ListDayVisitsQuery:
 
 @dataclass(frozen=True)
 class DayCountsView:
+    """상태별 수. 상태 이름과 같은 칸이 하나씩 있다 — 상태가 늘면 칸을 더하고, `of`가 그것을 채운다."""
+
     visit_count: int   # 마릿수 — 예약됨·미용 중·완료
     reserved: int
     in_progress: int
@@ -23,6 +27,16 @@ class DayCountsView:
     no_show: int
     unresolved: int
 
+    @classmethod
+    def of(cls, counts: Mapping[str, int], unresolved: int) -> DayCountsView:
+        """상태 이름 → 수 매핑에서 만든다. 어느 칸이 상태인지는 필드 이름으로 안다(visit_count·unresolved 는 아니다)."""
+        status_fields = [f.name for f in fields(cls) if f.name not in ("visit_count", "unresolved")]
+        return cls(
+            visit_count=sum(counts.get(s, 0) for s in COUNTED_STATUSES),
+            unresolved=unresolved,
+            **{name: counts.get(name, 0) for name in status_fields},
+        )
+
 
 @dataclass(frozen=True)
 class DayVisitItemView:
```

`backend/apps/visit/app/use_cases/list_day_visits_interactor.py`:

```diff
@@ -15,14 +15,8 @@ from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_board_repository import VisitBoardRepository
 from visit.app.services.visit_reader import describe_visits
-from visit.domain.entities.visit import CANCELED, COMPLETED, IN_PROGRESS, NO_SHOW, RESERVED
 from visit.domain.errors import VisitInputError
-from visit.domain.services.visit_board import (
-    COUNTED,
-    is_unresolved,
-    overlaps_other_group,
-    status_counts,
-)
+from visit.domain.services.visit_board import is_unresolved, overlaps_other_group, status_counts
 from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date
 
 
@@ -59,14 +53,9 @@ class ListDayVisitsInteractor(ListDayVisitsUseCase):
             )
             for visit, view in zip(visits, views)
         ]
-        counts = status_counts(visits)
         return DayVisitsView(
             date=day,
             closed_day=is_closed_day(day, settings, closed),
-            counts=DayCountsView(
-                visit_count=sum(counts[s] for s in COUNTED), reserved=counts[RESERVED],
-                in_progress=counts[IN_PROGRESS], completed=counts[COMPLETED], canceled=counts[CANCELED],
-                no_show=counts[NO_SHOW], unresolved=sum(item.unresolved for item in items),
-            ),
+            counts=DayCountsView.of(status_counts(visits), unresolved=sum(item.unresolved for item in items)),
             items=items,
         )
```

`backend/apps/visit/_docs/CLAUDE.md`:

```diff
@@ -4,7 +4,7 @@
 
 - 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
 - `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
-- 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK).
+- 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK). **상태 이름과 성질(살아 있음·마릿수·시작 시각)의 단일 원천은 `domain/state/visit_status.py`의 표다** — `ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·하루 집계 칸이 거기서 파생한다. 상태를 더하면 표에 한 줄, `visit_state.py`에 상태 클래스 하나, `DayCountsView`에 칸 하나, 그리고 새 마이그레이션이다(`test_schema_drift`가 알려 준다).
 - 행동(시작·완료·취소·노쇼·되돌리기)은 `visit_state.ACTIONS`와 바탕 상태 클래스의 같은 이름 메서드가 정한다. `transition()`은 행동 이름으로 메서드를 찾으므로 행동을 더할 때 if 체인을 늘리지 않는다. 시간을 다시 차지하는 행동(`SLOT_RECLAIMING_ACTIONS`)만 가족 확인에 반려동물을 넘긴다(`pets_to_confirm`). 완료가 생기거나 풀린 뒤의 후속 처리는 `app/services/completion_effects.py` 한 곳이다 — 전이·기록(④) 유스케이스가 같은 함수를 부른다.
 - **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
 - `visits` 표의 리포지토리는 포트 다섯으로 나뉜다(`app/ports/output/visit_*_repository.py`): 찾기·잠금(`VisitLookupRepository`), 쓰기(`VisitWriteRepository`, 찾기·잠금을 상속), 이력(`VisitHistoryRepository`), 원장(`VisitLedgerRepository`), 게시판(`VisitBoardRepository`). 구현은 `VisitPgRepository` 하나가 다 상속하고, 유스케이스는 자기가 부르는 포트만 생성자로 받는다(같은 인스턴스를 인자마다 넘긴다). 포트에 메서드를 더할 때는 그 축에 넣고, 새 축이면 포트를 새로 만든다.
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_visit_status.py apps/visit/tests/adapter/test_visit_orm_status.py apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py apps/visit/tests/adapter/test_visit_schema.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 753 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

Run (`infra/`): `docker compose run --rm backend pytest tests/test_schema_drift.py apps/visit/tests/adapter/test_visit_pg_repository.py tests/integration/test_visit_flow_wiring.py -q -p no:cacheprovider -m integration` → 20 passed(드리프트 없음 — CHECK 문자열이 0006 과 같다)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `visit_status.py`의 `CANCELED` 줄을 `counts_as_visit=True`로 → `test_파생_집합은_성질을_따른다`와 하루 목록 인터랙터의 마릿수 테스트 실패(2개).
- `visit_orm.py`의 `_ACTIVE_IN`을 `"status IN ('reserved')"`로 하드코딩 → `test_중복_예약_부분_색인은_살아_있는_상태만_담는다` 실패.
- `DayCountsView.of`의 `visit_count`를 `sum(counts.values())`로 → 하루 목록 인터랙터의 마릿수 테스트 실패(취소·노쇼를 센다).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(visit): 방문 상태의 단일 원천 — domain/state/visit_status 표에서 살아 있음·마릿수·시작 시각 집합과 ORM CHECK·부분 색인·하루 집계 칸을 파생한다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 6: 도메인 규칙을 도메인으로 — 소요 시간 기본값(`visit_duration`)과 카톡 초안 후보 등급(`draft_ranking`)을 인터랙터에서 뺀다 (B7)

**Files:**
- Create: `backend/apps/visit/domain/services/visit_duration.py`
- Create: `backend/apps/customer/domain/services/draft_ranking.py`
- Modify: `backend/apps/customer/app/use_cases/customer_directory_interactor.py`
- Create: `backend/apps/customer/tests/domain/test_draft_ranking.py`
- Modify: `backend/apps/visit/app/use_cases/register_visit_interactor.py`
- Create: `backend/apps/visit/tests/domain/test_visit_duration.py`

**Interfaces:**
- Consumes: `register_visit_interactor`의 소요 기본값 계산, `customer_directory_interactor.find_draft_candidates`의 등급 계산(rank 0~3), `Menu.default_duration_minutes`, `Customer.name`·`phone`, `Pet.id`·`name`.
- Produces: `visit.domain.services.visit_duration.default_duration(menus: Sequence[Menu], shop_default_minutes: int) -> int`; `customer.domain.services.draft_ranking.FamilyMatch(rank, matched_pet_ids)`(`.exact` = rank ≤ 1), 등급 상수 `PET_NAME=0`·`CUSTOMER_NAME=1`·`PHONE=2`·`PARTIAL=3`, `phone_digits(words) -> list[str]`, `match_family(customer, pets, words) -> FamilyMatch`. 인터랙터 결과(후보 순서·`exact`·`matched_pet_ids`)는 그대로다. `DRAFT_CANDIDATE_LIMIT`·`_MATCH_LIMIT`는 import 아래로 옮겨진다(값 그대로).

감사 결과(설계 4.1 B7): 두 규칙이 인터랙터 안에 있어 위젯·통합 테스트로만 검증됐다. 도메인 함수로 빼고 표 같은 단위 테스트를 붙인다. 기존 인터랙터 테스트는 손대지 않고 그대로 통과한다(동작 불변).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/domain/test_draft_ranking.py`:

```python
from customer.domain.services.draft_ranking import FamilyMatch, match_family, phone_digits
from customer.tests.helpers.fakes import FakeCustomers, FakePets, Journal


def _family(name="김민지", phone="01012345678", pet_names=("콩이",)):
    journal = Journal()
    customers = FakeCustomers(journal)
    customer = customers.seed(name=name, phone=phone)
    pets = FakePets(journal, customers)
    return customer, [pets.seed(customer.id, n) for n in pet_names]


def test_반려동물_이름이_맞으면_0등급이고_맞은_아이를_준다():
    customer, (kong, dubu) = _family(pet_names=("콩이", "두부"))
    assert match_family(customer, [kong, dubu], ("두부", "토요일")) == FamilyMatch(0, (dubu.id,))
    assert match_family(customer, [kong, dubu], ("두부",)).exact


def test_보호자_이름이_맞으면_1등급이다():
    customer, pets = _family()
    match = match_family(customer, pets, ("김민지",))
    assert (match.rank, match.matched_pet_ids, match.exact) == (1, (), True)


def test_전화는_8자리_이상_포함이거나_4자리_뒷자리다():
    customer, pets = _family(phone="01012345678")
    assert match_family(customer, pets, ("010-1234-5678",)).rank == 2
    assert match_family(customer, pets, ("12345678",)).rank == 2
    assert match_family(customer, pets, ("5678",)).rank == 2
    assert match_family(customer, pets, ("1234",)).rank == 3   # 앞자리 넷은 아니다
    assert match_family(customer, pets, ("567",)).rank == 3


def test_아무것도_맞지_않으면_3등급_부분_일치다():
    customer, pets = _family()
    match = match_family(customer, pets, ("콩",))
    assert (match.rank, match.exact) == (3, False)


def test_숫자_낱말만_전화로_본다():
    assert phone_digits(("010-1234-5678", "콩이", "3시", "5678")) == ["01012345678", "5678"]
```

`backend/apps/visit/tests/domain/test_visit_duration.py`:

```python
from visit.domain.services.visit_duration import default_duration
from visit.tests.helpers.fakes import FakeMenus


def _menus(*minutes):
    fake = FakeMenus()
    return [fake.seed(name=f"메뉴{i}", minutes=m) for i, m in enumerate(minutes)]


def test_메뉴의_기본_소요를_더한다():
    assert default_duration(_menus(60, 30), shop_default_minutes=120) == 90


def test_기본_소요가_없는_메뉴는_매장_기본으로_센다():
    assert default_duration(_menus(60, None), shop_default_minutes=120) == 180


def test_메뉴가_없으면_매장_기본_소요다():
    assert default_duration([], shop_default_minutes=90) == 90
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_visit_duration.py apps/customer/tests/domain/test_draft_ranking.py -q -p no:cacheprovider`
Expected: 두 파일 모두 수집 단계 `ModuleNotFoundError`(`visit.domain.services.visit_duration`, `customer.domain.services.draft_ranking`).

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/services/visit_duration.py`:

```python
"""예상 소요 시간의 기본값 — 고른 메뉴의 기본 소요를 더하고, 없으면 매장 기본 소요.

메뉴의 기본 소요가 비어 있으면(None) 그 메뉴는 매장 기본 소요로 센다. 메뉴를 하나도 고르지 않았으면 매장 기본
소요다. 등록·수정 화면의 "미리 채움"과 서버의 기본값이 같은 규칙을 써야 하므로 도메인에 둔다.
"""
from __future__ import annotations

from collections.abc import Sequence

from visit.domain.entities.menu import Menu


def default_duration(menus: Sequence[Menu], shop_default_minutes: int) -> int:
    return sum(m.default_duration_minutes or shop_default_minutes for m in menus) or shop_default_minutes
```

`backend/apps/customer/domain/services/draft_ranking.py`:

```python
"""카톡 예약 초안의 "누구" 후보 순위 — 낱말이 가족의 어디에 맞았는지로 등급을 매긴다.

등급 0 반려동물 이름 정확 일치 → 1 보호자 이름 정확 일치 → 2 전화(8자리 이상 포함 / 4자리 뒷자리) → 3 부분 일치
(검색이 걸어 준 가족이지만 위 셋에 해당하지 않음). 0·1 이 "정확"이다. 같은 등급 안의 순서(고객 ID)는 부르는 쪽이
정한다. 낱말은 여기서 저장하지도 기록하지도 않는다.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet

PET_NAME = 0
CUSTOMER_NAME = 1
PHONE = 2
PARTIAL = 3


@dataclass(frozen=True)
class FamilyMatch:
    rank: int
    matched_pet_ids: tuple[int, ...]

    @property
    def exact(self) -> bool:
        return self.rank <= CUSTOMER_NAME


def phone_digits(words: Sequence[str]) -> list[str]:
    """낱말 가운데 숫자만인 것(하이픈은 뗀다) — 전화 일치에 쓴다."""
    return [w.replace("-", "") for w in words if w.replace("-", "").isdigit()]


def match_family(customer: Customer, pets: Sequence[Pet], words: Sequence[str]) -> FamilyMatch:
    """가족 하나의 등급과, 이름이 맞은 반려동물 ID(등급 0 일 때만 비어 있지 않다)."""
    matched = tuple(p.id for p in pets if p.name in words)
    if matched:
        return FamilyMatch(PET_NAME, matched)
    if customer.name in words:
        return FamilyMatch(CUSTOMER_NAME, ())
    digits = phone_digits(words)
    if any((len(d) >= 8 and d in customer.phone) or (len(d) == 4 and customer.phone.endswith(d)) for d in digits):
        return FamilyMatch(PHONE, ())
    return FamilyMatch(PARTIAL, ())
```

`backend/apps/customer/app/use_cases/customer_directory_interactor.py`:

```diff
@@ -2,14 +2,12 @@ from __future__ import annotations
 
 from datetime import datetime
 
-DRAFT_CANDIDATE_LIMIT = 5
-_MATCH_LIMIT = 20   # 순위를 매기기 전에 읽는 가족 수 — 낱말 하나에 수십 가족이 걸려도 여기서 자른다
-
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
 from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.domain.errors import CustomerNotFoundError
+from customer.domain.services.draft_ranking import match_family
 from customer.domain.services.phone_number import mask_phone
 from customer.domain.services.search_terms import parse_query
 from hub.app.dtos.draft_candidate import DraftCandidate
@@ -18,6 +16,9 @@ from hub.app.dtos.shop_context import ShopContext
 from hub.app.errors import FamilyNotFoundError, FamilyPetNotFoundError, FamilyPetPassedAwayError
 from hub.app.ports.customer_directory_port import CustomerDirectoryPort
 
+DRAFT_CANDIDATE_LIMIT = 5
+_MATCH_LIMIT = 20   # 순위를 매기기 전에 읽는 가족 수 — 낱말 하나에 수십 가족이 걸려도 여기서 자른다
+
 
 class CustomerDirectoryInteractor(CustomerDirectoryPort):
     """허브의 CustomerDirectoryPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""
@@ -68,21 +69,11 @@ class CustomerDirectoryInteractor(CustomerDirectoryPort):
         for pet in await self._pets.list_for_customers(ctx, [c.id for c in customers]):
             if not pet.passed_away:
                 pets_of[pet.customer_id].append(pet)
-        digits = [w.replace("-", "") for w in words if w.replace("-", "").isdigit()]
-        ranked = []
-        for customer in customers:
-            matched = tuple(p.id for p in pets_of[customer.id] if p.name in words)
-            if matched:
-                rank = 0
-            elif customer.name in words:
-                rank = 1
-            elif any((len(d) >= 8 and d in customer.phone) or (len(d) == 4 and customer.phone.endswith(d))
-                     for d in digits):
-                rank = 2
-            else:
-                rank = 3
-            ranked.append((rank, customer.id, customer, matched))
-        ranked.sort(key=lambda r: (r[0], r[1]))
+        # 등급은 도메인(draft_ranking)이 매기고, 같은 등급 안에서는 고객 ID 오름차순이다.
+        ranked = sorted(
+            ((match_family(c, pets_of[c.id], words), c) for c in customers),
+            key=lambda pair: (pair[0].rank, pair[1].id),
+        )
         return [
             DraftCandidate(
                 customer=CustomerBrief(customer_id=c.id, name=c.name, phone_masked=mask_phone(c.phone)),
@@ -91,8 +82,8 @@ class CustomerDirectoryInteractor(CustomerDirectoryPort):
                              weight_kg=p.weight_kg, passed_away=False)
                     for p in pets_of[c.id]
                 ),
-                matched_pet_ids=matched,
-                exact=rank <= 1,
+                matched_pet_ids=match.matched_pet_ids,
+                exact=match.exact,
             )
-            for rank, _, c, matched in ranked[:DRAFT_CANDIDATE_LIMIT]
+            for match, c in ranked[:DRAFT_CANDIDATE_LIMIT]
         ]
```

`backend/apps/visit/app/use_cases/register_visit_interactor.py`:

```diff
@@ -14,6 +14,7 @@ from visit.app.services.visit_reader import describe_visits
 from visit.app.services.visit_warnings import warnings_after_save
 from visit.domain.entities.visit import IN_PROGRESS, RESERVED
 from visit.domain.errors import MenuNotAvailableError, VisitInputError
+from visit.domain.services.visit_duration import default_duration
 from visit.domain.services.visit_schedule import (
     check_duration,
     check_same_day,
@@ -45,9 +46,7 @@ class RegisterVisitInteractor(RegisterVisitUseCase):
             raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")
         duration = command.duration_minutes
         if duration is None:
-            duration = sum(m.default_duration_minutes or settings.default_duration_minutes for m in menus) or (
-                settings.default_duration_minutes
-            )
+            duration = default_duration(menus, settings.default_duration_minutes)
         check_duration(duration)
         if command.walk_in:
             starts_at, status, started_at = floor_to_step(now, tz), IN_PROGRESS, now
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/visit/tests/domain/test_visit_duration.py apps/customer/tests/domain/test_draft_ranking.py apps/visit/tests/app/use_cases/test_register_visit_interactor.py apps/customer/tests/app/use_cases/test_customer_directory_interactor.py -q -p no:cacheprovider` → 전부 통과

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 761 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `visit_duration.default_duration`에서 마지막 `or shop_default_minutes`를 뺀다 → `test_메뉴가_없으면_매장_기본_소요다` 실패.
- `draft_ranking.match_family`의 4자리 뒷자리 조건 `customer.phone.endswith(d)`를 `d in customer.phone`으로 → `test_전화는_8자리_이상_포함이거나_4자리_뒷자리다` 실패(앞자리 넷이 걸린다).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor: 도메인 규칙을 도메인으로 — 소요 시간 기본값(visit_duration)과 카톡 초안 후보 등급(draft_ranking)을 인터랙터에서 뺀다

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 7: 재인증 정책을 auth 스포크로 — 최근 로그인 창은 `domain/services/recent_login`, 가드는 `dependencies/recent_login_guard`, core 는 토큰 검증만 (B8)

**Files:**
- Create: `backend/apps/auth/domain/services/recent_login.py`
- Create: `backend/apps/auth/dependencies/recent_login_guard.py`
- Modify: `backend/core/security.py`
- Modify: `_docs/architecture.md`
- Modify: `backend/apps/auth/_docs/CLAUDE.md`
- Modify: `backend/apps/auth/adapter/inbound/api/v1/link_identity_router.py`
- Modify: `backend/apps/auth/adapter/inbound/api/v1/unlink_identity_router.py`
- Modify: `backend/apps/auth/adapter/inbound/api/v1/withdraw_router.py`
- Modify: `backend/apps/auth/tests/adapter/test_link_identity_router.py`
- Modify: `backend/apps/auth/tests/adapter/test_unlink_identity_router.py`
- Modify: `backend/apps/auth/tests/adapter/test_withdraw_router.py`
- Create: `backend/apps/auth/tests/dependencies/__init__.py`
- Create: `backend/apps/auth/tests/dependencies/test_recent_login_guard.py`
- Create: `backend/apps/auth/tests/domain/test_recent_login.py`
- Modify: `backend/tests/integration/test_route_wiring.py`
- Modify: `backend/tests/route_inspection.py`
- Modify: `backend/tests/test_security.py`

**Interfaces:**
- Consumes: `core/security.py`의 `_authenticate`·`require_recent_login`·`RecentLogin`·`RECENT_LOGIN_SECONDS`·`MAX_CLOCK_SKEW_SECONDS`, 이를 쓰는 auth 라우터 셋(연결·해제·탈퇴)과 라우터 테스트 셋, `tests/route_inspection.py`, `tests/integration/test_route_wiring.py`, `tests/test_security.py`.
- Produces: `core.security.get_access_claims(db, credentials) -> AccessClaims`(서명 검증 + 계정 상태 — 옛 `_authenticate`가 공개 의존성이 됐다); `get_current_user_id(db, credentials) -> int` 서명 그대로; `auth.domain.services.recent_login.RECENT_LOGIN_SECONDS = 300`, `MAX_CLOCK_SKEW_SECONDS = 60`, `is_recent_login(auth_time: int | None, now_epoch: int) -> bool`; `auth.dependencies.recent_login_guard.RecentLogin(user_id, auth_time)`, `require_recent_login(claims: AccessClaims = Depends(get_access_claims)) -> RecentLogin`(403 `REAUTH_REQUIRED`), 모듈 함수 `_utcnow`(테스트가 monkeypatch 한다). core 에는 `RecentLogin`·`require_recent_login`이 더는 없다. 라우트 표는 전후로 같다.

감사 결과(설계 4.1 B8): `core/security.py`가 서명 검증·계정 상태·재인증 정책 셋을 맡았다. 설계의 두 갈래 가운데 연결·해제·탈퇴 라우터가 모두 인증 프로세스에 있으므로 자리 없이 auth 로 옮긴다(결정 기록 007). 판정 규칙(300초·시계 차 60초·`auth_time` 없음)은 도메인 단위 테스트 4개가, 가드는 실제 토큰·users 표로 통합 테스트 6개가 본다. `tests/test_security.py`에서 재인증 테스트 8개를 지운다(옮긴 것). `get_current_user_id`의 서명(`db`, `credentials`)은 그대로 두어 다른 스포크의 라우터 테스트가 바뀌지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/auth/tests/adapter/test_link_identity_router.py`:

```diff
@@ -5,6 +5,7 @@ from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
 from auth.adapter.inbound.api.v1.link_identity_router import link_identity_router
 from auth.app.dtos.link_identity_dto import LinkedIdentities
 from auth.dependencies.link_identity_provider import get_link_identity_use_case
+from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
 from auth.domain.errors import (
     IdentityAlreadyLinkedError,
     ProviderAlreadyLinkedError,
@@ -12,7 +13,6 @@ from auth.domain.errors import (
 )
 from core.database import get_db
 from core.http_errors import install_error_handlers
-from core.security import RecentLogin, require_recent_login
 
 
 class _StubUseCase:
```

`backend/apps/auth/tests/adapter/test_unlink_identity_router.py`:

```diff
@@ -6,13 +6,13 @@ from auth.adapter.inbound.api.v1.unlink_identity_router import unlink_identity_r
 from auth.app.dtos.token_dto import TokenPair
 from auth.app.dtos.unlink_identity_dto import UnlinkIdentityResult
 from auth.dependencies.provider_revoker_provider import get_provider_revoker
+from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
 from auth.dependencies.unlink_identity_provider import get_unlink_identity_use_case
 from auth.domain.errors import IdentityNotFoundError, LastIdentityError, UnsupportedProviderError
 from auth.domain.value_objects.identity_revocation import IdentityRevocation
 from auth.domain.value_objects.provider import Provider
 from core.database import get_db
 from core.http_errors import install_error_handlers
-from core.security import RecentLogin, require_recent_login
 
 APPLE = IdentityRevocation(Provider.APPLE, "apple-1", "apple-refresh")
```

`backend/apps/auth/tests/adapter/test_withdraw_router.py`:

```diff
@@ -5,13 +5,13 @@ from auth.adapter.inbound.api.error_map import AUTH_ERROR_STATUS
 from auth.adapter.inbound.api.v1.withdraw_router import withdraw_router
 from auth.app.dtos.withdraw_dto import WithdrawResult
 from auth.dependencies.provider_revoker_provider import get_provider_revoker
+from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
 from auth.dependencies.withdraw_provider import get_withdraw_use_case
 from auth.domain.errors import UserNotFoundError
 from auth.domain.value_objects.identity_revocation import IdentityRevocation
 from auth.domain.value_objects.provider import Provider
 from core.database import get_db
 from core.http_errors import install_error_handlers
-from core.security import RecentLogin, require_recent_login
 
 KAKAO = IdentityRevocation(Provider.KAKAO, "kakao-100", None)
```

`backend/apps/auth/tests/dependencies/__init__.py`:

```python

```

`backend/apps/auth/tests/dependencies/test_recent_login_guard.py`:

```python
"""재인증 가드 — 실제 토큰과 users 표로 확인한다. 판정 규칙 자체는 domain/test_recent_login.py 가 본다."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import text

import auth.dependencies.recent_login_guard as guard
import core.security as security
from auth.adapter.outbound.gateways.jwt_token_issuer import JwtTokenIssuer
from auth.domain.services.recent_login import RECENT_LOGIN_SECONDS
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


async def _require(db, token):
    return await guard.require_recent_login(await security.get_access_claims(db=db, credentials=_bearer(token)))


@pytest.fixture
def issuer(monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    return JwtTokenIssuer(private_pem, ttl_seconds=900)


async def test_방금_로그인한_토큰은_최근_로그인으로_통과한다(db_session, issuer):
    await _insert_user(db_session, id=11)
    recent = await _require(db_session, issuer.issue_access(11, fresh_login=True).token)
    assert recent.user_id == 11
    assert recent.auth_time > 0


async def test_갱신으로_받은_토큰은_REAUTH_REQUIRED_다(db_session, issuer):
    await _insert_user(db_session, id=12)
    with pytest.raises(ApiError) as exc:
        await _require(db_session, issuer.issue_access(12).token)   # auth_time 없음 = 갱신이 발급한 토큰
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_로그인한_지_오래된_토큰은_403_이다(db_session, monkeypatch):
    private_pem, public_pem, _ = make_rsa_keypair()
    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
    await _insert_user(db_session, id=13)
    long_ago = lambda: datetime.now(timezone.utc) - timedelta(seconds=RECENT_LOGIN_SECONDS + 1)
    # 만료는 아직 멀었지만(ttl 900초) 로그인한 지 301초가 지났다.
    token = JwtTokenIssuer(private_pem, ttl_seconds=900, now=long_ago).issue_access(13, fresh_login=True).token
    with pytest.raises(ApiError) as exc:
        await _require(db_session, token)
    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")


async def test_정지된_계정은_최근_로그인이어도_403_ACCOUNT_SUSPENDED_다(db_session, issuer):
    await _insert_user(db_session, id=15, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await _require(db_session, issuer.issue_access(15, fresh_login=True).token)
    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")


async def test_탈퇴한_계정은_최근_로그인이어도_401_이다(db_session, issuer):
    await _insert_user(db_session, id=16, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
    with pytest.raises(ApiError) as exc:
        await _require(db_session, issuer.issue_access(16, fresh_login=True).token)
    assert exc.value.status_code == 401


async def test_가드는_지금_시각으로_판정한다(db_session, issuer, monkeypatch):
    """경계값 자체는 도메인 테스트가 본다. 여기서는 가드가 _utcnow 를 쓰는지만 못 박는다."""
    await _insert_user(db_session, id=17)
    logged_in = datetime.now(timezone.utc).replace(microsecond=0)
    token = issuer.issue_access(17, auth_time=int(logged_in.timestamp())).token
    monkeypatch.setattr(guard, "_utcnow", lambda: logged_in + timedelta(seconds=RECENT_LOGIN_SECONDS))
    assert (await _require(db_session, token)).auth_time == int(logged_in.timestamp())
    monkeypatch.setattr(guard, "_utcnow", lambda: logged_in + timedelta(seconds=RECENT_LOGIN_SECONDS + 1))
    with pytest.raises(ApiError):
        await _require(db_session, token)
```

`backend/apps/auth/tests/domain/test_recent_login.py`:

```python
from auth.domain.services.recent_login import MAX_CLOCK_SKEW_SECONDS, RECENT_LOGIN_SECONDS, is_recent_login

NOW = 1_700_000_000


def test_로그인_시각이_없으면_최근이_아니다():
    assert not is_recent_login(None, NOW)


def test_정확히_300초면_통과하고_301초면_아니다():
    assert is_recent_login(NOW - RECENT_LOGIN_SECONDS, NOW)
    assert not is_recent_login(NOW - RECENT_LOGIN_SECONDS - 1, NOW)


def test_미래의_로그인_시각은_시계_차_허용폭까지만_믿는다():
    assert is_recent_login(NOW + MAX_CLOCK_SKEW_SECONDS, NOW)
    assert not is_recent_login(NOW + MAX_CLOCK_SKEW_SECONDS + 1, NOW)


def test_방금_로그인은_통과한다():
    assert is_recent_login(NOW, NOW)
```

`backend/tests/integration/test_route_wiring.py`:

```diff
@@ -4,7 +4,7 @@ auth_main 은 import 시점에 JWT 개인키를 요구하므로 키를 넣어 
 """
 import pytest
 
-from core.security import require_recent_login
+from auth.dependencies.recent_login_guard import require_recent_login
 from tests.route_inspection import find_route_violations, routes_calling
 
 pytestmark = pytest.mark.integration
```

`backend/tests/route_inspection.py`:

```diff
@@ -12,7 +12,7 @@ from fastapi import FastAPI
 from fastapi.dependencies.models import Dependant
 from fastapi.routing import APIRoute, iter_route_contexts
 
-from core.security import require_recent_login
+from auth.dependencies.recent_login_guard import require_recent_login
 from core.shop_guard import get_shop_access_port, get_shop_context
 from platform_admin.dependencies.operator_guard import require_operator
```

`backend/tests/test_security.py`:

```diff
@@ -1,4 +1,4 @@
-from datetime import datetime, timedelta, timezone
+from datetime import datetime, timezone
 
 import pytest
 from fastapi.security import HTTPAuthorizationCredentials
@@ -65,89 +65,3 @@ def test_만료_시각이_없는_토큰은_받지_않는다():
     token = jwt.encode({"sub": "1", "typ": "access"}, private_pem, algorithm="RS256")
     with pytest.raises(security.InvalidAccessToken):
         security.decode_access_token(token, public_pem)
-
-
-async def test_방금_로그인한_토큰은_최근_로그인으로_통과한다(db_session, issuer):
-    await _insert_user(db_session, id=11)
-    token = issuer.issue_access(11, fresh_login=True).token
-    recent = await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert recent.user_id == 11
-    assert recent.auth_time > 0
-
-
-async def test_갱신으로_받은_토큰은_REAUTH_REQUIRED_다(db_session, issuer):
-    await _insert_user(db_session, id=12)
-    token = issuer.issue_access(12).token   # auth_time 없음 = 갱신이 발급한 토큰
-    with pytest.raises(ApiError) as exc:
-        await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")
-
-
-async def test_로그인한_지_오래된_토큰은_403_이다(db_session, monkeypatch):
-    private_pem, public_pem, _ = make_rsa_keypair()
-    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
-    await _insert_user(db_session, id=13)
-    long_ago = lambda: datetime.now(timezone.utc) - timedelta(seconds=security.RECENT_LOGIN_SECONDS + 1)
-    # 만료는 아직 멀었지만(ttl 900초) 로그인한 지 301초가 지났다.
-    token = JwtTokenIssuer(private_pem, ttl_seconds=900, now=long_ago).issue_access(13, fresh_login=True).token
-    with pytest.raises(ApiError) as exc:
-        await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")
-
-
-async def test_경계_안쪽의_토큰은_통과한다(db_session, monkeypatch):
-    private_pem, public_pem, _ = make_rsa_keypair()
-    monkeypatch.setattr(security, "JWT_PUBLIC_KEY", public_pem)
-    await _insert_user(db_session, id=14)
-    almost = lambda: datetime.now(timezone.utc) - timedelta(seconds=security.RECENT_LOGIN_SECONDS - 5)
-    token = JwtTokenIssuer(private_pem, ttl_seconds=900, now=almost).issue_access(14, fresh_login=True).token
-    assert (await security.require_recent_login(db=db_session, credentials=_bearer(token))).user_id == 14
-
-
-async def test_정지된_계정은_최근_로그인이어도_403_ACCOUNT_SUSPENDED_다(db_session, issuer):
-    await _insert_user(db_session, id=15, suspended_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
-    token = issuer.issue_access(15, fresh_login=True).token
-    with pytest.raises(ApiError) as exc:
-        await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert (exc.value.status_code, exc.value.code) == (403, "ACCOUNT_SUSPENDED")
-
-
-async def test_탈퇴한_계정은_최근_로그인이어도_401_이다(db_session, issuer):
-    await _insert_user(db_session, id=16, deleted_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
-    token = issuer.issue_access(16, fresh_login=True).token
-    with pytest.raises(ApiError) as exc:
-        await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert exc.value.status_code == 401
-
-
-def _freeze_now(monkeypatch, at):
-    monkeypatch.setattr(security, "_utcnow", lambda: at)
-
-
-async def test_로그인한_지_정확히_300초면_통과하고_301초면_403_이다(db_session, issuer, monkeypatch):
-    await _insert_user(db_session, id=17)
-    logged_in = datetime.now(timezone.utc).replace(microsecond=0)
-    auth_time = int(logged_in.timestamp())
-    token = issuer.issue_access(17, auth_time=auth_time).token
-
-    _freeze_now(monkeypatch, logged_in + timedelta(seconds=security.RECENT_LOGIN_SECONDS))
-    recent = await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert recent.auth_time == auth_time
-
-    _freeze_now(monkeypatch, logged_in + timedelta(seconds=security.RECENT_LOGIN_SECONDS + 1))
-    with pytest.raises(ApiError) as exc:
-        await security.require_recent_login(db=db_session, credentials=_bearer(token))
-    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")
-
-
-async def test_로그인_시각이_60초_넘게_미래면_403_이다(db_session, issuer, monkeypatch):
-    await _insert_user(db_session, id=18)
-    now = datetime.now(timezone.utc).replace(microsecond=0)
-    _freeze_now(monkeypatch, now)
-    at_limit = issuer.issue_access(18, auth_time=int(now.timestamp()) + 60).token
-    assert (await security.require_recent_login(db=db_session, credentials=_bearer(at_limit))).user_id == 18
-
-    too_far = issuer.issue_access(18, auth_time=int(now.timestamp()) + 61).token
-    with pytest.raises(ApiError) as exc:
-        await security.require_recent_login(db=db_session, credentials=_bearer(too_far))
-    assert (exc.value.status_code, exc.value.code) == (403, "REAUTH_REQUIRED")
```

- [ ] **Step 2: 테스트가 실패하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/auth/tests/domain/test_recent_login.py -q -p no:cacheprovider`
Expected: 수집 단계 `ModuleNotFoundError: No module named 'auth.domain.services.recent_login'`.

Run (`infra/`): `docker compose run --rm backend pytest apps/auth/tests/dependencies/test_recent_login_guard.py -q -p no:cacheprovider -m integration`
Expected: 수집 단계 `ModuleNotFoundError: No module named 'auth.dependencies.recent_login_guard'`.

- [ ] **Step 3: 구현한다**

`backend/apps/auth/domain/services/recent_login.py`:

```python
"""최근 로그인 판정 — 계정을 빼앗는 데 쓰일 수 있는 경로(수단 연결·해제, 탈퇴) 앞의 재인증 규칙.

소셜 로그인으로 받은 토큰에만 로그인 시각(auth_time)이 있다. 갱신으로 받은 토큰에는 없어 통과하지 못한다.
결정 기록 003·004: "최근 로그인 확인"(Firebase 방식), 창은 5분이다.
"""
from __future__ import annotations

RECENT_LOGIN_SECONDS = 300
# 발급 프로세스와 검증 프로세스의 시계 차로 봐줄 수 있는 폭. 이보다 먼 미래의 로그인 시각은 믿지 않는다.
MAX_CLOCK_SKEW_SECONDS = 60


def is_recent_login(auth_time: int | None, now_epoch: int) -> bool:
    """로그인 시각이 있고, 지금으로부터 RECENT_LOGIN_SECONDS 안이며, 시계 차 허용폭보다 미래가 아니면 참."""
    if auth_time is None:
        return False
    elapsed = now_epoch - auth_time
    return -MAX_CLOCK_SKEW_SECONDS <= elapsed <= RECENT_LOGIN_SECONDS
```

`backend/apps/auth/dependencies/recent_login_guard.py`:

```python
"""재인증 가드 — 로그인 수단 연결·해제와 회원 탈퇴 앞에서 최근 로그인만 받는다.

토큰 검증은 core(`get_access_claims`)가, 최근인지의 판정은 auth 도메인(`recent_login.is_recent_login`)이 한다.
훔친 액세스 토큰 하나로 계정을 빼앗는 것을 막는다 — 갱신으로 받은 토큰은 통과하지 못한다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends

from auth.domain.services.recent_login import is_recent_login
from core.http_errors import ApiError
from core.security import AccessClaims, get_access_claims


@dataclass(frozen=True)
class RecentLogin:
    user_id: int
    auth_time: int


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def require_recent_login(claims: AccessClaims = Depends(get_access_claims)) -> RecentLogin:
    if not is_recent_login(claims.auth_time, int(_utcnow().timestamp())):
        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
    return RecentLogin(user_id=claims.user_id, auth_time=claims.auth_time)
```

`backend/core/security.py`:

```diff
@@ -3,11 +3,12 @@
 발급은 auth 스포크 몫이고 여기는 서명 검증과 계정 상태 확인만 한다.
 스포크가 auth 를 import 하면 허브-스포크 위반이라 순수 인프라(core)에 둔다.
 users 를 원시 SQL 로 조회하는 이유는 core 가 스포크의 ORM 을 import 할 수 없어서다.
+"최근 로그인" 같은 정책은 여기 없다 — auth 스포크(`auth/domain/services/recent_login.py`)의 몫이고,
+그 가드(`auth/dependencies/recent_login_guard.py`)는 여기의 `get_access_claims` 위에 선다.
 """
 from __future__ import annotations
 
 from dataclasses import dataclass
-from datetime import datetime, timezone
 
 from fastapi import Depends
 from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
@@ -25,27 +26,12 @@ class InvalidAccessToken(Exception):
     pass
 
 
-RECENT_LOGIN_SECONDS = 300
-# 발급 프로세스와 검증 프로세스의 시계 차로 봐줄 수 있는 폭. 이보다 먼 미래의 로그인 시각은 믿지 않는다.
-MAX_CLOCK_SKEW_SECONDS = 60
-
-
 @dataclass(frozen=True)
 class AccessClaims:
     user_id: int
     auth_time: int | None  # 소셜 로그인으로 받은 토큰에만 있다 (갱신으로 받은 토큰에는 없다)
 
 
-@dataclass(frozen=True)
-class RecentLogin:
-    user_id: int
-    auth_time: int
-
-
-def _utcnow() -> datetime:
-    return datetime.now(timezone.utc)
-
-
 def decode_access_claims(token: str, public_key: str) -> AccessClaims:
     try:
         # 허용 알고리즘은 RS256 리터럴로 고정한다 (알고리즘 혼동 공격 방지).
@@ -67,7 +53,10 @@ def decode_access_token(token: str, public_key: str) -> int:
     return decode_access_claims(token, public_key).user_id
 
 
-async def _authenticate(db, credentials: HTTPAuthorizationCredentials | None) -> AccessClaims:
+async def get_access_claims(
+    db: DbSession,
+    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
+) -> AccessClaims:
     """서명 검증 + 계정 상태 확인. 정지·탈퇴는 이미 발급된 토큰도 즉시 막는다."""
     if credentials is None:
         raise ApiError(401, "UNAUTHENTICATED", "로그인이 필요합니다.")
@@ -92,19 +81,4 @@ async def get_current_user_id(
     db: DbSession,
     credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
 ) -> int:
-    return (await _authenticate(db, credentials)).user_id
-
-
-async def require_recent_login(
-    db: DbSession,
-    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
-) -> RecentLogin:
-    """로그인 수단 연결·해제와 회원 탈퇴 앞의 재인증. 소셜 로그인한 지 RECENT_LOGIN_SECONDS 안의
-    토큰만 받는다. 훔친 액세스 토큰 하나로 계정을 빼앗는 것을 막는다 — 갱신으로 받은 토큰은 통과하지 못한다."""
-    claims = await _authenticate(db, credentials)
-    if claims.auth_time is None:
-        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
-    elapsed = int(_utcnow().timestamp()) - claims.auth_time
-    if elapsed > RECENT_LOGIN_SECONDS or elapsed < -MAX_CLOCK_SKEW_SECONDS:
-        raise ApiError(403, "REAUTH_REQUIRED", "보안을 위해 다시 로그인해 주세요.")
-    return RecentLogin(user_id=claims.user_id, auth_time=claims.auth_time)
+    return (await get_access_claims(db, credentials)).user_id
```

`_docs/architecture.md`:

```diff
@@ -30,7 +30,7 @@
 - 허브는 `apps/hub`다. 포트(ABC)와 DTO만 가진다.
 - 스포크는 허브의 추상에만 의존한다. 스포크끼리 import하지 않고, 허브는 스포크를 import하지 않는다.
 - 스포크를 넘는 외래 키는 걸지 않는다. 다른 스포크의 ID는 인덱스만 있는 정수 컬럼이다.
-- `core/`는 인프라 공유(DB 세션, 설정, 토큰 검증)만 맡는다. `core/security.py`가 `users` 테이블을 원시 SQL로 조회하는 것은 의도한 예외다. core가 스포크의 ORM을 import할 수 없기 때문이다.
+- `core/`는 인프라 공유(DB 세션, 설정, 토큰 검증)만 맡는다. `core/security.py`가 `users` 테이블을 원시 SQL로 조회하는 것은 의도한 예외다. core가 스포크의 ORM을 import할 수 없기 때문이다. 정책(예: 재인증의 최근 로그인 창)은 core에 두지 않고 그 스포크의 도메인에 둔다 — `auth/domain/services/recent_login.py`.
 - `core/`는 허브의 추상(포트 ABC와 DTO)을 import할 수 있다. 스포크는 import할 수 없다.
 - 허브 포트를 구현하는 슬라이스는 그 포트를 입력 포트로 삼는다. 인터랙터가 허브 포트 ABC를 직접 상속하고, HTTP 표면이 없으므로 schema와 router를 생략한다.
 - 허브 포트가 던지는 오류는 `hub/app/errors.py`의 `HubPortError` 하위 타입뿐이다. 구현 스포크는 자기 도메인 오류를 잡아 허브 오류로 바꿔 던지고, 소비 스포크와 테스트 스텁은 그 타입만 안다. HTTP 상태는 `core/hub_errors.py`에 적고 `install_error_handlers`가 두 진입점에 자동으로 등록한다(`tests/test_hub_errors.py`가 빠진 것을 잡는다).
```

`backend/apps/auth/_docs/CLAUDE.md`:

```diff
@@ -16,5 +16,5 @@
 - **현재 세대로 토큰을 발급하는 경로(`SessionIssuer.issue(..., generation=None)`)는 유저 행을 잠그고 다시 확인한다.** `social_login`·`unlink_identity`가 여기 해당한다. `social_login`은 기존 유저를 찾으면 그 행을 잠근 뒤 신원을 다시 조회한다 — 잠금이 없으면 해제·탈퇴와 겹친 로그인이 사라진 수단으로 30일 세션을 쥔다. 어긋나면 조회를 처음부터 한 번만 다시 하고(해제된 수단은 새 계정이 된다), 두 번째에도 어긋나면 거절한다. 로그인이 잠그는 것은 유저 행 하나뿐이고 그 뒤로는 아무것도 잠그지 않는다. `grant_operator`도 같은 이유로 `lock`으로 읽는다. `refresh_token`은 이 규칙 밖이다 — 유저를 `get`으로 읽지만, 꺼낼 때(`take`) 받은 세대로 새 토큰을 저장하므로 그 사이 끼어든 전체 폐기가 새 토큰도 함께 무효로 만든다.
 - 잠금을 쥔 채 외부 HTTP를 부르지 않는다. 제공자 검증은 잠금 전에, 제공자 쪽 연결 끊기는 커밋 뒤 백그라운드 작업(`ProviderRevoker`)으로 한다. 끊지 못해도 탈퇴·해제는 끝난 것이며 로그만 남긴다. 구글은 서버가 끊지 않는다(앱이 `disconnect()`를 부른다).
 - 로그인 수단을 해제하면 모든 세션을 폐기하고 요청한 기기에만 새 토큰을 준다.
-- 민감한 계정 경로를 더할 때는 `require_recent_login` 을 쓰고 `tests/route_inspection.py` 의 `_RECENT_LOGIN_PREFIXES` 에 경로를 적는다. `auth_time` 은 소셜 로그인만 새로 찍고(`fresh_login=True`), 갱신은 찍지 않으며, 해제는 요청 토큰의 값을 물려준다.
+- 민감한 계정 경로를 더할 때는 `dependencies/recent_login_guard.require_recent_login` 을 쓰고 `tests/route_inspection.py` 의 `_RECENT_LOGIN_PREFIXES` 에 경로를 적는다. 최근 로그인의 창(300초)과 시계 차 허용폭은 `domain/services/recent_login.py`가 정한다 — core 는 토큰 검증(`get_access_claims`)만 한다. `auth_time` 은 소셜 로그인만 새로 찍고(`fresh_login=True`), 갱신은 찍지 않으며, 해제는 요청 토큰의 값을 물려준다.
 - 탈퇴의 DB 변경은 요청 하나의 트랜잭션이다. 소속 정리는 허브의 `MembershipLifecyclePort`(구현: tenancy)가 같은 세션에서 한다. 이 자리는 `auth_main.py`가 채운다.
```

`backend/apps/auth/adapter/inbound/api/v1/link_identity_router.py`:

```diff
@@ -7,7 +7,7 @@ from auth.adapter.inbound.api.schemas.link_identity_schema import (
 from auth.app.dtos.link_identity_dto import LinkIdentityCommand
 from auth.app.ports.input.link_identity_use_case import LinkIdentityUseCase
 from auth.dependencies.link_identity_provider import get_link_identity_use_case
-from core.security import RecentLogin, require_recent_login
+from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
 
 link_identity_router = APIRouter(prefix="/v1/auth", tags=["auth"])
```

`backend/apps/auth/adapter/inbound/api/v1/unlink_identity_router.py`:

```diff
@@ -5,8 +5,8 @@ from auth.app.dtos.unlink_identity_dto import UnlinkIdentityCommand
 from auth.app.ports.input.unlink_identity_use_case import UnlinkIdentityUseCase
 from auth.app.services.provider_revoker import ProviderRevoker
 from auth.dependencies.provider_revoker_provider import get_provider_revoker
+from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
 from auth.dependencies.unlink_identity_provider import get_unlink_identity_use_case
-from core.security import RecentLogin, require_recent_login
 
 unlink_identity_router = APIRouter(prefix="/v1/auth", tags=["auth"])
```

`backend/apps/auth/adapter/inbound/api/v1/withdraw_router.py`:

```diff
@@ -5,8 +5,8 @@ from auth.app.dtos.withdraw_dto import WithdrawCommand
 from auth.app.ports.input.withdraw_use_case import WithdrawUseCase
 from auth.app.services.provider_revoker import ProviderRevoker
 from auth.dependencies.provider_revoker_provider import get_provider_revoker
+from auth.dependencies.recent_login_guard import RecentLogin, require_recent_login
 from auth.dependencies.withdraw_provider import get_withdraw_use_case
-from core.security import RecentLogin, require_recent_login
 
 withdraw_router = APIRouter(prefix="/v1/auth", tags=["auth"])
```

- [ ] **Step 4: 테스트가 통과하는지 확인한다**

Run (`infra/`): `docker compose run --rm --no-deps backend pytest apps/auth/tests/domain/test_recent_login.py -q -p no:cacheprovider` → 4 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 765 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 260 passed(262 − 옮긴 8 + 가드 6; `test_route_wiring`·`test_reauth_wiring` 포함)

Run (`infra/`): `docker compose run --rm --no-deps auth python scripts/print_routes.py` → 작업 1 전과 줄 단위로 같다(55줄)

- [ ] **Step 5: 판별력을 확인한다(변이)**

각 변이를 하나씩 넣고 그 테스트가 실패하는지 본 뒤 되돌린다.

- `recent_login.is_recent_login`의 `elapsed <= RECENT_LOGIN_SECONDS`를 `<`로 → `test_정확히_300초면_통과하고_301초면_아니다` 실패.
- `recent_login_guard.require_recent_login`의 `if not is_recent_login(...)`를 `if False:`로 → 가드 통합 테스트 3개 실패(`갱신으로_받은_토큰`·`오래된_토큰`·`지금_시각으로_판정`).

- [ ] **Step 6: 커밋한다**

```bash
git add -A
git commit -m "refactor(auth): 재인증 정책을 auth 스포크로 — 최근 로그인 창은 domain/services/recent_login, 가드는 dependencies/recent_login_guard, core 는 토큰 검증(get_access_claims)만

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

### Task 8: 결정 기록 007 — ④-0 SOLID 정리(백엔드)에서 설계와 다르게 간 것과 남는 것

**Files:**
- Create: `_docs/decisions/007-record-media.md`

**Interfaces:**
- Consumes: 작업 1~7 의 결과와 검증 수치(단위 765·통합 260·계약 6·라우트 표 동일).
- Produces: 결정 기록 007 의 첫 절. ④-1·④-2·④-3 계획이 같은 파일에 절을 더한다.

문서 작업이라 테스트가 없다. 수치가 실제 실행 결과와 다르면 문서가 아니라 코드를 의심한다(작업 1~7 의 diff 가 그대로 적용됐는지).

- [ ] **Step 1: 결정 기록을 쓴다**

`_docs/decisions/007-record-media.md`:

```markdown
# 007 — 미용 기록·미디어(④)에서 내린 결정

설계: `docs/superpowers/specs/2026-09-24-record-media-design.md`. 이 기록은 계획마다 절을 더한다.

## ④-0 SOLID 정리(백엔드)에서 정한 것

2026-09-24 감사(설계 4.1절 B1~B10)를 기능 코드 없이 먼저 적용했다. 검증 기준은 "기존 단위·통합·구조 계약이 전후로 통과하고 라우트 표가 같다"였고, 그대로 지켰다(단위 727 → 765, 통합 262 → 260 — 재인증 테스트 8개가 auth 로 옮겨 6개가 되고 도메인 단위 4개가 생겼다, 계약 6종, 라우트 표 동일).

### 설계와 다르게 간 것

- **찾기·잠금 포트 이름과 범위.** 설계 B1 은 `get_many`·`lock` 둘만 가진 `VisitLockRepository`를 말했다. 실제로는 `get`도 같은 축(ID 로 찾기)이고 상세·초안 조회가 `get`만 쓰므로, 셋을 가진 `VisitLookupRepository`로 두고 `VisitWriteRepository`가 이를 상속한다. 조회 유스케이스가 쓰기 포트를 받지 않게 하는 것이 목적이었고 그 목적은 지켰다(`apps/visit/tests/app/test_visit_port_segregation.py`가 쓰기 포트를 받는 유스케이스를 넷으로 고정한다).
- **허브 오류는 포트 셋.** 설계 B2 는 `CustomerDirectoryPort`와 "기존 포트 둘"을 말했지만, 감사에서 같은 누수가 `ShopAccessPort`(tenancy 오류가 core 로)와 `MembershipLifecyclePort`(tenancy 오류가 auth 로)에도 있었다. 셋 다 허브 오류로 바꿨다. 탈퇴 오류 둘(`OWNERSHIP_TRANSFER_REQUIRED`·`SHOP_CLOSE_CONFIRM_REQUIRED`)은 tenancy 도메인에서 지우고 허브로 옮겼다(그 유스케이스만 던졌다). 매장 접근 거절 셋은 tenancy 가 자기 라우터에서도 쓰므로 tenancy 오류는 남기고, 포트 구현만 허브 오류를 던진다.
- **허브 오류의 HTTP 상태는 `core/hub_errors.py` 한 곳.** 설계는 소비 스포크의 `error_map.py`에 매핑하라고 했다. core 자신이 `ShopAccessPort`를 소비하고, 같은 오류가 두 프로세스에서 같은 상태로 나가야 하므로 맵을 core 에 두고 `install_error_handlers`가 자동으로 등록한다. `tests/test_hub_errors.py`가 HubPortError 의 모든 하위 클래스가 맵에 있고 두 진입점에 핸들러가 있는지 확인한다.
- **재인증 가드의 위치(설계 B8 의 두 갈래).** 연결·해제·탈퇴 라우터는 모두 인증 프로세스에 있었다. 그래서 자리 없이 `auth/dependencies/recent_login_guard.py`로 옮기고, 창(300초)·시계 차 허용폭은 `auth/domain/services/recent_login.py`가 정한다. core 는 `get_access_claims`(토큰 검증 + 계정 상태)만 남았고 `get_current_user_id`의 서명은 그대로다.
- **스텁 ABC 상속은 공용 스텁만.** 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다(하네스 문서에 적었다).

### 계획서 코드와 실행이 다르지 않았던 것

작업 8개 모두 참조 작업 트리에서 먼저 돌려 검증한 코드다. 상태 집합의 단일 원천은 `domain/state/visit_status.py` 표이고, 상태 클래스(`visit_state.py`)·`ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·`DayCountsView.of`가 거기서 파생한다. ORM 문자열은 마이그레이션 0006 과 글자까지 같아 스키마 드리프트가 없다.

### 남는 것 — 알고 미룬다

- `transition_visits`가 잠그기 전에 `get_many`를 한 번 더 읽는다(되돌리기가 아니어도). `lock_visits`도 같은 것을 읽으므로 방문당 조회 하나가 늘었다. 조회 결과를 `lock_visits`에 넘기는 인자를 두면 없앨 수 있으나 잠금 순서 서비스의 서명을 늘리는 값어치가 없다고 봤다.
- 행동 축의 스키마 `Literal`(`transition_visits_schema.py`)은 API 계약이라 남긴다. 행동을 더하면 `ACTIONS`·바탕 메서드·스키마 셋을 고친다.
- 상태를 더하면 여전히 새 마이그레이션이 필요하다(CHECK·부분 색인). 표 하나에서 파생되므로 빠뜨릴 수 없을 뿐이다.
```

- [ ] **Step 2: 전체를 마지막으로 확인한다**

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"` → 765 passed

Run (`infra/`): `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration` → 260 passed

Run (`infra/`): `docker compose run --rm --no-deps backend lint-imports --config .importlinter` → 6 kept, 0 broken

Run (`infra/`): `docker compose run --rm --no-deps auth python scripts/print_routes.py > /tmp/routes_after.txt && diff /tmp/routes_before.txt /tmp/routes_after.txt` → 컨테이너 이름 두 줄만 다르다(작업 1 전에 `/tmp/routes_before.txt`로 받아 둔 것과 비교)

Run (저장소 루트): `git diff ref/record-4-0-be -- backend _docs | head` → 비어 있다(참조 브랜치와 파일이 같다). 비어 있지 않으면 어느 작업의 diff 가 어긋났는지 찾아 고친다.

- [ ] **Step 3: 커밋한다**

```bash
git add -A
git commit -m "docs: 결정 기록 007 — ④-0 SOLID 정리(백엔드)에서 설계와 다르게 간 것과 남는 것

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"
```

---

## 계획 자체 점검(작성 시)

- 설계 4.1 표 B1~B10 → 작업: B1=2, B2=1, B3=3, B4·B6=4, B5=5, B7=6, B8=7, B9·B10=유지(작업 없음). 13절 첫 줄의 ④-0 검증 기준(단위·통합·계약 통과, 라우트 표 동일, API JSON 동일, 새 테스트 넷)은 작업 1·2·3·5·7 의 테스트와 작업 8 의 마지막 확인이 덮는다. 설계가 말한 "라우터 가드 전수"는 앱 몫(④-0 앱)이다.
- 자리 표시자 없음. 코드 블록은 참조 브랜치 커밋에서 기계적으로 뽑았다.
- 이름 일관성: `VisitLookupRepository`·`VisitWriteRepository`·`VisitHistoryRepository`·`VisitLedgerRepository`·`VisitBoardRepository`(작업 2 → 3·4·5), `HubPortError`와 하위 8개(작업 1 → 3), `apply_completion_effects`(작업 4), `COUNTED_STATUSES`·`status_list_sql`(작업 5), `get_access_claims`(작업 7)가 뒤 작업에서 같은 이름으로 쓰인다.
- Review Focus 다섯 줄 모두 해당 작업에 테스트가 있다.
