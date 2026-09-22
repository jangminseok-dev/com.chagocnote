# 차곡노트 ② 고객·반려동물 — 계획 ②-1: 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장 멤버가 고객(보호자)·반려동물·질병을 등록·조회·수정하고, 전화번호 뒷자리·이름·한글 초성으로 가족 단위 검색을 하고, 사장이 고객을 익명화 삭제할 수 있는 백엔드 `customer` 스포크를 만든다. 첫 작업으로 앱 `Pressable`의 의미 노드 경계를 고친다.

**Architecture:** 새 스포크 `backend/apps/customer`를 API 프로세스(`main.py`)에 붙인다. 경로는 모두 `/v1/shops/{shop_id}` 아래이고 `core/shop_guard.py`로 `ShopContext`를 받는다. 유스케이스 14개가 수직 슬라이스 1:1로 있고, 리포지토리 세 개(고객·반려동물·질병 종류)와 검색 포트 `CustomerSearchPort`(구현: PostgreSQL `pg_trgm`) 뒤에서 일한다. 가족(고객·반려동물·질병)을 바꾸는 유스케이스는 맨 앞에서 고객 행을 잠그고, 같은 트랜잭션 안에서 검색 줄(`customer_search_entries`, 유일한 역정규화 표)을 다시 만든다. 응답의 보호자·반려동물 정보는 언제나 원본 표에서 읽는다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) + asyncpg · Alembic · Pydantic 2 · PostgreSQL 17(pgvector 이미지, `pg_trgm`) · import-linter 2 · pytest + pytest-asyncio · Docker Compose / 앱은 Task 1 만 — Flutter 3.44.8

**Spec:** `docs/superpowers/specs/2026-09-22-customer-pet-design.md` — 이 계획은 11절의 "②-1 백엔드"다: 3.1절(백엔드 몫과 미뤄 둔 `Pressable` 하나), 4~7절 전부, 9절 위협 점검표의 백엔드 몫, 10절의 백엔드 테스트. 실행자는 설계 문서와 `_docs/architecture.md`, `_docs/harness.md`, `_docs/decisions/003-account-lifecycle.md`(두 세션 경합 테스트의 교훈), `_docs/decisions/004-flutter-app-and-reauth.md`(앱 골격)를 함께 읽는다.

**계획의 위치:** ②의 구현 계획 두 개 가운데 첫 번째다. **②-1(이 문서, 백엔드)** → ②-2(앱: 고객 탭 목록·등록 3단계·반려동물 상세·수정·삭제·무지개다리, 시뮬레이터 흐름 확인). 이 계획이 끝나면 ②-2가 부를 API가 모두 있다. 결정 기록 005는 이 계획이 백엔드 몫을 쓰고 ②-2가 앱 몫을 더한다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준 상대 경로다. 절대 경로를 코드나 설정에 쓰지 않는다.
- 작업 브랜치는 `feat/customer-2a-backend`다(설계 커밋 `aed816a`가 있는 브랜치). `main`에서 직접 작업하지 않는다.
- **커밋은 사용자가 작업 단위 커밋을 허용한 경우에만 한다.** 허용하지 않았으면 각 작업의 마지막 "커밋" 단계를 건너뛰고 바뀐 파일 목록만 보고한다. 푸시는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이다.
- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 테스트의 매장 이름으로 쓰는 것은 괜찮다.
- 이 계획은 새 의존성을 추가하지 않는다(백엔드 `requirements.txt`, 앱 `pubspec.yaml` 모두).
- 백엔드 명령은 전부 `infra/`에서 `docker compose run --rm backend …`로 돌린다. 맥에 파이썬 환경을 만들지 않는다. 앱 명령은 `app/`에서 돌린다.
- **볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다.** 개발 DB 스키마는 Task 16 에서 `docker compose restart backend`(시작 명령이 `alembic upgrade head`를 돈다)로 한 번 올린다 — 표를 더할 뿐이다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `backend/core/singleton/secret_manager.py`에서만 쓴다.
- 비밀값과 토큰 원문을 로그·테스트 출력·문서에 남기지 않는다. `.env*` 파일 내용을 출력하지 않는다. **고객의 전화번호·이름도 로그에 남기지 않는다**(설계 8.2, C7).
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`_docs/architecture.md` 그대로)
- 스포크 안은 `adapter → app → domain` 방향으로만 의존한다. `dependencies/`는 조립 전용이다.
- 수직 슬라이스 1:1: 유스케이스마다 router·schema·dto·input 포트·interactor·provider·interactor 테스트를 하나씩 둔다. 요청 본문이 없고 응답도 다른 슬라이스의 스키마를 쓰는 슬라이스는 schema 를 생략한다(tenancy `remove_member`와 같다). 리포지토리·DTO 는 도메인 말로 이름 짓는다(`customer_repository`, `customer_view_dto`).
- 유스케이스는 app DTO(frozen dataclass)를 받는다. 스키마와 DTO 사이의 변환은 라우터가 한다(스키마의 `to_input()`/`of()`를 라우터가 부른다 — tenancy `ShopResponseSchema.of`와 같은 모양). 아웃바운드 포트는 인터랙터가 실제로 호출하는 메서드만 가진다.
- 새 라우터 묶음에는 `GET <prefix>/myself`를 둔다(`/v1/shops/{shop_id}/customers/myself`). 실제 엔드포인트·데이터·제약을 적는다.
- **스포크끼리 import 하지 않는다. `dependencies/`도 예외가 아니다.** 이 계획은 새 허브 포트를 만들지 않는다(설계 4절).
- `app`·`domain`은 `fastapi`, `sqlalchemy`, `redis`, `httpx`, `jose`, `cryptography`를 import 하지 않는다. `domain`은 `pydantic`과 `core`도 import 하지 않는다(표준 라이브러리만). `core`는 스포크를 import 하지 않는다. 구조 계약 6종이 그대로 통과해야 한다.
- 새 폴더 이름은 통상 이름(`services`, `pg`, `mappers`, `orm`)만 쓴다. GoF 패턴 폴더는 만들지 않는다.

데이터 (설계 6절 그대로)
- **모든 표는 3NF 다. 역정규화는 `customer_search_entries` 하나뿐이다.** 가린 번호·뒷자리·초성·나이 표시는 저장하지 않고 계산한다(검색 줄만 예외).
- **`customers.shop_id`는 tenancy 의 매장 ID 라 외래 키 없이 인덱스만 둔다.** 스포크 안의 관계(고객 → 반려동물 → 질병, 검색 줄 → 고객)는 외래 키를 건다. `pets`에 `shop_id`를 두지 않는다.
- 설계 6.1절의 CHECK·부분 유일 색인을 그대로 만든다: `UNIQUE (shop_id, phone) WHERE deleted_at IS NULL`, `deleted_at IS NOT NULL OR (name IS NOT NULL AND phone IS NOT NULL)`, `species IN ('dog','cat')`, `sex IN ('female','male')`, `weight_kg > 0`, `birth_date IS NULL OR birth_year IS NULL`, `(type_code = 'other') = (custom_label IS NOT NULL)`, `UNIQUE (pet_id, type_code) WHERE type_code <> 'other'`, `terms`의 `gin_trgm_ops` GIN 색인, `(shop_id, last_activity_at)`·`(shop_id, sort_name)` 색인.
- 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 ORM 과 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에, 새 시드 표는 루트 `conftest.py`의 `_KEEP_TABLES`에 등록한다.
- 전화번호는 숫자만 저장한다. 문자열은 앞뒤 공백을 없애고 빈 문자열은 null 이다. 길이: 이름 50, 품종 50, 질병 직접 입력 30, 질병 메모 100, 메모 500.

행동 규칙
- **매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.** 예외는 매장과 상관없는 시드 표를 읽는 `ConditionTypeRepository.list_all()` 하나다.
- 다른 매장의 고객·반려동물 ID 는 404 다(존재 여부를 알리지 않는다). 반려동물은 반려동물 → 고객(살아 있음) → 매장 순서로 소속을 거른다. 익명화한 고객은 모든 조회·수정·검색·번호 조회에서 없는 것으로 본다.
- **가족(고객·반려동물·질병)을 바꾸는 유스케이스는 맨 앞에서 고객 행을 `FOR UPDATE`로 잠그고 다시 읽는다**(`lock_active` / `lock_owner`). 같은 트랜잭션 안에서 `rebuild_search_entry(ctx, customer_id)`를 부른다. customer 경로는 tenancy 의 행(유저·매장·멤버·초대)을 잠그지 않으므로 기존 잠금 순서(유저 → 매장 → 멤버 → 초대)와 겹치지 않는다. 잠금을 쥔 채 외부 HTTP 를 부르지 않는다(이 계획에는 외부 HTTP 가 없다).
- 오류 본문은 `{"code", "message"}`다. 도메인 규칙 위반은 도메인 예외로 던지고 `error_map.py`가 HTTP 상태로 바꾼다. 새 코드: `CUSTOMER_NOT_FOUND`·`PET_NOT_FOUND`(404), `CUSTOMER_PHONE_TAKEN`·`LAST_PET`(409), `PET_HEALTH_REQUIRED`·`PET_HEALTH_CONFLICT`(422). 그 밖의 입력 규칙 위반은 422 `VALIDATION_ERROR`다.
- 테스트는 mock 프레임워크 대신 스텁 구현을 쓴다. 실제 DB 에 붙는 테스트는 `integration` 마커를 단다. 두 세션 경합 테스트는 `asyncio.gather`가 아니라 "막힌 호출을 `create_task`로 들고 있다가 앞선 세션의 커밋 뒤 결과를 본다" 방식이고, 잠금 코드를 빼는 변이로 실패하는지 확인한다(결정 003).
- I/O 는 `async def`, CPU 작업은 `def`다. 포트와 구현체의 `def`/`async def`를 일치시킨다.

검증 명령의 줄임말 (`infra/`에서)
- **단위 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"`
- **통합 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`
- **구조 계약**: `docker compose run --rm --no-deps backend lint-imports --config .importlinter`
- 파일 하나만: `docker compose run --rm backend pytest <backend/ 기준 경로> -q -p no:cacheprovider` (통합 테스트 파일이면 마커 없이 그대로 돈다)

## 이 계획에서 새로 정한 것

설계 7.3 의 "4자리 이하면 뒷자리 우선"(그 밖의 정렬과 섞어 보여 준다)은 "뒷자리로만"으로 좁혔다(가운데 자리 3~4자리로는 찾지 못하고, 5자리 이상은 전체 번호 부분 일치다) — 순위 섞기가 커서 페이지와 충돌해서다. 그 밖에 설계와 모순되는 것은 없다. 설계의 빈틈을 가장 작게 메운 것과, 계획을 쓰며 코드를 읽다 찾은 것이다. 결정 기록 005(Task 16)에 같은 내용을 옮긴다.

1. **가족을 바꾸는 쓰기는 고객 행을 먼저 잠근다 (C13·C14, 설계 9절에 없던 경합).** `pets` INSERT 가 고객 행에 거는 암묵적 `KEY SHARE`는 익명화의 `UPDATE customers`(키가 아닌 칸 — `NO KEY UPDATE`)와 충돌하지 않는다. 잠금이 없으면 ① 익명화와 겹친 반려동물 추가가 익명화한 고객에게 이름 있는 반려동물을 붙이고 검색 줄을 되살린다 ② 마지막 두 마리를 동시에 지우면 둘 다 "두 마리"로 세어 반려동물 없는 가족이 남는다. 잠금을 기다린 뒤에는 PostgreSQL 이 `deleted_at IS NULL` 조건을 다시 평가하므로 익명화된 고객은 404 가 된다.
2. **접근 로그의 쿼리 문자열을 가린다 (C7).** 번호 조회(`?phone=`)와 검색(`?q=`)은 설계대로 GET 쿼리다. uvicorn 접근 로그가 쿼리를 그대로 남기므로 API 프로세스가 `uvicorn.access` 로거에 쿼리를 `?[가림]`으로 바꾸는 필터를 단다(`core/access_log.py`). 게이트웨이(Caddy)는 접근 로그를 켜지 않았다.
3. **`rebuild_search_entry(ctx, customer_id)`는 리포지토리가 아니라 `CustomerSearchPort`에 둔다.** 설계 6.4 는 "리포지토리 한 메서드"라고 했지만, 전용 검색 엔진으로 바꿀 때 색인 쓰기도 함께 바뀌어야 하므로 검색 포트가 맡는다. 이름과 동작(같은 트랜잭션, 원본에서 다시 만든다, 익명화면 지운다)은 설계 그대로다.
4. **요청·응답 모양.** 등록 본문은 `{"customer": {…}, "pet": {…}}`. 등록·고객 수정·고객 상세는 `{customer, pets}`(고객 상세, 전체 번호 포함)를, 반려동물 추가·상세·수정·무지개다리·되돌리기는 `{pet, owner, siblings}`(반려동물 상세, 보호자 번호는 가림)를 돌려준다. 삭제 둘은 204. 몸무게는 JSON 숫자로 나간다.
5. **목록 응답은 `{items, next_cursor, pet_count}`다.** `pet_count`는 검색·무지개다리 조건에 맞는 반려동물 수 — 앱 제목 "고객 N마리"(설계 8.1)에 쓴다. 커서는 정렬 키·고객 ID 를 담은 불투명 문자열이고, 틀리거나 다른 정렬의 커서면 422 다.
6. **뒷자리 검색은 "4자리 이하 숫자 → 번호 뒷자리가 그 숫자로 시작"이다**(치는 중인 `56`도 `5678`을 찾는다). 5자리 이상은 전체 번호 부분 일치, 하이픈은 무시한다. 초성 검색은 검색 문자열에 초성을 함께 넣어 일반 부분 일치로 찾는다.
7. **가나다순의 키는 보호자 이름이다.** 한글과 숫자·영문 사이의 순서는 DB 정렬 규칙(개발 DB `en_US.utf8` — 한글이 먼저)을 따른다.
8. **최근순의 키는 고객과 그 반려동물의 `updated_at` 가운데 가장 늦은 값이다.** 수정(PUT)·무지개다리는 값이 같아도 `updated_at`을 새로 찍는다. 반려동물 삭제는 활동으로 치지 않는다.
9. **나이 표시:** 생일이 있으면 만 나이(1살 전에는 "N개월"), 태어난 해만 있으면 해의 차이("1살 미만"), 둘 다 없으면 "나이 모름". 기준 날짜는 한국 시각(UTC+9)의 오늘이다. 생일은 오늘보다 늦을 수 없고, 생일·태어난 해는 40년 전까지 받는다.
10. **번호 조회의 `pet_names`에는 무지개다리 아이를 넣지 않는다.** 무지개다리를 다시 누르면 처음 시각을 지킨다. 반려동물 삭제의 "마지막" 판단에는 무지개다리 아이도 센다(기록이 남은 가족을 반려동물 없는 가족으로 만들지 않는다).
11. **전화번호 형식:** 휴대전화(010·011·016~019), 서울(02), 지역 번호(031~065 범위의 세 자리, 없는 국번 포함), 인터넷 전화(070). `+82` 표기와 전각 숫자는 받지 않는다. 보조 연락처도 같은 형식을 본다.
12. **질병 항목은 한 번에 20개까지.** 모르는 질병 종류, 기타가 아닌데 이름을 넣은 것, 기타인데 이름이 없는 것, 같은 정해진 질병 두 번은 422 `VALIDATION_ERROR`(도메인 예외 `CustomerInputError`)다. 없으면 외래 키·유일 색인 위반이 500 이 된다.
13. **칸 형식.** ID 는 설계대로 `bigint`(기존 표는 `integer`)이고 경로 변수는 bigint 상한을 넘으면 DB 에 닿기 전에 422 다. 문자열 칸은 기존 관례대로 길이 제한 `varchar`다(설계 표의 `text` 대신 — 검색 문자열 `terms`만 `text`). 전화번호 칸은 11자.
14. **검색 줄 재생성 스크립트 `backend/scripts/rebuild_customer_search.py`**(설계 6.4 "재생성 스크립트로 복구한다")를 둔다.
15. **자기소개(`/customers/myself`)는 매장 경로 아래라 소속 확인을 거친다**(설계 5절 표의 "멤버"). 토큰 없는 `/v1/shops/myself`(tenancy)와 다르다.

## 이 계획의 코드는 어떻게 검증했나

계획 2-1·2-2 에서 검증 없이 쓴 계획서 코드에 결함이 많았다(2-2 는 13개 작업 중 11개). 그래서 **이 계획서의 코드는 저장소 안의 임시 작업 트리에서 실제로 만들어 돌린 것을 그대로 옮겼다.**

- 작업 트리: `.superpowers/ref/wt-customer-2a` (git 무시 대상). 컨테이너 안에서는 `/work/.superpowers/ref/wt-customer-2a`로 보여서 `docker compose run -w … -e PYTHONPATH=…`로 원래 체크아웃을 건드리지 않고 돌렸다.
- 브랜치 `ref/customer-2a`: 처음 구현한 것(버리는 브랜치). 브랜치 `ref/customer-2a-plan`: **이 계획서의 작업 순서대로 다시 쌓은 것** — 작업마다 단위·구조 계약(DB 가 걸린 작업은 통합까지)을 돌리고 커밋했다. 결과는 아래 표다. 두 브랜치의 최종 코드는 `main.py`의 라우터 장착 순서만 다르다(문서는 결정 기록 005 의 한 문장을 이 계획 쪽에서 바로잡았다). 계획서의 코드 블록은 `ref/customer-2a-plan`에서 옮겼다.

  | 작업 | 단위 | 통합 | 구조 계약 |
  |---|---|---|---|
  | 1 (앱) | — | — | `flutter analyze` 0건, `flutter test` 240 |
  | 2 | 321 | — | 6 kept |
  | 3 | 340 | — | 6 kept |
  | 4 | 340 | 143 | 6 kept |
  | 5 | 340 | 158 | 6 kept |
  | 6 | 340 | 174 | 6 kept |
  | 7 | 353 | 174 | 6 kept |
  | 8 | 365 | 174 | 6 kept |
  | 9 | 375 | 174 | 6 kept |
  | 10 | 381 | 174 | 6 kept |
  | 11 | 391 | 174 | 6 kept |
  | 12 | 405 | 174 | 6 kept |
  | 13 | 408 | — | 6 kept |
  | 14 | 408 | 183 | 6 kept |
  | 15 | 408 | 187 | 6 kept |
  | 16 | 408 | 188 | 6 kept |
- 최종 상태: 단위 **408** 통과(기준 291 + 117), 통합 **188** 통과(기준 137 + 51), 구조 계약 **6 kept, 0 broken**, `flutter analyze` **0건**, `flutter test` **240** 통과(기준 238 + 2).
- 변이로 판별력을 확인했다: ① 부분 유일 색인을 일반 색인으로 → C2 동시 등록 테스트 포함 5개 실패 ② `add_pet`의 `lock_active`를 `get_active`로 → C14 추가 테스트 실패 ③ `lock_owner`의 `FOR UPDATE`를 빼면 → C13 동시 삭제 테스트 실패. 처음 쓴 **반려동물 수정 × 익명화 테스트는 ③에서도 통과해**(익명화가 `pets` 행도 고쳐서 행 잠금과 다시 읽기로 같은 결과가 난다) 판별력이 없었다 — Task 15 가 저장소 수준 테스트 `test_lock_owner가_고객_행을_쥔_동안_다른_세션의_고객_잠금은_기다린다`로 바꿨고, 이 테스트는 ③에서 실패한다(판별력 있음) ④ `Pressable`의 `container: true`를 `false`로 → 되돌린 `app_router_test`가 실패 ⑤ `_like_escape`를 값 그대로 돌려주게 → 특수 문자 테스트 실패 ⑥ `main.py`의 `redact_access_log_queries()` 호출을 막으면 → 필터 장착 테스트 실패 ⑦ `lookup_customer_router`를 `{customer_id}` 라우터 뒤로 옮기면 → 배선 테스트 2개 실패. 각 작업의 "판별력 확인" 단계가 이 변이들이다.
- 마이그레이션 `0005`는 테스트 DB 에서 `downgrade 0004` → `upgrade head`를 한 번 돌려 되돌리기도 확인했다.
- 접근 로그 가림은 작업 트리 코드로 실제 uvicorn 을 띄워 `GET …/customers/lookup?phone=…` 요청의 로그가 `…/customers/lookup?[가림]`로 남는 것을 확인했다.
- 흐름 스크립트 `check_customer_flow.sh`는 게이트웨이가 원래 체크아웃의 코드를 돌리므로 그대로는 돌릴 수 없었다. 대신 작업 트리의 인증·API 앱을 한 프로세스에 묶은 대역 서버(테스트 DB, Redis db 14)에 `BASE`를 바꿔 20단계 모두 통과를 확인했다. **실제 게이트웨이(Caddy) 경유 실행은 미검증이다** — Task 16 에서 실행자가 돌린다.
- 라우트 표(`print_routes.py`)에 customer 경로 14개가 API 프로세스(`backend`)로 나오는 것을 확인했다.
- **검증하지 않은 것:** 실제 게이트웨이 경유 흐름 스크립트, 개발 DB 에 `0005` 올리기(작업 트리는 테스트 DB 에만 올렸다), `rebuild_customer_search.py`의 `main()`(개발 DB 를 대상으로 하므로 돌리지 않았다 — `rebuild_all()`은 테스트했다).

그래도 규칙은 같다. **검토자는 이 계획서의 코드를 검토되지 않은 것으로 본다.** 작업 트리는 "컴파일되고 자기 테스트를 통과한다"까지만 보장한다. 테스트가 옳은 것을 확인하는지, 빠진 시나리오가 없는지는 아래 위협 점검표와 설계를 기준으로 판단한다.

수정하는 파일은 `diff` 블록으로 보인다 — `-` 줄을 지우고 `+` 줄을 더한다.

## 위협 점검표

계획 2-1 에서는 작업별 검토가 "계획서 코드와 일치하는가"만 확인하는 바람에 계획서 자체의 구멍이 최종 검토까지 통과했다. 설계 9절의 C1~C12 가운데 백엔드 몫과, 이 계획을 쓰며 코드를 읽다 찾은 C13~C21 을 적었다. 각 줄에 막는 코드와 테스트를 짝지었다. **구현자와 검토자는 이 표를 코드와 대조한다. 표에 없는 시나리오를 찾으면 보고한다.**

| # | 시나리오 | 막는 것 | 확인하는 테스트 |
|---|---|---|---|
| C1 | A매장 멤버가 B매장 고객·반려동물의 경로나 ID 를 부른다 | B매장 경로는 매장 접근 확인(기존)이 403. 내 매장 경로에 B의 ID 를 넣으면 모든 리포지토리가 `ShopContext.shop_id`로 걸러 404 | Task 14 `test_다른_매장의_고객과_반려동물에는_손댈_수_없다`(스포크의 첫 통합 테스트), Task 5 `test_등록한_고객을_컨텍스트의_매장에서만_읽는다`·`test_다른_매장에서는_반려동물이_없는_것과_같다`·`test_다른_매장의_고객은_고치지_못한다`·`test_다른_매장의_익명화는_아무것도_지우지_않는다`, Task 6 `test_다른_매장의_가족은_찾지_않는다`·`test_다른_매장_컨텍스트로는_검색_줄을_지우지도_만들지도_못한다` |
| C2 | 두 기기가 같은 번호로 동시에 등록한다 | 부분 유일 색인 `uq_customers_shop_phone_active` — 늦은 쪽은 색인에서 기다렸다가 위반 → 세이브포인트 → 409 `CUSTOMER_PHONE_TAKEN` | Task 15 `test_같은_번호의_동시_등록은_하나만_성공하고_늦은_쪽은_409_다`, Task 5 `test_같은_매장의_살아_있는_번호는_CUSTOMER_PHONE_TAKEN_이다`·`test_번호를_바꾸다_겹치면_CUSTOMER_PHONE_TAKEN_이다`, Task 4 `test_살아_있는_고객의_번호는_매장_안에서_하나다` |
| C3 | 삭제한 고객의 번호로 다시 등록한다 | 유일 색인이 `deleted_at IS NULL`에만 걸린다 → 새 고객 | Task 5 `test_익명화는_개인정보만_지우고_틀을_남긴다`, Task 14 `test_등록부터_익명화까지_돈다` |
| C4 | 직원이 고객을 삭제한다 | `require_permission("customer:delete")` → 403 | Task 9 `test_직원은_고객을_삭제하지_못한다`, Task 14 `test_직원은_등록하고_고치지만_고객을_삭제하지_못한다` |
| C5 | 내보내진 직원이 목록을 계속 본다 | 매 요청의 매장 접근 확인(기존). 앱의 `NOT_A_MEMBER` → 재조회는 ②-2 몫 | Task 14 `test_내보낸_직원은_받은_토큰으로도_목록을_볼_수_없다` |
| C6 | 삭제된 고객이 검색·번호 조회·상세에 걸린다 | 익명화 뒤 `rebuild_search_entry`가 검색 줄을 지운다. 모든 리포지토리가 `deleted_at IS NULL`로 거른다 | Task 6 `test_익명화하면_검색_줄이_지워진다`, Task 5 `test_익명화한_고객의_반려동물은_없는_것과_같다`, Task 14 `test_등록부터_익명화까지_돈다`(조회·번호 조회·검색 다섯 가지) |
| C7 | 목록·로그에 전체 번호가 노출된다 | 목록·반려동물 상세는 `mask_phone` 값만(스키마에 전체 번호 칸이 없다). 오류 문구에 번호를 담지 않는다. 접근 로그의 쿼리는 C15 | Task 2 `test_오류_문구에_입력한_번호를_담지_않는다`, Task 10 `test_검색_순서대로_가족_카드를_만들고_번호는_가린다`·`test_멤버는_기본값으로_목록을_본다`, Task 7 `test_멤버는_반려동물_상세를_보고_보호자_번호는_가려져_있다` |
| C8 | 질병과 "질병 없음"을 함께 보내거나 둘 다 비운다 | 도메인 `check_conditions` → 422 `PET_HEALTH_CONFLICT`/`PET_HEALTH_REQUIRED`. 인터랙터가 쓰기 전에 검증한다 | Task 3 `test_둘_다_아니면_PET_HEALTH_REQUIRED_다`·`test_둘_다면_PET_HEALTH_CONFLICT_다`, Task 11 `test_질병_규칙을_어기면_잠그지도_않는다`, Task 14 `test_같은_번호와_질병_규칙_위반은_설계의_오류다` |
| C9 | 다른 매장 고객의 반려동물 ID 를 끼워 넣는다 | 반려동물 경로는 반려동물 → 고객(살아 있음) → 매장으로 거른다. 추가는 넣은 뒤 `get(ctx)`로 다시 읽어 소속이 아니면 404 로 요청째 되돌린다 | Task 5 `test_다른_매장_고객에게_반려동물을_붙이면_404_다`, Task 14 C1 테스트의 "내 매장 경로" 절반 |
| C10 | 검색어에 LIKE 특수 문자(`%`, `_`, `\`) | 어댑터의 `_like_escape` + `ESCAPE '\'` | Task 6 `test_LIKE_특수_문자는_글자_그대로_찾는다`, Task 14 `test_뒷자리_초성_여러_낱말_특수_문자로_찾는다` |
| C11 | 검색 줄이 원본과 어긋난다 | 가족을 바꾸는 유스케이스가 같은 트랜잭션에서 다시 만든다. 응답은 원본에서 읽고, 검색 줄에만 있는 ID 는 버린다. 재생성 스크립트 | 인터랙터 테스트의 호출 기록(`("rebuild", …)`가 쓰기 뒤에 있다 — Task 8~12), Task 10 `test_검색_줄에_있어도_원본에_없는_가족은_빼고_원본을_따른다`, Task 16 `test_어긋난_검색_줄을_원본에서_다시_만든다` |
| C12 | 늦게 온 옛 검색 결과가 새 결과를 덮는다 | 앱 몫(②-2) | — |
| C13 | 마지막 두 마리를 동시에 지운다 → 반려동물 없는 가족 | `lock_owner`로 고객 행을 잠근 뒤 센다 → 늦은 쪽은 409 `LAST_PET` | Task 15 `test_마지막_두_마리를_동시에_지우면_하나는_LAST_PET_이다`, Task 12 `test_마지막_반려동물이면_LAST_PET_이다` |
| C14 | 익명화와 겹친 반려동물 추가·수정이 익명화한 고객에게 이름을 되살리고 검색 줄을 만든다 | 가족을 바꾸는 유스케이스가 맨 앞에서 고객 행을 `FOR UPDATE`로 잠근다. 풀려난 뒤 `deleted_at IS NULL` 재평가로 404 | Task 15 `test_익명화가_고객을_쥔_동안_반려동물_추가는_기다리고_뒤에는_404_다`(판별), `test_lock_owner가_고객_행을_쥔_동안_다른_세션의_고객_잠금은_기다린다`(저장소 수준 판별 — `lock_owner`의 `FOR UPDATE`를 빼면 실패, 판별력 없던 반려동물 수정×익명화 테스트를 대신함), 인터랙터 테스트의 `("lock_customer", …)`가 맨 앞 |
| C15 | 번호 조회(`?phone=`)·검색어(`?q=`)가 uvicorn 접근 로그에 남는다 | `core/access_log.py`의 `QueryStringRedactor`를 `main.py`가 단다 | Task 13 `test_쿼리_문자열을_가리고_경로는_남긴다`·`test_API_프로세스는_접근_로거에_가림_필터를_단다` |
| C16 | `/customers/myself`·`/customers/lookup`이 `/customers/{customer_id}`에 먼저 걸려 422 가 된다 | `main.py`가 두 라우터를 `{customer_id}` 라우터보다 먼저 붙인다 | Task 14 `test_질병_종류와_자기소개는_멤버에게_보인다`, `test_등록부터_익명화까지_돈다`의 번호 조회 |
| C17 | bigint 를 넘는 ID 로 부르면 asyncpg 오류로 500 | 경로 변수 `Path(ge=1, le=9_223_372_036_854_775_807)` | Task 7 `test_범위를_벗어난_ID_는_DB_에_닿기_전에_422_다` |
| C18 | 마케팅 동의·중성화에 문자열 `"true"`를 보내 조용히 참이 된다 | `StrictBool` | Task 8 `test_형식이_틀리면_422_VALIDATION_ERROR_다` |
| C19 | 커서를 고쳐 다른 매장·다른 정렬의 행을 읽는다 | 커서는 위치(정렬 키, 고객 ID)만 담고 검색은 언제나 `shop_id`로 거른다. 틀리거나 다른 정렬의 커서는 422 | Task 6 `test_엉터리_커서는_VALIDATION_ERROR_다`·`test_다른_정렬의_커서는_VALIDATION_ERROR_다`, Task 14 `test_목록은_30_가족씩_커서로_이어진다` |
| C20 | 테스트가 질병 종류 시드를 비워 다음 테스트부터 등록이 실패한다 | 루트 `conftest.py`의 `_KEEP_TABLES`에 `pet_condition_types` | Task 4 `test_질병_종류_시드가_설계_순서대로_들어_있다`(통합 전체에서 매번 통과) |
| C21 | 모르는 질병 코드·같은 질병 두 번 → 외래 키·유일 색인 위반으로 500 | 인터랙터가 질병 종류 표의 코드로 먼저 확인 → 422 | Task 3 `test_모르는_종류는_VALIDATION_ERROR_다`·`test_같은_정해진_질병을_두_번_넣을_수_없다`, Task 14 `test_같은_번호와_질병_규칙_위반은_설계의_오류다` |

**이 계획으로도 남는 것 (Task 16 에서 결정 기록에 적는다):** 요청 가드가 소속을 확인한 뒤 고객 행 잠금을 기다리는 사이 내보내진 직원의 쓰기는 그대로 끝난다(tenancy `update_shop`과 같은 모양, 003 의 "남는 것"). 고객 쓰기는 매장 행을 잠그지 않으므로 행위자를 다시 확인하려면 잠금 순서를 새로 정해야 한다.

## 시작 전 기준선

`feat/customer-2a-backend`(`aed816a`)의 상태다. 시작 전에 한 번 확인한다.

- 단위 291개, 통합 137개가 통과한다. 구조 계약 6종이 통과한다(`Contracts: 6 kept, 0 broken.`). `docker compose run --rm backend alembic current`는 `0004 (head)`.
- `app/`에서 `flutter analyze` 0건, `flutter test` 238개 통과.
- `docker compose ps`에서 여섯 서비스가 모두 `running`이다. 아니면 `docker compose up -d`를 먼저 한다.

## 파일 지도

```
app/lib/design/widgets/pressable.dart · app/test/design/pressable_test.dart · app/test/core/router/app_router_test.dart   # Task 1
backend/
├── .importlinter · orm_registry.py · conftest.py · main.py
├── alembic/versions/0005_customer_tables_and_seed.py
├── core/access_log.py
├── scripts/rebuild_customer_search.py · check_customer_flow.sh
├── tests/test_access_log.py · test_rebuild_customer_search.py
├── tests/integration/test_customer_flow_wiring.py · test_customer_locking.py
└── apps/customer/
    ├── CLAUDE.md → _docs/CLAUDE.md
    ├── domain/
    │   ├── errors.py
    │   ├── entities/{customer,pet,condition_type}.py
    │   ├── value_objects/{condition_entry,customer_profile,pet_profile}.py
    │   └── services/{phone_number,hangul_initials,search_terms,pet_age,pet_health}.py
    ├── app/
    │   ├── dtos/{customer_input,customer_view,customer_search}_dto.py + 슬라이스 DTO 14개
    │   ├── ports/input/ 14개 · ports/output/{customer_repository,pet_repository,condition_type_repository,customer_search_port,customer_myself_record_port}.py
    │   ├── services/detail_reader.py
    │   └── use_cases/ 14개
    ├── adapter/
    │   ├── inbound/api/{error_map,path_params}.py · schemas/ · v1/ 14개
    │   └── outbound/orm/customer_orm.py · mappers/customer_mapper.py · log_customer_myself_record_adapter.py
    │       pg/{customer_pg_repository,pet_pg_repository,condition_type_pg_repository,customer_search_pg_adapter}.py
    ├── dependencies/customer_wiring.py + 프로바이더 14개
    └── tests/{domain,app/use_cases,adapter,helpers}/
_docs/harness.md · _docs/decisions/005-customer-pet.md · README.md
```

| 슬라이스 | 표면 | 권한 | 작업 |
|---|---|---|---|
| `get_customer` | `GET /v1/shops/{shop_id}/customers/{customer_id}` | 멤버 | 7 |
| `get_pet` | `GET /v1/shops/{shop_id}/pets/{pet_id}` | 멤버 | 7 |
| `list_pet_condition_types` | `GET /v1/shops/{shop_id}/pet-condition-types` | 멤버 | 7 |
| `customer_myself` | `GET /v1/shops/{shop_id}/customers/myself` | 멤버 | 7 |
| `register_customer` | `POST /v1/shops/{shop_id}/customers` | `customer:write` | 8 |
| `lookup_customer` | `GET /v1/shops/{shop_id}/customers/lookup?phone=` | 멤버 | 8 |
| `update_customer` | `PUT /v1/shops/{shop_id}/customers/{customer_id}` | `customer:write` | 9 |
| `delete_customer` | `DELETE /v1/shops/{shop_id}/customers/{customer_id}` | `customer:delete` | 9 |
| `list_customers` | `GET /v1/shops/{shop_id}/customers?q=&sort=&include_passed=&cursor=` | 멤버 | 10 |
| `add_pet` | `POST /v1/shops/{shop_id}/customers/{customer_id}/pets` | `customer:write` | 11 |
| `update_pet` | `PUT /v1/shops/{shop_id}/pets/{pet_id}` | `customer:write` | 11 |
| `mark_pet_passed_away` | `POST /v1/shops/{shop_id}/pets/{pet_id}/passed-away` | `customer:write` | 12 |
| `unmark_pet_passed_away` | `DELETE /v1/shops/{shop_id}/pets/{pet_id}/passed-away` | `customer:write` | 12 |
| `delete_pet` | `DELETE /v1/shops/{shop_id}/pets/{pet_id}` | `customer:write` | 12 |

---

### Task 1: 앱 — `Pressable`의 의미 노드를 버튼 크기로 가둔다

설계 3.1 이 ②-1 의 첫 작업으로 미뤄 둔 것이다(설계는 "결정 기록 004 의 남는 것"이라 적었지만 004 에는 그 줄이 없다 — 005 에 고친 사실을 적는다). `Pressable`의 `Semantics`가 자기 의미 노드를 만들지 않아서, 이름표와 "버튼" 표시가 조상 노드에 합쳐진다. `ListView` 행 안에서 `Align`으로 왼쪽에 둔 `AppBackButton`의 스크린리더 포커스와 `find.bySemanticsLabel`의 탭 위치가 행 전체 폭(800×44)으로 잡히고, 그 가운데를 누르면 버튼이 아니다. 그래서 `app_router_test`가 `find.byType(AppBackButton)`으로 우회하고 있다. `Semantics(container: true, …)`로 경계를 만들고, 우회를 되돌리고, 의미 노드 크기가 버튼 크기(최소 44×44)인지 단언한다. 이 작업만 `app/`에서 돌린다.

**Files:**
- Modify: `app/lib/design/widgets/pressable.dart`
- Modify: `app/test/core/router/app_router_test.dart`
- Test: `app/test/design/pressable_test.dart`

**Interfaces:**
- Consumes: 없음
- Produces: `Pressable`의 공개 API 는 그대로다. 의미 노드가 `Pressable` 자신의 크기로 따로 잡힌다(골든은 바뀌지 않는다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`app/test/design/pressable_test.dart`:
```diff
@@ -12,6 +12,8 @@ Opacity _findOpacity(WidgetTester tester) =>
     tester.widget<Opacity>(find.byType(Opacity));
 
 void main() {
+  _semanticsBoundaryTests();
+
   testWidgets('누르는 중간에는 스케일이 1보다 작아진다', (tester) async {
     await tester.pumpWidget(
       CupertinoApp(
@@ -80,3 +82,40 @@ void main() {
     expect(size.height, greaterThanOrEqualTo(44));
   });
 }
+
+void _semanticsBoundaryTests() {
+  // 목록 행 안에서 왼쪽에 붙인 작은 버튼 — 설정 화면의 뒤로 가기와 같은 배치다.
+  Widget rowWithButton(VoidCallback onTap) => CupertinoApp(
+        home: ListView(
+          children: [
+            Align(
+              alignment: Alignment.centerLeft,
+              child: Pressable(
+                semanticLabel: '뒤로',
+                onTap: onTap,
+                child: const SizedBox(width: 24, height: 24),
+              ),
+            ),
+          ],
+        ),
+      );
+
+  testWidgets('의미 노드는 행 전체가 아니라 버튼 크기다', (tester) async {
+    final handle = tester.ensureSemantics();
+    await tester.pumpWidget(rowWithButton(() {}));
+
+    final node = tester.getSemantics(find.bySemanticsLabel('뒤로'));
+    expect(node.rect.size, const Size(44, 44));
+    handle.dispose();
+  });
+
+  testWidgets('이름표로 찾아 누르면 버튼이 눌린다', (tester) async {
+    var taps = 0;
+    await tester.pumpWidget(rowWithButton(() => taps++));
+
+    await tester.tap(find.bySemanticsLabel('뒤로'));
+    await tester.pumpAndSettle();
+
+    expect(taps, 1);
+  });
+}
```


- [ ] **Step 2: 돌려서 실패를 본다**

Run (`app/`에서): `flutter test test/design/pressable_test.dart`
Expected: FAIL 2개 — `의미 노드는 행 전체가 아니라 버튼 크기다`가 `Expected: Size(44.0, 44.0) Actual: Size(800.0, 44.0)`, `이름표로 찾아 누르면 버튼이 눌린다`가 `Expected: <1> Actual: <0>`.


- [ ] **Step 3: 구현한다**

`app/lib/design/widgets/pressable.dart`:
```diff
@@ -9,7 +9,8 @@ import '../tokens/app_springs.dart';
 /// - 누르는 순간 가벼운 햅틱을 준다.
 /// - `MediaQuery.disableAnimationsOf`가 true(시스템 "동작 줄이기")이면
 ///   스프링 스케일 대신 옅은 페이드로 대체한다.
-/// - `semanticLabel`을 주면 버튼으로 접근성에 노출한다.
+/// - `semanticLabel`을 주면 버튼으로 접근성에 노출한다. 의미 노드는 자기
+///   크기(최소 44×44)로 따로 잡힌다 — 행 안에 두어도 행 전체로 번지지 않는다.
 /// - 시각적 크기가 44×44보다 작아도 탭 영역은 `minSize`(기본 44) 이상을
 ///   보장한다.
 class Pressable extends StatefulWidget {
@@ -83,7 +84,11 @@ class _PressableState extends State<Pressable>
 
   @override
   Widget build(BuildContext context) {
+    // container: true — 자기 의미 노드를 따로 만든다. 없으면 이름표와 버튼
+    // 표시가 조상 노드(예: ListView 의 행)에 합쳐져, 스크린리더 포커스와
+    // 이름표로 찾은 탭 위치가 행 전체 폭으로 잡힌다.
     return Semantics(
+      container: true,
       button: widget.onTap != null,
       label: widget.semanticLabel,
       child: GestureDetector(
```


- [ ] **Step 4: 돌려서 통과를 본다**

Run: `flutter test test/design/pressable_test.dart`
Expected: `All tests passed!` (5개)


- [ ] **Step 5: 라우터 테스트의 우회를 되돌린다**

설정 화면의 뒤로 가기도 이제 이름표로 누를 수 있다. 쓰지 않게 된 `AppBackButton` import 도 지운다.
`app/test/core/router/app_router_test.dart`:
```diff
@@ -3,7 +3,6 @@ import 'package:chagocnote/core/proxy/providers.dart';
 import 'package:chagocnote/core/router/app_router.dart';
 import 'package:chagocnote/core/router/screen_keys.dart';
 import 'package:chagocnote/core/storage/token_store.dart';
-import 'package:chagocnote/design/widgets/app_back_button.dart';
 import 'package:chagocnote/features/auth/state/session.dart';
 import 'package:chagocnote/features/auth/state/session_controller.dart';
 import 'package:chagocnote/features/auth/state/session_gateway.dart';
@@ -273,9 +272,7 @@ void main() {
       await tester.pumpAndSettle();
       expect(find.byKey(ScreenKeys.settings), findsOneWidget);
 
-      // 설정의 뒤로 가기는 목록 행 안에서 왼쪽에 붙는다 — 의미 노드는 행 전체라
-      // 그 가운데를 누르면 버튼이 아니다. 위젯을 직접 누른다.
-      await tester.tap(find.byType(AppBackButton));
+      await tester.tap(find.bySemanticsLabel(AppStrings.back));
       await tester.pumpAndSettle();
 
       expect(find.byKey(ScreenKeys.home), findsOneWidget);
```


- [ ] **Step 6: 판별력을 확인한다**

`pressable.dart`의 `container: true`를 잠시 `container: false`로 바꾸고 `flutter test test/core/router/app_router_test.dart`를 돌린다 → `홈 → 설정 버튼 → 설정 화면 → 뒤로 → 홈 …` 테스트가 실패해야 한다. 되돌린다.


- [ ] **Step 7: 앱 전체를 확인한다**

Run (`app/`에서):
```bash
flutter analyze
flutter test
```
Expected: `No issues found!`, `All tests passed!` (240개 — 기준 238 + 2). 골든 파일은 바뀌지 않는다(`git status`에 `goldens/`가 없다).


- [ ] **Step 8: 커밋**

```bash
git add app/lib/design/widgets/pressable.dart app/test/design/pressable_test.dart app/test/core/router/app_router_test.dart
git commit -m "fix(app): Pressable 의 의미 노드를 버튼 크기로 가둔다"
```

---

### Task 2: customer 스포크 뼈대 — 도메인 오류, 전화번호, 초성, 검색 문자열

스포크 패키지를 만들고 구조 계약에 등록한 뒤, 표준 라이브러리만 쓰는 도메인 서비스 셋을 만든다(설계 4절). `phone_number`는 숫자만 남겨 한국 번호 형식을 검증하고 가린 표시를 만든다. `hangul_initials`는 음절을 초성으로 바꾼다. `search_terms`는 가족 한 줄의 검색 문자열을 만들고 검색어를 낱말로 나눈다(설계 7.3 — "이 계획에서 새로 정한 것" 6번의 뒷자리 규칙).

**Files:**
- Create: `backend/apps/customer/domain/errors.py`
- Create: `backend/apps/customer/domain/services/phone_number.py`
- Create: `backend/apps/customer/domain/services/hangul_initials.py`
- Create: `backend/apps/customer/domain/services/search_terms.py`
- Modify: `backend/.importlinter`
- Test: `backend/apps/customer/tests/domain/test_phone_number.py`
- Test: `backend/apps/customer/tests/domain/test_hangul_initials.py`
- Test: `backend/apps/customer/tests/domain/test_search_terms.py`
- Create: `backend/apps/customer/**/__init__.py` (빈 파일, 패키지 28개 — Step 1)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `customer.domain.errors`: `CustomerError`(바탕, `code` 속성) · `CustomerInputError`(`VALIDATION_ERROR`) · `CustomerNotFoundError` · `PetNotFoundError` · `CustomerPhoneTakenError` · `LastPetError` · `PetHealthRequiredError` · `PetHealthConflictError`
  - `customer.domain.services.phone_number`: `normalize_phone(raw: str) -> str`(형식이 아니면 `CustomerInputError`), `format_phone(digits: str) -> str`, `mask_phone(digits: str) -> str`, `phone_last4(digits: str) -> str`
  - `customer.domain.services.hangul_initials`: `to_initials(text: str) -> str`
  - `customer.domain.services.search_terms`: `SearchEntry(terms: str, phone_last4: str, sort_name: str)`, `SearchWord(kind: Literal["last4","phone","text"], value: str)`, `build_search_entry(customer_name: str, phone: str, pet_names: list[str]) -> SearchEntry`, `parse_query(q: str | None) -> tuple[SearchWord, ...]`

- [ ] **Step 1: 패키지를 만들고 구조 계약에 등록한다**

Run (`backend/`에서):
```bash
mkdir -p apps/customer/{_docs,domain/{entities,value_objects,services},app/{ports/{input,output},use_cases,dtos,services},adapter/{inbound/api/{schemas,v1},outbound/{orm,pg,mappers}},dependencies,tests/{domain,app/use_cases,adapter,helpers}}
touch apps/customer/__init__.py apps/customer/domain/__init__.py apps/customer/domain/entities/__init__.py apps/customer/domain/value_objects/__init__.py apps/customer/domain/services/__init__.py apps/customer/app/__init__.py apps/customer/app/ports/__init__.py apps/customer/app/ports/input/__init__.py apps/customer/app/ports/output/__init__.py apps/customer/app/use_cases/__init__.py apps/customer/app/dtos/__init__.py apps/customer/app/services/__init__.py apps/customer/adapter/__init__.py apps/customer/adapter/inbound/__init__.py apps/customer/adapter/inbound/api/__init__.py apps/customer/adapter/inbound/api/schemas/__init__.py apps/customer/adapter/inbound/api/v1/__init__.py apps/customer/adapter/outbound/__init__.py apps/customer/adapter/outbound/orm/__init__.py apps/customer/adapter/outbound/pg/__init__.py apps/customer/adapter/outbound/mappers/__init__.py apps/customer/dependencies/__init__.py apps/customer/tests/__init__.py apps/customer/tests/domain/__init__.py apps/customer/tests/app/__init__.py apps/customer/tests/app/use_cases/__init__.py apps/customer/tests/adapter/__init__.py apps/customer/tests/helpers/__init__.py
```

`backend/.importlinter`:
```diff
@@ -17,6 +17,7 @@ root_packages =
     auth
     tenancy
     platform_admin
+    customer
 include_external_packages = True
 
 [importlinter:contract:clean-architecture]
@@ -31,6 +32,7 @@ containers =
     auth
     tenancy
     platform_admin
+    customer
 
 [importlinter:contract:spoke-independence]
 name = 스포크 상호 독립 (스포크끼리 import 하지 않는다)
@@ -39,6 +41,7 @@ modules =
     auth
     tenancy
     platform_admin
+    customer
 
 [importlinter:contract:framework-isolation]
 name = 프레임워크 격리 (app·domain 은 웹·DB·외부 통신 라이브러리를 모른다)
@@ -51,6 +54,8 @@ source_modules =
     tenancy.domain
     platform_admin.app
     platform_admin.domain
+    customer.app
+    customer.domain
 forbidden_modules =
     fastapi
     sqlalchemy
@@ -66,6 +71,7 @@ source_modules =
     auth.domain
     tenancy.domain
     platform_admin.domain
+    customer.domain
 forbidden_modules =
     pydantic
     core
@@ -79,6 +85,7 @@ forbidden_modules =
     auth
     tenancy
     platform_admin
+    customer
 
 [importlinter:contract:core-isolation]
 name = core 격리 (core 는 스포크를 import 하지 않는다)
@@ -89,3 +96,4 @@ forbidden_modules =
     auth
     tenancy
     platform_admin
+    customer
```


- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/domain/test_phone_number.py`:
```python
import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.phone_number import (
    format_phone,
    mask_phone,
    normalize_phone,
    phone_last4,
)


@pytest.mark.parametrize(
    "raw, digits",
    [
        ("010-1234-5678", "01012345678"),
        (" 010 1234 5678 ", "01012345678"),
        ("011-123-4567", "0111234567"),
        ("02-123-4567", "021234567"),
        ("(02) 1234-5678", "0212345678"),
        ("031-123-4567", "0311234567"),
        ("064-7123-4567", "06471234567"),
        ("070-1234-5678", "07012345678"),
    ],
)
def test_숫자만_남기고_한국_번호_형식을_받는다(raw, digits):
    assert normalize_phone(raw) == digits


@pytest.mark.parametrize(
    "raw",
    ["", "1234", "010-123-456", "010-1234-56789", "012-1234-5678", "080-123-4567",
     "+82 10-1234-5678", "０１０-1234-5678", "010-abcd-5678"],
)
def test_형식이_아니면_VALIDATION_ERROR_다(raw):
    with pytest.raises(CustomerInputError) as caught:
        normalize_phone(raw)
    assert caught.value.code == "VALIDATION_ERROR"


def test_오류_문구에_입력한_번호를_담지_않는다():
    with pytest.raises(CustomerInputError) as caught:
        normalize_phone("010-1234")
    assert "1234" not in str(caught.value)


def test_하이픈_모양으로_보여_준다():
    assert format_phone("01012345678") == "010-1234-5678"
    assert format_phone("0111234567") == "011-123-4567"
    assert format_phone("021234567") == "02-123-4567"
    assert format_phone("0212345678") == "02-1234-5678"


def test_가운데_자리의_앞_두_글자만_남기고_가린다():
    assert mask_phone("01012345678") == "010-12··-5678"
    assert mask_phone("0111234567") == "011-12·-4567"
    assert mask_phone("021234567") == "02-12·-4567"
    assert mask_phone("0212345678") == "02-12··-5678"


def test_뒷자리_네_개():
    assert phone_last4("01012345678") == "5678"
```

`backend/apps/customer/tests/domain/test_hangul_initials.py`:
```python
from customer.domain.services.hangul_initials import to_initials


def test_한글_음절을_초성으로_바꾼다():
    assert to_initials("콩이") == "ㅋㅇ"
    assert to_initials("김민지") == "ㄱㅁㅈ"


def test_된소리와_겹받침도_초성만_남는다():
    assert to_initials("꽃닭") == "ㄲㄷ"
    assert to_initials("앉은뱅이") == "ㅇㅇㅂㅇ"


def test_한글이_아닌_글자는_그대로_둔다():
    assert to_initials("Coco콩2") == "Cocoㅋ2"
    assert to_initials("콩 이") == "ㅋ ㅇ"
    assert to_initials("ㅋㅇ") == "ㅋㅇ"
    assert to_initials("") == ""
```

`backend/apps/customer/tests/domain/test_search_terms.py`:
```python
from customer.domain.services.search_terms import SearchWord, build_search_entry, parse_query


def test_이름_초성_전화_숫자로_검색_문자열을_만든다():
    entry = build_search_entry("김민지", "01012345678", ["콩이", "두부"])
    assert entry.terms == "김민지 ㄱㅁㅈ 콩이 ㅋㅇ 두부 ㄷㅂ 01012345678"
    assert (entry.phone_last4, entry.sort_name) == ("5678", "김민지")


def test_영문_이름은_초성이_같아서_한_번만_넣는다():
    entry = build_search_entry("Mina", "01012345678", ["Coco"])
    assert entry.terms == "Mina Coco 01012345678"


def test_반려동물이_없어도_만든다():
    assert build_search_entry("콩이 보호자", "0212345678", []).terms == "콩이 보호자 ㅋㅇ ㅂㅎㅈ 0212345678"


def test_숫자_네_자리_이하는_뒷자리_그_이상은_전체_번호_검색이다():
    assert parse_query("5678") == (SearchWord("last4", "5678"),)
    assert parse_query("56") == (SearchWord("last4", "56"),)
    assert parse_query("1234-5678") == (SearchWord("phone", "12345678"),)
    assert parse_query("01012") == (SearchWord("phone", "01012"),)


def test_여러_낱말로_나눈다():
    assert parse_query("  5678  콩 ") == (SearchWord("last4", "5678"), SearchWord("text", "콩"))
    assert parse_query("ㅋㅇ") == (SearchWord("text", "ㅋㅇ"),)


def test_빈_검색어는_낱말이_없다():
    assert parse_query(None) == ()
    assert parse_query("   ") == ()
    assert parse_query("-") == (SearchWord("text", "-"),)
```



- [ ] **Step 3: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/domain/test_phone_number.py apps/customer/tests/domain/test_hangul_initials.py apps/customer/tests/domain/test_search_terms.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.domain.services.phone_number'` (세 파일 모두 import 오류)


- [ ] **Step 4: 구현한다**

`backend/apps/customer/domain/errors.py`:
```python
class CustomerError(Exception):
    """customer 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "CUSTOMER_ERROR"


class CustomerInputError(CustomerError):
    """형식은 맞지만 규칙에 어긋난 입력(전화번호 형식, 나이, 질병 항목, 커서). 스키마 검증과 같은 422 다."""

    code = "VALIDATION_ERROR"


class CustomerNotFoundError(CustomerError):
    code = "CUSTOMER_NOT_FOUND"


class PetNotFoundError(CustomerError):
    code = "PET_NOT_FOUND"


class CustomerPhoneTakenError(CustomerError):
    code = "CUSTOMER_PHONE_TAKEN"


class LastPetError(CustomerError):
    code = "LAST_PET"


class PetHealthRequiredError(CustomerError):
    code = "PET_HEALTH_REQUIRED"


class PetHealthConflictError(CustomerError):
    code = "PET_HEALTH_CONFLICT"
```

`backend/apps/customer/domain/services/phone_number.py`:
```python
"""전화번호 — 숫자만 남겨 검증하고, 목록에 보여 줄 가린 표시를 만든다.

저장·비교는 언제나 숫자만 쓴다. 하이픈·공백·괄호는 입력 편의일 뿐이다.
"""
from __future__ import annotations

import re

from customer.domain.errors import CustomerInputError

# 휴대전화(010·011·016~019), 서울(02), 지역 번호(031~064), 인터넷 전화(070).
_VALID = re.compile(r"^(01[016789]\d{7,8}|02\d{7,8}|0[3-6][1-5]\d{7,8}|070\d{8})$")


def normalize_phone(raw: str) -> str:
    """숫자만 남긴다. 한국 전화번호 형식이 아니면 CustomerInputError."""
    digits = "".join(ch for ch in raw if ch.isascii() and ch.isdigit())
    if not _VALID.match(digits):
        raise CustomerInputError("전화번호 형식이 올바르지 않습니다.")
    return digits


def _split(digits: str) -> tuple[str, str, str]:
    area = digits[:2] if digits.startswith("02") else digits[:3]
    return area, digits[len(area):-4], digits[-4:]


def format_phone(digits: str) -> str:
    """010-1234-5678 모양. 숫자만 저장된 번호를 보여 줄 때 쓴다."""
    return "-".join(_split(digits))


def mask_phone(digits: str) -> str:
    """가운데 자리의 앞 두 글자만 남기고 가린다. 010-1234-5678 → 010-12··-5678."""
    area, middle, last = _split(digits)
    return f"{area}-{middle[:2]}{'·' * (len(middle) - 2)}-{last}"


def phone_last4(digits: str) -> str:
    return digits[-4:]
```

`backend/apps/customer/domain/services/hangul_initials.py`:
```python
"""한글 초성 — 콩이 → ㅋㅇ. 초성 검색에 쓴다."""
from __future__ import annotations

_INITIALS = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_FIRST, _LAST = 0xAC00, 0xD7A3
_PER_INITIAL = 21 * 28  # 중성 21 × 종성 28


def to_initials(text: str) -> str:
    """한글 음절을 초성으로 바꾼다. 한글 음절이 아닌 글자(영문·숫자·자모)는 그대로 둔다."""
    return "".join(
        _INITIALS[(ord(ch) - _FIRST) // _PER_INITIAL] if _FIRST <= ord(ch) <= _LAST else ch
        for ch in text
    )
```

`backend/apps/customer/domain/services/search_terms.py`:
```python
"""검색 — 가족 한 줄의 검색 문자열을 만들고, 검색어를 낱말로 나눈다.

검색 문자열에는 보호자 이름·초성, 반려동물 이름·초성, 전화 숫자가 들어간다. 보조 연락처는 넣지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from customer.domain.services.hangul_initials import to_initials
from customer.domain.services.phone_number import phone_last4

WordKind = Literal["last4", "phone", "text"]
_LAST4_MAX = 4


@dataclass(frozen=True)
class SearchEntry:
    terms: str
    phone_last4: str
    sort_name: str


@dataclass(frozen=True)
class SearchWord:
    kind: WordKind
    value: str


def build_search_entry(customer_name: str, phone: str, pet_names: list[str]) -> SearchEntry:
    parts: list[str] = []
    for name in (customer_name, *pet_names):
        parts += [name, to_initials(name)]
    parts.append(phone)
    terms = " ".join(dict.fromkeys(parts))   # 순서를 지키며 겹치는 조각(영문 이름의 초성 등)을 뺀다
    return SearchEntry(terms=terms, phone_last4=phone_last4(phone), sort_name=customer_name)


def parse_query(q: str | None) -> tuple[SearchWord, ...]:
    """공백으로 낱말을 나눈다. 숫자(하이픈 허용)만이면 전화 검색 — 4자리 이하는 뒷자리, 그 이상은 전체 번호."""
    words = []
    for raw in (q or "").split():
        digits = raw.replace("-", "")
        if digits and digits.isascii() and digits.isdigit():
            words.append(SearchWord("last4" if len(digits) <= _LAST4_MAX else "phone", digits))
        else:
            words.append(SearchWord("text", raw))
    return tuple(words)
```



- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/domain/test_phone_number.py apps/customer/tests/domain/test_hangul_initials.py apps/customer/tests/domain/test_search_terms.py -q -p no:cacheprovider`
Expected: `30 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 단위 `321 passed`, `Contracts: 6 kept, 0 broken.`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/.importlinter backend/apps/customer
git commit -m "feat(customer): 스포크 뼈대와 전화번호·초성·검색 문자열"
```

---

### Task 3: 나이·질병 규칙과 검증된 입력 값 객체

반려동물 나이(생일·태어난 해·모름 중 하나, 나이 표시)와 질병 규칙("질병 있음" XOR "질병 없음 확인", 설계 6.1·7.1)을 도메인 서비스로 두고, 폼을 검증을 마친 값 객체(`CustomerProfile`, `PetProfile`)로 바꾸는 곳을 하나로 모은다. 리포지토리는 이 값 객체만 받는다 — 검증을 건너뛴 값이 DB 에 닿지 않는다. 질병 규칙은 두 표에 걸쳐 CHECK 로 쓸 수 없어서 여기서 확인한다(C8·C21). 나이 표시 규칙과 기준 날짜는 "이 계획에서 새로 정한 것" 9번이다.

**Files:**
- Create: `backend/apps/customer/domain/value_objects/condition_entry.py`
- Create: `backend/apps/customer/domain/services/pet_age.py`
- Create: `backend/apps/customer/domain/services/pet_health.py`
- Create: `backend/apps/customer/domain/value_objects/customer_profile.py`
- Create: `backend/apps/customer/domain/value_objects/pet_profile.py`
- Test: `backend/apps/customer/tests/domain/test_pet_age.py`
- Test: `backend/apps/customer/tests/domain/test_pet_health.py`
- Test: `backend/apps/customer/tests/domain/test_profiles.py`

**Interfaces:**
- Consumes: Task 2 의 `normalize_phone`, `CustomerInputError`·`PetHealthRequiredError`·`PetHealthConflictError`
- Produces:
  - `customer.domain.value_objects.condition_entry`: `OTHER = "other"`, `ConditionEntry(type_code: str, custom_label: str | None, note: str | None)`
  - `customer.domain.services.pet_age`: `seoul_today() -> date`, `check_birth(birth_date: date | None, birth_year: int | None, today: date) -> None`, `age_label(birth_date, birth_year, today) -> str`
  - `customer.domain.services.pet_health`: `check_conditions(conditions: tuple[ConditionEntry, ...], no_known_conditions: bool, known_codes: frozenset[str]) -> None`
  - `CustomerProfile(name, phone, phone_alt, marketing_consent, memo)` + `CustomerProfile.create(*, name, phone, phone_alt, marketing_consent, memo)` — 번호를 숫자만으로 바꾼다
  - `PetProfile(name, species, breed, sex, neutered, birth_date, birth_year, weight_kg: Decimal, no_known_conditions, memo, conditions)` + `PetProfile.create(*, …, known_condition_codes: frozenset[str], today: date)` — 나이·질병 규칙을 거친다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/domain/test_pet_age.py`:
```python
from datetime import date

import pytest

from customer.domain.errors import CustomerInputError
from customer.domain.services.pet_age import age_label, check_birth

TODAY = date(2026, 9, 22)


def test_생일과_태어난_해는_하나만_받는다():
    check_birth(date(2020, 1, 1), None, TODAY)
    check_birth(None, 2020, TODAY)
    check_birth(None, None, TODAY)   # 모름
    with pytest.raises(CustomerInputError):
        check_birth(date(2020, 1, 1), 2020, TODAY)


@pytest.mark.parametrize(
    "birth_date, birth_year",
    [(date(2026, 9, 23), None), (date(1985, 1, 1), None), (None, 2027), (None, 1985)],
)
def test_미래이거나_너무_오래된_값은_VALIDATION_ERROR_다(birth_date, birth_year):
    with pytest.raises(CustomerInputError):
        check_birth(birth_date, birth_year, TODAY)


def test_오늘_태어났거나_올해_태어난_것은_받는다():
    check_birth(TODAY, None, TODAY)
    check_birth(None, 2026, TODAY)


def test_생일이_있으면_만_나이이고_한_살_전에는_개월이다():
    assert age_label(date(2023, 9, 22), None, TODAY) == "3살"
    assert age_label(date(2023, 9, 23), None, TODAY) == "2살"    # 생일 전날
    assert age_label(date(2026, 3, 10), None, TODAY) == "6개월"
    assert age_label(date(2026, 9, 1), None, TODAY) == "0개월"
    assert age_label(date(2025, 9, 23), None, TODAY) == "11개월"


def test_태어난_해만_있으면_해의_차이다():
    assert age_label(None, 2021, TODAY) == "5살"
    assert age_label(None, 2026, TODAY) == "1살 미만"


def test_둘_다_없으면_나이_모름이다():
    assert age_label(None, None, TODAY) == "나이 모름"
```

`backend/apps/customer/tests/domain/test_pet_health.py`:
```python
import pytest

from customer.domain.errors import (
    CustomerInputError,
    PetHealthConflictError,
    PetHealthRequiredError,
)
from customer.domain.services.pet_health import check_conditions
from customer.domain.value_objects.condition_entry import ConditionEntry

CODES = frozenset({"patella_luxation", "heart_disease", "other"})


def _entry(code, custom=None, note=None):
    return ConditionEntry(type_code=code, custom_label=custom, note=note)


def test_질병이_있거나_질병_없음을_확인했으면_통과한다():
    check_conditions((_entry("patella_luxation", note="2기"),), False, CODES)
    check_conditions((), True, CODES)


def test_둘_다_아니면_PET_HEALTH_REQUIRED_다():
    with pytest.raises(PetHealthRequiredError):
        check_conditions((), False, CODES)


def test_둘_다면_PET_HEALTH_CONFLICT_다():
    with pytest.raises(PetHealthConflictError):
        check_conditions((_entry("heart_disease"),), True, CODES)


def test_기타는_이름이_있어야_하고_여러_개일_수_있다():
    check_conditions((_entry("other", "눈물 자국"), _entry("other", "기침")), False, CODES)
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("other"),), False, CODES)


def test_정해진_질병에는_이름을_직접_넣지_않는다():
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("heart_disease", "심장"),), False, CODES)


def test_같은_정해진_질병을_두_번_넣을_수_없다():
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("heart_disease"), _entry("heart_disease")), False, CODES)


def test_모르는_종류는_VALIDATION_ERROR_다():
    with pytest.raises(CustomerInputError):
        check_conditions((_entry("flu"),), False, CODES)
```

`backend/apps/customer/tests/domain/test_profiles.py`:
```python
from datetime import date
from decimal import Decimal

import pytest

from customer.domain.errors import CustomerInputError, PetHealthRequiredError
from customer.domain.value_objects.customer_profile import CustomerProfile
from customer.domain.value_objects.pet_profile import PetProfile


def test_보호자_번호와_보조_연락처를_숫자만으로_바꾼다():
    profile = CustomerProfile.create(
        name="김민지", phone="010-1234-5678", phone_alt="02-123-4567",
        marketing_consent=True, memo=None,
    )
    assert (profile.phone, profile.phone_alt) == ("01012345678", "021234567")


def test_보조_연락처도_형식을_본다():
    with pytest.raises(CustomerInputError):
        CustomerProfile.create(name="김민지", phone="01012345678", phone_alt="123",
                               marketing_consent=False, memo=None)


def _pet(**overrides):
    fields = dict(
        name="콩이", species="dog", breed="말티즈", sex="female", neutered=True,
        birth_date=None, birth_year=2021, weight_kg=Decimal("3.2"), no_known_conditions=True,
        memo=None, conditions=(), known_condition_codes=frozenset({"other"}),
        today=date(2026, 9, 22),
    )
    fields.update(overrides)
    return PetProfile.create(**fields)


def test_반려동물은_나이와_질병_규칙을_둘_다_거친다():
    assert _pet().birth_year == 2021
    with pytest.raises(CustomerInputError):
        _pet(birth_date=date(2021, 1, 1))
    with pytest.raises(PetHealthRequiredError):
        _pet(no_known_conditions=False)
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/domain/test_pet_age.py apps/customer/tests/domain/test_pet_health.py apps/customer/tests/domain/test_profiles.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.domain.services.pet_age'`(와 `pet_health`, `customer_profile`)


- [ ] **Step 3: 구현한다**

`backend/apps/customer/domain/value_objects/condition_entry.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

OTHER = "other"   # 직접 입력하는 질병 종류 코드. pet_condition_types 시드에 있다.


@dataclass(frozen=True)
class ConditionEntry:
    """반려동물이 가진 질병 한 항목. 정해진 종류면 custom_label 이 없고, 기타면 있다."""

    type_code: str
    custom_label: str | None
    note: str | None
```

`backend/apps/customer/domain/services/pet_age.py`:
```python
"""반려동물 나이 — 생일·태어난 해·모름 중 하나만, 그리고 목록에 보여 줄 나이 표시."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from customer.domain.errors import CustomerInputError

_KST = timezone(timedelta(hours=9))   # 한국은 일광 절약 시간이 없다
_OLDEST_YEARS = 40


def seoul_today() -> date:
    """나이 계산의 '오늘'. 매장이 모두 한국에 있다(매장 시간대 기본값 Asia/Seoul)."""
    return datetime.now(_KST).date()


def check_birth(birth_date: date | None, birth_year: int | None, today: date) -> None:
    """생일과 태어난 해는 함께 보내지 않는다. 둘 다 없으면 '모름'이다."""
    if birth_date is not None and birth_year is not None:
        raise CustomerInputError("생일과 태어난 해 중 하나만 보내 주세요.")
    if birth_date is not None and not (today.year - _OLDEST_YEARS <= birth_date.year and birth_date <= today):
        raise CustomerInputError("생일이 올바르지 않습니다.")
    if birth_year is not None and not (today.year - _OLDEST_YEARS <= birth_year <= today.year):
        raise CustomerInputError("태어난 해가 올바르지 않습니다.")


def age_label(birth_date: date | None, birth_year: int | None, today: date) -> str:
    """생일이 있으면 만 나이(1살 전에는 개월), 태어난 해만 있으면 해의 차이, 없으면 '나이 모름'."""
    if birth_date is not None:
        months = (today.year - birth_date.year) * 12 + today.month - birth_date.month
        if today.day < birth_date.day:
            months -= 1
        return f"{months}개월" if months < 12 else f"{months // 12}살"
    if birth_year is not None:
        years = today.year - birth_year
        return "1살 미만" if years < 1 else f"{years}살"
    return "나이 모름"
```

`backend/apps/customer/domain/services/pet_health.py`:
```python
"""질병 규칙 — 질병이 있거나, '질병 없음'을 직접 확인했거나 둘 중 하나다.

두 표(pets.no_known_conditions 와 pet_conditions 행)에 걸친 규칙이라 CHECK 로 쓸 수 없어 여기서 확인한다.
"""
from __future__ import annotations

from customer.domain.errors import (
    CustomerInputError,
    PetHealthConflictError,
    PetHealthRequiredError,
)
from customer.domain.value_objects.condition_entry import OTHER, ConditionEntry


def check_conditions(
    conditions: tuple[ConditionEntry, ...], no_known_conditions: bool, known_codes: frozenset[str]
) -> None:
    if not conditions and not no_known_conditions:
        raise PetHealthRequiredError("질병을 고르거나 '질병 없음'을 눌러 주세요.")
    if conditions and no_known_conditions:
        raise PetHealthConflictError("질병을 고르면서 '질병 없음'을 함께 누를 수 없습니다.")
    seen: set[str] = set()
    for entry in conditions:
        if entry.type_code not in known_codes:
            raise CustomerInputError("알 수 없는 질병 종류입니다.")
        if (entry.type_code == OTHER) != (entry.custom_label is not None):
            raise CustomerInputError("'기타'일 때만 질병 이름을 직접 입력합니다.")
        if entry.type_code != OTHER:
            if entry.type_code in seen:
                raise CustomerInputError("같은 질병을 두 번 넣을 수 없습니다.")
            seen.add(entry.type_code)
```

`backend/apps/customer/domain/value_objects/customer_profile.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from customer.domain.services.phone_number import normalize_phone


@dataclass(frozen=True)
class CustomerProfile:
    """검증을 마친 보호자 정보. 전화번호는 숫자만이다."""

    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    memo: str | None

    @classmethod
    def create(
        cls, *, name: str, phone: str, phone_alt: str | None, marketing_consent: bool,
        memo: str | None,
    ) -> CustomerProfile:
        return cls(
            name=name,
            phone=normalize_phone(phone),
            phone_alt=normalize_phone(phone_alt) if phone_alt is not None else None,
            marketing_consent=marketing_consent,
            memo=memo,
        )
```

`backend/apps/customer/domain/value_objects/pet_profile.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from customer.domain.services.pet_age import check_birth
from customer.domain.services.pet_health import check_conditions
from customer.domain.value_objects.condition_entry import ConditionEntry


@dataclass(frozen=True)
class PetProfile:
    """검증을 마친 반려동물 정보. 나이 규칙과 질병 규칙을 통과했다."""

    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    weight_kg: Decimal
    no_known_conditions: bool
    memo: str | None
    conditions: tuple[ConditionEntry, ...]

    @classmethod
    def create(
        cls, *, name: str, species: str, breed: str, sex: str, neutered: bool,
        birth_date: date | None, birth_year: int | None, weight_kg: Decimal,
        no_known_conditions: bool, memo: str | None, conditions: tuple[ConditionEntry, ...],
        known_condition_codes: frozenset[str], today: date,
    ) -> PetProfile:
        check_birth(birth_date, birth_year, today)
        check_conditions(conditions, no_known_conditions, known_condition_codes)
        return cls(
            name=name, species=species, breed=breed, sex=sex, neutered=neutered,
            birth_date=birth_date, birth_year=birth_year, weight_kg=weight_kg,
            no_known_conditions=no_known_conditions, memo=memo, conditions=conditions,
        )
```



- [ ] **Step 4: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/domain/test_pet_age.py apps/customer/tests/domain/test_pet_health.py apps/customer/tests/domain/test_profiles.py -q -p no:cacheprovider`
Expected: `19 passed`


- [ ] **Step 5: 전체 단위 테스트와 구조 계약을 돌린다**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 단위 `340 passed`, `Contracts: 6 kept, 0 broken.`. 실패 0.


- [ ] **Step 6: 커밋**

```bash
git add backend/apps/customer/domain backend/apps/customer/tests/domain
git commit -m "feat(customer): 나이·질병 규칙과 검증된 입력 값 객체"
```

---

### Task 4: 마이그레이션 0005 — 표 다섯 개, 질병 종류 시드, `pg_trgm`

설계 6.1 의 표와 제약을 그대로 만든다. `shop_id`는 tenancy 의 ID 라 외래 키 없이 인덱스만, 스포크 안의 관계는 외래 키(`pet_conditions.pet_id`는 `ON DELETE CASCADE`). ID 는 설계대로 `bigint`다. 질병 종류는 시드 표라 테스트 사이에 비우면 안 된다(C20) — 루트 `conftest.py`의 `_KEEP_TABLES`에 더한다. 스키마 불일치 테스트가 ORM 과 마이그레이션을 대조한다(GIN `gin_trgm_ops` 색인과 부분 유일 색인까지 비교된다 — 확인함).

**Files:**
- Create: `backend/alembic/versions/0005_customer_tables_and_seed.py`
- Create: `backend/apps/customer/adapter/outbound/orm/customer_orm.py`
- Modify: `backend/orm_registry.py`
- Modify: `backend/conftest.py`
- Test: `backend/apps/customer/tests/adapter/test_customer_schema.py`

**Interfaces:**
- Consumes: `core.database.Base`
- Produces: `customer.adapter.outbound.orm.customer_orm`의 `CustomerOrm`(`customers`), `PetOrm`(`pets`), `PetConditionTypeOrm`(`pet_condition_types`), `PetConditionOrm`(`pet_conditions`), `CustomerSearchEntryOrm`(`customer_search_entries`). 제약 이름: `uq_customers_shop_phone_active`(Task 5 가 이 이름으로 409 를 가린다), `ck_customers_alive_has_name_phone`, `ck_pets_species`, `ck_pets_sex`, `ck_pets_weight_positive`, `ck_pets_one_birth_field`, `ck_pet_conditions_other_label`, `uq_pet_conditions_pet_type`, `ix_customer_search_entries_terms_trgm`·`_shop_activity`·`_shop_sort_name`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_customer_schema.py`:
```python
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.integration


async def test_질병_종류_시드가_설계_순서대로_들어_있다(db_session):
    rows = (
        await db_session.execute(
            text("SELECT code, label FROM pet_condition_types ORDER BY sort_order")
        )
    ).all()
    assert rows == [
        ("patella_luxation", "슬개골 탈구"), ("heart_disease", "심장 질환"),
        ("skin_disease", "피부병"), ("arthritis", "관절염"), ("allergy", "알레르기"),
        ("ear_disease", "귀 질환"), ("disc_disease", "디스크"), ("seizure", "발작·뇌전증"),
        ("diabetes", "당뇨"), ("other", "기타"),
    ]


async def test_pg_trgm_확장이_켜져_있다(db_session):
    installed = (
        await db_session.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
    ).scalar()
    assert installed == 1


async def _insert_customer(session, shop_id=1, phone="01012345678", deleted=False):
    row = await session.execute(
        text(
            "INSERT INTO customers (shop_id, name, phone, marketing_consent, "
            "marketing_consent_changed_at, deleted_at) "
            "VALUES (:shop, '김민지', :phone, false, now(), CASE WHEN :deleted THEN now() END) "
            "RETURNING id"
        ),
        {"shop": shop_id, "phone": phone, "deleted": deleted},
    )
    return row.scalar_one()


async def _violates(session, sql, **params) -> str:
    """제약 위반이 일어나는지 세이브포인트 안에서 보고, 걸린 제약 이름을 돌려준다."""
    with pytest.raises(IntegrityError) as caught:
        async with session.begin_nested():
            await session.execute(text(sql), params)
    return caught.value.orig.__cause__.constraint_name


async def test_살아_있는_고객의_번호는_매장_안에서_하나다(db_session):
    await _insert_customer(db_session)
    await _insert_customer(db_session, shop_id=2)                     # 다른 매장은 괜찮다
    await _insert_customer(db_session, deleted=True)                  # 익명화한 고객과는 겹쳐도 된다
    with pytest.raises(IntegrityError):
        async with db_session.begin_nested():
            await _insert_customer(db_session)


async def test_살아_있는_고객은_이름과_번호가_있어야_한다(db_session):
    name = await _violates(
        db_session,
        "INSERT INTO customers (shop_id, name, phone, marketing_consent, marketing_consent_changed_at) "
        "VALUES (1, NULL, '01012345678', false, now())",
    )
    assert name == "ck_customers_alive_has_name_phone"


async def test_반려동물_CHECK_제약(db_session):
    customer_id = await _insert_customer(db_session)
    base = (
        "INSERT INTO pets (customer_id, name, species, breed, sex, neutered, birth_date, birth_year, "
        "weight_kg, no_known_conditions) VALUES (:c, '콩이', :species, '말티즈', :sex, true, "
        ":birth_date, :birth_year, :weight, true)"
    )
    ok = dict(c=customer_id, species="dog", sex="female", birth_date=None, birth_year=None, weight=3.2)
    await db_session.execute(text(base), ok)   # 나이 모름은 된다
    from datetime import date

    cases = [
        ({"species": "bird"}, "ck_pets_species"),
        ({"sex": "unknown"}, "ck_pets_sex"),
        ({"weight": 0}, "ck_pets_weight_positive"),
        ({"birth_date": date(2020, 1, 1), "birth_year": 2020}, "ck_pets_one_birth_field"),
    ]
    for override, constraint in cases:
        assert await _violates(db_session, base, **{**ok, **override}) == constraint


async def test_질병_행_제약(db_session):
    customer_id = await _insert_customer(db_session)
    pet_id = (
        await db_session.execute(
            text(
                "INSERT INTO pets (customer_id, name, species, breed, sex, neutered, weight_kg, "
                "no_known_conditions) VALUES (:c, '콩이', 'dog', '말티즈', 'female', true, 3.2, false) "
                "RETURNING id"
            ),
            {"c": customer_id},
        )
    ).scalar_one()
    insert = "INSERT INTO pet_conditions (pet_id, type_code, custom_label) VALUES (:p, :code, :label)"
    await db_session.execute(text(insert), {"p": pet_id, "code": "other", "label": "기침"})
    await db_session.execute(text(insert), {"p": pet_id, "code": "other", "label": "눈물"})   # 기타는 여러 개
    await db_session.execute(text(insert), {"p": pet_id, "code": "allergy", "label": None})

    assert await _violates(db_session, insert, p=pet_id, code="allergy", label=None) == "uq_pet_conditions_pet_type"
    assert await _violates(db_session, insert, p=pet_id, code="other", label=None) == "ck_pet_conditions_other_label"
    assert await _violates(db_session, insert, p=pet_id, code="arthritis", label="관절") == "ck_pet_conditions_other_label"
```


- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_schema.py -q -p no:cacheprovider`
Expected: FAIL 6개 — 아직 표와 확장이 없다(`UndefinedTableError: relation "pet_condition_types" does not exist` 등).


- [ ] **Step 3: 마이그레이션과 ORM 을 쓴다**

`backend/alembic/versions/0005_customer_tables_and_seed.py`:
```python
"""고객·반려동물·질병·검색 표 + 질병 종류 시드 + pg_trgm

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-22
"""
import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "customers",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),  # tenancy 의 매장 ID — 스포크를 넘는 외래 키는 걸지 않는다
        sa.Column("name", sa.String(50)),
        sa.Column("phone", sa.String(11)),
        sa.Column("phone_alt", sa.String(11)),
        sa.Column("marketing_consent", sa.Boolean, nullable=False),
        sa.Column("marketing_consent_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("memo", sa.String(500)),
        *_timestamps(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "deleted_at IS NOT NULL OR (name IS NOT NULL AND phone IS NOT NULL)",
            name="ck_customers_alive_has_name_phone",
        ),
    )
    op.create_index("ix_customers_shop_id", "customers", ["shop_id"])
    op.create_index(
        "uq_customers_shop_phone_active", "customers", ["shop_id", "phone"],
        unique=True, postgresql_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "pets",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.String(50)),
        sa.Column("species", sa.String(10), nullable=False),
        sa.Column("breed", sa.String(50), nullable=False),
        sa.Column("sex", sa.String(10), nullable=False),
        sa.Column("neutered", sa.Boolean, nullable=False),
        sa.Column("birth_date", sa.Date),
        sa.Column("birth_year", sa.SmallInteger),
        sa.Column("weight_kg", sa.Numeric(4, 1), nullable=False),
        sa.Column("no_known_conditions", sa.Boolean, nullable=False),
        sa.Column("memo", sa.String(500)),
        sa.Column("passed_away_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint("species IN ('dog', 'cat')", name="ck_pets_species"),
        sa.CheckConstraint("sex IN ('female', 'male')", name="ck_pets_sex"),
        sa.CheckConstraint("weight_kg > 0", name="ck_pets_weight_positive"),
        sa.CheckConstraint("birth_date IS NULL OR birth_year IS NULL", name="ck_pets_one_birth_field"),
    )
    op.create_index("ix_pets_customer_id", "pets", ["customer_id"])

    condition_types = op.create_table(
        "pet_condition_types",
        sa.Column("code", sa.String(30), primary_key=True),
        sa.Column("label", sa.String(30), nullable=False),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
    )

    op.create_table(
        "pet_conditions",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("pet_id", sa.BigInteger, sa.ForeignKey("pets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type_code", sa.String(30), sa.ForeignKey("pet_condition_types.code"), nullable=False),
        sa.Column("custom_label", sa.String(30)),
        sa.Column("note", sa.String(100)),
        sa.CheckConstraint(
            "(type_code = 'other') = (custom_label IS NOT NULL)", name="ck_pet_conditions_other_label"
        ),
    )
    op.create_index("ix_pet_conditions_pet_id", "pet_conditions", ["pet_id"])
    op.create_index(
        "uq_pet_conditions_pet_type", "pet_conditions", ["pet_id", "type_code"],
        unique=True, postgresql_where=sa.text("type_code <> 'other'"),
    )

    op.create_table(
        "customer_search_entries",
        sa.Column("customer_id", sa.BigInteger, sa.ForeignKey("customers.id"), primary_key=True),
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("terms", sa.Text, nullable=False),
        sa.Column("phone_last4", sa.String(4), nullable=False),
        sa.Column("sort_name", sa.String(50), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_customer_search_entries_terms_trgm", "customer_search_entries", ["terms"],
        postgresql_using="gin", postgresql_ops={"terms": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_customer_search_entries_shop_activity", "customer_search_entries",
        ["shop_id", "last_activity_at"],
    )
    op.create_index(
        "ix_customer_search_entries_shop_sort_name", "customer_search_entries",
        ["shop_id", "sort_name"],
    )

    op.bulk_insert(
        condition_types,
        [
            {"code": "patella_luxation", "label": "슬개골 탈구", "sort_order": 1},
            {"code": "heart_disease", "label": "심장 질환", "sort_order": 2},
            {"code": "skin_disease", "label": "피부병", "sort_order": 3},
            {"code": "arthritis", "label": "관절염", "sort_order": 4},
            {"code": "allergy", "label": "알레르기", "sort_order": 5},
            {"code": "ear_disease", "label": "귀 질환", "sort_order": 6},
            {"code": "disc_disease", "label": "디스크", "sort_order": 7},
            {"code": "seizure", "label": "발작·뇌전증", "sort_order": 8},
            {"code": "diabetes", "label": "당뇨", "sort_order": 9},
            {"code": "other", "label": "기타", "sort_order": 10},
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_search_entries_shop_sort_name", table_name="customer_search_entries")
    op.drop_index("ix_customer_search_entries_shop_activity", table_name="customer_search_entries")
    op.drop_index("ix_customer_search_entries_terms_trgm", table_name="customer_search_entries")
    op.drop_table("customer_search_entries")
    op.drop_index("uq_pet_conditions_pet_type", table_name="pet_conditions")
    op.drop_index("ix_pet_conditions_pet_id", table_name="pet_conditions")
    op.drop_table("pet_conditions")
    op.drop_table("pet_condition_types")
    op.drop_index("ix_pets_customer_id", table_name="pets")
    op.drop_table("pets")
    op.drop_index("uq_customers_shop_phone_active", table_name="customers")
    op.drop_index("ix_customers_shop_id", table_name="customers")
    op.drop_table("customers")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
```

`backend/apps/customer/adapter/outbound/orm/customer_orm.py`:
```python
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class CustomerOrm(Base):
    __tablename__ = "customers"
    __table_args__ = (
        # 익명화한 고객의 행은 남는다. 번호가 유일해야 하는 것은 살아 있는 고객뿐이다.
        Index(
            "uq_customers_shop_phone_active", "shop_id", "phone",
            unique=True, postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "deleted_at IS NOT NULL OR (name IS NOT NULL AND phone IS NOT NULL)",
            name="ck_customers_alive_has_name_phone",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger, index=True)
    name: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(11))
    phone_alt: Mapped[str | None] = mapped_column(String(11))
    marketing_consent: Mapped[bool] = mapped_column(Boolean)
    marketing_consent_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    memo: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PetOrm(Base):
    __tablename__ = "pets"
    __table_args__ = (
        CheckConstraint("species IN ('dog', 'cat')", name="ck_pets_species"),
        CheckConstraint("sex IN ('female', 'male')", name="ck_pets_sex"),
        CheckConstraint("weight_kg > 0", name="ck_pets_weight_positive"),
        CheckConstraint("birth_date IS NULL OR birth_year IS NULL", name="ck_pets_one_birth_field"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 매장은 고객을 거쳐 안다. 여기에 shop_id 를 두지 않는다(이행 종속).
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(50))
    species: Mapped[str] = mapped_column(String(10))
    breed: Mapped[str] = mapped_column(String(50))
    sex: Mapped[str] = mapped_column(String(10))
    neutered: Mapped[bool] = mapped_column(Boolean)
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_year: Mapped[int | None] = mapped_column(SmallInteger)
    weight_kg: Mapped[Decimal] = mapped_column(Numeric(4, 1))
    no_known_conditions: Mapped[bool] = mapped_column(Boolean)
    memo: Mapped[str | None] = mapped_column(String(500))
    passed_away_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PetConditionTypeOrm(Base):
    """정해진 질병 종류. 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다."""

    __tablename__ = "pet_condition_types"

    code: Mapped[str] = mapped_column(String(30), primary_key=True)
    label: Mapped[str] = mapped_column(String(30))
    sort_order: Mapped[int] = mapped_column(SmallInteger)


class PetConditionOrm(Base):
    __tablename__ = "pet_conditions"
    __table_args__ = (
        # 같은 정해진 질병은 한 번만. 기타는 여러 개 넣을 수 있다.
        Index(
            "uq_pet_conditions_pet_type", "pet_id", "type_code",
            unique=True, postgresql_where=text("type_code <> 'other'"),
        ),
        CheckConstraint(
            "(type_code = 'other') = (custom_label IS NOT NULL)", name="ck_pet_conditions_other_label"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    pet_id: Mapped[int] = mapped_column(ForeignKey("pets.id", ondelete="CASCADE"), index=True)
    type_code: Mapped[str] = mapped_column(ForeignKey("pet_condition_types.code"))
    custom_label: Mapped[str | None] = mapped_column(String(30))
    note: Mapped[str | None] = mapped_column(String(100))


class CustomerSearchEntryOrm(Base):
    """검색용 역정규화 표(설계 6.4). 원본은 customers·pets 이고 언제든 다시 만들 수 있다."""

    __tablename__ = "customer_search_entries"
    __table_args__ = (
        Index(
            "ix_customer_search_entries_terms_trgm", "terms",
            postgresql_using="gin", postgresql_ops={"terms": "gin_trgm_ops"},
        ),
        Index("ix_customer_search_entries_shop_activity", "shop_id", "last_activity_at"),
        Index("ix_customer_search_entries_shop_sort_name", "shop_id", "sort_name"),
    )

    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), primary_key=True)
    shop_id: Mapped[int] = mapped_column(BigInteger)
    terms: Mapped[str] = mapped_column(Text)
    phone_last4: Mapped[str] = mapped_column(String(4))
    sort_name: Mapped[str] = mapped_column(String(50))
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
```


- [ ] **Step 4: ORM 을 등록하고 시드 표를 지키게 한다**

`backend/orm_registry.py`:
```diff
@@ -6,3 +6,4 @@ core 는 스포크를 import 할 수 없어서 core 밖에 둔다. 새 ORM 모
 import auth.adapter.outbound.orm.user_orm  # noqa: F401
 import auth.adapter.outbound.orm.operator_orm  # noqa: F401
 import tenancy.adapter.outbound.orm.tenancy_orm  # noqa: F401
+import customer.adapter.outbound.orm.customer_orm  # noqa: F401
```

`backend/conftest.py`:
```diff
@@ -7,8 +7,10 @@ from pathlib import Path
 
 import pytest
 
-# 마이그레이션이 넣은 시드(역할·권한)와 버전 표는 테스트 사이에 비우지 않는다.
-_KEEP_TABLES = {"alembic_version", "roles", "permissions", "role_permissions"}
+# 마이그레이션이 넣은 시드(역할·권한·질병 종류)와 버전 표는 테스트 사이에 비우지 않는다.
+_KEEP_TABLES = {
+    "alembic_version", "roles", "permissions", "role_permissions", "pet_condition_types",
+}
 
 
 @pytest.fixture(scope="session")
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_schema.py tests/test_schema_drift.py -q -p no:cacheprovider`
Expected: `7 passed` (스키마 6 + 불일치 검사 1)


- [ ] **Step 6: 테스트 DB 에서 되돌리기를 확인한다**

개발 DB 에서는 `downgrade`를 돌리지 않는다. 테스트 DB 에서만 한 번 내렸다 올린다.
```bash
docker compose run --rm backend sh -c 'U=${DATABASE_URL%/*}/chagocnote_test; alembic -x db_url=$U downgrade 0004 && alembic -x db_url=$U current && alembic -x db_url=$U upgrade head && alembic -x db_url=$U current'
```
Expected: 오류 없이 `0004` 다음 `0005 (head)`가 찍힌다. 테스트 DB 는 다음 통합 테스트가 어차피 처음부터 다시 만든다.


- [ ] **Step 7: 전체를 돌린다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `340 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `143 passed`. 실패 0.


- [ ] **Step 8: 커밋**

```bash
git add backend/alembic/versions/0005_customer_tables_and_seed.py backend/apps/customer/adapter/outbound/orm backend/apps/customer/tests/adapter/test_customer_schema.py backend/orm_registry.py backend/conftest.py
git commit -m "feat(customer): 마이그레이션 0005 — 고객·반려동물·질병·검색 표와 질병 종류 시드"
```

---

### Task 5: 엔티티와 리포지토리 — 고객·반려동물·질병 종류

살아 있는 고객만 엔티티로 읽는다(익명화한 고객은 어느 메서드에서도 없는 것으로 본다 — C6). 반려동물은 언제나 "이 매장의 살아 있는 고객" 부분 질의로 소속을 거른다(C1·C9). `lock_active`·`lock_owner`는 고객 행을 `FOR UPDATE`로 잠그고 `populate_existing`으로 다시 읽는다 — 잠금을 기다린 뒤에는 `deleted_at IS NULL`을 다시 평가해 익명화된 고객이 빠진다(C13·C14 의 바탕, 경합 테스트는 Task 15). 번호 유일 색인 위반은 세이브포인트 안에서 잡아 `CustomerPhoneTakenError`로 바꾼다(C2). 반려동물 추가는 넣은 뒤 `get(ctx)`로 다시 읽어 다른 매장 고객이면 404 로 요청째 되돌린다(C9).

**Files:**
- Create: `backend/apps/customer/domain/entities/customer.py`
- Create: `backend/apps/customer/domain/entities/pet.py`
- Create: `backend/apps/customer/domain/entities/condition_type.py`
- Create: `backend/apps/customer/app/ports/output/customer_repository.py`
- Create: `backend/apps/customer/app/ports/output/pet_repository.py`
- Create: `backend/apps/customer/app/ports/output/condition_type_repository.py`
- Create: `backend/apps/customer/adapter/outbound/mappers/customer_mapper.py`
- Create: `backend/apps/customer/adapter/outbound/pg/customer_pg_repository.py`
- Create: `backend/apps/customer/adapter/outbound/pg/pet_pg_repository.py`
- Create: `backend/apps/customer/adapter/outbound/pg/condition_type_pg_repository.py`
- Create: `backend/apps/customer/tests/helpers/profiles.py` (테스트 도우미)
- Test: `backend/apps/customer/tests/adapter/test_customer_pg_repository.py`
- Test: `backend/apps/customer/tests/adapter/test_pet_pg_repository.py`

**Interfaces:**
- Consumes: Task 3 의 `CustomerProfile`·`PetProfile`, Task 4 의 ORM, `hub.app.dtos.shop_context.ShopContext`
- Produces:
  - 엔티티: `Customer(id, shop_id, name, phone, phone_alt, marketing_consent, marketing_consent_changed_at, memo)`, `PetCondition(type_code, label, custom_label, note)`, `Pet(id, customer_id, name, species, breed, sex, neutered, birth_date, birth_year, weight_kg, no_known_conditions, memo, passed_away_at, conditions: tuple[PetCondition, ...])` + 속성 `has_conditions`·`passed_away`, `ConditionType(code, label, sort_order)`
  - `CustomerRepository`: `async find_active_by_phone(ctx, phone) -> Customer | None`, `async get_active(ctx, customer_id) -> Customer`, `async lock_active(ctx, customer_id) -> Customer`, `async list_active(ctx, customer_ids: list[int]) -> list[Customer]`, `async create(ctx, profile) -> Customer`, `async update(ctx, customer_id, profile, consent_changed: bool) -> Customer`, `async anonymize(ctx, customer_id) -> None`
  - `PetRepository`: `async get(ctx, pet_id) -> Pet`, `async lock_owner(ctx, pet_id) -> int`(고객 ID), `async list_for_customers(ctx, customer_ids) -> list[Pet]`, `async add(ctx, customer_id, profile) -> Pet`, `async update(ctx, pet_id, profile) -> Pet`, `async set_passed_away(ctx, pet_id, passed_away: bool) -> Pet`, `async count_for_customer(ctx, customer_id) -> int`, `async delete(ctx, pet_id) -> None`
  - `ConditionTypeRepository`: `async list_all() -> list[ConditionType]`
  - 구현: `CustomerPgRepository(session)`, `PetPgRepository(session)`, `ConditionTypePgRepository(session)`
  - 테스트 도우미 `customer.tests.helpers.profiles`: `ctx(shop_id=1, member_id=11, role="owner") -> ShopContext`, `customer_profile(**overrides)`, `pet_profile(**overrides)`, `condition(type_code, custom_label=None, note=None)`, `STAFF_PERMISSIONS`, `OWNER_PERMISSIONS`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/helpers/profiles.py`:
```python
"""customer 테스트가 함께 쓰는 값 — 매장 컨텍스트와 검증을 마친 보호자·반려동물 정보."""
from __future__ import annotations

from decimal import Decimal

from customer.domain.value_objects.condition_entry import ConditionEntry
from customer.domain.value_objects.customer_profile import CustomerProfile
from customer.domain.value_objects.pet_profile import PetProfile
from hub.app.dtos.shop_context import ShopContext

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
    {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}
)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "owner") -> ShopContext:
    permissions = OWNER_PERMISSIONS if role == "owner" else STAFF_PERMISSIONS
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=permissions)


def customer_profile(**overrides) -> CustomerProfile:
    fields = dict(name="김민지", phone="01012345678", phone_alt=None, marketing_consent=False,
                  memo=None)
    fields.update(overrides)
    return CustomerProfile(**fields)


def pet_profile(**overrides) -> PetProfile:
    fields = dict(
        name="콩이", species="dog", breed="말티즈", sex="female", neutered=True, birth_date=None,
        birth_year=2021, weight_kg=Decimal("3.2"), no_known_conditions=True, memo=None,
        conditions=(),
    )
    fields.update(overrides)
    return PetProfile(**fields)


def condition(type_code: str, custom_label: str | None = None, note: str | None = None) -> ConditionEntry:
    return ConditionEntry(type_code=type_code, custom_label=custom_label, note=note)
```

`backend/apps/customer/tests/adapter/test_customer_pg_repository.py`:
```python
import pytest
from sqlalchemy import text

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError
from customer.tests.helpers.profiles import condition, ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def test_등록한_고객을_컨텍스트의_매장에서만_읽는다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile(phone_alt="021234567", memo="오전 선호"))
    assert (created.shop_id, created.name, created.phone, created.phone_alt, created.memo) == (
        1, "김민지", "01012345678", "021234567", "오전 선호",
    )
    assert (await repo.get_active(A, created.id)).id == created.id
    with pytest.raises(CustomerNotFoundError):
        await repo.get_active(B, created.id)
    with pytest.raises(CustomerNotFoundError):
        await repo.lock_active(B, created.id)
    assert await repo.find_active_by_phone(B, "01012345678") is None
    assert await repo.list_active(B, [created.id]) == []


async def test_같은_매장의_살아_있는_번호는_CUSTOMER_PHONE_TAKEN_이다(db_session):
    repo = CustomerPgRepository(db_session)
    await repo.create(A, customer_profile())
    with pytest.raises(CustomerPhoneTakenError):
        await repo.create(A, customer_profile(name="다른 사람"))
    # 세이브포인트로 되돌렸으니 같은 트랜잭션을 계속 쓸 수 있다. 다른 매장은 같은 번호를 쓸 수 있다.
    assert (await repo.create(B, customer_profile())).shop_id == 2


async def test_번호를_바꾸다_겹치면_CUSTOMER_PHONE_TAKEN_이다(db_session):
    repo = CustomerPgRepository(db_session)
    first = await repo.create(A, customer_profile())
    second = await repo.create(A, customer_profile(phone="01099998888"))
    with pytest.raises(CustomerPhoneTakenError):
        await repo.update(A, second.id, customer_profile(phone=first.phone), consent_changed=False)
    assert (await repo.get_active(A, second.id)).phone == "01099998888"


async def test_동의가_바뀔_때만_동의_시각을_새로_찍는다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile())
    await db_session.execute(
        text("UPDATE customers SET marketing_consent_changed_at = now() - interval '1 day'")
    )
    kept = await repo.update(A, created.id, customer_profile(memo="메모"), consent_changed=False)
    changed = await repo.update(A, created.id, customer_profile(marketing_consent=True), consent_changed=True)
    assert kept.marketing_consent_changed_at < changed.marketing_consent_changed_at
    assert changed.marketing_consent is True


async def test_다른_매장의_고객은_고치지_못한다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile())
    with pytest.raises(CustomerNotFoundError):
        await repo.update(B, created.id, customer_profile(name="빼앗은 이름"), consent_changed=False)
    assert (await repo.get_active(A, created.id)).name == "김민지"


async def test_익명화는_개인정보만_지우고_틀을_남긴다(db_session):
    customers, pets = CustomerPgRepository(db_session), PetPgRepository(db_session)
    created = await customers.create(A, customer_profile(phone_alt="021234567", memo="메모"))
    await pets.add(A, created.id, pet_profile(memo="겁이 많음", no_known_conditions=False,
                                              conditions=(condition("allergy", note="닭고기"),)))
    await customers.anonymize(A, created.id)

    with pytest.raises(CustomerNotFoundError):
        await customers.get_active(A, created.id)
    row = (await db_session.execute(text(
        "SELECT name, phone, phone_alt, memo, deleted_at IS NOT NULL FROM customers"
    ))).one()
    assert tuple(row) == (None, None, None, None, True)
    pet = (await db_session.execute(text("SELECT name, memo, species, breed FROM pets"))).one()
    assert tuple(pet) == (None, None, "dog", "말티즈")
    assert (await db_session.execute(text("SELECT count(*) FROM pet_conditions"))).scalar_one() == 0
    # 익명화한 번호로 다시 등록하면 새 고객이다.
    again = await customers.create(A, customer_profile())
    assert again.id != created.id


async def test_다른_매장의_익명화는_아무것도_지우지_않는다(db_session):
    repo = CustomerPgRepository(db_session)
    created = await repo.create(A, customer_profile())
    await repo.anonymize(B, created.id)
    assert (await repo.get_active(A, created.id)).name == "김민지"
```

`backend/apps/customer/tests/adapter/test_pet_pg_repository.py`:
```python
from datetime import date
from decimal import Decimal

import pytest

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.profiles import condition, ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _family(session, shop=A, phone="01012345678"):
    customer = await CustomerPgRepository(session).create(shop, customer_profile(phone=phone))
    return customer.id


async def test_반려동물과_질병을_넣고_종류_순서대로_읽는다(db_session):
    repo = PetPgRepository(db_session)
    customer_id = await _family(db_session)
    pet = await repo.add(A, customer_id, pet_profile(
        birth_year=None, birth_date=date(2021, 3, 1), weight_kg=Decimal("12.5"),
        no_known_conditions=False,
        conditions=(condition("other", "눈물 자국"), condition("patella_luxation", note="2기")),
    ))
    assert (pet.name, pet.birth_date, pet.weight_kg, pet.has_conditions) == (
        "콩이", date(2021, 3, 1), Decimal("12.5"), True,
    )
    assert [(c.type_code, c.label, c.custom_label, c.note) for c in pet.conditions] == [
        ("patella_luxation", "슬개골 탈구", None, "2기"), ("other", "기타", "눈물 자국", None),
    ]


async def test_다른_매장에서는_반려동물이_없는_것과_같다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile())
    with pytest.raises(PetNotFoundError):
        await repo.get(B, pet.id)
    with pytest.raises(PetNotFoundError):
        await repo.lock_owner(B, pet.id)
    assert await repo.list_for_customers(B, [pet.customer_id]) == []
    assert await repo.count_for_customer(B, pet.customer_id) == 0
    await repo.delete(B, pet.id)
    with pytest.raises(PetNotFoundError):
        await repo.update(B, pet.id, pet_profile(name="빼앗은 이름"))
    with pytest.raises(PetNotFoundError):
        await repo.set_passed_away(B, pet.id, True)
    assert (await repo.get(A, pet.id)).name == "콩이"


async def test_다른_매장_고객에게_반려동물을_붙이면_404_다(db_session):
    repo = PetPgRepository(db_session)
    customer_id = await _family(db_session, shop=A)
    with pytest.raises(PetNotFoundError):
        await repo.add(B, customer_id, pet_profile())


async def test_수정은_질병_목록을_통째로_바꾼다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile(
        no_known_conditions=False, conditions=(condition("allergy"),),
    ))
    updated = await repo.update(A, pet.id, pet_profile(
        name="콩순이", no_known_conditions=False,
        conditions=(condition("heart_disease"), condition("allergy", note="닭고기")),
    ))
    assert updated.name == "콩순이"
    assert [(c.type_code, c.note) for c in updated.conditions] == [
        ("heart_disease", None), ("allergy", "닭고기"),
    ]
    cleared = await repo.update(A, pet.id, pet_profile(no_known_conditions=True, conditions=()))
    assert (cleared.conditions, cleared.no_known_conditions) == ((), True)


async def test_무지개다리는_처음_시각을_지키고_되돌릴_수_있다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile())
    first = await repo.set_passed_away(A, pet.id, True)
    again = await repo.set_passed_away(A, pet.id, True)
    assert first.passed_away and again.passed_away_at == first.passed_away_at
    assert (await repo.set_passed_away(A, pet.id, False)).passed_away is False


async def test_삭제하면_질병도_함께_지워지고_수를_센다(db_session):
    repo = PetPgRepository(db_session)
    customer_id = await _family(db_session)
    first = await repo.add(A, customer_id, pet_profile(no_known_conditions=False,
                                                       conditions=(condition("allergy"),)))
    await repo.add(A, customer_id, pet_profile(name="두부"))
    assert await repo.count_for_customer(A, customer_id) == 2
    await repo.delete(A, first.id)
    assert await repo.count_for_customer(A, customer_id) == 1
    assert [p.name for p in await repo.list_for_customers(A, [customer_id])] == ["두부"]


async def test_익명화한_고객의_반려동물은_없는_것과_같다(db_session):
    repo = PetPgRepository(db_session)
    pet = await repo.add(A, await _family(db_session), pet_profile())
    await CustomerPgRepository(db_session).anonymize(A, pet.customer_id)
    with pytest.raises(PetNotFoundError):
        await repo.get(A, pet.id)
    with pytest.raises(PetNotFoundError):
        await repo.lock_owner(A, pet.id)


async def test_질병_종류는_칩_순서대로다(db_session):
    types = await ConditionTypePgRepository(db_session).list_all()
    assert [t.code for t in types][:2] == ["patella_luxation", "heart_disease"]
    assert (types[-1].code, types[-1].label) == ("other", "기타")
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_pg_repository.py apps/customer/tests/adapter/test_pet_pg_repository.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.adapter.outbound.pg.customer_pg_repository'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/domain/entities/customer.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Customer:
    """살아 있는(익명화하지 않은) 보호자. 익명화한 고객은 엔티티로 읽지 않는다 — 없는 것으로 본다."""

    id: int
    shop_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None
```

`backend/apps/customer/domain/entities/pet.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class PetCondition:
    """반려동물이 가진 질병 한 항목. label 은 정해진 종류의 이름이다(기타면 '기타')."""

    type_code: str
    label: str
    custom_label: str | None
    note: str | None


@dataclass(frozen=True)
class Pet:
    id: int
    customer_id: int
    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    weight_kg: Decimal
    no_known_conditions: bool
    memo: str | None
    passed_away_at: datetime | None
    conditions: tuple[PetCondition, ...]

    @property
    def has_conditions(self) -> bool:
        return bool(self.conditions)

    @property
    def passed_away(self) -> bool:
        return self.passed_away_at is not None
```

`backend/apps/customer/domain/entities/condition_type.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConditionType:
    code: str
    label: str
    sort_order: int
```

`backend/apps/customer/app/ports/output/customer_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.domain.entities.customer import Customer
from customer.domain.value_objects.customer_profile import CustomerProfile
from hub.app.dtos.shop_context import ShopContext


class CustomerRepository(ABC):
    """살아 있는 고객만 다룬다. 익명화한 고객은 어느 메서드에서도 없는 것으로 본다."""

    @abstractmethod
    async def find_active_by_phone(self, ctx: ShopContext, phone: str) -> Customer | None: ...

    @abstractmethod
    async def get_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        """없거나 다른 매장이거나 익명화했으면 CustomerNotFoundError."""

    @abstractmethod
    async def lock_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        """고객 행을 FOR UPDATE 로 잠그고 다시 읽는다. 가족(고객·반려동물·질병)을 바꾸는 유스케이스는 맨 앞에서 부른다."""

    @abstractmethod
    async def list_active(self, ctx: ShopContext, customer_ids: list[int]) -> list[Customer]: ...

    @abstractmethod
    async def create(self, ctx: ShopContext, profile: CustomerProfile) -> Customer:
        """번호가 살아 있는 다른 고객과 겹치면 CustomerPhoneTakenError."""

    @abstractmethod
    async def update(
        self, ctx: ShopContext, customer_id: int, profile: CustomerProfile, consent_changed: bool
    ) -> Customer:
        """consent_changed 일 때만 동의 시각을 새로 찍는다. 번호가 겹치면 CustomerPhoneTakenError."""

    @abstractmethod
    async def anonymize(self, ctx: ShopContext, customer_id: int) -> None:
        """개인정보를 지운다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행. 행과 틀은 남긴다."""
```

`backend/apps/customer/app/ports/output/pet_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.domain.entities.pet import Pet
from customer.domain.value_objects.pet_profile import PetProfile
from hub.app.dtos.shop_context import ShopContext


class PetRepository(ABC):
    """반려동물은 고객을 거쳐 매장에 속한다. 모든 메서드가 반려동물 → 고객(살아 있음) → 매장 순서로 소속을 거른다."""

    @abstractmethod
    async def get(self, ctx: ShopContext, pet_id: int) -> Pet:
        """없거나 다른 매장이거나 보호자가 익명화됐으면 PetNotFoundError."""

    @abstractmethod
    async def lock_owner(self, ctx: ShopContext, pet_id: int) -> int:
        """반려동물의 고객 행을 FOR UPDATE 로 잠그고 고객 ID 를 돌려준다. 소속이 아니면 PetNotFoundError."""

    @abstractmethod
    async def list_for_customers(self, ctx: ShopContext, customer_ids: list[int]) -> list[Pet]:
        """고객별로 등록 순서대로."""

    @abstractmethod
    async def add(self, ctx: ShopContext, customer_id: int, profile: PetProfile) -> Pet: ...

    @abstractmethod
    async def update(self, ctx: ShopContext, pet_id: int, profile: PetProfile) -> Pet:
        """질병 목록은 통째로 바꾼다."""

    @abstractmethod
    async def set_passed_away(self, ctx: ShopContext, pet_id: int, passed_away: bool) -> Pet: ...

    @abstractmethod
    async def count_for_customer(self, ctx: ShopContext, customer_id: int) -> int: ...

    @abstractmethod
    async def delete(self, ctx: ShopContext, pet_id: int) -> None:
        """행을 지운다. 질병 행은 외래 키의 ON DELETE CASCADE 로 함께 지워진다."""
```

`backend/apps/customer/app/ports/output/condition_type_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.domain.entities.condition_type import ConditionType


class ConditionTypeRepository(ABC):
    """정해진 질병 종류(마이그레이션 시드). 매장과 상관없는 표라 ShopContext 를 받지 않는다."""

    @abstractmethod
    async def list_all(self) -> list[ConditionType]:
        """칩 순서(sort_order)대로."""
```

`backend/apps/customer/adapter/outbound/mappers/customer_mapper.py`:
```python
from __future__ import annotations

from customer.adapter.outbound.orm.customer_orm import CustomerOrm, PetOrm
from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet, PetCondition


def to_customer(orm: CustomerOrm) -> Customer:
    """살아 있는 고객만 넘긴다 — 이름과 번호가 있다(CHECK 제약)."""
    return Customer(
        id=orm.id,
        shop_id=orm.shop_id,
        name=orm.name,
        phone=orm.phone,
        phone_alt=orm.phone_alt,
        marketing_consent=orm.marketing_consent,
        marketing_consent_changed_at=orm.marketing_consent_changed_at,
        memo=orm.memo,
    )


def to_pet(orm: PetOrm, conditions: list[PetCondition]) -> Pet:
    """살아 있는 고객의 반려동물만 넘긴다 — 이름이 있다."""
    return Pet(
        id=orm.id,
        customer_id=orm.customer_id,
        name=orm.name,
        species=orm.species,
        breed=orm.breed,
        sex=orm.sex,
        neutered=orm.neutered,
        birth_date=orm.birth_date,
        birth_year=orm.birth_year,
        weight_kg=orm.weight_kg,
        no_known_conditions=orm.no_known_conditions,
        memo=orm.memo,
        passed_away_at=orm.passed_away_at,
        conditions=tuple(conditions),
    )
```

`backend/apps/customer/adapter/outbound/pg/customer_pg_repository.py`:
```python
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.mappers.customer_mapper import to_customer
from customer.adapter.outbound.orm.customer_orm import CustomerOrm, PetConditionOrm, PetOrm
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.domain.entities.customer import Customer
from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError
from customer.domain.value_objects.customer_profile import CustomerProfile
from hub.app.dtos.shop_context import ShopContext

_PHONE_UNIQUE = "uq_customers_shop_phone_active"


class CustomerPgRepository(CustomerRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _active(self, ctx: ShopContext):
        return select(CustomerOrm).where(
            CustomerOrm.shop_id == ctx.shop_id, CustomerOrm.deleted_at.is_(None)
        )

    async def find_active_by_phone(self, ctx: ShopContext, phone: str) -> Customer | None:
        row = (
            await self._session.execute(self._active(ctx).where(CustomerOrm.phone == phone))
        ).scalar_one_or_none()
        return to_customer(row) if row else None

    async def get_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        return to_customer(await self._row(ctx, customer_id, lock=False))

    async def lock_active(self, ctx: ShopContext, customer_id: int) -> Customer:
        return to_customer(await self._row(ctx, customer_id, lock=True))

    async def list_active(self, ctx: ShopContext, customer_ids: list[int]) -> list[Customer]:
        rows = (
            await self._session.execute(self._active(ctx).where(CustomerOrm.id.in_(customer_ids)))
        ).scalars()
        return [to_customer(row) for row in rows]

    async def create(self, ctx: ShopContext, profile: CustomerProfile) -> Customer:
        row = CustomerOrm(
            shop_id=ctx.shop_id,
            name=profile.name,
            phone=profile.phone,
            phone_alt=profile.phone_alt,
            marketing_consent=profile.marketing_consent,
            marketing_consent_changed_at=func.now(),
            memo=profile.memo,
        )
        async with self._phone_guard():
            self._session.add(row)
            await self._session.flush()
        return to_customer(await self._row(ctx, row.id, lock=False))

    async def update(
        self, ctx: ShopContext, customer_id: int, profile: CustomerProfile, consent_changed: bool
    ) -> Customer:
        values = dict(
            name=profile.name,
            phone=profile.phone,
            phone_alt=profile.phone_alt,
            marketing_consent=profile.marketing_consent,
            memo=profile.memo,
            updated_at=func.now(),   # 값이 같아도 '수정'은 최근 활동이다(최근순 정렬)
        )
        if consent_changed:
            values["marketing_consent_changed_at"] = func.now()
        async with self._phone_guard():
            await self._session.execute(
                update(CustomerOrm)
                .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id,
                       CustomerOrm.deleted_at.is_(None))
                .values(**values)
            )
        return to_customer(await self._row(ctx, customer_id, lock=False))

    async def anonymize(self, ctx: ShopContext, customer_id: int) -> None:
        await self._session.execute(
            update(CustomerOrm)
            .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id,
                   CustomerOrm.deleted_at.is_(None))
            .values(name=None, phone=None, phone_alt=None, memo=None, deleted_at=func.now())
        )
        await self._session.execute(
            delete(PetConditionOrm).where(
                PetConditionOrm.pet_id.in_(select(PetOrm.id).where(PetOrm.customer_id == customer_id))
            )
        )
        await self._session.execute(
            update(PetOrm).where(PetOrm.customer_id == customer_id).values(name=None, memo=None)
        )

    async def _row(self, ctx: ShopContext, customer_id: int, lock: bool) -> CustomerOrm:
        # 잠근 뒤 다시 읽을 때 세션에 남은 옛 값을 보지 않는다.
        stmt = self._active(ctx).where(CustomerOrm.id == customer_id).execution_options(
            populate_existing=True
        )
        if lock:
            stmt = stmt.with_for_update()
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise CustomerNotFoundError("고객을 찾을 수 없습니다.")
        return row

    @asynccontextmanager
    async def _phone_guard(self):
        """번호 유일 색인 위반을 CUSTOMER_PHONE_TAKEN 으로 바꾼다. 세이브포인트라 트랜잭션은 계속 쓸 수 있다.

        같은 번호를 동시에 넣는 두 요청 중 늦은 쪽은 앞선 쪽이 커밋할 때까지 색인에서 기다렸다가 여기서 걸린다.
        """
        try:
            async with self._session.begin_nested():
                yield
        except IntegrityError as exc:
            self._raise_if_phone_taken(exc)
            raise

    @staticmethod
    def _raise_if_phone_taken(exc: IntegrityError) -> None:
        if getattr(exc.orig.__cause__, "constraint_name", None) == _PHONE_UNIQUE:
            raise CustomerPhoneTakenError("이미 등록된 전화번호입니다.") from exc
```

`backend/apps/customer/adapter/outbound/pg/pet_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import delete, func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.mappers.customer_mapper import to_pet
from customer.adapter.outbound.orm.customer_orm import (
    CustomerOrm,
    PetConditionOrm,
    PetConditionTypeOrm,
    PetOrm,
)
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.entities.pet import Pet, PetCondition
from customer.domain.errors import PetNotFoundError
from customer.domain.value_objects.pet_profile import PetProfile
from hub.app.dtos.shop_context import ShopContext


def _owner_ids(ctx: ShopContext):
    """이 매장의 살아 있는 고객 ID. 반려동물의 소속은 언제나 이것으로 거른다."""
    return select(CustomerOrm.id).where(
        CustomerOrm.shop_id == ctx.shop_id, CustomerOrm.deleted_at.is_(None)
    )


def _profile_values(profile: PetProfile) -> dict:
    return dict(
        name=profile.name, species=profile.species, breed=profile.breed, sex=profile.sex,
        neutered=profile.neutered, birth_date=profile.birth_date, birth_year=profile.birth_year,
        weight_kg=profile.weight_kg, no_known_conditions=profile.no_known_conditions,
        memo=profile.memo,
    )


class PetPgRepository(PetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _owned(self, ctx: ShopContext):
        return select(PetOrm).where(PetOrm.customer_id.in_(_owner_ids(ctx)))

    async def get(self, ctx: ShopContext, pet_id: int) -> Pet:
        row = (
            await self._session.execute(
                self._owned(ctx).where(PetOrm.id == pet_id).execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        conditions = await self._conditions([row.id])
        return to_pet(row, conditions.get(row.id, []))

    async def lock_owner(self, ctx: ShopContext, pet_id: int) -> int:
        # 잠금을 기다리는 사이 고객이 익명화되면, 풀려난 뒤 WHERE 를 다시 평가해 행이 빠진다 → 404.
        customer_id = (
            await self._session.execute(
                select(CustomerOrm.id)
                .join(PetOrm, PetOrm.customer_id == CustomerOrm.id)
                .where(PetOrm.id == pet_id, CustomerOrm.shop_id == ctx.shop_id,
                       CustomerOrm.deleted_at.is_(None))
                .with_for_update(of=CustomerOrm)
            )
        ).scalar_one_or_none()
        if customer_id is None:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        return customer_id

    async def list_for_customers(self, ctx: ShopContext, customer_ids: list[int]) -> list[Pet]:
        rows = (
            await self._session.execute(
                self._owned(ctx)
                .where(PetOrm.customer_id.in_(customer_ids))
                .order_by(PetOrm.customer_id, PetOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        conditions = await self._conditions([row.id for row in rows])
        return [to_pet(row, conditions.get(row.id, [])) for row in rows]

    async def add(self, ctx: ShopContext, customer_id: int, profile: PetProfile) -> Pet:
        pet_id = (
            await self._session.execute(
                insert(PetOrm)
                .values(customer_id=customer_id, **_profile_values(profile))
                .returning(PetOrm.id)
            )
        ).scalar_one()
        await self._insert_conditions(pet_id, profile)
        return await self.get(ctx, pet_id)   # 다른 매장의 고객이면 여기서 404 가 되고 요청째 되돌린다

    async def update(self, ctx: ShopContext, pet_id: int, profile: PetProfile) -> Pet:
        await self._session.execute(
            update(PetOrm)
            .where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
            .values(**_profile_values(profile), updated_at=func.now())
        )
        await self._session.execute(delete(PetConditionOrm).where(PetConditionOrm.pet_id == pet_id))
        await self._insert_conditions(pet_id, profile)
        return await self.get(ctx, pet_id)

    async def set_passed_away(self, ctx: ShopContext, pet_id: int, passed_away: bool) -> Pet:
        # 이미 무지개다리면 처음 시각을 지킨다.
        stamp = func.coalesce(PetOrm.passed_away_at, func.now()) if passed_away else None
        await self._session.execute(
            update(PetOrm)
            .where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
            .values(passed_away_at=stamp, updated_at=func.now())
        )
        return await self.get(ctx, pet_id)

    async def count_for_customer(self, ctx: ShopContext, customer_id: int) -> int:
        return (
            await self._session.execute(
                select(func.count())
                .select_from(PetOrm)
                .where(PetOrm.customer_id == customer_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
            )
        ).scalar_one()

    async def delete(self, ctx: ShopContext, pet_id: int) -> None:
        await self._session.execute(
            delete(PetOrm).where(PetOrm.id == pet_id, PetOrm.customer_id.in_(_owner_ids(ctx)))
        )

    async def _insert_conditions(self, pet_id: int, profile: PetProfile) -> None:
        if profile.conditions:
            await self._session.execute(
                insert(PetConditionOrm),
                [
                    dict(pet_id=pet_id, type_code=c.type_code, custom_label=c.custom_label, note=c.note)
                    for c in profile.conditions
                ],
            )

    async def _conditions(self, pet_ids: list[int]) -> dict[int, list[PetCondition]]:
        rows = (
            await self._session.execute(
                select(PetConditionOrm, PetConditionTypeOrm.label)
                .join(PetConditionTypeOrm, PetConditionTypeOrm.code == PetConditionOrm.type_code)
                .where(PetConditionOrm.pet_id.in_(pet_ids))
                .order_by(PetConditionTypeOrm.sort_order, PetConditionOrm.id)
            )
        ).all()
        found: dict[int, list[PetCondition]] = {}
        for row, label in rows:
            found.setdefault(row.pet_id, []).append(
                PetCondition(type_code=row.type_code, label=label,
                             custom_label=row.custom_label, note=row.note)
            )
        return found
```

`backend/apps/customer/adapter/outbound/pg/condition_type_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.customer_orm import PetConditionTypeOrm
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.domain.entities.condition_type import ConditionType


class ConditionTypePgRepository(ConditionTypeRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_all(self) -> list[ConditionType]:
        rows = (
            await self._session.execute(
                select(PetConditionTypeOrm).order_by(PetConditionTypeOrm.sort_order)
            )
        ).scalars()
        return [ConditionType(code=r.code, label=r.label, sort_order=r.sort_order) for r in rows]
```



- [ ] **Step 4: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_pg_repository.py apps/customer/tests/adapter/test_pet_pg_repository.py -q -p no:cacheprovider`
Expected: `15 passed`


- [ ] **Step 5: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `340 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `158 passed`. 실패 0.


- [ ] **Step 6: 커밋**

```bash
git add backend/apps/customer/domain/entities backend/apps/customer/app/ports/output backend/apps/customer/adapter/outbound backend/apps/customer/tests
git commit -m "feat(customer): 고객·반려동물·질병 종류 리포지토리"
```

---

### Task 6: 검색 포트와 PostgreSQL 검색 어댑터

`CustomerSearchPort`는 검색 줄을 원본에서 다시 만들고(`rebuild_search_entry` — "이 계획에서 새로 정한 것" 3번), 가족 ID 를 정렬·커서로 찾고(한 쪽 30 가족), 반려동물 수를 센다. 검색 줄에는 보호자·반려동물 이름과 초성, 전화 숫자가 들어간다(보조 연락처 제외). 뒷자리는 `phone_last4 LIKE '56%'`, 그 밖은 `terms ILIKE '%…%'`이고 모든 낱말이 맞아야 한다. LIKE 특수 문자는 이스케이프한다(C10). 기본은 살아 있는 반려동물이 한 마리라도 있는 가족만이다. 커서는 `[정렬, 키, 고객 ID]`를 base64 로 싼 불투명 문자열이고 틀리면 422(C19). 최근순 키는 원본의 `updated_at` 가운데 가장 늦은 값이라 검색 줄은 언제든 원본에서 똑같이 다시 만들 수 있다.

**Files:**
- Create: `backend/apps/customer/app/dtos/customer_search_dto.py`
- Create: `backend/apps/customer/app/ports/output/customer_search_port.py`
- Create: `backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py`
- Test: `backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py`

**Interfaces:**
- Consumes: Task 2 의 `build_search_entry`·`parse_query`·`SearchWord`, Task 4 의 ORM, Task 5 의 리포지토리(테스트에서 가족을 만든다)
- Produces:
  - `customer.app.dtos.customer_search_dto`: `SortKey = Literal["recent", "name"]`, `PAGE_SIZE = 30`, `SearchRequest(words: tuple[SearchWord, ...], sort: SortKey, include_passed: bool, cursor: str | None, limit: int = 30)`, `SearchPage(customer_ids: list[int], next_cursor: str | None)`
  - `CustomerSearchPort`: `async rebuild_search_entry(ctx, customer_id) -> None`, `async search(ctx, request: SearchRequest) -> SearchPage`, `async count_pets(ctx, words, include_passed: bool) -> int`
  - 구현: `CustomerSearchPgAdapter(session)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py`:
```python
import pytest
from sqlalchemy import text

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.customer_search_dto import SearchRequest
from customer.domain.errors import CustomerInputError
from customer.domain.services.search_terms import parse_query
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _family(session, name, phone, pets, shop=A):
    """가족 하나를 넣고 검색 줄을 만든다. 유스케이스가 하는 순서 그대로다."""
    customer = await CustomerPgRepository(session).create(shop, customer_profile(name=name, phone=phone))
    for pet_name in pets:
        await PetPgRepository(session).add(shop, customer.id, pet_profile(name=pet_name))
    await CustomerSearchPgAdapter(session).rebuild_search_entry(shop, customer.id)
    return customer.id


async def _find(session, q, shop=A, sort="recent", include_passed=False, cursor=None, limit=30):
    page = await CustomerSearchPgAdapter(session).search(
        shop, SearchRequest(words=parse_query(q), sort=sort, include_passed=include_passed,
                            cursor=cursor, limit=limit),
    )
    return page


async def _ids(session, q, **kwargs):
    return (await _find(session, q, **kwargs)).customer_ids


async def test_검색_줄은_원본에서_만든다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이", "두부"])
    row = (await db_session.execute(text(
        "SELECT shop_id, terms, phone_last4, sort_name FROM customer_search_entries WHERE customer_id = :id"
    ), {"id": customer_id})).one()
    assert tuple(row) == (1, "김민지 ㄱㅁㅈ 콩이 ㅋㅇ 두부 ㄷㅂ 01012345678", "5678", "김민지")


async def test_뒷자리가_같은_가족을_모두_찾는다(db_session):
    first = await _family(db_session, "김민지", "01012345678", ["콩이"])
    second = await _family(db_session, "박서준", "01098765678", ["보리"])
    await _family(db_session, "이하나", "01011112222", ["구름"])
    assert set(await _ids(db_session, "5678")) == {first, second}
    assert set(await _ids(db_session, "56")) == {first, second}   # 뒷자리를 앞에서부터 치는 중
    assert await _ids(db_session, "1234-5678") == [first]          # 다섯 자리 이상은 전체 번호 부분 일치


async def test_이름_초성_여러_낱말로_찾는다(db_session):
    kong = await _family(db_session, "김민지", "01012345678", ["콩이", "두부"])
    await _family(db_session, "박서준", "01098765678", ["콩떡"])
    assert await _ids(db_session, "두부") == [kong]
    assert await _ids(db_session, "ㄱㅁㅈ") == [kong]
    assert await _ids(db_session, "ㅋㅇ") == [kong]
    assert await _ids(db_session, "5678 콩이") == [kong]      # 모든 낱말이 걸려야 한다
    assert await _ids(db_session, "민지 ㄷㅂ") == [kong]
    assert await _ids(db_session, "5678 없는이름") == []


async def test_LIKE_특수_문자는_글자_그대로_찾는다(db_session):
    percent = await _family(db_session, "100%보호자", "01012345678", ["콩이"])
    await _family(db_session, "김민지", "01098765678", ["두부"])
    under = await _family(db_session, "a_b", "01011112222", ["보리"])
    assert await _ids(db_session, "%") == [percent]
    assert await _ids(db_session, "_") == [under]
    assert await _ids(db_session, "\\") == []


async def test_다른_매장의_가족은_찾지_않는다(db_session):
    await _family(db_session, "김민지", "01012345678", ["콩이"], shop=B)
    assert await _ids(db_session, "콩이") == []
    assert await _ids(db_session, "") == []


async def test_익명화하면_검색_줄이_지워진다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    await CustomerPgRepository(db_session).anonymize(A, customer_id)
    await CustomerSearchPgAdapter(db_session).rebuild_search_entry(A, customer_id)
    assert (await db_session.execute(text("SELECT count(*) FROM customer_search_entries"))).scalar_one() == 0


async def test_다른_매장_컨텍스트로는_검색_줄을_지우지도_만들지도_못한다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    await CustomerSearchPgAdapter(db_session).rebuild_search_entry(B, customer_id)
    assert await _ids(db_session, "콩이") == [customer_id]


async def test_반려동물이_모두_무지개다리인_가족은_기본에서_빠진다(db_session):
    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
    pet_id = (await PetPgRepository(db_session).list_for_customers(A, [customer_id]))[0].id
    await PetPgRepository(db_session).set_passed_away(A, pet_id, True)
    assert await _ids(db_session, "") == []
    assert await _ids(db_session, "", include_passed=True) == [customer_id]


async def test_반려동물_수는_검색과_무지개다리를_따른다(db_session):
    adapter = CustomerSearchPgAdapter(db_session)
    kong = await _family(db_session, "김민지", "01012345678", ["콩이", "두부"])
    await _family(db_session, "박서준", "01098765678", ["보리"])
    dubu = (await PetPgRepository(db_session).list_for_customers(A, [kong]))[1].id
    await PetPgRepository(db_session).set_passed_away(A, dubu, True)
    assert await adapter.count_pets(A, parse_query(""), include_passed=False) == 2
    assert await adapter.count_pets(A, parse_query(""), include_passed=True) == 3
    assert await adapter.count_pets(A, parse_query("5678 콩"), include_passed=False) == 1   # 콩이만 (두부는 무지개다리)
    assert await adapter.count_pets(B, parse_query(""), include_passed=True) == 0


async def test_가나다순과_최근순으로_커서를_따라_끝까지_읽는다(db_session):
    names = ["다현", "가은", "나래", "라희", "마루"]
    ids = {}
    for index, name in enumerate(names):
        ids[name] = await _family(db_session, name, f"0101234{index:04d}", ["콩이"])
        await db_session.execute(text(
            "UPDATE customer_search_entries SET last_activity_at = now() - make_interval(mins => :m) "
            "WHERE customer_id = :id"
        ), {"m": 10 - index, "id": ids[name]})

    async def read_all(sort):
        seen, cursor = [], None
        while True:
            page = await _find(db_session, "", sort=sort, cursor=cursor, limit=2)
            seen += page.customer_ids
            if page.next_cursor is None:
                return seen
            cursor = page.next_cursor

    assert await read_all("name") == [ids[n] for n in ["가은", "나래", "다현", "라희", "마루"]]
    assert await read_all("recent") == [ids[n] for n in reversed(names)]


async def test_같은_정렬_값이면_ID_로_이어서_빠지거나_겹치지_않는다(db_session):
    ids = [await _family(db_session, "같은이름", f"0101234{i:04d}", ["콩이"]) for i in range(3)]
    first = await _find(db_session, "", sort="name", limit=2)
    second = await _find(db_session, "", sort="name", cursor=first.next_cursor, limit=2)
    assert first.customer_ids + second.customer_ids == ids
    assert second.next_cursor is None


@pytest.mark.parametrize("cursor", ["", "not-base64!", "WzEsMiwzXQ", "eyJhIjoxfQ"])
async def test_엉터리_커서는_VALIDATION_ERROR_다(db_session, cursor):
    with pytest.raises(CustomerInputError):
        await _find(db_session, "", sort="name", cursor=cursor)


async def test_다른_정렬의_커서는_VALIDATION_ERROR_다(db_session):
    for i in range(3):
        await _family(db_session, f"이름{i}", f"0101234{i:04d}", ["콩이"])
    recent = await _find(db_session, "", sort="recent", limit=1)
    with pytest.raises(CustomerInputError):
        await _find(db_session, "", sort="name", cursor=recent.next_cursor)
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_search_pg_adapter.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.adapter.outbound.pg.customer_search_pg_adapter'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/customer_search_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from customer.domain.services.search_terms import SearchWord

SortKey = Literal["recent", "name"]
PAGE_SIZE = 30


@dataclass(frozen=True)
class SearchRequest:
    words: tuple[SearchWord, ...]
    sort: SortKey
    include_passed: bool
    cursor: str | None
    limit: int = PAGE_SIZE


@dataclass(frozen=True)
class SearchPage:
    """찾은 가족(고객 ID)을 정렬 순서대로. 다음 쪽이 없으면 next_cursor 는 None."""

    customer_ids: list[int]
    next_cursor: str | None
```

`backend/apps/customer/app/ports/output/customer_search_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_search_dto import SearchPage, SearchRequest
from customer.domain.services.search_terms import SearchWord
from hub.app.dtos.shop_context import ShopContext


class CustomerSearchPort(ABC):
    """가족 단위 검색. 지금 구현은 PostgreSQL(pg_trgm)이고, 전용 검색 엔진으로 바꿀 때 어댑터만 교체한다.

    검색 결과는 고객 ID 뿐이다. 화면에 보여 줄 보호자·반려동물 정보는 원본 표에서 읽는다.
    """

    @abstractmethod
    async def rebuild_search_entry(self, ctx: ShopContext, customer_id: int) -> None:
        """그 가족의 검색 줄을 원본에서 다시 만든다. 고객이 익명화됐거나 없으면 줄을 지운다.

        가족(고객·반려동물·질병)을 바꾸는 모든 유스케이스가 같은 트랜잭션 안에서 부른다.
        """

    @abstractmethod
    async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
        """커서가 올바르지 않으면 CustomerInputError."""

    @abstractmethod
    async def count_pets(
        self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool
    ) -> int:
        """검색에 걸린 가족들의 반려동물 수(목록 제목의 'N마리'). 쪽과 상관없이 전체를 센다."""
```

`backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py`:
```python
from __future__ import annotations

import base64
import binascii
import json
from datetime import datetime

from sqlalchemy import delete, exists, func, select, tuple_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from customer.adapter.outbound.orm.customer_orm import CustomerOrm, CustomerSearchEntryOrm, PetOrm
from customer.app.dtos.customer_search_dto import SearchPage, SearchRequest, SortKey
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.domain.errors import CustomerInputError
from customer.domain.services.search_terms import SearchWord, build_search_entry
from hub.app.dtos.shop_context import ShopContext

Entry = CustomerSearchEntryOrm


def _like_escape(value: str) -> str:
    """LIKE 의 특수 문자(\\, %, _)를 글자 그대로 찾게 한다. 이스케이프 문자는 역슬래시다."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _encode_cursor(sort: SortKey, key: str, customer_id: int) -> str:
    raw = json.dumps([sort, key, customer_id]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str, sort: SortKey) -> tuple[str | datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        cursor_sort, key, customer_id = json.loads(raw)
        if cursor_sort != sort or not isinstance(key, str) or type(customer_id) is not int:
            raise ValueError
        return (datetime.fromisoformat(key) if sort == "recent" else key), customer_id
    except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
        raise CustomerInputError("목록 위치(cursor)가 올바르지 않습니다.") from None


class CustomerSearchPgAdapter(CustomerSearchPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def rebuild_search_entry(self, ctx: ShopContext, customer_id: int) -> None:
        customer = (
            await self._session.execute(
                select(CustomerOrm)
                .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if customer is None or customer.deleted_at is not None:
            await self._session.execute(
                delete(Entry).where(Entry.customer_id == customer_id, Entry.shop_id == ctx.shop_id)
            )
            return
        pets = (
            await self._session.execute(
                select(PetOrm.name, PetOrm.updated_at)
                .where(PetOrm.customer_id == customer_id)
                .order_by(PetOrm.id)
            )
        ).all()
        built = build_search_entry(customer.name, customer.phone, [name for name, _ in pets])
        values = dict(
            shop_id=ctx.shop_id,
            terms=built.terms,
            phone_last4=built.phone_last4,
            sort_name=built.sort_name,
            # 원본의 마지막 변경 시각. 반려동물을 지운 것은 활동으로 치지 않는다.
            last_activity_at=max([customer.updated_at, *(updated for _, updated in pets)]),
        )
        stmt = insert(Entry).values(customer_id=customer_id, **values)
        await self._session.execute(
            stmt.on_conflict_do_update(index_elements=[Entry.customer_id], set_=values)
        )

    def _matching(self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool):
        """검색어의 모든 낱말에 걸리는 이 매장의 가족. 기본은 살아 있는 반려동물이 한 마리라도 있는 가족만."""
        conditions = [Entry.shop_id == ctx.shop_id]
        for word in words:
            pattern = _like_escape(word.value)
            if word.kind == "last4":
                conditions.append(Entry.phone_last4.like(pattern + "%", escape="\\"))
            else:
                conditions.append(Entry.terms.ilike("%" + pattern + "%", escape="\\"))
        if not include_passed:
            live = aliased(PetOrm)   # 반려동물 수를 셀 때 바깥 쿼리의 pets 와 섞이지 않게 따로 부른다
            conditions.append(
                exists().where(live.customer_id == Entry.customer_id, live.passed_away_at.is_(None))
            )
        return conditions

    async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
        key_column = Entry.last_activity_at if request.sort == "recent" else Entry.sort_name
        stmt = select(Entry.customer_id, key_column).where(
            *self._matching(ctx, request.words, request.include_passed)
        )
        if request.cursor is not None:
            key, after_id = _decode_cursor(request.cursor, request.sort)
            position, after = tuple_(key_column, Entry.customer_id), tuple_(key, after_id)
            stmt = stmt.where(position < after if request.sort == "recent" else position > after)
        if request.sort == "recent":
            stmt = stmt.order_by(key_column.desc(), Entry.customer_id.desc())
        else:
            stmt = stmt.order_by(key_column, Entry.customer_id)
        rows = (await self._session.execute(stmt.limit(request.limit + 1))).all()

        page = rows[: request.limit]
        next_cursor = None
        if len(rows) > request.limit:
            last_id, last_key = page[-1]
            key_text = last_key.isoformat() if request.sort == "recent" else last_key
            next_cursor = _encode_cursor(request.sort, key_text, last_id)
        return SearchPage(customer_ids=[customer_id for customer_id, _ in page], next_cursor=next_cursor)

    async def count_pets(
        self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool
    ) -> int:
        stmt = (
            select(func.count(PetOrm.id))
            .join(Entry, Entry.customer_id == PetOrm.customer_id)
            .where(*self._matching(ctx, words, include_passed))
        )
        if not include_passed:
            stmt = stmt.where(PetOrm.passed_away_at.is_(None))
        return (await self._session.execute(stmt)).scalar_one()
```



- [ ] **Step 4: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/adapter/test_customer_search_pg_adapter.py -q -p no:cacheprovider`
Expected: `16 passed`


- [ ] **Step 5: 판별력을 확인한다**

어댑터의 `_like_escape`가 값을 그대로 돌려주게 잠시 바꾸고 `test_LIKE_특수_문자는_글자_그대로_찾는다`를 돌린다 → `%`가 모든 가족을 찾아 실패해야 한다. 되돌린다.


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `340 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app/dtos/customer_search_dto.py backend/apps/customer/app/ports/output/customer_search_port.py backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py
git commit -m "feat(customer): 검색 포트와 PostgreSQL 검색 어댑터"
```

---

### Task 7: 공용 부품과 조회 슬라이스 넷 — 고객 상세, 반려동물 상세, 질병 종류, 자기소개

슬라이스들이 함께 쓰는 부품(보기 DTO, 상세 조립, 오류 표, 경로 변수, 조립 함수, 인터랙터용 메모리 스텁, 라우터 테스트 도우미)을 만들고, 쓰기가 없는 슬라이스 넷으로 API 프로세스에 처음 붙인다. 고객 상세는 전체 번호를 주는 유일한 응답이다. 반려동물 상세의 보호자 번호는 가린다(C7). 경로 변수는 bigint 상한을 넘으면 422(C17). 자기소개는 매장 경로 아래라 소속 확인을 거친다("이 계획에서 새로 정한 것" 15번).

인터랙터 테스트의 스텁(`tests/helpers/fakes.py`)은 포트 전체를 한 번에 만든다 — 뒤 작업의 인터랙터 테스트도 이것을 쓴다. 스텁들은 호출을 `journal` 한 목록에 남겨서 "잠근 뒤 쓰고, 쓴 뒤 검색 줄을 다시 만든다"를 순서째 단언할 수 있다.

**Files:**
- Create: `backend/apps/customer/app/dtos/customer_view_dto.py`
- Create: `backend/apps/customer/app/services/detail_reader.py`
- Create: `backend/apps/customer/adapter/inbound/api/error_map.py`
- Create: `backend/apps/customer/adapter/inbound/api/path_params.py`
- Create: `backend/apps/customer/dependencies/customer_wiring.py`
- Create: `backend/apps/customer/app/dtos/get_customer_dto.py`
- Create: `backend/apps/customer/app/ports/input/get_customer_use_case.py`
- Create: `backend/apps/customer/app/use_cases/get_customer_interactor.py`
- Create: `backend/apps/customer/dependencies/get_customer_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/get_customer_router.py`
- Create: `backend/apps/customer/app/dtos/get_pet_dto.py`
- Create: `backend/apps/customer/app/ports/input/get_pet_use_case.py`
- Create: `backend/apps/customer/app/use_cases/get_pet_interactor.py`
- Create: `backend/apps/customer/dependencies/get_pet_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/get_pet_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/get_pet_router.py`
- Create: `backend/apps/customer/app/dtos/list_pet_condition_types_dto.py`
- Create: `backend/apps/customer/app/ports/input/list_pet_condition_types_use_case.py`
- Create: `backend/apps/customer/app/use_cases/list_pet_condition_types_interactor.py`
- Create: `backend/apps/customer/dependencies/list_pet_condition_types_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/list_pet_condition_types_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/list_pet_condition_types_router.py`
- Create: `backend/apps/customer/app/ports/output/customer_myself_record_port.py`
- Create: `backend/apps/customer/adapter/outbound/log_customer_myself_record_adapter.py`
- Create: `backend/apps/customer/app/dtos/customer_myself_dto.py`
- Create: `backend/apps/customer/app/ports/input/customer_myself_use_case.py`
- Create: `backend/apps/customer/app/use_cases/customer_myself_interactor.py`
- Create: `backend/apps/customer/dependencies/customer_myself_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/customer_myself_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/customer_myself_router.py`
- Modify: `backend/main.py`
- Create: `backend/apps/customer/tests/helpers/fakes.py` (테스트 도우미)
- Create: `backend/apps/customer/tests/helpers/api.py` (테스트 도우미)
- Test: `backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_get_customer_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_get_pet_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_get_pet_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_list_pet_condition_types_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_list_pet_condition_types_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_customer_myself_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_customer_myself_router.py`

**Interfaces:**
- Consumes: Task 5 의 리포지토리 포트·엔티티, Task 6 의 `SearchPage`, Task 3 의 `age_label`·`seoul_today`, Task 2 의 `mask_phone`, `core.shop_guard.get_shop_context`
- Produces:
  - `customer.app.dtos.customer_view_dto`: `ConditionView`, `PetView`(+`PetView.of(pet, today)`), `CustomerView`(+`of(customer)`), `CustomerDetailView(customer, pets)`, `OwnerSummaryView(customer_id, name, phone_masked)`(+`of`), `SiblingView(pet_id, name, species, passed_away)`, `PetDetailView(pet, owner, siblings)`
  - `customer.app.services.detail_reader`: `async read_customer_detail(ctx, customer_id, customers, pets, today) -> CustomerDetailView`, `async read_pet_detail(ctx, pet_id, customers, pets, today) -> PetDetailView`
  - `customer.adapter.inbound.api.error_map.CUSTOMER_ERROR_STATUS`, `customer.adapter.inbound.api.path_params`: `CustomerId`, `PetId`
  - `customer.dependencies.customer_wiring`: `build_customer_repository(db)`, `build_pet_repository(db)`, `build_condition_type_repository(db)`, `build_customer_search(db)`
  - 스키마: `get_customer_schema`의 `PetSchema`(+`of`), `CustomerSchema`, `CustomerDetailSchema`(+`of`); `get_pet_schema`의 `PetDetailSchema`(+`of`) — 뒤 작업의 응답이 이것을 쓴다
  - 입력 포트: `GetCustomerUseCase.get_customer(GetCustomerQuery(ctx, customer_id)) -> CustomerDetailView`, `GetPetUseCase.get_pet(GetPetQuery(ctx, pet_id)) -> PetDetailView`, `ListPetConditionTypesUseCase.list_pet_condition_types(ListPetConditionTypesQuery(ctx)) -> list[ConditionTypeView]`, `CustomerMyselfUseCase.introduce_myself(CustomerMyselfQuery(id, name)) -> CustomerMyselfResponse`
  - 프로바이더: `get_get_customer_use_case`, `get_get_pet_use_case`, `get_list_pet_condition_types_use_case`, `get_customer_myself_use_case`
  - 테스트 도우미: `fakes.family() -> (journal, FakeCustomers, FakePets, FakeConditionTypes, FakeSearch)`, `fakes.today`, `FakeSearch(journal, page=None, pet_count=0)`; `api.build_app(router, provider, stub_use_case, access=None, user_id=5)`, `api.STAFF`, `api.NO_WRITE`, `api.customer_detail_view()`, `api.pet_detail_view()`, `api.pet_view()`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/helpers/fakes.py`:
```python
"""customer 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal

from customer.app.dtos.customer_search_dto import SearchPage
from customer.domain.entities.condition_type import ConditionType
from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet, PetCondition
from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenError, PetNotFoundError

TODAY = date(2026, 9, 22)
NOW = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)
LABELS = {"patella_luxation": "슬개골 탈구", "heart_disease": "심장 질환", "allergy": "알레르기",
          "other": "기타"}


def today() -> date:
    return TODAY


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeConditionTypes:
    async def list_all(self):
        return [ConditionType(code=c, label=l, sort_order=i) for i, (c, l) in enumerate(LABELS.items())]


class FakeCustomers:
    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.rows: dict[int, Customer] = {}
        self._next = 1

    def seed(self, shop_id=1, name="김민지", phone="01012345678", consent=False) -> Customer:
        customer = Customer(id=self._next, shop_id=shop_id, name=name, phone=phone, phone_alt=None,
                            marketing_consent=consent, marketing_consent_changed_at=NOW, memo=None)
        self.rows[customer.id] = customer
        self._next += 1
        return customer

    def _find(self, ctx, customer_id) -> Customer:
        customer = self.rows.get(customer_id)
        if customer is None or customer.shop_id != ctx.shop_id:
            raise CustomerNotFoundError("고객을 찾을 수 없습니다.")
        return customer

    async def find_active_by_phone(self, ctx, phone):
        return next((c for c in self.rows.values() if c.shop_id == ctx.shop_id and c.phone == phone), None)

    async def get_active(self, ctx, customer_id):
        return self._find(ctx, customer_id)

    async def lock_active(self, ctx, customer_id):
        self.journal.append(("lock_customer", customer_id))
        return self._find(ctx, customer_id)

    async def list_active(self, ctx, customer_ids):
        return [c for i, c in self.rows.items() if i in customer_ids and c.shop_id == ctx.shop_id]

    async def create(self, ctx, profile):
        if await self.find_active_by_phone(ctx, profile.phone):
            raise CustomerPhoneTakenError("이미 등록된 전화번호입니다.")
        customer = self.seed(shop_id=ctx.shop_id, name=profile.name, phone=profile.phone,
                             consent=profile.marketing_consent)
        self.rows[customer.id] = replace(customer, phone_alt=profile.phone_alt, memo=profile.memo)
        self.journal.append(("create_customer", customer.id))
        return self.rows[customer.id]

    async def update(self, ctx, customer_id, profile, consent_changed):
        current = self._find(ctx, customer_id)
        self.rows[customer_id] = replace(
            current, name=profile.name, phone=profile.phone, phone_alt=profile.phone_alt,
            marketing_consent=profile.marketing_consent, memo=profile.memo,
        )
        self.journal.append(("update_customer", customer_id, consent_changed))
        return self.rows[customer_id]

    async def anonymize(self, ctx, customer_id):
        self._find(ctx, customer_id)
        del self.rows[customer_id]
        self.journal.append(("anonymize", customer_id))


class FakePets:
    def __init__(self, journal: Journal, customers: FakeCustomers) -> None:
        self.journal = journal
        self.customers = customers
        self.rows: dict[int, Pet] = {}
        self._next = 101

    def seed(self, customer_id, name="콩이", passed_away=False, conditions=()) -> Pet:
        pet = Pet(id=self._next, customer_id=customer_id, name=name, species="dog", breed="말티즈",
                  sex="female", neutered=True, birth_date=None, birth_year=2021,
                  weight_kg=Decimal("3.2"), no_known_conditions=not conditions,
                  memo=None, passed_away_at=NOW if passed_away else None, conditions=tuple(conditions))
        self.rows[pet.id] = pet
        self._next += 1
        return pet

    def _owned(self, ctx, pet_id) -> Pet:
        pet = self.rows.get(pet_id)
        owner = self.customers.rows.get(pet.customer_id) if pet else None
        if owner is None or owner.shop_id != ctx.shop_id:
            raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
        return pet

    async def get(self, ctx, pet_id):
        return self._owned(ctx, pet_id)

    async def lock_owner(self, ctx, pet_id):
        customer_id = self._owned(ctx, pet_id).customer_id
        self.journal.append(("lock_customer", customer_id))
        return customer_id

    async def list_for_customers(self, ctx, customer_ids):
        return [p for p in self.rows.values() if p.customer_id in customer_ids
                and self.customers.rows.get(p.customer_id) is not None
                and self.customers.rows[p.customer_id].shop_id == ctx.shop_id]

    async def add(self, ctx, customer_id, profile):
        pet = self.seed(customer_id, name=profile.name)
        self.rows[pet.id] = self._apply(pet, profile)
        self.journal.append(("add_pet", customer_id))
        return self.rows[pet.id]

    async def update(self, ctx, pet_id, profile):
        self.rows[pet_id] = self._apply(self._owned(ctx, pet_id), profile)
        self.journal.append(("update_pet", pet_id))
        return self.rows[pet_id]

    async def set_passed_away(self, ctx, pet_id, passed_away):
        self.rows[pet_id] = replace(self._owned(ctx, pet_id), passed_away_at=NOW if passed_away else None)
        self.journal.append(("set_passed_away", pet_id, passed_away))
        return self.rows[pet_id]

    async def count_for_customer(self, ctx, customer_id):
        return len([p for p in self.rows.values() if p.customer_id == customer_id])

    async def delete(self, ctx, pet_id):
        self._owned(ctx, pet_id)
        del self.rows[pet_id]
        self.journal.append(("delete_pet", pet_id))

    @staticmethod
    def _apply(pet: Pet, profile) -> Pet:
        return replace(
            pet, name=profile.name, species=profile.species, breed=profile.breed, sex=profile.sex,
            neutered=profile.neutered, birth_date=profile.birth_date, birth_year=profile.birth_year,
            weight_kg=profile.weight_kg, no_known_conditions=profile.no_known_conditions,
            memo=profile.memo,
            conditions=tuple(
                PetCondition(type_code=c.type_code, label=LABELS[c.type_code],
                             custom_label=c.custom_label, note=c.note)
                for c in profile.conditions
            ),
        )


class FakeSearch:
    def __init__(self, journal: Journal, page: SearchPage | None = None, pet_count: int = 0) -> None:
        self.journal = journal
        self.page = page or SearchPage(customer_ids=[], next_cursor=None)
        self.pet_count = pet_count
        self.requests = []

    async def rebuild_search_entry(self, ctx, customer_id):
        self.journal.append(("rebuild", customer_id))

    async def search(self, ctx, request):
        self.requests.append((ctx, request))
        return self.page

    async def count_pets(self, ctx, words, include_passed):
        self.requests.append((ctx, words, include_passed))
        return self.pet_count


def family():
    """스텁 한 벌을 같은 호출 기록으로 묶어 만든다."""
    journal = Journal()
    customers = FakeCustomers(journal)
    pets = FakePets(journal, customers)
    return journal, customers, pets, FakeConditionTypes(), FakeSearch(journal)
```

`backend/apps/customer/tests/helpers/api.py`:
```python
"""customer 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from customer.adapter.inbound.api.error_map import CUSTOMER_ERROR_STATUS
from customer.app.dtos.customer_view_dto import (
    CustomerDetailView,
    CustomerView,
    OwnerSummaryView,
    PetDetailView,
    PetView,
)
from customer.tests.helpers.profiles import OWNER_PERMISSIONS, STAFF_PERMISSIONS
from hub.app.dtos.shop_context import ShopContext

NOW = datetime(2026, 9, 22, 1, 0, tzinfo=timezone.utc)

class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=OWNER_PERMISSIONS, role="owner"):
        self.permissions = frozenset(permissions)
        self.role = role

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role=self.role, permissions=self.permissions)


STAFF = StubShopAccess(STAFF_PERMISSIONS, role="staff")
NO_WRITE = StubShopAccess(frozenset({"reservation:write"}), role="staff")


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None, user_id=5) -> FastAPI:
    """access=None 이면 사장 권한으로 통과시킨다. user_id=None 이면 토큰 없는 요청이 된다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, CUSTOMER_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    if user_id is not None:
        app.dependency_overrides[get_current_user_id] = lambda: user_id
    app.dependency_overrides[get_shop_access_port] = lambda: access or StubShopAccess()
    return app


def pet_view(pet_id=101, name="콩이") -> PetView:
    return PetView(
        pet_id=pet_id, customer_id=1, name=name, species="dog", breed="말티즈", sex="female",
        neutered=True, birth_date=None, birth_year=2021, age_label="5살", weight_kg=Decimal("3.2"),
        no_known_conditions=True, has_conditions=False, conditions=[], memo=None, passed_away_at=None,
    )


def customer_detail_view() -> CustomerDetailView:
    return CustomerDetailView(
        customer=CustomerView(customer_id=1, name="김민지", phone="01012345678", phone_alt=None,
                              marketing_consent=True, marketing_consent_changed_at=NOW, memo=None),
        pets=[pet_view()],
    )


def pet_detail_view() -> PetDetailView:
    return PetDetailView(
        pet=pet_view(),
        owner=OwnerSummaryView(customer_id=1, name="김민지", phone_masked="010-12··-5678"),
        siblings=[],
    )
```

`backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py`:
```python
import pytest

from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_보호자_전체와_반려동물_전체를_돌려준다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    view = await GetCustomerInteractor(customers, pets, today).get_customer(
        GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
    )
    assert view.customer.phone == "01012345678"   # 상세는 전체 번호다
    assert [(p.name, p.passed_away_at is not None) for p in view.pets] == [("콩이", False), ("별이", True)]


async def test_다른_매장의_고객은_404_다():
    _, customers, pets, _, _ = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await GetCustomerInteractor(customers, pets, today).get_customer(
            GetCustomerQuery(ctx=ctx(shop_id=1), customer_id=customer.id)
        )
```

`backend/apps/customer/tests/adapter/test_get_customer_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
from customer.dependencies.get_customer_provider import get_get_customer_use_case
from customer.domain.errors import (
    CustomerInputError,
    CustomerNotFoundError,
    CustomerPhoneTakenError,
    LastPetError,
    PetHealthConflictError,
    PetHealthRequiredError,
    PetNotFoundError,
)
from customer.tests.helpers.api import NO_WRITE, build_app, customer_detail_view


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.queries = []

    async def get_customer(self, query):
        self.queries.append(query)
        if self.error:
            raise self.error
        return customer_detail_view()


async def _get(stub, path="/v1/shops/3/customers/1"):
    app = build_app(get_customer_router, get_get_customer_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_멤버는_전체_번호가_든_고객_상세를_본다():
    stub = _StubUseCase()
    response = await _get(stub)
    assert response.status_code == 200
    assert response.json()["customer"]["phone"] == "01012345678"
    assert (stub.queries[0].ctx.shop_id, stub.queries[0].customer_id) == (3, 1)


async def test_범위를_벗어난_ID_는_DB_에_닿기_전에_422_다():
    for path in ("/v1/shops/3/customers/0", "/v1/shops/3/customers/9223372036854775808",
                 "/v1/shops/3/customers/abc"):
        stub = _StubUseCase()
        response = await _get(stub, path)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR"), path
        assert stub.queries == []


async def test_도메인_오류는_설계의_상태_코드와_코드로_나간다():
    cases = [
        (CustomerNotFoundError("x"), 404, "CUSTOMER_NOT_FOUND"),
        (PetNotFoundError("x"), 404, "PET_NOT_FOUND"),
        (CustomerPhoneTakenError("x"), 409, "CUSTOMER_PHONE_TAKEN"),
        (LastPetError("x"), 409, "LAST_PET"),
        (CustomerInputError("x"), 422, "VALIDATION_ERROR"),
        (PetHealthRequiredError("x"), 422, "PET_HEALTH_REQUIRED"),
        (PetHealthConflictError("x"), 422, "PET_HEALTH_CONFLICT"),
    ]
    for error, status, code in cases:
        response = await _get(_StubUseCase(error))
        assert (response.status_code, response.json()["code"]) == (status, code)
```

`backend/apps/customer/tests/app/use_cases/test_get_pet_interactor.py`:
```python
import pytest

from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.use_cases.get_pet_interactor import GetPetInteractor
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_반려동물과_보호자_요약과_같은_보호자의_다른_아이를_돌려준다():
    _, customers, pets, _, _ = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    view = await GetPetInteractor(customers, pets, today).get_pet(GetPetQuery(ctx=ctx(), pet_id=kong.id))
    assert view.pet.name == "콩이"
    assert (view.owner.name, view.owner.phone_masked) == ("김민지", "010-12··-5678")
    assert [(s.name, s.passed_away) for s in view.siblings] == [("별이", True)]


async def test_다른_매장의_반려동물은_404_다():
    _, customers, pets, _, _ = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await GetPetInteractor(customers, pets, today).get_pet(GetPetQuery(ctx=ctx(shop_id=1), pet_id=pet.id))
```

`backend/apps/customer/tests/adapter/test_get_pet_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
from customer.dependencies.get_pet_provider import get_get_pet_use_case
from customer.tests.helpers.api import NO_WRITE, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def get_pet(self, query):
        self.queries.append(query)
        return pet_detail_view()


async def test_멤버는_반려동물_상세를_보고_보호자_번호는_가려져_있다():
    stub = _StubUseCase()
    app = build_app(get_pet_router, get_get_pet_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/shops/3/pets/101")
    assert response.status_code == 200
    assert response.json()["owner"] == {"customer_id": 1, "name": "김민지", "phone_masked": "010-12··-5678"}
    assert (stub.queries[0].ctx.shop_id, stub.queries[0].pet_id) == (3, 101)
```

`backend/apps/customer/tests/app/use_cases/test_list_pet_condition_types_interactor.py`:
```python
from customer.app.dtos.list_pet_condition_types_dto import ListPetConditionTypesQuery
from customer.app.use_cases.list_pet_condition_types_interactor import ListPetConditionTypesInteractor
from customer.tests.helpers.fakes import FakeConditionTypes
from customer.tests.helpers.profiles import ctx


async def test_질병_종류를_순서대로_돌려준다():
    views = await ListPetConditionTypesInteractor(FakeConditionTypes()).list_pet_condition_types(
        ListPetConditionTypesQuery(ctx=ctx())
    )
    assert [(v.code, v.label) for v in views][-1] == ("other", "기타")
    assert [v.sort_order for v in views] == sorted(v.sort_order for v in views)
```

`backend/apps/customer/tests/adapter/test_list_pet_condition_types_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.list_pet_condition_types_router import (
    list_pet_condition_types_router,
)
from customer.app.dtos.list_pet_condition_types_dto import ConditionTypeView
from customer.dependencies.list_pet_condition_types_provider import (
    get_list_pet_condition_types_use_case,
)
from customer.tests.helpers.api import NO_WRITE, build_app


class _StubUseCase:
    async def list_pet_condition_types(self, query):
        return [ConditionTypeView(code="patella_luxation", label="슬개골 탈구", sort_order=1)]


async def test_멤버는_질병_종류를_본다():
    app = build_app(list_pet_condition_types_router, get_list_pet_condition_types_use_case,
                    _StubUseCase(), access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.get("/v1/shops/3/pet-condition-types")
    assert response.json() == [{"code": "patella_luxation", "label": "슬개골 탈구", "sort_order": 1}]
```

`backend/apps/customer/tests/app/use_cases/test_customer_myself_interactor.py`:
```python
from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery
from customer.app.use_cases.customer_myself_interactor import CustomerMyselfInteractor


class _StubRecord:
    def __init__(self):
        self.records = []

    async def record(self, subject, note):
        self.records.append((subject, note))


async def test_자기소개는_실제_엔드포인트와_제약을_말하고_기록을_남긴다():
    record = _StubRecord()
    result = await CustomerMyselfInteractor(record=record).introduce_myself(
        CustomerMyselfQuery(id=4, name="고객 (customer)")
    )
    assert result.id == 4
    for path in ("GET /customers", "/customers/lookup", "POST /customers/{customer_id}/pets",
                 "/pets/{pet_id}/passed-away", "/pet-condition-types"):
        assert path in result.introduction
    assert "customer:delete" in result.introduction and "익명화" in result.introduction
    assert record.records[0][0] == "introduce_myself"
```

`backend/apps/customer/tests/adapter/test_customer_myself_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.customer_myself_router import customer_myself_router
from customer.adapter.outbound.log_customer_myself_record_adapter import (
    LogCustomerMyselfRecordAdapter,
)
from customer.app.use_cases.customer_myself_interactor import CustomerMyselfInteractor
from customer.dependencies.customer_myself_provider import get_customer_myself_use_case
from customer.tests.helpers.api import NO_WRITE, build_app


async def _get(user_id=5):
    use_case = CustomerMyselfInteractor(record=LogCustomerMyselfRecordAdapter())
    app = build_app(customer_myself_router, get_customer_myself_use_case, use_case,
                    access=NO_WRITE, user_id=user_id)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get("/v1/shops/3/customers/myself")


async def test_멤버는_자기소개를_본다():
    response = await _get()
    assert response.status_code == 200
    assert response.json()["name"] == "고객 (customer)"
    assert "/customers/lookup" in response.json()["introduction"]


async def test_토큰이_없으면_401_이다():
    response = await _get(user_id=None)
    assert (response.status_code, response.json()["code"]) == (401, "UNAUTHENTICATED")
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_get_customer_interactor.py apps/customer/tests/adapter/test_get_customer_router.py apps/customer/tests/app/use_cases/test_get_pet_interactor.py apps/customer/tests/adapter/test_get_pet_router.py apps/customer/tests/app/use_cases/test_list_pet_condition_types_interactor.py apps/customer/tests/adapter/test_list_pet_condition_types_router.py apps/customer/tests/app/use_cases/test_customer_myself_interactor.py apps/customer/tests/adapter/test_customer_myself_router.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.app.use_cases.get_customer_interactor'`(여덟 파일 모두 import 오류)


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/customer_view_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from customer.domain.entities.customer import Customer
from customer.domain.entities.pet import Pet
from customer.domain.services.pet_age import age_label
from customer.domain.services.phone_number import mask_phone


@dataclass(frozen=True)
class ConditionView:
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


@dataclass(frozen=True)
class PetView:
    pet_id: int
    customer_id: int
    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    age_label: str
    weight_kg: Decimal
    no_known_conditions: bool
    has_conditions: bool
    conditions: list[ConditionView]
    memo: str | None
    passed_away_at: datetime | None

    @classmethod
    def of(cls, pet: Pet, today: date) -> PetView:
        return cls(
            pet_id=pet.id, customer_id=pet.customer_id, name=pet.name, species=pet.species,
            breed=pet.breed, sex=pet.sex, neutered=pet.neutered, birth_date=pet.birth_date,
            birth_year=pet.birth_year, age_label=age_label(pet.birth_date, pet.birth_year, today),
            weight_kg=pet.weight_kg, no_known_conditions=pet.no_known_conditions,
            has_conditions=pet.has_conditions,
            conditions=[
                ConditionView(type_code=c.type_code, label=c.label, custom_label=c.custom_label,
                              note=c.note)
                for c in pet.conditions
            ],
            memo=pet.memo, passed_away_at=pet.passed_away_at,
        )


@dataclass(frozen=True)
class CustomerView:
    """보호자 전체 — 전체 번호가 들어 있다. 고객 상세에서만 내보낸다."""

    customer_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None

    @classmethod
    def of(cls, customer: Customer) -> CustomerView:
        return cls(
            customer_id=customer.id, name=customer.name, phone=customer.phone,
            phone_alt=customer.phone_alt, marketing_consent=customer.marketing_consent,
            marketing_consent_changed_at=customer.marketing_consent_changed_at, memo=customer.memo,
        )


@dataclass(frozen=True)
class CustomerDetailView:
    customer: CustomerView
    pets: list[PetView]


@dataclass(frozen=True)
class OwnerSummaryView:
    """반려동물 화면의 보호자 요약. 번호는 가린다 — 전체 번호는 고객 상세에서만 준다."""

    customer_id: int
    name: str
    phone_masked: str

    @classmethod
    def of(cls, customer: Customer) -> OwnerSummaryView:
        return cls(customer_id=customer.id, name=customer.name, phone_masked=mask_phone(customer.phone))


@dataclass(frozen=True)
class SiblingView:
    pet_id: int
    name: str
    species: str
    passed_away: bool


@dataclass(frozen=True)
class PetDetailView:
    pet: PetView
    owner: OwnerSummaryView
    siblings: list[SiblingView]
```

`backend/apps/customer/app/services/detail_reader.py`:
```python
"""고객 상세·반려동물 상세를 원본 표에서 읽어 조립한다. 여러 슬라이스가 쓰기를 마친 뒤 같은 모양으로 돌려준다."""
from __future__ import annotations

from datetime import date

from customer.app.dtos.customer_view_dto import (
    CustomerDetailView,
    CustomerView,
    OwnerSummaryView,
    PetDetailView,
    PetView,
    SiblingView,
)
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from hub.app.dtos.shop_context import ShopContext


async def read_customer_detail(
    ctx: ShopContext, customer_id: int, customers: CustomerRepository, pets: PetRepository,
    today: date,
) -> CustomerDetailView:
    customer = await customers.get_active(ctx, customer_id)
    family = await pets.list_for_customers(ctx, [customer_id])
    return CustomerDetailView(
        customer=CustomerView.of(customer), pets=[PetView.of(pet, today) for pet in family]
    )


async def read_pet_detail(
    ctx: ShopContext, pet_id: int, customers: CustomerRepository, pets: PetRepository, today: date
) -> PetDetailView:
    pet = await pets.get(ctx, pet_id)
    owner = await customers.get_active(ctx, pet.customer_id)
    family = await pets.list_for_customers(ctx, [pet.customer_id])
    return PetDetailView(
        pet=PetView.of(pet, today),
        owner=OwnerSummaryView.of(owner),
        siblings=[
            SiblingView(pet_id=p.id, name=p.name, species=p.species, passed_away=p.passed_away)
            for p in family if p.id != pet.id
        ],
    )
```

`backend/apps/customer/adapter/inbound/api/error_map.py`:
```python
"""customer 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from customer.domain.errors import (
    CustomerInputError,
    CustomerNotFoundError,
    CustomerPhoneTakenError,
    LastPetError,
    PetHealthConflictError,
    PetHealthRequiredError,
    PetNotFoundError,
)

CUSTOMER_ERROR_STATUS: dict[type[Exception], int] = {
    CustomerNotFoundError: 404,
    PetNotFoundError: 404,
    CustomerPhoneTakenError: 409,
    LastPetError: 409,
    CustomerInputError: 422,
    PetHealthRequiredError: 422,
    PetHealthConflictError: 422,
}
```

`backend/apps/customer/adapter/inbound/api/path_params.py`:
```python
"""customer 경로 변수. bigint 를 넘는 값은 DB 에 닿기 전에 422 로 막는다(닿으면 asyncpg 오류로 500 이 된다)."""
from typing import Annotated

from fastapi import Path

_MAX_BIGINT = 9_223_372_036_854_775_807

CustomerId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
PetId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
```

`backend/apps/customer/dependencies/customer_wiring.py`:
```python
"""customer 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository


def build_customer_repository(db: AsyncSession) -> CustomerRepository:
    return CustomerPgRepository(db)


def build_pet_repository(db: AsyncSession) -> PetRepository:
    return PetPgRepository(db)


def build_condition_type_repository(db: AsyncSession) -> ConditionTypeRepository:
    return ConditionTypePgRepository(db)


def build_customer_search(db: AsyncSession) -> CustomerSearchPort:
    return CustomerSearchPgAdapter(db)
```

`backend/apps/customer/app/dtos/get_customer_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetCustomerQuery:
    ctx: ShopContext
    customer_id: int
```

`backend/apps/customer/app/ports/input/get_customer_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.get_customer_dto import GetCustomerQuery


class GetCustomerUseCase(ABC):
    @abstractmethod
    async def get_customer(self, query: GetCustomerQuery) -> CustomerDetailView: ...
```

`backend/apps/customer/app/use_cases/get_customer_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class GetCustomerInteractor(GetCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def get_customer(self, query: GetCustomerQuery) -> CustomerDetailView:
        return await read_customer_detail(
            query.ctx, query.customer_id, self._customers, self._pets, self._today()
        )
```

`backend/apps/customer/dependencies/get_customer_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_get_customer_use_case(db: DbSession) -> GetCustomerUseCase:
    return GetCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py`:
```python
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from customer.app.dtos.customer_view_dto import CustomerDetailView, CustomerView, PetView


class ConditionSchema(BaseModel):
    type_code: str
    label: str
    custom_label: str | None
    note: str | None


class PetSchema(BaseModel):
    pet_id: int
    customer_id: int
    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    age_label: str
    weight_kg: float
    no_known_conditions: bool
    has_conditions: bool
    conditions: list[ConditionSchema]
    memo: str | None
    passed_away_at: datetime | None

    @classmethod
    def of(cls, view: PetView) -> PetSchema:
        return cls(
            pet_id=view.pet_id, customer_id=view.customer_id, name=view.name,
            species=view.species, breed=view.breed, sex=view.sex, neutered=view.neutered,
            birth_date=view.birth_date, birth_year=view.birth_year, age_label=view.age_label,
            weight_kg=float(view.weight_kg), no_known_conditions=view.no_known_conditions,
            has_conditions=view.has_conditions,
            conditions=[
                ConditionSchema(type_code=c.type_code, label=c.label,
                                custom_label=c.custom_label, note=c.note)
                for c in view.conditions
            ],
            memo=view.memo, passed_away_at=view.passed_away_at,
        )


class CustomerSchema(BaseModel):
    customer_id: int
    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    marketing_consent_changed_at: datetime
    memo: str | None

    @classmethod
    def of(cls, view: CustomerView) -> CustomerSchema:
        return cls(
            customer_id=view.customer_id, name=view.name, phone=view.phone,
            phone_alt=view.phone_alt, marketing_consent=view.marketing_consent,
            marketing_consent_changed_at=view.marketing_consent_changed_at, memo=view.memo,
        )


class CustomerDetailSchema(BaseModel):
    """고객 상세 — 전체 번호가 들어 있는 유일한 응답이다."""

    customer: CustomerSchema
    pets: list[PetSchema]

    @classmethod
    def of(cls, view: CustomerDetailView) -> CustomerDetailSchema:
        return cls(customer=CustomerSchema.of(view.customer), pets=[PetSchema.of(p) for p in view.pets])
```

`backend/apps/customer/adapter/inbound/api/v1/get_customer_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.app.dtos.get_customer_dto import GetCustomerQuery
from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
from customer.dependencies.get_customer_provider import get_get_customer_use_case
from hub.app.dtos.shop_context import ShopContext

get_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@get_customer_router.get("/{shop_id}/customers/{customer_id}", response_model=CustomerDetailSchema)
async def get_customer(
    customer_id: CustomerId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetCustomerUseCase = Depends(get_get_customer_use_case),
) -> CustomerDetailSchema:
    return CustomerDetailSchema.of(
        await use_case.get_customer(GetCustomerQuery(ctx=ctx, customer_id=customer_id))
    )
```

`backend/apps/customer/app/dtos/get_pet_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetPetQuery:
    ctx: ShopContext
    pet_id: int
```

`backend/apps/customer/app/ports/input/get_pet_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.get_pet_dto import GetPetQuery


class GetPetUseCase(ABC):
    @abstractmethod
    async def get_pet(self, query: GetPetQuery) -> PetDetailView: ...
```

`backend/apps/customer/app/use_cases/get_pet_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class GetPetInteractor(GetPetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._today = today

    async def get_pet(self, query: GetPetQuery) -> PetDetailView:
        return await read_pet_detail(query.ctx, query.pet_id, self._customers, self._pets, self._today())
```

`backend/apps/customer/dependencies/get_pet_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.app.use_cases.get_pet_interactor import GetPetInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_get_pet_use_case(db: DbSession) -> GetPetUseCase:
    return GetPetInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/get_pet_schema.py`:
```python
from __future__ import annotations

from pydantic import BaseModel

from customer.adapter.inbound.api.schemas.get_customer_schema import PetSchema
from customer.app.dtos.customer_view_dto import PetDetailView


class OwnerSummarySchema(BaseModel):
    customer_id: int
    name: str
    phone_masked: str


class SiblingSchema(BaseModel):
    pet_id: int
    name: str
    species: str
    passed_away: bool


class PetDetailSchema(BaseModel):
    pet: PetSchema
    owner: OwnerSummarySchema
    siblings: list[SiblingSchema]

    @classmethod
    def of(cls, view: PetDetailView) -> PetDetailSchema:
        return cls(
            pet=PetSchema.of(view.pet),
            owner=OwnerSummarySchema(
                customer_id=view.owner.customer_id, name=view.owner.name,
                phone_masked=view.owner.phone_masked,
            ),
            siblings=[
                SiblingSchema(pet_id=s.pet_id, name=s.name, species=s.species,
                              passed_away=s.passed_away)
                for s in view.siblings
            ],
        )
```

`backend/apps/customer/adapter/inbound/api/v1/get_pet_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.get_pet_dto import GetPetQuery
from customer.app.ports.input.get_pet_use_case import GetPetUseCase
from customer.dependencies.get_pet_provider import get_get_pet_use_case
from hub.app.dtos.shop_context import ShopContext

get_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@get_pet_router.get("/{shop_id}/pets/{pet_id}", response_model=PetDetailSchema)
async def get_pet(
    pet_id: PetId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetPetUseCase = Depends(get_get_pet_use_case),
) -> PetDetailSchema:
    return PetDetailSchema.of(await use_case.get_pet(GetPetQuery(ctx=ctx, pet_id=pet_id)))
```

`backend/apps/customer/app/dtos/list_pet_condition_types_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListPetConditionTypesQuery:
    ctx: ShopContext


@dataclass(frozen=True)
class ConditionTypeView:
    code: str
    label: str
    sort_order: int
```

`backend/apps/customer/app/ports/input/list_pet_condition_types_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.list_pet_condition_types_dto import (
    ConditionTypeView,
    ListPetConditionTypesQuery,
)


class ListPetConditionTypesUseCase(ABC):
    @abstractmethod
    async def list_pet_condition_types(
        self, query: ListPetConditionTypesQuery
    ) -> list[ConditionTypeView]: ...
```

`backend/apps/customer/app/use_cases/list_pet_condition_types_interactor.py`:
```python
from __future__ import annotations

from customer.app.dtos.list_pet_condition_types_dto import (
    ConditionTypeView,
    ListPetConditionTypesQuery,
)
from customer.app.ports.input.list_pet_condition_types_use_case import ListPetConditionTypesUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository


class ListPetConditionTypesInteractor(ListPetConditionTypesUseCase):
    def __init__(self, condition_types: ConditionTypeRepository) -> None:
        self._condition_types = condition_types

    async def list_pet_condition_types(
        self, query: ListPetConditionTypesQuery
    ) -> list[ConditionTypeView]:
        return [
            ConditionTypeView(code=t.code, label=t.label, sort_order=t.sort_order)
            for t in await self._condition_types.list_all()
        ]
```

`backend/apps/customer/dependencies/list_pet_condition_types_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_pet_condition_types_use_case import ListPetConditionTypesUseCase
from customer.app.use_cases.list_pet_condition_types_interactor import ListPetConditionTypesInteractor
from customer.dependencies.customer_wiring import build_condition_type_repository


def get_list_pet_condition_types_use_case(db: DbSession) -> ListPetConditionTypesUseCase:
    return ListPetConditionTypesInteractor(
        condition_types=build_condition_type_repository(db),
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/list_pet_condition_types_schema.py`:
```python
from pydantic import BaseModel


class ConditionTypeSchema(BaseModel):
    code: str
    label: str
    sort_order: int
```

`backend/apps/customer/adapter/inbound/api/v1/list_pet_condition_types_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.list_pet_condition_types_schema import (
    ConditionTypeSchema,
)
from customer.app.dtos.list_pet_condition_types_dto import ListPetConditionTypesQuery
from customer.app.ports.input.list_pet_condition_types_use_case import (
    ListPetConditionTypesUseCase,
)
from customer.dependencies.list_pet_condition_types_provider import (
    get_list_pet_condition_types_use_case,
)
from hub.app.dtos.shop_context import ShopContext

list_pet_condition_types_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@list_pet_condition_types_router.get(
    "/{shop_id}/pet-condition-types", response_model=list[ConditionTypeSchema]
)
async def list_pet_condition_types(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListPetConditionTypesUseCase = Depends(get_list_pet_condition_types_use_case),
) -> list[ConditionTypeSchema]:
    views = await use_case.list_pet_condition_types(ListPetConditionTypesQuery(ctx=ctx))
    return [ConditionTypeSchema(code=v.code, label=v.label, sort_order=v.sort_order) for v in views]
```

`backend/apps/customer/app/ports/output/customer_myself_record_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class CustomerMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/customer/adapter/outbound/log_customer_myself_record_adapter.py`:
```python
from __future__ import annotations

import logging

from customer.app.ports.output.customer_myself_record_port import CustomerMyselfRecordPort

logger = logging.getLogger(__name__)


class LogCustomerMyselfRecordAdapter(CustomerMyselfRecordPort):
    """기록을 로그로 남기는 구현. 고객 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[customer-myself-record] %s | %s", subject, note)
```

`backend/apps/customer/app/dtos/customer_myself_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class CustomerMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/customer/app/ports/input/customer_myself_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery, CustomerMyselfResponse


class CustomerMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: CustomerMyselfQuery) -> CustomerMyselfResponse: ...
```

`backend/apps/customer/app/use_cases/customer_myself_interactor.py`:
```python
from __future__ import annotations

from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery, CustomerMyselfResponse
from customer.app.ports.input.customer_myself_use_case import CustomerMyselfUseCase
from customer.app.ports.output.customer_myself_record_port import CustomerMyselfRecordPort


class CustomerMyselfInteractor(CustomerMyselfUseCase):
    def __init__(self, record: CustomerMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: CustomerMyselfQuery) -> CustomerMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return CustomerMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 고객(보호자)과 반려동물, 반려동물의 질병을 관리합니다. "
                "경로는 모두 /v1/shops/{shop_id} 아래이고 매 요청마다 매장 소속을 확인합니다. "
                "GET /customers 는 가족 카드 목록입니다(q 검색: 전화 뒷자리·보호자 이름·반려동물 이름·한글 초성, "
                "sort=recent|name, include_passed, cursor, 한 쪽에 30 가족). "
                "GET /customers/lookup?phone= 는 등록 전 번호 조회, POST /customers 는 보호자와 첫 반려동물 등록, "
                "GET·PUT·DELETE /customers/{customer_id} 는 고객 상세·수정·삭제, "
                "POST /customers/{customer_id}/pets 는 반려동물 추가입니다. "
                "GET·PUT·DELETE /pets/{pet_id} 는 반려동물 상세·수정·삭제, "
                "POST·DELETE /pets/{pet_id}/passed-away 는 무지개다리 표시와 되돌리기, "
                "GET /pet-condition-types 는 정해진 질병 종류입니다. "
                "등록·수정은 customer:write(사장·직원), 고객 삭제는 customer:delete(사장)가 필요합니다. "
                "전화번호는 숫자만 저장하고 매장 안에서 살아 있는 고객끼리 겹치지 않습니다(겹치면 409). "
                "목록과 반려동물 상세의 번호는 가리고, 전체 번호는 고객 상세에서만 줍니다. "
                "고객 삭제는 이름·전화·메모와 반려동물 이름·메모·질병을 지우는 익명화이고, "
                "삭제한 고객은 조회·검색·번호 조회에서 없는 것으로 봅니다. "
                "반려동물은 질병을 하나 이상 고르거나 '질병 없음'을 직접 확인해야 저장됩니다. "
                "다른 매장의 고객·반려동물 ID 는 404 입니다."
            ),
        )
```

`backend/apps/customer/dependencies/customer_myself_provider.py`:
```python
from __future__ import annotations

from customer.adapter.outbound.log_customer_myself_record_adapter import (
    LogCustomerMyselfRecordAdapter,
)
from customer.app.ports.input.customer_myself_use_case import CustomerMyselfUseCase
from customer.app.use_cases.customer_myself_interactor import CustomerMyselfInteractor


def get_customer_myself_use_case() -> CustomerMyselfUseCase:
    return CustomerMyselfInteractor(record=LogCustomerMyselfRecordAdapter())
```

`backend/apps/customer/adapter/inbound/api/schemas/customer_myself_schema.py`:
```python
from pydantic import BaseModel


class CustomerMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/customer/adapter/inbound/api/v1/customer_myself_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.customer_myself_schema import CustomerMyselfResponseSchema
from customer.app.dtos.customer_myself_dto import CustomerMyselfQuery
from customer.app.ports.input.customer_myself_use_case import CustomerMyselfUseCase
from customer.dependencies.customer_myself_provider import get_customer_myself_use_case

customer_myself_router = APIRouter(prefix="/v1/shops", tags=["customers"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@customer_myself_router.get(
    "/{shop_id}/customers/myself", response_model=CustomerMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: CustomerMyselfUseCase = Depends(get_customer_myself_use_case),
) -> CustomerMyselfResponseSchema:
    result = await use_case.introduce_myself(CustomerMyselfQuery(id=4, name="고객 (customer)"))
    return CustomerMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
```



- [ ] **Step 4: API 프로세스에 붙인다**

`backend/main.py`에 세 곳을 고친다.

(1) import — `from platform_admin.adapter.inbound.api.error_map …` 줄 바로 위(customer import 묶음, 모듈 경로 순)에 더한다.
```python
from customer.adapter.inbound.api.error_map import CUSTOMER_ERROR_STATUS
from customer.adapter.inbound.api.v1.customer_myself_router import customer_myself_router
from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
from customer.adapter.inbound.api.v1.get_pet_router import get_pet_router
from customer.adapter.inbound.api.v1.list_pet_condition_types_router import (
    list_pet_condition_types_router,
)
```

(2) 라우터 — `app.include_router(create_shop_router)` 바로 아래에 더한다. 뒤 작업들은 이 묶음의 끝(`install_error_handlers(` 바로 위)에 줄을 더한다. **`/customers/myself`와 `/customers/lookup`은 `/customers/{customer_id}`보다 먼저 붙여야 한다**(C16).
```python
# customer — /customers/myself 와 /customers/lookup 은 /customers/{customer_id} 보다 먼저 붙인다.
# 늦게 붙이면 {customer_id} 가 먼저 걸려 정수 변환 실패(422)가 된다.
app.include_router(customer_myself_router)
app.include_router(get_customer_router)
app.include_router(get_pet_router)
app.include_router(list_pet_condition_types_router)
```

(3) 오류 처리기에 customer 오류 표를 더한다.
```diff
 install_error_handlers(
-    app, {**AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS}
+    app,
+    {
+        **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
+        **CUSTOMER_ERROR_STATUS,
+    },
 )
```

`tests/test_hub_port_binding.py`의 `test_API_프로세스에는_빈_자리도_빠진_가드도_없다`가 새 경로 넷이 모두 `get_shop_context`를 거치는지 본다.


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_get_customer_interactor.py apps/customer/tests/adapter/test_get_customer_router.py apps/customer/tests/app/use_cases/test_get_pet_interactor.py apps/customer/tests/adapter/test_get_pet_router.py apps/customer/tests/app/use_cases/test_list_pet_condition_types_interactor.py apps/customer/tests/adapter/test_list_pet_condition_types_router.py apps/customer/tests/app/use_cases/test_customer_myself_interactor.py apps/customer/tests/adapter/test_customer_myself_router.py -q -p no:cacheprovider`
Expected: `13 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `353 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app backend/apps/customer/adapter backend/apps/customer/dependencies backend/apps/customer/tests backend/main.py
git commit -m "feat(customer): 공용 부품과 조회 슬라이스 — 고객·반려동물 상세, 질병 종류, 자기소개"
```

---

### Task 8: 등록과 번호 조회 — `POST /customers`, `GET /customers/lookup`

등록 3단계의 서버 몫이다. 번호 조회는 살아 있는 고객 중 이 번호가 있으면 `{customer_id, name, pet_names}`(무지개다리 아이 제외 — 새로 정한 것 10번), 없으면 404. 등록은 두 폼을 **쓰기 전에** 모두 검증하고(C8·C21), 보호자와 첫 반려동물을 한 트랜잭션으로 넣고, 검색 줄을 만든다. 번호 중복은 유일 색인이 막는다(C2 — 동시 경합은 Task 15). 폼 스키마의 `to_input()`이 앞뒤 공백·빈 문자열을 정리하고, 불리언은 `StrictBool`이라 문자열 `"true"`를 받지 않는다(C18). 반려동물 폼 스키마(`PetFieldsSchema`)는 Task 11 이 재사용한다.

**Files:**
- Create: `backend/apps/customer/app/dtos/customer_input_dto.py`
- Create: `backend/apps/customer/app/dtos/register_customer_dto.py`
- Create: `backend/apps/customer/app/ports/input/register_customer_use_case.py`
- Create: `backend/apps/customer/app/use_cases/register_customer_interactor.py`
- Create: `backend/apps/customer/dependencies/register_customer_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/register_customer_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/register_customer_router.py`
- Create: `backend/apps/customer/app/dtos/lookup_customer_dto.py`
- Create: `backend/apps/customer/app/ports/input/lookup_customer_use_case.py`
- Create: `backend/apps/customer/app/use_cases/lookup_customer_interactor.py`
- Create: `backend/apps/customer/dependencies/lookup_customer_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/lookup_customer_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/lookup_customer_router.py`
- Modify: `backend/main.py`
- Create: `backend/apps/customer/tests/helpers/inputs.py` (테스트 도우미)
- Modify: `backend/apps/customer/tests/helpers/api.py` (끝에 폼 본문 예시를 더한다)
- Test: `backend/apps/customer/tests/app/use_cases/test_register_customer_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_register_customer_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_lookup_customer_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_lookup_customer_router.py`

**Interfaces:**
- Consumes: Task 7 의 공용 부품·스텁·`CustomerDetailSchema`, Task 3 의 값 객체, Task 5·6 의 포트
- Produces:
  - `customer.app.dtos.customer_input_dto`: `CustomerInput(name, phone, phone_alt, marketing_consent, memo)` + `to_profile() -> CustomerProfile`, `PetInput(name, species, breed, sex, neutered, birth_date, birth_year, weight_kg, no_known_conditions, memo, conditions: tuple[ConditionEntry, ...])` + `to_profile(known_condition_codes, today) -> PetProfile`
  - 스키마 `register_customer_schema`: `CustomerFieldsSchema`(+`to_input()`), `ConditionSchema`, `PetFieldsSchema`(+`to_input()`), `RegisterCustomerRequestSchema(customer, pet)`
  - `RegisterCustomerUseCase.register_customer(RegisterCustomerCommand(ctx, customer: CustomerInput, pet: PetInput)) -> CustomerDetailView`
  - `LookupCustomerUseCase.lookup_customer(LookupCustomerQuery(ctx, phone)) -> LookupCustomerResult(customer_id, name, pet_names)`
  - 테스트 도우미 `customer.tests.helpers.inputs`: `customer_input(**overrides)`, `pet_input(**overrides)`; `api.CUSTOMER_BODY`, `api.PET_BODY`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/helpers/inputs.py`:
```python
"""customer 인터랙터 테스트가 함께 쓰는 폼 입력 — 라우터가 스키마에서 바꿔 넣는 모양 그대로다."""
from __future__ import annotations

from decimal import Decimal

from customer.app.dtos.customer_input_dto import CustomerInput, PetInput


def customer_input(**overrides) -> CustomerInput:
    fields = dict(name="김민지", phone="010-1234-5678", phone_alt=None, marketing_consent=False,
                  memo=None)
    fields.update(overrides)
    return CustomerInput(**fields)


def pet_input(**overrides) -> PetInput:
    fields = dict(
        name="콩이", species="dog", breed="말티즈", sex="female", neutered=True, birth_date=None,
        birth_year=2021, weight_kg=Decimal("3.2"), no_known_conditions=True, memo=None,
        conditions=(),
    )
    fields.update(overrides)
    return PetInput(**fields)
```

`backend/apps/customer/tests/helpers/api.py` 끝에 더한다.
```python
# 폼 본문 예시 — 앞뒤 공백과 빈 문자열을 일부러 넣었다(라우터가 없애고 None 으로 바꾸는지 본다).
CUSTOMER_BODY = {"name": " 김민지 ", "phone": "010-1234-5678", "phone_alt": "", "marketing_consent": True,
                 "memo": ""}
PET_BODY = {
    "name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": False,
    "conditions": [{"type_code": "other", "custom_label": " 눈물 자국 ", "note": ""}], "memo": "",
}
```

`backend/apps/customer/tests/app/use_cases/test_register_customer_interactor.py`:
```python
import pytest

from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.use_cases.register_customer_interactor import RegisterCustomerInteractor
from customer.domain.errors import CustomerInputError, CustomerPhoneTakenError, PetHealthRequiredError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.inputs import customer_input, pet_input
from customer.tests.helpers.profiles import condition, ctx


def _interactor():
    journal, customers, pets, types, search = family()
    return journal, customers, RegisterCustomerInteractor(customers, pets, types, search, today)


async def test_보호자와_첫_반려동물을_넣고_검색_줄을_만든_뒤_상세를_돌려준다():
    journal, _, interactor = _interactor()
    view = await interactor.register_customer(RegisterCustomerCommand(
        ctx=ctx(), customer=customer_input(),
        pet=pet_input(no_known_conditions=False, conditions=(condition("allergy", note="닭고기"),)),
    ))
    assert view.customer.phone == "01012345678"   # 숫자만 저장한다
    assert [(p.name, p.age_label, p.has_conditions) for p in view.pets] == [("콩이", "5살", True)]
    assert journal == [("create_customer", 1), ("add_pet", 1), ("rebuild", 1)]


async def test_반려동물_폼이_틀리면_아무것도_쓰지_않는다():
    journal, customers, interactor = _interactor()
    with pytest.raises(PetHealthRequiredError):
        await interactor.register_customer(RegisterCustomerCommand(
            ctx=ctx(), customer=customer_input(), pet=pet_input(no_known_conditions=False),
        ))
    with pytest.raises(CustomerInputError):
        await interactor.register_customer(RegisterCustomerCommand(
            ctx=ctx(), customer=customer_input(phone="12"), pet=pet_input(),
        ))
    assert journal == [] and customers.rows == {}


async def test_번호가_겹치면_CUSTOMER_PHONE_TAKEN_이다():
    journal, customers, interactor = _interactor()
    customers.seed(phone="01012345678")
    with pytest.raises(CustomerPhoneTakenError):
        await interactor.register_customer(RegisterCustomerCommand(
            ctx=ctx(), customer=customer_input(), pet=pet_input(),
        ))
    assert journal == []
```

`backend/apps/customer/tests/adapter/test_register_customer_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.register_customer_router import register_customer_router
from customer.dependencies.register_customer_provider import get_register_customer_use_case
from customer.tests.helpers.api import (
    CUSTOMER_BODY,
    NO_WRITE,
    PET_BODY,
    STAFF,
    build_app,
    customer_detail_view,
)


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def register_customer(self, command):
        self.commands.append(command)
        return customer_detail_view()


async def _post(stub, body, access=None):
    app = build_app(register_customer_router, get_register_customer_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/customers", json=body)


async def test_직원도_등록하고_201_과_고객_상세를_받는다():
    stub = _StubUseCase()
    response = await _post(stub, {"customer": CUSTOMER_BODY, "pet": PET_BODY}, access=STAFF)
    assert response.status_code == 201
    assert response.json()["customer"]["phone"] == "01012345678"
    assert response.json()["pets"][0]["weight_kg"] == 3.2   # 문자열이 아니라 숫자로 나간다
    command = stub.commands[0]
    assert command.ctx.shop_id == 3
    # 앞뒤 공백을 없애고 빈 문자열은 None 으로 바꾼다. 전화번호 정규화는 유스케이스가 한다.
    assert (command.customer.name, command.customer.phone, command.customer.phone_alt,
            command.customer.memo) == ("김민지", "010-1234-5678", None, None)
    assert command.pet.conditions[0].custom_label == "눈물 자국"
    assert command.pet.conditions[0].note is None


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _post(stub, {"customer": CUSTOMER_BODY, "pet": PET_BODY}, access=NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []


async def test_형식이_틀리면_422_VALIDATION_ERROR_다():
    cases = [
        {"customer": CUSTOMER_BODY},                                                    # 반려동물 없음
        {"customer": {**CUSTOMER_BODY, "name": "  "}, "pet": PET_BODY},                 # 빈 이름
        {"customer": {**CUSTOMER_BODY, "marketing_consent": "true"}, "pet": PET_BODY},  # 문자열 불리언
        {"customer": {**CUSTOMER_BODY, "marketing_consent": None}, "pet": PET_BODY},    # 동의는 필수 선택
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "species": "bird"}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "sex": "unknown"}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "weight_kg": 0}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "weight_kg": 3.25}},           # 소수 한 자리
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "weight_kg": 1000}},           # numeric(4,1)
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "name": "가" * 51}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "memo": "가" * 501}},
        {"customer": CUSTOMER_BODY, "pet": {**PET_BODY, "conditions": [{"type_code": "other", "custom_label": "가" * 31}]}},
    ]
    for body in cases:
        response = await _post(_StubUseCase(), body)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR"), body
```

`backend/apps/customer/tests/app/use_cases/test_lookup_customer_interactor.py`:
```python
import pytest

from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery
from customer.app.use_cases.lookup_customer_interactor import LookupCustomerInteractor
from customer.domain.errors import CustomerInputError, CustomerNotFoundError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx


async def test_하이픈을_넣은_번호로도_찾고_살아_있는_아이_이름만_준다():
    _, customers, pets, _, _ = family()
    customer = customers.seed(phone="01012345678")
    pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "두부")
    pets.seed(customer.id, "별이", passed_away=True)
    result = await LookupCustomerInteractor(customers, pets).lookup_customer(
        LookupCustomerQuery(ctx=ctx(), phone="010-1234-5678")
    )
    assert (result.customer_id, result.name, result.pet_names) == (customer.id, "김민지", ["콩이", "두부"])


async def test_없거나_다른_매장이면_CUSTOMER_NOT_FOUND_다():
    _, customers, pets, _, _ = family()
    customers.seed(shop_id=2, phone="01012345678")
    with pytest.raises(CustomerNotFoundError):
        await LookupCustomerInteractor(customers, pets).lookup_customer(
            LookupCustomerQuery(ctx=ctx(shop_id=1), phone="01012345678")
        )


async def test_번호_형식이_아니면_VALIDATION_ERROR_다():
    _, customers, pets, _, _ = family()
    with pytest.raises(CustomerInputError):
        await LookupCustomerInteractor(customers, pets).lookup_customer(
            LookupCustomerQuery(ctx=ctx(), phone="5678")
        )
```

`backend/apps/customer/tests/adapter/test_lookup_customer_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.lookup_customer_router import lookup_customer_router
from customer.app.dtos.lookup_customer_dto import LookupCustomerResult
from customer.dependencies.lookup_customer_provider import get_lookup_customer_use_case
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.api import NO_WRITE, build_app


class _StubUseCase:
    def __init__(self, found=True):
        self.found = found
        self.queries = []

    async def lookup_customer(self, query):
        self.queries.append(query)
        if not self.found:
            raise CustomerNotFoundError("이 번호로 등록된 고객이 없습니다.")
        return LookupCustomerResult(customer_id=1, name="김민지", pet_names=["콩이", "두부"])


async def _get(stub, path):
    app = build_app(lookup_customer_router, get_lookup_customer_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_멤버는_번호로_조회한다():
    stub = _StubUseCase()
    response = await _get(stub, "/v1/shops/3/customers/lookup?phone=010-1234-5678")
    assert response.json() == {"customer_id": 1, "name": "김민지", "pet_names": ["콩이", "두부"]}
    assert stub.queries[0].phone == "010-1234-5678"


async def test_없으면_404_CUSTOMER_NOT_FOUND_다():
    stub = _StubUseCase(found=False)
    response = await _get(stub, "/v1/shops/3/customers/lookup?phone=01012345678")
    assert (response.status_code, response.json()["code"]) == (404, "CUSTOMER_NOT_FOUND")


async def test_번호가_없으면_422_다():
    response = await _get(_StubUseCase(), "/v1/shops/3/customers/lookup")
    assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_register_customer_interactor.py apps/customer/tests/adapter/test_register_customer_router.py apps/customer/tests/app/use_cases/test_lookup_customer_interactor.py apps/customer/tests/adapter/test_lookup_customer_router.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.app.use_cases.register_customer_interactor'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/customer_input_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from customer.domain.value_objects.condition_entry import ConditionEntry
from customer.domain.value_objects.customer_profile import CustomerProfile
from customer.domain.value_objects.pet_profile import PetProfile


@dataclass(frozen=True)
class CustomerInput:
    """보호자 폼 전체. 문자열은 앞뒤 공백을 없앴고 빈 값은 None 이다(라우터가 바꿔 넣는다)."""

    name: str
    phone: str
    phone_alt: str | None
    marketing_consent: bool
    memo: str | None

    def to_profile(self) -> CustomerProfile:
        return CustomerProfile.create(
            name=self.name, phone=self.phone, phone_alt=self.phone_alt,
            marketing_consent=self.marketing_consent, memo=self.memo,
        )


@dataclass(frozen=True)
class PetInput:
    """반려동물 폼 전체. 질병 목록은 통째로 온다."""

    name: str
    species: str
    breed: str
    sex: str
    neutered: bool
    birth_date: date | None
    birth_year: int | None
    weight_kg: Decimal
    no_known_conditions: bool
    memo: str | None
    conditions: tuple[ConditionEntry, ...]

    def to_profile(self, known_condition_codes: frozenset[str], today: date) -> PetProfile:
        return PetProfile.create(
            name=self.name, species=self.species, breed=self.breed, sex=self.sex,
            neutered=self.neutered, birth_date=self.birth_date, birth_year=self.birth_year,
            weight_kg=self.weight_kg, no_known_conditions=self.no_known_conditions,
            memo=self.memo, conditions=self.conditions,
            known_condition_codes=known_condition_codes, today=today,
        )
```

`backend/apps/customer/app/dtos/register_customer_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import CustomerInput, PetInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class RegisterCustomerCommand:
    """보호자와 첫 반려동물을 한 번에 등록한다."""

    ctx: ShopContext
    customer: CustomerInput
    pet: PetInput
```

`backend/apps/customer/app/ports/input/register_customer_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand


class RegisterCustomerUseCase(ABC):
    @abstractmethod
    async def register_customer(self, command: RegisterCustomerCommand) -> CustomerDetailView: ...
```

`backend/apps/customer/app/use_cases/register_customer_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class RegisterCustomerInteractor(RegisterCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today

    async def register_customer(self, command: RegisterCustomerCommand) -> CustomerDetailView:
        # 쓰기 전에 두 폼을 모두 검증한다. 번호 중복은 유일 색인이 막는다(동시에 두 번 와도 하나만 성공).
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        customer_profile = command.customer.to_profile()
        pet_profile = command.pet.to_profile(codes, self._today())
        customer = await self._customers.create(command.ctx, customer_profile)
        await self._pets.add(command.ctx, customer.id, pet_profile)
        await self._search.rebuild_search_entry(command.ctx, customer.id)
        return await read_customer_detail(
            command.ctx, customer.id, self._customers, self._pets, self._today()
        )
```

`backend/apps/customer/dependencies/register_customer_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.app.use_cases.register_customer_interactor import RegisterCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository,
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_register_customer_use_case(db: DbSession) -> RegisterCustomerUseCase:
    return RegisterCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), search=build_customer_search(db),
        today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/register_customer_schema.py`:
```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StrictBool, StringConstraints

from customer.app.dtos.customer_input_dto import CustomerInput, PetInput
from customer.domain.value_objects.condition_entry import ConditionEntry

Required50 = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]

# 앞뒤 공백을 없앤 선택 문자열. 빈 문자열은 to_input 이 None 으로 바꾼다.
Optional20 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=20)] | None
Optional30 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=30)] | None
Optional100 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)] | None
Optional500 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=500)] | None


class CustomerFieldsSchema(BaseModel):
    """보호자 폼. 전화번호는 하이픈을 넣어 보내도 되고, 서버가 숫자만 남겨 검증한다."""

    name: Required50
    phone: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
    phone_alt: Optional20 = None
    marketing_consent: StrictBool
    memo: Optional500 = None

    def to_input(self) -> CustomerInput:
        return CustomerInput(
            name=self.name, phone=self.phone, phone_alt=self.phone_alt or None,
            marketing_consent=self.marketing_consent, memo=self.memo or None,
        )


class ConditionSchema(BaseModel):
    type_code: Annotated[str, StringConstraints(min_length=1, max_length=30)]
    custom_label: Optional30 = None
    note: Optional100 = None


class PetFieldsSchema(BaseModel):
    """반려동물 폼. 생일·태어난 해는 하나만(둘 다 없으면 모름), 질병은 목록 전체를 보낸다."""

    name: Required50
    species: Literal["dog", "cat"]
    breed: Required50
    sex: Literal["female", "male"]
    neutered: StrictBool
    birth_date: date | None = None
    birth_year: int | None = None
    weight_kg: Annotated[Decimal, Field(gt=0, max_digits=4, decimal_places=1)]
    no_known_conditions: StrictBool
    conditions: Annotated[list[ConditionSchema], Field(max_length=20)] = []
    memo: Optional500 = None

    def to_input(self) -> PetInput:
        return PetInput(
            name=self.name, species=self.species, breed=self.breed, sex=self.sex,
            neutered=self.neutered, birth_date=self.birth_date, birth_year=self.birth_year,
            weight_kg=self.weight_kg, no_known_conditions=self.no_known_conditions,
            memo=self.memo or None,
            conditions=tuple(
                ConditionEntry(type_code=c.type_code, custom_label=c.custom_label or None,
                               note=c.note or None)
                for c in self.conditions
            ),
        )


class RegisterCustomerRequestSchema(BaseModel):
    customer: CustomerFieldsSchema
    pet: PetFieldsSchema
```

`backend/apps/customer/adapter/inbound/api/v1/register_customer_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.adapter.inbound.api.schemas.register_customer_schema import (
    RegisterCustomerRequestSchema,
)
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.ports.input.register_customer_use_case import RegisterCustomerUseCase
from customer.dependencies.register_customer_provider import get_register_customer_use_case
from hub.app.dtos.shop_context import ShopContext

register_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@register_customer_router.post(
    "/{shop_id}/customers", response_model=CustomerDetailSchema, status_code=201
)
async def register_customer(
    body: RegisterCustomerRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: RegisterCustomerUseCase = Depends(get_register_customer_use_case),
) -> CustomerDetailSchema:
    view = await use_case.register_customer(
        RegisterCustomerCommand(ctx=ctx, customer=body.customer.to_input(), pet=body.pet.to_input())
    )
    return CustomerDetailSchema.of(view)
```

`backend/apps/customer/app/dtos/lookup_customer_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class LookupCustomerQuery:
    ctx: ShopContext
    phone: str


@dataclass(frozen=True)
class LookupCustomerResult:
    """등록 1단계에서 '이미 등록된 번호예요 — 김민지(콩이, 두부)'를 보여 줄 만큼만. 번호는 담지 않는다."""

    customer_id: int
    name: str
    pet_names: list[str]
```

`backend/apps/customer/app/ports/input/lookup_customer_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery, LookupCustomerResult


class LookupCustomerUseCase(ABC):
    @abstractmethod
    async def lookup_customer(self, query: LookupCustomerQuery) -> LookupCustomerResult: ...
```

`backend/apps/customer/app/use_cases/lookup_customer_interactor.py`:
```python
from __future__ import annotations

from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery, LookupCustomerResult
from customer.app.ports.input.lookup_customer_use_case import LookupCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import CustomerNotFoundError
from customer.domain.services.phone_number import normalize_phone


class LookupCustomerInteractor(LookupCustomerUseCase):
    def __init__(self, customers: CustomerRepository, pets: PetRepository) -> None:
        self._customers = customers
        self._pets = pets

    async def lookup_customer(self, query: LookupCustomerQuery) -> LookupCustomerResult:
        customer = await self._customers.find_active_by_phone(query.ctx, normalize_phone(query.phone))
        if customer is None:
            raise CustomerNotFoundError("이 번호로 등록된 고객이 없습니다.")
        family = await self._pets.list_for_customers(query.ctx, [customer.id])
        return LookupCustomerResult(
            customer_id=customer.id,
            name=customer.name,
            pet_names=[pet.name for pet in family if not pet.passed_away],
        )
```

`backend/apps/customer/dependencies/lookup_customer_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.lookup_customer_use_case import LookupCustomerUseCase
from customer.app.use_cases.lookup_customer_interactor import LookupCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_pet_repository,
)


def get_lookup_customer_use_case(db: DbSession) -> LookupCustomerUseCase:
    return LookupCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/lookup_customer_schema.py`:
```python
from pydantic import BaseModel


class LookupCustomerResponseSchema(BaseModel):
    customer_id: int
    name: str
    pet_names: list[str]
```

`backend/apps/customer/adapter/inbound/api/v1/lookup_customer_router.py`:
```python
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.lookup_customer_schema import (
    LookupCustomerResponseSchema,
)
from customer.app.dtos.lookup_customer_dto import LookupCustomerQuery
from customer.app.ports.input.lookup_customer_use_case import LookupCustomerUseCase
from customer.dependencies.lookup_customer_provider import get_lookup_customer_use_case
from hub.app.dtos.shop_context import ShopContext

lookup_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@lookup_customer_router.get("/{shop_id}/customers/lookup", response_model=LookupCustomerResponseSchema)
async def lookup_customer(
    phone: Annotated[str, Query(min_length=1, max_length=20)],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: LookupCustomerUseCase = Depends(get_lookup_customer_use_case),
) -> LookupCustomerResponseSchema:
    result = await use_case.lookup_customer(LookupCustomerQuery(ctx=ctx, phone=phone))
    return LookupCustomerResponseSchema(
        customer_id=result.customer_id, name=result.name, pet_names=result.pet_names
    )
```



- [ ] **Step 4: API 프로세스에 붙인다**

`backend/main.py` — customer import 묶음(모듈 경로 순 자리)에 더한다.
```python
from customer.adapter.inbound.api.v1.lookup_customer_router import lookup_customer_router
from customer.adapter.inbound.api.v1.register_customer_router import register_customer_router
```

라우터 줄은 두 곳이다. `lookup_customer_router`는 **`app.include_router(customer_myself_router)` 바로 아래**에(`{customer_id}` 보다 먼저 — C16), `register_customer_router`는 묶음의 끝에 더한다.
```python
app.include_router(lookup_customer_router)
app.include_router(register_customer_router)
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_register_customer_interactor.py apps/customer/tests/adapter/test_register_customer_router.py apps/customer/tests/app/use_cases/test_lookup_customer_interactor.py apps/customer/tests/adapter/test_lookup_customer_router.py -q -p no:cacheprovider`
Expected: `12 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `365 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app backend/apps/customer/adapter backend/apps/customer/dependencies backend/apps/customer/tests backend/main.py
git commit -m "feat(customer): 고객 등록과 번호 조회"
```

---

### Task 9: 보호자 수정과 고객 삭제(익명화) — `PUT`·`DELETE /customers/{customer_id}`

둘 다 맨 앞에서 고객 행을 잠근다(`lock_active` — 새로 정한 것 1번). 수정은 번호를 바꿀 수 있고 겹치면 409, 마케팅 동의 값이 바뀔 때만 동의 시각을 새로 찍는다(설계 7.1). 삭제는 사장만(`customer:delete`, C4)이고, 개인정보만 지우는 익명화 뒤 검색 줄을 지운다(C6). 폼이 틀리면 잠그기 전에 막는다.

**Files:**
- Create: `backend/apps/customer/app/dtos/update_customer_dto.py`
- Create: `backend/apps/customer/app/ports/input/update_customer_use_case.py`
- Create: `backend/apps/customer/app/use_cases/update_customer_interactor.py`
- Create: `backend/apps/customer/dependencies/update_customer_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/update_customer_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/update_customer_router.py`
- Create: `backend/apps/customer/app/dtos/delete_customer_dto.py`
- Create: `backend/apps/customer/app/ports/input/delete_customer_use_case.py`
- Create: `backend/apps/customer/app/use_cases/delete_customer_interactor.py`
- Create: `backend/apps/customer/dependencies/delete_customer_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/delete_customer_router.py`
- Modify: `backend/main.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_update_customer_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_update_customer_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_delete_customer_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_delete_customer_router.py`

**Interfaces:**
- Consumes: Task 8 의 `CustomerFieldsSchema`·`CustomerInput`, Task 7 의 공용 부품, Task 5 의 `lock_active`·`update`·`anonymize`, Task 6 의 `rebuild_search_entry`
- Produces:
  - `UpdateCustomerUseCase.update_customer(UpdateCustomerCommand(ctx, customer_id, customer: CustomerInput)) -> CustomerDetailView`, 스키마 `UpdateCustomerRequestSchema(CustomerFieldsSchema)`
  - `DeleteCustomerUseCase.delete_customer(DeleteCustomerCommand(ctx, customer_id)) -> None`(라우터는 204)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/app/use_cases/test_update_customer_interactor.py`:
```python
import pytest

from customer.app.dtos.update_customer_dto import UpdateCustomerCommand
from customer.app.use_cases.update_customer_interactor import UpdateCustomerInteractor
from customer.domain.errors import CustomerInputError, CustomerNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.inputs import customer_input
from customer.tests.helpers.profiles import ctx


def _setup(consent=False):
    journal, customers, pets, _, search = family()
    customer = customers.seed(consent=consent)
    pets.seed(customer.id)
    return journal, customer, UpdateCustomerInteractor(customers, pets, search, today)


async def test_잠근_뒤_고치고_검색_줄을_다시_만든다():
    journal, customer, interactor = _setup()
    view = await interactor.update_customer(UpdateCustomerCommand(
        ctx=ctx(), customer_id=customer.id, customer=customer_input(name="김민지(콩이 엄마)"),
    ))
    assert view.customer.name == "김민지(콩이 엄마)"
    assert journal == [("lock_customer", customer.id), ("update_customer", customer.id, False),
                       ("rebuild", customer.id)]


async def test_동의가_바뀔_때만_동의_시각을_바꾸라고_한다():
    journal, customer, interactor = _setup(consent=False)
    await interactor.update_customer(UpdateCustomerCommand(
        ctx=ctx(), customer_id=customer.id, customer=customer_input(marketing_consent=True),
    ))
    assert ("update_customer", customer.id, True) in journal


async def test_다른_매장이면_404_이고_아무것도_쓰지_않는다():
    journal, customer, interactor = _setup()
    with pytest.raises(CustomerNotFoundError):
        await interactor.update_customer(UpdateCustomerCommand(
            ctx=ctx(shop_id=2), customer_id=customer.id, customer=customer_input(),
        ))
    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_번호_형식이_틀리면_잠그기_전에_막는다():
    journal, customer, interactor = _setup()
    with pytest.raises(CustomerInputError):
        await interactor.update_customer(UpdateCustomerCommand(
            ctx=ctx(), customer_id=customer.id, customer=customer_input(phone="12"),
        ))
    assert journal == []
```

`backend/apps/customer/tests/adapter/test_update_customer_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
from customer.dependencies.update_customer_provider import get_update_customer_use_case
from customer.tests.helpers.api import CUSTOMER_BODY, NO_WRITE, STAFF, build_app, customer_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def update_customer(self, command):
        self.commands.append(command)
        return customer_detail_view()


async def _put(stub, body, access):
    app = build_app(update_customer_router, get_update_customer_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.put("/v1/shops/3/customers/1", json=body)


async def test_직원도_보호자를_고친다():
    stub = _StubUseCase()
    response = await _put(stub, CUSTOMER_BODY, STAFF)
    assert response.status_code == 200
    command = stub.commands[0]
    assert (command.customer_id, command.customer.name, command.customer.marketing_consent) == (1, "김민지", True)


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _put(stub, CUSTOMER_BODY, NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []
```

`backend/apps/customer/tests/app/use_cases/test_delete_customer_interactor.py`:
```python
import pytest

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.domain.errors import CustomerNotFoundError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx


async def test_잠근_뒤_익명화하고_검색_줄을_정리한다():
    journal, customers, _, _, search = family()
    customer = customers.seed()
    await DeleteCustomerInteractor(customers, search).delete_customer(
        DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
    )
    assert journal == [("lock_customer", customer.id), ("anonymize", customer.id), ("rebuild", customer.id)]


async def test_이미_삭제했거나_다른_매장이면_404_다():
    journal, customers, _, _, search = family()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await DeleteCustomerInteractor(customers, search).delete_customer(
            DeleteCustomerCommand(ctx=ctx(shop_id=1), customer_id=customer.id)
        )
    assert [entry[0] for entry in journal] == ["lock_customer"]
```

`backend/apps/customer/tests/adapter/test_delete_customer_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.delete_customer_router import delete_customer_router
from customer.dependencies.delete_customer_provider import get_delete_customer_use_case
from customer.tests.helpers.api import STAFF, build_app


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def delete_customer(self, command):
        self.commands.append(command)


async def _delete(stub, access=None):
    app = build_app(delete_customer_router, get_delete_customer_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/customers/1")


async def test_사장은_고객을_삭제하고_204_를_받는다():
    stub = _StubUseCase()
    response = await _delete(stub)
    assert response.status_code == 204
    assert (stub.commands[0].ctx.shop_id, stub.commands[0].customer_id) == (3, 1)


async def test_직원은_고객을_삭제하지_못한다():
    stub = _StubUseCase()
    response = await _delete(stub, access=STAFF)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_update_customer_interactor.py apps/customer/tests/adapter/test_update_customer_router.py apps/customer/tests/app/use_cases/test_delete_customer_interactor.py apps/customer/tests/adapter/test_delete_customer_router.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.app.use_cases.update_customer_interactor'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/update_customer_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import CustomerInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateCustomerCommand:
    ctx: ShopContext
    customer_id: int
    customer: CustomerInput
```

`backend/apps/customer/app/ports/input/update_customer_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.update_customer_dto import UpdateCustomerCommand


class UpdateCustomerUseCase(ABC):
    @abstractmethod
    async def update_customer(self, command: UpdateCustomerCommand) -> CustomerDetailView: ...
```

`backend/apps/customer/app/use_cases/update_customer_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import CustomerDetailView
from customer.app.dtos.update_customer_dto import UpdateCustomerCommand
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_customer_detail


class UpdateCustomerInteractor(UpdateCustomerUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def update_customer(self, command: UpdateCustomerCommand) -> CustomerDetailView:
        profile = command.customer.to_profile()
        # 고객 행을 잠근 뒤 다시 읽는다. 익명화와 겹치면 익명화가 끝난 뒤 404 가 된다.
        current = await self._customers.lock_active(command.ctx, command.customer_id)
        await self._customers.update(
            command.ctx, command.customer_id, profile,
            consent_changed=current.marketing_consent != profile.marketing_consent,
        )
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)
        return await read_customer_detail(
            command.ctx, command.customer_id, self._customers, self._pets, self._today()
        )
```

`backend/apps/customer/dependencies/update_customer_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.app.use_cases.update_customer_interactor import UpdateCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_update_customer_use_case(db: DbSession) -> UpdateCustomerUseCase:
    return UpdateCustomerInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/update_customer_schema.py`:
```python
from customer.adapter.inbound.api.schemas.register_customer_schema import CustomerFieldsSchema


class UpdateCustomerRequestSchema(CustomerFieldsSchema):
    """보호자 폼 전체를 보낸다(PUT). 번호를 바꿀 수 있고, 겹치면 409 다."""
```

`backend/apps/customer/adapter/inbound/api/v1/update_customer_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
from customer.adapter.inbound.api.schemas.update_customer_schema import UpdateCustomerRequestSchema
from customer.app.dtos.update_customer_dto import UpdateCustomerCommand
from customer.app.ports.input.update_customer_use_case import UpdateCustomerUseCase
from customer.dependencies.update_customer_provider import get_update_customer_use_case
from hub.app.dtos.shop_context import ShopContext

update_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@update_customer_router.put("/{shop_id}/customers/{customer_id}", response_model=CustomerDetailSchema)
async def update_customer(
    customer_id: CustomerId,
    body: UpdateCustomerRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: UpdateCustomerUseCase = Depends(get_update_customer_use_case),
) -> CustomerDetailSchema:
    view = await use_case.update_customer(
        UpdateCustomerCommand(ctx=ctx, customer_id=customer_id, customer=body.to_input())
    )
    return CustomerDetailSchema.of(view)
```

`backend/apps/customer/app/dtos/delete_customer_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class DeleteCustomerCommand:
    ctx: ShopContext
    customer_id: int
```

`backend/apps/customer/app/ports/input/delete_customer_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand


class DeleteCustomerUseCase(ABC):
    @abstractmethod
    async def delete_customer(self, command: DeleteCustomerCommand) -> None: ...
```

`backend/apps/customer/app/use_cases/delete_customer_interactor.py`:
```python
from __future__ import annotations

from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort


class DeleteCustomerInteractor(DeleteCustomerUseCase):
    """고객 삭제는 익명화다. 개인정보만 지우고 행은 남긴다(③·④의 기록이 가리킬 틀)."""

    def __init__(self, customers: CustomerRepository, search: CustomerSearchPort) -> None:
        self._customers = customers
        self._search = search

    async def delete_customer(self, command: DeleteCustomerCommand) -> None:
        await self._customers.lock_active(command.ctx, command.customer_id)
        await self._customers.anonymize(command.ctx, command.customer_id)
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)   # 익명화한 고객이라 줄이 지워진다
```

`backend/apps/customer/dependencies/delete_customer_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
)


def get_delete_customer_use_case(db: DbSession) -> DeleteCustomerUseCase:
    return DeleteCustomerInteractor(
        customers=build_customer_repository(db), search=build_customer_search(db),
    )
```

`backend/apps/customer/adapter/inbound/api/v1/delete_customer_router.py`:
```python
from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
from customer.dependencies.delete_customer_provider import get_delete_customer_use_case
from hub.app.dtos.shop_context import ShopContext

delete_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@delete_customer_router.delete("/{shop_id}/customers/{customer_id}", status_code=204)
async def delete_customer(
    customer_id: CustomerId,
    ctx: ShopContext = Depends(require_permission("customer:delete")),
    use_case: DeleteCustomerUseCase = Depends(get_delete_customer_use_case),
) -> Response:
    await use_case.delete_customer(DeleteCustomerCommand(ctx=ctx, customer_id=customer_id))
    return Response(status_code=204)
```



- [ ] **Step 4: API 프로세스에 붙인다**

`backend/main.py` — customer import 묶음(모듈 경로 순 자리)에 더한다.
```python
from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
from customer.adapter.inbound.api.v1.delete_customer_router import delete_customer_router
```

customer 라우터 묶음의 끝(`install_error_handlers(` 바로 위)에 더한다.
```python
app.include_router(update_customer_router)
app.include_router(delete_customer_router)
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_update_customer_interactor.py apps/customer/tests/adapter/test_update_customer_router.py apps/customer/tests/app/use_cases/test_delete_customer_interactor.py apps/customer/tests/adapter/test_delete_customer_router.py -q -p no:cacheprovider`
Expected: `10 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `375 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app backend/apps/customer/adapter backend/apps/customer/dependencies backend/apps/customer/tests backend/main.py
git commit -m "feat(customer): 보호자 수정과 고객 익명화 삭제"
```

---

### Task 10: 가족 카드 목록 — `GET /customers?q=&sort=&include_passed=&cursor=`

검색 포트로 가족 ID 를 찾고, 보여 줄 정보는 원본 표에서 읽는다(C11 — 검색 줄에만 있고 원본에 없는 ID 는 버린다). 카드마다 보호자 이름·**가린 번호**(C7)와 반려동물 요약(이름·종류·품종·나이 표시·질병 여부·무지개다리 여부). 기본은 무지개다리 아이를 카드에서 빼고, 반려동물이 모두 무지개다리인 가족도 뺀다(검색 어댑터가 거른다). 응답에 `pet_count`를 싣는다(새로 정한 것 5번). `sort`는 `recent`·`name`만, `q`는 50자까지.

**Files:**
- Create: `backend/apps/customer/app/dtos/list_customers_dto.py`
- Create: `backend/apps/customer/app/ports/input/list_customers_use_case.py`
- Create: `backend/apps/customer/app/use_cases/list_customers_interactor.py`
- Create: `backend/apps/customer/dependencies/list_customers_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/list_customers_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/list_customers_router.py`
- Modify: `backend/main.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_list_customers_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_list_customers_router.py`

**Interfaces:**
- Consumes: Task 6 의 `CustomerSearchPort.search`·`count_pets`·`SearchRequest`, Task 2 의 `parse_query`·`mask_phone`, Task 3 의 `age_label`, Task 5 의 `list_active`·`list_for_customers`
- Produces: `ListCustomersUseCase.list_customers(ListCustomersQuery(ctx, q, sort, include_passed, cursor)) -> CustomerListView(items: list[FamilyCardView], next_cursor, pet_count)`, `FamilyCardView(customer_id, name, phone_masked, pets: list[PetSummaryView])`, `PetSummaryView(pet_id, name, species, breed, age_label, has_conditions, passed_away)`, 스키마 `CustomerListSchema`(+`of`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/app/use_cases/test_list_customers_interactor.py`:
```python
from customer.app.dtos.customer_search_dto import SearchPage
from customer.app.dtos.list_customers_dto import ListCustomersQuery
from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
from customer.domain.entities.pet import PetCondition
from customer.domain.services.search_terms import SearchWord
from customer.tests.helpers.fakes import FakeSearch, family, today
from customer.tests.helpers.profiles import ctx


def _query(**overrides):
    fields = dict(ctx=ctx(), q="5678 콩", sort="name", include_passed=False, cursor="abc")
    fields.update(overrides)
    return ListCustomersQuery(**fields)


def _setup():
    journal, customers, pets, _, _ = family()
    kim = customers.seed(name="김민지", phone="01012345678")
    park = customers.seed(name="박서준", phone="0212345678")
    pets.seed(kim.id, "콩이", conditions=[PetCondition("allergy", "알레르기", None, None)])
    pets.seed(kim.id, "별이", passed_away=True)
    pets.seed(park.id, "보리")
    search = FakeSearch(journal, SearchPage(customer_ids=[park.id, kim.id], next_cursor="next"), pet_count=2)
    return kim, park, search, ListCustomersInteractor(customers, pets, search, today)


async def test_검색_순서대로_가족_카드를_만들고_번호는_가린다():
    kim, park, search, interactor = _setup()
    view = await interactor.list_customers(_query())
    assert [(c.customer_id, c.name, c.phone_masked) for c in view.items] == [
        (park.id, "박서준", "02-12··-5678"), (kim.id, "김민지", "010-12··-5678"),
    ]
    assert [(p.name, p.age_label, p.has_conditions) for p in view.items[1].pets] == [("콩이", "5살", True)]
    assert (view.next_cursor, view.pet_count) == ("next", 2)
    _, request = search.requests[0]
    assert request.words == (SearchWord("last4", "5678"), SearchWord("text", "콩"))
    assert (request.sort, request.include_passed, request.cursor, request.limit) == ("name", False, "abc", 30)


async def test_무지개다리를_포함하면_카드에도_보인다():
    kim, _, _, interactor = _setup()
    view = await interactor.list_customers(_query(include_passed=True))
    card = next(c for c in view.items if c.customer_id == kim.id)
    assert [(p.name, p.passed_away) for p in card.pets] == [("콩이", False), ("별이", True)]


async def test_검색_줄에_있어도_원본에_없는_가족은_빼고_원본을_따른다():
    journal, customers, pets, _, _ = family()
    kim = customers.seed()
    pets.seed(kim.id)
    search = FakeSearch(journal, SearchPage(customer_ids=[999, kim.id], next_cursor=None))
    view = await ListCustomersInteractor(customers, pets, search, today).list_customers(_query())
    assert [c.customer_id for c in view.items] == [kim.id]
```

`backend/apps/customer/tests/adapter/test_list_customers_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.list_customers_router import list_customers_router
from customer.app.dtos.list_customers_dto import CustomerListView, FamilyCardView, PetSummaryView
from customer.dependencies.list_customers_provider import get_list_customers_use_case
from customer.tests.helpers.api import NO_WRITE, build_app


class _StubUseCase:
    def __init__(self):
        self.queries = []

    async def list_customers(self, query):
        self.queries.append(query)
        pet = PetSummaryView(pet_id=101, name="콩이", species="dog", breed="말티즈", age_label="5살",
                             has_conditions=True, passed_away=False)
        card = FamilyCardView(customer_id=1, name="김민지", phone_masked="010-12··-5678", pets=[pet])
        return CustomerListView(items=[card], next_cursor="next", pet_count=1)


async def _get(stub, path):
    app = build_app(list_customers_router, get_list_customers_use_case, stub, access=NO_WRITE)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.get(path)


async def test_멤버는_기본값으로_목록을_본다():
    stub = _StubUseCase()
    response = await _get(stub, "/v1/shops/3/customers")
    assert response.status_code == 200
    body = response.json()
    assert (body["pet_count"], body["next_cursor"]) == (1, "next")
    assert body["items"][0]["phone_masked"] == "010-12··-5678"
    assert "phone" not in body["items"][0]   # 목록에는 전체 번호 칸이 없다
    query = stub.queries[0]
    assert (query.q, query.sort, query.include_passed, query.cursor) == (None, "recent", False, None)


async def test_검색어_정렬_포함_여부_커서를_넘긴다():
    stub = _StubUseCase()
    await _get(stub, "/v1/shops/3/customers?q=5678%20%EC%BD%A9&sort=name&include_passed=true&cursor=abc")
    query = stub.queries[0]
    assert (query.q, query.sort, query.include_passed, query.cursor) == ("5678 콩", "name", True, "abc")


async def test_모르는_정렬이나_너무_긴_검색어는_422_다():
    for path in ("/v1/shops/3/customers?sort=visit", "/v1/shops/3/customers?q=" + "가" * 51):
        response = await _get(_StubUseCase(), path)
        assert (response.status_code, response.json()["code"]) == (422, "VALIDATION_ERROR")
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_list_customers_interactor.py apps/customer/tests/adapter/test_list_customers_router.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.app.use_cases.list_customers_interactor'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/list_customers_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_search_dto import SortKey
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListCustomersQuery:
    ctx: ShopContext
    q: str | None
    sort: SortKey
    include_passed: bool
    cursor: str | None


@dataclass(frozen=True)
class PetSummaryView:
    pet_id: int
    name: str
    species: str
    breed: str
    age_label: str
    has_conditions: bool
    passed_away: bool


@dataclass(frozen=True)
class FamilyCardView:
    """가족 카드 — 보호자 이름과 가린 번호, 그 아래 반려동물 줄."""

    customer_id: int
    name: str
    phone_masked: str
    pets: list[PetSummaryView]


@dataclass(frozen=True)
class CustomerListView:
    items: list[FamilyCardView]
    next_cursor: str | None
    pet_count: int
```

`backend/apps/customer/app/ports/input/list_customers_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.list_customers_dto import CustomerListView, ListCustomersQuery


class ListCustomersUseCase(ABC):
    @abstractmethod
    async def list_customers(self, query: ListCustomersQuery) -> CustomerListView: ...
```

`backend/apps/customer/app/use_cases/list_customers_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_search_dto import SearchRequest
from customer.app.dtos.list_customers_dto import (
    CustomerListView,
    FamilyCardView,
    ListCustomersQuery,
    PetSummaryView,
)
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.services.pet_age import age_label
from customer.domain.services.phone_number import mask_phone
from customer.domain.services.search_terms import parse_query


class ListCustomersInteractor(ListCustomersUseCase):
    """검색 포트로 가족 ID 를 찾고, 보여 줄 정보는 원본 표에서 읽는다(검색 줄은 찾기와 정렬에만 쓴다)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def list_customers(self, query: ListCustomersQuery) -> CustomerListView:
        words = parse_query(query.q)
        page = await self._search.search(
            query.ctx,
            SearchRequest(words=words, sort=query.sort, include_passed=query.include_passed,
                          cursor=query.cursor),
        )
        customers = {c.id: c for c in await self._customers.list_active(query.ctx, page.customer_ids)}
        pets_by_customer: dict[int, list] = {}
        for pet in await self._pets.list_for_customers(query.ctx, page.customer_ids):
            if query.include_passed or not pet.passed_away:
                pets_by_customer.setdefault(pet.customer_id, []).append(pet)

        today = self._today()
        items = [
            FamilyCardView(
                customer_id=customer_id,
                name=customers[customer_id].name,
                phone_masked=mask_phone(customers[customer_id].phone),
                pets=[
                    PetSummaryView(
                        pet_id=p.id, name=p.name, species=p.species, breed=p.breed,
                        age_label=age_label(p.birth_date, p.birth_year, today),
                        has_conditions=p.has_conditions, passed_away=p.passed_away,
                    )
                    for p in pets_by_customer.get(customer_id, [])
                ],
            )
            for customer_id in page.customer_ids
            if customer_id in customers   # 검색 줄과 원본이 어긋났으면(익명화 직후 등) 원본을 따른다
        ]
        pet_count = await self._search.count_pets(query.ctx, words, query.include_passed)
        return CustomerListView(items=items, next_cursor=page.next_cursor, pet_count=pet_count)
```

`backend/apps/customer/dependencies/list_customers_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.app.use_cases.list_customers_interactor import ListCustomersInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_list_customers_use_case(db: DbSession) -> ListCustomersUseCase:
    return ListCustomersInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/list_customers_schema.py`:
```python
from __future__ import annotations

from pydantic import BaseModel

from customer.app.dtos.list_customers_dto import CustomerListView


class PetSummarySchema(BaseModel):
    pet_id: int
    name: str
    species: str
    breed: str
    age_label: str
    has_conditions: bool
    passed_away: bool


class FamilyCardSchema(BaseModel):
    customer_id: int
    name: str
    phone_masked: str
    pets: list[PetSummarySchema]


class CustomerListSchema(BaseModel):
    """목록 — 번호는 가린 값만 들어 있다."""

    items: list[FamilyCardSchema]
    next_cursor: str | None
    pet_count: int

    @classmethod
    def of(cls, view: CustomerListView) -> CustomerListSchema:
        return cls(
            items=[
                FamilyCardSchema(
                    customer_id=card.customer_id, name=card.name, phone_masked=card.phone_masked,
                    pets=[
                        PetSummarySchema(
                            pet_id=p.pet_id, name=p.name, species=p.species, breed=p.breed,
                            age_label=p.age_label, has_conditions=p.has_conditions,
                            passed_away=p.passed_away,
                        )
                        for p in card.pets
                    ],
                )
                for card in view.items
            ],
            next_cursor=view.next_cursor,
            pet_count=view.pet_count,
        )
```

`backend/apps/customer/adapter/inbound/api/v1/list_customers_router.py`:
```python
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from customer.adapter.inbound.api.schemas.list_customers_schema import CustomerListSchema
from customer.app.dtos.list_customers_dto import ListCustomersQuery
from customer.app.ports.input.list_customers_use_case import ListCustomersUseCase
from customer.dependencies.list_customers_provider import get_list_customers_use_case
from hub.app.dtos.shop_context import ShopContext

list_customers_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@list_customers_router.get("/{shop_id}/customers", response_model=CustomerListSchema)
async def list_customers(
    q: Annotated[str | None, Query(max_length=50)] = None,
    sort: Literal["recent", "name"] = "recent",
    include_passed: bool = False,
    cursor: Annotated[str | None, Query(max_length=500)] = None,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListCustomersUseCase = Depends(get_list_customers_use_case),
) -> CustomerListSchema:
    view = await use_case.list_customers(
        ListCustomersQuery(ctx=ctx, q=q, sort=sort, include_passed=include_passed, cursor=cursor)
    )
    return CustomerListSchema.of(view)
```



- [ ] **Step 4: API 프로세스에 붙인다**

`backend/main.py` — customer import 묶음(모듈 경로 순 자리)에 더한다.
```python
from customer.adapter.inbound.api.v1.list_customers_router import list_customers_router
```

customer 라우터 묶음의 끝(`install_error_handlers(` 바로 위)에 더한다.
```python
app.include_router(list_customers_router)
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_list_customers_interactor.py apps/customer/tests/adapter/test_list_customers_router.py -q -p no:cacheprovider`
Expected: `6 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `381 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app backend/apps/customer/adapter backend/apps/customer/dependencies backend/apps/customer/tests backend/main.py
git commit -m "feat(customer): 가족 카드 목록과 검색"
```

---

### Task 11: 반려동물 추가·수정 — `POST /customers/{customer_id}/pets`, `PUT /pets/{pet_id}`

추가는 고객 행을(`lock_active`), 수정은 반려동물 → 고객 행을(`lock_owner`) 맨 앞에서 잠근다. 잠금이 없으면 익명화와 겹친 추가가 익명화한 고객에게 이름을 되살린다(C14 — 두 세션 테스트는 Task 15). 폼은 잠그기 전에 검증한다(C8·C21). 수정은 질병 목록을 통째로 바꾼다(설계 7.1). 둘 다 반려동물 상세를 돌려준다.

**Files:**
- Create: `backend/apps/customer/app/dtos/add_pet_dto.py`
- Create: `backend/apps/customer/app/ports/input/add_pet_use_case.py`
- Create: `backend/apps/customer/app/use_cases/add_pet_interactor.py`
- Create: `backend/apps/customer/dependencies/add_pet_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/add_pet_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/add_pet_router.py`
- Create: `backend/apps/customer/app/dtos/update_pet_dto.py`
- Create: `backend/apps/customer/app/ports/input/update_pet_use_case.py`
- Create: `backend/apps/customer/app/use_cases/update_pet_interactor.py`
- Create: `backend/apps/customer/dependencies/update_pet_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/schemas/update_pet_schema.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/update_pet_router.py`
- Modify: `backend/main.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_add_pet_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_add_pet_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_update_pet_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_update_pet_router.py`

**Interfaces:**
- Consumes: Task 8 의 `PetFieldsSchema`·`PetInput`, Task 7 의 `read_pet_detail`·`PetDetailSchema`, Task 5 의 `lock_active`·`lock_owner`·`add`·`update`
- Produces: `AddPetUseCase.add_pet(AddPetCommand(ctx, customer_id, pet: PetInput)) -> PetDetailView`(201), `UpdatePetUseCase.update_pet(UpdatePetCommand(ctx, pet_id, pet: PetInput)) -> PetDetailView`, 스키마 `AddPetRequestSchema`·`UpdatePetRequestSchema`(둘 다 `PetFieldsSchema`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/app/use_cases/test_add_pet_interactor.py`:
```python
import pytest

from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.use_cases.add_pet_interactor import AddPetInteractor
from customer.domain.errors import CustomerNotFoundError, PetHealthConflictError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.inputs import pet_input
from customer.tests.helpers.profiles import condition, ctx


def _setup(shop_id=1):
    journal, customers, pets, types, search = family()
    customer = customers.seed(shop_id=shop_id)
    pets.seed(customer.id, "콩이")
    return journal, customer, AddPetInteractor(customers, pets, types, search, today)


async def test_고객을_잠근_뒤_반려동물을_더하고_상세를_돌려준다():
    journal, customer, interactor = _setup()
    view = await interactor.add_pet(AddPetCommand(ctx=ctx(), customer_id=customer.id,
                                                  pet=pet_input(name="두부", species="cat")))
    assert (view.pet.name, view.pet.species, view.owner.phone_masked) == ("두부", "cat", "010-12··-5678")
    assert [s.name for s in view.siblings] == ["콩이"]
    assert journal == [("lock_customer", customer.id), ("add_pet", customer.id), ("rebuild", customer.id)]


async def test_질병_규칙을_어기면_잠그지도_않는다():
    journal, customer, interactor = _setup()
    with pytest.raises(PetHealthConflictError):
        await interactor.add_pet(AddPetCommand(
            ctx=ctx(), customer_id=customer.id,
            pet=pet_input(no_known_conditions=True, conditions=(condition("allergy"),)),
        ))
    assert journal == []


async def test_다른_매장_고객이면_404_다():
    journal, customer, interactor = _setup(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await interactor.add_pet(AddPetCommand(ctx=ctx(shop_id=1), customer_id=customer.id, pet=pet_input()))
    assert [entry[0] for entry in journal] == ["lock_customer"]
```

`backend/apps/customer/tests/adapter/test_add_pet_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.add_pet_router import add_pet_router
from customer.dependencies.add_pet_provider import get_add_pet_use_case
from customer.tests.helpers.api import NO_WRITE, PET_BODY, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def add_pet(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _post(stub, access):
    app = build_app(add_pet_router, get_add_pet_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/customers/1/pets", json=PET_BODY)


async def test_직원도_반려동물을_더하고_201_과_반려동물_상세를_받는다():
    stub = _StubUseCase()
    response = await _post(stub, STAFF)
    assert response.status_code == 201
    assert response.json()["owner"]["phone_masked"] == "010-12··-5678"
    assert (stub.commands[0].customer_id, stub.commands[0].pet.name) == (1, "콩이")


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _post(stub, NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
    assert stub.commands == []
```

`backend/apps/customer/tests/app/use_cases/test_update_pet_interactor.py`:
```python
from datetime import date

import pytest

from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.use_cases.update_pet_interactor import UpdatePetInteractor
from customer.domain.errors import CustomerInputError, PetNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.inputs import pet_input
from customer.tests.helpers.profiles import condition, ctx


def _setup(shop_id=1):
    journal, customers, pets, types, search = family()
    pet = pets.seed(customers.seed(shop_id=shop_id).id)
    return journal, pet, UpdatePetInteractor(customers, pets, types, search, today)


async def test_고객을_잠근_뒤_고치고_검색_줄을_다시_만든다():
    journal, pet, interactor = _setup()
    view = await interactor.update_pet(UpdatePetCommand(
        ctx=ctx(), pet_id=pet.id,
        pet=pet_input(name="콩순이", no_known_conditions=False,
                      conditions=(condition("other", "눈물 자국"),)),
    ))
    assert view.pet.name == "콩순이"
    assert [(c.label, c.custom_label) for c in view.pet.conditions] == [("기타", "눈물 자국")]
    assert journal == [("lock_customer", pet.customer_id), ("update_pet", pet.id), ("rebuild", pet.customer_id)]


async def test_생일과_태어난_해를_함께_보내면_VALIDATION_ERROR_다():
    journal, pet, interactor = _setup()
    with pytest.raises(CustomerInputError):
        await interactor.update_pet(UpdatePetCommand(
            ctx=ctx(), pet_id=pet.id, pet=pet_input(birth_date=date(2021, 1, 1), birth_year=2021),
        ))
    assert journal == []


async def test_다른_매장의_반려동물은_404_다():
    journal, pet, interactor = _setup(shop_id=2)
    with pytest.raises(PetNotFoundError):
        await interactor.update_pet(UpdatePetCommand(ctx=ctx(shop_id=1), pet_id=pet.id, pet=pet_input()))
    assert journal == []
```

`backend/apps/customer/tests/adapter/test_update_pet_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
from customer.dependencies.update_pet_provider import get_update_pet_use_case
from customer.tests.helpers.api import NO_WRITE, PET_BODY, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def update_pet(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _put(stub, body, access):
    app = build_app(update_pet_router, get_update_pet_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.put("/v1/shops/3/pets/101", json=body)


async def test_직원도_반려동물을_고친다():
    stub = _StubUseCase()
    body = {**PET_BODY, "birth_year": None, "birth_date": "2021-03-01", "conditions": [],
            "no_known_conditions": True}
    response = await _put(stub, body, STAFF)
    assert response.status_code == 200
    command = stub.commands[0]
    assert (command.pet_id, str(command.pet.birth_date), command.pet.conditions) == (101, "2021-03-01", ())


async def test_customer_write_가_없으면_403_이다():
    stub = _StubUseCase()
    response = await _put(stub, PET_BODY, NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_add_pet_interactor.py apps/customer/tests/adapter/test_add_pet_router.py apps/customer/tests/app/use_cases/test_update_pet_interactor.py apps/customer/tests/adapter/test_update_pet_router.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.app.use_cases.add_pet_interactor'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/add_pet_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import PetInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class AddPetCommand:
    ctx: ShopContext
    customer_id: int
    pet: PetInput
```

`backend/apps/customer/app/ports/input/add_pet_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.dtos.customer_view_dto import PetDetailView


class AddPetUseCase(ABC):
    @abstractmethod
    async def add_pet(self, command: AddPetCommand) -> PetDetailView: ...
```

`backend/apps/customer/app/use_cases/add_pet_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.ports.input.add_pet_use_case import AddPetUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class AddPetInteractor(AddPetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today

    async def add_pet(self, command: AddPetCommand) -> PetDetailView:
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        profile = command.pet.to_profile(codes, self._today())
        # 고객 행을 잠근 뒤 다시 읽는다. 익명화한 고객에게 이름 있는 반려동물을 붙이지 않는다.
        await self._customers.lock_active(command.ctx, command.customer_id)
        pet = await self._pets.add(command.ctx, command.customer_id, profile)
        await self._search.rebuild_search_entry(command.ctx, command.customer_id)
        return await read_pet_detail(command.ctx, pet.id, self._customers, self._pets, self._today())
```

`backend/apps/customer/dependencies/add_pet_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.add_pet_use_case import AddPetUseCase
from customer.app.use_cases.add_pet_interactor import AddPetInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository,
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_add_pet_use_case(db: DbSession) -> AddPetUseCase:
    return AddPetInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), search=build_customer_search(db),
        today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/add_pet_schema.py`:
```python
from customer.adapter.inbound.api.schemas.register_customer_schema import PetFieldsSchema


class AddPetRequestSchema(PetFieldsSchema):
    """기존 고객에게 반려동물을 더한다. 폼은 등록 3단계와 같다."""
```

`backend/apps/customer/adapter/inbound/api/v1/add_pet_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import CustomerId
from customer.adapter.inbound.api.schemas.add_pet_schema import AddPetRequestSchema
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.ports.input.add_pet_use_case import AddPetUseCase
from customer.dependencies.add_pet_provider import get_add_pet_use_case
from hub.app.dtos.shop_context import ShopContext

add_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@add_pet_router.post(
    "/{shop_id}/customers/{customer_id}/pets", response_model=PetDetailSchema, status_code=201
)
async def add_pet(
    customer_id: CustomerId,
    body: AddPetRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: AddPetUseCase = Depends(get_add_pet_use_case),
) -> PetDetailSchema:
    view = await use_case.add_pet(AddPetCommand(ctx=ctx, customer_id=customer_id, pet=body.to_input()))
    return PetDetailSchema.of(view)
```

`backend/apps/customer/app/dtos/update_pet_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from customer.app.dtos.customer_input_dto import PetInput
from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdatePetCommand:
    ctx: ShopContext
    pet_id: int
    pet: PetInput
```

`backend/apps/customer/app/ports/input/update_pet_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.update_pet_dto import UpdatePetCommand


class UpdatePetUseCase(ABC):
    @abstractmethod
    async def update_pet(self, command: UpdatePetCommand) -> PetDetailView: ...
```

`backend/apps/customer/app/use_cases/update_pet_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.ports.input.update_pet_use_case import UpdatePetUseCase
from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class UpdatePetInteractor(UpdatePetUseCase):
    def __init__(
        self, customers: CustomerRepository, pets: PetRepository,
        condition_types: ConditionTypeRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._condition_types = condition_types
        self._search = search
        self._today = today

    async def update_pet(self, command: UpdatePetCommand) -> PetDetailView:
        codes = frozenset(t.code for t in await self._condition_types.list_all())
        profile = command.pet.to_profile(codes, self._today())
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.update(command.ctx, command.pet_id, profile)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
```

`backend/apps/customer/dependencies/update_pet_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.update_pet_use_case import UpdatePetUseCase
from customer.app.use_cases.update_pet_interactor import UpdatePetInteractor
from customer.dependencies.customer_wiring import (
    build_condition_type_repository,
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_update_pet_use_case(db: DbSession) -> UpdatePetUseCase:
    return UpdatePetInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        condition_types=build_condition_type_repository(db), search=build_customer_search(db),
        today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/schemas/update_pet_schema.py`:
```python
from customer.adapter.inbound.api.schemas.register_customer_schema import PetFieldsSchema


class UpdatePetRequestSchema(PetFieldsSchema):
    """반려동물 폼 전체를 보낸다(PUT). 질병 목록도 통째로 바꾼다."""
```

`backend/apps/customer/adapter/inbound/api/v1/update_pet_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.adapter.inbound.api.schemas.update_pet_schema import UpdatePetRequestSchema
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.ports.input.update_pet_use_case import UpdatePetUseCase
from customer.dependencies.update_pet_provider import get_update_pet_use_case
from hub.app.dtos.shop_context import ShopContext

update_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@update_pet_router.put("/{shop_id}/pets/{pet_id}", response_model=PetDetailSchema)
async def update_pet(
    pet_id: PetId,
    body: UpdatePetRequestSchema,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: UpdatePetUseCase = Depends(get_update_pet_use_case),
) -> PetDetailSchema:
    view = await use_case.update_pet(UpdatePetCommand(ctx=ctx, pet_id=pet_id, pet=body.to_input()))
    return PetDetailSchema.of(view)
```



- [ ] **Step 4: API 프로세스에 붙인다**

`backend/main.py` — customer import 묶음(모듈 경로 순 자리)에 더한다.
```python
from customer.adapter.inbound.api.v1.add_pet_router import add_pet_router
from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
```

customer 라우터 묶음의 끝(`install_error_handlers(` 바로 위)에 더한다.
```python
app.include_router(add_pet_router)
app.include_router(update_pet_router)
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_add_pet_interactor.py apps/customer/tests/adapter/test_add_pet_router.py apps/customer/tests/app/use_cases/test_update_pet_interactor.py apps/customer/tests/adapter/test_update_pet_router.py -q -p no:cacheprovider`
Expected: `10 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `391 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app backend/apps/customer/adapter backend/apps/customer/dependencies backend/apps/customer/tests backend/main.py
git commit -m "feat(customer): 반려동물 추가와 수정"
```

---

### Task 12: 무지개다리와 반려동물 삭제 — `POST·DELETE /pets/{pet_id}/passed-away`, `DELETE /pets/{pet_id}`

무지개다리는 `passed_away_at`만 찍고(다시 누르면 처음 시각을 지킨다), 되돌리기는 지운다. 삭제는 잘못 등록한 아이를 지우는 것이라 직원도 할 수 있다(`customer:write`). **고객 행을 잠근 뒤 센다** — 잠금이 없으면 마지막 두 마리를 동시에 지워 반려동물 없는 가족이 남는다(C13). 마지막 한 마리면 409 `LAST_PET`(고객 삭제를 안내). 무지개다리 아이도 수에 들어간다(새로 정한 것 10번). 셋 다 요청 본문이 없어 schema 파일이 없다.

**Files:**
- Create: `backend/apps/customer/app/dtos/mark_pet_passed_away_dto.py`
- Create: `backend/apps/customer/app/ports/input/mark_pet_passed_away_use_case.py`
- Create: `backend/apps/customer/app/use_cases/mark_pet_passed_away_interactor.py`
- Create: `backend/apps/customer/dependencies/mark_pet_passed_away_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/mark_pet_passed_away_router.py`
- Create: `backend/apps/customer/app/dtos/unmark_pet_passed_away_dto.py`
- Create: `backend/apps/customer/app/ports/input/unmark_pet_passed_away_use_case.py`
- Create: `backend/apps/customer/app/use_cases/unmark_pet_passed_away_interactor.py`
- Create: `backend/apps/customer/dependencies/unmark_pet_passed_away_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/unmark_pet_passed_away_router.py`
- Create: `backend/apps/customer/app/dtos/delete_pet_dto.py`
- Create: `backend/apps/customer/app/ports/input/delete_pet_use_case.py`
- Create: `backend/apps/customer/app/use_cases/delete_pet_interactor.py`
- Create: `backend/apps/customer/dependencies/delete_pet_provider.py`
- Create: `backend/apps/customer/adapter/inbound/api/v1/delete_pet_router.py`
- Modify: `backend/main.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_mark_pet_passed_away_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_unmark_pet_passed_away_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_unmark_pet_passed_away_router.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_delete_pet_interactor.py`
- Test: `backend/apps/customer/tests/adapter/test_delete_pet_router.py`

**Interfaces:**
- Consumes: Task 5 의 `lock_owner`·`set_passed_away`·`count_for_customer`·`delete`, Task 7 의 `read_pet_detail`·`PetDetailSchema`
- Produces: `MarkPetPassedAwayUseCase.mark_pet_passed_away(MarkPetPassedAwayCommand(ctx, pet_id)) -> PetDetailView`, `UnmarkPetPassedAwayUseCase.unmark_pet_passed_away(UnmarkPetPassedAwayCommand(ctx, pet_id)) -> PetDetailView`, `DeletePetUseCase.delete_pet(DeletePetCommand(ctx, pet_id)) -> None`(204)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py`:
```python
import pytest

from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
from customer.domain.errors import PetNotFoundError
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_고객을_잠근_뒤_무지개다리를_표시한다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed().id)
    view = await MarkPetPassedAwayInteractor(customers, pets, search, today).mark_pet_passed_away(
        MarkPetPassedAwayCommand(ctx=ctx(), pet_id=pet.id)
    )
    assert view.pet.passed_away_at is not None
    assert journal == [("lock_customer", pet.customer_id), ("set_passed_away", pet.id, True),
                       ("rebuild", pet.customer_id)]


async def test_다른_매장의_반려동물은_404_다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await MarkPetPassedAwayInteractor(customers, pets, search, today).mark_pet_passed_away(
            MarkPetPassedAwayCommand(ctx=ctx(shop_id=1), pet_id=pet.id)
        )
    assert journal == []
```

`backend/apps/customer/tests/adapter/test_mark_pet_passed_away_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.mark_pet_passed_away_router import mark_pet_passed_away_router
from customer.dependencies.mark_pet_passed_away_provider import get_mark_pet_passed_away_use_case
from customer.tests.helpers.api import NO_WRITE, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def mark_pet_passed_away(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _post(stub, access):
    app = build_app(mark_pet_passed_away_router, get_mark_pet_passed_away_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.post("/v1/shops/3/pets/101/passed-away")


async def test_직원도_무지개다리를_표시한다():
    stub = _StubUseCase()
    assert (await _post(stub, STAFF)).status_code == 200
    assert stub.commands[0].pet_id == 101


async def test_customer_write_가_없으면_403_이다():
    response = await _post(_StubUseCase(), NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
```

`backend/apps/customer/tests/app/use_cases/test_unmark_pet_passed_away_interactor.py`:
```python
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand
from customer.app.use_cases.unmark_pet_passed_away_interactor import UnmarkPetPassedAwayInteractor
from customer.tests.helpers.fakes import family, today
from customer.tests.helpers.profiles import ctx


async def test_고객을_잠근_뒤_무지개다리를_되돌린다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed().id, passed_away=True)
    view = await UnmarkPetPassedAwayInteractor(customers, pets, search, today).unmark_pet_passed_away(
        UnmarkPetPassedAwayCommand(ctx=ctx(), pet_id=pet.id)
    )
    assert view.pet.passed_away_at is None
    assert journal == [("lock_customer", pet.customer_id), ("set_passed_away", pet.id, False),
                       ("rebuild", pet.customer_id)]
```

`backend/apps/customer/tests/adapter/test_unmark_pet_passed_away_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
    unmark_pet_passed_away_router,
)
from customer.dependencies.unmark_pet_passed_away_provider import (
    get_unmark_pet_passed_away_use_case,
)
from customer.tests.helpers.api import NO_WRITE, STAFF, build_app, pet_detail_view


class _StubUseCase:
    def __init__(self):
        self.commands = []

    async def unmark_pet_passed_away(self, command):
        self.commands.append(command)
        return pet_detail_view()


async def _delete(stub, access):
    app = build_app(unmark_pet_passed_away_router, get_unmark_pet_passed_away_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/pets/101/passed-away")


async def test_직원도_무지개다리를_되돌린다():
    stub = _StubUseCase()
    assert (await _delete(stub, STAFF)).status_code == 200
    assert stub.commands[0].pet_id == 101


async def test_customer_write_가_없으면_403_이다():
    response = await _delete(_StubUseCase(), NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
```

`backend/apps/customer/tests/app/use_cases/test_delete_pet_interactor.py`:
```python
import pytest

from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.domain.errors import LastPetError, PetNotFoundError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx


async def test_고객을_잠근_뒤_세고_지우고_검색_줄을_다시_만든다():
    journal, customers, pets, _, search = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "두부")
    await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
    assert journal == [("lock_customer", customer.id), ("delete_pet", kong.id), ("rebuild", customer.id)]


async def test_마지막_반려동물이면_LAST_PET_이다():
    journal, customers, pets, _, search = family()
    only = pets.seed(customers.seed().id)
    with pytest.raises(LastPetError):
        await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=only.id))
    assert only.id in pets.rows
    assert [entry[0] for entry in journal] == ["lock_customer"]


async def test_무지개다리인_아이도_수에_들어간다():
    """무지개다리 아이가 남아 있으면 마지막이 아니다 — 가족 기록이 남는다."""
    journal, customers, pets, _, search = family()
    customer = customers.seed()
    kong = pets.seed(customer.id, "콩이")
    pets.seed(customer.id, "별이", passed_away=True)
    await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
    assert kong.id not in pets.rows


async def test_다른_매장의_반려동물은_404_다():
    journal, customers, pets, _, search = family()
    pet = pets.seed(customers.seed(shop_id=2).id)
    with pytest.raises(PetNotFoundError):
        await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(shop_id=1), pet_id=pet.id))
```

`backend/apps/customer/tests/adapter/test_delete_pet_router.py`:
```python
from httpx import ASGITransport, AsyncClient

from customer.adapter.inbound.api.v1.delete_pet_router import delete_pet_router
from customer.dependencies.delete_pet_provider import get_delete_pet_use_case
from customer.domain.errors import LastPetError
from customer.tests.helpers.api import NO_WRITE, STAFF, build_app


class _StubUseCase:
    def __init__(self, error=None):
        self.error = error
        self.commands = []

    async def delete_pet(self, command):
        self.commands.append(command)
        if self.error:
            raise self.error


async def _delete(stub, access):
    app = build_app(delete_pet_router, get_delete_pet_use_case, stub, access=access)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        return await client.delete("/v1/shops/3/pets/101")


async def test_직원도_잘못_등록한_반려동물을_지운다():
    stub = _StubUseCase()
    assert (await _delete(stub, STAFF)).status_code == 204
    assert stub.commands[0].pet_id == 101


async def test_마지막_반려동물이면_409_LAST_PET_이다():
    response = await _delete(_StubUseCase(LastPetError("마지막")), STAFF)
    assert (response.status_code, response.json()["code"]) == (409, "LAST_PET")


async def test_customer_write_가_없으면_403_이다():
    response = await _delete(_StubUseCase(), NO_WRITE)
    assert (response.status_code, response.json()["code"]) == (403, "PERMISSION_DENIED")
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py apps/customer/tests/adapter/test_mark_pet_passed_away_router.py apps/customer/tests/app/use_cases/test_unmark_pet_passed_away_interactor.py apps/customer/tests/adapter/test_unmark_pet_passed_away_router.py apps/customer/tests/app/use_cases/test_delete_pet_interactor.py apps/customer/tests/adapter/test_delete_pet_router.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'customer.app.use_cases.mark_pet_passed_away_interactor'`


- [ ] **Step 3: 구현한다**

`backend/apps/customer/app/dtos/mark_pet_passed_away_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class MarkPetPassedAwayCommand:
    ctx: ShopContext
    pet_id: int
```

`backend/apps/customer/app/ports/input/mark_pet_passed_away_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand


class MarkPetPassedAwayUseCase(ABC):
    @abstractmethod
    async def mark_pet_passed_away(self, command: MarkPetPassedAwayCommand) -> PetDetailView: ...
```

`backend/apps/customer/app/use_cases/mark_pet_passed_away_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class MarkPetPassedAwayInteractor(MarkPetPassedAwayUseCase):
    """무지개다리 — 기록은 남기고 목록 기본에서 숨긴다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def mark_pet_passed_away(self, command: MarkPetPassedAwayCommand) -> PetDetailView:
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_passed_away(command.ctx, command.pet_id, passed_away=True)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
```

`backend/apps/customer/dependencies/mark_pet_passed_away_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_mark_pet_passed_away_use_case(db: DbSession) -> MarkPetPassedAwayUseCase:
    return MarkPetPassedAwayInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/v1/mark_pet_passed_away_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
from customer.dependencies.mark_pet_passed_away_provider import get_mark_pet_passed_away_use_case
from hub.app.dtos.shop_context import ShopContext

mark_pet_passed_away_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@mark_pet_passed_away_router.post("/{shop_id}/pets/{pet_id}/passed-away", response_model=PetDetailSchema)
async def mark_pet_passed_away(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: MarkPetPassedAwayUseCase = Depends(get_mark_pet_passed_away_use_case),
) -> PetDetailSchema:
    view = await use_case.mark_pet_passed_away(MarkPetPassedAwayCommand(ctx=ctx, pet_id=pet_id))
    return PetDetailSchema.of(view)
```

`backend/apps/customer/app/dtos/unmark_pet_passed_away_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UnmarkPetPassedAwayCommand:
    ctx: ShopContext
    pet_id: int
```

`backend/apps/customer/app/ports/input/unmark_pet_passed_away_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand


class UnmarkPetPassedAwayUseCase(ABC):
    @abstractmethod
    async def unmark_pet_passed_away(self, command: UnmarkPetPassedAwayCommand) -> PetDetailView: ...
```

`backend/apps/customer/app/use_cases/unmark_pet_passed_away_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import date

from customer.app.dtos.customer_view_dto import PetDetailView
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand
from customer.app.ports.input.unmark_pet_passed_away_use_case import UnmarkPetPassedAwayUseCase
from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.app.services.detail_reader import read_pet_detail


class UnmarkPetPassedAwayInteractor(UnmarkPetPassedAwayUseCase):
    """잘못 누른 무지개다리를 되돌린다."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
        today: Callable[[], date],
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._search = search
        self._today = today

    async def unmark_pet_passed_away(self, command: UnmarkPetPassedAwayCommand) -> PetDetailView:
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        await self._pets.set_passed_away(command.ctx, command.pet_id, passed_away=False)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
        return await read_pet_detail(
            command.ctx, command.pet_id, self._customers, self._pets, self._today()
        )
```

`backend/apps/customer/dependencies/unmark_pet_passed_away_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.unmark_pet_passed_away_use_case import UnmarkPetPassedAwayUseCase
from customer.app.use_cases.unmark_pet_passed_away_interactor import UnmarkPetPassedAwayInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_pet_repository,
)
from customer.domain.services.pet_age import seoul_today


def get_unmark_pet_passed_away_use_case(db: DbSession) -> UnmarkPetPassedAwayUseCase:
    return UnmarkPetPassedAwayInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        search=build_customer_search(db), today=seoul_today,
    )
```

`backend/apps/customer/adapter/inbound/api/v1/unmark_pet_passed_away_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.adapter.inbound.api.schemas.get_pet_schema import PetDetailSchema
from customer.app.dtos.unmark_pet_passed_away_dto import UnmarkPetPassedAwayCommand
from customer.app.ports.input.unmark_pet_passed_away_use_case import UnmarkPetPassedAwayUseCase
from customer.dependencies.unmark_pet_passed_away_provider import (
    get_unmark_pet_passed_away_use_case,
)
from hub.app.dtos.shop_context import ShopContext

unmark_pet_passed_away_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@unmark_pet_passed_away_router.delete(
    "/{shop_id}/pets/{pet_id}/passed-away", response_model=PetDetailSchema
)
async def unmark_pet_passed_away(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: UnmarkPetPassedAwayUseCase = Depends(get_unmark_pet_passed_away_use_case),
) -> PetDetailSchema:
    view = await use_case.unmark_pet_passed_away(UnmarkPetPassedAwayCommand(ctx=ctx, pet_id=pet_id))
    return PetDetailSchema.of(view)
```

`backend/apps/customer/app/dtos/delete_pet_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class DeletePetCommand:
    ctx: ShopContext
    pet_id: int
```

`backend/apps/customer/app/ports/input/delete_pet_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from customer.app.dtos.delete_pet_dto import DeletePetCommand


class DeletePetUseCase(ABC):
    @abstractmethod
    async def delete_pet(self, command: DeletePetCommand) -> None: ...
```

`backend/apps/customer/app/use_cases/delete_pet_interactor.py`:
```python
from __future__ import annotations

from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import LastPetError


class DeletePetInteractor(DeletePetUseCase):
    """잘못 등록한 반려동물을 지운다. 세상을 떠난 아이는 지우지 않고 무지개다리로 둔다."""

    def __init__(self, pets: PetRepository, search: CustomerSearchPort) -> None:
        self._pets = pets
        self._search = search

    async def delete_pet(self, command: DeletePetCommand) -> None:
        # 고객 행을 잠근 뒤 센다. 잠금이 없으면 마지막 두 마리를 동시에 지워 반려동물 없는 가족이 남는다.
        customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
        if await self._pets.count_for_customer(command.ctx, customer_id) <= 1:
            raise LastPetError("마지막 반려동물은 지울 수 없습니다. 고객 삭제를 이용해 주세요.")
        await self._pets.delete(command.ctx, command.pet_id)
        await self._search.rebuild_search_entry(command.ctx, customer_id)
```

`backend/apps/customer/dependencies/delete_pet_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.dependencies.customer_wiring import (
    build_customer_search,
    build_pet_repository,
)


def get_delete_pet_use_case(db: DbSession) -> DeletePetUseCase:
    return DeletePetInteractor(
        pets=build_pet_repository(db), search=build_customer_search(db),
    )
```

`backend/apps/customer/adapter/inbound/api/v1/delete_pet_router.py`:
```python
from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from customer.adapter.inbound.api.path_params import PetId
from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
from customer.dependencies.delete_pet_provider import get_delete_pet_use_case
from hub.app.dtos.shop_context import ShopContext

delete_pet_router = APIRouter(prefix="/v1/shops", tags=["customers"])


@delete_pet_router.delete("/{shop_id}/pets/{pet_id}", status_code=204)
async def delete_pet(
    pet_id: PetId,
    ctx: ShopContext = Depends(require_permission("customer:write")),
    use_case: DeletePetUseCase = Depends(get_delete_pet_use_case),
) -> Response:
    await use_case.delete_pet(DeletePetCommand(ctx=ctx, pet_id=pet_id))
    return Response(status_code=204)
```



- [ ] **Step 4: API 프로세스에 붙인다**

`backend/main.py` — customer import 묶음(모듈 경로 순 자리)에 더한다.
```python
from customer.adapter.inbound.api.v1.mark_pet_passed_away_router import mark_pet_passed_away_router
from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
    unmark_pet_passed_away_router,
)
from customer.adapter.inbound.api.v1.delete_pet_router import delete_pet_router
```

customer 라우터 묶음의 끝(`install_error_handlers(` 바로 위)에 더한다.
```python
app.include_router(mark_pet_passed_away_router)
app.include_router(unmark_pet_passed_away_router)
app.include_router(delete_pet_router)
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py apps/customer/tests/adapter/test_mark_pet_passed_away_router.py apps/customer/tests/app/use_cases/test_unmark_pet_passed_away_interactor.py apps/customer/tests/adapter/test_unmark_pet_passed_away_router.py apps/customer/tests/app/use_cases/test_delete_pet_interactor.py apps/customer/tests/adapter/test_delete_pet_router.py -q -p no:cacheprovider`
Expected: `14 passed`


- [ ] **Step 6: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `405 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `174 passed`. 실패 0.


- [ ] **Step 7: 커밋**

```bash
git add backend/apps/customer/app backend/apps/customer/adapter backend/apps/customer/dependencies backend/apps/customer/tests backend/main.py
git commit -m "feat(customer): 무지개다리와 반려동물 삭제"
```

---

### Task 13: 접근 로그의 쿼리 문자열을 가린다 (C7·C15)

번호 조회(`?phone=01012345678`)와 검색(`?q=김민지`)이 uvicorn 접근 로그(`INFO: … "GET /v1/shops/1/customers/lookup?phone=… HTTP/1.1" 200`)에 그대로 남는다. 설계의 API 모양은 그대로 두고(새로 정한 것 2번), API 프로세스가 import 될 때 `uvicorn.access` 로거에 쿼리를 `?[가림]`으로 바꾸는 필터를 한 번 단다. uvicorn 은 로깅을 설정한 뒤에 앱을 import 하므로(`--reload`의 하위 프로세스도 같다) 이때 단 필터가 남는다. 경로는 남긴다. 인증 프로세스에는 쿼리로 받는 개인정보가 없어 달지 않는다.

**Files:**
- Create: `backend/core/access_log.py`
- Modify: `backend/main.py`
- Test: `backend/tests/test_access_log.py`

**Interfaces:**
- Consumes: 없음(표준 `logging`)
- Produces: `core.access_log`: `QueryStringRedactor(logging.Filter)`, `redact_access_log_queries() -> None`(여러 번 불러도 필터는 하나)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_access_log.py`:
```python
"""접근 로그에 검색어·전화번호가 남지 않는다(설계 9절 C7)."""
import logging

from core.access_log import QueryStringRedactor


def _uvicorn_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 0, '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", path, "1.1", 200), None,
    )


def test_쿼리_문자열을_가리고_경로는_남긴다():
    record = _uvicorn_record("/v1/shops/1/customers/lookup?phone=01012345678")
    assert QueryStringRedactor().filter(record) is True
    message = record.getMessage()
    assert message == '127.0.0.1:5000 - "GET /v1/shops/1/customers/lookup?[가림] HTTP/1.1" 200'
    assert "01012345678" not in message


def test_쿼리가_없거나_모양이_다른_기록은_그대로_둔다():
    plain = _uvicorn_record("/v1/shops/1/customers")
    QueryStringRedactor().filter(plain)
    assert "/v1/shops/1/customers HTTP" in plain.getMessage()
    other = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 0, "시작", None, None)
    assert QueryStringRedactor().filter(other) is True and other.getMessage() == "시작"


def test_API_프로세스는_접근_로거에_가림_필터를_단다():
    import main  # noqa: F401 — import 할 때 단다

    filters = logging.getLogger("uvicorn.access").filters
    assert sum(isinstance(f, QueryStringRedactor) for f in filters) == 1
```



- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest tests/test_access_log.py -q -p no:cacheprovider`
Expected: FAIL — 수집 단계에서 `ModuleNotFoundError: No module named 'core.access_log'`


- [ ] **Step 3: 구현한다**

`backend/core/access_log.py`:
```python
"""접근 로그에서 쿼리 문자열을 가린다.

고객 검색어(`?q=` — 이름·번호 뒷자리)와 번호 조회(`?phone=`)가 uvicorn 접근 로그에 그대로 남지 않게 한다.
경로는 남긴다. uvicorn 은 접근 로그를 `'%s - "%s %s HTTP/%s" %d'` 와 인자 튜플로 남기며 세 번째 인자가
쿼리가 붙은 경로다.
"""
from __future__ import annotations

import logging

_REDACTED = "?[가림]"


class QueryStringRedactor(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        args = record.args
        if isinstance(args, tuple) and len(args) >= 3 and isinstance(args[2], str) and "?" in args[2]:
            record.args = (*args[:2], args[2].split("?", 1)[0] + _REDACTED, *args[3:])
        return True


def redact_access_log_queries() -> None:
    """uvicorn 접근 로거에 가림 필터를 한 번만 단다. 진입점이 import 될 때 부른다."""
    logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(f, QueryStringRedactor) for f in logger.filters):
        logger.addFilter(QueryStringRedactor())
```



- [ ] **Step 4: API 프로세스가 필터를 달게 한다**

`backend/main.py`
```diff
+from core.access_log import redact_access_log_queries
 from core.database import dispose_engine, init_engine
```
```diff
+# 고객 검색어·번호 조회가 쿼리 문자열로 오므로 접근 로그에서 가린다(설계 9절 C7).
+redact_access_log_queries()
+
 app = FastAPI(title="차곡노트 API", lifespan=lifespan)
```


- [ ] **Step 5: 돌려서 통과를 본다**

Run: `docker compose run --rm backend pytest tests/test_access_log.py -q -p no:cacheprovider`
Expected: `3 passed`


- [ ] **Step 6: 판별력을 확인한다**

`main.py`의 `redact_access_log_queries()` 호출을 잠시 주석으로 막고 `docker compose run --rm backend pytest tests/test_access_log.py -q -p no:cacheprovider`를 돌린다 → `test_API_프로세스는_접근_로거에_가림_필터를_단다`가 실패해야 한다. 되돌린다. 실제 uvicorn 로그는 Task 16 의 흐름 확인에서 본다.


- [ ] **Step 7: 전체 단위 테스트와 구조 계약을 돌린다**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 단위 `408 passed`, `Contracts: 6 kept, 0 broken.`. 실패 0.


- [ ] **Step 8: 커밋**

```bash
git add backend/core/access_log.py backend/tests/test_access_log.py backend/main.py
git commit -m "feat(core): 접근 로그의 쿼리 문자열을 가린다"
```

---

### Task 14: 실제 배선 통합 테스트 — 테넌트 격리부터

두 프로세스의 실제 앱 객체(`wired` 픽스처)에 붙어 프로바이더·DB 커밋·매장 접근 확인까지 통과한다. **첫 테스트는 테넌트 격리(C1)다**(`_docs/harness.md` — 스포크를 새로 만들면 첫 통합 테스트로 둔다): B매장 경로 14개는 403 `NOT_A_MEMBER`, 내 매장 경로에 B의 ID 를 넣은 10개는 404. 그다음 등록부터 익명화까지 한 바퀴(C3·C6·C16), 직원 권한(C4), 내보낸 직원(C5), 번호·질병 규칙(C2 순차·C8·C21), 검색 정확도(뒷자리·초성·여러 낱말·특수 문자, C10), 30 가족 쪽 나누기(C19), 토큰 없는 요청.

이 작업은 새 코드가 없다 — 앞 작업들의 배선을 실제로 확인한다. **테스트가 실패하면 테스트를 고치지 말고 원인 코드를 고친 뒤 무엇이 계획서와 달라졌는지 보고한다.**

**Files:**
- Test: `backend/tests/integration/test_customer_flow_wiring.py`

**Interfaces:**
- Consumes: `tests/integration/support.py`의 `make_operator`, `shop_with_owner`, `accept_invite`, `staff_invite`, `bearer`, `error_of`; `wired` 픽스처
- Produces: 없음

- [ ] **Step 1: 테스트를 쓴다**

`backend/tests/integration/test_customer_flow_wiring.py`:
```python
"""고객·반려동물을 실제 배선(프로바이더·DB 커밋·매장 접근 확인)으로 확인한다. 첫 테스트는 테넌트 격리다."""
import pytest

from tests.integration.support import (
    accept_invite,
    bearer,
    error_of,
    make_operator,
    shop_with_owner,
    staff_invite,
)

pytestmark = pytest.mark.integration

CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {
    "name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True,
}


async def _register(wired, shop_id, headers, customer=None, pet=None):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers",
        json={"customer": {**CUSTOMER, **(customer or {})}, "pet": {**PET, **(pet or {})}},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["customer"]["customer_id"], body["pets"][0]["pet_id"]


async def _list(wired, shop_id, headers, query=""):
    response = await wired.api.get(f"/v1/shops/{shop_id}/customers{query}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_다른_매장의_고객과_반려동물에는_손댈_수_없다(wired):
    """C1 — B매장 경로는 403 NOT_A_MEMBER, 내 매장 경로에 B매장의 ID 를 넣으면 404 다."""
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    b = bearer(b_owner["access_token"])
    b_customer, b_pet = await _register(wired, b_shop, b)
    a = bearer(a_owner["access_token"])
    body = {"customer": CUSTOMER, "pet": PET}

    their_shop = [
        await wired.api.get(f"/v1/shops/{b_shop}/customers", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/customers/lookup?phone=01012345678", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/customers", json=body, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/customers/{b_customer}", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/customers/{b_customer}", json=CUSTOMER, headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/customers/{b_customer}", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/customers/{b_customer}/pets", json=PET, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/pets/{b_pet}", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/pets/{b_pet}", json=PET, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/pets/{b_pet}/passed-away", headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/pets/{b_pet}/passed-away", headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/pets/{b_pet}", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/pet-condition-types", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/customers/myself", headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * len(their_shop)

    # 경로의 매장은 내 매장이라 소속 확인은 통과한다. 대상은 컨텍스트의 매장 안에서만 찾는다(C9).
    own_shop = [
        (await wired.api.get(f"/v1/shops/{a_shop}/customers/{b_customer}", headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.put(f"/v1/shops/{a_shop}/customers/{b_customer}", json=CUSTOMER, headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.delete(f"/v1/shops/{a_shop}/customers/{b_customer}", headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.post(f"/v1/shops/{a_shop}/customers/{b_customer}/pets", json=PET, headers=a), "CUSTOMER_NOT_FOUND"),
        (await wired.api.get(f"/v1/shops/{a_shop}/pets/{b_pet}", headers=a), "PET_NOT_FOUND"),
        (await wired.api.put(f"/v1/shops/{a_shop}/pets/{b_pet}", json=PET, headers=a), "PET_NOT_FOUND"),
        (await wired.api.post(f"/v1/shops/{a_shop}/pets/{b_pet}/passed-away", headers=a), "PET_NOT_FOUND"),
        (await wired.api.delete(f"/v1/shops/{a_shop}/pets/{b_pet}/passed-away", headers=a), "PET_NOT_FOUND"),
        (await wired.api.delete(f"/v1/shops/{a_shop}/pets/{b_pet}", headers=a), "PET_NOT_FOUND"),
        (await wired.api.get(f"/v1/shops/{a_shop}/customers/lookup?phone=01012345678", headers=a), "CUSTOMER_NOT_FOUND"),
    ]
    assert [error_of(r) for r, _ in own_shop] == [(404, code) for _, code in own_shop]
    assert (await _list(wired, a_shop, a))["items"] == []

    # B 매장의 가족은 그대로다.
    detail = await wired.api.get(f"/v1/shops/{b_shop}/customers/{b_customer}", headers=b)
    assert detail.json()["customer"]["name"] == "김민지"
    assert [(p["name"], p["passed_away_at"]) for p in detail.json()["pets"]] == [("콩이", None)]


async def test_등록부터_익명화까지_돈다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])

    customer_id, kong = await _register(wired, shop_id, headers, customer={"phone_alt": "02-123-4567"})
    looked_up = await wired.api.get(f"/v1/shops/{shop_id}/customers/lookup?phone=01012345678", headers=headers)
    assert looked_up.json() == {"customer_id": customer_id, "name": "김민지", "pet_names": ["콩이"]}

    added = await wired.api.post(
        f"/v1/shops/{shop_id}/customers/{customer_id}/pets",
        json={**PET, "name": "두부", "species": "cat", "no_known_conditions": False,
              "conditions": [{"type_code": "patella_luxation", "note": "2기"},
                             {"type_code": "other", "custom_label": "눈물 자국"}]},
        headers=headers,
    )
    assert added.status_code == 201
    dubu = added.json()["pet"]["pet_id"]
    assert [s["name"] for s in added.json()["siblings"]] == ["콩이"]
    assert [(c["label"], c["custom_label"]) for c in added.json()["pet"]["conditions"]] == [
        ("슬개골 탈구", None), ("기타", "눈물 자국"),
    ]

    listed = await _list(wired, shop_id, headers)
    assert listed["pet_count"] == 2
    card = listed["items"][0]
    assert (card["name"], card["phone_masked"]) == ("김민지", "010-12··-5678")
    assert [(p["name"], p["has_conditions"]) for p in card["pets"]] == [("콩이", False), ("두부", True)]

    detail = await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)
    assert (detail.json()["customer"]["phone"], detail.json()["customer"]["phone_alt"]) == ("01012345678", "021234567")

    # 질병을 통째로 바꾸고, 무지개다리를 표시했다가 되돌린다.
    updated = await wired.api.put(
        f"/v1/shops/{shop_id}/pets/{dubu}",
        json={**PET, "name": "두부", "species": "cat", "no_known_conditions": True, "conditions": []},
        headers=headers,
    )
    assert updated.json()["pet"]["has_conditions"] is False
    passed = await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)
    assert passed.json()["pet"]["passed_away_at"] is not None
    assert [p["name"] for p in (await _list(wired, shop_id, headers))["items"][0]["pets"]] == ["두부"]
    everyone = await _list(wired, shop_id, headers, "?include_passed=true")
    assert [(p["name"], p["passed_away"]) for p in everyone["items"][0]["pets"]] == [("콩이", True), ("두부", False)]
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)).status_code == 200

    # 잘못 등록한 아이를 지우고, 마지막 아이는 지울 수 없다.
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{dubu}", headers=headers)).status_code == 204
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/pets/{kong}", headers=headers)) == (409, "LAST_PET")

    # 번호를 바꾸면 검색도 새 번호를 따른다.
    changed = await wired.api.put(
        f"/v1/shops/{shop_id}/customers/{customer_id}",
        json={**CUSTOMER, "phone": "010-9999-0000"}, headers=headers,
    )
    assert changed.json()["customer"]["phone"] == "01099990000"
    assert [c["customer_id"] for c in (await _list(wired, shop_id, headers, "?q=0000"))["items"]] == [customer_id]
    assert (await _list(wired, shop_id, headers, "?q=5678"))["items"] == []

    # 익명화(C6) — 조회·검색·번호 조회에서 사라지고, 같은 번호로 다시 등록하면 새 고객이다(C3).
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204
    gone = [
        await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers),
        await wired.api.get(f"/v1/shops/{shop_id}/customers/lookup?phone=01099990000", headers=headers),
        await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers),
    ]
    assert [error_of(r) for r in gone] == [(404, "CUSTOMER_NOT_FOUND")] * 3
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/pets/{kong}", headers=headers)) == (404, "PET_NOT_FOUND")
    for query in ("", "?include_passed=true", "?q=김민지", "?q=0000", "?q=ㅋㅇ"):
        assert (await _list(wired, shop_id, headers, query))["items"] == [], query
    again, _ = await _register(wired, shop_id, headers, customer={"phone": "01099990000"})
    assert again != customer_id


async def test_직원은_등록하고_고치지만_고객을_삭제하지_못한다(wired):
    """C4 — customer:delete 는 사장만 가진다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    headers = bearer(staff["access_token"])

    customer_id, pet_id = await _register(wired, shop_id, headers)
    assert (await wired.api.put(f"/v1/shops/{shop_id}/customers/{customer_id}", json=CUSTOMER, headers=headers)).status_code == 200
    assert (await wired.api.post(f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": "두부"}, headers=headers)).status_code == 201
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{pet_id}", headers=headers)).status_code == 204
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)) == (403, "PERMISSION_DENIED")
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 200


async def test_내보낸_직원은_받은_토큰으로도_목록을_볼_수_없다(wired):
    """C5 — 매 요청의 매장 접근 확인이 막는다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    joined = await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))
    headers = bearer(staff["access_token"])
    assert (await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=headers)).status_code == 200

    member_path = f"/v1/shops/{shop_id}/members/{joined.json()['member_id']}"
    assert (await wired.api.delete(member_path, headers=bearer(owner["access_token"]))).status_code == 204
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/customers", headers=headers)) == (403, "NOT_A_MEMBER")


async def test_같은_번호와_질병_규칙_위반은_설계의_오류다(wired):
    """C2(순차)·C8 — 번호는 살아 있는 고객끼리 하나, 질병은 고르거나 '질병 없음' 중 하나."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    first, _ = await _register(wired, shop_id, headers)
    second, _ = await _register(wired, shop_id, headers, customer={"phone": "01011112222"})

    def post(customer=None, pet=None):
        return wired.api.post(
            f"/v1/shops/{shop_id}/customers",
            json={"customer": {**CUSTOMER, **(customer or {})}, "pet": {**PET, **(pet or {})}},
            headers=headers,
        )

    assert error_of(await post(customer={"phone": "01012345678"})) == (409, "CUSTOMER_PHONE_TAKEN")
    assert error_of(await wired.api.put(
        f"/v1/shops/{shop_id}/customers/{second}", json={**CUSTOMER, "phone": "010 1234 5678"}, headers=headers,
    )) == (409, "CUSTOMER_PHONE_TAKEN")
    assert error_of(await post(customer={"phone": "01055556666"}, pet={"no_known_conditions": False})) == (422, "PET_HEALTH_REQUIRED")
    assert error_of(await post(
        customer={"phone": "01055556666"}, pet={"conditions": [{"type_code": "allergy"}]},
    )) == (422, "PET_HEALTH_CONFLICT")
    assert error_of(await post(
        customer={"phone": "01055556666"},
        pet={"no_known_conditions": False, "conditions": [{"type_code": "flu"}]},
    )) == (422, "VALIDATION_ERROR")
    assert error_of(await post(customer={"phone": "5678"})) == (422, "VALIDATION_ERROR")
    assert error_of(await post(customer={"phone": "01055556666"}, pet={"birth_date": "2021-01-01"})) == (422, "VALIDATION_ERROR")
    assert (await _list(wired, shop_id, headers))["pet_count"] == 2   # 실패한 등록은 아무것도 남기지 않는다
    assert first != second


async def test_뒷자리_초성_여러_낱말_특수_문자로_찾는다(wired):
    """7.3 — 가족 카드 단위로 찾는다. 뒷자리가 같은 고객은 모두 나온다. C10 특수 문자는 글자 그대로다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    kim, _ = await _register(wired, shop_id, headers)
    park, _ = await _register(wired, shop_id, headers, customer={"name": "박서준", "phone": "01098765678"},
                              pet={"name": "보리"})
    percent, _ = await _register(wired, shop_id, headers, customer={"name": "100%보호자", "phone": "01011112222"},
                                 pet={"name": "구름"})

    async def found(q):
        return {c["customer_id"] for c in (await _list(wired, shop_id, headers, f"?q={q}"))["items"]}

    assert await found("5678") == {kim, park}
    assert await found("ㅋㅇ") == {kim}
    assert await found("5678%20보리") == {park}
    assert await found("%25") == {percent}
    assert await found("_") == set()
    names = [c["name"] for c in (await _list(wired, shop_id, headers, "?sort=name"))["items"]]
    # 한글끼리는 가나다순이다. 한글과 숫자·영문 사이의 순서는 DB 의 정렬 규칙(개발 DB 는 en_US.utf8 — 한글이 먼저)을 따른다.
    assert [n for n in names if n != "100%보호자"] == ["김민지", "박서준"]


async def test_목록은_30_가족씩_커서로_이어진다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    for i in range(31):
        await _register(wired, shop_id, headers, customer={"name": f"보호자{i:02d}", "phone": f"0101234{i:04d}"})

    first = await _list(wired, shop_id, headers, "?sort=name")
    assert len(first["items"]) == 30 and first["pet_count"] == 31
    second = await _list(wired, shop_id, headers, f"?sort=name&cursor={first['next_cursor']}")
    assert [c["name"] for c in second["items"]] == ["보호자30"] and second["next_cursor"] is None
    assert error_of(await wired.api.get(f"/v1/shops/{shop_id}/customers?cursor=broken", headers=headers)) == (422, "VALIDATION_ERROR")


async def test_질병_종류와_자기소개는_멤버에게_보인다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    types = await wired.api.get(f"/v1/shops/{shop_id}/pet-condition-types", headers=headers)
    assert [t["code"] for t in types.json()][-1] == "other" and len(types.json()) == 10
    myself = await wired.api.get(f"/v1/shops/{shop_id}/customers/myself", headers=headers)
    assert myself.status_code == 200   # /customers/{customer_id} 보다 먼저 걸린다(422 가 아니다)
    assert "/customers/lookup" in myself.json()["introduction"]


async def test_토큰_없는_요청은_고객_표면마다_401_이다(wired):
    requests = [
        ("GET", "/v1/shops/1/customers"), ("GET", "/v1/shops/1/customers/lookup?phone=01012345678"),
        ("POST", "/v1/shops/1/customers"), ("GET", "/v1/shops/1/customers/1"),
        ("PUT", "/v1/shops/1/customers/1"), ("DELETE", "/v1/shops/1/customers/1"),
        ("POST", "/v1/shops/1/customers/1/pets"), ("GET", "/v1/shops/1/pets/1"),
        ("PUT", "/v1/shops/1/pets/1"), ("DELETE", "/v1/shops/1/pets/1"),
        ("POST", "/v1/shops/1/pets/1/passed-away"), ("DELETE", "/v1/shops/1/pets/1/passed-away"),
        ("GET", "/v1/shops/1/pet-condition-types"), ("GET", "/v1/shops/1/customers/myself"),
    ]
    for method, path in requests:
        response = await wired.api.request(method, path, json={"customer": CUSTOMER, "pet": PET, **PET})
        assert error_of(response) == (401, "UNAUTHENTICATED"), f"{method} {path}"
```


- [ ] **Step 2: 돌려서 통과를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest tests/integration/test_customer_flow_wiring.py -q -p no:cacheprovider`
Expected: `9 passed`


- [ ] **Step 3: 판별력을 확인한다**

`main.py`에서 `app.include_router(lookup_customer_router)` 줄을 잠시 customer 묶음의 끝으로 옮기고 같은 명령을 돌린다 → `test_다른_매장의_고객과_반려동물에는_손댈_수_없다`와 `test_등록부터_익명화까지_돈다`가 실패해야 한다(`/customers/lookup`이 `/customers/{{customer_id}}`에 걸려 422 — C16). 되돌린다.


- [ ] **Step 4: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `408 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `183 passed`. 실패 0.


- [ ] **Step 5: 커밋**

```bash
git add backend/tests/integration/test_customer_flow_wiring.py
git commit -m "test(customer): 실제 배선 통합 테스트 — 테넌트 격리·익명화·권한·검색"
```

---

### Task 15: 두 세션 경합 테스트 — 동시 등록, 익명화 × 추가·수정, 마지막 두 마리

결정 003 의 교훈대로 HTTP 두 요청을 `gather`하지 않는다(로컬 Postgres 에서는 판별력이 없다). 세션 둘을 직접 열고, 막힌 쪽을 `asyncio.create_task`로 들고 있다가 0.5초 뒤에도 끝나지 않았는지(기다림) 보고, 앞선 세션을 커밋한 뒤 결과를 본다. **판별은 "기다렸다"와 "커밋 뒤의 결과" 두 단언이 함께 한다** — 검색 줄의 행 잠금이나 `pets` 행 잠금 때문에 잠금 코드가 없어도 기다릴 수 있다(외래 키 `KEY SHARE`의 거짓 통과와 같은 함정).

- C2: 같은 번호 동시 등록 → 늦은 쪽은 유일 색인에서 기다렸다가 `CustomerPhoneTakenError`, 고객 1명·검색 줄 1개.
- C14: 익명화가 고객 행을 쥔 동안 반려동물 추가 → 기다렸다가 `CustomerNotFoundError`, 이름 있는 반려동물 0·검색 줄 0. 반려동물 수정도 같은 결과(단 판별력 없음 — 테스트 설명 참고).
- C13: 마지막 두 마리 동시 삭제 → 늦은 쪽은 `LastPetError`, 한 마리가 남는다.

**Files:**
- Test: `backend/tests/integration/test_customer_locking.py`

**Interfaces:**
- Consumes: 인터랙터 `RegisterCustomerInteractor`·`DeleteCustomerInteractor`·`AddPetInteractor`·`UpdatePetInteractor`·`DeletePetInteractor`와 PG 구현 넷, `customer.tests.helpers.fakes.today`, `customer.tests.helpers.inputs`, `customer.tests.helpers.profiles`
- Produces: 없음

- [ ] **Step 1: 테스트를 쓴다**

`backend/tests/integration/test_customer_locking.py`:
```python
"""customer 의 경합 — 실제 두 세션으로 확인한다.

막힌 호출을 create_task 로 들고 있다가, 앞선 세션이 커밋한 뒤의 결과를 본다(결정 기록 003 의 교훈).
판별은 '기다렸다'와 '커밋 뒤의 결과' 두 단언이 함께 한다. 외래 키의 암묵적 잠금이나 검색 줄의 행 잠금
때문에 잠금 코드가 없어도 기다릴 수 있으므로, 기다림만으로는 판별하지 않는다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.add_pet_dto import AddPetCommand
from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.dtos.delete_pet_dto import DeletePetCommand
from customer.app.dtos.register_customer_dto import RegisterCustomerCommand
from customer.app.dtos.update_pet_dto import UpdatePetCommand
from customer.app.use_cases.add_pet_interactor import AddPetInteractor
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
from customer.app.use_cases.register_customer_interactor import RegisterCustomerInteractor
from customer.app.use_cases.update_pet_interactor import UpdatePetInteractor
from customer.domain.errors import (
    CustomerNotFoundError,
    CustomerPhoneTakenError,
    LastPetError,
    PetNotFoundError,
)
from customer.tests.helpers.fakes import today
from customer.tests.helpers.inputs import customer_input, pet_input
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
BLOCKED = 0.5   # 이만큼 기다려도 끝나지 않으면 잠금에서 기다리는 것으로 본다


def _repos(session):
    return (CustomerPgRepository(session), PetPgRepository(session),
            ConditionTypePgRepository(session), CustomerSearchPgAdapter(session))


def _register(session, name):
    customers, pets, types, search = _repos(session)
    return RegisterCustomerInteractor(customers, pets, types, search, today).register_customer(
        RegisterCustomerCommand(ctx=SHOP, customer=customer_input(name=name), pet=pet_input())
    )


async def _still_waiting(task) -> bool:
    await asyncio.sleep(BLOCKED)
    return not task.done()


async def _family(factory, pet_names=("콩이",)):
    async with factory() as setup:
        customer = await CustomerPgRepository(setup).create(SHOP, customer_profile())
        pets = [await PetPgRepository(setup).add(SHOP, customer.id, pet_profile(name=n)) for n in pet_names]
        await CustomerSearchPgAdapter(setup).rebuild_search_entry(SHOP, customer.id)
        await setup.commit()
    return customer.id, [p.id for p in pets]


async def _scalar(factory, sql, **params):
    async with factory() as check:
        return (await check.execute(text(sql), params)).scalar_one()


async def test_같은_번호의_동시_등록은_하나만_성공하고_늦은_쪽은_409_다(db_engine):
    """C2 — 늦은 쪽은 유일 색인에서 앞선 쪽의 커밋을 기다렸다가 CUSTOMER_PHONE_TAKEN 을 받는다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as first, factory() as second:
        await _register(first, "먼저 온 사람")
        late = asyncio.create_task(_register(second, "늦게 온 사람"))
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(CustomerPhoneTakenError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM customers") == 1
    assert await _scalar(factory, "SELECT name FROM customers") == "먼저 온 사람"
    assert await _scalar(factory, "SELECT count(*) FROM customer_search_entries") == 1


async def test_익명화가_고객을_쥔_동안_반려동물_추가는_기다리고_뒤에는_404_다(db_engine):
    """C14 — 잠금이 없으면 익명화한 고객에게 이름 있는 반려동물이 붙고 검색 줄이 되살아난다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, _ = await _family(factory)

    async with factory() as deleting, factory() as adding:
        customers, _, _, search = _repos(deleting)
        await DeleteCustomerInteractor(customers, search).delete_customer(
            DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id)
        )
        customers, pets, types, search = _repos(adding)
        add = asyncio.create_task(AddPetInteractor(customers, pets, types, search, today).add_pet(
            AddPetCommand(ctx=SHOP, customer_id=customer_id, pet=pet_input(name="두부"))
        ))
        assert await _still_waiting(add)

        await deleting.commit()
        with pytest.raises(CustomerNotFoundError):
            await add
        await adding.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM pets WHERE name IS NOT NULL") == 0
    assert await _scalar(factory, "SELECT count(*) FROM customer_search_entries") == 0


async def test_익명화가_고객을_쥔_동안_반려동물_수정은_기다리고_뒤에는_404_다(db_engine):
    """C14 — 반려동물 경로도 반려동물 → 고객 순서로 고객 행을 잠근다.

    판별력 주의: 익명화가 pets 행도 고치므로, lock_owner 의 잠금을 빼도 수정은 pets 행 잠금에서 기다렸다가
    다시 읽기(get)에서 404 가 되어 같은 결과가 나온다(변이로 확인함). 이 테스트는 결과를 지킬 뿐이고,
    lock_owner 잠금의 판별은 아래 LAST_PET 테스트가 한다.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (pet_id,) = await _family(factory)

    async with factory() as deleting, factory() as updating:
        customers, _, _, search = _repos(deleting)
        await DeleteCustomerInteractor(customers, search).delete_customer(
            DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id)
        )
        customers, pets, types, search = _repos(updating)
        update = asyncio.create_task(UpdatePetInteractor(customers, pets, types, search, today).update_pet(
            UpdatePetCommand(ctx=SHOP, pet_id=pet_id, pet=pet_input(name="되살린 이름"))
        ))
        assert await _still_waiting(update)

        await deleting.commit()
        with pytest.raises(PetNotFoundError):
            await update
        await updating.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM pets WHERE name IS NOT NULL") == 0
    assert await _scalar(factory, "SELECT count(*) FROM customer_search_entries") == 0


async def test_마지막_두_마리를_동시에_지우면_하나는_LAST_PET_이다(db_engine):
    """C13 — 고객 행을 잠근 뒤 센다. 잠금이 없으면 둘 다 '두 마리'로 보고 지워 반려동물 없는 가족이 남는다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong, dubu) = await _family(factory, pet_names=("콩이", "두부"))

    async with factory() as first, factory() as second:
        _, pets, _, search = _repos(first)
        await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=kong))
        _, pets, _, search = _repos(second)
        late = asyncio.create_task(
            DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=dubu))
        )
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(LastPetError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM pets WHERE customer_id = :id", id=customer_id) == 1
```


- [ ] **Step 2: 돌려서 통과를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest tests/integration/test_customer_locking.py -q -p no:cacheprovider`
Expected: `4 passed` (2초쯤 걸린다 — 테스트마다 0.5초 기다린다)


- [ ] **Step 3: 변이로 판별력을 확인한다**

하나씩 바꾸고 같은 명령을 돌린 뒤 되돌린다. 셋 다 실패해야 한다.
1. `alembic/versions/0005_customer_tables_and_seed.py`의 `uq_customers_shop_phone_active`에서 `unique=True,`를 지운다 → `test_같은_번호의_동시_등록은…` 실패(테스트 DB 는 세션마다 다시 만들어지므로 마이그레이션만 바꾸면 된다).
2. `add_pet_interactor.py`의 `self._customers.lock_active(`를 `self._customers.get_active(`로 → `test_익명화가_고객을_쥔_동안_반려동물_추가는…` 실패.
3. `pet_pg_repository.py`의 `lock_owner`에서 `.with_for_update(of=CustomerOrm)` 줄을 지운다 → `test_마지막_두_마리를_동시에_지우면…` 실패. (이때 `…반려동물_수정은…` 테스트는 통과한다 — 판별력이 없다는 설명 그대로다.)


- [ ] **Step 4: 전체 단위 테스트와 구조 계약을 돌린다 (통합 포함)**

Run (`infra/`에서): 단위 테스트 전체, 구조 계약, 통합 테스트 전체
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm --no-deps backend lint-imports --config .importlinter
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
```
Expected: 단위 `408 passed`, `Contracts: 6 kept, 0 broken.`, 통합 `187 passed`. 실패 0.


- [ ] **Step 5: 커밋**

```bash
git add backend/tests/integration/test_customer_locking.py
git commit -m "test(customer): 두 세션 경합 — 동시 등록, 익명화와 겹친 쓰기, 마지막 두 마리"
```

---

### Task 16: 검색 줄 재생성 스크립트, 흐름 확인 스크립트, 문서와 최종 검증

설계 6.4 의 "재생성 스크립트"(C11)와 10절의 흐름 확인 스크립트를 만들고, 스포크 규칙·하네스·결정 기록을 적는다. 마지막으로 개발 DB 에 `0005`를 올리고 게이트웨이 경유로 흐름을 돌린다 — **계획을 쓸 때 게이트웨이 경유는 검증하지 못했다**(대역 서버로만 확인). 설계는 `Pressable` 항목을 "결정 기록 004 의 남는 것"이라 했지만 004 에는 그 줄이 없다 — 005 에 고친 사실만 적는다.

**Files:**
- Create: `backend/scripts/rebuild_customer_search.py`
- Create: `backend/scripts/check_customer_flow.sh` (실행 권한)
- Create: `backend/apps/customer/_docs/CLAUDE.md`, `backend/apps/customer/CLAUDE.md` (→ `_docs/CLAUDE.md` 심볼릭 링크, tenancy 와 같다)
- Create: `_docs/decisions/005-customer-pet.md`
- Modify: `_docs/harness.md`, `README.md`
- Test: `backend/tests/test_rebuild_customer_search.py`

**Interfaces:**
- Consumes: Task 6 의 `CustomerSearchPgAdapter.rebuild_search_entry`, Task 4 의 `CustomerOrm`, `tests/integration/support.py`와 같은 흐름 스크립트 관례(`check_shop_flow.sh`)
- Produces: `scripts.rebuild_customer_search.rebuild_all(session: AsyncSession) -> int`(다시 만든 고객 수, 커밋은 부른 쪽)

- [ ] **Step 1: 재생성 스크립트의 실패하는 테스트를 쓴다**

`backend/tests/test_rebuild_customer_search.py`:
```python
"""검색 줄 재생성 스크립트 — 어긋난 줄을 원본대로 되돌리고, 익명화한 고객의 줄은 지운다."""
import pytest
from sqlalchemy import text

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
from scripts.rebuild_customer_search import rebuild_all

pytestmark = pytest.mark.integration


async def test_어긋난_검색_줄을_원본에서_다시_만든다(db_session):
    customers, pets = CustomerPgRepository(db_session), PetPgRepository(db_session)
    alive = await customers.create(ctx(shop_id=1), customer_profile())
    await pets.add(ctx(shop_id=1), alive.id, pet_profile())
    gone = await customers.create(ctx(shop_id=2), customer_profile(phone="01099998888"))
    await customers.anonymize(ctx(shop_id=2), gone.id)
    # 어긋난 상태: 살아 있는 고객의 줄은 없고, 익명화한 고객의 줄이 남아 있다.
    await db_session.execute(text(
        "INSERT INTO customer_search_entries (customer_id, shop_id, terms, phone_last4, sort_name, "
        "last_activity_at) VALUES (:id, 2, '옛 이름', '8888', '옛 이름', now())"
    ), {"id": gone.id})

    assert await rebuild_all(db_session) == 2
    rows = (await db_session.execute(text(
        "SELECT customer_id, shop_id, terms FROM customer_search_entries"
    ))).all()
    assert [tuple(r) for r in rows] == [(alive.id, 1, "김민지 ㄱㅁㅈ 콩이 ㅋㅇ 01012345678")]
    assert await rebuild_all(db_session) == 2   # 다시 돌려도 같다
```


- [ ] **Step 2: 돌려서 실패를 본다**

Run (`infra/`에서): `docker compose run --rm backend pytest tests/test_rebuild_customer_search.py -q -p no:cacheprovider`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.rebuild_customer_search'`


- [ ] **Step 3: 재생성 스크립트를 쓴다**

`backend/scripts/rebuild_customer_search.py`:
```python
"""고객 검색 줄(customer_search_entries)을 원본(customers·pets)에서 모두 다시 만든다. 여러 번 실행해도 결과가 같다.

검색 줄은 역정규화 표라 원본과 어긋나면 이 스크립트로 복구한다(설계 6.4). 익명화한 고객의 줄은 지운다.
사용: cd infra && docker compose run --rm backend python scripts/rebuild_customer_search.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from customer.adapter.outbound.orm.customer_orm import CustomerOrm
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from hub.app.dtos.shop_context import ShopContext


async def rebuild_all(session: AsyncSession) -> int:
    """모든 고객(익명화한 고객 포함)의 줄을 다시 만들고, 다시 만든 고객 수를 돌려준다. 커밋은 부른 쪽이 한다."""
    search = CustomerSearchPgAdapter(session)
    rows = (await session.execute(select(CustomerOrm.id, CustomerOrm.shop_id).order_by(CustomerOrm.id))).all()
    for customer_id, shop_id in rows:
        # 사람의 요청이 아니라 운영 작업이다. 멤버·권한 없이 그 고객의 매장으로만 범위를 정한다.
        ctx = ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset())
        await search.rebuild_search_entry(ctx, customer_id)
    return len(rows)


async def _run() -> int:
    engine = create_async_engine(DATABASE_URL)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            count = await rebuild_all(session)
            await session.commit()
            return count
    finally:
        await engine.dispose()


def main() -> None:
    print(f"고객 {asyncio.run(_run())}명의 검색 줄을 다시 만들었습니다.")


if __name__ == "__main__":
    main()
```


- [ ] **Step 4: 돌려서 통과를 본다**

Run: 같은 명령
Expected: `1 passed`


- [ ] **Step 5: 흐름 확인 스크립트를 쓴다**

`backend/scripts/check_customer_flow.sh`:
```bash
#!/usr/bin/env bash
# 개발 환경에서 고객 등록 → 번호 조회 → 반려동물 추가 → 검색 → 무지개다리 → 고객 삭제(익명화)를 끝까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_customer_flow.sh
# infra/ 에서 실행해야 한다 (운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저와 익명화한 고객이 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
LAST4="${PHONE: -4}"

# field <경로> — JSON 응답에서 값을 꺼낸다. 예: field "['customer']['customer_id']"
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
# call <메서드> <경로> <토큰> [본문] — 응답 본문을 출력한다
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
# status <메서드> <경로> <토큰> [본문] — 상태 코드만 출력한다
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }

pet() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,$2}"; }

op=$(login "cflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"고객흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "cflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "cflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
echo "통과  매장 $shop_id 에 사장과 직원이 있다"
S="/v1/shops/$shop_id"

expect "등록 전 번호 조회는 404" "$(status GET "$S/customers/lookup?phone=$PHONE" "$staff_token")" "404"
registered=$(call POST "$S/customers" "$staff_token" \
  "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":$(pet 콩이 '"no_known_conditions":true')}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']")
kong_id=$(echo "$registered" | field "['pets'][0]['pet_id']")
echo "통과  직원이 고객 $customer_id 와 첫 반려동물을 등록했다"
expect "같은 번호로 다시 등록하면 409" "$(status POST "$S/customers" "$staff_token" \
  "{\"customer\":{\"name\":\"다른사람\",\"phone\":\"$PHONE\",\"marketing_consent\":false},\"pet\":$(pet 두부 '"no_known_conditions":true')}")" "409"
expect "번호 조회는 보호자와 아이 이름을 준다" "$(call GET "$S/customers/lookup?phone=$PHONE" "$staff_token" | field "['pet_names']")" "['콩이']"

dubu_id=$(call POST "$S/customers/$customer_id/pets" "$staff_token" \
  "$(pet 두부 '"no_known_conditions":false,"conditions":[{"type_code":"patella_luxation","note":"2기"}]')" | field "['pet']['pet_id']")
echo "통과  반려동물 $dubu_id 을(를) 더했다"
expect "질병도 질병 없음도 아니면 422" "$(status PUT "$S/pets/$dubu_id" "$staff_token" "$(pet 두부 '"no_known_conditions":false')")" "422"

expect "뒷자리로 찾으면 가족이 나온다" "$(call GET "$S/customers?q=$LAST4" "$staff_token" | field "['items'][0]['customer_id']")" "$customer_id"
expect "초성 ㅋㅇ 로 찾으면 가족이 나온다" "$(call GET "$S/customers?q=%E3%85%8B%E3%85%87" "$staff_token" | field "['items'][0]['customer_id']")" "$customer_id"
expect "목록의 번호는 가려져 있다" "$(call GET "$S/customers" "$staff_token" | field "['items'][0]['phone_masked'][-4:]")" "$LAST4"
expect "목록 제목의 반려동물 수" "$(call GET "$S/customers" "$staff_token" | field "['pet_count']")" "2"

expect "무지개다리를 표시한다" "$(status POST "$S/pets/$kong_id/passed-away" "$staff_token")" "200"
expect "무지개다리 아이는 목록 기본에서 빠진다" "$(call GET "$S/customers" "$staff_token" | field "['pet_count']")" "1"
expect "잘못 등록한 아이를 지운다" "$(status DELETE "$S/pets/$dubu_id" "$staff_token")" "204"
expect "마지막 아이는 지울 수 없다" "$(status DELETE "$S/pets/$kong_id" "$staff_token")" "409"

expect "직원은 고객을 삭제할 수 없다" "$(status DELETE "$S/customers/$customer_id" "$staff_token")" "403"
expect "사장은 고객을 삭제한다" "$(status DELETE "$S/customers/$customer_id" "$owner_token")" "204"
expect "삭제한 고객은 조회되지 않는다" "$(status GET "$S/customers/$customer_id" "$owner_token")" "404"
expect "삭제한 고객은 번호 조회에 걸리지 않는다" "$(status GET "$S/customers/lookup?phone=$PHONE" "$owner_token")" "404"
expect "삭제한 고객은 검색에 걸리지 않는다" "$(call GET "$S/customers?q=$LAST4&include_passed=true" "$owner_token" | field "['items']")" "[]"

echo "전체 흐름 확인 완료"
```

Run (저장소 루트에서): `chmod +x backend/scripts/check_customer_flow.sh && bash -n backend/scripts/check_customer_flow.sh` → 출력 없음.


- [ ] **Step 6: 스포크 규칙을 적는다**

`backend/apps/customer/_docs/CLAUDE.md`:
```markdown
# customer — 고객(보호자), 반려동물, 질병, 검색

소유 데이터: `customers`, `pets`, `pet_condition_types`(시드), `pet_conditions`, `customer_search_entries`(검색용 역정규화).

- 고객(사람)이 기본이고 반려동물은 선택적인 하위 대상이다. 반려동물은 고객을 거쳐 매장에 속한다 — `pets`에 `shop_id`를 두지 않는다.
- `customers.shop_id`는 tenancy의 매장 ID지만 외래 키를 걸지 않는다. 스포크 안의 관계(고객 → 반려동물 → 질병)는 외래 키를 건다.
- 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다. 매장과 상관없는 `ConditionTypeRepository.list_all()`만 예외다. 반려동물은 언제나 반려동물 → 고객(살아 있음) → 매장 순서로 소속을 거른다. 다른 매장의 ID는 404다.
- 표는 3NF다. 역정규화는 `customer_search_entries` 하나뿐이고, 원본은 언제나 `customers`·`pets`다. 응답의 보호자·반려동물 정보는 원본에서 읽는다.
- **가족(고객·반려동물·질병)을 바꾸는 유스케이스는 맨 앞에서 고객 행을 잠근다.** 고객 경로는 `CustomerRepository.lock_active`, 반려동물 경로는 `PetRepository.lock_owner`(반려동물 → 고객 행). 잠금이 없으면 익명화와 겹친 반려동물 추가가 익명화한 고객에게 이름을 되살리고, 마지막 두 마리를 동시에 지워 반려동물 없는 가족이 남는다. 잠금 순서는 고객 행 → 반려동물 행이다. customer 경로는 tenancy의 행(유저·매장·멤버·초대)을 잠그지 않는다.
- 같은 트랜잭션 안에서 `CustomerSearchPort.rebuild_search_entry(ctx, customer_id)`로 그 가족의 검색 줄을 다시 만든다. 익명화한 고객이면 줄을 지운다. 어긋나면 `scripts/rebuild_customer_search.py`로 복구한다.
- 검색은 `CustomerSearchPort` 뒤에 있다(지금은 PostgreSQL `pg_trgm`). 전용 검색 엔진으로 바꿀 때 어댑터만 바꾼다. LIKE 특수 문자는 어댑터가 이스케이프한다.
- 전화번호는 숫자만 저장한다. 매장 안에서 살아 있는 고객끼리 유일하다(부분 유일 색인 `uq_customers_shop_phone_active` — 동시에 두 번 와도 하나만 성공, 늦은 쪽은 409). 보조 연락처는 중복 판단에 쓰지 않는다.
- 목록과 반려동물 상세의 번호는 가린다(`010-12··-5678`). 전체 번호는 고객 상세에서만 준다. 전화번호·이름을 로그에 남기지 않는다. 검색어와 번호 조회는 쿼리 문자열로 오므로 API 프로세스가 접근 로그의 쿼리를 가린다(`core/access_log.py`).
- 고객 삭제는 익명화다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행을 지우고 `deleted_at`을 찍는다. 행과 틀(종류·품종·성별 등)은 남긴다. 익명화한 고객은 모든 조회·검색·번호 조회에서 없는 것으로 본다.
- 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
- 새 허브 포트는 없다. 다른 스포크와 협력할 일이 생기면 허브에 포트를 둔다.
```

Run (저장소 루트에서): `ln -s _docs/CLAUDE.md backend/apps/customer/CLAUDE.md`


- [ ] **Step 7: 하네스 문서와 README 를 고친다**

`_docs/harness.md`:
```diff
@@ -11,13 +11,15 @@
 | 로그인 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_auth_flow.sh` |
 | 매장 개설·합류 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_shop_flow.sh` — 개발 DB에 확인용 매장과 유저가 남는다 |
 | 회원 탈퇴 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_account_flow.sh` — 개발 DB에 "탈퇴한 사용자" 행이 남는다 |
+| 고객·반려동물 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_customer_flow.sh` — 개발 DB에 확인용 매장·유저와 익명화한 고객이 남는다 |
+| 고객 검색 줄 재생성 | `docker compose run --rm backend python scripts/rebuild_customer_search.py` (검색 줄이 원본과 어긋났을 때) |
 | 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
 | 앱 정적 분석 | `flutter analyze` (`app/`에서, 경고 0) |
 | 앱 테스트 (위젯·골든·`ApiClient` 포함) | `flutter test` (`app/`에서) |
 | 앱 골든 갱신 | `flutter test --update-goldens` (`app/`에서, 의도해서 바꿀 때만) |
 | 앱 개발용 실행 | `app/tool/run_dev.sh` (백엔드를 `infra/`에서 먼저 띄운 뒤) |
 
-- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`)와 마이그레이션 버전 표(`alembic_version`)를 뺀 모든 표를 비운다.
+- 통합 테스트는 별도 데이터베이스 `chagocnote_test`를 쓴다. 개발 데이터를 건드리지 않는다. pytest가 세션마다 한 번 `scripts/prepare_test_db.py`를 돌려 스키마를 비우고 `alembic upgrade head`로 다시 만든다. 테스트 사이에는 시드 표(`roles`, `permissions`, `role_permissions`, `pet_condition_types`)와 마이그레이션 버전 표(`alembic_version`)를 뺀 모든 표를 비운다.
 - 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 마이그레이션 결과와 ORM이 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다.
 - 구조 위반은 테스트가 아니라 import-linter가 잡는다. 구조를 건드린 변경은 테스트와 구조 계약을 둘 다 돌린다. 계약은 6종이다 — 설계 문서가 말하는 5종에 "core는 스포크를 import하지 않는다"를 하네스에서 더했다.
 - 라우터를 추가하거나 옮긴 변경은 라우트 표를 변경 전후로 비교한다.
@@ -27,3 +29,5 @@
 - 허브 포트 자리를 새로 만들어도 더할 목록은 없다. `tests/route_inspection.py`가 두 앱의 라우트 의존성 트리를 훑어 ① 채우지 않은 허브 포트 자리 ② `{shop_id}` 경로인데 `get_shop_context`를 거치지 않는 라우트 ③ `/v1/platform/` 경로인데 `require_operator`를 거치지 않는 라우트를 잡는다. API 프로세스는 `tests/test_hub_port_binding.py`가, 인증 프로세스는 `tests/integration/test_route_wiring.py`가 돌린다.
 - 권한이나 불변식이 걸린 슬라이스를 계획할 때는 악의적이거나 운 나쁜 시나리오(내보내진 사람이 쥔 것, 같은 요청이 동시에 두 번, 읽기와 쓰기 사이)를 먼저 표로 적고, 각각을 막는 코드와 테스트를 작업에 넣는다. 작업별 검토는 계획서와의 일치가 아니라 그 표를 기준으로 한다.
 - 통합 테스트에서 두 번째 로그인 수단이 필요하면 `fake_kakao` 픽스처를 쓴다.
+- 마이그레이션에 시드 표를 새로 만들면 루트 `conftest.py`의 `_KEEP_TABLES`에 더한다. 빠뜨리면 첫 테스트가 시드를 비워 그다음 테스트부터 실패한다.
+- 두 세션 경합 테스트는 막힌 호출을 `asyncio.create_task`로 들고 있다가 앞선 세션이 커밋한 뒤의 결과를 본다. "기다렸다"만으로 판별하지 않는다 — 외래 키의 암묵적 잠금이나 같은 행의 다른 잠금 때문에 잠금 코드가 없어도 기다릴 수 있다. 잠금 코드를 빼는 변이로 테스트가 실패하는지 확인한다.
```

`README.md`:
```diff
@@ -18,6 +18,7 @@
     bash ../backend/scripts/check_auth_flow.sh                                      # 로그인 흐름 확인
     bash ../backend/scripts/check_shop_flow.sh                                      # 매장 개설·합류 흐름 확인
     bash ../backend/scripts/check_account_flow.sh                                   # 회원 탈퇴 흐름 확인
+    bash ../backend/scripts/check_customer_flow.sh                                  # 고객·반려동물 흐름 확인
 
 개발 환경에서는 제공자 `dev`로 이름만 넣어 로그인한다. 운영자는 `docker compose run --rm backend python scripts/grant_operator.py <user_id>`로 지정한다.
```


- [ ] **Step 8: 결정 기록을 남긴다**

`_docs/decisions/005-customer-pet.md`:
```markdown
# 005 — 고객·반려동물과 기본 검색에서 내린 결정

- 날짜: 2026-09-22
- 대상 브랜치: `feat/customer-2a-backend` (②-1 백엔드). ②-2 앱이 끝나면 같은 문서에 앱 몫을 더한다.
- 근거: 설계 `docs/superpowers/specs/2026-09-22-customer-pet-design.md`, 계획 `docs/superpowers/plans/2026-09-22-customer-2a-backend.md`

## 무엇을 만들었나 (②-1)

`backend/apps/customer` 스포크를 API 프로세스에 붙였다. 엔드포인트 14개(설계 5절 표 전부 — 목록·번호 조회·등록·고객 상세·수정·익명화 삭제·반려동물 추가·상세·수정·무지개다리·되돌리기·삭제·질병 종류·자기소개), 마이그레이션 `0005`(표 5개, 질병 종류 시드 10개, `pg_trgm`), 검색 포트 `CustomerSearchPort`와 PostgreSQL 구현, 검색 줄 재생성 스크립트, 흐름 확인 스크립트 `check_customer_flow.sh`. 앱 쪽은 `Pressable`의 의미 노드 경계 하나만 고쳤다 — `Semantics(container: true)`로 스크린리더 포커스와 이름표 탭 위치가 행 전체 폭이 아니라 버튼 크기(최소 44×44)로 잡힌다. 설계 3.1 은 이 항목을 "결정 기록 004 의 남는 것"이라 적었지만 004 에는 그 줄이 없었다.

## 가족을 바꾸는 쓰기는 고객 행을 먼저 잠근다

설계 9절 표에 없던 경합 두 개를 계획을 쓰며 찾았다.
- **익명화와 겹친 반려동물 추가(C14).** `pets` INSERT 는 `customers` 행에 `KEY SHARE`만 걸고, 익명화의 `UPDATE customers`(키가 아닌 칸)는 `NO KEY UPDATE`라 서로 막지 않는다. 잠금이 없으면 익명화가 커밋된 뒤 추가도 커밋되어 익명화한 고객에게 이름 있는 반려동물이 붙고, 검색 줄이 되살아난다.
- **마지막 두 마리 동시 삭제(C13).** 둘 다 "두 마리"로 세고 지워 반려동물 없는 가족이 남는다(목록은 반려동물 중심이라 그 가족이 보이지 않는다).

그래서 가족을 바꾸는 유스케이스는 맨 앞에서 고객 행을 `FOR UPDATE`로 잠그고 다시 읽는다(`lock_active`, 반려동물 경로는 `lock_owner`). 잠금을 기다리는 사이 익명화됐으면 PostgreSQL 이 풀려난 뒤 `deleted_at IS NULL` 조건을 다시 평가해 행이 빠지므로 404 가 된다. 두 세션 테스트는 잠금을 빼는 변이로 실패하는 것을 확인했다. 반려동물 수정·무지개다리는 익명화가 `pets` 행도 고치기 때문에 잠금 없이도 같은 결과가 나온다 — 그 테스트는 결과를 지킬 뿐 판별력은 없다고 테스트 설명에 적었다.

## 접근 로그의 쿼리 문자열을 가린다

번호 조회(`?phone=`)와 검색(`?q=` — 이름·번호 뒷자리)은 설계대로 GET 쿼리로 받는다. uvicorn 의 접근 로그가 쿼리를 그대로 남기므로(C7 "로그 금지"에 어긋남) API 프로세스가 import 될 때 `uvicorn.access` 로거에 쿼리를 `?[가림]`으로 바꾸는 필터를 단다(`core/access_log.py`). 경로는 남는다. 게이트웨이(Caddy)는 접근 로그를 켜지 않았다. 검토한 다른 안: 번호 조회를 POST 로 바꾸기(설계의 API 모양이 바뀌고 검색어 문제는 그대로 남는다), 접근 로그 끄기(경로까지 사라진다).

## 계획에서 새로 정한 것

설계의 빈틈을 가장 작게 메운 것이다. 계획서 머리말 "이 계획에서 새로 정한 것"과 같다.
- 뒷자리 검색은 "4자리 이하 숫자 → 번호 뒷자리가 그 숫자로 시작"이다(치는 중인 56 도 5678 을 찾는다). 5자리 이상은 전체 번호 부분 일치.
- 가나다순의 키는 보호자 이름이다. 한글과 숫자·영문 사이의 순서는 DB 정렬 규칙(개발 DB `en_US.utf8` — 한글이 먼저)을 따른다.
- 최근순의 키는 고객과 그 반려동물의 `updated_at` 가운데 가장 늦은 값이다. 수정(PUT)은 값이 같아도 `updated_at`을 새로 찍는다. 반려동물 삭제는 활동으로 치지 않는다.
- 나이 표시: 생일이 있으면 만 나이(1살 전에는 "N개월"), 태어난 해만 있으면 해의 차이("1살 미만"), 둘 다 없으면 "나이 모름". 기준 날짜는 한국 시각의 오늘이다.
- 목록 응답에 `pet_count`(검색·무지개다리 조건에 맞는 반려동물 수 — 앱 제목 "고객 N마리")를 더했다.
- 번호 조회의 `pet_names`에는 무지개다리 아이를 넣지 않는다.
- 무지개다리를 다시 누르면 처음 시각을 지킨다.
- 전화번호 형식: 휴대전화(010·011·016~019), 서울(02), 지역 번호(031~064), 인터넷 전화(070). `+82` 표기는 받지 않는다.
- 질병 항목은 한 번에 20개까지. 모르는 질병 종류, 기타가 아닌데 이름을 넣은 것, 같은 정해진 질병 두 번은 422 `VALIDATION_ERROR`.
- 문자열 칸은 기존 관례대로 길이 제한이 있는 `varchar`다(설계 표의 `text` 대신). 전화번호 칸은 11자.

## 남는 것 — 알고 미룬다

- **낡은 `ShopContext`로 끝나는 쓰기.** 요청 가드가 소속을 확인한 뒤 고객 행 잠금을 기다리는 사이 내보내진 직원의 요청은 그대로 끝난다(tenancy 의 `update_shop`과 같은 모양, 003 의 "남는 것"). 고객 쓰기는 매장 행을 잠그지 않으므로 행위자 재확인을 넣으려면 잠금 순서를 새로 정해야 한다.
- **검색 줄의 반려동물 이름에는 무지개다리 아이도 들어간다.** 무지개다리 아이 이름으로 찾으면 그 가족 카드가 나오지만, 기본 목록에서는 그 아이가 카드에 보이지 않는다.
- **질병 메모·반려동물 메모에 개인정보를 적는 것은 막지 않는다.** 익명화 때 함께 지워진다.
```

작업별 검토에서 계획서와 다르게 고친 것이 있으면 `## 계획에서 새로 정한 것` 다음에 `## 실행 중 바뀐 것` 절을 만들어 한 줄씩 적는다(없으면 만들지 않는다).


- [ ] **Step 9: 최종 검증 — 테스트**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```
Expected: 단위 `408 passed`, 통합 `188 passed`, `Contracts: 6 kept, 0 broken.` 실패 0. (`app/`의 `flutter analyze`·`flutter test`는 Task 1 이후 바뀐 것이 없다 — 0건·240개.)


- [ ] **Step 10: 최종 검증 — 라우트 표**

Run: `docker compose run --rm --no-deps auth python scripts/print_routes.py | grep -E 'customers|pets|pet-condition'`
Expected: 14줄, 모두 `backend` 프로세스다.
```
backend  GET     /v1/shops/{shop_id}/customers                list_customers
backend  POST    /v1/shops/{shop_id}/customers                register_customer
backend  GET     /v1/shops/{shop_id}/customers/lookup         lookup_customer
backend  GET     /v1/shops/{shop_id}/customers/myself         introduce_myself
backend  DELETE  /v1/shops/{shop_id}/customers/{customer_id}  delete_customer
backend  GET     /v1/shops/{shop_id}/customers/{customer_id}  get_customer
backend  PUT     /v1/shops/{shop_id}/customers/{customer_id}  update_customer
backend  POST    /v1/shops/{shop_id}/customers/{customer_id}/pets add_pet
backend  GET     /v1/shops/{shop_id}/pet-condition-types      list_pet_condition_types
backend  DELETE  /v1/shops/{shop_id}/pets/{pet_id}            delete_pet
backend  GET     /v1/shops/{shop_id}/pets/{pet_id}            get_pet
backend  PUT     /v1/shops/{shop_id}/pets/{pet_id}            update_pet
backend  DELETE  /v1/shops/{shop_id}/pets/{pet_id}/passed-away unmark_pet_passed_away
backend  POST    /v1/shops/{shop_id}/pets/{pet_id}/passed-away mark_pet_passed_away
```
나머지 줄(기존 경로)은 시작 전과 같다.


- [ ] **Step 11: 개발 DB 에 0005 를 올리고 게이트웨이로 흐름을 돌린다**

Run (`infra/`에서):
```bash
docker compose restart backend          # 시작 명령이 alembic upgrade head 를 돈다 — 개발 DB 에 표를 더할 뿐이다
docker compose run --rm backend alembic current
bash ../backend/scripts/check_customer_flow.sh
docker compose logs backend --since 10m | grep -c 'phone=' || true
```
Expected: `0005 (head)`; 스크립트가 `통과` 20줄 뒤 `전체 흐름 확인 완료`로 끝난다; 마지막 명령은 `0`(접근 로그에 번호가 남지 않았다 — `lookup?[가림]`으로 찍힌다). 개발 DB 에 확인용 매장·유저와 익명화한 고객이 남는다.


- [ ] **Step 12: 커밋**

```bash
git add backend/scripts/rebuild_customer_search.py backend/tests/test_rebuild_customer_search.py backend/scripts/check_customer_flow.sh backend/apps/customer/_docs backend/apps/customer/CLAUDE.md _docs/harness.md _docs/decisions/005-customer-pet.md README.md
git commit -m "docs(customer): 검색 줄 재생성·흐름 확인 스크립트, 스포크 규칙, 하네스, 결정 기록 005"
```

---

## ②-2(앱)로 넘기는 것

이 계획이 끝나면 ②-2 가 부를 API 가 모두 있다. 앱이 알아야 할 것:

1. **요청 본문.** 등록 `POST …/customers` 는 `{"customer": {name, phone, phone_alt?, marketing_consent, memo?}, "pet": {name, species: "dog"|"cat", breed, sex: "female"|"male", neutered, birth_date?(YYYY-MM-DD) | birth_year?, weight_kg(소수 한 자리), no_known_conditions, conditions: [{type_code, custom_label?, note?}], memo?}}`. 보호자 수정·반려동물 추가·수정은 각 폼 하나를 그대로 보낸다(PUT 은 전체 교체, 질병 목록도 통째로). 불리언은 JSON `true`/`false`만 받는다. 빈 문자열은 "없음"이 된다. 전화번호는 하이픈을 넣어 보내도 된다(서버가 숫자만 남긴다).
2. **응답 모양.** 고객 상세 `{customer: {customer_id, name, phone(전체), phone_alt, marketing_consent, marketing_consent_changed_at, memo}, pets: [pet]}`, 반려동물 상세 `{pet, owner: {customer_id, name, phone_masked}, siblings: [{pet_id, name, species, passed_away}]}`, pet 은 `{pet_id, customer_id, name, species, breed, sex, neutered, birth_date, birth_year, age_label, weight_kg(숫자), no_known_conditions, has_conditions, conditions: [{type_code, label, custom_label, note}], memo, passed_away_at}`. 목록 `{items: [{customer_id, name, phone_masked, pets: [{pet_id, name, species, breed, age_label, has_conditions, passed_away}]}], next_cursor, pet_count}` — 제목 "고객 N마리"는 `pet_count`, 다음 쪽은 `cursor=next_cursor`(정렬을 바꾸면 커서를 버린다 — 다른 정렬의 커서는 422).
3. **오류 문구 표에 더할 코드:** `CUSTOMER_NOT_FOUND`·`PET_NOT_FOUND`(404), `CUSTOMER_PHONE_TAKEN`·`LAST_PET`(409), `PET_HEALTH_REQUIRED`·`PET_HEALTH_CONFLICT`(422). 입력 규칙 위반은 `VALIDATION_ERROR`(422)다.
4. **번호 조회 404 는 오류가 아니라 "새 번호"다**(등록 1단계). 200 이면 "이미 등록된 번호예요 — {name}({pet_names})"와 "이 보호자에게 반려동물 추가"로 간다.
5. **전체 번호는 고객 상세에서만 온다.** 목록·반려동물 상세의 번호는 이미 가려져 있다. 앱은 번호를 로그·print 로 남기지 않는다.
6. **질병 칩은 `GET …/pet-condition-types`의 순서대로.** "기타"(`other`)만 직접 입력 이름이 있다. 질병이 없으면 "질병 없음"을 눌러야 저장된다(`no_known_conditions: true`).
7. **검색어는 서버가 해석한다** — 숫자 4자리 이하는 뒷자리, 그 이상은 번호, 그 밖은 이름·초성, 공백으로 나눈 낱말은 모두 맞아야 한다. 늦게 온 옛 결과를 버리는 것(C12)과 조합이 끝난 뒤 0.3초 쉬는 것은 앱 몫이다.
8. **직원에게 고객 삭제 버튼을 보이지 않는다**(서버는 403). 반려동물 삭제·무지개다리는 직원도 된다. 마지막 반려동물 삭제의 `LAST_PET`에는 고객 삭제를 안내한다.
