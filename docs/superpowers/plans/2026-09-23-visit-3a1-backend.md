# 차곡노트 ③-A 예약·방문 — 계획 ③-A1: 백엔드 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 매장 멤버가 반려동물(또는 보호자만)의 방문을 예약·수정·옮기고 시작·완료·취소·노쇼·되돌리기로 상태를 바꾸며, 하루 목록·월 달력·시간 칸 경고·"지난번처럼"·다음 예약 초안을 쓰고, 사장이 매장 일정과 메뉴표를 관리하는 백엔드 `visit` 스포크를 만든다. customer 는 방문을 보고 반려동물 삭제·무지개다리·익명화를 막고 최근 방문순으로 정렬한다.

**Architecture:** 새 스포크 `backend/apps/visit`를 API 프로세스(`main.py`)에 붙인다. 경로는 모두 `/v1/shops/{shop_id}` 아래이고 `core/shop_guard.py`로 `ShopContext`(이 계획에서 매장 시간대가 실린다)를 받는다. 유스케이스 20개가 수직 슬라이스 1:1로 있고 상태 전이는 `visit/domain/state/`(State 패턴)다. visit 과 customer 는 서로를 import 하지 않고 허브 포트 둘로 협력한다 — `CustomerDirectoryPort`(customer 구현: 가족 잠금·요약·마지막 방문 시각)와 `VisitLedgerPort`(visit 구현: 방문 있음·앞으로의 예약·노쇼·메모 비우기). 방문 표에는 고객으로 가는 외래 키가 없어서, 방문을 쓰는 모든 경로는 맨 앞에서 허브 포트로 **고객 행을 잠그고** 그다음 방문 행을 ID 오름차순으로 잠근다.

**Tech Stack:** Python 3.13 · FastAPI · SQLAlchemy 2.0(asyncio) + asyncpg · Alembic · Pydantic 2 · PostgreSQL 17 · `zoneinfo`(표준 라이브러리, 시스템 시간대 데이터) · import-linter 2 · pytest + pytest-asyncio · Docker Compose

**Spec:** `docs/superpowers/specs/2026-09-23-visit-reservation-design.md` — 이 계획은 12절의 "③-A1 백엔드"다: 3.1절의 백엔드 몫(1~4·6, 5 의 customer 변경), 4~6절, 8절의 API(③-A3 몫인 `POST /visit-drafts` 제외), 10절 위협 점검표의 백엔드 몫, 11절의 백엔드 테스트. 실행자는 설계 문서와 `_docs/architecture.md`, `_docs/harness.md`, `_docs/decisions/003-account-lifecycle.md`(두 세션 경합 테스트의 교훈), `_docs/decisions/005-customer-pet.md`(가족 잠금, 검색 줄, 제어 문자·`hide_parameters`)를 함께 읽는다.

**계획의 위치:** ③-A 의 구현 계획 세 개 가운데 첫 번째다. **③-A1(이 문서, 백엔드)** → ③-A2(앱: 캘린더 탭·하루 화면·예약 2단계·방문 상세·설정 화면, 시뮬레이터 흐름 확인) → ③-A3(카톡 예약 초안: 해석기·초안 API·붙여넣기·공유 확장). 이 계획이 끝나면 ③-A2 가 부를 API 가 모두 있다. 결정 기록 006 은 이 계획이 백엔드 몫을 쓰고 ③-A2·③-A3 이 더한다.

## Global Constraints

작업 규칙
- 모든 경로는 저장소 루트(`com.chagocnote/`) 기준 상대 경로다. 절대 경로를 코드나 설정에 쓰지 않는다.
- 작업 브랜치는 `feat/visit-3a1-backend`다(설계 커밋 `f108b2f`가 있는 브랜치). `main`에서 직접 작업하지 않는다.
- **커밋은 사용자가 작업 단위 커밋을 허용한 경우에만 한다.** 허용하지 않았으면 각 작업의 마지막 "커밋" 단계를 건너뛰고 바뀐 파일 목록만 보고한다. 푸시는 하지 않는다. CI 는 없다 — 검증은 로컬에서 한다.
- 주석·문서·테스트 이름·커밋 메시지는 한국어다. 커밋은 `type(scope): 요약` 형식이다.
- **Hiss Haus는 플랫폼 이름이 아니라 첫 입점 매장 이름이다.** 테스트의 매장 이름으로 쓰는 것은 괜찮다.
- 이 계획은 새 의존성을 추가하지 않는다(`requirements.txt` 그대로). 시간대는 표준 라이브러리 `zoneinfo`와 컨테이너의 시스템 시간대 데이터(`/usr/share/zoneinfo`)로 계산한다 — `tzdata` 패키지를 더하지 않는다.
- 백엔드 명령은 전부 `infra/`에서 `docker compose run --rm backend …`로 돌린다. 맥에 파이썬 환경을 만들지 않는다.
- **볼륨 삭제, `docker compose down -v`, 개발 DB 에서의 `alembic downgrade`는 실행하지 않는다.** 개발 DB 스키마는 Task 15 에서 `docker compose restart backend`로 한 번 올린다 — 표와 칸을 더할 뿐이다.
- `load_dotenv`·`os.getenv`·`os.environ`은 `backend/core/singleton/secret_manager.py`에서만 쓴다.
- 비밀값과 토큰 원문을 로그·테스트 출력·문서에 남기지 않는다. `.env*` 파일 내용을 출력하지 않는다. **고객의 전화번호·이름도 로그에 남기지 않는다.** 새 스크립트의 엔진은 `hide_parameters=True`다(005).
- 일어날 수 없는 상황에 대한 방어 코드를 넣지 않는다.

구조 (`_docs/architecture.md` 그대로)
- 스포크 안은 `adapter → app → domain` 방향으로만 의존한다. `dependencies/`는 조립 전용이다.
- 수직 슬라이스 1:1: 유스케이스마다 router·schema·dto·input 포트·interactor·provider·interactor 테스트를 하나씩 둔다. 요청 본문이 없는 슬라이스는 schema 를 생략할 수 있다(`delete_closed_date`). 여러 슬라이스가 함께 쓰는 응답 모양은 도메인 말로 이름 짓는다(`visit_view_dto.py`와 짝인 `visit_view_schema.py`, `schedule_view_dto.py`, `menu_view_dto.py`).
- 유스케이스는 app DTO(frozen dataclass)를 받는다. 스키마와 DTO 사이의 변환은 라우터가 한다. 아웃바운드 포트는 인터랙터가 실제로 호출하는 메서드만 가진다 — `VisitRepository`는 작업마다 필요한 메서드만큼 자란다.
- 새 라우터 묶음에는 `GET <prefix>/myself`를 둔다(`/v1/shops/{shop_id}/visits/myself`, 번호 5).
- **스포크끼리 import 하지 않는다. `dependencies/`도 예외가 아니다.** 다른 스포크가 구현한 허브 포트는 소비하는 스포크의 `dependencies/hub_ports.py`에 "자리" 함수(RuntimeError)를 두고 `main.py`가 `app.dependency_overrides[자리] = 구현 프로바이더`로 꽂는다(결정 002). 허브 포트를 구현하는 슬라이스는 HTTP 없이 인터랙터가 허브 포트 ABC 를 직접 상속한다.
- `app`·`domain`은 `fastapi`, `sqlalchemy`, `redis`, `httpx`, `jose`, `cryptography`를 import 하지 않는다. `domain`은 `pydantic`과 `core`도 import 하지 않는다(표준 라이브러리만). 새 스포크 `visit`을 구조 계약 여섯에 모두 더한다(Task 2). 계약 6종이 그대로 통과해야 한다.
- 새 GoF 폴더는 `visit/domain/state/`(State) 하나다 — 대응표의 "(예정)"을 지운다(Task 15). 그 밖의 새 폴더 이름은 통상 이름(`services`, `pg`, `mappers`, `orm`)만 쓴다.
- 스포크마다 `_docs/CLAUDE.md`와 그것을 가리키는 심볼릭 링크 `CLAUDE.md`를 둔다(Task 15).

데이터 (설계 5절)
- **모든 표는 3NF 다.** 역정규화는 `visits.customer_id`·`visits.shop_id`(설계 5.3 — 다른 스포크라 조인할 수 없다)와 `customer_search_entries.last_visit_at`(최근 방문순 색인) 둘뿐이다. 끝 시각·가족 묶음·노쇼 횟수·지난번처럼·주기·정리 안 됨은 저장하지 않고 계산한다.
- `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키 없이 색인만 둔다. 스포크 안의 관계(설정 ← 쉬는 요일·휴무·메뉴, 방문 ← 방문 메뉴 → 메뉴)는 외래 키를 건다.
- 설계 5.1절의 CHECK·부분 유일 색인을 그대로 만든다. 마이그레이션은 손으로 쓴다. `tests/test_schema_drift.py`가 ORM 과 어긋나면 실패한다. 새 ORM 모듈은 `backend/orm_registry.py`에 등록한다. 시드 표는 없다(`_KEEP_TABLES` 그대로).

행동 규칙
- **매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.** 다른 매장의 방문·메뉴 ID 는 404 다(존재 여부를 알리지 않는다). 요청 본문의 메뉴가 이 매장의 보관하지 않은 메뉴가 아니면 422 `MENU_NOT_FOUND`다.
- **방문을 쓰는 유스케이스(등록·수정·옮기기·상태 전이)는 맨 앞에서 `CustomerDirectoryPort.lock_family`로 고객 행을 잠그고**, 그다음 방문 행을 ID 오름차순으로 잠근 뒤 다시 읽는다(`visit/app/services/visit_locking.py`). customer 쪽 익명화·무지개다리·반려동물 삭제는 고객 행을 먼저 잠근 뒤 `VisitLedgerPort`로 묻는다. 잠금 순서는 **고객 행 → 방문 행**이다(기존 유저 → 매장 → 멤버 → 초대와 겹치는 경로는 없다). 잠금을 쥔 채 외부 HTTP 를 부르지 않는다(이 계획에는 외부 HTTP 가 없다).
- 겹침·휴무·영업시간 밖은 막지 않는 **경고**다. 판단은 `visit_schedule.warnings_for` 한 곳에만 있다.
- 요청 시각은 시간대가 붙어 와야 하고(`AwareDatetime`), 응답 시각은 매장 시간대로 나간다. "오늘"과 하루의 경계는 매장 시간대로 센다.
- 오류 본문은 `{"code", "message"}`다. 도메인 규칙 위반은 도메인 예외로 던지고 `error_map.py`가 HTTP 상태로 바꾼다. 새 코드 — visit: `VISIT_NOT_FOUND`(404), `MENU_NOT_FOUND`(404 경로 / 422 본문), `VISIT_STATE_CONFLICT`·`VISIT_NOT_YET`·`VISIT_DUPLICATE`·`MENU_NAME_TAKEN`(409), `VISIT_CROSSES_MIDNIGHT`·`VISIT_GROUP_MISMATCH`(422); customer: `PET_HAS_VISITS`·`PET_HAS_UPCOMING_VISITS`·`CUSTOMER_HAS_UPCOMING_VISITS`(409), `PET_PASSED_AWAY`(422). 그 밖의 입력 규칙 위반은 422 `VALIDATION_ERROR`다. 문자열 입력은 NUL·제어 문자를 422 로 막고(메모만 개행 허용), 정수·불리언은 `StrictInt`·`StrictBool`이다.
- 테스트는 mock 프레임워크 대신 스텁 구현을 쓴다(`visit/tests/helpers/fakes.py` — 호출 순서를 `Journal`에 남긴다). 실제 DB 에 붙는 테스트는 `integration` 마커를 단다. 두 세션 경합 테스트는 "막힌 호출을 `create_task`로 들고 있다가 앞선 세션의 커밋 뒤 결과를 본다" 방식이고, 잠금 코드를 빼는 변이로 실패하는지 확인한다(결정 003).
- I/O 는 `async def`, CPU 작업은 `def`다. 포트와 구현체의 `def`/`async def`를 일치시킨다.

검증 명령의 줄임말 (`infra/`에서)
- **단위 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"`
- **통합 테스트 전체**: `docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration`
- **구조 계약**: `docker compose run --rm --no-deps backend lint-imports --config .importlinter`
- 파일·폴더 하나만: `docker compose run --rm backend pytest <backend/ 기준 경로> -q -p no:cacheprovider` (통합 테스트 파일이면 마커 없이 그대로 돈다)

## 이 계획에서 새로 정한 것

설계와 모순되는 것은 없다. 설계의 빈틈을 가장 작게 메운 것과 코드를 쓰며 찾은 것이다. 결정 기록 006(Task 15)에 같은 내용을 옮긴다.

1. **`ShopContext.timezone`의 기본값은 `"Asia/Seoul"`이다**(`shops.timezone`의 기본값과 같다). 매장 접근 확인은 언제나 DB 값을 채우고, 기본값은 이미 있는 테스트의 컨텍스트 생성 20여 곳을 건드리지 않으려는 것이다.
2. **시각은 시간대를 붙여 받고 매장 시간대로 돌려준다.** 요청의 `starts_at`은 `AwareDatetime`(시간대 없는 시각은 422), 응답의 모든 시각은 매장 시간대(`+09:00`)다.
3. **경고 판단은 서버 한 곳(`visit_schedule.warnings_for`)에만 있다.** 등록·수정·옮기기 응답과 시간 칸 조회가 같은 함수를 쓴다. 같은 가족 묶음끼리는 겹침이 아니고, 시간 칸 조회는 묶음 없이 묻는 것이라 누구의 방문과도 겹친다. 옮기기 화면을 위해 시간 칸 조회에 `exclude`(옮길 방문, 최대 10개)를 더했다.
4. **수정에서 가족 확인에 넘기는 아이는 새로 고른 아이뿐이다.** 그대로인 아이를 넘기면 완료한 방문의 아이가 나중에 무지개다리를 건넌 경우 메모조차 못 고친다. 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다. 잠금을 기다리는 사이 반려동물이 바뀌었으면 409 `VISIT_STATE_CONFLICT`다.
5. **되돌리기는 아이도 확인한다.** 취소·노쇼·완료를 되돌리면 다시 시간을 차지하는 예약이 되므로 무지개다리 아이의 방문이면 `PET_PASSED_AWAY`(422)로 막는다(V7). 다른 전이는 보호자만 잠근다. 되돌린 자리에 새 예약이 이미 있으면 409 `VISIT_DUPLICATE`다.
6. **'최근 방문순'의 키는 마지막 완료 방문의 시작 시각이다**(완료 시각이 아니라 예약 날짜). 완료가 생기거나 풀리는 전이 뒤에 원본에서 다시 계산해 같은 트랜잭션에서 넘긴다. 방문한 적 없는 가족은 맨 뒤(NULLS LAST)이고, 커서의 빈 문자열 키가 "방문 없음"이다.
7. **가족 옮기기는 묶음에서 가장 긴 소요로** 자정 넘김과 경고를 본다.
8. **하루 목록은 취소·노쇼까지 모두 보인다.** 마릿수(`visit_count`)는 예약됨·미용 중·완료만 센다. 달력 위쪽의 "정리 안 된 예약 N건"(`unresolved_total`)은 달과 상관없이 매장 전체이고 가장 이른 날(`oldest_unresolved_date`)을 함께 준다.
9. **"앞으로의 예약"은 예약됨·미용 중인 방문이다** — 날짜가 지났어도 정리하지 않았으면 든다(익명화·무지개다리를 막는다). 고객 상세의 "다가오는 예약"은 그중 오늘(매장 시간대) 이후에 시작하는 것만, 최대 3건이다.
10. **반려동물 삭제는 `PET_HAS_VISITS`를 `LAST_PET`보다 먼저 본다.** 취소된 방문만 있어도 지우지 않는다.
11. **고객 상세(GET)만 방문 요약을 더한다**(`CustomerOverviewSchema` — `no_show_count`, `upcoming_visits`). 등록·수정 응답은 그대로다.
12. **일정 설정 수정은 설정 행 UPDATE 를 맨 먼저 한다.** 두 사장이 동시에 바꾸면 늦은 쪽이 그 행에서 기다렸다가 앞선 쪽이 커밋한 쉬는 요일을 지우고 넣는다 — 따로 잠그는 SELECT 가 필요 없다.
13. **설정·쉬는 요일·임시 휴무·메뉴는 설정 행을 외래 키로 가리킨다.** 그래서 휴무 추가와 메뉴 추가는 먼저 설정을 준비(`ensure`)한다. 메뉴 이름은 보관하지 않은 메뉴끼리만 겹치지 않는다 — 보관한 이름은 다시 쓸 수 있다. 조회(GET)도 처음이면 설정과 기본 메뉴를 만든다.
14. **'지난번처럼'은 반려동물 ID 만으로 이 매장의 방문을 본다.** 다른 매장의 아이 ID 를 넣어도 빈 기본값이 될 뿐 아무것도 새지 않아 가족 확인(허브 포트)을 부르지 않는다.
15. **다음 예약 초안은 완료한 방문에서만**(아니면 409), 같은 묶음에서 완료한 아이들 전체로, 주기는 그 아이의 완료 방문 시작 시각 두 개로 계산한다.
16. **칸 형식.** ID 는 `bigint`, 상태·취소 사유는 `varchar(20)`, 메모 `varchar(500)`, 메뉴 이름 `varchar(30)`, 휴무 메모 `varchar(30)`. 임시 휴무 표의 칸 이름은 설계대로 `date`이고 ORM 속성은 `day`다(주석의 `date` 형과 부딪혀서). 요청 본문의 목록(반려동물·메뉴·방문 ID)은 10개까지, 같은 ID 두 번은 422 다.
17. **자기소개의 번호는 5번**(auth 1, tenancy 2, platform_admin 3, customer 4 다음).
18. **방문 행 잠금은 고객 잠금과 겹쳐 지킨다.** 모든 방문 쓰기가 고객 행을 먼저 잠그므로 방문 행 `FOR UPDATE`만으로 판별되는 경합은 없다 — Task 14 의 완료×노쇼 테스트는 둘 다 빼야 실패한다(설명에 적었다). 고객 잠금을 우회하는 방문 쓰기가 생기면 방문 행 잠금이 지킨다.

## 이 계획의 코드는 어떻게 검증했나

②-1·②-2 에서 계획서를 미리 돌려 본 방식이 효과적이었다. **이 계획서의 코드는 저장소 안의 임시 작업 트리에서 실제로 만들어 돌린 것을 그대로 옮겼다.**

- 작업 트리: `.superpowers/ref/wt-visit-3a1` (git 무시 대상), 브랜치 `ref/visit-3a1-plan` — **이 계획서의 작업 순서대로 쌓았고** 작업마다 단위·통합·구조 계약을 돌려 커밋했다. 컨테이너 안에서는 `/work/.superpowers/ref/wt-visit-3a1`로 보여서 `docker compose run -w … -e PYTHONPATH=…`로 원래 체크아웃을 건드리지 않고 돌렸다. 계획서의 코드 블록과 diff 는 이 브랜치의 작업 커밋에서 그대로 뽑았다. 커밋마다 되돌아가 다시 돌린 결과가 아래 표다.

  | 작업 | 단위 | 통합 | 구조 계약 |
  |---|---|---|---|
  | 기준선 | 411 | 197 | 6 kept |
  | 1 | 411 | 198 | 6 kept |
  | 2 | 476 | 198 | 6 kept |
  | 3 | 476 | 208 | 6 kept |
  | 4 | 484 | 213 | 6 kept |
  | 5 | 502 | 220 | 6 kept |
  | 6 | 522 | 224 | 6 kept |
  | 7 | 543 | 228 | 6 kept |
  | 8 | 562 | 230 | 6 kept |
  | 9 | 584 | 234 | 6 kept |
  | 10 | 595 | 236 | 6 kept |
  | 11 | 607 | 237 | 6 kept |
  | 12 | 616 | 240 | 6 kept |
  | 13 | 616 | 245 | 6 kept |
  | 14 | 616 | 249 | 6 kept |
  | 15 | 616 | 251 | 6 kept |

- 최종 상태: 단위 **616**(기준 411 + 205), 통합 **251**(기준 197 + 54), 구조 계약 **6 kept, 0 broken**.
- **변이로 판별력을 확인했다** — 각 작업의 "판별력 확인" 단계가 그것이다. 모두 적은 대로 실패하는 것을 확인했다. 그 과정에서 판별력 없는 테스트 하나를 찾아 고쳤다: 처음 쓴 Task 8 의 겹침 테스트는 형제 묶음이 다른 가족과도 겹쳐 있어 "같은 묶음은 겹침이 아니다" 조건을 빼도 통과했다 — 형제끼리만 같은 시간을 차지하는 묶음을 더했다. 또 처음 쓴 일정 설정 수정은 설정 행을 따로 잠그는 SELECT 를 먼저 했는데, 설정 행 UPDATE 가 먼저 나가면 두 요청이 이미 그 행에서 줄을 서므로 필요 없어 뺐다(동시 수정 테스트가 그대로 통과한다 — "새로 정한 것" 12).
- 두 세션 경합(Task 14)은 잠금 코드를 빼는 변이 넷으로 실패하는 것을 확인했다.
- 흐름 스크립트 `check_visit_flow.sh`는 게이트웨이가 원래 체크아웃의 코드를 돌리므로 그대로는 돌릴 수 없었다. 대신 작업 트리의 인증·API 앱을 한 포트에 묶은 대역 서버(테스트 DB, Redis db 14)에 `BASE`를 바꿔 **29단계 모두 통과**를 확인했다. **실제 게이트웨이(Caddy) 경유 실행은 미검증이다** — Task 15 에서 실행자가 돌린다.
- 라우트 표(`print_routes.py`)에 visit 경로 **20개**가 API 프로세스(`backend`)로 나오는 것을 확인했다.
- **검증하지 않은 것:** 실제 게이트웨이 경유 흐름 스크립트, 개발 DB 에 `0006` 올리기(작업 트리는 테스트 DB 에만 올렸다), `rebuild_last_visit.py`의 `main()`(개발 DB 를 대상으로 하므로 돌리지 않았다 — `rebuild_all()`과 `_run()`은 테스트했다), 마이그레이션 0006 의 `downgrade`.

그래도 규칙은 같다. **검토자는 이 계획서의 코드를 검토되지 않은 것으로 본다.** 작업 트리는 "컴파일되고 자기 테스트를 통과한다"까지만 보장한다. 테스트가 옳은 것을 확인하는지, 빠진 시나리오가 없는지는 아래 위협 점검표와 설계를 기준으로 판단한다.

수정하는 파일은 `diff` 블록으로 보인다 — `-` 줄을 지우고 `+` 줄을 더한다. 새 파일은 전체 내용이다.

## 위협 점검표

설계 10절의 V1~V14 가운데 백엔드 몫과, 이 계획을 쓰며 찾은 V15~V23 이다. 각 줄에 막는 코드와 테스트를 짝지었다. **구현자와 검토자는 이 표를 코드와 대조한다. 표에 없는 시나리오를 찾으면 보고한다.**

| # | 시나리오 | 막는 것 | 확인하는 테스트 |
|---|---|---|---|
| V1 | A매장 멤버가 B매장 방문·메뉴 ID 를 부른다 | B매장 경로는 매장 접근 확인(기존)이 403. 내 매장 경로에 B의 ID 를 넣으면 모든 리포지토리가 `ShopContext.shop_id`로 걸러 404, 본문의 메뉴는 `list_active_by_ids`가 걸러 422 | Task 13 `test_다른_매장의_방문과_메뉴에는_손댈_수_없다`(스포크의 첫 통합 테스트 — B 의 값이 그대로인지까지), Task 4 `test_다른_매장의_ID_는_빠진다`, Task 5 `test_매장마다_따로다`, Task 6 `test_다른_매장의_메뉴는_고치거나_보관하지_못한다`, Task 7 `test_고를_수_없는_메뉴면_잠그지도_않는다`, Task 9 `test_하나와_여럿을_읽고_다른_매장은_없다` |
| V2 | 다른 보호자·다른 매장의 반려동물을 끼워 예약한다 | `lock_family`가 반려동물이 그 보호자의 아이인지 확인 → 404 `PET_NOT_FOUND`, 다른 매장 보호자는 404 `CUSTOMER_NOT_FOUND` | Task 4 `test_다른_보호자의_반려동물이면_PET_NOT_FOUND_다`·`test_다른_매장의_고객이면_CUSTOMER_NOT_FOUND_다`, Task 7 `test_가족_확인에서_거절되면_넣지_않는다`, Task 13 격리 테스트의 `borrowed_pet`·남의 보호자 예약 |
| V3 | 익명화와 예약 생성·되돌리기가 겹친다 | 방문 쓰기가 맨 앞에서 고객 행을 잠근다(`lock_family`), 익명화도 고객 행을 먼저 잠근 뒤 장부를 묻는다 | Task 14 `test_익명화가_고객을_쥔_동안_예약은_기다리고_뒤에는_404_다`·`test_예약이_고객을_쥔_동안_익명화는_기다리고_뒤에는_409_다`(변이로 판별), 인터랙터 테스트의 journal 순서(Task 7·9·10) |
| V4 | 두 기기가 같은 방문에 완료와 노쇼를 동시에 누른다 | 고객 행 → 방문 행 잠금 뒤 다시 읽은 상태로 판정 → 늦은 쪽 409 | Task 14 `test_두_기기가_같은_방문에_완료와_노쇼를_누르면_늦은_쪽은_409_다`("새로 정한 것" 18), Task 2 상태 전이 표 |
| V5 | 저장을 두 번 눌러 중복 예약 | 부분 유일 색인 둘 → 세이브포인트 → 409 `VISIT_DUPLICATE` | Task 3 `test_같은_반려동물의_같은_시각에는_살아_있는_예약이_하나다`·`test_보호자만의_예약은_보호자와_시각으로_하나다`, Task 7 `test_같은_시각의_중복은_VISIT_DUPLICATE_이고_세션은_계속_쓴다`, Task 14 `test_같은_예약을_두_기기가_동시에_잡으면_하나만_된다` |
| V6 | 가족 등록·전이·옮기기가 절반만 된다 | 등록은 세이브포인트 하나에 모두, 전이는 모두 판정한 뒤 쓰기, 옮기기는 UPDATE 한 번(세이브포인트) | Task 7 `test_같은_시각의_중복은_…`(묶음 전체가 들어가지 않는다), Task 9 `test_옮기기가_하나라도_겹치면_모두_되돌린다`·`test_예약됨이_아닌_방문이_있으면_하나도_옮기지_않는다`, Task 10 `test_하나라도_안_되면_아무것도_바꾸지_않는다`·`test_되돌리기가_중복이_되면_VISIT_DUPLICATE_이고_모두_그대로다` |
| V7 | 무지개다리·익명화 뒤 앞으로의 예약이 남는다 | 409 `PET_HAS_UPCOMING_VISITS`·`CUSTOMER_HAS_UPCOMING_VISITS`, 무지개다리 아이 예약·되돌리기 422 `PET_PASSED_AWAY` | Task 12 customer 인터랙터 테스트 셋, Task 10 `test_무지개다리_아이의_방문은_되돌리지_못한다`, Task 4 `test_무지개다리_아이면_PET_PASSED_AWAY_다`, Task 13 `test_customer_의_규칙이_방문을_본다` |
| V8 | 직원이 일정·메뉴를 바꾼다 | `require_permission("shop:update")` → 403 | Task 5 `test_직원은_설정을_바꾸지_못한다`·휴무 추가·삭제 라우터 테스트, Task 6 메뉴 라우터 테스트 셋, Task 13 `test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다` |
| V9 | 카톡 글이 로그·DB 에 남는다 | ③-A3 몫 | — |
| V10 | 시각 전 노쇼, 미래 날 시작 | 상태 규칙 → 409 `VISIT_NOT_YET`, 하루는 매장 시간대 | Task 2 `test_미래_날의_예약은_시작하거나_완료할_수_없다`·`test_예약_시각_전에는_노쇼로_처리할_수_없다`·`test_하루의_경계는_매장_시간대로_센다` |
| V11 | 익명화한 고객의 방문 메모에 개인정보가 남는다 | 익명화가 `clear_customer_memos`를 부른다 | Task 12 `test_잠근_뒤_익명화하고_방문_메모와_검색_줄을_정리한다`·`test_메모를_비운다`, Task 13 `test_customer_의_규칙이_방문을_본다`(메모 None) |
| V12 | 공유 확장이 토큰에 접근한다 | ③-A3 몫 | — |
| V13 | 수정으로 반려동물을 다른 보호자의 아이로 바꾼다 | 새로 고른 아이를 `lock_family`가 확인 | Task 9 `test_다른_보호자의_아이로는_바꾸지_못한다` |
| V14 | 묶음 전이·옮기기에 다른 보호자의 방문 ID 를 섞는다 | `lock_visits` → 422 `VISIT_GROUP_MISMATCH`(잠그기 전에) | Task 9 `test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다`, Task 10 같은 이름 테스트 |
| V15 | `/visits/myself`·`calendar`·`slots`·`defaults`가 `/visits/{visit_id}`에 먼저 걸려 422 | `main.py`가 넷을 먼저 붙인다 | Task 13 `test_자기소개와_경로_순서`(변이로 판별) |
| V16 | bigint 를 넘는 ID 로 부르면 asyncpg 오류로 500 | 경로 변수 `Path(ge=1, le=bigint)`, 본문 `EntityId`, `exclude` 쿼리 | Task 6 `test_없는_메뉴는_404_범위를_넘는_ID_는_422_다`, Task 9 `test_없는_방문은_404_범위를_넘는_ID_는_422_다`, Task 8 시간 칸 `exclude=0` |
| V17 | 문자열의 NUL·제어 문자가 DB 에 닿아 500 | `reject_control_chars`(메모만 개행 허용) | Task 6 `test_이름이_비었거나_길거나_소요가_문자열이면_422_다`, Task 7 `test_형식이_틀리면_422_VALIDATION_ERROR_다` |
| V18 | `"true"`·`"90"` 같은 문자열이 조용히 참·숫자가 된다 | `StrictBool`·`StrictInt` | Task 5 `test_요일이_범위를_벗어나거나_문자열이면_422_다`, Task 7 `walk_in: "true"`·`customer_id: "1"` |
| V19 | 두 요청이 동시에 매장을 처음 써서 기본 메뉴가 두 번 들어간다 | 설정 행 `INSERT … ON CONFLICT DO NOTHING RETURNING` — 늦은 쪽은 기다렸다가 DO NOTHING, 메뉴는 넣은 쪽만 | Task 5 `test_두_세션이_동시에_처음_써도_메뉴는_한_번만_들어간다` |
| V20 | 두 사장이 동시에 쉬는 요일을 바꿔 기본 키가 부딪힌다 | 설정 행 UPDATE 를 맨 먼저 — 늦은 쪽이 기다렸다가 새 값을 지우고 넣는다 | Task 5 `test_두_사장이_동시에_쉬는_요일을_바꿔도_늦은_쪽이_앞선_쪽을_덮는다` |
| V21 | 허브 포트 자리를 채우는 것을 잊어 운영에서 500 | 라우트 구조 검사가 두 앱의 의존성 트리를 훑는다 | `tests/test_hub_port_binding.py`(Task 7·12 의 변이로 판별) |
| V22 | 완료한 방문의 아이가 나중에 무지개다리를 건너 메모를 못 고친다 | 수정은 새로 고른 아이만 가족 확인에 넘긴다 | Task 9 `test_완료한_방문은_메모와_메뉴만_고친다`(변이로 판별) |
| V23 | 익명화한 고객의 방문을 보여 줄 때 이름이 새거나 목록이 깨진다 | `FamilyBriefRepository`가 틀만 돌려준다(이름·번호 None) | Task 4 `test_익명화한_가족도_틀은_돌려주고_이름은_비운다`, Task 8 `test_그날_시작하는_방문을_시작_순으로_상태별로_센다`, Task 13 |

## 시작 전 기준선

`feat/visit-3a1-backend`(`f108b2f`)의 상태다. 시작 전에 한 번 확인한다.

- 단위 411개, 통합 197개가 통과한다. 구조 계약 6종이 통과한다(`Contracts: 6 kept, 0 broken.`). `docker compose run --rm backend alembic current`는 `0005 (head)`.
- `docker compose ps`에서 여섯 서비스가 모두 `running`이다. 아니면 `docker compose up -d`를 먼저 한다.

## 파일 지도

```
backend/
├── .importlinter · orm_registry.py · main.py
├── alembic/versions/0006_visit_tables.py
├── scripts/rebuild_last_visit.py · check_visit_flow.sh · rebuild_customer_search.py(문서 한 줄)
├── tests/test_rebuild_last_visit.py
├── tests/integration/test_visit_flow_wiring.py · test_visit_locking.py · test_customer_locking.py(장부 인자)
└── apps/
    ├── hub/app/dtos/{shop_context,family_brief,upcoming_visit}.py · ports/{customer_directory_port,visit_ledger_port}.py
    ├── tenancy/ (접근 기록에 시간대)
    ├── customer/
    │   ├── _docs/CLAUDE.md (허브 포트 줄)
    │   ├── domain/errors.py (+4)
    │   ├── app/ports/output/{family_brief_repository,customer_search_port}.py · dtos/{customer_view_dto,customer_search_dto}.py
    │   ├── app/use_cases/customer_directory_interactor.py (+ 삭제·무지개다리·익명화·고객 상세 인터랙터 변경)
    │   ├── adapter/outbound/pg/{family_brief_pg_repository,customer_search_pg_adapter}.py · orm/customer_orm.py
    │   ├── adapter/inbound/api/{error_map.py, schemas/get_customer_schema.py, v1/get_customer_router.py, v1/list_customers_router.py}
    │   └── dependencies/{hub_ports,customer_directory_provider,customer_wiring}.py (+ 프로바이더 넷 변경)
    └── visit/
        ├── CLAUDE.md → _docs/CLAUDE.md
        ├── domain/errors.py · entities/{visit,menu}.py · value_objects/{schedule_settings,closed_date,new_visit}.py
        │   state/visit_state.py · services/{visit_schedule,visit_cycle,visit_board}.py
        ├── app/dtos/ (슬라이스 DTO + visit_view·schedule_view·menu_view) · ports/input/ 20개 · ports/output/{visit,menu,schedule,visit_myself_record}_*.py
        │   services/{visit_reader,visit_locking,visit_warnings}.py · use_cases/ 20개 + visit_ledger_interactor.py
        ├── adapter/inbound/api/{error_map,path_params}.py · schemas/ · v1/ 20개
        │   outbound/orm/visit_orm.py · mappers/visit_mapper.py · pg/{visit,menu,schedule}_pg_repository.py · log_visit_myself_record_adapter.py
        ├── dependencies/{hub_ports,visit_wiring,visit_ledger_provider}.py + 프로바이더 20개
        └── tests/{domain,app/use_cases,adapter,helpers}/
CLAUDE.md · _docs/{architecture,harness}.md · _docs/decisions/006-visit-reservation.md
```

| 슬라이스 | 표면 | 권한 | 작업 |
|---|---|---|---|
| `customer_directory` (허브 포트 구현) | — | — | 4 |
| `get_visit_settings` | `GET /v1/shops/{shop_id}/visit-settings` | 멤버 | 5 |
| `update_visit_settings` | `PUT /v1/shops/{shop_id}/visit-settings` | `shop:update` | 5 |
| `list_closed_dates` | `GET /v1/shops/{shop_id}/closed-dates?from=&to=` | 멤버 | 5 |
| `add_closed_date` | `POST /v1/shops/{shop_id}/closed-dates` | `shop:update` | 5 |
| `delete_closed_date` | `DELETE /v1/shops/{shop_id}/closed-dates/{date}` | `shop:update` | 5 |
| `list_menus` | `GET /v1/shops/{shop_id}/menus?include_archived=` | 멤버 | 6 |
| `create_menu` | `POST /v1/shops/{shop_id}/menus` | `shop:update` | 6 |
| `update_menu` | `PUT /v1/shops/{shop_id}/menus/{menu_id}` | `shop:update` | 6 |
| `archive_menu` | `POST /v1/shops/{shop_id}/menus/{menu_id}/archive` | `shop:update` | 6 |
| `register_visit` | `POST /v1/shops/{shop_id}/visits` | `reservation:write` | 7 |
| `list_day_visits` | `GET /v1/shops/{shop_id}/visits?date=` | 멤버 | 8 |
| `get_visit_calendar` | `GET /v1/shops/{shop_id}/visits/calendar?month=` | 멤버 | 8 |
| `list_visit_slots` | `GET /v1/shops/{shop_id}/visits/slots?date=&duration=&at=&exclude=` | 멤버 | 8 |
| `get_visit` | `GET /v1/shops/{shop_id}/visits/{visit_id}` | 멤버 | 9 |
| `update_visit` | `PUT /v1/shops/{shop_id}/visits/{visit_id}` | `reservation:write` | 9 |
| `reschedule_visits` | `POST /v1/shops/{shop_id}/visits/reschedule` | `reservation:write` | 9 |
| `transition_visits` | `POST /v1/shops/{shop_id}/visits/transitions` | `reservation:write` | 10 |
| `get_visit_defaults` | `GET /v1/shops/{shop_id}/visits/defaults?pet_id=` | 멤버 | 11 |
| `get_next_visit_draft` | `GET /v1/shops/{shop_id}/visits/{visit_id}/next-draft` | 멤버 | 11 |
| `visit_myself` | `GET /v1/shops/{shop_id}/visits/myself` | 멤버 | 11 |
| `visit_ledger` (허브 포트 구현) | — | — | 12 |

---

### Task 1: `ShopContext`에 매장 시간대를 싣는다

"오늘"과 하루의 경계를 매장 시간대로 세려면 유스케이스가 시간대를 알아야 한다(설계 3.1-3). 매장 접근 확인(tenancy)이 이미 읽는 매장 행에서 `shops.timezone`을 함께 읽어 `ShopContext`에 싣는다. 기본값 `"Asia/Seoul"`은 이미 있는 테스트의 컨텍스트 생성 20여 곳을 건드리지 않으려는 것이다 — 매장 접근 확인은 언제나 DB 값을 채운다("새로 정한 것" 1).

**Files:**
- Modify: `backend/apps/hub/app/dtos/shop_context.py`
- Modify: `backend/apps/tenancy/app/dtos/shop_access_record.py`
- Modify: `backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py`
- Modify: `backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py`
- Modify (test): `backend/apps/tenancy/tests/adapter/test_member_pg_repository.py`
- Modify (test): `backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py`

**Interfaces:**
- Consumes: 없음
- Produces: `hub.app.dtos.shop_context.ShopContext.timezone: str`(기본 `"Asia/Seoul"`), `tenancy.app.dtos.shop_access_record.ShopAccessRecord.timezone: str`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/tenancy/tests/adapter/test_member_pg_repository.py` (수정):
```diff
@@ -31,6 +31,7 @@ async def test_사장의_접근_기록에는_모든_권한이_있다(db_session)
     assert (record.member_id, record.role) == (member.id, "owner")
     assert {"member:manage", "shop:update", "sales:read"} <= record.permissions
     assert (record.shop_suspended, record.shop_closed) == (False, False)
+    assert record.timezone == "Asia/Seoul"   # 매장 표의 기본값
 
 
 async def test_직원의_접근_기록에는_입력_권한만_있다(db_session):
@@ -57,6 +58,16 @@ async def test_닫히거나_정지된_매장은_접근_기록에_표시된다(db
     assert (record.shop_suspended, record.shop_closed) == (True, True)
 
 
+async def test_접근_기록에_매장의_시간대가_실린다(db_session):
+    shop = await _shop(db_session)
+    repo = MemberPgRepository(db_session)
+    await repo.add(shop.id, user_id=7, role=RoleCode.OWNER)
+    await db_session.execute(
+        text("UPDATE shops SET timezone = 'Asia/Tokyo' WHERE id = :id"), {"id": shop.id}
+    )
+    assert (await repo.find_access(shop.id, user_id=7)).timezone == "Asia/Tokyo"
+
+
 async def test_같은_매장에_두_번_합류할_수_없다(db_session):
     shop = await _shop(db_session)
     repo = MemberPgRepository(db_session)
```

`backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py` (수정):
```diff
@@ -18,14 +18,15 @@ class _StubMembers:
 
 def _record(**overrides):
     base = dict(member_id=11, role="staff", permissions=frozenset({"record:write"}),
-                shop_suspended=False, shop_closed=False)
+                shop_suspended=False, shop_closed=False, timezone="Asia/Tokyo")
     return ShopAccessRecord(**{**base, **overrides})
 
 
 async def test_멤버면_컨텍스트를_돌려준다():
     members = _StubMembers(_record())
     ctx = await ResolveShopAccessInteractor(members).resolve(user_id=5, shop_id=3)
-    assert ctx == ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset({"record:write"}))
+    assert ctx == ShopContext(shop_id=3, member_id=11, role="staff", permissions=frozenset({"record:write"}),
+                              timezone="Asia/Tokyo")
     assert members.calls == [(3, 5)]
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py apps/tenancy/tests/adapter/test_member_pg_repository.py -q -p no:cacheprovider
```

Expected: `ShopAccessRecord.__init__() got an unexpected keyword argument 'timezone'`(인터랙터 테스트)와 `AttributeError: ... 'timezone'`(리포지토리 테스트)로 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/hub/app/dtos/shop_context.py` (수정):
```diff
@@ -15,3 +15,6 @@ class ShopContext:
     member_id: int
     role: str
     permissions: frozenset[str]
+    # 매장의 IANA 시간대. "오늘"과 하루의 경계를 이 시간대로 계산한다(③ 예약).
+    # 기본값은 shops.timezone 의 기본값과 같다 — 매장 접근 확인(tenancy)은 언제나 DB 값을 채운다.
+    timezone: str = "Asia/Seoul"
```

`backend/apps/tenancy/app/dtos/shop_access_record.py` (수정):
```diff
@@ -12,3 +12,4 @@ class ShopAccessRecord:
     permissions: frozenset[str]
     shop_suspended: bool
     shop_closed: bool
+    timezone: str
```

`backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py` (수정):
```diff
@@ -26,4 +26,5 @@ class ResolveShopAccessInteractor(ShopAccessPort):
             member_id=record.member_id,
             role=record.role,
             permissions=record.permissions,
+            timezone=record.timezone,
         )
```

`backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py` (수정):
```diff
@@ -33,7 +33,8 @@ class MemberPgRepository(MemberRepository):
     async def find_access(self, shop_id: int, user_id: int) -> ShopAccessRecord | None:
         stmt = (
             select(
-                ShopMemberOrm.id, RoleOrm.id, RoleOrm.code, ShopOrm.suspended_at, ShopOrm.closed_at
+                ShopMemberOrm.id, RoleOrm.id, RoleOrm.code, ShopOrm.suspended_at, ShopOrm.closed_at,
+                ShopOrm.timezone,
             )
             .join(RoleOrm, RoleOrm.id == ShopMemberOrm.role_id)
             .join(ShopOrm, ShopOrm.id == ShopMemberOrm.shop_id)
@@ -46,7 +47,7 @@ class MemberPgRepository(MemberRepository):
         row = (await self._session.execute(stmt)).first()
         if row is None:
             return None
-        member_id, role_id, role_code, suspended_at, closed_at = row
+        member_id, role_id, role_code, suspended_at, closed_at, timezone = row
         codes = (
             await self._session.execute(
                 select(PermissionOrm.code)
@@ -60,6 +61,7 @@ class MemberPgRepository(MemberRepository):
             permissions=frozenset(codes),
             shop_suspended=suspended_at is not None,
             shop_closed=closed_at is not None,
+            timezone=timezone,
         )
 
     async def list_for_user(self, user_id: int) -> list[MembershipSummary]:
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py apps/tenancy/tests/adapter/test_member_pg_repository.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **411 passed**, 통합 **198 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `resolve_shop_access_interactor.py`의 `timezone=record.timezone,` 줄을 지운다 → `test_멤버면_컨텍스트를_돌려준다`가 실패한다(기본값 `Asia/Seoul` ≠ `Asia/Tokyo`) — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/hub/app/dtos/shop_context.py backend/apps/tenancy/adapter/outbound/pg/member_pg_repository.py backend/apps/tenancy/app/dtos/shop_access_record.py backend/apps/tenancy/app/use_cases/resolve_shop_access_interactor.py backend/apps/tenancy/tests/adapter/test_member_pg_repository.py backend/apps/tenancy/tests/app/use_cases/test_resolve_shop_access_interactor.py
git commit -m "feat(tenancy): ShopContext 에 매장 시간대를 싣는다"
```

---

### Task 2: visit 스포크 뼈대와 도메인 — 상태 전이, 일정 판정, 방문 주기

스포크 패키지를 만들고 구조 계약 여섯에 모두 등록한 뒤, 표준 라이브러리만 쓰는 도메인을 만든다. `domain/state/visit_state.py`는 State 패턴이다 — 상태마다 할 수 있는 행동만 구현하고 나머지는 바탕 클래스가 `VISIT_STATE_CONFLICT`로 거절한다(설계 6.1). `visit_schedule`은 끝 시각·예약 가능 범위(앞뒤 1년, 10분 단위)·자정 넘김·하루 경계·경고(겹침·휴무·영업시간 밖)를, `visit_cycle`은 다음 예약 주기(마지막 두 완료 방문 간격을 주 단위로 반올림, 없으면 4주, 1~12주)를 계산한다. `zoneinfo`는 표준 라이브러리이고, 컨테이너에 시스템 시간대 데이터가 있다(`/usr/share/zoneinfo`).

**Files:**
- Create: `backend/apps/visit/domain/entities/menu.py`
- Create: `backend/apps/visit/domain/entities/visit.py`
- Create: `backend/apps/visit/domain/errors.py`
- Create: `backend/apps/visit/domain/services/visit_cycle.py`
- Create: `backend/apps/visit/domain/services/visit_schedule.py`
- Create: `backend/apps/visit/domain/state/visit_state.py`
- Create: `backend/apps/visit/domain/value_objects/schedule_settings.py`
- Modify: `backend/.importlinter`
- Test: `backend/apps/visit/tests/domain/test_visit_cycle.py`
- Test: `backend/apps/visit/tests/domain/test_visit_schedule.py`
- Test: `backend/apps/visit/tests/domain/test_visit_state.py`
- Test: `backend/apps/visit/tests/helpers/builders.py`
- Create: 빈 `__init__.py` 11개(Step 1)

**Interfaces:**
- Consumes: 없음
- Produces:
  - `visit.domain.errors`: `VisitError`(바탕, `code`) · `VisitInputError`(`VALIDATION_ERROR`) · `VisitNotFoundError` · `VisitStateConflictError` · `VisitNotYetError` · `VisitDuplicateError` · `VisitCrossesMidnightError` · `VisitGroupMismatchError` · `MenuNotFoundError`(404) · `MenuNotAvailableError`(422, 코드는 `MENU_NOT_FOUND`) · `MenuNameTakenError`
  - `visit.domain.entities.visit`: 상태 상수 `RESERVED`·`IN_PROGRESS`·`COMPLETED`·`CANCELED`·`NO_SHOW`, `ACTIVE_STATUSES`, `CANCEL_REASONS`, `Visit`(frozen — `ends_at`·`is_active`·`group_key` 속성)
  - `visit.domain.entities.menu.Menu`(`archived` 속성)
  - `visit.domain.value_objects.schedule_settings`: `ScheduleSettings(opens_at, closes_at, default_duration_minutes, closed_weekdays)`, `DEFAULT_SETTINGS`, `DEFAULT_MENUS`
  - `visit.domain.state.visit_state`: `StatusChange(status, started_at, completed_at, canceled_at, cancel_reason)`, `transition(visit, action, now, tz, cancel_reason=None) -> StatusChange`
  - `visit.domain.services.visit_schedule`: `utc_now()`, `local_date`, `day_bounds`, `at_local`, `floor_to_step`, `check_duration`, `check_start`, `check_same_day`, `Occupied`, `is_closed_day`, `warnings_for`, `hourly_starts`, 경고 상수 `OVERLAP`·`CLOSED_DAY`·`OUTSIDE_HOURS`, `MAX_DURATION`·`STEP_MINUTES`
  - `visit.domain.services.visit_cycle`: `interval_weeks(completed_starts) -> int`, `next_start(source_starts_at, weeks, tz) -> datetime`
  - `visit.tests.helpers.builders`: `kst(month, day, hour=0, minute=0)`(2026년 한국 시각 → UTC), `ctx(...)`, `visit(**overrides)`, `menu(...)`, `TZ`, `OWNER_PERMISSIONS`·`STAFF_PERMISSIONS`

> 빈 `__init__.py`는 `touch`로 만든다. `visit/app`·`visit/adapter` 패키지가 없으면 계층 계약이 `Missing layer in container 'visit'`로 실패한다 — 빈 패키지라도 이 작업에서 만든다.

- [ ] **Step 1: 패키지를 만든다**

Run (저장소 루트에서):
```bash
mkdir -p backend/apps/visit \
  backend/apps/visit/adapter \
  backend/apps/visit/app \
  backend/apps/visit/domain \
  backend/apps/visit/domain/entities \
  backend/apps/visit/domain/services \
  backend/apps/visit/domain/state \
  backend/apps/visit/domain/value_objects \
  backend/apps/visit/tests \
  backend/apps/visit/tests/domain \
  backend/apps/visit/tests/helpers
touch backend/apps/visit/__init__.py \
  backend/apps/visit/adapter/__init__.py \
  backend/apps/visit/app/__init__.py \
  backend/apps/visit/domain/__init__.py \
  backend/apps/visit/domain/entities/__init__.py \
  backend/apps/visit/domain/services/__init__.py \
  backend/apps/visit/domain/state/__init__.py \
  backend/apps/visit/domain/value_objects/__init__.py \
  backend/apps/visit/tests/__init__.py \
  backend/apps/visit/tests/domain/__init__.py \
  backend/apps/visit/tests/helpers/__init__.py
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/domain/test_visit_cycle.py`:
```python
from datetime import timedelta

from visit.domain.services.visit_cycle import interval_weeks, next_start
from visit.tests.helpers.builders import TZ, kst


def test_완료_방문이_두_번이_안_되면_4주():
    assert interval_weeks([]) == 4
    assert interval_weeks([kst(9, 2, 14)]) == 4


def test_가장_최근_두_번의_간격을_주_단위로_반올림한다():
    starts = [kst(7, 1, 14), kst(8, 5, 14), kst(9, 2, 14)]   # 마지막 간격 4주
    assert interval_weeks(starts) == 4
    assert interval_weeks([kst(9, 2, 14), kst(8, 16, 14)]) == 2   # 17일 → 2.4주 → 2주
    assert interval_weeks([kst(9, 3, 14), kst(8, 16, 14)]) == 3   # 18일 → 2.6주 → 3주


def test_주기는_1주에서_12주로_자른다():
    assert interval_weeks([kst(9, 2, 10), kst(9, 2, 9)]) == 1
    assert interval_weeks([kst(9, 2, 10), kst(9, 2, 10) - timedelta(weeks=30)]) == 12


def test_다음_시작은_같은_요일_같은_벽시계_시각이다():
    assert next_start(kst(9, 23, 14), 4, TZ) == kst(10, 21, 14)
```

`backend/apps/visit/tests/domain/test_visit_schedule.py`:
```python
from datetime import date, time

import pytest

from visit.domain.errors import VisitCrossesMidnightError, VisitInputError
from visit.domain.services.visit_schedule import (
    CLOSED_DAY,
    OUTSIDE_HOURS,
    OVERLAP,
    Occupied,
    check_duration,
    check_same_day,
    check_start,
    day_bounds,
    floor_to_step,
    hourly_starts,
    local_date,
    warnings_for,
)
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS, ScheduleSettings
from visit.tests.helpers.builders import TZ, kst

NOW = kst(9, 23, 15)


def test_하루의_경계는_매장_시간대의_0시다():
    start, end = day_bounds(date(2026, 9, 23), TZ)
    assert (start, end) == (kst(9, 23), kst(9, 24))
    assert local_date(kst(9, 24, 0, 10), TZ) == date(2026, 9, 24)


@pytest.mark.parametrize("minutes", [10, 90, 600])
def test_소요는_10분_단위로_10분에서_600분(minutes):
    check_duration(minutes)


@pytest.mark.parametrize("minutes", [0, 5, 95, 610])
def test_범위_밖이거나_10분_단위가_아닌_소요는_거절한다(minutes):
    with pytest.raises(VisitInputError):
        check_duration(minutes)


def test_예약_시각은_10분_단위여야_한다():
    check_start(kst(9, 30, 14, 20), NOW, TZ)
    with pytest.raises(VisitInputError):
        check_start(kst(9, 30, 14, 25), NOW, TZ)


def test_예약은_오늘_기준_앞뒤_1년까지():
    from datetime import timedelta

    check_start(kst(9, 23, 10) + timedelta(days=366), NOW, TZ)
    check_start(kst(9, 23, 10) - timedelta(days=366), NOW, TZ)   # 카톡의 지난 방문을 옮겨 적는다
    with pytest.raises(VisitInputError):
        check_start(kst(9, 23, 10) + timedelta(days=367), NOW, TZ)
    with pytest.raises(VisitInputError):
        check_start(kst(9, 23, 10) - timedelta(days=367), NOW, TZ)


def test_딱_자정에_끝나면_된다():
    check_same_day(kst(9, 23, 22), 120, TZ)


def test_자정을_넘기면_VISIT_CROSSES_MIDNIGHT_다():
    with pytest.raises(VisitCrossesMidnightError):
        check_same_day(kst(9, 23, 22), 130, TZ)


def test_지금_시작한_손님의_예약_시각은_10분_단위로_내린다():
    assert floor_to_step(kst(9, 23, 15, 37), TZ) == kst(9, 23, 15, 30)


def _warn(starts_at, minutes=60, group=(9, kst(1, 1)), settings=DEFAULT_SETTINGS, closed=(), occupied=()):
    return warnings_for(starts_at, minutes, group, TZ, settings, frozenset(closed), list(occupied))


def test_경고가_없는_예약():
    assert _warn(kst(9, 23, 11)) == []


def test_다른_묶음과_시간이_겹치면_overlap():
    other = Occupied(kst(9, 23, 11), kst(9, 23, 12), group=(2, kst(9, 23, 11)))
    assert _warn(kst(9, 23, 11, 30), occupied=[other]) == [OVERLAP]


def test_끝과_시작이_맞닿으면_겹치지_않는다():
    other = Occupied(kst(9, 23, 11), kst(9, 23, 12), group=(2, kst(9, 23, 11)))
    assert _warn(kst(9, 23, 12), occupied=[other]) == []


def test_같은_가족_묶음끼리는_겹침이_아니다():
    """두부·보리를 같은 시각에 맡기면 방문 둘이 같은 시간을 차지하지만 경고할 일이 아니다."""
    group = (1, kst(9, 23, 13))
    sibling = Occupied(kst(9, 23, 13), kst(9, 23, 14), group=group)
    assert _warn(kst(9, 23, 13), group=group, occupied=[sibling]) == []


def test_묶음_없이_물으면_어떤_예약과도_겹친다():
    other = Occupied(kst(9, 23, 13), kst(9, 23, 14), group=(1, kst(9, 23, 13)))
    assert _warn(kst(9, 23, 13), group=None, occupied=[other]) == [OVERLAP]


def test_쉬는_요일과_임시_휴무는_closed_day():
    monday_off = ScheduleSettings(time(10), time(19), 120, frozenset({0}))
    assert _warn(kst(9, 28, 11), settings=monday_off) == [CLOSED_DAY]   # 9/28 은 월요일
    assert _warn(kst(9, 25, 11), closed=[date(2026, 9, 25)]) == [CLOSED_DAY]


def test_영업시간_밖으로_나가면_outside_hours():
    assert _warn(kst(9, 23, 9, 30)) == [OUTSIDE_HOURS]            # 여는 시각 전에 시작
    assert _warn(kst(9, 23, 18, 30)) == [OUTSIDE_HOURS]           # 닫는 시각 뒤에 끝남
    assert _warn(kst(9, 23, 18), minutes=60) == []                # 딱 닫는 시각에 끝남


def test_경고는_여러_개가_함께_나온다():
    other = Occupied(kst(9, 25, 8), kst(9, 25, 10), group=(2, kst(9, 25, 8)))
    assert _warn(kst(9, 25, 9), closed=[date(2026, 9, 25)], occupied=[other]) == [
        OVERLAP, CLOSED_DAY, OUTSIDE_HOURS,
    ]


def test_시간_칸은_영업시간의_정시마다():
    slots = hourly_starts(date(2026, 9, 23), DEFAULT_SETTINGS, TZ)
    assert slots == [kst(9, 23, hour) for hour in range(10, 19)]


def test_영업시간이_정시가_아니면_걸친_정시를_모두_보인다():
    settings = ScheduleSettings(time(9, 30), time(18, 30), 120, frozenset())
    assert hourly_starts(date(2026, 9, 23), settings, TZ) == [kst(9, 23, h) for h in range(9, 19)]
```

`backend/apps/visit/tests/domain/test_visit_state.py`:
```python
import pytest

from visit.domain.errors import VisitInputError, VisitNotYetError, VisitStateConflictError
from visit.domain.state.visit_state import StatusChange, transition
from visit.tests.helpers.builders import TZ, kst, visit

NOW = kst(9, 23, 15)   # 오늘 오후 3시
TODAY_2PM = kst(9, 23, 14)
TOMORROW = kst(9, 24, 10)


def _apply(status, action, starts_at=TODAY_2PM, reason=None, **fields):
    return transition(visit(status=status, starts_at=starts_at, **fields), action, NOW, TZ, reason)


# (지금 상태, 행동, 취소 사유) → 결과. 표에 없는 조합은 아래에서 모두 VISIT_STATE_CONFLICT 로 확인한다.
ALLOWED = [
    ("reserved", "start", None, StatusChange("in_progress", started_at=NOW)),
    ("reserved", "complete", None, StatusChange("completed", started_at=NOW, completed_at=NOW)),
    ("reserved", "cancel", "customer_request",
     StatusChange("canceled", canceled_at=NOW, cancel_reason="customer_request")),
    ("reserved", "cancel", "shop_reason", StatusChange("canceled", canceled_at=NOW, cancel_reason="shop_reason")),
    ("reserved", "no_show", None, StatusChange("no_show")),
    ("in_progress", "revert", None, StatusChange("reserved")),
    ("completed", "revert", None, StatusChange("reserved")),
    ("canceled", "revert", None, StatusChange("reserved")),
    ("no_show", "revert", None, StatusChange("reserved")),
]


@pytest.mark.parametrize(("status", "action", "reason", "expected"), ALLOWED)
def test_허용된_전이(status, action, reason, expected):
    assert _apply(status, action, reason=reason) == expected


def test_미용_중에서_완료하면_시작_시각을_지킨다():
    started = kst(9, 23, 14, 5)
    change = _apply("in_progress", "complete", started_at=started)
    assert change == StatusChange("completed", started_at=started, completed_at=NOW)


REFUSED = [
    (status, action)
    for status in ("reserved", "in_progress", "completed", "canceled", "no_show")
    for action in ("start", "complete", "cancel", "no_show", "revert")
    if (status, action) not in {(s, a) for s, a, _, _ in ALLOWED} | {("in_progress", "complete")}
]


@pytest.mark.parametrize(("status", "action"), REFUSED)
def test_나머지_전이는_VISIT_STATE_CONFLICT_다(status, action):
    reason = "customer_request" if action == "cancel" else None
    with pytest.raises(VisitStateConflictError):
        _apply(status, action, reason=reason)


def test_거절되는_조합은_열여섯_가지다():
    """상태 다섯 × 행동 다섯 = 25칸. 허용은 9칸(예약됨 넷, 미용 중 둘, 끝난 상태 셋의 되돌리기) → 거절 16칸."""
    assert len(REFUSED) == 16


@pytest.mark.parametrize("action", ["start", "complete"])
def test_미래_날의_예약은_시작하거나_완료할_수_없다(action):
    with pytest.raises(VisitNotYetError):
        _apply("reserved", action, starts_at=TOMORROW)


@pytest.mark.parametrize("action", ["start", "complete"])
def test_지난_날의_예약은_시작하거나_완료할_수_있다(action):
    assert _apply("reserved", action, starts_at=kst(9, 20, 10)).status in ("in_progress", "completed")


def test_오늘이면_예약_시각_전이라도_시작할_수_있다():
    assert _apply("reserved", "start", starts_at=kst(9, 23, 18)).status == "in_progress"


def test_예약_시각_전에는_노쇼로_처리할_수_없다():
    with pytest.raises(VisitNotYetError):
        _apply("reserved", "no_show", starts_at=kst(9, 23, 18))


def test_예약_시각과_같으면_노쇼로_처리할_수_있다():
    assert _apply("reserved", "no_show", starts_at=NOW).status == "no_show"


def test_하루의_경계는_매장_시간대로_센다():
    """한국 시각 9/24 0시 10분은 UTC 로는 아직 9/23 이다 — 매장 시간대로 보면 내일이라 시작할 수 없다."""
    with pytest.raises(VisitNotYetError):
        _apply("reserved", "start", starts_at=kst(9, 24, 0, 10))


def test_취소에는_사유가_있어야_한다():
    with pytest.raises(VisitInputError):
        _apply("reserved", "cancel")


def test_취소가_아닌데_사유를_보내면_안_된다():
    with pytest.raises(VisitInputError):
        _apply("reserved", "start", reason="shop_reason")


def test_모르는_사유와_모르는_행동은_VALIDATION_ERROR_다():
    with pytest.raises(VisitInputError):
        _apply("reserved", "cancel", reason="weather")
    with pytest.raises(VisitInputError):
        _apply("reserved", "teleport")
```

`backend/apps/visit/tests/helpers/builders.py`:
```python
"""visit 테스트가 함께 쓰는 값 — 매장 컨텍스트와 방문·메뉴 엔티티를 짧게 만든다."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.menu import Menu
from visit.domain.entities.visit import RESERVED, Visit

STAFF_PERMISSIONS = frozenset({"reservation:write", "customer:write", "record:write", "sales:write"})
OWNER_PERMISSIONS = STAFF_PERMISSIONS | frozenset(
    {"sales:read", "record:delete", "customer:delete", "member:manage", "shop:update"}
)
TZ = "Asia/Seoul"


def kst(month: int, day: int, hour: int = 0, minute: int = 0) -> datetime:
    """2026년 한국 시각을 UTC 로. 테스트의 모든 시각은 이것으로 만든다."""
    from zoneinfo import ZoneInfo

    return datetime(2026, month, day, hour, minute, tzinfo=ZoneInfo(TZ)).astimezone(timezone.utc)


def ctx(shop_id: int = 1, member_id: int = 11, role: str = "owner") -> ShopContext:
    permissions = OWNER_PERMISSIONS if role == "owner" else STAFF_PERMISSIONS
    return ShopContext(shop_id=shop_id, member_id=member_id, role=role, permissions=permissions,
                       timezone=TZ)


def visit(**overrides) -> Visit:
    fields = dict(
        id=1, shop_id=1, customer_id=1, pet_id=101, starts_at=kst(9, 23, 14), duration_minutes=90,
        status=RESERVED, started_at=None, completed_at=None, canceled_at=None, cancel_reason=None,
        memo=None, menu_ids=(), created_by_member_id=11, status_changed_by_member_id=None,
    )
    fields.update(overrides)
    return Visit(**fields)


def menu(menu_id: int = 1, name: str = "목욕", minutes: int | None = 60, shop_id: int = 1,
         archived: bool = False) -> Menu:
    return Menu(id=menu_id, shop_id=shop_id, name=name, default_duration_minutes=minutes,
                sort_order=menu_id, archived_at=kst(9, 1) if archived else None)


def but(entity, **changes):
    return replace(entity, **changes)
```

- [ ] **Step 3: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests/domain -q -p no:cacheprovider
```

Expected: `ModuleNotFoundError: No module named 'visit.domain.state'` 등으로 모두 실패한다.

- [ ] **Step 4: 구현한다**

`backend/apps/visit/domain/entities/menu.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Menu:
    """매장 메뉴 하나. 지우지 않고 보관한다 — 지난 방문이 가리키고 있다."""

    id: int
    shop_id: int
    name: str
    default_duration_minutes: int | None   # None 이면 매장 기본 소요
    sort_order: int
    archived_at: datetime | None

    @property
    def archived(self) -> bool:
        return self.archived_at is not None
```

`backend/apps/visit/domain/entities/visit.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

RESERVED = "reserved"
IN_PROGRESS = "in_progress"
COMPLETED = "completed"
CANCELED = "canceled"
NO_SHOW = "no_show"

# 살아 있는 방문 — 시간을 차지하고, 앞으로의 예약으로 센다.
ACTIVE_STATUSES = frozenset({RESERVED, IN_PROGRESS})

CANCEL_REASONS = frozenset({"customer_request", "shop_reason"})


@dataclass(frozen=True)
class Visit:
    """반려동물 한 마리(pet_id 가 None 이면 보호자만)의 방문 하나. 예약부터 완료까지 한 애그리거트다."""

    id: int
    shop_id: int
    customer_id: int
    pet_id: int | None
    starts_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    cancel_reason: str | None
    memo: str | None
    menu_ids: tuple[int, ...]
    created_by_member_id: int
    status_changed_by_member_id: int | None

    @property
    def ends_at(self) -> datetime:
        return self.starts_at + timedelta(minutes=self.duration_minutes)

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    @property
    def group_key(self) -> tuple[int, datetime]:
        """가족 묶음 — 같은 보호자 + 같은 시작 시각. 저장하지 않고 계산한다."""
        return (self.customer_id, self.starts_at)
```

`backend/apps/visit/domain/errors.py`:
```python
class VisitError(Exception):
    """visit 도메인 오류의 바탕. code 는 응답 본문의 code 로 나간다."""

    code = "VISIT_ERROR"


class VisitInputError(VisitError):
    """형식은 맞지만 규칙에 어긋난 입력(10분 단위가 아닌 시각, 예약 가능 범위 밖, 취소 사유 누락). 422 다."""

    code = "VALIDATION_ERROR"


class VisitNotFoundError(VisitError):
    code = "VISIT_NOT_FOUND"


class VisitStateConflictError(VisitError):
    """지금 상태에서 할 수 없는 행동. 다른 기기가 먼저 상태를 바꾼 경우도 여기로 온다."""

    code = "VISIT_STATE_CONFLICT"


class VisitNotYetError(VisitError):
    """아직 할 수 없는 행동 — 미래 날의 시작·완료, 예약 시각 전의 노쇼."""

    code = "VISIT_NOT_YET"


class VisitDuplicateError(VisitError):
    """같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있다."""

    code = "VISIT_DUPLICATE"


class VisitCrossesMidnightError(VisitError):
    code = "VISIT_CROSSES_MIDNIGHT"


class VisitGroupMismatchError(VisitError):
    """한 번에 다루는 방문들이 같은 보호자의 방문이 아니다."""

    code = "VISIT_GROUP_MISMATCH"


class MenuNotFoundError(VisitError):
    """경로의 메뉴가 없거나 다른 매장의 것이다. 404."""

    code = "MENU_NOT_FOUND"


class MenuNotAvailableError(VisitError):
    """요청 본문의 메뉴가 이 매장의 보관되지 않은 메뉴가 아니다. 코드는 MENU_NOT_FOUND 로 같고 422 다."""

    code = "MENU_NOT_FOUND"


class MenuNameTakenError(VisitError):
    code = "MENU_NAME_TAKEN"
```

`backend/apps/visit/domain/services/visit_cycle.py`:
```python
"""다음 예약 — 그 아이의 방문 주기와, 같은 요일·같은 시각의 다음 시작 시각."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

DEFAULT_WEEKS = 4
MIN_WEEKS = 1
MAX_WEEKS = 12


def interval_weeks(completed_starts: list[datetime]) -> int:
    """가장 최근 두 완료 방문의 간격을 주 단위로 반올림한다. 두 번이 안 되면 4주. 1~12주로 자른다."""
    if len(completed_starts) < 2:
        return DEFAULT_WEEKS
    latest, previous = sorted(completed_starts, reverse=True)[:2]
    weeks = round((latest - previous) / timedelta(weeks=1))
    return max(MIN_WEEKS, min(MAX_WEEKS, weeks))


def next_start(source_starts_at: datetime, weeks: int, tz: str) -> datetime:
    """weeks 주 뒤의 같은 요일·같은 벽시계 시각."""
    local = source_starts_at.astimezone(ZoneInfo(tz))
    wall = local.replace(tzinfo=None) + timedelta(weeks=weeks)
    return wall.replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)
```

`backend/apps/visit/domain/services/visit_schedule.py`:
```python
"""일정 판정 — 끝 시각, 예약 가능 범위, 자정 넘김, 하루의 경계, 겹침·휴무·영업시간 경고.

모든 시각은 시간대가 붙은 datetime 이다. "하루"와 "오늘"은 매장 시간대(ShopContext.timezone)로 센다.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from visit.domain.errors import VisitCrossesMidnightError, VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings

STEP_MINUTES = 10
MIN_DURATION = 10
MAX_DURATION = 600
BOOKING_HORIZON_DAYS = 366   # 오늘 기준 앞뒤 1년

OVERLAP = "overlap"
CLOSED_DAY = "closed_day"
OUTSIDE_HOURS = "outside_hours"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def local_date(moment: datetime, tz: str) -> date:
    return moment.astimezone(ZoneInfo(tz)).date()


def day_bounds(day: date, tz: str) -> tuple[datetime, datetime]:
    """매장 시간대의 그날 0시와 다음 날 0시(UTC)."""
    zone = ZoneInfo(tz)
    start = datetime.combine(day, time(0), zone)
    end = datetime.combine(day + timedelta(days=1), time(0), zone)
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def at_local(day: date, clock: time, tz: str) -> datetime:
    return datetime.combine(day, clock, ZoneInfo(tz)).astimezone(timezone.utc)


def floor_to_step(moment: datetime, tz: str) -> datetime:
    """10분 단위로 내린다(지금 시작한 손님의 예약 시각). 매장 시간대의 벽시계로 내린다."""
    local = moment.astimezone(ZoneInfo(tz))
    floored = local.replace(minute=local.minute - local.minute % STEP_MINUTES, second=0, microsecond=0)
    return floored.astimezone(timezone.utc)


def check_duration(minutes: int) -> None:
    if not (MIN_DURATION <= minutes <= MAX_DURATION) or minutes % STEP_MINUTES:
        raise VisitInputError("소요 시간은 10분 단위로 10분에서 600분 사이여야 합니다.")


def check_start(starts_at: datetime, now: datetime, tz: str) -> None:
    """예약 시각 — 10분 단위, 오늘 기준 앞뒤 1년 안."""
    local = starts_at.astimezone(ZoneInfo(tz))
    if local.minute % STEP_MINUTES or local.second or local.microsecond:
        raise VisitInputError("예약 시각은 10분 단위여야 합니다.")
    days = (local.date() - local_date(now, tz)).days
    if abs(days) > BOOKING_HORIZON_DAYS:
        raise VisitInputError("예약은 오늘 기준 앞뒤 1년 안에서만 잡을 수 있습니다.")


def check_same_day(starts_at: datetime, duration_minutes: int, tz: str) -> None:
    """끝나는 시각이 그날(매장 시간대) 24시를 넘으면 안 된다. 딱 24시는 된다."""
    _, next_midnight = day_bounds(local_date(starts_at, tz), tz)
    if starts_at + timedelta(minutes=duration_minutes) > next_midnight:
        raise VisitCrossesMidnightError("끝나는 시각이 자정을 넘습니다.")


@dataclass(frozen=True)
class Occupied:
    """시간을 차지한 살아 있는 방문 하나(경고 계산용)."""

    starts_at: datetime
    ends_at: datetime
    group: tuple[int, datetime]   # 가족 묶음 — 같은 묶음끼리는 겹침으로 치지 않는다


def is_closed_day(day: date, settings: ScheduleSettings, closed_dates: frozenset[date]) -> bool:
    return day.weekday() in settings.closed_weekdays or day in closed_dates


def warnings_for(
    starts_at: datetime, duration_minutes: int, group: tuple[int, datetime] | None, tz: str,
    settings: ScheduleSettings, closed_dates: frozenset[date], occupied: list[Occupied],
) -> list[str]:
    """막지 않는 경고. group 이 None 이면 누구의 예약도 아닌 빈 칸을 묻는 것이다(시간 칸)."""
    ends_at = starts_at + timedelta(minutes=duration_minutes)
    found = []
    if any(o.starts_at < ends_at and starts_at < o.ends_at and o.group != group for o in occupied):
        found.append(OVERLAP)
    day = local_date(starts_at, tz)
    if is_closed_day(day, settings, closed_dates):
        found.append(CLOSED_DAY)
    if starts_at < at_local(day, settings.opens_at, tz) or ends_at > at_local(day, settings.closes_at, tz):
        found.append(OUTSIDE_HOURS)
    return found


def hourly_starts(day: date, settings: ScheduleSettings, tz: str) -> list[datetime]:
    """시간 칸 — 영업 시작 시각이 속한 정시부터 닫는 시각 전까지 한 시간마다."""
    first = settings.opens_at.hour
    last = settings.closes_at.hour if settings.closes_at.minute == 0 else settings.closes_at.hour + 1
    return [at_local(day, time(hour), tz) for hour in range(first, last)]
```

`backend/apps/visit/domain/state/visit_state.py`:
```python
"""방문 상태 전이 — State 패턴. 상태마다 할 수 있는 행동만 구현하고, 나머지는 바탕 클래스가 거절한다.

행동은 다섯 가지다: 시작(start), 완료(complete), 취소(cancel), 노쇼(no_show), 되돌리기(revert).
예약됨에서 바로 완료하면 "바로 완료"다(시작 시각 = 완료 시각). 미용 중인 방문의 취소는 되돌린 뒤 한다.
"""
from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from visit.domain.entities.visit import (
    CANCEL_REASONS,
    CANCELED,
    COMPLETED,
    IN_PROGRESS,
    NO_SHOW,
    RESERVED,
    Visit,
)
from visit.domain.errors import VisitInputError, VisitNotYetError, VisitStateConflictError
from visit.domain.services.visit_schedule import local_date

ACTIONS = frozenset({"start", "complete", "cancel", "no_show", "revert"})


@dataclass(frozen=True)
class StatusChange:
    """전이의 결과 — 방문 행의 상태 칸을 통째로 이 값으로 바꾼다. 없는 시각은 비운다."""

    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    canceled_at: datetime | None = None
    cancel_reason: str | None = None


class VisitState(ABC):
    status: ClassVar[str]

    def start(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        raise self._refuse("시작")

    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        raise self._refuse("완료")

    def cancel(self, visit: Visit, now: datetime, reason: str) -> StatusChange:
        raise self._refuse("취소")

    def no_show(self, visit: Visit, now: datetime) -> StatusChange:
        raise self._refuse("노쇼 처리")

    def revert(self, visit: Visit) -> StatusChange:
        # 알림장을 보낸 뒤에는 되돌릴 수 없다는 규칙이 ⑤에서 더해진다.
        return StatusChange(status=RESERVED)

    def _refuse(self, action: str) -> VisitStateConflictError:
        return VisitStateConflictError(f"지금 상태({self.status})에서는 {action}할 수 없습니다.")


def _check_day_reached(visit: Visit, now: datetime, tz: str) -> None:
    if local_date(visit.starts_at, tz) > local_date(now, tz):
        raise VisitNotYetError("예약한 날이 되어야 시작하거나 완료할 수 있습니다.")


class ReservedState(VisitState):
    status = RESERVED

    def start(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        _check_day_reached(visit, now, tz)
        return StatusChange(status=IN_PROGRESS, started_at=now)

    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        _check_day_reached(visit, now, tz)
        return StatusChange(status=COMPLETED, started_at=now, completed_at=now)   # 바로 완료

    def cancel(self, visit: Visit, now: datetime, reason: str) -> StatusChange:
        return StatusChange(status=CANCELED, canceled_at=now, cancel_reason=reason)

    def no_show(self, visit: Visit, now: datetime) -> StatusChange:
        if visit.starts_at > now:
            raise VisitNotYetError("예약 시각이 지나야 노쇼로 처리할 수 있습니다.")
        return StatusChange(status=NO_SHOW)

    def revert(self, visit: Visit) -> StatusChange:
        raise self._refuse("되돌리기")


class InProgressState(VisitState):
    status = IN_PROGRESS

    def complete(self, visit: Visit, now: datetime, tz: str) -> StatusChange:
        return StatusChange(status=COMPLETED, started_at=visit.started_at, completed_at=now)


class CompletedState(VisitState):
    status = COMPLETED


class CanceledState(VisitState):
    status = CANCELED


class NoShowState(VisitState):
    status = NO_SHOW


_STATES: dict[str, VisitState] = {
    state.status: state
    for state in (ReservedState(), InProgressState(), CompletedState(), CanceledState(), NoShowState())
}


def transition(
    visit: Visit, action: str, now: datetime, tz: str, cancel_reason: str | None = None
) -> StatusChange:
    """방문 하나에 행동 하나를 적용한 결과. 취소 사유는 취소에만, 그리고 취소에는 반드시 있어야 한다."""
    if action not in ACTIONS:
        raise VisitInputError("알 수 없는 행동입니다.")
    if (action == "cancel") != (cancel_reason is not None):
        raise VisitInputError("취소 사유는 취소할 때만, 반드시 보내 주세요.")
    if cancel_reason is not None and cancel_reason not in CANCEL_REASONS:
        raise VisitInputError("취소 사유가 올바르지 않습니다.")
    state = _STATES[visit.status]
    if action == "start":
        return state.start(visit, now, tz)
    if action == "complete":
        return state.complete(visit, now, tz)
    if action == "cancel":
        return state.cancel(visit, now, cancel_reason)
    if action == "no_show":
        return state.no_show(visit, now)
    return state.revert(visit)
```

`backend/apps/visit/domain/value_objects/schedule_settings.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True)
class ScheduleSettings:
    """매장 일정 설정 — 영업시간 하나, 기본 소요, 매주 쉬는 요일(월=0 … 일=6)."""

    opens_at: time
    closes_at: time
    default_duration_minutes: int
    closed_weekdays: frozenset[int]


DEFAULT_SETTINGS = ScheduleSettings(
    opens_at=time(10, 0), closes_at=time(19, 0), default_duration_minutes=120,
    closed_weekdays=frozenset(),
)

# 매장을 처음 쓸 때 넣는 메뉴(이름, 기본 소요). 첫 짐작이고 사장이 바꾼다.
DEFAULT_MENUS: tuple[tuple[str, int], ...] = (
    ("목욕", 60), ("위생", 60), ("부분 미용", 90), ("전체 미용", 150), ("스포팅", 120),
)
```

`backend/.importlinter` (수정):
```diff
@@ -18,6 +18,7 @@ root_packages =
     tenancy
     platform_admin
     customer
+    visit
 include_external_packages = True
 
 [importlinter:contract:clean-architecture]
@@ -33,6 +34,7 @@ containers =
     tenancy
     platform_admin
     customer
+    visit
 
 [importlinter:contract:spoke-independence]
 name = 스포크 상호 독립 (스포크끼리 import 하지 않는다)
@@ -42,6 +44,7 @@ modules =
     tenancy
     platform_admin
     customer
+    visit
 
 [importlinter:contract:framework-isolation]
 name = 프레임워크 격리 (app·domain 은 웹·DB·외부 통신 라이브러리를 모른다)
@@ -56,6 +59,8 @@ source_modules =
     platform_admin.domain
     customer.app
     customer.domain
+    visit.app
+    visit.domain
 forbidden_modules =
     fastapi
     sqlalchemy
@@ -72,6 +77,7 @@ source_modules =
     tenancy.domain
     platform_admin.domain
     customer.domain
+    visit.domain
 forbidden_modules =
     pydantic
     core
@@ -86,6 +92,8 @@ forbidden_modules =
     tenancy
     platform_admin
     customer
+    visit
+    visit
 
 [importlinter:contract:core-isolation]
 name = core 격리 (core 는 스포크를 import 하지 않는다)
@@ -97,3 +105,5 @@ forbidden_modules =
     tenancy
     platform_admin
     customer
+    visit
+    visit
```

- [ ] **Step 5: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests/domain -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 6: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **476 passed**, 통합 **198 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 7: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 5 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `ReservedState.no_show`의 `if visit.starts_at > now:` 검사를 지운다 → `test_예약_시각_전에는_노쇼로_처리할_수_없다`가 실패한다 — 되돌린다.
- `_check_day_reached`가 `local_date(..., tz)` 대신 UTC 날짜(`visit.starts_at.date() > now.date()`)를 비교하게 바꾼다 → `test_하루의_경계는_매장_시간대로_센다`가 실패한다 — 되돌린다.

- [ ] **Step 8: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/.importlinter backend/apps/visit/__init__.py backend/apps/visit/adapter/__init__.py backend/apps/visit/app/__init__.py backend/apps/visit/domain/__init__.py backend/apps/visit/domain/entities/__init__.py backend/apps/visit/domain/entities/menu.py backend/apps/visit/domain/entities/visit.py backend/apps/visit/domain/errors.py backend/apps/visit/domain/services/__init__.py backend/apps/visit/domain/services/visit_cycle.py backend/apps/visit/domain/services/visit_schedule.py backend/apps/visit/domain/state/__init__.py backend/apps/visit/domain/state/visit_state.py backend/apps/visit/domain/value_objects/__init__.py backend/apps/visit/domain/value_objects/schedule_settings.py backend/apps/visit/tests/__init__.py backend/apps/visit/tests/domain/__init__.py backend/apps/visit/tests/domain/test_visit_cycle.py backend/apps/visit/tests/domain/test_visit_schedule.py backend/apps/visit/tests/domain/test_visit_state.py backend/apps/visit/tests/helpers/__init__.py backend/apps/visit/tests/helpers/builders.py
git commit -m "feat(visit): 스포크 뼈대와 도메인 — 상태 전이, 일정 판정, 방문 주기"
```

---

### Task 3: 마이그레이션 0006 — 방문·매장 일정·메뉴 표, 검색 줄의 마지막 방문 시각

설계 5.1절의 표 여섯과 customer 검색 줄의 `last_visit_at` 칸을 손으로 쓴 마이그레이션으로 만든다. 상태와 시각·사유의 짝은 CHECK 로, 중복 예약은 부분 유일 색인 둘로 막는다(V5). 설정·쉬는 요일·임시 휴무·메뉴는 설정 행을 외래 키로 가리킨다(스포크 안의 관계). `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 새 ORM 모듈은 `orm_registry.py`에 등록한다(스키마 불일치 테스트가 쓴다). 시드 표는 없다 — 기본 메뉴는 매장마다 처음 쓸 때 넣는다(Task 5).

**Files:**
- Modify: `backend/apps/customer/adapter/outbound/orm/customer_orm.py`
- Create: `backend/apps/visit/adapter/outbound/orm/visit_orm.py`
- Create: `backend/alembic/versions/0006_visit_tables.py`
- Modify: `backend/orm_registry.py`
- Test: `backend/apps/visit/tests/adapter/test_visit_schema.py`
- Create: 빈 `__init__.py` 3개(Step 1)

**Interfaces:**
- Consumes: Task 2 의 스포크 패키지
- Produces: ORM `VisitShopSettingsOrm`·`VisitWeeklyClosureOrm`·`VisitClosedDateOrm`(칸 `date` ↔ 속성 `day`)·`ServiceMenuOrm`·`VisitOrm`·`VisitMenuOrm`, 제약 이름 `uq_visits_pet_start_active`·`uq_visits_customer_start_active`·`uq_service_menus_shop_name_active`, `CustomerSearchEntryOrm.last_visit_at`, 테스트 도우미는 아직 없음

- [ ] **Step 1: 패키지를 만든다**

Run (저장소 루트에서):
```bash
mkdir -p backend/apps/visit/adapter/outbound \
  backend/apps/visit/adapter/outbound/orm \
  backend/apps/visit/tests/adapter
touch backend/apps/visit/adapter/outbound/__init__.py \
  backend/apps/visit/adapter/outbound/orm/__init__.py \
  backend/apps/visit/tests/adapter/__init__.py
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_visit_schema.py`:
```python
"""마이그레이션 0006 의 제약 — 상태와 시각·사유의 짝, 소요 규칙, 중복 예약, 메뉴 이름."""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from visit.tests.helpers.builders import kst

pytestmark = pytest.mark.integration

_INSERT = (
    "INSERT INTO visits (shop_id, customer_id, pet_id, starts_at, duration_minutes, status, "
    "started_at, completed_at, canceled_at, cancel_reason, created_by_member_id) VALUES "
    "(1, :customer, :pet, :starts, :minutes, :status, :started, :completed, :canceled, :reason, 11)"
)
START = kst(9, 23, 14)


def _row(**overrides):
    row = dict(customer=1, pet=101, starts=START, minutes=90, status="reserved", started=None,
               completed=None, canceled=None, reason=None)
    row.update(overrides)
    return row


async def _insert(session, **overrides):
    await session.execute(text(_INSERT), _row(**overrides))


async def _violates(session, **overrides) -> str:
    with pytest.raises(IntegrityError) as caught:
        async with session.begin_nested():
            await _insert(session, **overrides)
    return caught.value.orig.__cause__.constraint_name


async def test_상태와_시각_사유는_짝이_맞아야_한다(db_session):
    await _insert(db_session, status="completed", started=START, completed=START)
    await _insert(db_session, status="canceled", canceled=START, reason="shop_reason")
    assert await _violates(db_session, status="completed", started=START) == "ck_visits_completed_at"
    assert await _violates(db_session, status="canceled", canceled=START) == "ck_visits_canceled_fields"
    assert await _violates(db_session, status="reserved", canceled=START, reason="shop_reason") == (
        "ck_visits_canceled_fields"
    )
    assert await _violates(db_session, status="in_progress") == "ck_visits_started_at"
    assert await _violates(db_session, status="reserved", started=START) == "ck_visits_started_at"
    assert await _violates(db_session, status="waiting") == "ck_visits_status"
    assert await _violates(db_session, status="canceled", canceled=START, reason="weather") == (
        "ck_visits_cancel_reason"
    )


@pytest.mark.parametrize("minutes", [0, 5, 95, 610])
async def test_소요는_10분_단위로_10분에서_600분(db_session, minutes):
    assert await _violates(db_session, minutes=minutes) == "ck_visits_duration"


async def test_같은_반려동물의_같은_시각에는_살아_있는_예약이_하나다(db_session):
    await _insert(db_session)
    assert await _violates(db_session) == "uq_visits_pet_start_active"
    assert await _violates(db_session, status="in_progress", started=START) == "uq_visits_pet_start_active"
    # 취소·노쇼·완료된 방문과는 겹쳐도 된다 — 취소한 자리에 다시 예약한다.
    await _insert(db_session, status="canceled", canceled=START, reason="customer_request")
    await _insert(db_session, status="no_show")
    await _insert(db_session, pet=102)   # 같은 시각의 형제는 된다(가족 묶음)


async def test_보호자만의_예약은_보호자와_시각으로_하나다(db_session):
    await _insert(db_session, pet=None)
    assert await _violates(db_session, pet=None) == "uq_visits_customer_start_active"
    await _insert(db_session, pet=101)   # 같은 보호자의 반려동물 예약과는 다른 것이다


async def _settings(session, shop_id=1):
    await session.execute(
        text("INSERT INTO visit_shop_settings (shop_id, opens_at, closes_at, default_duration_minutes) "
             "VALUES (:shop, '10:00', '19:00', 120)"),
        {"shop": shop_id},
    )


async def test_매장_설정의_규칙(db_session):
    with pytest.raises(IntegrityError) as caught:
        async with db_session.begin_nested():
            await db_session.execute(text(
                "INSERT INTO visit_shop_settings (shop_id, opens_at, closes_at, default_duration_minutes) "
                "VALUES (1, '19:00', '10:00', 120)"))
    assert caught.value.orig.__cause__.constraint_name == "ck_visit_shop_settings_hours"
    await _settings(db_session)
    with pytest.raises(IntegrityError) as caught:
        async with db_session.begin_nested():
            await db_session.execute(text("INSERT INTO visit_weekly_closures VALUES (1, 7)"))
    assert caught.value.orig.__cause__.constraint_name == "ck_visit_weekly_closures_weekday"


async def test_보관하지_않은_메뉴끼리_이름이_겹치지_않는다(db_session):
    await _settings(db_session)
    add = ("INSERT INTO service_menus (shop_id, name, sort_order, archived_at) "
           "VALUES (1, '목욕', 1, CASE WHEN :archived THEN now() END)")
    await db_session.execute(text(add), {"archived": True})
    await db_session.execute(text(add), {"archived": False})
    with pytest.raises(IntegrityError) as caught:
        async with db_session.begin_nested():
            await db_session.execute(text(add), {"archived": False})
    assert caught.value.orig.__cause__.constraint_name == "uq_service_menus_shop_name_active"


async def test_검색_줄에_마지막_방문_시각_칸이_있다(db_session):
    column = (await db_session.execute(text(
        "SELECT is_nullable FROM information_schema.columns "
        "WHERE table_name = 'customer_search_entries' AND column_name = 'last_visit_at'"
    ))).scalar_one()
    assert column == "YES"
```

- [ ] **Step 3: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests/adapter/test_visit_schema.py tests/test_schema_drift.py -q -p no:cacheprovider
```

Expected: `relation "visits" does not exist` 등으로 실패한다(테스트 DB 는 세션마다 `alembic upgrade head`로 다시 만든다).

- [ ] **Step 4: 구현한다**

`backend/apps/customer/adapter/outbound/orm/customer_orm.py` (수정):
```diff
@@ -123,6 +123,7 @@ class CustomerSearchEntryOrm(Base):
         ),
         Index("ix_customer_search_entries_shop_activity", "shop_id", "last_activity_at"),
         Index("ix_customer_search_entries_shop_sort_name", "shop_id", "sort_name"),
+        Index("ix_customer_search_entries_shop_last_visit", "shop_id", "last_visit_at"),
     )
 
     customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), primary_key=True)
@@ -131,3 +132,5 @@ class CustomerSearchEntryOrm(Base):
     phone_last4: Mapped[str] = mapped_column(String(4))
     sort_name: Mapped[str] = mapped_column(String(50))
     last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
+    # 마지막 완료 방문의 시작 시각(최근 방문순). 원본은 visits 이고 visit 스포크가 허브 포트로 알려 준다.
+    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

`backend/apps/visit/adapter/outbound/orm/visit_orm.py`:
```python
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Time,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base

_DURATION_RULE = "BETWEEN 10 AND 600 AND {col} % 10 = 0"


class VisitShopSettingsOrm(Base):
    """매장마다 한 줄. 이 행이 있다는 것이 곧 기본 메뉴를 넣었다는 뜻이다(설계 5.1)."""

    __tablename__ = "visit_shop_settings"
    __table_args__ = (
        CheckConstraint("opens_at < closes_at", name="ck_visit_shop_settings_hours"),
        CheckConstraint(
            "default_duration_minutes " + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_visit_shop_settings_duration",
        ),
    )

    # tenancy 의 매장 ID. 스포크를 넘는 외래 키는 걸지 않는다.
    shop_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    opens_at: Mapped[time] = mapped_column(Time)
    closes_at: Mapped[time] = mapped_column(Time)
    default_duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VisitWeeklyClosureOrm(Base):
    """매주 쉬는 요일 하나(월=0 … 일=6). 배열 칸 대신 행이다(1NF)."""

    __tablename__ = "visit_weekly_closures"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_visit_weekly_closures_weekday"),
    )

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("visit_shop_settings.shop_id"), primary_key=True
    )
    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)


class VisitClosedDateOrm(Base):
    __tablename__ = "visit_closed_dates"

    shop_id: Mapped[int] = mapped_column(
        ForeignKey("visit_shop_settings.shop_id"), primary_key=True
    )
    # 칸 이름은 date 다. 속성 이름을 date 로 두면 주석의 date 형과 부딪혀 day 로 부른다.
    day: Mapped[date] = mapped_column("date", Date, primary_key=True)
    note: Mapped[str | None] = mapped_column(String(30))


class ServiceMenuOrm(Base):
    __tablename__ = "service_menus"
    __table_args__ = (
        # 보관한 메뉴는 이름이 겹쳐도 된다 — 같은 이름으로 다시 만들 수 있다.
        Index(
            "uq_service_menus_shop_name_active", "shop_id", "name",
            unique=True, postgresql_where=text("archived_at IS NULL"),
        ),
        CheckConstraint(
            "default_duration_minutes IS NULL OR default_duration_minutes "
            + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_service_menus_duration",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("visit_shop_settings.shop_id"), index=True)
    name: Mapped[str] = mapped_column(String(30))
    default_duration_minutes: Mapped[int | None] = mapped_column(SmallInteger)
    sort_order: Mapped[int] = mapped_column(SmallInteger)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class VisitOrm(Base):
    """반려동물 한 마리(pet_id 가 NULL 이면 보호자만)의 방문 하나."""

    __tablename__ = "visits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('reserved', 'in_progress', 'completed', 'canceled', 'no_show')",
            name="ck_visits_status",
        ),
        CheckConstraint(
            "duration_minutes " + _DURATION_RULE.format(col="duration_minutes"),
            name="ck_visits_duration",
        ),
        CheckConstraint(
            "cancel_reason IS NULL OR cancel_reason IN ('customer_request', 'shop_reason')",
            name="ck_visits_cancel_reason",
        ),
        # 상태가 원본이고, 시각·사유 칸은 그 상태일 때만 있다(설계 5.2).
        CheckConstraint(
            "(status = 'canceled') = (canceled_at IS NOT NULL) "
            "AND (status = 'canceled') = (cancel_reason IS NOT NULL)",
            name="ck_visits_canceled_fields",
        ),
        CheckConstraint(
            "(status = 'completed') = (completed_at IS NOT NULL)", name="ck_visits_completed_at"
        ),
        CheckConstraint(
            "(status IN ('in_progress', 'completed')) = (started_at IS NOT NULL)",
            name="ck_visits_started_at",
        ),
        # 중복 예약 방지 — 저장을 두 번 눌러도 살아 있는 예약은 하나다(설계 V5).
        Index(
            "uq_visits_pet_start_active", "pet_id", "starts_at", unique=True,
            postgresql_where=text("pet_id IS NOT NULL AND status IN ('reserved', 'in_progress')"),
        ),
        Index(
            "uq_visits_customer_start_active", "customer_id", "starts_at", unique=True,
            postgresql_where=text("pet_id IS NULL AND status IN ('reserved', 'in_progress')"),
        ),
        Index("ix_visits_shop_starts_at", "shop_id", "starts_at"),
        Index("ix_visits_shop_customer", "shop_id", "customer_id"),
        Index("ix_visits_shop_pet", "shop_id", "pet_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    # 다른 스포크(tenancy·customer)의 ID — 외래 키 없이 색인만. 설계 5.3 의 역정규화.
    shop_id: Mapped[int] = mapped_column(BigInteger)
    customer_id: Mapped[int] = mapped_column(BigInteger)
    pet_id: Mapped[int | None] = mapped_column(BigInteger)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(SmallInteger)
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancel_reason: Mapped[str | None] = mapped_column(String(20))
    memo: Mapped[str | None] = mapped_column(String(500))
    created_by_member_id: Mapped[int] = mapped_column(BigInteger)
    status_changed_by_member_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class VisitMenuOrm(Base):
    __tablename__ = "visit_menus"

    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True
    )
    menu_id: Mapped[int] = mapped_column(ForeignKey("service_menus.id"), primary_key=True)
```

`backend/alembic/versions/0006_visit_tables.py`:
```python
"""방문·매장 일정·메뉴 표 + 검색 줄의 마지막 방문 시각

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-23
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

_DURATION_RULE = "BETWEEN 10 AND 600 AND {col} % 10 = 0"


def _now(name: str) -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "visit_shop_settings",
        sa.Column("shop_id", sa.BigInteger, primary_key=True, autoincrement=False),  # tenancy 의 매장 ID
        sa.Column("opens_at", sa.Time, nullable=False),
        sa.Column("closes_at", sa.Time, nullable=False),
        sa.Column("default_duration_minutes", sa.SmallInteger, nullable=False),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint("opens_at < closes_at", name="ck_visit_shop_settings_hours"),
        sa.CheckConstraint(
            "default_duration_minutes " + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_visit_shop_settings_duration",
        ),
    )

    op.create_table(
        "visit_weekly_closures",
        sa.Column("shop_id", sa.BigInteger, sa.ForeignKey("visit_shop_settings.shop_id"), primary_key=True),
        sa.Column("weekday", sa.SmallInteger, primary_key=True, autoincrement=False),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_visit_weekly_closures_weekday"),
    )

    op.create_table(
        "visit_closed_dates",
        sa.Column("shop_id", sa.BigInteger, sa.ForeignKey("visit_shop_settings.shop_id"), primary_key=True),
        sa.Column("date", sa.Date, primary_key=True),
        sa.Column("note", sa.String(30)),
    )

    op.create_table(
        "service_menus",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("shop_id", sa.BigInteger, sa.ForeignKey("visit_shop_settings.shop_id"), nullable=False),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("default_duration_minutes", sa.SmallInteger),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _now("created_at"),
        sa.CheckConstraint(
            "default_duration_minutes IS NULL OR default_duration_minutes "
            + _DURATION_RULE.format(col="default_duration_minutes"),
            name="ck_service_menus_duration",
        ),
    )
    op.create_index("ix_service_menus_shop_id", "service_menus", ["shop_id"])
    op.create_index(
        "uq_service_menus_shop_name_active", "service_menus", ["shop_id", "name"],
        unique=True, postgresql_where=sa.text("archived_at IS NULL"),
    )

    op.create_table(
        "visits",
        sa.Column("id", sa.BigInteger, primary_key=True),
        # 다른 스포크의 ID — 외래 키 없이 색인만(설계 5.3).
        sa.Column("shop_id", sa.BigInteger, nullable=False),
        sa.Column("customer_id", sa.BigInteger, nullable=False),
        sa.Column("pet_id", sa.BigInteger),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.SmallInteger, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("canceled_at", sa.DateTime(timezone=True)),
        sa.Column("cancel_reason", sa.String(20)),
        sa.Column("memo", sa.String(500)),
        sa.Column("created_by_member_id", sa.BigInteger, nullable=False),
        sa.Column("status_changed_by_member_id", sa.BigInteger),
        _now("created_at"),
        _now("updated_at"),
        sa.CheckConstraint(
            "status IN ('reserved', 'in_progress', 'completed', 'canceled', 'no_show')",
            name="ck_visits_status",
        ),
        sa.CheckConstraint(
            "duration_minutes " + _DURATION_RULE.format(col="duration_minutes"),
            name="ck_visits_duration",
        ),
        sa.CheckConstraint(
            "cancel_reason IS NULL OR cancel_reason IN ('customer_request', 'shop_reason')",
            name="ck_visits_cancel_reason",
        ),
        sa.CheckConstraint(
            "(status = 'canceled') = (canceled_at IS NOT NULL) "
            "AND (status = 'canceled') = (cancel_reason IS NOT NULL)",
            name="ck_visits_canceled_fields",
        ),
        sa.CheckConstraint(
            "(status = 'completed') = (completed_at IS NOT NULL)", name="ck_visits_completed_at"
        ),
        sa.CheckConstraint(
            "(status IN ('in_progress', 'completed')) = (started_at IS NOT NULL)",
            name="ck_visits_started_at",
        ),
    )
    op.create_index(
        "uq_visits_pet_start_active", "visits", ["pet_id", "starts_at"], unique=True,
        postgresql_where=sa.text("pet_id IS NOT NULL AND status IN ('reserved', 'in_progress')"),
    )
    op.create_index(
        "uq_visits_customer_start_active", "visits", ["customer_id", "starts_at"], unique=True,
        postgresql_where=sa.text("pet_id IS NULL AND status IN ('reserved', 'in_progress')"),
    )
    op.create_index("ix_visits_shop_starts_at", "visits", ["shop_id", "starts_at"])
    op.create_index("ix_visits_shop_customer", "visits", ["shop_id", "customer_id"])
    op.create_index("ix_visits_shop_pet", "visits", ["shop_id", "pet_id"])

    op.create_table(
        "visit_menus",
        sa.Column("visit_id", sa.BigInteger, sa.ForeignKey("visits.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("menu_id", sa.BigInteger, sa.ForeignKey("service_menus.id"), primary_key=True),
    )

    op.add_column(
        "customer_search_entries", sa.Column("last_visit_at", sa.DateTime(timezone=True))
    )
    op.create_index(
        "ix_customer_search_entries_shop_last_visit", "customer_search_entries",
        ["shop_id", "last_visit_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_customer_search_entries_shop_last_visit", table_name="customer_search_entries")
    op.drop_column("customer_search_entries", "last_visit_at")
    op.drop_table("visit_menus")
    op.drop_index("ix_visits_shop_pet", table_name="visits")
    op.drop_index("ix_visits_shop_customer", table_name="visits")
    op.drop_index("ix_visits_shop_starts_at", table_name="visits")
    op.drop_index("uq_visits_customer_start_active", table_name="visits")
    op.drop_index("uq_visits_pet_start_active", table_name="visits")
    op.drop_table("visits")
    op.drop_index("uq_service_menus_shop_name_active", table_name="service_menus")
    op.drop_index("ix_service_menus_shop_id", table_name="service_menus")
    op.drop_table("service_menus")
    op.drop_table("visit_closed_dates")
    op.drop_table("visit_weekly_closures")
    op.drop_table("visit_shop_settings")
```

`backend/orm_registry.py` (수정):
```diff
@@ -7,3 +7,4 @@ import auth.adapter.outbound.orm.user_orm  # noqa: F401
 import auth.adapter.outbound.orm.operator_orm  # noqa: F401
 import tenancy.adapter.outbound.orm.tenancy_orm  # noqa: F401
 import customer.adapter.outbound.orm.customer_orm  # noqa: F401
+import visit.adapter.outbound.orm.visit_orm  # noqa: F401
```

> 개발 DB 에는 아직 올리지 않는다. Task 15 에서 `docker compose restart backend`(시작 명령이 `alembic upgrade head`를 돈다)로 한 번 올린다 — 표를 더할 뿐이다.

- [ ] **Step 5: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests/adapter/test_visit_schema.py tests/test_schema_drift.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 6: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **476 passed**, 통합 **208 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 7: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 5 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- 마이그레이션의 `uq_visits_pet_start_active`를 `unique=False`로 바꾼다 → `test_같은_반려동물의_같은_시각에는_살아_있는_예약이_하나다`와 스키마 불일치 테스트가 실패한다 — 되돌린다.

- [ ] **Step 8: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/alembic/versions/0006_visit_tables.py backend/apps/customer/adapter/outbound/orm/customer_orm.py backend/apps/visit/adapter/outbound/__init__.py backend/apps/visit/adapter/outbound/orm/__init__.py backend/apps/visit/adapter/outbound/orm/visit_orm.py backend/apps/visit/tests/adapter/__init__.py backend/apps/visit/tests/adapter/test_visit_schema.py backend/orm_registry.py
git commit -m "feat(visit): 마이그레이션 0006 — 방문·매장 일정·메뉴 표, 검색 줄의 마지막 방문 시각"
```

---

### Task 4: 허브 포트 `CustomerDirectoryPort`와 customer 쪽 구현 — 가족 잠금·요약·마지막 방문 시각

visit 이 customer 를 import 하지 않고 가족을 확인·잠그고 이름을 읽도록 허브에 포트를 둔다(설계 4.1). 구현은 customer 의 HTTP 없는 슬라이스 `customer_directory`다 — 인터랙터가 허브 포트 ABC 를 직접 상속한다. `lock_family`는 가족을 바꾸는 customer 유스케이스와 같은 잠금(`lock_active` — 고객 행 `FOR UPDATE`)을 쥐므로, 익명화·무지개다리·반려동물 삭제와 예약 쓰기가 서로를 기다린다(V3). 요약은 익명화한 고객도 틀을 돌려준다(이름 None) — 방문 기록은 익명화 뒤에도 남기 때문이다. `CustomerRepository`는 "살아 있는 고객만"이라 요약 전용 출력 포트 `FamilyBriefRepository`를 따로 둔다. `set_last_visit`는 검색 포트가 맡는다(검색 줄의 칸이다). 검색 줄을 다시 만들 때(`rebuild_search_entry`) 이 칸은 upsert 의 `set_`에 없어 그대로다.

**Files:**
- Modify: `backend/apps/customer/domain/errors.py`
- Create: `backend/apps/hub/app/dtos/family_brief.py`
- Create: `backend/apps/hub/app/ports/customer_directory_port.py`
- Modify: `backend/apps/customer/app/ports/output/customer_search_port.py`
- Create: `backend/apps/customer/app/ports/output/family_brief_repository.py`
- Create: `backend/apps/customer/app/use_cases/customer_directory_interactor.py`
- Modify: `backend/apps/customer/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py`
- Create: `backend/apps/customer/adapter/outbound/pg/family_brief_pg_repository.py`
- Create: `backend/apps/customer/dependencies/customer_directory_provider.py`
- Modify: `backend/apps/customer/dependencies/customer_wiring.py`
- Modify (test): `backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py`
- Test: `backend/apps/customer/tests/adapter/test_family_brief_pg_repository.py`
- Test: `backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`
- Modify (test): `backend/apps/customer/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: Task 3 의 `CustomerSearchEntryOrm.last_visit_at`
- Produces:
  - `hub.app.dtos.family_brief`: `CustomerBrief(customer_id, name, phone_masked)`, `PetBrief(pet_id, customer_id, name, species, breed, weight_kg, passed_away)`, `FamilyBriefs(customers: dict, pets: dict)`
  - `hub.app.ports.customer_directory_port.CustomerDirectoryPort`: `lock_family(ctx, customer_id, pet_ids: tuple) -> None`, `briefs(ctx, customer_ids: list, pet_ids: list) -> FamilyBriefs`, `set_last_visit(ctx, customer_id, at: datetime | None) -> None`
  - `customer.domain.errors.PetPassedAwayError`(`PET_PASSED_AWAY`, 422)
  - `customer.dependencies.customer_directory_provider.get_customer_directory_use_case(db) -> CustomerDirectoryPort`(Task 7 에서 `main.py`가 꽂는다)
  - `CustomerSearchPort.set_last_visit(ctx, customer_id, at)`, 테스트 스텁 `FakeSearch.set_last_visit`(journal 에 `("set_last_visit", id, at)`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py` (수정):
```diff
@@ -174,3 +174,33 @@ async def test_customer_id가_bigint_범위를_벗어난_커서는_VALIDATION_ER
 async def test_key에_NUL이_있는_커서는_VALIDATION_ERROR_다(db_session):
     with pytest.raises(CustomerInputError):
         await _find(db_session, "", sort="name", cursor=_forged_cursor("김민\x00지", 1))
+
+
+async def _last_visit(session, customer_id):
+    return (await session.execute(
+        text("SELECT last_visit_at FROM customer_search_entries WHERE customer_id = :id"), {"id": customer_id}
+    )).scalar_one()
+
+
+async def test_마지막_방문_시각을_바꾸고_다시_만들어도_지킨다(db_session):
+    """원본은 visits 라 검색 줄을 다시 만들 때(가족 수정) 이 칸은 건드리지 않는다."""
+    from datetime import datetime, timezone
+
+    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
+    at = datetime(2026, 9, 23, 5, tzinfo=timezone.utc)
+    search = CustomerSearchPgAdapter(db_session)
+    await search.set_last_visit(A, customer_id, at)
+    assert await _last_visit(db_session, customer_id) == at
+    await search.rebuild_search_entry(A, customer_id)
+    assert await _last_visit(db_session, customer_id) == at
+    await search.set_last_visit(A, customer_id, None)
+    assert await _last_visit(db_session, customer_id) is None
+
+
+async def test_다른_매장_컨텍스트로는_마지막_방문_시각을_바꾸지_못한다(db_session):
+    from datetime import datetime, timezone
+
+    customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
+    await CustomerSearchPgAdapter(db_session).set_last_visit(
+        B, customer_id, datetime(2026, 9, 23, tzinfo=timezone.utc))
+    assert await _last_visit(db_session, customer_id) is None
```

`backend/apps/customer/tests/adapter/test_family_brief_pg_repository.py`:
```python
import pytest

from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _family(session, shop, phone="01012345678"):
    customer = await CustomerPgRepository(session).create(shop, customer_profile(phone=phone))
    pet = await PetPgRepository(session).add(shop, customer.id, pet_profile())
    return customer.id, pet.id


async def test_살아_있는_가족은_이름과_가린_번호를_돌려준다(db_session):
    customer_id, pet_id = await _family(db_session, A)
    repo = FamilyBriefPgRepository(db_session)
    [customer] = await repo.list_customer_briefs(A, [customer_id])
    assert (customer.name, customer.phone_masked) == ("김민지", "010-12··-5678")
    [pet] = await repo.list_pet_briefs(A, [pet_id])
    assert (pet.customer_id, pet.name, pet.species, pet.breed, pet.passed_away) == (
        customer_id, "콩이", "dog", "말티즈", False)


async def test_익명화한_가족도_틀은_돌려주고_이름은_비운다(db_session):
    customer_id, pet_id = await _family(db_session, A)
    await CustomerPgRepository(db_session).anonymize(A, customer_id)
    repo = FamilyBriefPgRepository(db_session)
    [customer] = await repo.list_customer_briefs(A, [customer_id])
    assert (customer.name, customer.phone_masked) == (None, None)
    [pet] = await repo.list_pet_briefs(A, [pet_id])
    assert (pet.name, pet.breed) == (None, "말티즈")


async def test_다른_매장의_ID_는_빠진다(db_session):
    """V1 — 다른 매장 방문이 가리키는 가족의 이름이 새지 않는다."""
    customer_id, pet_id = await _family(db_session, B)
    repo = FamilyBriefPgRepository(db_session)
    assert await repo.list_customer_briefs(A, [customer_id]) == []
    assert await repo.list_pet_briefs(A, [pet_id]) == []
```

`backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py`:
```python
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.domain.errors import CustomerNotFoundError, PetNotFoundError, PetPassedAwayError
from customer.tests.helpers.fakes import family
from customer.tests.helpers.profiles import ctx
from hub.app.dtos.family_brief import CustomerBrief, PetBrief


class _FakeBriefs:
    def __init__(self):
        self.calls = []

    async def list_customer_briefs(self, ctx, customer_ids):
        self.calls.append(("customers", customer_ids))
        return [CustomerBrief(customer_id=i, name=None, phone_masked=None) for i in customer_ids]

    async def list_pet_briefs(self, ctx, pet_ids):
        self.calls.append(("pets", pet_ids))
        return [PetBrief(pet_id=i, customer_id=1, name=None, species="dog", breed="말티즈",
                         weight_kg=Decimal("3.2"), passed_away=False) for i in pet_ids]


def _directory():
    journal, customers, pets, _, search = family()
    briefs = _FakeBriefs()
    return journal, customers, pets, briefs, CustomerDirectoryInteractor(customers, pets, briefs, search)


async def test_고객_행을_잠그고_반려동물이_그_가족인지_본다():
    journal, customers, pets, _, directory = _directory()
    customer = customers.seed()
    kong, dubu = pets.seed(customer.id, "콩이"), pets.seed(customer.id, "두부")
    await directory.lock_family(ctx(), customer.id, (kong.id, dubu.id))
    assert journal == [("lock_customer", customer.id)]


async def test_반려동물_없이_보호자만_잠글_수_있다():
    journal, customers, _, _, directory = _directory()
    customer = customers.seed()
    await directory.lock_family(ctx(), customer.id, ())
    assert journal == [("lock_customer", customer.id)]


async def test_다른_보호자의_반려동물이면_PET_NOT_FOUND_다():
    """V2 — 같은 매장이라도 다른 가족의 아이를 끼워 넣을 수 없다."""
    _, customers, pets, _, directory = _directory()
    mine, theirs = customers.seed(), customers.seed(phone="01099998888")
    other_pet = pets.seed(theirs.id, "남의 아이")
    with pytest.raises(PetNotFoundError):
        await directory.lock_family(ctx(), mine.id, (other_pet.id,))


async def test_무지개다리_아이면_PET_PASSED_AWAY_다():
    _, customers, pets, _, directory = _directory()
    customer = customers.seed()
    star = pets.seed(customer.id, "별이", passed_away=True)
    with pytest.raises(PetPassedAwayError):
        await directory.lock_family(ctx(), customer.id, (star.id,))


async def test_다른_매장의_고객이면_CUSTOMER_NOT_FOUND_다():
    _, customers, _, _, directory = _directory()
    customer = customers.seed(shop_id=2)
    with pytest.raises(CustomerNotFoundError):
        await directory.lock_family(ctx(shop_id=1), customer.id, ())


async def test_요약은_ID_로_찾게_묶는다():
    _, _, _, briefs, directory = _directory()
    found = await directory.briefs(ctx(), [1, 2], [101])
    assert set(found.customers) == {1, 2} and set(found.pets) == {101}
    assert briefs.calls == [("customers", [1, 2]), ("pets", [101])]


async def test_빈_목록이면_읽지_않는다():
    _, _, _, briefs, directory = _directory()
    found = await directory.briefs(ctx(), [], [])
    assert (found.customers, found.pets, briefs.calls) == ({}, {}, [])


async def test_마지막_방문_시각은_검색_포트로_넘긴다():
    journal, _, _, _, directory = _directory()
    at = datetime(2026, 9, 23, 5, tzinfo=timezone.utc)
    await directory.set_last_visit(ctx(), 1, at)
    await directory.set_last_visit(ctx(), 1, None)
    assert journal == [("set_last_visit", 1, at), ("set_last_visit", 1, None)]
```

`backend/apps/customer/tests/helpers/fakes.py` (수정):
```diff
@@ -171,6 +171,9 @@ class FakeSearch:
     async def rebuild_search_entry(self, ctx, customer_id):
         self.journal.append(("rebuild", customer_id))
 
+    async def set_last_visit(self, ctx, customer_id, at):
+        self.journal.append(("set_last_visit", customer_id, at))
+
     async def search(self, ctx, request):
         self.requests.append((ctx, request))
         return self.page
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_customer_directory_interactor.py apps/customer/tests/adapter/test_family_brief_pg_repository.py apps/customer/tests/adapter/test_customer_search_pg_adapter.py -q -p no:cacheprovider
```

Expected: `ModuleNotFoundError: No module named 'customer.app.use_cases.customer_directory_interactor'`, `AttributeError: ... 'set_last_visit'`로 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/customer/domain/errors.py` (수정):
```diff
@@ -32,3 +32,9 @@ class PetHealthRequiredError(CustomerError):
 
 class PetHealthConflictError(CustomerError):
     code = "PET_HEALTH_CONFLICT"
+
+
+class PetPassedAwayError(CustomerError):
+    """무지개다리 아이에게 예약을 잡으려 했다."""
+
+    code = "PET_PASSED_AWAY"
```

`backend/apps/hub/app/dtos/family_brief.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CustomerBrief:
    """다른 스포크에 보여 줄 보호자 요약. 익명화한 고객이면 이름과 번호가 None 이다."""

    customer_id: int
    name: str | None
    phone_masked: str | None


@dataclass(frozen=True)
class PetBrief:
    """다른 스포크에 보여 줄 반려동물 요약. 보호자가 익명화됐으면 이름이 None 이다."""

    pet_id: int
    customer_id: int
    name: str | None
    species: str
    breed: str
    weight_kg: Decimal
    passed_away: bool


@dataclass(frozen=True)
class FamilyBriefs:
    """ID 로 찾는 요약 묶음. 이 매장에 없는 ID 는 빠진다."""

    customers: dict[int, CustomerBrief]
    pets: dict[int, PetBrief]
```

`backend/apps/hub/app/ports/customer_directory_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.family_brief import FamilyBriefs
from hub.app.dtos.shop_context import ShopContext


class CustomerDirectoryPort(ABC):
    """구현: customer. 사용: visit (예약 등록·수정·상태 전이, 목록의 이름 표시, 최근 방문순)."""

    @abstractmethod
    async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
        """고객 행을 FOR UPDATE 로 잠그고 확인한다: 살아 있는 이 매장의 고객인가, 반려동물이 모두 그 보호자의
        아이이고 무지개다리가 아닌가. 통과하지 못하면 구현 쪽 도메인 오류(CUSTOMER_NOT_FOUND·PET_NOT_FOUND·
        PET_PASSED_AWAY)를 던진다.

        잠금은 부르는 쪽 트랜잭션이 끝날 때 풀린다. 방문을 쓰는 유스케이스는 방문 행을 잠그기 **전에** 부른다
        (잠금 순서: 고객 행 → 방문 행). 익명화·무지개다리·반려동물 삭제와 겹치지 않게 하려는 것이다.
        """

    @abstractmethod
    async def briefs(
        self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]
    ) -> FamilyBriefs:
        """보여 줄 요약. 익명화한 고객과 그 반려동물도 틀은 돌려준다(이름은 None)."""

    @abstractmethod
    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        """고객 목록 '최근 방문순'의 키를 바꾼다. 원본(visits)에서 다시 계산한 값을 같은 트랜잭션에서 넘긴다."""
```

`backend/apps/customer/app/ports/output/customer_search_port.py` (수정):
```diff
@@ -1,6 +1,7 @@
 from __future__ import annotations
 
 from abc import ABC, abstractmethod
+from datetime import datetime
 
 from customer.app.dtos.customer_search_dto import SearchPage, SearchRequest
 from customer.domain.services.search_terms import SearchWord
@@ -20,6 +21,13 @@ class CustomerSearchPort(ABC):
         가족(고객·반려동물·질병)을 바꾸는 모든 유스케이스가 같은 트랜잭션 안에서 부른다.
         """
 
+    @abstractmethod
+    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
+        """'최근 방문순'의 키를 바꾼다. 검색 줄이 없으면(익명화한 고객) 아무것도 하지 않는다.
+
+        원본은 visits 다 — visit 스포크가 허브 포트(CustomerDirectoryPort)로 알려 준다.
+        """
+
     @abstractmethod
     async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
         """커서가 올바르지 않으면 CustomerInputError."""
```

`backend/apps/customer/app/ports/output/family_brief_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from hub.app.dtos.shop_context import ShopContext


class FamilyBriefRepository(ABC):
    """다른 스포크에 보여 줄 요약. CustomerRepository 와 달리 익명화한 고객도 틀을 돌려준다(이름은 None) —
    방문 기록은 익명화한 뒤에도 남기 때문이다(설계 5.4)."""

    @abstractmethod
    async def list_customer_briefs(self, ctx: ShopContext, customer_ids: list[int]) -> list[CustomerBrief]: ...

    @abstractmethod
    async def list_pet_briefs(self, ctx: ShopContext, pet_ids: list[int]) -> list[PetBrief]: ...
```

`backend/apps/customer/app/use_cases/customer_directory_interactor.py`:
```python
from __future__ import annotations

from datetime import datetime

from customer.app.ports.output.customer_repository import CustomerRepository
from customer.app.ports.output.customer_search_port import CustomerSearchPort
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.app.ports.output.pet_repository import PetRepository
from customer.domain.errors import PetNotFoundError, PetPassedAwayError
from hub.app.dtos.family_brief import FamilyBriefs
from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort


class CustomerDirectoryInteractor(CustomerDirectoryPort):
    """허브의 CustomerDirectoryPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(
        self, customers: CustomerRepository, pets: PetRepository, briefs: FamilyBriefRepository,
        search: CustomerSearchPort,
    ) -> None:
        self._customers = customers
        self._pets = pets
        self._briefs = briefs
        self._search = search

    async def lock_family(self, ctx: ShopContext, customer_id: int, pet_ids: tuple[int, ...]) -> None:
        # 가족을 바꾸는 customer 유스케이스와 같은 잠금이다 — 익명화와 예약 생성이 서로를 기다린다.
        await self._customers.lock_active(ctx, customer_id)
        if not pet_ids:
            return
        family = {pet.id: pet for pet in await self._pets.list_for_customers(ctx, [customer_id])}
        for pet_id in pet_ids:
            if pet_id not in family:
                raise PetNotFoundError("반려동물을 찾을 수 없습니다.")
            if family[pet_id].passed_away:
                raise PetPassedAwayError("무지개다리를 건넌 아이에게는 예약을 잡을 수 없습니다.")

    async def briefs(self, ctx: ShopContext, customer_ids: list[int], pet_ids: list[int]) -> FamilyBriefs:
        customers = await self._briefs.list_customer_briefs(ctx, customer_ids) if customer_ids else []
        pets = await self._briefs.list_pet_briefs(ctx, pet_ids) if pet_ids else []
        return FamilyBriefs(
            customers={c.customer_id: c for c in customers}, pets={p.pet_id: p for p in pets}
        )

    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
        await self._search.set_last_visit(ctx, customer_id, at)
```

`backend/apps/customer/adapter/inbound/api/error_map.py` (수정):
```diff
@@ -7,6 +7,7 @@ from customer.domain.errors import (
     PetHealthConflictError,
     PetHealthRequiredError,
     PetNotFoundError,
+    PetPassedAwayError,
 )
 
 CUSTOMER_ERROR_STATUS: dict[type[Exception], int] = {
@@ -17,4 +18,5 @@ CUSTOMER_ERROR_STATUS: dict[type[Exception], int] = {
     CustomerInputError: 422,
     PetHealthRequiredError: 422,
     PetHealthConflictError: 422,
+    PetPassedAwayError: 422,
 }
```

`backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py` (수정):
```diff
@@ -5,7 +5,7 @@ import binascii
 import json
 from datetime import datetime
 
-from sqlalchemy import delete, exists, func, select, tuple_
+from sqlalchemy import delete, exists, func, select, tuple_, update
 from sqlalchemy.dialects.postgresql import insert
 from sqlalchemy.ext.asyncio import AsyncSession
 from sqlalchemy.orm import aliased
@@ -85,6 +85,13 @@ class CustomerSearchPgAdapter(CustomerSearchPort):
             stmt.on_conflict_do_update(index_elements=[Entry.customer_id], set_=values)
         )
 
+    async def set_last_visit(self, ctx: ShopContext, customer_id: int, at: datetime | None) -> None:
+        await self._session.execute(
+            update(Entry)
+            .where(Entry.customer_id == customer_id, Entry.shop_id == ctx.shop_id)
+            .values(last_visit_at=at)
+        )
+
     def _matching(self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool):
         """검색어의 모든 낱말에 걸리는 이 매장의 가족. 기본은 살아 있는 반려동물이 한 마리라도 있는 가족만."""
         conditions = [Entry.shop_id == ctx.shop_id]
```

`backend/apps/customer/adapter/outbound/pg/family_brief_pg_repository.py`:
```python
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from customer.adapter.outbound.orm.customer_orm import CustomerOrm, PetOrm
from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
from customer.domain.services.phone_number import mask_phone
from hub.app.dtos.family_brief import CustomerBrief, PetBrief
from hub.app.dtos.shop_context import ShopContext


class FamilyBriefPgRepository(FamilyBriefRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_customer_briefs(self, ctx: ShopContext, customer_ids: list[int]) -> list[CustomerBrief]:
        rows = (
            await self._session.execute(
                select(CustomerOrm.id, CustomerOrm.name, CustomerOrm.phone).where(
                    CustomerOrm.id.in_(customer_ids), CustomerOrm.shop_id == ctx.shop_id
                )
            )
        ).all()
        return [
            CustomerBrief(customer_id=id_, name=name, phone_masked=mask_phone(phone) if phone else None)
            for id_, name, phone in rows
        ]

    async def list_pet_briefs(self, ctx: ShopContext, pet_ids: list[int]) -> list[PetBrief]:
        rows = (
            await self._session.execute(
                select(PetOrm)
                .join(CustomerOrm, CustomerOrm.id == PetOrm.customer_id)
                .where(PetOrm.id.in_(pet_ids), CustomerOrm.shop_id == ctx.shop_id)
            )
        ).scalars()
        return [
            PetBrief(pet_id=p.id, customer_id=p.customer_id, name=p.name, species=p.species,
                     breed=p.breed, weight_kg=p.weight_kg, passed_away=p.passed_away_at is not None)
            for p in rows
        ]
```

`backend/apps/customer/dependencies/customer_directory_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.dependencies.customer_wiring import (
    build_customer_repository,
    build_customer_search,
    build_family_brief_repository,
    build_pet_repository,
)
from hub.app.ports.customer_directory_port import CustomerDirectoryPort


def get_customer_directory_use_case(db: DbSession) -> CustomerDirectoryPort:
    return CustomerDirectoryInteractor(
        customers=build_customer_repository(db), pets=build_pet_repository(db),
        briefs=build_family_brief_repository(db), search=build_customer_search(db),
    )
```

`backend/apps/customer/dependencies/customer_wiring.py` (수정):
```diff
@@ -6,10 +6,12 @@ from sqlalchemy.ext.asyncio import AsyncSession
 from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
 from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
 from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
+from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
 from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
 from customer.app.ports.output.condition_type_repository import ConditionTypeRepository
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
+from customer.app.ports.output.family_brief_repository import FamilyBriefRepository
 from customer.app.ports.output.pet_repository import PetRepository
 
 
@@ -27,3 +29,7 @@ def build_condition_type_repository(db: AsyncSession) -> ConditionTypeRepository
 
 def build_customer_search(db: AsyncSession) -> CustomerSearchPort:
     return CustomerSearchPgAdapter(db)
+
+
+def build_family_brief_repository(db: AsyncSession) -> FamilyBriefRepository:
+    return FamilyBriefPgRepository(db)
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/customer/tests/app/use_cases/test_customer_directory_interactor.py apps/customer/tests/adapter/test_family_brief_pg_repository.py apps/customer/tests/adapter/test_customer_search_pg_adapter.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **484 passed**, 통합 **213 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `family_brief_pg_repository.py` 두 쿼리의 `shop_id == ctx.shop_id` 조건을 지운다 → `test_다른_매장의_ID_는_빠진다`가 실패한다 — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/customer/adapter/inbound/api/error_map.py backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py backend/apps/customer/adapter/outbound/pg/family_brief_pg_repository.py backend/apps/customer/app/ports/output/customer_search_port.py backend/apps/customer/app/ports/output/family_brief_repository.py backend/apps/customer/app/use_cases/customer_directory_interactor.py backend/apps/customer/dependencies/customer_directory_provider.py backend/apps/customer/dependencies/customer_wiring.py backend/apps/customer/domain/errors.py backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py backend/apps/customer/tests/adapter/test_family_brief_pg_repository.py backend/apps/customer/tests/app/use_cases/test_customer_directory_interactor.py backend/apps/customer/tests/helpers/fakes.py backend/apps/hub/app/dtos/family_brief.py backend/apps/hub/app/ports/customer_directory_port.py
git commit -m "feat(customer): 허브 포트 CustomerDirectoryPort 와 customer 쪽 구현 — 가족 잠금·요약·마지막 방문 시각"
```

---

### Task 5: 매장 일정 설정과 임시 휴무 — 설정 조회·수정, 휴무 조회·추가·삭제

visit 의 첫 슬라이스 다섯과 공용 부품(오류 표, 경로 변수, 제어 문자 검증기, 조립 함수, 라우터 테스트 도우미)을 만든다. 설정 행은 매장을 처음 쓸 때 기본값으로 만들고 **같은 트랜잭션에서** 기본 메뉴를 넣는다(`ensure` — `INSERT … ON CONFLICT DO NOTHING RETURNING`, 돌려받은 행이 있을 때만 메뉴를 넣는다). 설정 행이 있다는 것이 곧 기본 메뉴를 넣었다는 뜻이라 표시 칸이 없다. 수정은 설정 행 UPDATE 를 맨 먼저 한다 — 두 사장이 동시에 바꾸면 늦은 쪽이 그 행에서 기다렸다가 앞선 쪽이 커밋한 쉬는 요일을 지우고 넣는다("새로 정한 것" 12). 휴무 추가·삭제는 두 번 눌러도 같은 결과다. 일정 수정은 `shop:update`(사장만, V8).

**Files:**
- Modify: `backend/apps/visit/domain/services/visit_schedule.py`
- Create: `backend/apps/visit/domain/value_objects/closed_date.py`
- Create: `backend/apps/visit/app/dtos/add_closed_date_dto.py`
- Create: `backend/apps/visit/app/dtos/delete_closed_date_dto.py`
- Create: `backend/apps/visit/app/dtos/get_visit_settings_dto.py`
- Create: `backend/apps/visit/app/dtos/list_closed_dates_dto.py`
- Create: `backend/apps/visit/app/dtos/schedule_view_dto.py`
- Create: `backend/apps/visit/app/dtos/update_visit_settings_dto.py`
- Create: `backend/apps/visit/app/ports/input/add_closed_date_use_case.py`
- Create: `backend/apps/visit/app/ports/input/delete_closed_date_use_case.py`
- Create: `backend/apps/visit/app/ports/input/get_visit_settings_use_case.py`
- Create: `backend/apps/visit/app/ports/input/list_closed_dates_use_case.py`
- Create: `backend/apps/visit/app/ports/input/update_visit_settings_use_case.py`
- Create: `backend/apps/visit/app/ports/output/schedule_repository.py`
- Create: `backend/apps/visit/app/use_cases/add_closed_date_interactor.py`
- Create: `backend/apps/visit/app/use_cases/delete_closed_date_interactor.py`
- Create: `backend/apps/visit/app/use_cases/get_visit_settings_interactor.py`
- Create: `backend/apps/visit/app/use_cases/list_closed_dates_interactor.py`
- Create: `backend/apps/visit/app/use_cases/update_visit_settings_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/error_map.py`
- Create: `backend/apps/visit/adapter/inbound/api/path_params.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/add_closed_date_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_settings_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/list_closed_dates_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/text_validators.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/update_visit_settings_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/add_closed_date_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/delete_closed_date_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_visit_settings_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/list_closed_dates_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/update_visit_settings_router.py`
- Create: `backend/apps/visit/adapter/outbound/pg/schedule_pg_repository.py`
- Create: `backend/apps/visit/dependencies/add_closed_date_provider.py`
- Create: `backend/apps/visit/dependencies/delete_closed_date_provider.py`
- Create: `backend/apps/visit/dependencies/get_visit_settings_provider.py`
- Create: `backend/apps/visit/dependencies/list_closed_dates_provider.py`
- Create: `backend/apps/visit/dependencies/update_visit_settings_provider.py`
- Create: `backend/apps/visit/dependencies/visit_wiring.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_add_closed_date_router.py`
- Test: `backend/apps/visit/tests/adapter/test_delete_closed_date_router.py`
- Test: `backend/apps/visit/tests/adapter/test_get_visit_settings_router.py`
- Test: `backend/apps/visit/tests/adapter/test_list_closed_dates_router.py`
- Test: `backend/apps/visit/tests/adapter/test_schedule_pg_repository.py`
- Test: `backend/apps/visit/tests/adapter/test_update_visit_settings_router.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_add_closed_date_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_delete_closed_date_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_get_visit_settings_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_list_closed_dates_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_update_visit_settings_interactor.py`
- Test: `backend/apps/visit/tests/helpers/api.py`
- Test: `backend/apps/visit/tests/helpers/fakes.py`
- Create: 빈 `__init__.py` 15개(Step 1)

**Interfaces:**
- Consumes: Task 2 의 `ScheduleSettings`·`DEFAULT_*`·`check_duration`, Task 3 의 ORM
- Produces:
  - `visit.domain.services.visit_schedule.check_settings(settings)`, `visit.domain.value_objects.closed_date.ClosedDate(day, note)`
  - `visit.app.ports.output.schedule_repository.ScheduleRepository`: `ensure(ctx) -> ScheduleSettings`, `update(ctx, settings)`, `list_closed_dates(ctx, start, end)`, `add_closed_date(ctx, day, note)`, `delete_closed_date(ctx, day)`
  - `visit.app.dtos.schedule_view_dto`: `VisitSettingsView`, `ClosedDateView`
  - `visit.adapter.inbound.api.error_map.VISIT_ERROR_STATUS`, `path_params.VisitId`·`MenuId`, `schemas.text_validators.reject_control_chars`
  - `visit.dependencies.visit_wiring.build_schedule_repository(db)`
  - 테스트 도우미 `visit.tests.helpers.api`: `build_app`, `client`, `error_of`, `Recorder`(스텁 유스케이스 — 받은 명령을 `calls`에), `OWNER`·`STAFF`·`READ_ONLY`; `visit.tests.helpers.fakes`: `Journal`, `FakeSchedule`

- [ ] **Step 1: 패키지를 만든다**

Run (저장소 루트에서):
```bash
mkdir -p backend/apps/visit/adapter/inbound \
  backend/apps/visit/adapter/inbound/api \
  backend/apps/visit/adapter/inbound/api/schemas \
  backend/apps/visit/adapter/inbound/api/v1 \
  backend/apps/visit/adapter/outbound/mappers \
  backend/apps/visit/adapter/outbound/pg \
  backend/apps/visit/app/dtos \
  backend/apps/visit/app/ports \
  backend/apps/visit/app/ports/input \
  backend/apps/visit/app/ports/output \
  backend/apps/visit/app/services \
  backend/apps/visit/app/use_cases \
  backend/apps/visit/dependencies \
  backend/apps/visit/tests/app \
  backend/apps/visit/tests/app/use_cases
touch backend/apps/visit/adapter/inbound/__init__.py \
  backend/apps/visit/adapter/inbound/api/__init__.py \
  backend/apps/visit/adapter/inbound/api/schemas/__init__.py \
  backend/apps/visit/adapter/inbound/api/v1/__init__.py \
  backend/apps/visit/adapter/outbound/mappers/__init__.py \
  backend/apps/visit/adapter/outbound/pg/__init__.py \
  backend/apps/visit/app/dtos/__init__.py \
  backend/apps/visit/app/ports/__init__.py \
  backend/apps/visit/app/ports/input/__init__.py \
  backend/apps/visit/app/ports/output/__init__.py \
  backend/apps/visit/app/services/__init__.py \
  backend/apps/visit/app/use_cases/__init__.py \
  backend/apps/visit/dependencies/__init__.py \
  backend/apps/visit/tests/app/__init__.py \
  backend/apps/visit/tests/app/use_cases/__init__.py
```

- [ ] **Step 2: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_add_closed_date_router.py`:
```python
from datetime import date

from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.dependencies.add_closed_date_provider import get_add_closed_date_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


async def test_휴무_추가는_사장만_메모의_빈_문자열은_None():
    stub = Recorder(ClosedDateView(date=date(2026, 10, 9), note=None))
    async with client(build_app(add_closed_date_router, get_add_closed_date_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/closed-dates", json={"date": "2026-10-09", "note": " "})
    assert response.status_code == 200
    assert (stub.calls[0].day, stub.calls[0].note) == (date(2026, 10, 9), None)
    async with client(build_app(add_closed_date_router, get_add_closed_date_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/closed-dates", json={"date": "2026-10-09"})
    assert error_of(response) == (403, "PERMISSION_DENIED")
```

`backend/apps/visit/tests/adapter/test_delete_closed_date_router.py`:
```python
from datetime import date

from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
from visit.dependencies.delete_closed_date_provider import get_delete_closed_date_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of


async def test_휴무_삭제는_사장만_204():
    stub = Recorder()
    async with client(build_app(delete_closed_date_router, get_delete_closed_date_use_case, stub)) as c:
        assert (await c.delete("/v1/shops/3/closed-dates/2026-10-09")).status_code == 204
        assert error_of(await c.delete("/v1/shops/3/closed-dates/10월9일")) == (422, "VALIDATION_ERROR")
    assert stub.calls[0].day == date(2026, 10, 9)
    async with client(build_app(delete_closed_date_router, get_delete_closed_date_use_case, stub, STAFF)) as c:
        assert error_of(await c.delete("/v1/shops/3/closed-dates/2026-10-09")) == (403, "PERMISSION_DENIED")
```

`backend/apps/visit/tests/adapter/test_get_visit_settings_router.py`:
```python
from datetime import time

from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.dependencies.get_visit_settings_provider import get_get_visit_settings_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client

SETTINGS = VisitSettingsView(opens_at=time(10), closes_at=time(19), default_duration_minutes=120,
                             closed_weekdays=[0])


async def test_직원도_설정을_본다():
    stub = Recorder(SETTINGS)
    async with client(build_app(get_visit_settings_router, get_get_visit_settings_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visit-settings")
    assert response.json() == {"opens_at": "10:00:00", "closes_at": "19:00:00",
                               "default_duration_minutes": 120, "closed_weekdays": [0]}
    assert stub.calls[0].ctx.shop_id == 3
```

`backend/apps/visit/tests/adapter/test_list_closed_dates_router.py`:
```python
from datetime import date

from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.dependencies.list_closed_dates_provider import get_list_closed_dates_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_휴무_조회는_from_to_로_받는다():
    stub = Recorder([ClosedDateView(date=date(2026, 10, 9), note="한글날")])
    async with client(build_app(list_closed_dates_router, get_list_closed_dates_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/closed-dates?from=2026-10-01&to=2026-10-31")
    assert response.json() == {"items": [{"date": "2026-10-09", "note": "한글날"}]}
    assert (stub.calls[0].start, stub.calls[0].end) == (date(2026, 10, 1), date(2026, 10, 31))
```

`backend/apps/visit/tests/adapter/test_schedule_pg_repository.py`:
```python
import asyncio
from datetime import date, time

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS, ScheduleSettings
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _menus(session, shop_id=1):
    return (await session.execute(
        text("SELECT name, default_duration_minutes FROM service_menus WHERE shop_id = :s ORDER BY sort_order"),
        {"s": shop_id})).all()


async def test_처음_쓰면_기본_설정과_기본_메뉴가_생긴다(db_session):
    settings = await SchedulePgRepository(db_session).ensure(A)
    assert settings == DEFAULT_SETTINGS
    assert await _menus(db_session) == [("목욕", 60), ("위생", 60), ("부분 미용", 90), ("전체 미용", 150),
                                        ("스포팅", 120)]


async def test_두_번_준비해도_메뉴는_한_번만_들어간다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.ensure(A)
    assert len(await _menus(db_session)) == 5


async def test_두_세션이_동시에_처음_써도_메뉴는_한_번만_들어간다(db_engine):
    """늦은 쪽은 설정 행 INSERT 에서 앞선 쪽의 커밋을 기다렸다가 DO NOTHING 이 된다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as first, factory() as second:
        await SchedulePgRepository(first).ensure(A)
        late = asyncio.create_task(SchedulePgRepository(second).ensure(A))
        await asyncio.sleep(0.3)
        assert not late.done()
        await first.commit()
        assert await late == DEFAULT_SETTINGS
        await second.commit()
    async with factory() as check:
        assert len(await _menus(check)) == 5


async def test_설정을_통째로_바꾼다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.update(A, ScheduleSettings(time(9, 30), time(18), 90, frozenset({0, 6})))
    changed = await repo.update(A, ScheduleSettings(time(9, 30), time(18), 90, frozenset({1})))
    assert changed == ScheduleSettings(time(9, 30), time(18), 90, frozenset({1}))


async def test_매장마다_따로다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.ensure(B)
    await repo.update(A, ScheduleSettings(time(9), time(18), 60, frozenset({0})))
    assert await repo.ensure(B) == DEFAULT_SETTINGS
    await repo.add_closed_date(A, date(2026, 10, 9), "한글날")
    assert await repo.list_closed_dates(B, date(2026, 1, 1), date(2026, 12, 31)) == []
    await repo.delete_closed_date(B, date(2026, 10, 9))   # 다른 매장 컨텍스트로는 지우지 못한다
    assert len(await repo.list_closed_dates(A, date(2026, 1, 1), date(2026, 12, 31))) == 1


async def test_임시_휴무는_두_번_넣어도_하나고_처음_메모를_지킨다(db_session):
    repo = SchedulePgRepository(db_session)
    await repo.ensure(A)
    await repo.add_closed_date(A, date(2026, 10, 9), "한글날")
    again = await repo.add_closed_date(A, date(2026, 10, 9), "다른 메모")
    assert (again.day, again.note) == (date(2026, 10, 9), "한글날")
    await repo.add_closed_date(A, date(2026, 10, 3), None)
    found = await repo.list_closed_dates(A, date(2026, 10, 1), date(2026, 10, 9))
    assert [c.day for c in found] == [date(2026, 10, 3), date(2026, 10, 9)]
    await repo.delete_closed_date(A, date(2026, 10, 3))
    await repo.delete_closed_date(A, date(2026, 10, 3))
    assert [c.day for c in await repo.list_closed_dates(A, date(2026, 10, 1), date(2026, 10, 31))] == [
        date(2026, 10, 9)]


async def test_두_사장이_동시에_쉬는_요일을_바꿔도_늦은_쪽이_앞선_쪽을_덮는다(db_engine):
    """늦은 쪽은 설정 행 UPDATE 에서 기다렸다가, 앞선 쪽이 커밋한 쉬는 요일을 지우고 자기 것을 넣는다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    async with factory() as setup:
        await SchedulePgRepository(setup).ensure(A)
        await setup.commit()
    async with factory() as first, factory() as second:
        await SchedulePgRepository(first).update(A, ScheduleSettings(time(10), time(19), 120, frozenset({0, 1})))
        late = asyncio.create_task(
            SchedulePgRepository(second).update(A, ScheduleSettings(time(9), time(18), 90, frozenset({1, 2})))
        )
        await asyncio.sleep(0.3)
        assert not late.done()
        await first.commit()
        assert (await late).closed_weekdays == frozenset({1, 2})
        await second.commit()
    async with factory() as check:
        assert await SchedulePgRepository(check).ensure(A) == ScheduleSettings(time(9), time(18), 90, frozenset({1, 2}))
```

`backend/apps/visit/tests/adapter/test_update_visit_settings_router.py`:
```python
from datetime import time

from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.dependencies.update_visit_settings_provider import get_update_visit_settings_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

SETTINGS = VisitSettingsView(opens_at=time(10), closes_at=time(19), default_duration_minutes=120,
                             closed_weekdays=[0])
BODY = {"opens_at": "09:30", "closes_at": "18:00", "default_duration_minutes": 90, "closed_weekdays": [0, 6]}


async def test_사장은_설정을_바꾼다():
    stub = Recorder(SETTINGS)
    async with client(build_app(update_visit_settings_router, get_update_visit_settings_use_case, stub)) as c:
        response = await c.put("/v1/shops/3/visit-settings", json=BODY)
    assert response.status_code == 200
    settings = stub.calls[0].settings
    assert (settings.opens_at, settings.closes_at, settings.default_duration_minutes, settings.closed_weekdays) == (
        time(9, 30), time(18), 90, frozenset({0, 6}))


async def test_직원은_설정을_바꾸지_못한다():
    """V8 — 일정·메뉴 수정은 shop:update(사장만)."""
    async with client(build_app(update_visit_settings_router, get_update_visit_settings_use_case,
                                Recorder(SETTINGS), STAFF)) as c:
        response = await c.put("/v1/shops/3/visit-settings", json=BODY)
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_요일이_범위를_벗어나거나_문자열이면_422_다():
    async with client(build_app(update_visit_settings_router, get_update_visit_settings_use_case,
                                Recorder(SETTINGS))) as c:
        for bad in ({**BODY, "closed_weekdays": [7]}, {**BODY, "closed_weekdays": ["0"]},
                    {**BODY, "default_duration_minutes": "90"}):
            assert error_of(await c.put("/v1/shops/3/visit-settings", json=bad)) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/app/use_cases/test_add_closed_date_interactor.py`:
```python
from datetime import date

from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.use_cases.add_closed_date_interactor import AddClosedDateInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_추가는_설정을_준비한_뒤_넣는다():
    schedule = FakeSchedule()
    view = await AddClosedDateInteractor(schedule).add_closed_date(
        AddClosedDateCommand(ctx=ctx(), day=date(2026, 10, 9), note="한글날"))
    assert (view.date, view.note) == (date(2026, 10, 9), "한글날")
    assert schedule.journal == [("ensure", 1), ("add_closed_date", date(2026, 10, 9))]
```

`backend/apps/visit/tests/app/use_cases/test_delete_closed_date_interactor.py`:
```python
from datetime import date

from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand
from visit.app.use_cases.delete_closed_date_interactor import DeleteClosedDateInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_삭제는_없어도_성공한다():
    schedule = FakeSchedule()
    await DeleteClosedDateInteractor(schedule).delete_closed_date(
        DeleteClosedDateCommand(ctx=ctx(), day=date(2026, 10, 9)))
    assert schedule.journal == [("delete_closed_date", date(2026, 10, 9))]
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_settings_interactor.py`:
```python
from datetime import time

from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.use_cases.get_visit_settings_interactor import GetVisitSettingsInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_조회는_설정을_준비하고_쉬는_요일을_정렬해_돌려준다():
    schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 120, frozenset({6, 0})))
    view = await GetVisitSettingsInteractor(schedule).get_visit_settings(GetVisitSettingsQuery(ctx=ctx()))
    assert (view.opens_at, view.closes_at, view.default_duration_minutes, view.closed_weekdays) == (
        time(10), time(19), 120, [0, 6])
    assert schedule.journal == [("ensure", 1)]
```

`backend/apps/visit/tests/app/use_cases/test_list_closed_dates_interactor.py`:
```python
from datetime import date

import pytest

from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.use_cases.list_closed_dates_interactor import ListClosedDatesInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.closed_date import ClosedDate
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_기간_안의_휴무를_날짜_순으로():
    schedule = FakeSchedule()
    for shop, day in ((1, date(2026, 10, 9)), (1, date(2026, 10, 3)), (1, date(2026, 11, 1)), (2, date(2026, 10, 5))):
        schedule.closed[(shop, day)] = ClosedDate(day=day, note=None)
    views = await ListClosedDatesInteractor(schedule).list_closed_dates(
        ListClosedDatesQuery(ctx=ctx(), start=date(2026, 10, 1), end=date(2026, 10, 31)))
    assert [v.date for v in views] == [date(2026, 10, 3), date(2026, 10, 9)]


@pytest.mark.parametrize(("start", "end"), [
    (date(2026, 10, 2), date(2026, 10, 1)),     # 거꾸로
    (date(2026, 1, 1), date(2027, 2, 6)),       # 401일
])
async def test_기간이_거꾸로거나_400일을_넘으면_VALIDATION_ERROR_다(start, end):
    with pytest.raises(VisitInputError):
        await ListClosedDatesInteractor(FakeSchedule()).list_closed_dates(
            ListClosedDatesQuery(ctx=ctx(), start=start, end=end))
```

`backend/apps/visit/tests/app/use_cases/test_update_visit_settings_interactor.py`:
```python
from datetime import time

import pytest

from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand
from visit.app.use_cases.update_visit_settings_interactor import UpdateVisitSettingsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeSchedule


async def test_수정은_검증하고_준비한_뒤_바꾼다():
    schedule = FakeSchedule()
    new = ScheduleSettings(time(9, 30), time(18), 90, frozenset({0}))
    view = await UpdateVisitSettingsInteractor(schedule).update_visit_settings(
        UpdateVisitSettingsCommand(ctx=ctx(), settings=new))
    assert (view.opens_at, view.closed_weekdays) == (time(9, 30), [0])
    assert schedule.journal == [("ensure", 1), ("update_settings", 1)]


@pytest.mark.parametrize("settings", [
    ScheduleSettings(time(19), time(10), 120, frozenset()),        # 여는 시각이 늦다
    ScheduleSettings(time(10), time(10), 120, frozenset()),        # 같다
    ScheduleSettings(time(10, 15), time(19), 120, frozenset()),    # 10분 단위가 아니다
    ScheduleSettings(time(10), time(19), 95, frozenset()),         # 소요 규칙
])
async def test_규칙에_어긋나면_쓰지_않는다(settings):
    schedule = FakeSchedule()
    with pytest.raises(VisitInputError):
        await UpdateVisitSettingsInteractor(schedule).update_visit_settings(
            UpdateVisitSettingsCommand(ctx=ctx(), settings=settings))
    assert schedule.journal == []
```

`backend/apps/visit/tests/helpers/api.py`:
```python
"""visit 라우터 테스트가 함께 쓰는 도우미 — 유스케이스와 매장 접근 확인을 스텁으로 바꾼 앱을 만든다."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_db
from core.http_errors import install_error_handlers
from core.security import get_current_user_id
from core.shop_guard import get_shop_access_port
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
from visit.tests.helpers.builders import OWNER_PERMISSIONS, STAFF_PERMISSIONS, TZ


class StubShopAccess:
    """ShopAccessPort 스텁 — 어느 매장이든 같은 역할·권한의 멤버로 통과시킨다."""

    def __init__(self, permissions=OWNER_PERMISSIONS, role="owner"):
        self.permissions = frozenset(permissions)
        self.role = role

    async def resolve(self, user_id, shop_id):
        return ShopContext(shop_id=shop_id, member_id=11, role=self.role, permissions=self.permissions,
                           timezone=TZ)


OWNER = StubShopAccess()
STAFF = StubShopAccess(STAFF_PERMISSIONS, role="staff")
READ_ONLY = StubShopAccess(frozenset({"customer:write"}), role="staff")   # reservation:write 없음


async def _no_db():
    yield None


def build_app(router, provider, stub_use_case, access=None) -> FastAPI:
    """access=None 이면 사장 권한으로 통과시킨다."""
    app = FastAPI()
    app.include_router(router)
    install_error_handlers(app, VISIT_ERROR_STATUS)
    app.dependency_overrides[provider] = lambda: stub_use_case
    app.dependency_overrides[get_db] = _no_db
    app.dependency_overrides[get_current_user_id] = lambda: 5
    app.dependency_overrides[get_shop_access_port] = lambda: access or OWNER
    return app


def client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def error_of(response) -> tuple[int, str]:
    return (response.status_code, response.json()["code"])


class Recorder:
    """유스케이스 스텁 — 받은 명령을 남기고, 정해 둔 값을 돌려주거나 오류를 던진다."""

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def __getattr__(self, name):
        async def call(command):
            self.calls.append(command)
            if self.error:
                raise self.error
            return self.result

        return call
```

`backend/apps/visit/tests/helpers/fakes.py`:
```python
"""visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
from __future__ import annotations

from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS


class Journal(list):
    """스텁들이 함께 쓰는 호출 기록. 항목은 (이름, 인자…) 튜플이다."""


class FakeSchedule:
    def __init__(self, journal: Journal | None = None, settings=DEFAULT_SETTINGS) -> None:
        self.journal = journal if journal is not None else Journal()
        self.settings = settings
        self.closed: dict[tuple[int, object], ClosedDate] = {}

    async def ensure(self, ctx):
        self.journal.append(("ensure", ctx.shop_id))
        return self.settings

    async def update(self, ctx, settings):
        self.journal.append(("update_settings", ctx.shop_id))
        self.settings = settings
        return settings

    async def list_closed_dates(self, ctx, start, end):
        return sorted(
            (c for (shop, day), c in self.closed.items() if shop == ctx.shop_id and start <= day <= end),
            key=lambda c: c.day,
        )

    async def add_closed_date(self, ctx, day, note):
        self.journal.append(("add_closed_date", day))
        return self.closed.setdefault((ctx.shop_id, day), ClosedDate(day=day, note=note))

    async def delete_closed_date(self, ctx, day):
        self.journal.append(("delete_closed_date", day))
        self.closed.pop((ctx.shop_id, day), None)
```

- [ ] **Step 3: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해(`ModuleNotFoundError`) 모두 실패한다.

- [ ] **Step 4: 구현한다**

`backend/apps/visit/domain/services/visit_schedule.py` (수정):
```diff
@@ -53,6 +53,16 @@ def check_duration(minutes: int) -> None:
         raise VisitInputError("소요 시간은 10분 단위로 10분에서 600분 사이여야 합니다.")
 
 
+def check_settings(settings: ScheduleSettings) -> None:
+    """영업시간은 10분 단위이고 여는 시각이 닫는 시각보다 앞선다. 기본 소요도 소요 규칙을 따른다."""
+    for clock in (settings.opens_at, settings.closes_at):
+        if clock.minute % STEP_MINUTES or clock.second or clock.microsecond:
+            raise VisitInputError("영업시간은 10분 단위여야 합니다.")
+    if settings.opens_at >= settings.closes_at:
+        raise VisitInputError("여는 시각은 닫는 시각보다 앞서야 합니다.")
+    check_duration(settings.default_duration_minutes)
+
+
 def check_start(starts_at: datetime, now: datetime, tz: str) -> None:
     """예약 시각 — 10분 단위, 오늘 기준 앞뒤 1년 안."""
     local = starts_at.astimezone(ZoneInfo(tz))
```

`backend/apps/visit/domain/value_objects/closed_date.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ClosedDate:
    """임시 휴무일 하나."""

    day: date
    note: str | None
```

`backend/apps/visit/app/dtos/add_closed_date_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class AddClosedDateCommand:
    ctx: ShopContext
    day: date
    note: str | None
```

`backend/apps/visit/app/dtos/delete_closed_date_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class DeleteClosedDateCommand:
    ctx: ShopContext
    day: date
```

`backend/apps/visit/app/dtos/get_visit_settings_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetVisitSettingsQuery:
    ctx: ShopContext
```

`backend/apps/visit/app/dtos/list_closed_dates_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListClosedDatesQuery:
    ctx: ShopContext
    start: date
    end: date
```

`backend/apps/visit/app/dtos/schedule_view_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings


@dataclass(frozen=True)
class VisitSettingsView:
    opens_at: time
    closes_at: time
    default_duration_minutes: int
    closed_weekdays: list[int]   # 월=0 … 일=6, 오름차순

    @classmethod
    def of(cls, settings: ScheduleSettings) -> VisitSettingsView:
        return cls(opens_at=settings.opens_at, closes_at=settings.closes_at,
                   default_duration_minutes=settings.default_duration_minutes,
                   closed_weekdays=sorted(settings.closed_weekdays))


@dataclass(frozen=True)
class ClosedDateView:
    date: date
    note: str | None

    @classmethod
    def of(cls, closed: ClosedDate) -> ClosedDateView:
        return cls(date=closed.day, note=closed.note)
```

`backend/apps/visit/app/dtos/update_visit_settings_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.schedule_settings import ScheduleSettings


@dataclass(frozen=True)
class UpdateVisitSettingsCommand:
    """설정 전체를 바꾼다(PUT). 쉬는 요일도 통째로."""

    ctx: ShopContext
    settings: ScheduleSettings
```

`backend/apps/visit/app/ports/input/add_closed_date_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.dtos.schedule_view_dto import ClosedDateView


class AddClosedDateUseCase(ABC):
    @abstractmethod
    async def add_closed_date(self, command: AddClosedDateCommand) -> ClosedDateView: ...
```

`backend/apps/visit/app/ports/input/delete_closed_date_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand


class DeleteClosedDateUseCase(ABC):
    @abstractmethod
    async def delete_closed_date(self, command: DeleteClosedDateCommand) -> None: ...
```

`backend/apps/visit/app/ports/input/get_visit_settings_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.dtos.schedule_view_dto import VisitSettingsView


class GetVisitSettingsUseCase(ABC):
    @abstractmethod
    async def get_visit_settings(self, query: GetVisitSettingsQuery) -> VisitSettingsView: ...
```

`backend/apps/visit/app/ports/input/list_closed_dates_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.dtos.schedule_view_dto import ClosedDateView


class ListClosedDatesUseCase(ABC):
    @abstractmethod
    async def list_closed_dates(self, query: ListClosedDatesQuery) -> list[ClosedDateView]: ...
```

`backend/apps/visit/app/ports/input/update_visit_settings_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand


class UpdateVisitSettingsUseCase(ABC):
    @abstractmethod
    async def update_visit_settings(self, command: UpdateVisitSettingsCommand) -> VisitSettingsView: ...
```

`backend/apps/visit/app/ports/output/schedule_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings


class ScheduleRepository(ABC):
    """매장 일정 설정과 임시 휴무. 설정 행은 매장을 처음 쓸 때 만든다."""

    @abstractmethod
    async def ensure(self, ctx: ShopContext) -> ScheduleSettings:
        """설정을 읽는다. 없으면 기본값으로 만들고 **같은 트랜잭션에서** 기본 메뉴를 넣는다.

        두 요청이 동시에 처음 써도 설정과 기본 메뉴는 한 번만 들어간다(INSERT … ON CONFLICT DO NOTHING).
        """

    @abstractmethod
    async def update(self, ctx: ShopContext, settings: ScheduleSettings) -> ScheduleSettings:
        """통째로 바꾼다(쉬는 요일도). 설정 행이 이미 있어야 한다(ensure 뒤에 부른다)."""

    @abstractmethod
    async def list_closed_dates(self, ctx: ShopContext, start: date, end: date) -> list[ClosedDate]:
        """start 부터 end 까지(둘 다 포함) 날짜 순으로."""

    @abstractmethod
    async def add_closed_date(self, ctx: ShopContext, day: date, note: str | None) -> ClosedDate:
        """이미 있으면 그대로 두고 있는 것을 돌려준다. 설정 행이 이미 있어야 한다(ensure 뒤에 부른다)."""

    @abstractmethod
    async def delete_closed_date(self, ctx: ShopContext, day: date) -> None:
        """없으면 아무것도 하지 않는다."""
```

`backend/apps/visit/app/use_cases/add_closed_date_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.app.ports.input.add_closed_date_use_case import AddClosedDateUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository


class AddClosedDateInteractor(AddClosedDateUseCase):
    """임시 휴무 추가. 이미 있으면 그대로 둔다(두 번 눌러도 하나). 그날의 예약은 그대로다(경고만 생긴다)."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def add_closed_date(self, command: AddClosedDateCommand) -> ClosedDateView:
        await self._schedule.ensure(command.ctx)   # 휴무 행은 설정 행을 가리킨다(외래 키)
        return ClosedDateView.of(
            await self._schedule.add_closed_date(command.ctx, command.day, command.note)
        )
```

`backend/apps/visit/app/use_cases/delete_closed_date_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand
from visit.app.ports.input.delete_closed_date_use_case import DeleteClosedDateUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository


class DeleteClosedDateInteractor(DeleteClosedDateUseCase):
    """없는 날을 지워도 성공이다(두 번 눌러도 같은 결과)."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def delete_closed_date(self, command: DeleteClosedDateCommand) -> None:
        await self._schedule.delete_closed_date(command.ctx, command.day)
```

`backend/apps/visit/app/use_cases/get_visit_settings_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.app.ports.input.get_visit_settings_use_case import GetVisitSettingsUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository


class GetVisitSettingsInteractor(GetVisitSettingsUseCase):
    """처음 부르는 매장이면 기본 설정과 기본 메뉴가 이때 생긴다."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def get_visit_settings(self, query: GetVisitSettingsQuery) -> VisitSettingsView:
        return VisitSettingsView.of(await self._schedule.ensure(query.ctx))
```

`backend/apps/visit/app/use_cases/list_closed_dates_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.dtos.schedule_view_dto import ClosedDateView
from visit.app.ports.input.list_closed_dates_use_case import ListClosedDatesUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.errors import VisitInputError

MAX_RANGE_DAYS = 400


class ListClosedDatesInteractor(ListClosedDatesUseCase):
    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def list_closed_dates(self, query: ListClosedDatesQuery) -> list[ClosedDateView]:
        if query.start > query.end or (query.end - query.start).days > MAX_RANGE_DAYS:
            raise VisitInputError("기간은 시작이 끝보다 앞서고 400일을 넘지 않아야 합니다.")
        found = await self._schedule.list_closed_dates(query.ctx, query.start, query.end)
        return [ClosedDateView.of(closed) for closed in found]
```

`backend/apps/visit/app/use_cases/update_visit_settings_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.schedule_view_dto import VisitSettingsView
from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand
from visit.app.ports.input.update_visit_settings_use_case import UpdateVisitSettingsUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.visit_schedule import check_settings


class UpdateVisitSettingsInteractor(UpdateVisitSettingsUseCase):
    """영업시간·기본 소요·쉬는 요일을 바꾼다. 이미 잡힌 예약은 그대로다(경고만 달라진다)."""

    def __init__(self, schedule: ScheduleRepository) -> None:
        self._schedule = schedule

    async def update_visit_settings(self, command: UpdateVisitSettingsCommand) -> VisitSettingsView:
        check_settings(command.settings)
        await self._schedule.ensure(command.ctx)
        return VisitSettingsView.of(await self._schedule.update(command.ctx, command.settings))
```

`backend/apps/visit/adapter/inbound/api/error_map.py`:
```python
"""visit 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
from visit.domain.errors import (
    MenuNameTakenError,
    MenuNotAvailableError,
    MenuNotFoundError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotFoundError,
    VisitNotYetError,
    VisitStateConflictError,
)

VISIT_ERROR_STATUS: dict[type[Exception], int] = {
    VisitNotFoundError: 404,
    MenuNotFoundError: 404,
    VisitStateConflictError: 409,
    VisitNotYetError: 409,
    VisitDuplicateError: 409,
    MenuNameTakenError: 409,
    VisitInputError: 422,
    VisitCrossesMidnightError: 422,
    VisitGroupMismatchError: 422,
    MenuNotAvailableError: 422,
}
```

`backend/apps/visit/adapter/inbound/api/path_params.py`:
```python
"""visit 경로 변수. bigint 를 넘는 값은 DB 에 닿기 전에 422 로 막는다(닿으면 asyncpg 오류로 500 이 된다)."""
from typing import Annotated

from fastapi import Path

_MAX_BIGINT = 9_223_372_036_854_775_807

VisitId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
MenuId = Annotated[int, Path(ge=1, le=_MAX_BIGINT)]
```

`backend/apps/visit/adapter/inbound/api/schemas/add_closed_date_schema.py`:
```python
from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import AfterValidator, BaseModel, StringConstraints

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars


class AddClosedDateRequestSchema(BaseModel):
    date: date
    note: Annotated[
        str, StringConstraints(strip_whitespace=True, max_length=30), AfterValidator(reject_control_chars)
    ] | None = None
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_settings_schema.py`:
```python
from __future__ import annotations

from datetime import time

from pydantic import BaseModel

from visit.app.dtos.schedule_view_dto import VisitSettingsView


class VisitSettingsSchema(BaseModel):
    opens_at: time
    closes_at: time
    default_duration_minutes: int
    closed_weekdays: list[int]   # 월=0 … 일=6

    @classmethod
    def of(cls, view: VisitSettingsView) -> VisitSettingsSchema:
        return cls(opens_at=view.opens_at, closes_at=view.closes_at,
                   default_duration_minutes=view.default_duration_minutes,
                   closed_weekdays=view.closed_weekdays)
```

`backend/apps/visit/adapter/inbound/api/schemas/list_closed_dates_schema.py`:
```python
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.app.dtos.schedule_view_dto import ClosedDateView


class ClosedDateSchema(BaseModel):
    date: date
    note: str | None

    @classmethod
    def of(cls, view: ClosedDateView) -> ClosedDateSchema:
        return cls(date=view.date, note=view.note)


class ClosedDateListSchema(BaseModel):
    items: list[ClosedDateSchema]
```

`backend/apps/visit/adapter/inbound/api/schemas/text_validators.py`:
```python
"""문자열 입력의 NUL·제어 문자를 막는 검증기(customer 와 같은 규칙 — 스포크끼리 import 하지 않아 따로 둔다).

NUL 이나 제어 문자가 그대로 DB 에 닿으면 asyncpg 가 DBAPIError 를 일으켜 500 이 된다. 여기서 422 로 막는다.
메모는 개행만 예외로 허용한다.
"""
from __future__ import annotations

import unicodedata


def reject_control_chars(value: str | None, *, allow_newline: bool = False) -> str | None:
    if value is None:
        return value
    for ch in value:
        if allow_newline and ch == "\n":
            continue
        if unicodedata.category(ch) == "Cc":
            raise ValueError("NUL·제어 문자를 포함할 수 없습니다.")
    return value
```

`backend/apps/visit/adapter/inbound/api/schemas/update_visit_settings_schema.py`:
```python
from __future__ import annotations

from datetime import time
from typing import Annotated

from pydantic import BaseModel, Field, StrictInt

from visit.domain.value_objects.schedule_settings import ScheduleSettings

Weekday = Annotated[StrictInt, Field(ge=0, le=6)]


class UpdateVisitSettingsRequestSchema(BaseModel):
    """영업시간(10분 단위), 기본 소요(10분 단위 10~600), 쉬는 요일(월=0 … 일=6)."""

    opens_at: time
    closes_at: time
    default_duration_minutes: StrictInt
    closed_weekdays: Annotated[list[Weekday], Field(max_length=7)]

    def to_settings(self) -> ScheduleSettings:
        return ScheduleSettings(
            opens_at=self.opens_at, closes_at=self.closes_at,
            default_duration_minutes=self.default_duration_minutes,
            closed_weekdays=frozenset(self.closed_weekdays),
        )
```

`backend/apps/visit/adapter/inbound/api/v1/add_closed_date_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.add_closed_date_schema import AddClosedDateRequestSchema
from visit.adapter.inbound.api.schemas.list_closed_dates_schema import ClosedDateSchema
from visit.app.dtos.add_closed_date_dto import AddClosedDateCommand
from visit.app.ports.input.add_closed_date_use_case import AddClosedDateUseCase
from visit.dependencies.add_closed_date_provider import get_add_closed_date_use_case

add_closed_date_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@add_closed_date_router.post("/{shop_id}/closed-dates", response_model=ClosedDateSchema)
async def add_closed_date(
    body: AddClosedDateRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: AddClosedDateUseCase = Depends(get_add_closed_date_use_case),
) -> ClosedDateSchema:
    view = await use_case.add_closed_date(
        AddClosedDateCommand(ctx=ctx, day=body.date, note=body.note or None)
    )
    return ClosedDateSchema.of(view)
```

`backend/apps/visit/adapter/inbound/api/v1/delete_closed_date_router.py`:
```python
from datetime import date

from fastapi import APIRouter, Depends, Response

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.delete_closed_date_dto import DeleteClosedDateCommand
from visit.app.ports.input.delete_closed_date_use_case import DeleteClosedDateUseCase
from visit.dependencies.delete_closed_date_provider import get_delete_closed_date_use_case

delete_closed_date_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@delete_closed_date_router.delete("/{shop_id}/closed-dates/{day}", status_code=204)
async def delete_closed_date(
    day: date,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: DeleteClosedDateUseCase = Depends(get_delete_closed_date_use_case),
) -> Response:
    await use_case.delete_closed_date(DeleteClosedDateCommand(ctx=ctx, day=day))
    return Response(status_code=204)
```

`backend/apps/visit/adapter/inbound/api/v1/get_visit_settings_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_settings_schema import VisitSettingsSchema
from visit.app.dtos.get_visit_settings_dto import GetVisitSettingsQuery
from visit.app.ports.input.get_visit_settings_use_case import GetVisitSettingsUseCase
from visit.dependencies.get_visit_settings_provider import get_get_visit_settings_use_case

get_visit_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_settings_router.get("/{shop_id}/visit-settings", response_model=VisitSettingsSchema)
async def get_visit_settings(
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitSettingsUseCase = Depends(get_get_visit_settings_use_case),
) -> VisitSettingsSchema:
    return VisitSettingsSchema.of(await use_case.get_visit_settings(GetVisitSettingsQuery(ctx=ctx)))
```

`backend/apps/visit/adapter/inbound/api/v1/list_closed_dates_router.py`:
```python
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_closed_dates_schema import (
    ClosedDateListSchema,
    ClosedDateSchema,
)
from visit.app.dtos.list_closed_dates_dto import ListClosedDatesQuery
from visit.app.ports.input.list_closed_dates_use_case import ListClosedDatesUseCase
from visit.dependencies.list_closed_dates_provider import get_list_closed_dates_use_case

list_closed_dates_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_closed_dates_router.get("/{shop_id}/closed-dates", response_model=ClosedDateListSchema)
async def list_closed_dates(
    start: Annotated[date, Query(alias="from")],
    end: Annotated[date, Query(alias="to")],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListClosedDatesUseCase = Depends(get_list_closed_dates_use_case),
) -> ClosedDateListSchema:
    views = await use_case.list_closed_dates(ListClosedDatesQuery(ctx=ctx, start=start, end=end))
    return ClosedDateListSchema(items=[ClosedDateSchema.of(v) for v in views])
```

`backend/apps/visit/adapter/inbound/api/v1/update_visit_settings_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_settings_schema import VisitSettingsSchema
from visit.adapter.inbound.api.schemas.update_visit_settings_schema import (
    UpdateVisitSettingsRequestSchema,
)
from visit.app.dtos.update_visit_settings_dto import UpdateVisitSettingsCommand
from visit.app.ports.input.update_visit_settings_use_case import UpdateVisitSettingsUseCase
from visit.dependencies.update_visit_settings_provider import get_update_visit_settings_use_case

update_visit_settings_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_visit_settings_router.put("/{shop_id}/visit-settings", response_model=VisitSettingsSchema)
async def update_visit_settings(
    body: UpdateVisitSettingsRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateVisitSettingsUseCase = Depends(get_update_visit_settings_use_case),
) -> VisitSettingsSchema:
    view = await use_case.update_visit_settings(
        UpdateVisitSettingsCommand(ctx=ctx, settings=body.to_settings())
    )
    return VisitSettingsSchema.of(view)
```

`backend/apps/visit/adapter/outbound/pg/schedule_pg_repository.py`:
```python
from __future__ import annotations

from datetime import date

from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.orm.visit_orm import (
    ServiceMenuOrm,
    VisitClosedDateOrm,
    VisitShopSettingsOrm,
    VisitWeeklyClosureOrm,
)
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import DEFAULT_MENUS, DEFAULT_SETTINGS, ScheduleSettings


class SchedulePgRepository(ScheduleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure(self, ctx: ShopContext) -> ScheduleSettings:
        # 동시에 처음 쓰는 두 요청 중 늦은 쪽은 앞선 쪽의 커밋까지 여기서 기다렸다가 DO NOTHING 이 된다.
        created = (
            await self._session.execute(
                pg_insert(VisitShopSettingsOrm)
                .values(
                    shop_id=ctx.shop_id,
                    opens_at=DEFAULT_SETTINGS.opens_at,
                    closes_at=DEFAULT_SETTINGS.closes_at,
                    default_duration_minutes=DEFAULT_SETTINGS.default_duration_minutes,
                )
                .on_conflict_do_nothing(index_elements=[VisitShopSettingsOrm.shop_id])
                .returning(VisitShopSettingsOrm.shop_id)
            )
        ).scalar_one_or_none()
        if created is not None:
            await self._session.execute(
                insert(ServiceMenuOrm),
                [
                    dict(shop_id=ctx.shop_id, name=name, default_duration_minutes=minutes, sort_order=order)
                    for order, (name, minutes) in enumerate(DEFAULT_MENUS, start=1)
                ],
            )
        return await self._read(ctx)

    async def update(self, ctx: ShopContext, settings: ScheduleSettings) -> ScheduleSettings:
        # 설정 행 UPDATE 를 맨 먼저 한다 — 두 사장이 동시에 바꾸면 늦은 쪽이 이 행에서 기다렸다가, 앞선 쪽이
        # 커밋한 쉬는 요일을 보고 지우고 넣는다(지우고 넣기가 섞여 기본 키가 부딪히지 않는다).
        await self._session.execute(
            update(VisitShopSettingsOrm)
            .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
            .values(opens_at=settings.opens_at, closes_at=settings.closes_at,
                    default_duration_minutes=settings.default_duration_minutes)
        )
        await self._session.execute(
            delete(VisitWeeklyClosureOrm).where(VisitWeeklyClosureOrm.shop_id == ctx.shop_id)
        )
        if settings.closed_weekdays:
            await self._session.execute(
                insert(VisitWeeklyClosureOrm),
                [dict(shop_id=ctx.shop_id, weekday=d) for d in sorted(settings.closed_weekdays)],
            )
        return await self._read(ctx)

    async def list_closed_dates(self, ctx: ShopContext, start: date, end: date) -> list[ClosedDate]:
        rows = (
            await self._session.execute(
                select(VisitClosedDateOrm)
                .where(VisitClosedDateOrm.shop_id == ctx.shop_id,
                       VisitClosedDateOrm.day.between(start, end))
                .order_by(VisitClosedDateOrm.day)
            )
        ).scalars()
        return [ClosedDate(day=row.day, note=row.note) for row in rows]

    async def add_closed_date(self, ctx: ShopContext, day: date, note: str | None) -> ClosedDate:
        await self._session.execute(
            pg_insert(VisitClosedDateOrm)
            .values(shop_id=ctx.shop_id, day=day, note=note)
            .on_conflict_do_nothing(index_elements=[VisitClosedDateOrm.shop_id, VisitClosedDateOrm.day])
        )
        [found] = await self.list_closed_dates(ctx, day, day)
        return found

    async def delete_closed_date(self, ctx: ShopContext, day: date) -> None:
        await self._session.execute(
            delete(VisitClosedDateOrm).where(
                VisitClosedDateOrm.shop_id == ctx.shop_id, VisitClosedDateOrm.day == day
            )
        )

    async def _read(self, ctx: ShopContext) -> ScheduleSettings:
        row = (
            await self._session.execute(
                select(VisitShopSettingsOrm)
                .where(VisitShopSettingsOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one()
        weekdays = (
            await self._session.execute(
                select(VisitWeeklyClosureOrm.weekday).where(VisitWeeklyClosureOrm.shop_id == ctx.shop_id)
            )
        ).scalars()
        return ScheduleSettings(
            opens_at=row.opens_at, closes_at=row.closes_at,
            default_duration_minutes=row.default_duration_minutes, closed_weekdays=frozenset(weekdays),
        )
```

`backend/apps/visit/dependencies/add_closed_date_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.add_closed_date_use_case import AddClosedDateUseCase
from visit.app.use_cases.add_closed_date_interactor import AddClosedDateInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_add_closed_date_use_case(db: DbSession) -> AddClosedDateUseCase:
    return AddClosedDateInteractor(schedule=build_schedule_repository(db))
```

`backend/apps/visit/dependencies/delete_closed_date_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.delete_closed_date_use_case import DeleteClosedDateUseCase
from visit.app.use_cases.delete_closed_date_interactor import DeleteClosedDateInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_delete_closed_date_use_case(db: DbSession) -> DeleteClosedDateUseCase:
    return DeleteClosedDateInteractor(schedule=build_schedule_repository(db))
```

`backend/apps/visit/dependencies/get_visit_settings_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_visit_settings_use_case import GetVisitSettingsUseCase
from visit.app.use_cases.get_visit_settings_interactor import GetVisitSettingsInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_get_visit_settings_use_case(db: DbSession) -> GetVisitSettingsUseCase:
    return GetVisitSettingsInteractor(schedule=build_schedule_repository(db))
```

`backend/apps/visit/dependencies/list_closed_dates_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.list_closed_dates_use_case import ListClosedDatesUseCase
from visit.app.use_cases.list_closed_dates_interactor import ListClosedDatesInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_list_closed_dates_use_case(db: DbSession) -> ListClosedDatesUseCase:
    return ListClosedDatesInteractor(schedule=build_schedule_repository(db))
```

`backend/apps/visit/dependencies/update_visit_settings_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_visit_settings_use_case import UpdateVisitSettingsUseCase
from visit.app.use_cases.update_visit_settings_interactor import UpdateVisitSettingsInteractor
from visit.dependencies.visit_wiring import build_schedule_repository


def get_update_visit_settings_use_case(db: DbSession) -> UpdateVisitSettingsUseCase:
    return UpdateVisitSettingsInteractor(schedule=build_schedule_repository(db))
```

`backend/apps/visit/dependencies/visit_wiring.py`:
```python
"""visit 슬라이스 프로바이더들이 함께 쓰는 조립 함수."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository


def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
    return SchedulePgRepository(db)
```

`backend/main.py` (수정):
```diff
@@ -55,6 +55,12 @@ from tenancy.dependencies.hub_ports import get_active_user_guard, get_user_direc
 from tenancy.dependencies.list_memberships_provider import get_list_memberships_use_case
 from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_case
 from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case
+from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
+from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
+from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
+from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
+from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
+from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 
 
 @asynccontextmanager
@@ -98,11 +104,17 @@ app.include_router(update_pet_router)
 app.include_router(mark_pet_passed_away_router)
 app.include_router(unmark_pet_passed_away_router)
 app.include_router(delete_pet_router)
+# visit
+app.include_router(get_visit_settings_router)
+app.include_router(update_visit_settings_router)
+app.include_router(list_closed_dates_router)
+app.include_router(add_closed_date_router)
+app.include_router(delete_closed_date_router)
 install_error_handlers(
     app,
     {
         **AUTH_ERROR_STATUS, **TENANCY_ERROR_STATUS, **PLATFORM_ADMIN_ERROR_STATUS,
-        **CUSTOMER_ERROR_STATUS,
+        **CUSTOMER_ERROR_STATUS, **VISIT_ERROR_STATUS,
     },
 )
```

> 라우터를 `main.py`에 붙이고 오류 표를 합친다. 라우트 구조 검사(`tests/test_hub_port_binding.py`)가 새 `{shop_id}` 경로가 매장 확인을 거치는지 본다.

- [ ] **Step 5: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 6: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **502 passed**, 통합 **220 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 7: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 5 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `SchedulePgRepository.ensure`의 `if created is not None:`을 `if True:`로 바꾼다 → 두 번째 준비에서 같은 이름의 메뉴를 또 넣어 이름 유일 색인에 걸린다 — `test_두_세션이_동시에_처음_써도_메뉴는_한_번만_들어간다` 등 넷이 실패한다 — 되돌린다.
- `update_visit_settings_router.py`의 `Depends(require_permission("shop:update"))`를 `Depends(get_shop_context)`로 바꾼다(import 도 `get_shop_context`로) → `test_직원은_설정을_바꾸지_못한다`가 실패한다 — 되돌린다.

- [ ] **Step 8: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/__init__.py backend/apps/visit/adapter/inbound/api/__init__.py backend/apps/visit/adapter/inbound/api/error_map.py backend/apps/visit/adapter/inbound/api/path_params.py backend/apps/visit/adapter/inbound/api/schemas/__init__.py backend/apps/visit/adapter/inbound/api/schemas/add_closed_date_schema.py backend/apps/visit/adapter/inbound/api/schemas/get_visit_settings_schema.py backend/apps/visit/adapter/inbound/api/schemas/list_closed_dates_schema.py backend/apps/visit/adapter/inbound/api/schemas/text_validators.py backend/apps/visit/adapter/inbound/api/schemas/update_visit_settings_schema.py backend/apps/visit/adapter/inbound/api/v1/__init__.py backend/apps/visit/adapter/inbound/api/v1/add_closed_date_router.py backend/apps/visit/adapter/inbound/api/v1/delete_closed_date_router.py backend/apps/visit/adapter/inbound/api/v1/get_visit_settings_router.py backend/apps/visit/adapter/inbound/api/v1/list_closed_dates_router.py backend/apps/visit/adapter/inbound/api/v1/update_visit_settings_router.py backend/apps/visit/adapter/outbound/mappers/__init__.py backend/apps/visit/adapter/outbound/pg/__init__.py backend/apps/visit/adapter/outbound/pg/schedule_pg_repository.py backend/apps/visit/app/dtos/__init__.py backend/apps/visit/app/dtos/add_closed_date_dto.py backend/apps/visit/app/dtos/delete_closed_date_dto.py backend/apps/visit/app/dtos/get_visit_settings_dto.py backend/apps/visit/app/dtos/list_closed_dates_dto.py backend/apps/visit/app/dtos/schedule_view_dto.py backend/apps/visit/app/dtos/update_visit_settings_dto.py backend/apps/visit/app/ports/__init__.py backend/apps/visit/app/ports/input/__init__.py backend/apps/visit/app/ports/input/add_closed_date_use_case.py backend/apps/visit/app/ports/input/delete_closed_date_use_case.py backend/apps/visit/app/ports/input/get_visit_settings_use_case.py backend/apps/visit/app/ports/input/list_closed_dates_use_case.py backend/apps/visit/app/ports/input/update_visit_settings_use_case.py backend/apps/visit/app/ports/output/__init__.py backend/apps/visit/app/ports/output/schedule_repository.py backend/apps/visit/app/services/__init__.py backend/apps/visit/app/use_cases/__init__.py backend/apps/visit/app/use_cases/add_closed_date_interactor.py backend/apps/visit/app/use_cases/delete_closed_date_interactor.py backend/apps/visit/app/use_cases/get_visit_settings_interactor.py backend/apps/visit/app/use_cases/list_closed_dates_interactor.py backend/apps/visit/app/use_cases/update_visit_settings_interactor.py backend/apps/visit/dependencies/__init__.py backend/apps/visit/dependencies/add_closed_date_provider.py backend/apps/visit/dependencies/delete_closed_date_provider.py backend/apps/visit/dependencies/get_visit_settings_provider.py backend/apps/visit/dependencies/list_closed_dates_provider.py backend/apps/visit/dependencies/update_visit_settings_provider.py backend/apps/visit/dependencies/visit_wiring.py backend/apps/visit/domain/services/visit_schedule.py backend/apps/visit/domain/value_objects/closed_date.py backend/apps/visit/tests/adapter/test_add_closed_date_router.py backend/apps/visit/tests/adapter/test_delete_closed_date_router.py backend/apps/visit/tests/adapter/test_get_visit_settings_router.py backend/apps/visit/tests/adapter/test_list_closed_dates_router.py backend/apps/visit/tests/adapter/test_schedule_pg_repository.py backend/apps/visit/tests/adapter/test_update_visit_settings_router.py backend/apps/visit/tests/app/__init__.py backend/apps/visit/tests/app/use_cases/__init__.py backend/apps/visit/tests/app/use_cases/test_add_closed_date_interactor.py backend/apps/visit/tests/app/use_cases/test_delete_closed_date_interactor.py backend/apps/visit/tests/app/use_cases/test_get_visit_settings_interactor.py backend/apps/visit/tests/app/use_cases/test_list_closed_dates_interactor.py backend/apps/visit/tests/app/use_cases/test_update_visit_settings_interactor.py backend/apps/visit/tests/helpers/api.py backend/apps/visit/tests/helpers/fakes.py backend/main.py
git commit -m "feat(visit): 매장 일정 설정과 임시 휴무 — 설정 조회·수정, 휴무 조회·추가·삭제"
```

---

### Task 6: 메뉴표 — 조회·추가·수정·보관, 처음 쓰는 매장의 기본 메뉴

메뉴는 지우지 않고 보관한다(지난 방문이 가리킨다). 이름은 보관하지 않은 메뉴끼리만 겹치지 않는다 — 부분 유일 색인을 세이브포인트 안에서 걸고 409 `MENU_NAME_TAKEN`으로 바꾼다. 조회는 설정을 준비(`ensure`)한 뒤 읽으므로, 처음 여는 매장도 기본 메뉴 다섯이 바로 보인다. 새 메뉴는 맨 뒤 순서다. 다른 매장의 메뉴 ID 는 404 다(V1).

**Files:**
- Create: `backend/apps/visit/app/dtos/archive_menu_dto.py`
- Create: `backend/apps/visit/app/dtos/create_menu_dto.py`
- Create: `backend/apps/visit/app/dtos/list_menus_dto.py`
- Create: `backend/apps/visit/app/dtos/menu_view_dto.py`
- Create: `backend/apps/visit/app/dtos/update_menu_dto.py`
- Create: `backend/apps/visit/app/ports/input/archive_menu_use_case.py`
- Create: `backend/apps/visit/app/ports/input/create_menu_use_case.py`
- Create: `backend/apps/visit/app/ports/input/list_menus_use_case.py`
- Create: `backend/apps/visit/app/ports/input/update_menu_use_case.py`
- Create: `backend/apps/visit/app/ports/output/menu_repository.py`
- Create: `backend/apps/visit/app/use_cases/archive_menu_interactor.py`
- Create: `backend/apps/visit/app/use_cases/create_menu_interactor.py`
- Create: `backend/apps/visit/app/use_cases/list_menus_interactor.py`
- Create: `backend/apps/visit/app/use_cases/update_menu_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/create_menu_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/list_menus_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/update_menu_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/archive_menu_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/create_menu_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/list_menus_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/update_menu_router.py`
- Create: `backend/apps/visit/adapter/outbound/mappers/visit_mapper.py`
- Create: `backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`
- Create: `backend/apps/visit/dependencies/archive_menu_provider.py`
- Create: `backend/apps/visit/dependencies/create_menu_provider.py`
- Create: `backend/apps/visit/dependencies/list_menus_provider.py`
- Create: `backend/apps/visit/dependencies/update_menu_provider.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_archive_menu_router.py`
- Test: `backend/apps/visit/tests/adapter/test_create_menu_router.py`
- Test: `backend/apps/visit/tests/adapter/test_list_menus_router.py`
- Test: `backend/apps/visit/tests/adapter/test_menu_pg_repository.py`
- Test: `backend/apps/visit/tests/adapter/test_update_menu_router.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_archive_menu_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_create_menu_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_list_menus_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_update_menu_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: Task 5 의 `ScheduleRepository.ensure`, 공용 부품
- Produces:
  - `visit.app.ports.output.menu_repository.MenuRepository`: `list(ctx, include_archived)`, `create(ctx, name, default_duration_minutes)`, `update(ctx, menu_id, name, default_duration_minutes, sort_order)`, `archive(ctx, menu_id)`
  - `visit.app.dtos.menu_view_dto.MenuView`, `visit.adapter.outbound.mappers.visit_mapper.to_menu`
  - `visit.adapter.inbound.api.schemas.list_menus_schema.MenuSchema`, `create_menu_schema.MenuName`
  - `build_menu_repository(db)`, 테스트 스텁 `FakeMenus`(`seed(...)`, `list_active_by_ids` 포함 — Task 7 이 쓴다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_archive_menu_router.py`:
```python
from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.archive_menu_provider import get_archive_menu_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

ARCHIVED = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=True)


async def test_사장은_메뉴를_보관한다():
    stub = Recorder(ARCHIVED)
    async with client(build_app(archive_menu_router, get_archive_menu_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/menus/1/archive")
    assert response.json()["archived"] is True
    assert stub.calls[0].menu_id == 1


async def test_직원은_메뉴를_보관하지_못한다():
    async with client(build_app(archive_menu_router, get_archive_menu_use_case, Recorder(ARCHIVED), STAFF)) as c:
        assert error_of(await c.post("/v1/shops/3/menus/1/archive")) == (403, "PERMISSION_DENIED")
```

`backend/apps/visit/tests/adapter/test_create_menu_router.py`:
```python
from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.create_menu_provider import get_create_menu_use_case
from visit.domain.errors import MenuNameTakenError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

NAIL = MenuView(menu_id=6, name="발톱", default_duration_minutes=None, sort_order=6, archived=False)


async def test_사장은_메뉴를_만든다_201():
    stub = Recorder(NAIL)
    async with client(build_app(create_menu_router, get_create_menu_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/menus", json={"name": " 발톱 "})
    assert (response.status_code, response.json()["menu_id"]) == (201, 6)
    assert (stub.calls[0].name, stub.calls[0].default_duration_minutes) == ("발톱", None)


async def test_직원은_메뉴를_만들지_못한다():
    async with client(build_app(create_menu_router, get_create_menu_use_case, Recorder(NAIL), STAFF)) as c:
        response = await c.post("/v1/shops/3/menus", json={"name": "발톱"})
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_이름이_비었거나_길거나_소요가_문자열이면_422_다():
    async with client(build_app(create_menu_router, get_create_menu_use_case, Recorder(NAIL))) as c:
        for bad in ({"name": " "}, {"name": "가" * 31}, {"name": "발톱", "default_duration_minutes": "60"},
                    {"name": "발\x00톱"}):
            assert error_of(await c.post("/v1/shops/3/menus", json=bad)) == (422, "VALIDATION_ERROR")


async def test_이름이_겹치면_409_MENU_NAME_TAKEN_이다():
    stub = Recorder(error=MenuNameTakenError("겹침"))
    async with client(build_app(create_menu_router, get_create_menu_use_case, stub)) as c:
        response = await c.post("/v1/shops/3/menus", json={"name": "목욕"})
    assert error_of(response) == (409, "MENU_NAME_TAKEN")
```

`backend/apps/visit/tests/adapter/test_list_menus_router.py`:
```python
from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.list_menus_provider import get_list_menus_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client

BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False)


async def test_직원도_메뉴표를_본다():
    stub = Recorder([BATH])
    async with client(build_app(list_menus_router, get_list_menus_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/menus")
        await c.get("/v1/shops/3/menus?include_archived=true")
    assert response.json() == {"items": [{"menu_id": 1, "name": "목욕", "default_duration_minutes": 60,
                                          "sort_order": 1, "archived": False}]}
    assert [q.include_archived for q in stub.calls] == [False, True]
```

`backend/apps/visit/tests/adapter/test_menu_pg_repository.py`:
```python
import pytest

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.domain.errors import MenuNameTakenError, MenuNotFoundError
from visit.tests.helpers.builders import ctx

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


async def _prepared(session, *shops):
    for shop in shops:
        await SchedulePgRepository(session).ensure(shop)
    return MenuPgRepository(session)


async def test_새_메뉴는_맨_뒤_순서다(db_session):
    menus = await _prepared(db_session, A)
    nail = await menus.create(A, "발톱", None)
    assert (nail.sort_order, nail.default_duration_minutes, nail.archived) == (6, None, False)
    assert [m.name for m in await menus.list(A, include_archived=False)][-1] == "발톱"


async def test_보관하지_않은_메뉴끼리_이름이_겹치면_MENU_NAME_TAKEN_이고_세션은_계속_쓴다(db_session):
    menus = await _prepared(db_session, A)
    with pytest.raises(MenuNameTakenError):
        await menus.create(A, "목욕", 60)
    [bath] = [m for m in await menus.list(A, include_archived=False) if m.name == "목욕"]
    await menus.archive(A, bath.id)
    again = await menus.create(A, "목욕", 70)   # 보관한 이름은 다시 쓸 수 있다
    with pytest.raises(MenuNameTakenError):
        await menus.update(A, again.id, "위생", 60, 1)


async def test_보관은_처음_시각을_지키고_목록에서_빠진다(db_session):
    menus = await _prepared(db_session, A)
    [bath, *_] = await menus.list(A, include_archived=False)
    first = await menus.archive(A, bath.id)
    second = await menus.archive(A, bath.id)
    assert first.archived_at == second.archived_at
    assert bath.id not in [m.id for m in await menus.list(A, include_archived=False)]
    assert bath.id in [m.id for m in await menus.list(A, include_archived=True)]


async def test_다른_매장의_메뉴는_고치거나_보관하지_못한다(db_session):
    """V1 — 다른 매장 컨텍스트로는 404 이고 값도 그대로다."""
    menus = await _prepared(db_session, A, B)
    [theirs, *_] = await menus.list(B, include_archived=False)
    with pytest.raises(MenuNotFoundError):
        await menus.update(A, theirs.id, "침입", 10, 1)
    with pytest.raises(MenuNotFoundError):
        await menus.archive(A, theirs.id)
    [still, *_] = await menus.list(B, include_archived=False)
    assert (still.name, still.archived) == (theirs.name, False)
```

`backend/apps/visit/tests/adapter/test_update_menu_router.py`:
```python
from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
from visit.app.dtos.menu_view_dto import MenuView
from visit.dependencies.update_menu_provider import get_update_menu_use_case
from visit.domain.errors import MenuNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

BATH = MenuView(menu_id=1, name="목욕", default_duration_minutes=60, sort_order=1, archived=False)
BODY = {"name": "목욕", "default_duration_minutes": 60, "sort_order": 2}


async def test_사장은_메뉴를_고친다():
    stub = Recorder(BATH)
    async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
        assert (await c.put("/v1/shops/3/menus/1", json=BODY)).status_code == 200
    assert (stub.calls[0].menu_id, stub.calls[0].sort_order) == (1, 2)


async def test_직원은_메뉴를_고치지_못한다():
    async with client(build_app(update_menu_router, get_update_menu_use_case, Recorder(BATH), STAFF)) as c:
        assert error_of(await c.put("/v1/shops/3/menus/1", json=BODY)) == (403, "PERMISSION_DENIED")


async def test_없는_메뉴는_404_범위를_넘는_ID_는_422_다():
    stub = Recorder(error=MenuNotFoundError("없음"))
    async with client(build_app(update_menu_router, get_update_menu_use_case, stub)) as c:
        assert error_of(await c.put("/v1/shops/3/menus/9", json=BODY)) == (404, "MENU_NOT_FOUND")
        assert error_of(await c.put("/v1/shops/3/menus/9223372036854775808", json=BODY)) == (
            422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/app/use_cases/test_archive_menu_interactor.py`:
```python
import pytest

from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.use_cases.archive_menu_interactor import ArchiveMenuInteractor
from visit.domain.errors import MenuNotFoundError
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus


async def test_보관한다():
    menus = FakeMenus()
    bath = menus.seed("목욕")
    view = await ArchiveMenuInteractor(menus).archive_menu(ArchiveMenuCommand(ctx=ctx(), menu_id=bath.id))
    assert view.archived
    assert menus.journal == [("archive_menu", bath.id)]


async def test_다른_매장의_메뉴는_MENU_NOT_FOUND_다():
    menus = FakeMenus()
    theirs = menus.seed("목욕", shop_id=2)
    with pytest.raises(MenuNotFoundError):
        await ArchiveMenuInteractor(menus).archive_menu(ArchiveMenuCommand(ctx=ctx(shop_id=1), menu_id=theirs.id))
```

`backend/apps/visit/tests/app/use_cases/test_create_menu_interactor.py`:
```python
import pytest

from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.use_cases.create_menu_interactor import CreateMenuInteractor
from visit.domain.errors import MenuNameTakenError, VisitInputError
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, Journal


async def test_설정을_준비한_뒤_만든다():
    journal = Journal()
    view = await CreateMenuInteractor(FakeSchedule(journal), FakeMenus(journal)).create_menu(
        CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=None))
    assert (view.name, view.default_duration_minutes, view.archived) == ("발톱", None, False)
    assert journal == [("ensure", 1), ("create_menu", "발톱")]


async def test_소요_규칙에_어긋나면_쓰지_않는다():
    journal = Journal()
    with pytest.raises(VisitInputError):
        await CreateMenuInteractor(FakeSchedule(journal), FakeMenus(journal)).create_menu(
            CreateMenuCommand(ctx=ctx(), name="발톱", default_duration_minutes=15))
    assert journal == []


async def test_보관하지_않은_메뉴와_이름이_겹치면_MENU_NAME_TAKEN_이다():
    menus = FakeMenus()
    menus.seed("목욕")
    with pytest.raises(MenuNameTakenError):
        await CreateMenuInteractor(FakeSchedule(), menus).create_menu(
            CreateMenuCommand(ctx=ctx(), name="목욕", default_duration_minutes=60))
```

`backend/apps/visit/tests/app/use_cases/test_list_menus_interactor.py`:
```python
from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.use_cases.list_menus_interactor import ListMenusInteractor
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, Journal


async def test_설정을_준비한_뒤_보관하지_않은_메뉴를_순서대로():
    journal = Journal()
    menus = FakeMenus(journal)
    menus.seed("목욕")
    menus.seed("위생", archived=True)
    menus.seed("전체 미용", minutes=None)
    menus.seed("남의 메뉴", shop_id=2)
    views = await ListMenusInteractor(FakeSchedule(journal), menus).list_menus(
        ListMenusQuery(ctx=ctx(), include_archived=False))
    assert [(v.name, v.default_duration_minutes, v.archived) for v in views] == [
        ("목욕", 60, False), ("전체 미용", None, False)]
    assert journal == [("ensure", 1)]


async def test_보관한_메뉴도_달라면_준다():
    menus = FakeMenus()
    menus.seed("목욕")
    menus.seed("위생", archived=True)
    views = await ListMenusInteractor(FakeSchedule(), menus).list_menus(
        ListMenusQuery(ctx=ctx(), include_archived=True))
    assert [(v.name, v.archived) for v in views] == [("목욕", False), ("위생", True)]
```

`backend/apps/visit/tests/app/use_cases/test_update_menu_interactor.py`:
```python
import pytest

from visit.app.dtos.update_menu_dto import UpdateMenuCommand
from visit.app.use_cases.update_menu_interactor import UpdateMenuInteractor
from visit.domain.errors import MenuNotFoundError, VisitInputError
from visit.tests.helpers.builders import ctx
from visit.tests.helpers.fakes import FakeMenus


async def test_이름_소요_순서를_바꾼다():
    menus = FakeMenus()
    bath = menus.seed("목욕")
    view = await UpdateMenuInteractor(menus).update_menu(
        UpdateMenuCommand(ctx=ctx(), menu_id=bath.id, name="목욕(대형견)", default_duration_minutes=90,
                          sort_order=9))
    assert (view.name, view.default_duration_minutes, view.sort_order) == ("목욕(대형견)", 90, 9)


async def test_소요_규칙에_어긋나면_쓰지_않는다():
    menus = FakeMenus()
    bath = menus.seed("목욕")
    with pytest.raises(VisitInputError):
        await UpdateMenuInteractor(menus).update_menu(
            UpdateMenuCommand(ctx=ctx(), menu_id=bath.id, name="목욕", default_duration_minutes=700,
                              sort_order=1))
    assert menus.journal == []


async def test_다른_매장의_메뉴는_MENU_NOT_FOUND_다():
    menus = FakeMenus()
    theirs = menus.seed("목욕", shop_id=2)
    with pytest.raises(MenuNotFoundError):
        await UpdateMenuInteractor(menus).update_menu(
            UpdateMenuCommand(ctx=ctx(shop_id=1), menu_id=theirs.id, name="침입", default_duration_minutes=None,
                              sort_order=1))
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -1,8 +1,13 @@
 """visit 인터랙터 테스트용 메모리 스텁. 호출 순서를 journal 한 목록에 남겨 '잠근 뒤 쓴다'를 확인할 수 있다."""
 from __future__ import annotations
 
+from dataclasses import replace
+
+from visit.domain.entities.menu import Menu
+from visit.domain.errors import MenuNameTakenError, MenuNotFoundError
 from visit.domain.value_objects.closed_date import ClosedDate
 from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
+from visit.tests.helpers.builders import kst
 
 
 class Journal(list):
@@ -37,3 +42,56 @@ class FakeSchedule:
     async def delete_closed_date(self, ctx, day):
         self.journal.append(("delete_closed_date", day))
         self.closed.pop((ctx.shop_id, day), None)
+
+
+class FakeMenus:
+    def __init__(self, journal: Journal | None = None) -> None:
+        self.journal = journal if journal is not None else Journal()
+        self.rows: dict[int, Menu] = {}
+        self._next = 1
+
+    def seed(self, name="목욕", minutes=60, shop_id=1, archived=False) -> Menu:
+        menu = Menu(id=self._next, shop_id=shop_id, name=name, default_duration_minutes=minutes,
+                    sort_order=self._next, archived_at=kst(9, 1) if archived else None)
+        self.rows[menu.id] = menu
+        self._next += 1
+        return menu
+
+    def _find(self, ctx, menu_id) -> Menu:
+        menu = self.rows.get(menu_id)
+        if menu is None or menu.shop_id != ctx.shop_id:
+            raise MenuNotFoundError("메뉴를 찾을 수 없습니다.")
+        return menu
+
+    def _check_name(self, ctx, name, menu_id=None):
+        if any(m.name == name and not m.archived and m.shop_id == ctx.shop_id and m.id != menu_id
+               for m in self.rows.values()):
+            raise MenuNameTakenError("같은 이름의 메뉴가 있습니다.")
+
+    async def list(self, ctx, include_archived):
+        return sorted((m for m in self.rows.values() if m.shop_id == ctx.shop_id
+                       and (include_archived or not m.archived)), key=lambda m: m.sort_order)
+
+    async def list_active_by_ids(self, ctx, menu_ids):
+        return [m for m in self.rows.values() if m.id in menu_ids and m.shop_id == ctx.shop_id
+                and not m.archived]
+
+    async def create(self, ctx, name, default_duration_minutes):
+        self._check_name(ctx, name)
+        menu = self.seed(name=name, minutes=default_duration_minutes, shop_id=ctx.shop_id)
+        self.journal.append(("create_menu", name))
+        return menu
+
+    async def update(self, ctx, menu_id, name, default_duration_minutes, sort_order):
+        current = self._find(ctx, menu_id)
+        self._check_name(ctx, name, menu_id)
+        self.rows[menu_id] = replace(current, name=name, default_duration_minutes=default_duration_minutes,
+                                     sort_order=sort_order)
+        self.journal.append(("update_menu", menu_id))
+        return self.rows[menu_id]
+
+    async def archive(self, ctx, menu_id):
+        current = self._find(ctx, menu_id)
+        self.rows[menu_id] = replace(current, archived_at=current.archived_at or kst(9, 23))
+        self.journal.append(("archive_menu", menu_id))
+        return self.rows[menu_id]
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해 메뉴 테스트가 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/dtos/archive_menu_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ArchiveMenuCommand:
    ctx: ShopContext
    menu_id: int
```

`backend/apps/visit/app/dtos/create_menu_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class CreateMenuCommand:
    ctx: ShopContext
    name: str
    default_duration_minutes: int | None
```

`backend/apps/visit/app/dtos/list_menus_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListMenusQuery:
    ctx: ShopContext
    include_archived: bool
```

`backend/apps/visit/app/dtos/menu_view_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from visit.domain.entities.menu import Menu


@dataclass(frozen=True)
class MenuView:
    menu_id: int
    name: str
    default_duration_minutes: int | None
    sort_order: int
    archived: bool

    @classmethod
    def of(cls, menu: Menu) -> MenuView:
        return cls(menu_id=menu.id, name=menu.name, default_duration_minutes=menu.default_duration_minutes,
                   sort_order=menu.sort_order, archived=menu.archived)
```

`backend/apps/visit/app/dtos/update_menu_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class UpdateMenuCommand:
    ctx: ShopContext
    menu_id: int
    name: str
    default_duration_minutes: int | None
    sort_order: int
```

`backend/apps/visit/app/ports/input/archive_menu_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.dtos.menu_view_dto import MenuView


class ArchiveMenuUseCase(ABC):
    @abstractmethod
    async def archive_menu(self, command: ArchiveMenuCommand) -> MenuView: ...
```

`backend/apps/visit/app/ports/input/create_menu_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.dtos.menu_view_dto import MenuView


class CreateMenuUseCase(ABC):
    @abstractmethod
    async def create_menu(self, command: CreateMenuCommand) -> MenuView: ...
```

`backend/apps/visit/app/ports/input/list_menus_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.dtos.menu_view_dto import MenuView


class ListMenusUseCase(ABC):
    @abstractmethod
    async def list_menus(self, query: ListMenusQuery) -> list[MenuView]: ...
```

`backend/apps/visit/app/ports/input/update_menu_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.menu_view_dto import MenuView
from visit.app.dtos.update_menu_dto import UpdateMenuCommand


class UpdateMenuUseCase(ABC):
    @abstractmethod
    async def update_menu(self, command: UpdateMenuCommand) -> MenuView: ...
```

`backend/apps/visit/app/ports/output/menu_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.menu import Menu


class MenuRepository(ABC):
    """매장 메뉴표. 메뉴는 지우지 않고 보관한다. 새 메뉴를 만들기 전에 설정 행이 있어야 한다(외래 키)."""

    @abstractmethod
    async def list(self, ctx: ShopContext, include_archived: bool) -> list[Menu]:
        """순서(sort_order) 대로."""

    @abstractmethod
    async def create(self, ctx: ShopContext, name: str, default_duration_minutes: int | None) -> Menu:
        """맨 뒤 순서로 넣는다. 보관하지 않은 메뉴와 이름이 겹치면 MenuNameTakenError."""

    @abstractmethod
    async def update(
        self, ctx: ShopContext, menu_id: int, name: str, default_duration_minutes: int | None,
        sort_order: int,
    ) -> Menu:
        """없거나 다른 매장이면 MenuNotFoundError. 이름이 겹치면 MenuNameTakenError."""

    @abstractmethod
    async def archive(self, ctx: ShopContext, menu_id: int) -> Menu:
        """이미 보관했으면 처음 시각을 지킨다. 없거나 다른 매장이면 MenuNotFoundError."""
```

`backend/apps/visit/app/use_cases/archive_menu_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.dtos.menu_view_dto import MenuView
from visit.app.ports.input.archive_menu_use_case import ArchiveMenuUseCase
from visit.app.ports.output.menu_repository import MenuRepository


class ArchiveMenuInteractor(ArchiveMenuUseCase):
    """메뉴는 지우지 않고 보관한다 — 지난 방문이 가리키고 있다. 보관한 메뉴는 새 예약에 고를 수 없다."""

    def __init__(self, menus: MenuRepository) -> None:
        self._menus = menus

    async def archive_menu(self, command: ArchiveMenuCommand) -> MenuView:
        return MenuView.of(await self._menus.archive(command.ctx, command.menu_id))
```

`backend/apps/visit/app/use_cases/create_menu_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.dtos.menu_view_dto import MenuView
from visit.app.ports.input.create_menu_use_case import CreateMenuUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.domain.services.visit_schedule import check_duration


class CreateMenuInteractor(CreateMenuUseCase):
    def __init__(self, schedule: ScheduleRepository, menus: MenuRepository) -> None:
        self._schedule = schedule
        self._menus = menus

    async def create_menu(self, command: CreateMenuCommand) -> MenuView:
        if command.default_duration_minutes is not None:
            check_duration(command.default_duration_minutes)
        await self._schedule.ensure(command.ctx)   # 메뉴는 설정 행을 가리킨다(외래 키)
        return MenuView.of(
            await self._menus.create(command.ctx, command.name, command.default_duration_minutes)
        )
```

`backend/apps/visit/app/use_cases/list_menus_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.dtos.menu_view_dto import MenuView
from visit.app.ports.input.list_menus_use_case import ListMenusUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository


class ListMenusInteractor(ListMenusUseCase):
    """처음 여는 매장이면 기본 메뉴가 이때 생긴다 — 사장이 메뉴표를 만들지 않아도 바로 쓴다."""

    def __init__(self, schedule: ScheduleRepository, menus: MenuRepository) -> None:
        self._schedule = schedule
        self._menus = menus

    async def list_menus(self, query: ListMenusQuery) -> list[MenuView]:
        await self._schedule.ensure(query.ctx)
        return [MenuView.of(m) for m in await self._menus.list(query.ctx, query.include_archived)]
```

`backend/apps/visit/app/use_cases/update_menu_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.menu_view_dto import MenuView
from visit.app.dtos.update_menu_dto import UpdateMenuCommand
from visit.app.ports.input.update_menu_use_case import UpdateMenuUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.services.visit_schedule import check_duration


class UpdateMenuInteractor(UpdateMenuUseCase):
    """이름·기본 소요·순서를 바꾼다. 이미 잡힌 예약의 소요는 그대로다(방문이 자기 소요를 가진다)."""

    def __init__(self, menus: MenuRepository) -> None:
        self._menus = menus

    async def update_menu(self, command: UpdateMenuCommand) -> MenuView:
        if command.default_duration_minutes is not None:
            check_duration(command.default_duration_minutes)
        menu = await self._menus.update(
            command.ctx, command.menu_id, command.name, command.default_duration_minutes,
            command.sort_order,
        )
        return MenuView.of(menu)
```

`backend/apps/visit/adapter/inbound/api/schemas/create_menu_schema.py`:
```python
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, StrictInt, StringConstraints

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars

MenuName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30),
    AfterValidator(reject_control_chars),
]


class CreateMenuRequestSchema(BaseModel):
    """기본 소요를 비우면 매장 기본 소요를 쓴다."""

    name: MenuName
    default_duration_minutes: StrictInt | None = None
```

`backend/apps/visit/adapter/inbound/api/schemas/list_menus_schema.py`:
```python
from __future__ import annotations

from pydantic import BaseModel

from visit.app.dtos.menu_view_dto import MenuView


class MenuSchema(BaseModel):
    menu_id: int
    name: str
    default_duration_minutes: int | None   # None 이면 매장 기본 소요
    sort_order: int
    archived: bool

    @classmethod
    def of(cls, view: MenuView) -> MenuSchema:
        return cls(menu_id=view.menu_id, name=view.name,
                   default_duration_minutes=view.default_duration_minutes, sort_order=view.sort_order,
                   archived=view.archived)


class MenuListSchema(BaseModel):
    items: list[MenuSchema]
```

`backend/apps/visit/adapter/inbound/api/schemas/update_menu_schema.py`:
```python
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, StrictInt

from visit.adapter.inbound.api.schemas.create_menu_schema import MenuName


class UpdateMenuRequestSchema(BaseModel):
    name: MenuName
    default_duration_minutes: StrictInt | None
    sort_order: Annotated[StrictInt, Field(ge=0, le=32_767)]
```

`backend/apps/visit/adapter/inbound/api/v1/archive_menu_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import MenuId
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuSchema
from visit.app.dtos.archive_menu_dto import ArchiveMenuCommand
from visit.app.ports.input.archive_menu_use_case import ArchiveMenuUseCase
from visit.dependencies.archive_menu_provider import get_archive_menu_use_case

archive_menu_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@archive_menu_router.post("/{shop_id}/menus/{menu_id}/archive", response_model=MenuSchema)
async def archive_menu(
    menu_id: MenuId,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: ArchiveMenuUseCase = Depends(get_archive_menu_use_case),
) -> MenuSchema:
    return MenuSchema.of(await use_case.archive_menu(ArchiveMenuCommand(ctx=ctx, menu_id=menu_id)))
```

`backend/apps/visit/adapter/inbound/api/v1/create_menu_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.create_menu_schema import CreateMenuRequestSchema
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuSchema
from visit.app.dtos.create_menu_dto import CreateMenuCommand
from visit.app.ports.input.create_menu_use_case import CreateMenuUseCase
from visit.dependencies.create_menu_provider import get_create_menu_use_case

create_menu_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@create_menu_router.post("/{shop_id}/menus", response_model=MenuSchema, status_code=201)
async def create_menu(
    body: CreateMenuRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: CreateMenuUseCase = Depends(get_create_menu_use_case),
) -> MenuSchema:
    view = await use_case.create_menu(
        CreateMenuCommand(ctx=ctx, name=body.name, default_duration_minutes=body.default_duration_minutes)
    )
    return MenuSchema.of(view)
```

`backend/apps/visit/adapter/inbound/api/v1/list_menus_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuListSchema, MenuSchema
from visit.app.dtos.list_menus_dto import ListMenusQuery
from visit.app.ports.input.list_menus_use_case import ListMenusUseCase
from visit.dependencies.list_menus_provider import get_list_menus_use_case

list_menus_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_menus_router.get("/{shop_id}/menus", response_model=MenuListSchema)
async def list_menus(
    include_archived: bool = False,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListMenusUseCase = Depends(get_list_menus_use_case),
) -> MenuListSchema:
    views = await use_case.list_menus(ListMenusQuery(ctx=ctx, include_archived=include_archived))
    return MenuListSchema(items=[MenuSchema.of(v) for v in views])
```

`backend/apps/visit/adapter/inbound/api/v1/update_menu_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import MenuId
from visit.adapter.inbound.api.schemas.list_menus_schema import MenuSchema
from visit.adapter.inbound.api.schemas.update_menu_schema import UpdateMenuRequestSchema
from visit.app.dtos.update_menu_dto import UpdateMenuCommand
from visit.app.ports.input.update_menu_use_case import UpdateMenuUseCase
from visit.dependencies.update_menu_provider import get_update_menu_use_case

update_menu_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_menu_router.put("/{shop_id}/menus/{menu_id}", response_model=MenuSchema)
async def update_menu(
    menu_id: MenuId,
    body: UpdateMenuRequestSchema,
    ctx: ShopContext = Depends(require_permission("shop:update")),
    use_case: UpdateMenuUseCase = Depends(get_update_menu_use_case),
) -> MenuSchema:
    view = await use_case.update_menu(
        UpdateMenuCommand(ctx=ctx, menu_id=menu_id, name=body.name,
                          default_duration_minutes=body.default_duration_minutes, sort_order=body.sort_order)
    )
    return MenuSchema.of(view)
```

`backend/apps/visit/adapter/outbound/mappers/visit_mapper.py`:
```python
from __future__ import annotations

from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm
from visit.domain.entities.menu import Menu


def to_menu(orm: ServiceMenuOrm) -> Menu:
    return Menu(
        id=orm.id, shop_id=orm.shop_id, name=orm.name,
        default_duration_minutes=orm.default_duration_minutes, sort_order=orm.sort_order,
        archived_at=orm.archived_at,
    )
```

`backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`:
```python
from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_menu
from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.menu import Menu
from visit.domain.errors import MenuNameTakenError, MenuNotFoundError

_NAME_UNIQUE = "uq_service_menus_shop_name_active"


class MenuPgRepository(MenuRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self, ctx: ShopContext, include_archived: bool) -> list[Menu]:
        stmt = select(ServiceMenuOrm).where(ServiceMenuOrm.shop_id == ctx.shop_id)
        if not include_archived:
            stmt = stmt.where(ServiceMenuOrm.archived_at.is_(None))
        rows = (
            await self._session.execute(
                stmt.order_by(ServiceMenuOrm.sort_order, ServiceMenuOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars()
        return [to_menu(row) for row in rows]

    async def create(self, ctx: ShopContext, name: str, default_duration_minutes: int | None) -> Menu:
        next_order = (
            select(func.coalesce(func.max(ServiceMenuOrm.sort_order), 0) + 1)
            .where(ServiceMenuOrm.shop_id == ctx.shop_id)
            .scalar_subquery()
        )
        async with self._name_guard():
            menu_id = (
                await self._session.execute(
                    insert(ServiceMenuOrm)
                    .values(shop_id=ctx.shop_id, name=name,
                            default_duration_minutes=default_duration_minutes, sort_order=next_order)
                    .returning(ServiceMenuOrm.id)
                )
            ).scalar_one()
        return await self._get(ctx, menu_id)

    async def update(
        self, ctx: ShopContext, menu_id: int, name: str, default_duration_minutes: int | None,
        sort_order: int,
    ) -> Menu:
        async with self._name_guard():
            await self._session.execute(
                update(ServiceMenuOrm)
                .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
                .values(name=name, default_duration_minutes=default_duration_minutes, sort_order=sort_order)
            )
        return await self._get(ctx, menu_id)

    async def archive(self, ctx: ShopContext, menu_id: int) -> Menu:
        await self._session.execute(
            update(ServiceMenuOrm)
            .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
            .values(archived_at=func.coalesce(ServiceMenuOrm.archived_at, func.now()))
        )
        return await self._get(ctx, menu_id)

    async def _get(self, ctx: ShopContext, menu_id: int) -> Menu:
        row = (
            await self._session.execute(
                select(ServiceMenuOrm)
                .where(ServiceMenuOrm.id == menu_id, ServiceMenuOrm.shop_id == ctx.shop_id)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise MenuNotFoundError("메뉴를 찾을 수 없습니다.")
        return to_menu(row)

    @asynccontextmanager
    async def _name_guard(self):
        """이름 유일 색인 위반을 MENU_NAME_TAKEN 으로 바꾼다. 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""
        try:
            async with self._session.begin_nested():
                yield
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) == _NAME_UNIQUE:
                raise MenuNameTakenError("같은 이름의 메뉴가 있습니다.") from exc
            raise
```

`backend/apps/visit/dependencies/archive_menu_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.archive_menu_use_case import ArchiveMenuUseCase
from visit.app.use_cases.archive_menu_interactor import ArchiveMenuInteractor
from visit.dependencies.visit_wiring import build_menu_repository


def get_archive_menu_use_case(db: DbSession) -> ArchiveMenuUseCase:
    return ArchiveMenuInteractor(menus=build_menu_repository(db))
```

`backend/apps/visit/dependencies/create_menu_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.create_menu_use_case import CreateMenuUseCase
from visit.app.use_cases.create_menu_interactor import CreateMenuInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository


def get_create_menu_use_case(db: DbSession) -> CreateMenuUseCase:
    return CreateMenuInteractor(schedule=build_schedule_repository(db), menus=build_menu_repository(db))
```

`backend/apps/visit/dependencies/list_menus_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.list_menus_use_case import ListMenusUseCase
from visit.app.use_cases.list_menus_interactor import ListMenusInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_schedule_repository


def get_list_menus_use_case(db: DbSession) -> ListMenusUseCase:
    return ListMenusInteractor(schedule=build_schedule_repository(db), menus=build_menu_repository(db))
```

`backend/apps/visit/dependencies/update_menu_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.update_menu_use_case import UpdateMenuUseCase
from visit.app.use_cases.update_menu_interactor import UpdateMenuInteractor
from visit.dependencies.visit_wiring import build_menu_repository


def get_update_menu_use_case(db: DbSession) -> UpdateMenuUseCase:
    return UpdateMenuInteractor(menus=build_menu_repository(db))
```

`backend/apps/visit/dependencies/visit_wiring.py` (수정):
```diff
@@ -3,9 +3,15 @@ from __future__ import annotations
 
 from sqlalchemy.ext.asyncio import AsyncSession
 
+from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
+from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 
 
 def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
     return SchedulePgRepository(db)
+
+
+def build_menu_repository(db: AsyncSession) -> MenuRepository:
+    return MenuPgRepository(db)
```

`backend/main.py` (수정):
```diff
@@ -57,9 +57,13 @@ from tenancy.dependencies.provision_shop_provider import get_provision_shop_use_
 from tenancy.dependencies.resolve_shop_access_provider import get_resolve_shop_access_use_case
 from visit.adapter.inbound.api.error_map import VISIT_ERROR_STATUS
 from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_router
+from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
+from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
 from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
 from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
+from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
+from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 
 
@@ -110,6 +114,10 @@ app.include_router(update_visit_settings_router)
 app.include_router(list_closed_dates_router)
 app.include_router(add_closed_date_router)
 app.include_router(delete_closed_date_router)
+app.include_router(list_menus_router)
+app.include_router(create_menu_router)
+app.include_router(update_menu_router)
+app.include_router(archive_menu_router)
 install_error_handlers(
     app,
     {
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **522 passed**, 통합 **224 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `MenuPgRepository._get`의 `ServiceMenuOrm.shop_id == ctx.shop_id` 조건을 지운다 → `test_다른_매장의_메뉴는_고치거나_보관하지_못한다`가 실패한다 — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/api/schemas/create_menu_schema.py backend/apps/visit/adapter/inbound/api/schemas/list_menus_schema.py backend/apps/visit/adapter/inbound/api/schemas/update_menu_schema.py backend/apps/visit/adapter/inbound/api/v1/archive_menu_router.py backend/apps/visit/adapter/inbound/api/v1/create_menu_router.py backend/apps/visit/adapter/inbound/api/v1/list_menus_router.py backend/apps/visit/adapter/inbound/api/v1/update_menu_router.py backend/apps/visit/adapter/outbound/mappers/visit_mapper.py backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py backend/apps/visit/app/dtos/archive_menu_dto.py backend/apps/visit/app/dtos/create_menu_dto.py backend/apps/visit/app/dtos/list_menus_dto.py backend/apps/visit/app/dtos/menu_view_dto.py backend/apps/visit/app/dtos/update_menu_dto.py backend/apps/visit/app/ports/input/archive_menu_use_case.py backend/apps/visit/app/ports/input/create_menu_use_case.py backend/apps/visit/app/ports/input/list_menus_use_case.py backend/apps/visit/app/ports/input/update_menu_use_case.py backend/apps/visit/app/ports/output/menu_repository.py backend/apps/visit/app/use_cases/archive_menu_interactor.py backend/apps/visit/app/use_cases/create_menu_interactor.py backend/apps/visit/app/use_cases/list_menus_interactor.py backend/apps/visit/app/use_cases/update_menu_interactor.py backend/apps/visit/dependencies/archive_menu_provider.py backend/apps/visit/dependencies/create_menu_provider.py backend/apps/visit/dependencies/list_menus_provider.py backend/apps/visit/dependencies/update_menu_provider.py backend/apps/visit/dependencies/visit_wiring.py backend/apps/visit/tests/adapter/test_archive_menu_router.py backend/apps/visit/tests/adapter/test_create_menu_router.py backend/apps/visit/tests/adapter/test_list_menus_router.py backend/apps/visit/tests/adapter/test_menu_pg_repository.py backend/apps/visit/tests/adapter/test_update_menu_router.py backend/apps/visit/tests/app/use_cases/test_archive_menu_interactor.py backend/apps/visit/tests/app/use_cases/test_create_menu_interactor.py backend/apps/visit/tests/app/use_cases/test_list_menus_interactor.py backend/apps/visit/tests/app/use_cases/test_update_menu_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/main.py
git commit -m "feat(visit): 메뉴표 — 조회·추가·수정·보관, 처음 쓰는 매장의 기본 메뉴"
```

---

### Task 7: 예약 등록 — `POST /visits`, 가족 잠금 뒤 방문 N개, 중복 방지, 막지 않는 경고

반려동물 N마리 → 방문 N개를 한 번에 넣는다(빈 목록이면 보호자만의 방문 하나, `walk_in`이면 지금 시각을 10분 단위로 내린 미용 중 방문). 순서: 입력·메뉴·시각 검증 → **가족 잠금**(`CustomerDirectoryPort.lock_family`, 고객 행) → 넣기 → 경고 계산 → 요약 조립. 검증에서 걸리면 잠그지도 않는다. 메뉴·소요를 비우면 소요는 메뉴 기본 소요의 합(기본 소요 없는 메뉴는 매장 기본으로 센다), 메뉴도 없으면 매장 기본이다. 중복 예약은 유일 색인이 막고 세이브포인트 안에서 409 `VISIT_DUPLICATE`로 바꾼다 — 묶음 가운데 하나라도 걸리면 묶음 전체가 들어가지 않는다(V5·V6). visit 의 첫 허브 포트 자리(`dependencies/hub_ports.get_customer_directory`)를 만들고 `main.py`가 customer 의 구현을 꽂는다.

**Files:**
- Create: `backend/apps/visit/domain/value_objects/new_visit.py`
- Create: `backend/apps/visit/app/dtos/register_visit_dto.py`
- Create: `backend/apps/visit/app/dtos/visit_view_dto.py`
- Create: `backend/apps/visit/app/ports/input/register_visit_use_case.py`
- Modify: `backend/apps/visit/app/ports/output/menu_repository.py`
- Create: `backend/apps/visit/app/ports/output/visit_repository.py`
- Create: `backend/apps/visit/app/services/visit_reader.py`
- Create: `backend/apps/visit/app/use_cases/register_visit_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/visit_view_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/register_visit_router.py`
- Modify: `backend/apps/visit/adapter/outbound/mappers/visit_mapper.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py`
- Create: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/dependencies/hub_ports.py`
- Create: `backend/apps/visit/dependencies/register_visit_provider.py`
- Modify: `backend/apps/visit/dependencies/visit_wiring.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_register_visit_router.py`
- Test: `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`
- Test: `backend/apps/visit/tests/helpers/views.py`

**Interfaces:**
- Consumes: Task 4 의 `CustomerDirectoryPort`·`get_customer_directory_use_case`, Task 2·5·6 의 도메인·일정·메뉴
- Produces:
  - `visit.dependencies.hub_ports.get_customer_directory`(자리)
  - `visit.domain.value_objects.new_visit.NewVisit`
  - `visit.app.ports.output.visit_repository.VisitRepository`: `create_many(ctx, visits)`, `list_occupied(ctx, start, end)`; `MenuRepository.list_active_by_ids(ctx, menu_ids)`
  - `visit.app.dtos.visit_view_dto`: `VisitView`(시각은 매장 시간대)·`CustomerBriefView`·`PetBriefView`·`MenuBriefView`
  - `visit.app.services.visit_reader.describe_visits(ctx, visits, directory, menus) -> list[VisitView]`
  - `visit.adapter.inbound.api.schemas.visit_view_schema.VisitSchema`, `register_visit_schema.EntityId`·`Memo`·`unique_ids`
  - `build_visit_repository(db)`, 테스트 스텁 `FakeDirectory`(`family(...)`, 거절은 `FamilyRejected`)·`FakeVisits`(`seed(**fields)`), `visit.tests.helpers.views.visit_view(...)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_register_visit_router.py`:
```python
from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
from visit.app.dtos.register_visit_dto import RegisteredVisitsView
from visit.dependencies.register_visit_provider import get_register_visit_use_case
from visit.domain.errors import (
    MenuNotAvailableError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
)
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

BODY = {"customer_id": 1, "pet_ids": [101, 102], "starts_at": "2026-10-02T14:00:00+09:00",
        "menu_ids": [1], "memo": " 발톱 짧게 "}
CREATED = RegisteredVisitsView(visits=[visit_view()], warnings=["overlap"])


async def _post(body, stub=None, access=STAFF):
    stub = stub or Recorder(CREATED)
    async with client(build_app(register_visit_router, get_register_visit_use_case, stub, access)) as c:
        return await c.post("/v1/shops/3/visits", json=body), stub


async def test_직원도_예약을_잡고_201_로_방문과_경고를_받는다():
    response, stub = await _post(BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["warnings"] == ["overlap"]
    [visit] = body["visits"]
    assert (visit["starts_at"], visit["pet"]["weight_kg"], visit["menus"]) == (
        "2026-10-02T14:00:00+09:00", 3.2, [{"menu_id": 1, "name": "목욕"}])
    command = stub.calls[0]
    assert (command.ctx.shop_id, command.pet_ids, command.menu_ids, command.memo, command.walk_in) == (
        3, (101, 102), (1,), "발톱 짧게", False)


async def test_지금_시작은_시각_없이_보낸다():
    response, stub = await _post({"customer_id": 1, "walk_in": True})
    assert response.status_code == 201
    assert (stub.calls[0].starts_at, stub.calls[0].walk_in, stub.calls[0].pet_ids) == (None, True, ())


async def test_reservation_write_가_없으면_403_이다():
    response, _ = await _post(BODY, access=READ_ONLY)
    assert error_of(response) == (403, "PERMISSION_DENIED")


async def test_형식이_틀리면_422_VALIDATION_ERROR_다():
    for bad in (
        {**BODY, "starts_at": "2026-10-02T14:00:00"},       # 시간대 없는 시각
        {**BODY, "pet_ids": [101, 101]},                    # 같은 아이 두 번
        {**BODY, "menu_ids": [1, 1]},
        {**BODY, "customer_id": "1"},
        {**BODY, "memo": "발\x00톱"},
        {**BODY, "pet_ids": list(range(1, 12))},            # 열한 마리
        {**BODY, "walk_in": "true"},
    ):
        response, _ = await _post(bad)
        assert error_of(response) == (422, "VALIDATION_ERROR"), bad


async def test_도메인_오류는_설계의_코드와_상태다():
    for error, expected in (
        (VisitDuplicateError("중복"), (409, "VISIT_DUPLICATE")),
        (VisitCrossesMidnightError("자정"), (422, "VISIT_CROSSES_MIDNIGHT")),
        (MenuNotAvailableError("메뉴"), (422, "MENU_NOT_FOUND")),
    ):
        response, _ = await _post(BODY, stub=Recorder(error=error))
        assert error_of(response) == expected
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py`:
```python
from datetime import timedelta

import pytest

from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.domain.errors import VisitDuplicateError
from visit.domain.value_objects.new_visit import NewVisit
from visit.tests.helpers.builders import ctx, kst

pytestmark = pytest.mark.integration

A, B = ctx(shop_id=1), ctx(shop_id=2)


def new(pet_id=101, customer_id=1, starts_at=None, minutes=90, status="reserved", started_at=None, menu_ids=()):
    return NewVisit(customer_id=customer_id, pet_id=pet_id, starts_at=starts_at or kst(10, 2, 14),
                    duration_minutes=minutes, status=status, started_at=started_at, menu_ids=menu_ids,
                    memo=None, created_by_member_id=11)


async def _menu_ids(session, shop=A):
    await SchedulePgRepository(session).ensure(shop)
    return [m.id for m in await MenuPgRepository(session).list(shop, include_archived=False)]


async def test_한_번에_넣고_메뉴와_함께_읽는다(db_session):
    bath, trim, *_ = await _menu_ids(db_session)
    visits = await VisitPgRepository(db_session).create_many(
        A, [new(101, menu_ids=(bath, trim)), new(102, menu_ids=(bath, trim))])
    assert [(v.pet_id, v.status, v.menu_ids, v.shop_id) for v in visits] == [
        (101, "reserved", (bath, trim), 1), (102, "reserved", (bath, trim), 1)]


async def test_지금_시작한_손님은_상태를_바꾼_멤버가_만든_사람이다(db_session):
    [visit] = await VisitPgRepository(db_session).create_many(
        A, [new(status="in_progress", started_at=kst(10, 2, 14, 3))])
    assert (visit.status, visit.started_at, visit.status_changed_by_member_id) == (
        "in_progress", kst(10, 2, 14, 3), 11)


async def test_같은_시각의_중복은_VISIT_DUPLICATE_이고_세션은_계속_쓴다(db_session):
    """V5 — 한 번에 넣는 묶음 가운데 하나라도 걸리면 묶음 전체가 들어가지 않는다."""
    repo = VisitPgRepository(db_session)
    await repo.create_many(A, [new(101)])
    with pytest.raises(VisitDuplicateError):
        await repo.create_many(A, [new(102), new(101)])
    with pytest.raises(VisitDuplicateError):
        await repo.create_many(A, [new(None), new(None)])   # 보호자만의 방문도 보호자·시각으로 하나
    occupied = await repo.list_occupied(A, kst(10, 2), kst(10, 3))
    assert [v.pet_id for v in occupied] == [101]


async def test_시간이_겹치는_살아_있는_방문만(db_session):
    repo = VisitPgRepository(db_session)
    await repo.create_many(A, [new(101, starts_at=kst(10, 1, 20), minutes=240)])     # 전날 밤 → 자정에 끝
    await repo.create_many(A, [new(102, starts_at=kst(10, 2, 10))])
    await repo.create_many(A, [new(103, starts_at=kst(10, 2, 23, 50), minutes=10)])
    await repo.create_many(B, [new(104, starts_at=kst(10, 2, 11))])                    # 다른 매장
    await repo.create_many(A, [new(105, starts_at=kst(10, 3, 0))])                     # 다음 날
    occupied = await repo.list_occupied(A, kst(10, 2), kst(10, 3))
    assert [v.pet_id for v in occupied] == [102, 103]   # 전날 밤 방문은 딱 0시에 끝나 겹치지 않는다
    long_before = await repo.list_occupied(A, kst(10, 1, 23), kst(10, 1, 23) + timedelta(hours=1))
    assert [v.pet_id for v in long_before] == [101]
```

`backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py`:
```python
from datetime import date, time

import pytest

from visit.app.dtos.register_visit_dto import RegisterVisitCommand
from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
from visit.domain.errors import (
    MenuNotAvailableError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitInputError,
)
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeMenus,
    FakeSchedule,
    FakeVisits,
    FamilyRejected,
    Journal,
)

NOW = kst(9, 23, 15, 37)


def _setup(settings=None):
    journal = Journal()
    schedule = FakeSchedule(journal) if settings is None else FakeSchedule(journal, settings)
    menus, visits, directory = FakeMenus(journal), FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102))
    interactor = RegisterVisitInteractor(visits, menus, schedule, directory, now=lambda: NOW)
    return journal, schedule, menus, visits, directory, interactor


def _command(**overrides):
    fields = dict(ctx=ctx(), customer_id=1, pet_ids=(101,), starts_at=kst(10, 2, 14), duration_minutes=None,
                  menu_ids=(), memo=None, walk_in=False)
    fields.update(overrides)
    return RegisterVisitCommand(**fields)


async def test_두_마리면_방문이_둘이고_가족을_잠근_뒤_넣는다():
    journal, _, menus, _, _, interactor = _setup()
    bath = menus.seed("목욕", minutes=60)
    nails = menus.seed("발톱", minutes=None)   # 기본 소요가 없으면 매장 기본(120)으로 센다
    result = await interactor.register_visit(_command(pet_ids=(101, 102), menu_ids=(bath.id, nails.id)))
    assert [(v.pet.pet_id, v.status, v.duration_minutes) for v in result.visits] == [
        (101, "reserved", 180), (102, "reserved", 180)]
    assert [m.name for m in result.visits[0].menus] == ["목욕", "발톱"]
    assert result.warnings == []   # 형제끼리는 겹침이 아니다
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("create_visits")
    assert ("lock_family", 1, (101, 102)) in journal


async def test_시각은_매장_시간대로_내보낸다():
    *_, interactor = _setup()
    [visit] = (await interactor.register_visit(_command())).visits
    assert (visit.starts_at.isoformat(), visit.ends_at.isoformat()) == (
        "2026-10-02T14:00:00+09:00", "2026-10-02T16:00:00+09:00")
    assert (visit.customer.name, visit.pet.name) == ("김민지", "아이101")


async def test_반려동물_없이_보호자만의_방문_하나():
    *_, visits, _, interactor = _setup()
    [visit] = (await interactor.register_visit(_command(pet_ids=()))).visits
    assert visit.pet is None
    assert visits.rows[visit.visit_id].pet_id is None


async def test_메뉴도_소요도_없으면_매장_기본_소요다():
    *_, interactor = _setup(ScheduleSettings(time(10), time(19), 90, frozenset()))
    [visit] = (await interactor.register_visit(_command())).visits
    assert visit.duration_minutes == 90


async def test_소요를_보내면_그_값이다():
    *_, interactor = _setup()
    [visit] = (await interactor.register_visit(_command(duration_minutes=150))).visits
    assert visit.duration_minutes == 150


async def test_지금_시작한_손님은_10분_단위로_내린_시각에_미용_중이다():
    *_, visits, _, interactor = _setup()
    [visit] = (await interactor.register_visit(_command(starts_at=None, walk_in=True))).visits
    row = visits.rows[visit.visit_id]
    assert (row.starts_at, row.status, row.started_at, row.status_changed_by_member_id) == (
        kst(9, 23, 15, 30), "in_progress", NOW, 11)


@pytest.mark.parametrize("fields", [dict(walk_in=True), dict(starts_at=None)])
async def test_예약_시각과_지금_시작은_하나만(fields):
    journal, *_, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.register_visit(_command(**fields))
    assert journal == []


async def test_고를_수_없는_메뉴면_잠그지도_않는다():
    """V1 — 다른 매장 메뉴와 보관한 메뉴는 이 매장에 없는 메뉴다."""
    journal, _, menus, *_, interactor = _setup()
    theirs = menus.seed("남의 메뉴", shop_id=2)
    archived = menus.seed("옛 메뉴", archived=True)
    for menu_id in (theirs.id, archived.id, 999):
        with pytest.raises(MenuNotAvailableError):
            await interactor.register_visit(_command(menu_ids=(menu_id,)))
    assert "lock_family" not in [entry[0] for entry in journal]


@pytest.mark.parametrize(("fields", "error"), [
    (dict(starts_at=kst(10, 2, 14, 5)), VisitInputError),                  # 10분 단위가 아니다
    (dict(starts_at=kst(10, 2, 23), duration_minutes=120), VisitCrossesMidnightError),
    (dict(duration_minutes=95), VisitInputError),
])
async def test_시각_규칙에_어긋나면_잠그지도_않는다(fields, error):
    journal, *_, interactor = _setup()
    with pytest.raises(error):
        await interactor.register_visit(_command(**fields))
    assert "lock_family" not in [entry[0] for entry in journal]


async def test_가족_확인에서_거절되면_넣지_않는다():
    """V2 — 다른 가족·다른 매장의 반려동물, 무지개다리 아이는 customer 가 거절한다."""
    journal, *_, interactor = _setup()
    with pytest.raises(FamilyRejected):
        await interactor.register_visit(_command(pet_ids=(999,)))
    assert "create_visits" not in [entry[0] for entry in journal]


async def test_같은_시각에_이미_있으면_VISIT_DUPLICATE_다():
    *_, interactor = _setup()
    await interactor.register_visit(_command())
    with pytest.raises(VisitDuplicateError):
        await interactor.register_visit(_command())


async def test_경고는_막지_않고_함께_돌려준다():
    _, _, _, visits, directory, interactor = _setup(
        ScheduleSettings(time(10), time(19), 120, frozenset({4})))   # 금요일 휴무
    directory.family(2, pets=(201,))
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 13), duration_minutes=120)
    result = await interactor.register_visit(_command(starts_at=kst(10, 2, 18)))   # 10/2 는 금요일
    assert result.warnings == ["closed_day", "outside_hours"]
    result = await interactor.register_visit(_command(pet_ids=(102,), starts_at=kst(10, 2, 14)))
    assert result.warnings == ["overlap", "closed_day"]


async def test_임시_휴무일도_closed_day():
    _, schedule, *_, interactor = _setup()
    schedule.closed[(1, date(2026, 10, 2))] = ClosedDate(day=date(2026, 10, 2), note=None)
    assert (await interactor.register_visit(_command())).warnings == ["closed_day"]
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -2,9 +2,12 @@
 from __future__ import annotations
 
 from dataclasses import replace
+from decimal import Decimal
 
+from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from visit.domain.entities.menu import Menu
-from visit.domain.errors import MenuNameTakenError, MenuNotFoundError
+from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
+from visit.domain.errors import MenuNameTakenError, MenuNotFoundError, VisitDuplicateError
 from visit.domain.value_objects.closed_date import ClosedDate
 from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
 from visit.tests.helpers.builders import kst
@@ -95,3 +98,82 @@ class FakeMenus:
         self.rows[menu_id] = replace(current, archived_at=current.archived_at or kst(9, 23))
         self.journal.append(("archive_menu", menu_id))
         return self.rows[menu_id]
+
+
+class FamilyRejected(Exception):
+    """FakeDirectory 가 가족을 거절할 때 던진다 — 실제로는 customer 의 도메인 오류(404·422)다."""
+
+
+class FakeDirectory:
+    """CustomerDirectoryPort 스텁. families 는 {고객 ID: (매장 ID, {반려동물 ID: 무지개다리 여부})}."""
+
+    def __init__(self, journal: Journal | None = None) -> None:
+        self.journal = journal if journal is not None else Journal()
+        self.families: dict[int, tuple[int, dict[int, bool]]] = {}
+        self.names: dict[int, str | None] = {}
+
+    def family(self, customer_id=1, pets=(101,), shop_id=1, name="김민지", passed=()) -> None:
+        self.families[customer_id] = (shop_id, {p: p in passed for p in pets})
+        self.names[customer_id] = name
+
+    async def lock_family(self, ctx, customer_id, pet_ids):
+        self.journal.append(("lock_family", customer_id, tuple(pet_ids)))
+        shop, pets = self.families.get(customer_id, (None, {}))
+        if shop != ctx.shop_id or any(p not in pets or pets[p] for p in pet_ids):
+            raise FamilyRejected(customer_id)
+
+    async def briefs(self, ctx, customer_ids, pet_ids):
+        customers = {
+            c: CustomerBrief(customer_id=c, name=self.names[c], phone_masked="010-12··-5678")
+            for c in customer_ids if self.families.get(c, (None,))[0] == ctx.shop_id
+        }
+        pets = {}
+        for c, (shop, family) in self.families.items():
+            for p in family:
+                if p in pet_ids and shop == ctx.shop_id:
+                    pets[p] = PetBrief(pet_id=p, customer_id=c, name=f"아이{p}", species="dog", breed="말티즈",
+                                       weight_kg=Decimal("3.2"), passed_away=family[p])
+        return FamilyBriefs(customers=customers, pets=pets)
+
+    async def set_last_visit(self, ctx, customer_id, at):
+        self.journal.append(("set_last_visit", customer_id, at))
+
+
+class FakeVisits:
+    def __init__(self, journal: Journal | None = None) -> None:
+        self.journal = journal if journal is not None else Journal()
+        self.rows: dict[int, Visit] = {}
+        self._next = 1
+
+    def seed(self, **fields) -> Visit:
+        from visit.tests.helpers.builders import visit
+
+        row = visit(**{"id": self._next, **fields})
+        self.rows[row.id] = row
+        self._next = max(self._next, row.id) + 1
+        return row
+
+    def _clash(self, ctx, customer_id, pet_id, starts_at, ignore=()) -> bool:
+        return any(
+            v.shop_id == ctx.shop_id and v.status in ACTIVE_STATUSES and v.starts_at == starts_at
+            and v.id not in ignore
+            and (v.pet_id == pet_id if pet_id is not None else (v.pet_id is None and v.customer_id == customer_id))
+            for v in self.rows.values()
+        )
+
+    async def create_many(self, ctx, visits):
+        if any(self._clash(ctx, n.customer_id, n.pet_id, n.starts_at) for n in visits):
+            raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
+        created = [
+            self.seed(shop_id=ctx.shop_id, customer_id=n.customer_id, pet_id=n.pet_id, starts_at=n.starts_at,
+                      duration_minutes=n.duration_minutes, status=n.status, started_at=n.started_at,
+                      menu_ids=n.menu_ids, memo=n.memo, created_by_member_id=n.created_by_member_id,
+                      status_changed_by_member_id=n.created_by_member_id if n.started_at else None)
+            for n in visits
+        ]
+        self.journal.append(("create_visits", [v.id for v in created]))
+        return created
+
+    async def list_occupied(self, ctx, start, end):
+        return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id and v.is_active
+                       and v.starts_at < end and v.ends_at > start), key=lambda v: (v.starts_at, v.id))
```

`backend/apps/visit/tests/helpers/views.py`:
```python
"""라우터 테스트가 스텁 유스케이스에서 돌려줄 방문 보기 값."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from visit.app.dtos.visit_view_dto import CustomerBriefView, MenuBriefView, PetBriefView, VisitView

_SEOUL = ZoneInfo("Asia/Seoul")


def visit_view(visit_id: int = 1, **overrides) -> VisitView:
    fields = dict(
        visit_id=visit_id,
        customer=CustomerBriefView(customer_id=1, name="김민지", phone_masked="010-12··-5678"),
        pet=PetBriefView(pet_id=101, name="콩이", species="dog", breed="말티즈", weight_kg=Decimal("3.2")),
        starts_at=datetime(2026, 10, 2, 14, tzinfo=_SEOUL), ends_at=datetime(2026, 10, 2, 15, 30, tzinfo=_SEOUL),
        duration_minutes=90, status="reserved", started_at=None, completed_at=None, canceled_at=None,
        cancel_reason=None, memo=None, menus=[MenuBriefView(menu_id=1, name="목욕")],
        status_changed_by_member_id=None,
    )
    return replace(VisitView(**fields), **overrides)
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests tests/test_hub_port_binding.py -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해 등록 테스트가 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/value_objects/new_visit.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewVisit:
    """새로 넣을 방문 하나. 예약이면 reserved, 지금 시작한 손님이면 in_progress 로 들어간다."""

    customer_id: int
    pet_id: int | None
    starts_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    menu_ids: tuple[int, ...]
    memo: str | None
    created_by_member_id: int
```

`backend/apps/visit/app/dtos/register_visit_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class RegisterVisitCommand:
    """반려동물 N마리 → 방문 N개. pet_ids 가 비면 보호자만의 방문 하나.

    walk_in 이면 예약 없이 온 손님이다 — starts_at 은 받지 않고 지금(10분 단위 내림)으로, 미용 중으로 만든다.
    duration_minutes 가 없으면 고른 메뉴의 기본 소요 합, 메뉴도 없으면 매장 기본 소요.
    """

    ctx: ShopContext
    customer_id: int
    pet_ids: tuple[int, ...]
    starts_at: datetime | None
    duration_minutes: int | None
    menu_ids: tuple[int, ...]
    memo: str | None
    walk_in: bool


@dataclass(frozen=True)
class RegisteredVisitsView:
    visits: list[VisitView]
    warnings: list[str]   # overlap · closed_day · outside_hours — 막지 않는 경고
```

`backend/apps/visit/app/dtos/visit_view_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from hub.app.dtos.family_brief import FamilyBriefs
from visit.domain.entities.visit import Visit


@dataclass(frozen=True)
class MenuBriefView:
    menu_id: int
    name: str


@dataclass(frozen=True)
class CustomerBriefView:
    """익명화한 고객이면 이름과 번호가 None 이다 — 앱은 '삭제된 고객'으로 보인다."""

    customer_id: int
    name: str | None
    phone_masked: str | None


@dataclass(frozen=True)
class PetBriefView:
    pet_id: int
    name: str | None
    species: str
    breed: str
    weight_kg: Decimal


@dataclass(frozen=True)
class VisitView:
    """방문 하나. 시각은 모두 매장 시간대로 바꿔 내보낸다."""

    visit_id: int
    customer: CustomerBriefView
    pet: PetBriefView | None
    starts_at: datetime
    ends_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    cancel_reason: str | None
    memo: str | None
    menus: list[MenuBriefView]
    status_changed_by_member_id: int | None

    @classmethod
    def of(cls, visit: Visit, briefs: FamilyBriefs, menu_names: dict[int, str], zone: ZoneInfo) -> VisitView:
        def local(moment: datetime | None) -> datetime | None:
            return moment.astimezone(zone) if moment is not None else None

        customer = briefs.customers.get(visit.customer_id)
        pet = briefs.pets.get(visit.pet_id) if visit.pet_id is not None else None
        return cls(
            visit_id=visit.id,
            customer=CustomerBriefView(
                customer_id=visit.customer_id,
                name=customer.name if customer else None,
                phone_masked=customer.phone_masked if customer else None,
            ),
            pet=PetBriefView(pet_id=pet.pet_id, name=pet.name, species=pet.species, breed=pet.breed,
                             weight_kg=pet.weight_kg) if pet else None,
            starts_at=local(visit.starts_at), ends_at=local(visit.ends_at),
            duration_minutes=visit.duration_minutes, status=visit.status,
            started_at=local(visit.started_at), completed_at=local(visit.completed_at),
            canceled_at=local(visit.canceled_at), cancel_reason=visit.cancel_reason, memo=visit.memo,
            menus=[MenuBriefView(menu_id=m, name=menu_names[m]) for m in visit.menu_ids],
            status_changed_by_member_id=visit.status_changed_by_member_id,
        )
```

`backend/apps/visit/app/ports/input/register_visit_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.register_visit_dto import RegisteredVisitsView, RegisterVisitCommand


class RegisterVisitUseCase(ABC):
    @abstractmethod
    async def register_visit(self, command: RegisterVisitCommand) -> RegisteredVisitsView: ...
```

`backend/apps/visit/app/ports/output/menu_repository.py` (수정):
```diff
@@ -13,6 +13,10 @@ class MenuRepository(ABC):
     async def list(self, ctx: ShopContext, include_archived: bool) -> list[Menu]:
         """순서(sort_order) 대로."""
 
+    @abstractmethod
+    async def list_active_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
+        """요청 본문이 고른 메뉴 가운데 이 매장의 보관하지 않은 것만."""
+
     @abstractmethod
     async def create(self, ctx: ShopContext, name: str, default_duration_minutes: int | None) -> Menu:
         """맨 뒤 순서로 넣는다. 보관하지 않은 메뉴와 이름이 겹치면 MenuNameTakenError."""
```

`backend/apps/visit/app/ports/output/visit_repository.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.domain.entities.visit import Visit
from visit.domain.value_objects.new_visit import NewVisit


class VisitRepository(ABC):
    """방문. 모든 메서드가 ShopContext 의 매장으로 거른다."""

    @abstractmethod
    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
        VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""

    @abstractmethod
    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        """[start, end) 와 시간이 겹치는 살아 있는 방문(예약됨·미용 중)."""
```

`backend/apps/visit/app/services/visit_reader.py`:
```python
"""방문을 화면에 보여 줄 모양으로 조립한다 — 보호자·반려동물 이름은 허브 포트로, 메뉴 이름은 메뉴표에서.

여러 슬라이스가 쓰기를 마친 뒤 같은 모양으로 돌려준다. 이름을 방문에 복사해 두지 않는다(설계 5.3).
"""
from __future__ import annotations

from zoneinfo import ZoneInfo

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.visit_view_dto import VisitView
from visit.app.ports.output.menu_repository import MenuRepository
from visit.domain.entities.visit import Visit


async def describe_visits(
    ctx: ShopContext, visits: list[Visit], directory: CustomerDirectoryPort, menus: MenuRepository
) -> list[VisitView]:
    if not visits:
        return []
    briefs = await directory.briefs(
        ctx,
        sorted({v.customer_id for v in visits}),
        sorted({v.pet_id for v in visits if v.pet_id is not None}),
    )
    menu_names = {}
    if any(v.menu_ids for v in visits):
        # 보관한 메뉴도 이름을 보여 준다 — 지난 방문이 가리키고 있다.
        menu_names = {m.id: m.name for m in await menus.list(ctx, include_archived=True)}
    zone = ZoneInfo(ctx.timezone)
    return [VisitView.of(v, briefs, menu_names, zone) for v in visits]
```

`backend/apps/visit/app/use_cases/register_visit_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.register_visit_dto import RegisteredVisitsView, RegisterVisitCommand
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import IN_PROGRESS, RESERVED
from visit.domain.errors import MenuNotAvailableError, VisitInputError
from visit.domain.services.visit_schedule import (
    Occupied,
    check_duration,
    check_same_day,
    check_start,
    day_bounds,
    floor_to_step,
    local_date,
    warnings_for,
)
from visit.domain.value_objects.new_visit import NewVisit


class RegisterVisitInteractor(RegisterVisitUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._now = now

    async def register_visit(self, command: RegisterVisitCommand) -> RegisteredVisitsView:
        ctx, tz, now = command.ctx, command.ctx.timezone, self._now()
        if command.walk_in == (command.starts_at is not None):
            raise VisitInputError("예약 시각과 '지금 시작' 중 하나만 보내 주세요.")
        settings = await self._schedule.ensure(ctx)
        menus = await self._menus.list_active_by_ids(ctx, list(command.menu_ids))
        if len(menus) != len(command.menu_ids):
            raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")
        duration = command.duration_minutes
        if duration is None:
            duration = sum(m.default_duration_minutes or settings.default_duration_minutes for m in menus) or (
                settings.default_duration_minutes
            )
        check_duration(duration)
        if command.walk_in:
            starts_at, status, started_at = floor_to_step(now, tz), IN_PROGRESS, now
        else:
            starts_at, status, started_at = command.starts_at, RESERVED, None
            check_start(starts_at, now, tz)
        check_same_day(starts_at, duration, tz)

        # 고객 행 → 방문 행. 익명화·무지개다리·반려동물 삭제와 겹치지 않게 가족부터 잠근다(설계 4.2, V3).
        await self._directory.lock_family(ctx, command.customer_id, command.pet_ids)
        created = await self._visits.create_many(
            ctx,
            [
                NewVisit(customer_id=command.customer_id, pet_id=pet_id, starts_at=starts_at,
                         duration_minutes=duration, status=status, started_at=started_at,
                         menu_ids=command.menu_ids, memo=command.memo, created_by_member_id=ctx.member_id)
                for pet_id in (command.pet_ids or (None,))
            ],
        )

        day = local_date(starts_at, tz)
        start, end = day_bounds(day, tz)
        occupied = [Occupied(v.starts_at, v.ends_at, v.group_key)
                    for v in await self._visits.list_occupied(ctx, start, end)]
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        warnings = warnings_for(starts_at, duration, (command.customer_id, starts_at), tz, settings, closed,
                                occupied)
        return RegisteredVisitsView(
            visits=await describe_visits(ctx, created, self._directory, self._menus), warnings=warnings
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py`:
```python
from __future__ import annotations

from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    Field,
    StrictBool,
    StrictInt,
    StringConstraints,
    field_validator,
)

from visit.adapter.inbound.api.schemas.text_validators import reject_control_chars
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.register_visit_dto import RegisteredVisitsView

_MAX_BIGINT = 9_223_372_036_854_775_807

EntityId = Annotated[StrictInt, Field(ge=1, le=_MAX_BIGINT)]
Memo = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500),
    AfterValidator(lambda v: reject_control_chars(v, allow_newline=True)),
] | None


def _unique(ids: list[int]) -> list[int]:
    if len(set(ids)) != len(ids):
        raise ValueError("같은 ID 를 두 번 보낼 수 없습니다.")
    return ids


class RegisterVisitRequestSchema(BaseModel):
    """예약 등록. starts_at 은 시간대가 붙은 시각이어야 한다(예: 2026-10-02T14:00:00+09:00).
    walk_in 이면 starts_at 을 보내지 않는다 — 지금 시작한 손님이다."""

    customer_id: EntityId
    pet_ids: Annotated[list[EntityId], Field(max_length=10)] = []
    starts_at: AwareDatetime | None = None
    duration_minutes: StrictInt | None = None
    menu_ids: Annotated[list[EntityId], Field(max_length=10)] = []
    memo: Memo = None
    walk_in: StrictBool = False

    _pets_unique = field_validator("pet_ids", "menu_ids")(_unique)


class RegisteredVisitsSchema(BaseModel):
    visits: list[VisitSchema]
    warnings: list[str]   # overlap · closed_day · outside_hours

    @classmethod
    def of(cls, view: RegisteredVisitsView) -> RegisteredVisitsSchema:
        return cls(visits=[VisitSchema.of(v) for v in view.visits], warnings=view.warnings)
```

`backend/apps/visit/adapter/inbound/api/schemas/visit_view_schema.py`:
```python
"""방문 응답 모양 — 여러 슬라이스가 함께 쓴다(app 의 visit_view_dto 와 짝)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.app.dtos.visit_view_dto import VisitView


class MenuBriefSchema(BaseModel):
    menu_id: int
    name: str


class CustomerBriefSchema(BaseModel):
    customer_id: int
    name: str | None          # 익명화한 고객이면 None
    phone_masked: str | None


class PetBriefSchema(BaseModel):
    pet_id: int
    name: str | None
    species: str
    breed: str
    weight_kg: float   # JSON 숫자로 내보낸다(customer 와 같은 관례)


class VisitSchema(BaseModel):
    visit_id: int
    customer: CustomerBriefSchema
    pet: PetBriefSchema | None   # None 이면 보호자만의 방문
    starts_at: datetime          # 매장 시간대
    ends_at: datetime
    duration_minutes: int
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    canceled_at: datetime | None
    cancel_reason: str | None
    memo: str | None
    menus: list[MenuBriefSchema]
    status_changed_by_member_id: int | None

    @classmethod
    def of(cls, view: VisitView) -> VisitSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/register_visit_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.register_visit_schema import (
    RegisteredVisitsSchema,
    RegisterVisitRequestSchema,
)
from visit.app.dtos.register_visit_dto import RegisterVisitCommand
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.dependencies.register_visit_provider import get_register_visit_use_case

register_visit_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@register_visit_router.post("/{shop_id}/visits", response_model=RegisteredVisitsSchema, status_code=201)
async def register_visit(
    body: RegisterVisitRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: RegisterVisitUseCase = Depends(get_register_visit_use_case),
) -> RegisteredVisitsSchema:
    view = await use_case.register_visit(
        RegisterVisitCommand(
            ctx=ctx, customer_id=body.customer_id, pet_ids=tuple(body.pet_ids), starts_at=body.starts_at,
            duration_minutes=body.duration_minutes, menu_ids=tuple(body.menu_ids),
            memo=body.memo or None, walk_in=body.walk_in,
        )
    )
    return RegisteredVisitsSchema.of(view)
```

`backend/apps/visit/adapter/outbound/mappers/visit_mapper.py` (수정):
```diff
@@ -1,7 +1,8 @@
 from __future__ import annotations
 
-from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm
+from visit.adapter.outbound.orm.visit_orm import ServiceMenuOrm, VisitOrm
 from visit.domain.entities.menu import Menu
+from visit.domain.entities.visit import Visit
 
 
 def to_menu(orm: ServiceMenuOrm) -> Menu:
@@ -10,3 +11,14 @@ def to_menu(orm: ServiceMenuOrm) -> Menu:
         default_duration_minutes=orm.default_duration_minutes, sort_order=orm.sort_order,
         archived_at=orm.archived_at,
     )
+
+
+def to_visit(orm: VisitOrm, menu_ids: list[int]) -> Visit:
+    return Visit(
+        id=orm.id, shop_id=orm.shop_id, customer_id=orm.customer_id, pet_id=orm.pet_id,
+        starts_at=orm.starts_at, duration_minutes=orm.duration_minutes, status=orm.status,
+        started_at=orm.started_at, completed_at=orm.completed_at, canceled_at=orm.canceled_at,
+        cancel_reason=orm.cancel_reason, memo=orm.memo, menu_ids=tuple(menu_ids),
+        created_by_member_id=orm.created_by_member_id,
+        status_changed_by_member_id=orm.status_changed_by_member_id,
+    )
```

`backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py` (수정):
```diff
@@ -32,6 +32,17 @@ class MenuPgRepository(MenuRepository):
         ).scalars()
         return [to_menu(row) for row in rows]
 
+    async def list_active_by_ids(self, ctx: ShopContext, menu_ids: list[int]) -> list[Menu]:
+        rows = (
+            await self._session.execute(
+                select(ServiceMenuOrm).where(
+                    ServiceMenuOrm.id.in_(menu_ids), ServiceMenuOrm.shop_id == ctx.shop_id,
+                    ServiceMenuOrm.archived_at.is_(None),
+                )
+            )
+        ).scalars()
+        return [to_menu(row) for row in rows]
+
     async def create(self, ctx: ShopContext, name: str, default_duration_minutes: int | None) -> Menu:
         next_order = (
             select(func.coalesce(func.max(ServiceMenuOrm.sort_order), 0) + 1)
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`:
```python
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from sqlalchemy import insert, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.mappers.visit_mapper import to_visit
from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
from visit.domain.errors import VisitDuplicateError
from visit.domain.services.visit_schedule import MAX_DURATION
from visit.domain.value_objects.new_visit import NewVisit

_DUPLICATE = {"uq_visits_pet_start_active", "uq_visits_customer_start_active"}


class VisitPgRepository(VisitRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, ctx: ShopContext, visits: list[NewVisit]) -> list[Visit]:
        async with self._duplicate_guard():
            ids = []
            for new in visits:
                visit_id = (
                    await self._session.execute(
                        insert(VisitOrm)
                        .values(
                            shop_id=ctx.shop_id, customer_id=new.customer_id, pet_id=new.pet_id,
                            starts_at=new.starts_at, duration_minutes=new.duration_minutes,
                            status=new.status, started_at=new.started_at, memo=new.memo,
                            created_by_member_id=new.created_by_member_id,
                            status_changed_by_member_id=(
                                new.created_by_member_id if new.started_at is not None else None
                            ),
                        )
                        .returning(VisitOrm.id)
                    )
                ).scalar_one()
                if new.menu_ids:
                    await self._session.execute(
                        insert(VisitMenuOrm), [dict(visit_id=visit_id, menu_id=m) for m in new.menu_ids]
                    )
                ids.append(visit_id)
        return await self._read(ctx, select(VisitOrm).where(VisitOrm.id.in_(ids)))

    async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
        # 소요는 최대 600분이라 그만큼 앞에서 시작한 방문까지 가져와 끝 시각으로 거른다.
        rows = await self._read(
            ctx,
            select(VisitOrm).where(
                VisitOrm.status.in_(ACTIVE_STATUSES),
                VisitOrm.starts_at >= start - timedelta(minutes=MAX_DURATION),
                VisitOrm.starts_at < end,
            ),
        )
        return [v for v in rows if v.ends_at > start]

    async def _read(self, ctx: ShopContext, stmt) -> list[Visit]:
        rows = (
            await self._session.execute(
                stmt.where(VisitOrm.shop_id == ctx.shop_id)
                .order_by(VisitOrm.starts_at, VisitOrm.id)
                .execution_options(populate_existing=True)
            )
        ).scalars().all()
        menus: dict[int, list[int]] = {}
        if rows:
            pairs = await self._session.execute(
                select(VisitMenuOrm.visit_id, VisitMenuOrm.menu_id)
                .where(VisitMenuOrm.visit_id.in_([r.id for r in rows]))
                .order_by(VisitMenuOrm.visit_id, VisitMenuOrm.menu_id)
            )
            for visit_id, menu_id in pairs:
                menus.setdefault(visit_id, []).append(menu_id)
        return [to_visit(row, menus.get(row.id, [])) for row in rows]

    @asynccontextmanager
    async def _duplicate_guard(self):
        """중복 예약 유일 색인 위반을 VISIT_DUPLICATE 로 바꾼다. 세이브포인트라 트랜잭션은 계속 쓸 수 있다.

        같은 예약을 동시에 넣는 두 요청 중 늦은 쪽은 앞선 쪽이 커밋할 때까지 색인에서 기다렸다가 여기서 걸린다.
        """
        try:
            async with self._session.begin_nested():
                yield
        except IntegrityError as exc:
            if getattr(exc.orig.__cause__, "constraint_name", None) in _DUPLICATE:
                raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.") from exc
            raise
```

`backend/apps/visit/dependencies/hub_ports.py`:
```python
"""허브 포트 자리 — visit 이 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.customer_directory_port import CustomerDirectoryPort


def get_customer_directory() -> CustomerDirectoryPort:
    raise RuntimeError("CustomerDirectoryPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/visit/dependencies/register_visit_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.register_visit_use_case import RegisterVisitUseCase
from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_register_visit_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> RegisterVisitUseCase:
    return RegisterVisitInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
    )
```

`backend/apps/visit/dependencies/visit_wiring.py` (수정):
```diff
@@ -5,8 +5,10 @@ from sqlalchemy.ext.asyncio import AsyncSession
 
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
+from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
+from visit.app.ports.output.visit_repository import VisitRepository
 
 
 def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
@@ -15,3 +17,7 @@ def build_schedule_repository(db: AsyncSession) -> ScheduleRepository:
 
 def build_menu_repository(db: AsyncSession) -> MenuRepository:
     return MenuPgRepository(db)
+
+
+def build_visit_repository(db: AsyncSession) -> VisitRepository:
+    return VisitPgRepository(db)
```

`backend/main.py` (수정):
```diff
@@ -38,6 +38,7 @@ from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
 )
 from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
 from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
+from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
 from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
@@ -63,8 +64,10 @@ from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed
 from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
+from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
+from visit.dependencies.hub_ports import get_customer_directory
 
 
 @asynccontextmanager
@@ -118,6 +121,7 @@ app.include_router(list_menus_router)
 app.include_router(create_menu_router)
 app.include_router(update_menu_router)
 app.include_router(archive_menu_router)
+app.include_router(register_visit_router)
 install_error_handlers(
     app,
     {
@@ -133,6 +137,7 @@ app.dependency_overrides[get_shop_provisioning] = get_provision_shop_use_case
 app.dependency_overrides[get_user_directory] = get_get_user_profiles_use_case
 app.dependency_overrides[get_membership_directory] = get_list_memberships_use_case
 app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
+app.dependency_overrides[get_customer_directory] = get_customer_directory_use_case
 
 
 @app.get("/health")
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests tests/test_hub_port_binding.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **543 passed**, 통합 **228 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `main.py`의 `app.dependency_overrides[get_customer_directory] = …` 줄을 주석으로 막는다 → `test_API_프로세스에는_빈_자리도_빠진_가드도_없다`가 `허브 포트 자리 get_customer_directory 가 비어 있다`로 실패한다 — 되돌린다.
- `RegisterVisitInteractor`에서 `lock_family` 호출을 지운다 → `test_두_마리면_방문이_둘이고_가족을_잠근_뒤_넣는다`(journal 순서)가 실패한다 — 되돌린다. 실제 두 세션 판별은 Task 14 다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py backend/apps/visit/adapter/inbound/api/schemas/visit_view_schema.py backend/apps/visit/adapter/inbound/api/v1/register_visit_router.py backend/apps/visit/adapter/outbound/mappers/visit_mapper.py backend/apps/visit/adapter/outbound/pg/menu_pg_repository.py backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py backend/apps/visit/app/dtos/register_visit_dto.py backend/apps/visit/app/dtos/visit_view_dto.py backend/apps/visit/app/ports/input/register_visit_use_case.py backend/apps/visit/app/ports/output/menu_repository.py backend/apps/visit/app/ports/output/visit_repository.py backend/apps/visit/app/services/visit_reader.py backend/apps/visit/app/use_cases/register_visit_interactor.py backend/apps/visit/dependencies/hub_ports.py backend/apps/visit/dependencies/register_visit_provider.py backend/apps/visit/dependencies/visit_wiring.py backend/apps/visit/domain/value_objects/new_visit.py backend/apps/visit/tests/adapter/test_register_visit_router.py backend/apps/visit/tests/adapter/test_visit_pg_repository.py backend/apps/visit/tests/app/use_cases/test_register_visit_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/apps/visit/tests/helpers/views.py backend/main.py
git commit -m "feat(visit): 예약 등록 — POST /visits, 가족 잠금 뒤 방문 N개, 중복 방지, 막지 않는 경고"
```

---

### Task 8: 하루 목록·월 달력·시간 칸 — 가족 묶음, 겹침, 정리 안 된 예약

조회 슬라이스 셋. 하루 목록은 그날 시작하는 방문 전부(취소·노쇼 포함)를 시작 순으로 주고, 방문마다 가족 묶음 키(`group_key`)·다른 묶음과의 겹침·정리 안 된 예약(지난 날인데 아직 예약됨) 표시를 붙인다. 마릿수는 예약됨·미용 중·완료만 센다. 월 달력은 그달 모든 날의 수와 휴무를 주고, 위쪽 "정리 안 된 예약 N건"은 달과 상관없이 매장 전체와 가장 이른 날이다(설계 6.4). 시간 칸은 영업시간의 정시마다(또는 `at` 한 시각) 경고를 준다 — 빈 칸을 묻는 것이라 묶음 없이 누구의 방문과도 겹친다. 옮기기 화면을 위해 `exclude`(옮길 방문)를 받는다. `/visits/calendar`·`/visits/slots`는 `/visits/{visit_id}`(Task 9)보다 먼저 붙인다.

**Files:**
- Create: `backend/apps/visit/domain/services/visit_board.py`
- Create: `backend/apps/visit/app/dtos/get_visit_calendar_dto.py`
- Create: `backend/apps/visit/app/dtos/list_day_visits_dto.py`
- Create: `backend/apps/visit/app/dtos/list_visit_slots_dto.py`
- Create: `backend/apps/visit/app/ports/input/get_visit_calendar_use_case.py`
- Create: `backend/apps/visit/app/ports/input/list_day_visits_use_case.py`
- Create: `backend/apps/visit/app/ports/input/list_visit_slots_use_case.py`
- Modify: `backend/apps/visit/app/ports/output/visit_repository.py`
- Create: `backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py`
- Create: `backend/apps/visit/app/use_cases/list_day_visits_interactor.py`
- Create: `backend/apps/visit/app/use_cases/list_visit_slots_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_calendar_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/list_visit_slots_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_visit_calendar_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/list_day_visits_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/list_visit_slots_router.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/dependencies/get_visit_calendar_provider.py`
- Create: `backend/apps/visit/dependencies/list_day_visits_provider.py`
- Create: `backend/apps/visit/dependencies/list_visit_slots_provider.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_get_visit_calendar_router.py`
- Test: `backend/apps/visit/tests/adapter/test_list_day_visits_router.py`
- Test: `backend/apps/visit/tests/adapter/test_list_visit_slots_router.py`
- Modify (test): `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_get_visit_calendar_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_list_visit_slots_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: Task 7 의 `VisitRepository`·`describe_visits`·`FakeVisits`
- Produces:
  - `VisitRepository.list_between(ctx, start, end)`, `unresolved_before(ctx, before) -> (int, datetime | None)`
  - `visit.domain.services.visit_board`: `COUNTED`, `is_unresolved(visit, today, tz)`, `overlaps_other_group(visit, occupied)`, `status_counts(visits)`
  - DTO `DayVisitsView`·`VisitCalendarView`·`VisitSlotsView`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_visit_calendar_router.py`:
```python
from datetime import date

from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
from visit.app.dtos.get_visit_calendar_dto import CalendarDayView, VisitCalendarView
from visit.dependencies.get_visit_calendar_provider import get_get_visit_calendar_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

CALENDAR = VisitCalendarView(
    year=2026, month=9,
    days=[CalendarDayView(date=date(2026, 9, 1), visit_count=3, completed_count=1, open_count=2,
                          unresolved_count=1, closed_day=False)],
    unresolved_total=4, oldest_unresolved_date=date(2026, 7, 14),
)


async def test_달은_YYYY_MM_으로_받는다():
    stub = Recorder(CALENDAR)
    async with client(build_app(get_visit_calendar_router, get_get_visit_calendar_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/calendar?month=2026-09")
        for bad in ("2026-9", "2026-13", "202609", ""):
            assert error_of(await c.get(f"/v1/shops/3/visits/calendar?month={bad}")) == (422, "VALIDATION_ERROR")
    body = response.json()
    assert (body["month"], body["unresolved_total"], body["oldest_unresolved_date"]) == (
        "2026-09", 4, "2026-07-14")
    assert body["days"][0] == {"date": "2026-09-01", "visit_count": 3, "completed_count": 1, "open_count": 2,
                               "unresolved_count": 1, "closed_day": False}
    assert (stub.calls[0].year, stub.calls[0].month) == (2026, 9)
```

`backend/apps/visit/tests/adapter/test_list_day_visits_router.py`:
```python
from datetime import date

from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
from visit.app.dtos.list_day_visits_dto import DayCountsView, DayVisitItemView, DayVisitsView
from visit.dependencies.list_day_visits_provider import get_list_day_visits_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

DAY = DayVisitsView(
    date=date(2026, 10, 2), closed_day=False,
    counts=DayCountsView(visit_count=1, reserved=1, in_progress=0, completed=0, canceled=0, no_show=0,
                         unresolved=0),
    items=[DayVisitItemView(visit=visit_view(), group_key="1:2026-10-02T05:00:00+00:00", overlapping=True,
                            unresolved=False)],
)


async def test_직원도_하루_목록을_본다():
    stub = Recorder(DAY)
    async with client(build_app(list_day_visits_router, get_list_day_visits_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits?date=2026-10-02")
        missing = await c.get("/v1/shops/3/visits")
    body = response.json()
    assert (body["date"], body["counts"]["visit_count"], body["items"][0]["overlapping"]) == (
        "2026-10-02", 1, True)
    assert body["items"][0]["visit"]["starts_at"] == "2026-10-02T14:00:00+09:00"
    assert stub.calls[0].day == date(2026, 10, 2)
    assert error_of(missing) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_list_visit_slots_router.py`:
```python
from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
from visit.app.dtos.list_visit_slots_dto import SlotView, VisitSlotsView
from visit.dependencies.list_visit_slots_provider import get_list_visit_slots_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

SLOTS = VisitSlotsView(
    date=date(2026, 10, 2), duration_minutes=90, closed_day=False,
    slots=[SlotView(starts_at=datetime(2026, 10, 2, 10, tzinfo=ZoneInfo("Asia/Seoul")), warnings=["overlap"])],
)


async def test_시간_칸_조회는_날짜_소요_시각_제외를_받는다():
    stub = Recorder(SLOTS)
    async with client(build_app(list_visit_slots_router, get_list_visit_slots_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/slots?date=2026-10-02&duration=90&at=14:10&exclude=7&exclude=8")
        plain = await c.get("/v1/shops/3/visits/slots?date=2026-10-02")
        bad = await c.get("/v1/shops/3/visits/slots?date=2026-10-02&exclude=0")
    assert response.json()["slots"] == [{"starts_at": "2026-10-02T10:00:00+09:00", "warnings": ["overlap"]}]
    query = stub.calls[0]
    assert (query.day, query.duration_minutes, query.at, query.exclude) == (date(2026, 10, 2), 90, time(14, 10), (7, 8))
    assert (stub.calls[1].duration_minutes, stub.calls[1].at, stub.calls[1].exclude) == (None, None, ())
    assert plain.status_code == 200
    assert error_of(bad) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py` (수정):
```diff
@@ -63,3 +63,26 @@ async def test_시간이_겹치는_살아_있는_방문만(db_session):
     assert [v.pet_id for v in occupied] == [102, 103]   # 전날 밤 방문은 딱 0시에 끝나 겹치지 않는다
     long_before = await repo.list_occupied(A, kst(10, 1, 23), kst(10, 1, 23) + timedelta(hours=1))
     assert [v.pet_id for v in long_before] == [101]
+
+
+async def test_시작_시각이_구간_안인_방문은_상태와_상관없이(db_session):
+    repo = VisitPgRepository(db_session)
+    await repo.create_many(A, [new(101, starts_at=kst(10, 2, 10))])
+    await repo.create_many(A, [new(102, starts_at=kst(10, 2, 10), status="in_progress",
+                                   started_at=kst(10, 2, 10))])
+    await repo.create_many(A, [new(103, starts_at=kst(10, 1, 23))])
+    await repo.create_many(B, [new(104, starts_at=kst(10, 2, 11))])
+    found = await repo.list_between(A, kst(10, 2), kst(10, 3))
+    assert [(v.pet_id, v.status) for v in found] == [(101, "reserved"), (102, "in_progress")]
+
+
+async def test_정리_안_된_예약의_수와_가장_이른_시각(db_session):
+    repo = VisitPgRepository(db_session)
+    await repo.create_many(A, [new(101, starts_at=kst(7, 14, 10))])
+    await repo.create_many(A, [new(102, starts_at=kst(9, 22, 10))])
+    await repo.create_many(A, [new(103, starts_at=kst(9, 21, 10), status="in_progress",
+                                   started_at=kst(9, 21, 10))])      # 미용 중은 정리 안 됨이 아니다
+    await repo.create_many(A, [new(104, starts_at=kst(9, 23, 10))])  # 오늘
+    await repo.create_many(B, [new(105, starts_at=kst(6, 1, 10))])
+    assert await repo.unresolved_before(A, kst(9, 23)) == (2, kst(7, 14, 10))
+    assert await repo.unresolved_before(A, kst(7, 1)) == (0, None)
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_calendar_interactor.py`:
```python
from datetime import date, time

import pytest

from visit.app.dtos.get_visit_calendar_dto import GetVisitCalendarQuery
from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.closed_date import ClosedDate
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeSchedule, FakeVisits

NOW = kst(9, 23, 15)


def _setup():
    visits = FakeVisits()
    schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 120, frozenset({0})))
    return visits, schedule, GetVisitCalendarInteractor(visits, schedule, now=lambda: NOW)


async def test_날마다_마릿수_완료_예약_정리_안_됨_휴무():
    visits, schedule, interactor = _setup()
    visits.seed(pet_id=101, starts_at=kst(9, 2, 10), status="completed", started_at=kst(9, 2, 10),
                completed_at=kst(9, 2, 11))
    visits.seed(pet_id=102, starts_at=kst(9, 2, 10))                                   # 정리 안 됨
    visits.seed(pet_id=103, starts_at=kst(9, 2, 12), status="no_show")                 # 마릿수에 안 든다
    visits.seed(pet_id=104, starts_at=kst(9, 25, 14))
    visits.seed(pet_id=105, starts_at=kst(10, 1, 0, 10))                                # 다음 달
    visits.seed(pet_id=106, starts_at=kst(8, 31, 23, 50), duration_minutes=10)          # 지난달 마지막 날
    schedule.closed[(1, date(2026, 9, 17))] = ClosedDate(day=date(2026, 9, 17), note=None)
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=9))
    assert len(view.days) == 30
    second, seventeenth, twenty_fifth = view.days[1], view.days[16], view.days[24]
    assert (second.visit_count, second.completed_count, second.open_count, second.unresolved_count) == (2, 1, 1, 1)
    assert (twenty_fifth.visit_count, twenty_fifth.open_count, twenty_fifth.unresolved_count) == (1, 1, 0)
    assert seventeenth.closed_day and view.days[6].closed_day   # 임시 휴무, 월요일(9/7)
    assert sum(d.visit_count for d in view.days) == 3


async def test_정리_안_된_예약은_달과_상관없이_매장_전체를_센다():
    visits, _, interactor = _setup()
    visits.seed(pet_id=101, starts_at=kst(7, 14, 10))
    visits.seed(pet_id=102, starts_at=kst(9, 22, 10))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 10))   # 오늘 — 아직 정리할 때가 아니다
    visits.seed(pet_id=104, starts_at=kst(7, 1, 10), shop_id=2)
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=10))
    assert (view.unresolved_total, view.oldest_unresolved_date) == (2, date(2026, 7, 14))


async def test_정리할_것이_없으면_가장_이른_날도_없다():
    _, _, interactor = _setup()
    view = await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=2026, month=9))
    assert (view.unresolved_total, view.oldest_unresolved_date) == (0, None)


@pytest.mark.parametrize(("year", "month"), [(2026, 13), (1999, 1)])
async def test_달이_이상하면_VALIDATION_ERROR_다(year, month):
    _, _, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx(), year=year, month=month))
```

`backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py`:
```python
from datetime import date, time

from visit.app.dtos.list_day_visits_dto import ListDayVisitsQuery
from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, FakeVisits

NOW = kst(9, 23, 15)


def _setup(settings=None):
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    directory.family(2, pets=(201,), name=None)   # 익명화한 고객
    schedule = FakeSchedule() if settings is None else FakeSchedule(settings=settings)
    interactor = ListDayVisitsInteractor(visits, FakeMenus(), schedule, directory, now=lambda: NOW)
    return visits, interactor


async def _day(interactor, day, shop_id=1):
    return await interactor.list_day_visits(ListDayVisitsQuery(ctx=ctx(shop_id=shop_id), day=day))


async def test_그날_시작하는_방문을_시작_순으로_상태별로_센다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 10), status="completed",
                started_at=kst(9, 23, 10), completed_at=kst(9, 23, 12))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13), status="in_progress", started_at=kst(9, 23, 13))
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 16), status="canceled", canceled_at=NOW,
                cancel_reason="customer_request")
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 24, 10))       # 다음 날
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 11), shop_id=2)   # 다른 매장
    day = await _day(interactor, date(2026, 9, 23))
    assert [(i.visit.pet.pet_id, i.visit.status) for i in day.items] == [
        (101, "completed"), (102, "in_progress"), (201, "canceled")]
    counts = day.counts
    assert (counts.visit_count, counts.completed, counts.in_progress, counts.canceled, counts.reserved) == (
        2, 1, 1, 1, 0)
    assert day.items[2].visit.customer.name is None   # 익명화한 고객은 이름 없이 틀만


async def test_가족_묶음과_다른_묶음과의_겹침():
    """13시 가족은 14시 다른 가족과 겹친다. 17시 가족은 형제끼리만 같은 시간을 차지해 겹침이 아니다."""
    visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 25, 13), duration_minutes=90)
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 25, 13), duration_minutes=90)
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 25, 14), duration_minutes=60)
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 25, 17), duration_minutes=60)
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 25, 17), duration_minutes=60)
    day = await _day(interactor, date(2026, 9, 25))
    keys = [i.group_key for i in day.items]
    assert keys[0] == keys[1] == f"1:{kong.starts_at.isoformat()}" != keys[2]
    assert keys[3] == keys[4] != keys[0]
    assert [i.overlapping for i in day.items] == [True, True, True, False, False]


async def test_지난_날의_예약됨은_정리_안_됨이다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 21, 10))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 21, 10), status="no_show")
    day = await _day(interactor, date(2026, 9, 21))
    assert [i.unresolved for i in day.items] == [True, False]
    assert day.counts.unresolved == 1
    today = await _day(interactor, date(2026, 9, 23))
    assert today.counts.unresolved == 0


async def test_휴무일을_알린다():
    _, interactor = _setup(ScheduleSettings(time(10), time(19), 120, frozenset({0})))
    assert (await _day(interactor, date(2026, 9, 28))).closed_day is True     # 월요일
    assert (await _day(interactor, date(2026, 9, 29))).closed_day is False
```

`backend/apps/visit/tests/app/use_cases/test_list_visit_slots_interactor.py`:
```python
from datetime import date, time

import pytest

from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery
from visit.app.use_cases.list_visit_slots_interactor import ListVisitSlotsInteractor
from visit.domain.errors import VisitInputError
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeSchedule, FakeVisits

DAY = date(2026, 10, 2)


def _setup(settings=ScheduleSettings(time(10), time(14), 120, frozenset())):
    visits = FakeVisits()
    return visits, ListVisitSlotsInteractor(visits, FakeSchedule(settings=settings))


def _query(**overrides):
    fields = dict(ctx=ctx(), day=DAY, duration_minutes=60, at=None, exclude=())
    fields.update(overrides)
    return ListVisitSlotsQuery(**fields)


async def test_영업시간의_정시마다_경고를_붙인다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 11), duration_minutes=60)
    view = await interactor.list_visit_slots(_query())
    assert [(s.starts_at.hour, s.warnings) for s in view.slots] == [
        (10, []), (11, ["overlap"]), (12, []), (13, [])]
    assert view.slots[0].starts_at.isoformat() == "2026-10-02T10:00:00+09:00"


async def test_같은_가족의_예약과도_겹친다고_알린다():
    """빈 칸을 묻는 것이라 묶음이 없다 — 시간을 차지한 방문이면 누구든 겹침이다."""
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 12))
    view = await interactor.list_visit_slots(_query())
    assert view.slots[2].warnings == ["overlap"]


async def test_옮길_방문은_빼고_본다():
    visits, interactor = _setup()
    mine = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 11), duration_minutes=60)
    view = await interactor.list_visit_slots(_query(exclude=(mine.id,)))
    assert all(s.warnings == [] for s in view.slots)


async def test_한_시각만_물을_수_있고_소요가_없으면_매장_기본이다():
    _, interactor = _setup()
    view = await interactor.list_visit_slots(_query(at=time(13, 10), duration_minutes=None))
    assert view.duration_minutes == 120
    assert [(s.starts_at.hour, s.starts_at.minute, s.warnings) for s in view.slots] == [
        (13, 10, ["outside_hours"])]


async def test_휴무일이면_모든_칸에_closed_day():
    _, interactor = _setup(ScheduleSettings(time(10), time(12), 120, frozenset({4})))   # 10/2 금요일
    view = await interactor.list_visit_slots(_query())
    assert view.closed_day and all("closed_day" in s.warnings for s in view.slots)


@pytest.mark.parametrize("fields", [dict(at=time(13, 5)), dict(duration_minutes=15)])
async def test_10분_단위가_아니면_VALIDATION_ERROR_다(fields):
    _, interactor = _setup()
    with pytest.raises(VisitInputError):
        await interactor.list_visit_slots(_query(**fields))
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -174,6 +174,16 @@ class FakeVisits:
         self.journal.append(("create_visits", [v.id for v in created]))
         return created
 
+    def _mine(self, ctx):
+        return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id), key=lambda v: (v.starts_at, v.id))
+
+    async def list_between(self, ctx, start, end):
+        return [v for v in self._mine(ctx) if start <= v.starts_at < end]
+
+    async def unresolved_before(self, ctx, before):
+        found = [v for v in self._mine(ctx) if v.status == "reserved" and v.starts_at < before]
+        return len(found), (found[0].starts_at if found else None)
+
     async def list_occupied(self, ctx, start, end):
         return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id and v.is_active
                        and v.starts_at < end and v.ends_at > start), key=lambda v: (v.starts_at, v.id))
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해 조회 테스트가 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/domain/services/visit_board.py`:
```python
"""하루 목록과 달력의 표시 — 정리 안 된 예약, 가족 묶음, 겹침, 상태별 수. 저장하지 않고 계산한다."""
from __future__ import annotations

from collections import Counter
from datetime import date

from visit.domain.entities.visit import COMPLETED, IN_PROGRESS, RESERVED, Visit
from visit.domain.services.visit_schedule import local_date

# 마릿수로 치는 상태 — 취소·노쇼는 그날 한 일이 아니다.
COUNTED = frozenset({RESERVED, IN_PROGRESS, COMPLETED})


def is_unresolved(visit: Visit, today: date, tz: str) -> bool:
    """지난 날(매장 시간대로 오늘 이전)인데 아직 예약됨 — 완료를 깜빡했거나 되돌린 방문이다."""
    return visit.status == RESERVED and local_date(visit.starts_at, tz) < today


def overlaps_other_group(visit: Visit, occupied: list[Visit]) -> bool:
    """살아 있는 방문이 다른 가족 묶음과 시간이 겹치는가. 끝난 방문(완료·취소·노쇼)은 겹침을 따지지 않는다."""
    return visit.is_active and any(
        o.id != visit.id and o.group_key != visit.group_key
        and o.starts_at < visit.ends_at and visit.starts_at < o.ends_at
        for o in occupied
    )


def status_counts(visits: list[Visit]) -> Counter:
    return Counter(v.status for v in visits)
```

`backend/apps/visit/app/dtos/get_visit_calendar_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class GetVisitCalendarQuery:
    ctx: ShopContext
    year: int
    month: int


@dataclass(frozen=True)
class CalendarDayView:
    date: date
    visit_count: int       # 마릿수 — 예약됨·미용 중·완료
    completed_count: int
    open_count: int        # 예약됨·미용 중
    unresolved_count: int  # 지난 날인데 아직 예약됨
    closed_day: bool


@dataclass(frozen=True)
class VisitCalendarView:
    year: int
    month: int
    days: list[CalendarDayView]            # 그달의 모든 날
    unresolved_total: int                  # 달과 상관없이 매장 전체
    oldest_unresolved_date: date | None
```

`backend/apps/visit/app/dtos/list_day_visits_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class ListDayVisitsQuery:
    ctx: ShopContext
    day: date   # 매장 시간대의 날짜


@dataclass(frozen=True)
class DayCountsView:
    visit_count: int   # 마릿수 — 예약됨·미용 중·완료
    reserved: int
    in_progress: int
    completed: int
    canceled: int
    no_show: int
    unresolved: int


@dataclass(frozen=True)
class DayVisitItemView:
    visit: VisitView
    group_key: str      # 가족 묶음 — 같은 값끼리 한 카드로 묶는다
    overlapping: bool   # 다른 묶음과 시간이 겹친다
    unresolved: bool    # 지난 날인데 아직 예약됨


@dataclass(frozen=True)
class DayVisitsView:
    date: date
    closed_day: bool
    counts: DayCountsView
    items: list[DayVisitItemView]
```

`backend/apps/visit/app/dtos/list_visit_slots_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from hub.app.dtos.shop_context import ShopContext


@dataclass(frozen=True)
class ListVisitSlotsQuery:
    """at 이 있으면 그 시각 한 칸만, 없으면 영업시간의 정시 칸마다. exclude 의 방문은 없는 것으로 친다(옮기기)."""

    ctx: ShopContext
    day: date
    duration_minutes: int | None
    at: time | None
    exclude: tuple[int, ...]


@dataclass(frozen=True)
class SlotView:
    starts_at: datetime        # 매장 시간대
    warnings: list[str]


@dataclass(frozen=True)
class VisitSlotsView:
    date: date
    duration_minutes: int
    closed_day: bool
    slots: list[SlotView]
```

`backend/apps/visit/app/ports/input/get_visit_calendar_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_calendar_dto import GetVisitCalendarQuery, VisitCalendarView


class GetVisitCalendarUseCase(ABC):
    @abstractmethod
    async def get_visit_calendar(self, query: GetVisitCalendarQuery) -> VisitCalendarView: ...
```

`backend/apps/visit/app/ports/input/list_day_visits_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_day_visits_dto import DayVisitsView, ListDayVisitsQuery


class ListDayVisitsUseCase(ABC):
    @abstractmethod
    async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView: ...
```

`backend/apps/visit/app/ports/input/list_visit_slots_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery, VisitSlotsView


class ListVisitSlotsUseCase(ABC):
    @abstractmethod
    async def list_visit_slots(self, query: ListVisitSlotsQuery) -> VisitSlotsView: ...
```

`backend/apps/visit/app/ports/output/visit_repository.py` (수정):
```diff
@@ -16,6 +16,14 @@ class VisitRepository(ABC):
         """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
         VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""
 
+    @abstractmethod
+    async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
+        """시작 시각이 [start, end) 인 방문 — 상태와 상관없이, 시작 순으로."""
+
+    @abstractmethod
+    async def unresolved_before(self, ctx: ShopContext, before: datetime) -> tuple[int, datetime | None]:
+        """시작 시각이 before 전인데 아직 예약됨인 방문(정리 안 된 예약)의 수와 가장 이른 시작 시각."""
+
     @abstractmethod
     async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
         """[start, end) 와 시간이 겹치는 살아 있는 방문(예약됨·미용 중)."""
```

`backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py`:
```python
from __future__ import annotations

import calendar
from collections import defaultdict
from collections.abc import Callable
from datetime import date, datetime

from visit.app.dtos.get_visit_calendar_dto import (
    CalendarDayView,
    GetVisitCalendarQuery,
    VisitCalendarView,
)
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_board import COUNTED, is_unresolved
from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date


class GetVisitCalendarInteractor(GetVisitCalendarUseCase):
    """월 달력 — 날마다 마릿수·완료·예약·정리 안 됨, 휴무. 위쪽 '정리 안 된 예약 N건'은 매장 전체다."""

    def __init__(
        self, visits: VisitRepository, schedule: ScheduleRepository, now: Callable[[], datetime]
    ) -> None:
        self._visits = visits
        self._schedule = schedule
        self._now = now

    async def get_visit_calendar(self, query: GetVisitCalendarQuery) -> VisitCalendarView:
        ctx, tz = query.ctx, query.ctx.timezone
        if not (1 <= query.month <= 12 and 2000 <= query.year <= 2100):
            raise VisitInputError("달이 올바르지 않습니다.")
        settings = await self._schedule.ensure(ctx)
        last = calendar.monthrange(query.year, query.month)[1]
        first_day, last_day = date(query.year, query.month, 1), date(query.year, query.month, last)
        start, _ = day_bounds(first_day, tz)
        _, end = day_bounds(last_day, tz)
        today = local_date(self._now(), tz)

        by_day = defaultdict(list)
        for visit in await self._visits.list_between(ctx, start, end):
            by_day[local_date(visit.starts_at, tz)].append(visit)
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, first_day, last_day))
        days = []
        for number in range(1, last + 1):
            day = date(query.year, query.month, number)
            visits = by_day[day]
            days.append(CalendarDayView(
                date=day,
                visit_count=sum(v.status in COUNTED for v in visits),
                completed_count=sum(v.status == COMPLETED for v in visits),
                open_count=sum(v.is_active for v in visits),
                unresolved_count=sum(is_unresolved(v, today, tz) for v in visits),
                closed_day=is_closed_day(day, settings, closed),
            ))
        today_start, _ = day_bounds(today, tz)
        total, oldest = await self._visits.unresolved_before(ctx, today_start)
        return VisitCalendarView(
            year=query.year, month=query.month, days=days, unresolved_total=total,
            oldest_unresolved_date=local_date(oldest, tz) if oldest else None,
        )
```

`backend/apps/visit/app/use_cases/list_day_visits_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.list_day_visits_dto import (
    DayCountsView,
    DayVisitItemView,
    DayVisitsView,
    ListDayVisitsQuery,
)
from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import CANCELED, COMPLETED, IN_PROGRESS, NO_SHOW, RESERVED
from visit.domain.services.visit_board import (
    COUNTED,
    is_unresolved,
    overlaps_other_group,
    status_counts,
)
from visit.domain.services.visit_schedule import day_bounds, is_closed_day, local_date


class ListDayVisitsInteractor(ListDayVisitsUseCase):
    """하루 화면 — 그날 시작하는 방문 전부(취소·노쇼 포함)를 시작 순으로."""

    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._now = now

    async def list_day_visits(self, query: ListDayVisitsQuery) -> DayVisitsView:
        ctx, tz, day = query.ctx, query.ctx.timezone, query.day
        settings = await self._schedule.ensure(ctx)
        start, end = day_bounds(day, tz)
        visits = await self._visits.list_between(ctx, start, end)
        occupied = await self._visits.list_occupied(ctx, start, end)   # 전날 밤에 시작한 방문도 겹칠 수 있다
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        today = local_date(self._now(), tz)
        views = await describe_visits(ctx, visits, self._directory, self._menus)
        items = [
            DayVisitItemView(
                visit=view,
                group_key=f"{visit.customer_id}:{visit.starts_at.isoformat()}",
                overlapping=overlaps_other_group(visit, occupied),
                unresolved=is_unresolved(visit, today, tz),
            )
            for visit, view in zip(visits, views)
        ]
        counts = status_counts(visits)
        return DayVisitsView(
            date=day,
            closed_day=is_closed_day(day, settings, closed),
            counts=DayCountsView(
                visit_count=sum(counts[s] for s in COUNTED), reserved=counts[RESERVED],
                in_progress=counts[IN_PROGRESS], completed=counts[COMPLETED], canceled=counts[CANCELED],
                no_show=counts[NO_SHOW], unresolved=sum(item.unresolved for item in items),
            ),
            items=items,
        )
```

`backend/apps/visit/app/use_cases/list_visit_slots_interactor.py`:
```python
from __future__ import annotations

from zoneinfo import ZoneInfo

from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery, SlotView, VisitSlotsView
from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.errors import VisitInputError
from visit.domain.services.visit_schedule import (
    STEP_MINUTES,
    Occupied,
    at_local,
    check_duration,
    day_bounds,
    hourly_starts,
    is_closed_day,
    warnings_for,
)


class ListVisitSlotsInteractor(ListVisitSlotsUseCase):
    """예약 ② 화면의 시간 칸. 경고 판단은 서버 한 곳에만 둔다 — 앱은 이 응답만 보고 줄을 긋는다(설계 6.3)."""

    def __init__(self, visits: VisitRepository, schedule: ScheduleRepository) -> None:
        self._visits = visits
        self._schedule = schedule

    async def list_visit_slots(self, query: ListVisitSlotsQuery) -> VisitSlotsView:
        ctx, tz, day = query.ctx, query.ctx.timezone, query.day
        settings = await self._schedule.ensure(ctx)
        duration = query.duration_minutes or settings.default_duration_minutes
        check_duration(duration)
        if query.at is not None and query.at.minute % STEP_MINUTES:
            raise VisitInputError("시각은 10분 단위여야 합니다.")
        start, end = day_bounds(day, tz)
        occupied = [
            Occupied(v.starts_at, v.ends_at, v.group_key)
            for v in await self._visits.list_occupied(ctx, start, end) if v.id not in query.exclude
        ]
        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
        starts = [at_local(day, query.at, tz)] if query.at is not None else hourly_starts(day, settings, tz)
        zone = ZoneInfo(tz)
        return VisitSlotsView(
            date=day, duration_minutes=duration, closed_day=is_closed_day(day, settings, closed),
            slots=[
                SlotView(starts_at=s.astimezone(zone),
                         warnings=warnings_for(s, duration, None, tz, settings, closed, occupied))
                for s in starts
            ],
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_calendar_schema.py`:
```python
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.app.dtos.get_visit_calendar_dto import VisitCalendarView


class CalendarDaySchema(BaseModel):
    date: date
    visit_count: int
    completed_count: int
    open_count: int
    unresolved_count: int
    closed_day: bool


class VisitCalendarSchema(BaseModel):
    month: str                 # 2026-09
    days: list[CalendarDaySchema]
    unresolved_total: int
    oldest_unresolved_date: date | None

    @classmethod
    def of(cls, view: VisitCalendarView) -> VisitCalendarSchema:
        return cls(
            month=f"{view.year:04d}-{view.month:02d}",
            days=[CalendarDaySchema.model_validate(d, from_attributes=True) for d in view.days],
            unresolved_total=view.unresolved_total, oldest_unresolved_date=view.oldest_unresolved_date,
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py`:
```python
from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.list_day_visits_dto import DayVisitsView


class DayCountsSchema(BaseModel):
    visit_count: int   # 마릿수 — 예약됨·미용 중·완료
    reserved: int
    in_progress: int
    completed: int
    canceled: int
    no_show: int
    unresolved: int


class DayVisitItemSchema(BaseModel):
    visit: VisitSchema
    group_key: str
    overlapping: bool
    unresolved: bool


class DayVisitsSchema(BaseModel):
    date: date
    closed_day: bool
    counts: DayCountsSchema
    items: list[DayVisitItemSchema]

    @classmethod
    def of(cls, view: DayVisitsView) -> DayVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/schemas/list_visit_slots_schema.py`:
```python
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from visit.app.dtos.list_visit_slots_dto import VisitSlotsView


class SlotSchema(BaseModel):
    starts_at: datetime        # 매장 시간대
    warnings: list[str]        # overlap · closed_day · outside_hours


class VisitSlotsSchema(BaseModel):
    date: date
    duration_minutes: int
    closed_day: bool
    slots: list[SlotSchema]

    @classmethod
    def of(cls, view: VisitSlotsView) -> VisitSlotsSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/get_visit_calendar_router.py`:
```python
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_calendar_schema import VisitCalendarSchema
from visit.app.dtos.get_visit_calendar_dto import GetVisitCalendarQuery
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.dependencies.get_visit_calendar_provider import get_get_visit_calendar_use_case

get_visit_calendar_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_calendar_router.get("/{shop_id}/visits/calendar", response_model=VisitCalendarSchema)
async def get_visit_calendar(
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitCalendarUseCase = Depends(get_get_visit_calendar_use_case),
) -> VisitCalendarSchema:
    year, number = (int(part) for part in month.split("-"))
    view = await use_case.get_visit_calendar(GetVisitCalendarQuery(ctx=ctx, year=year, month=number))
    return VisitCalendarSchema.of(view)
```

`backend/apps/visit/adapter/inbound/api/v1/list_day_visits_router.py`:
```python
from datetime import date

from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_day_visits_schema import DayVisitsSchema
from visit.app.dtos.list_day_visits_dto import ListDayVisitsQuery
from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
from visit.dependencies.list_day_visits_provider import get_list_day_visits_use_case

list_day_visits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@list_day_visits_router.get("/{shop_id}/visits", response_model=DayVisitsSchema)
async def list_day_visits(
    date: date,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListDayVisitsUseCase = Depends(get_list_day_visits_use_case),
) -> DayVisitsSchema:
    return DayVisitsSchema.of(await use_case.list_day_visits(ListDayVisitsQuery(ctx=ctx, day=date)))
```

`backend/apps/visit/adapter/inbound/api/v1/list_visit_slots_router.py`:
```python
from datetime import date, time
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.list_visit_slots_schema import VisitSlotsSchema
from visit.app.dtos.list_visit_slots_dto import ListVisitSlotsQuery
from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
from visit.dependencies.list_visit_slots_provider import get_list_visit_slots_use_case

list_visit_slots_router = APIRouter(prefix="/v1/shops", tags=["visits"])

_MAX_BIGINT = 9_223_372_036_854_775_807


@list_visit_slots_router.get("/{shop_id}/visits/slots", response_model=VisitSlotsSchema)
async def list_visit_slots(
    date: date,
    duration: int | None = None,
    at: time | None = None,
    exclude: Annotated[list[Annotated[int, Query(ge=1, le=_MAX_BIGINT)]], Query(max_length=10)] = [],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: ListVisitSlotsUseCase = Depends(get_list_visit_slots_use_case),
) -> VisitSlotsSchema:
    view = await use_case.list_visit_slots(
        ListVisitSlotsQuery(ctx=ctx, day=date, duration_minutes=duration, at=at, exclude=tuple(exclude))
    )
    return VisitSlotsSchema.of(view)
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py` (수정):
```diff
@@ -3,7 +3,7 @@ from __future__ import annotations
 from contextlib import asynccontextmanager
 from datetime import datetime, timedelta
 
-from sqlalchemy import insert, select
+from sqlalchemy import func, insert, select
 from sqlalchemy.exc import IntegrityError
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -11,7 +11,7 @@ from hub.app.dtos.shop_context import ShopContext
 from visit.adapter.outbound.mappers.visit_mapper import to_visit
 from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
 from visit.app.ports.output.visit_repository import VisitRepository
-from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
+from visit.domain.entities.visit import ACTIVE_STATUSES, RESERVED, Visit
 from visit.domain.errors import VisitDuplicateError
 from visit.domain.services.visit_schedule import MAX_DURATION
 from visit.domain.value_objects.new_visit import NewVisit
@@ -49,6 +49,22 @@ class VisitPgRepository(VisitRepository):
                 ids.append(visit_id)
         return await self._read(ctx, select(VisitOrm).where(VisitOrm.id.in_(ids)))
 
+    async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
+        return await self._read(
+            ctx, select(VisitOrm).where(VisitOrm.starts_at >= start, VisitOrm.starts_at < end)
+        )
+
+    async def unresolved_before(self, ctx: ShopContext, before: datetime) -> tuple[int, datetime | None]:
+        count, oldest = (
+            await self._session.execute(
+                select(func.count(), func.min(VisitOrm.starts_at)).where(
+                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.status == RESERVED,
+                    VisitOrm.starts_at < before,
+                )
+            )
+        ).one()
+        return count, oldest
+
     async def list_occupied(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
         # 소요는 최대 600분이라 그만큼 앞에서 시작한 방문까지 가져와 끝 시각으로 거른다.
         rows = await self._read(
```

`backend/apps/visit/dependencies/get_visit_calendar_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_visit_calendar_use_case import GetVisitCalendarUseCase
from visit.app.use_cases.get_visit_calendar_interactor import GetVisitCalendarInteractor
from visit.dependencies.visit_wiring import build_schedule_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_get_visit_calendar_use_case(db: DbSession) -> GetVisitCalendarUseCase:
    return GetVisitCalendarInteractor(
        visits=build_visit_repository(db), schedule=build_schedule_repository(db), now=utc_now
    )
```

`backend/apps/visit/dependencies/list_day_visits_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.list_day_visits_use_case import ListDayVisitsUseCase
from visit.app.use_cases.list_day_visits_interactor import ListDayVisitsInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_list_day_visits_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> ListDayVisitsUseCase:
    return ListDayVisitsInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
    )
```

`backend/apps/visit/dependencies/list_visit_slots_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.list_visit_slots_use_case import ListVisitSlotsUseCase
from visit.app.use_cases.list_visit_slots_interactor import ListVisitSlotsInteractor
from visit.dependencies.visit_wiring import build_schedule_repository, build_visit_repository


def get_list_visit_slots_use_case(db: DbSession) -> ListVisitSlotsUseCase:
    return ListVisitSlotsInteractor(visits=build_visit_repository(db), schedule=build_schedule_repository(db))
```

`backend/main.py` (수정):
```diff
@@ -61,9 +61,12 @@ from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_
 from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
 from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
 from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
+from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
 from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
+from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
+from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
@@ -121,6 +124,10 @@ app.include_router(list_menus_router)
 app.include_router(create_menu_router)
 app.include_router(update_menu_router)
 app.include_router(archive_menu_router)
+# /visits/calendar 와 /visits/slots 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
+app.include_router(get_visit_calendar_router)
+app.include_router(list_visit_slots_router)
+app.include_router(list_day_visits_router)
 app.include_router(register_visit_router)
 install_error_handlers(
     app,
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **562 passed**, 통합 **230 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `overlaps_other_group`의 `o.group_key != visit.group_key` 조건을 지운다 → `test_가족_묶음과_다른_묶음과의_겹침`이 실패한다(17시 형제끼리 겹침으로 나온다) — 되돌린다. 처음 쓴 이 테스트는 형제 묶음이 다른 가족과도 겹쳐 있어 이 변이로 실패하지 않았다 — 형제끼리만 같은 시간을 차지하는 17시 묶음을 더했다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/api/schemas/get_visit_calendar_schema.py backend/apps/visit/adapter/inbound/api/schemas/list_day_visits_schema.py backend/apps/visit/adapter/inbound/api/schemas/list_visit_slots_schema.py backend/apps/visit/adapter/inbound/api/v1/get_visit_calendar_router.py backend/apps/visit/adapter/inbound/api/v1/list_day_visits_router.py backend/apps/visit/adapter/inbound/api/v1/list_visit_slots_router.py backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py backend/apps/visit/app/dtos/get_visit_calendar_dto.py backend/apps/visit/app/dtos/list_day_visits_dto.py backend/apps/visit/app/dtos/list_visit_slots_dto.py backend/apps/visit/app/ports/input/get_visit_calendar_use_case.py backend/apps/visit/app/ports/input/list_day_visits_use_case.py backend/apps/visit/app/ports/input/list_visit_slots_use_case.py backend/apps/visit/app/ports/output/visit_repository.py backend/apps/visit/app/use_cases/get_visit_calendar_interactor.py backend/apps/visit/app/use_cases/list_day_visits_interactor.py backend/apps/visit/app/use_cases/list_visit_slots_interactor.py backend/apps/visit/dependencies/get_visit_calendar_provider.py backend/apps/visit/dependencies/list_day_visits_provider.py backend/apps/visit/dependencies/list_visit_slots_provider.py backend/apps/visit/domain/services/visit_board.py backend/apps/visit/tests/adapter/test_get_visit_calendar_router.py backend/apps/visit/tests/adapter/test_list_day_visits_router.py backend/apps/visit/tests/adapter/test_list_visit_slots_router.py backend/apps/visit/tests/adapter/test_visit_pg_repository.py backend/apps/visit/tests/app/use_cases/test_get_visit_calendar_interactor.py backend/apps/visit/tests/app/use_cases/test_list_day_visits_interactor.py backend/apps/visit/tests/app/use_cases/test_list_visit_slots_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/main.py
git commit -m "feat(visit): 하루 목록·월 달력·시간 칸 — 가족 묶음, 겹침, 정리 안 된 예약, 막지 않는 경고"
```

---

### Task 9: 방문 상세·수정·가족 한꺼번에 옮기기 — 고객 행 → 방문 행 잠금

방문을 쓰는 경로의 공통 순서를 `app/services/visit_locking.lock_visits`에 둔다: 이 매장의 방문인지(아니면 404), 같은 보호자의 방문인지(아니면 422 `VISIT_GROUP_MISMATCH`, V14) 확인 → 고객 행 잠금(허브 포트) → 방문 행 ID 오름차순 `FOR UPDATE` → 다시 읽기. 수정(PUT)은 통째로 바꾸되 날짜·시간·반려동물은 예약됨일 때만, 반려동물은 같은 보호자의 아이로만(V13) 바꾼다. 가족 확인에는 **새로 고른 아이만** 넘긴다 — 그대로인 아이를 넘기면 완료한 방문의 아이가 나중에 무지개다리를 건넌 경우 메모조차 못 고친다. 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다. 옮기기는 묶음 전부가 예약됨이어야 하고 전부 되거나 전부 안 된다(V6). 자정 넘김과 경고는 묶음에서 가장 긴 소요로 본다. 저장 뒤 경고는 `app/services/visit_warnings.warnings_after_save`로 모은다(등록도 이것을 쓰게 바꾼다). 상세는 같은 묶음의 다른 방문, 그 아이(보호자만이면 보호자)의 지난 완료 방문, 보호자의 노쇼 횟수를 준다.

**Files:**
- Create: `backend/apps/visit/app/dtos/get_visit_dto.py`
- Create: `backend/apps/visit/app/dtos/reschedule_visits_dto.py`
- Create: `backend/apps/visit/app/dtos/update_visit_dto.py`
- Create: `backend/apps/visit/app/ports/input/get_visit_use_case.py`
- Create: `backend/apps/visit/app/ports/input/reschedule_visits_use_case.py`
- Create: `backend/apps/visit/app/ports/input/update_visit_use_case.py`
- Modify: `backend/apps/visit/app/ports/output/visit_repository.py`
- Create: `backend/apps/visit/app/services/visit_locking.py`
- Create: `backend/apps/visit/app/services/visit_warnings.py`
- Create: `backend/apps/visit/app/use_cases/get_visit_interactor.py`
- Modify: `backend/apps/visit/app/use_cases/register_visit_interactor.py`
- Create: `backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`
- Create: `backend/apps/visit/app/use_cases/update_visit_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py`
- Modify: `backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/reschedule_visits_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/update_visit_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_visit_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/reschedule_visits_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/update_visit_router.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/dependencies/get_visit_provider.py`
- Create: `backend/apps/visit/dependencies/reschedule_visits_provider.py`
- Create: `backend/apps/visit/dependencies/update_visit_provider.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_get_visit_router.py`
- Test: `backend/apps/visit/tests/adapter/test_reschedule_visits_router.py`
- Test: `backend/apps/visit/tests/adapter/test_update_visit_router.py`
- Modify (test): `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`
- Test: `backend/apps/visit/tests/helpers/rows.py`

**Interfaces:**
- Consumes: Task 7·8 의 저장소와 조립 서비스
- Produces:
  - `VisitRepository`: `get(ctx, visit_id)`, `get_many(ctx, visit_ids)`, `lock(ctx, visit_ids)`, `update_details(ctx, visit_id, starts_at, pet_id, duration_minutes, menu_ids, memo)`, `reschedule(ctx, visit_ids, starts_at)`, `list_group(ctx, customer_id, starts_at)`, `last_completed_before(ctx, customer_id, pet_id, before)`, `count_no_show(ctx, customer_id)`
  - `visit.app.services.visit_locking.lock_visits(ctx, visit_ids, visits, directory, pet_ids=()) -> list[Visit]`
  - `visit.app.services.visit_warnings.warnings_after_save(ctx, customer_id, starts_at, duration_minutes, settings, visits, schedule) -> list[str]`
  - 테스트 도우미 `visit.tests.helpers.rows.insert_visit(session, starts_at, status=…, …)`(상태에 맞는 시각·사유 칸을 채워 바로 넣는다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_visit_router.py`:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
from visit.app.dtos.get_visit_dto import PreviousVisitView, VisitDetailView
from visit.dependencies.get_visit_provider import get_get_visit_use_case
from visit.domain.errors import VisitNotFoundError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

DETAIL = VisitDetailView(
    visit=visit_view(1), group=[visit_view(2)],
    previous_visit=PreviousVisitView(visit_id=7, starts_at=datetime(2026, 9, 2, 14, tzinfo=ZoneInfo("Asia/Seoul"))),
    no_show_count=1,
)


async def test_직원도_방문_상세를_본다():
    stub = Recorder(DETAIL)
    async with client(build_app(get_visit_router, get_get_visit_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/1")
    body = response.json()
    assert (body["visit"]["visit_id"], [v["visit_id"] for v in body["group"]], body["no_show_count"]) == (1, [2], 1)
    assert body["previous_visit"] == {"visit_id": 7, "starts_at": "2026-09-02T14:00:00+09:00"}
    assert stub.calls[0].visit_id == 1


async def test_없는_방문은_404_범위를_넘는_ID_는_422_다():
    stub = Recorder(error=VisitNotFoundError("없음"))
    async with client(build_app(get_visit_router, get_get_visit_use_case, stub)) as c:
        assert error_of(await c.get("/v1/shops/3/visits/9")) == (404, "VISIT_NOT_FOUND")
        assert error_of(await c.get("/v1/shops/3/visits/9223372036854775808")) == (422, "VALIDATION_ERROR")
```

`backend/apps/visit/tests/adapter/test_reschedule_visits_router.py`:
```python
from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView
from visit.dependencies.reschedule_visits_provider import get_reschedule_visits_use_case
from visit.domain.errors import VisitGroupMismatchError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

BODY = {"visit_ids": [1, 2], "starts_at": "2026-10-03T15:00:00+09:00"}


async def test_직원도_가족_예약을_함께_옮긴다():
    stub = Recorder(RescheduledVisitsView(visits=[visit_view(1), visit_view(2)], warnings=["overlap"]))
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, stub, STAFF)) as c:
        response = await c.post("/v1/shops/3/visits/reschedule", json=BODY)
    assert (len(response.json()["visits"]), response.json()["warnings"]) == (2, ["overlap"])
    assert stub.calls[0].visit_ids == (1, 2)


async def test_형식_권한_묶음_오류():
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, Recorder())) as c:
        for bad in ({**BODY, "visit_ids": []}, {**BODY, "visit_ids": [1, 1]}, {**BODY, "starts_at": "2026-10-03T15:00"}):
            assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=bad)) == (422, "VALIDATION_ERROR")
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, Recorder(), READ_ONLY)) as c:
        assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=BODY)) == (403, "PERMISSION_DENIED")
    stub = Recorder(error=VisitGroupMismatchError("섞임"))
    async with client(build_app(reschedule_visits_router, get_reschedule_visits_use_case, stub)) as c:
        assert error_of(await c.post("/v1/shops/3/visits/reschedule", json=BODY)) == (422, "VISIT_GROUP_MISMATCH")
```

`backend/apps/visit/tests/adapter/test_update_visit_router.py`:
```python
from datetime import datetime, timezone

from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
from visit.app.dtos.update_visit_dto import UpdatedVisitView
from visit.dependencies.update_visit_provider import get_update_visit_use_case
from visit.domain.errors import VisitStateConflictError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

BODY = {"starts_at": "2026-10-03T11:00:00+09:00", "pet_id": None, "duration_minutes": 60, "menu_ids": [],
        "memo": ""}


async def test_직원도_방문을_고친다():
    stub = Recorder(UpdatedVisitView(visit=visit_view(), warnings=[]))
    async with client(build_app(update_visit_router, get_update_visit_use_case, stub, STAFF)) as c:
        response = await c.put("/v1/shops/3/visits/1", json=BODY)
    assert response.status_code == 200
    command = stub.calls[0]
    assert (command.visit_id, command.pet_id, command.memo, command.starts_at) == (
        1, None, None, datetime(2026, 10, 3, 2, tzinfo=timezone.utc))


async def test_PUT_은_모든_칸을_받는다():
    async with client(build_app(update_visit_router, get_update_visit_use_case, Recorder())) as c:
        for key in BODY:
            partial = {k: v for k, v in BODY.items() if k != key}
            assert error_of(await c.put("/v1/shops/3/visits/1", json=partial)) == (422, "VALIDATION_ERROR"), key


async def test_권한과_상태_충돌():
    async with client(build_app(update_visit_router, get_update_visit_use_case, Recorder(), READ_ONLY)) as c:
        assert error_of(await c.put("/v1/shops/3/visits/1", json=BODY)) == (403, "PERMISSION_DENIED")
    stub = Recorder(error=VisitStateConflictError("완료"))
    async with client(build_app(update_visit_router, get_update_visit_use_case, stub)) as c:
        assert error_of(await c.put("/v1/shops/3/visits/1", json=BODY)) == (409, "VISIT_STATE_CONFLICT")
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py` (수정):
```diff
@@ -5,9 +5,10 @@ import pytest
 from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
-from visit.domain.errors import VisitDuplicateError
+from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
 from visit.domain.value_objects.new_visit import NewVisit
 from visit.tests.helpers.builders import ctx, kst
+from visit.tests.helpers.rows import insert_visit
 
 pytestmark = pytest.mark.integration
 
@@ -86,3 +87,53 @@ async def test_정리_안_된_예약의_수와_가장_이른_시각(db_session):
     await repo.create_many(B, [new(105, starts_at=kst(6, 1, 10))])
     assert await repo.unresolved_before(A, kst(9, 23)) == (2, kst(7, 14, 10))
     assert await repo.unresolved_before(A, kst(7, 1)) == (0, None)
+
+
+async def test_하나와_여럿을_읽고_다른_매장은_없다(db_session):
+    repo = VisitPgRepository(db_session)
+    [mine] = await repo.create_many(A, [new(101)])
+    [theirs] = await repo.create_many(B, [new(201)])
+    assert (await repo.get(A, mine.id)).pet_id == 101
+    with pytest.raises(VisitNotFoundError):
+        await repo.get(A, theirs.id)
+    assert [v.id for v in await repo.get_many(A, [mine.id, theirs.id])] == [mine.id]
+    assert [v.id for v in await repo.lock(A, [theirs.id, mine.id])] == [mine.id]
+
+
+async def test_세부를_통째로_바꾸고_메뉴도_바꾼다(db_session):
+    bath, trim, *_ = await _menu_ids(db_session)
+    repo = VisitPgRepository(db_session)
+    [visit] = await repo.create_many(A, [new(101, menu_ids=(bath,))])
+    changed = await repo.update_details(A, visit.id, kst(10, 3, 11), None, 60, (trim,), "발톱")
+    assert (changed.starts_at, changed.pet_id, changed.duration_minutes, changed.menu_ids, changed.memo) == (
+        kst(10, 3, 11), None, 60, (trim,), "발톱")
+    [other] = await repo.create_many(A, [new(102, starts_at=kst(10, 5, 10))])
+    with pytest.raises(VisitDuplicateError):
+        await repo.update_details(A, other.id, kst(10, 3, 11), None, 60, (), None)   # 보호자만의 같은 시각
+
+
+async def test_옮기기가_하나라도_겹치면_모두_되돌린다(db_session):
+    repo = VisitPgRepository(db_session)
+    kong, bori = await repo.create_many(A, [new(101), new(102)])
+    await repo.create_many(A, [new(102, starts_at=kst(10, 3, 15))])
+    with pytest.raises(VisitDuplicateError):
+        await repo.reschedule(A, [kong.id, bori.id], kst(10, 3, 15))
+    assert {v.starts_at for v in await repo.get_many(A, [kong.id, bori.id])} == {kst(10, 2, 14)}
+    moved = await repo.reschedule(A, [kong.id, bori.id], kst(10, 4, 15))
+    assert {v.starts_at for v in moved} == {kst(10, 4, 15)}
+
+
+async def test_묶음_지난_완료_노쇼_수(db_session):
+    repo = VisitPgRepository(db_session)
+    await insert_visit(db_session, kst(7, 1, 14), "completed")
+    await insert_visit(db_session, kst(8, 1, 14), "completed")
+    await insert_visit(db_session, kst(8, 20, 14), "completed", pet_id=None)
+    await insert_visit(db_session, kst(9, 1, 14), "no_show")
+    await insert_visit(db_session, kst(9, 1, 14), "no_show", shop_id=2)
+    await insert_visit(db_session, kst(9, 3, 14), "completed", customer_id=2, pet_id=201)
+    kong, bori = await repo.create_many(A, [new(101), new(102)])
+    assert [v.id for v in await repo.list_group(A, 1, kst(10, 2, 14))] == [kong.id, bori.id]
+    assert (await repo.last_completed_before(A, 1, 101, kst(10, 2, 14))).starts_at == kst(8, 1, 14)
+    assert (await repo.last_completed_before(A, 1, None, kst(10, 2, 14))).starts_at == kst(8, 20, 14)
+    assert await repo.last_completed_before(A, 1, 102, kst(10, 2, 14)) is None
+    assert await repo.count_no_show(A, 1) == 1
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py`:
```python
import pytest

from visit.app.dtos.get_visit_dto import GetVisitQuery
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.domain.errors import VisitNotFoundError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits


def _setup():
    visits, directory = FakeVisits(), FakeDirectory()
    directory.family(1, pets=(101, 102))
    return visits, GetVisitInteractor(visits, FakeMenus(), directory)


async def test_묶음_지난_방문_노쇼_횟수를_함께_준다():
    visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(8, 1, 14), status="completed",
                started_at=kst(8, 1, 14), completed_at=kst(8, 1, 15))
    last = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                       started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 10, 14), status="completed",
                started_at=kst(9, 10, 14), completed_at=kst(9, 10, 15))   # 형제의 방문은 지난 방문이 아니다
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 16, 14), status="no_show")
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert detail.visit.visit_id == kong.id
    assert [v.visit_id for v in detail.group] == [bori.id]
    assert (detail.previous_visit.visit_id, detail.previous_visit.starts_at.isoformat()) == (
        last.id, "2026-09-02T14:00:00+09:00")
    assert detail.no_show_count == 1


async def test_지난_방문이_없으면_비어_있다():
    visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    detail = await interactor.get_visit(GetVisitQuery(ctx=ctx(), visit_id=kong.id))
    assert (detail.group, detail.previous_visit, detail.no_show_count) == ([], None, 0)


async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    visits, interactor = _setup()
    theirs = visits.seed(shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.get_visit(GetVisitQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))
```

`backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py`:
```python
import pytest

from visit.app.dtos.reschedule_visits_dto import RescheduleVisitsCommand
from visit.app.use_cases.reschedule_visits_interactor import RescheduleVisitsInteractor
from visit.domain.errors import (
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotFoundError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeSchedule, FakeVisits, Journal

NOW = kst(9, 23, 15)


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102))
    directory.family(2, pets=(201,))
    return journal, visits, RescheduleVisitsInteractor(visits, FakeMenus(), FakeSchedule(), directory,
                                                       now=lambda: NOW)


def _move(ids, starts_at=kst(10, 3, 15), shop_id=1):
    return RescheduleVisitsCommand(ctx=ctx(shop_id=shop_id), visit_ids=tuple(ids), starts_at=starts_at)


async def test_가족_묶음을_함께_옮긴다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=90)
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=120)
    result = await interactor.reschedule_visits(_move([bori.id, kong.id]))
    assert [(v.visit_id, v.starts_at.isoformat()) for v in result.visits] == [
        (kong.id, "2026-10-03T15:00:00+09:00"), (bori.id, "2026-10-03T15:00:00+09:00")]
    assert result.warnings == []
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("lock_visits") < names.index("reschedule")


async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
    """V14"""
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 14))
    with pytest.raises(VisitGroupMismatchError):
        await interactor.reschedule_visits(_move([kong.id, other.id]))
    assert journal == []


async def test_예약됨이_아닌_방문이_있으면_하나도_옮기지_않는다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 14))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 14), status="in_progress",
                       started_at=kst(9, 23, 14))
    with pytest.raises(VisitStateConflictError):
        await interactor.reschedule_visits(_move([kong.id, bori.id]))
    assert "reschedule" not in [entry[0] for entry in journal]


async def test_가장_긴_소요로_자정_넘김을_본다():
    _, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=60)
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 2, 14), duration_minutes=180)
    with pytest.raises(VisitCrossesMidnightError):
        await interactor.reschedule_visits(_move([kong.id, bori.id], starts_at=kst(10, 3, 22)))


async def test_없는_방문_범위_밖_시각_중복():
    _, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 3, 15))
    with pytest.raises(VisitNotFoundError):
        await interactor.reschedule_visits(_move([kong.id, 999]))
    with pytest.raises(VisitInputError):
        await interactor.reschedule_visits(_move([kong.id], starts_at=kst(10, 3, 15, 5)))
    with pytest.raises(VisitDuplicateError):
        await interactor.reschedule_visits(_move([kong.id]))
    theirs = visits.seed(customer_id=9, shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.reschedule_visits(_move([theirs.id]))
```

`backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py`:
```python
import pytest

from visit.app.dtos.update_visit_dto import UpdateVisitCommand
from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
from visit.domain.errors import (
    MenuNotAvailableError,
    VisitCrossesMidnightError,
    VisitDuplicateError,
    VisitNotFoundError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import (
    FakeDirectory,
    FakeMenus,
    FakeSchedule,
    FakeVisits,
    FamilyRejected,
    Journal,
)

NOW = kst(9, 23, 15)


def _setup():
    journal = Journal()
    visits, menus, directory = FakeVisits(journal), FakeMenus(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102, 103), passed=(103,))
    directory.family(2, pets=(201,))
    interactor = UpdateVisitInteractor(visits, menus, FakeSchedule(), directory, now=lambda: NOW)
    return journal, visits, menus, interactor


def _command(visit, **overrides):
    fields = dict(ctx=ctx(), visit_id=visit.id, starts_at=visit.starts_at, pet_id=visit.pet_id,
                  duration_minutes=visit.duration_minutes, menu_ids=visit.menu_ids, memo=visit.memo)
    fields.update(overrides)
    return UpdateVisitCommand(**fields)


async def test_예약은_시간과_아이와_메뉴를_바꾼다():
    journal, visits, menus, interactor = _setup()
    bath = menus.seed("목욕")
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    result = await interactor.update_visit(_command(
        kong, starts_at=kst(10, 3, 11), pet_id=102, duration_minutes=60, menu_ids=(bath.id,), memo="발톱"))
    row = visits.rows[kong.id]
    assert (row.starts_at, row.pet_id, row.duration_minutes, row.menu_ids, row.memo) == (
        kst(10, 3, 11), 102, 60, (bath.id,), "발톱")
    assert result.warnings == []
    names = [entry[0] for entry in journal]
    assert names.index("lock_family") < names.index("lock_visits") < names.index("update_visit")
    assert ("lock_family", 1, (102,)) in journal   # 새로 고른 아이만 확인한다


async def test_다른_보호자의_아이로는_바꾸지_못한다():
    """V13 — 반려동물은 같은 보호자의 아이로만. 가족 확인이 거절한다."""
    journal, visits, _, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    with pytest.raises(FamilyRejected):
        await interactor.update_visit(_command(kong, pet_id=201))
    assert "update_visit" not in [entry[0] for entry in journal]


async def test_완료한_방문은_메모와_메뉴만_고친다():
    _, visits, menus, interactor = _setup()
    bath = menus.seed("목욕")
    done = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 2, 14), status="completed",
                       started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))   # 그 뒤 무지개다리를 건넌 아이
    result = await interactor.update_visit(_command(done, menu_ids=(bath.id,), memo="귀 청소도 함"))
    assert (result.visit.memo, result.warnings) == ("귀 청소도 함", [])
    for moved in (dict(starts_at=kst(9, 2, 15)), dict(pet_id=101)):
        with pytest.raises(VisitStateConflictError):
            await interactor.update_visit(_command(done, **moved))


async def test_이미_붙은_메뉴는_보관됐어도_둘_수_있다():
    _, visits, menus, interactor = _setup()
    old = menus.seed("옛 메뉴", archived=True)
    other_old = menus.seed("다른 옛 메뉴", archived=True)
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14), menu_ids=(old.id,))
    await interactor.update_visit(_command(kong, memo="그대로"))
    with pytest.raises(MenuNotAvailableError):
        await interactor.update_visit(_command(kong, menu_ids=(old.id, other_old.id)))


async def test_시각_규칙과_중복():
    _, visits, _, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 9, 14))
    with pytest.raises(VisitCrossesMidnightError):
        await interactor.update_visit(_command(kong, starts_at=kst(10, 2, 23), duration_minutes=120))
    with pytest.raises(VisitDuplicateError):
        await interactor.update_visit(_command(kong, starts_at=kst(10, 9, 14)))


async def test_다른_매장의_방문은_VISIT_NOT_FOUND_다():
    _, visits, _, interactor = _setup()
    theirs = visits.seed(shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.update_visit(_command(theirs))


async def test_경고를_함께_돌려준다():
    _, visits, _, interactor = _setup()
    visits.seed(customer_id=2, pet_id=201, starts_at=kst(10, 2, 11))
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    result = await interactor.update_visit(_command(kong, starts_at=kst(10, 2, 11)))
    assert result.warnings == ["overlap"]
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -7,7 +7,12 @@ from decimal import Decimal
 from hub.app.dtos.family_brief import CustomerBrief, FamilyBriefs, PetBrief
 from visit.domain.entities.menu import Menu
 from visit.domain.entities.visit import ACTIVE_STATUSES, Visit
-from visit.domain.errors import MenuNameTakenError, MenuNotFoundError, VisitDuplicateError
+from visit.domain.errors import (
+    MenuNameTakenError,
+    MenuNotFoundError,
+    VisitDuplicateError,
+    VisitNotFoundError,
+)
 from visit.domain.value_objects.closed_date import ClosedDate
 from visit.domain.value_objects.schedule_settings import DEFAULT_SETTINGS
 from visit.tests.helpers.builders import kst
@@ -174,6 +179,52 @@ class FakeVisits:
         self.journal.append(("create_visits", [v.id for v in created]))
         return created
 
+    def _owned(self, ctx, visit_id):
+        row = self.rows.get(visit_id)
+        if row is None or row.shop_id != ctx.shop_id:
+            raise VisitNotFoundError("방문을 찾을 수 없습니다.")
+        return row
+
+    async def get(self, ctx, visit_id):
+        return self._owned(ctx, visit_id)
+
+    async def get_many(self, ctx, visit_ids):
+        return [v for v in self._mine(ctx) if v.id in visit_ids]
+
+    async def lock(self, ctx, visit_ids):
+        found = [v for v in self._mine(ctx) if v.id in visit_ids]
+        self.journal.append(("lock_visits", sorted(v.id for v in found)))
+        return found
+
+    async def update_details(self, ctx, visit_id, starts_at, pet_id, duration_minutes, menu_ids, memo):
+        current = self._owned(ctx, visit_id)
+        if current.is_active and self._clash(ctx, current.customer_id, pet_id, starts_at, ignore=(visit_id,)):
+            raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
+        self.rows[visit_id] = replace(current, starts_at=starts_at, pet_id=pet_id,
+                                      duration_minutes=duration_minutes, menu_ids=menu_ids, memo=memo)
+        self.journal.append(("update_visit", visit_id))
+        return self.rows[visit_id]
+
+    async def reschedule(self, ctx, visit_ids, starts_at):
+        moving = [self._owned(ctx, i) for i in visit_ids]
+        if any(self._clash(ctx, v.customer_id, v.pet_id, starts_at, ignore=tuple(visit_ids)) for v in moving):
+            raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
+        for v in moving:
+            self.rows[v.id] = replace(v, starts_at=starts_at)
+        self.journal.append(("reschedule", sorted(visit_ids)))
+        return [self.rows[i] for i in sorted(visit_ids)]
+
+    async def list_group(self, ctx, customer_id, starts_at):
+        return [v for v in self._mine(ctx) if v.customer_id == customer_id and v.starts_at == starts_at]
+
+    async def last_completed_before(self, ctx, customer_id, pet_id, before):
+        found = [v for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
+                 and v.status == "completed" and v.starts_at < before]
+        return found[-1] if found else None
+
+    async def count_no_show(self, ctx, customer_id):
+        return sum(v.customer_id == customer_id and v.status == "no_show" for v in self._mine(ctx))
+
     def _mine(self, ctx):
         return sorted((v for v in self.rows.values() if v.shop_id == ctx.shop_id), key=lambda v: (v.starts_at, v.id))
```

`backend/apps/visit/tests/helpers/rows.py`:
```python
"""통합 테스트가 방문 행을 상태째 바로 넣는 도우미 — 상태에 맞는 시각·사유 칸을 채운다(CHECK 제약)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from visit.adapter.outbound.orm.visit_orm import VisitOrm


async def insert_visit(
    session: AsyncSession, starts_at: datetime, status: str = "reserved", shop_id: int = 1,
    customer_id: int = 1, pet_id: int | None = 101, duration_minutes: int = 90, memo: str | None = None,
) -> int:
    started = starts_at if status in ("in_progress", "completed") else None
    return (
        await session.execute(
            insert(VisitOrm)
            .values(
                shop_id=shop_id, customer_id=customer_id, pet_id=pet_id, starts_at=starts_at,
                duration_minutes=duration_minutes, status=status, started_at=started,
                completed_at=starts_at if status == "completed" else None,
                canceled_at=starts_at if status == "canceled" else None,
                cancel_reason="customer_request" if status == "canceled" else None,
                memo=memo, created_by_member_id=11,
            )
            .returning(VisitOrm.id)
        )
    ).scalar_one()
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해 상세·수정·옮기기 테스트가 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/dtos/get_visit_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class GetVisitQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class PreviousVisitView:
    visit_id: int
    starts_at: datetime   # 매장 시간대


@dataclass(frozen=True)
class VisitDetailView:
    visit: VisitView
    group: list[VisitView]                 # 같은 묶음의 다른 방문(같은 보호자 + 같은 시작 시각)
    previous_visit: PreviousVisitView | None   # 그 아이(보호자만이면 보호자)의 지난 완료 방문
    no_show_count: int                     # 이 보호자의 노쇼 횟수
```

`backend/apps/visit/app/dtos/reschedule_visits_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class RescheduleVisitsCommand:
    """같은 보호자의 예약 여러 개(가족 묶음)를 한 시각으로 함께 옮긴다. 전부 되거나 전부 안 된다."""

    ctx: ShopContext
    visit_ids: tuple[int, ...]
    starts_at: datetime


@dataclass(frozen=True)
class RescheduledVisitsView:
    visits: list[VisitView]
    warnings: list[str]
```

`backend/apps/visit/app/dtos/update_visit_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class UpdateVisitCommand:
    """방문 하나를 통째로 바꾼다(PUT). 날짜·시간·반려동물은 예약됨일 때만, 반려동물은 같은 보호자의 아이로만
    바꿀 수 있다. 메뉴·소요·메모는 미용 중·완료일 때도 바꾼다(실제로 한 메뉴를 ④ 기록이 쓴다)."""

    ctx: ShopContext
    visit_id: int
    starts_at: datetime
    pet_id: int | None
    duration_minutes: int
    menu_ids: tuple[int, ...]
    memo: str | None


@dataclass(frozen=True)
class UpdatedVisitView:
    visit: VisitView
    warnings: list[str]
```

`backend/apps/visit/app/ports/input/get_visit_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_dto import GetVisitQuery, VisitDetailView


class GetVisitUseCase(ABC):
    @abstractmethod
    async def get_visit(self, query: GetVisitQuery) -> VisitDetailView: ...
```

`backend/apps/visit/app/ports/input/reschedule_visits_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand


class RescheduleVisitsUseCase(ABC):
    @abstractmethod
    async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView: ...
```

`backend/apps/visit/app/ports/input/update_visit_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand


class UpdateVisitUseCase(ABC):
    @abstractmethod
    async def update_visit(self, command: UpdateVisitCommand) -> UpdatedVisitView: ...
```

`backend/apps/visit/app/ports/output/visit_repository.py` (수정):
```diff
@@ -16,6 +16,43 @@ class VisitRepository(ABC):
         """한 번에 넣는다. 같은 반려동물(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약이 이미 있으면
         VisitDuplicateError — 세이브포인트라 트랜잭션은 계속 쓸 수 있다."""
 
+    @abstractmethod
+    async def get(self, ctx: ShopContext, visit_id: int) -> Visit:
+        """없거나 다른 매장이면 VisitNotFoundError."""
+
+    @abstractmethod
+    async def get_many(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
+        """이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""
+
+    @abstractmethod
+    async def lock(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
+        """방문 행을 ID 오름차순으로 FOR UPDATE 잠그고 다시 읽는다. 고객 행을 잠근 **뒤에** 부른다(설계 4.2).
+        이 매장의 것만 돌려준다 — 모자라면 부르는 쪽이 없는 것으로 본다."""
+
+    @abstractmethod
+    async def update_details(
+        self, ctx: ShopContext, visit_id: int, starts_at: datetime, pet_id: int | None,
+        duration_minutes: int, menu_ids: tuple[int, ...], memo: str | None,
+    ) -> Visit:
+        """메뉴는 통째로 바꾼다. 중복 예약이 되면 VisitDuplicateError."""
+
+    @abstractmethod
+    async def reschedule(self, ctx: ShopContext, visit_ids: list[int], starts_at: datetime) -> list[Visit]:
+        """여러 방문의 시작 시각을 한 번에 바꾼다. 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""
+
+    @abstractmethod
+    async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
+        """같은 가족 묶음(같은 보호자 + 같은 시작 시각)의 방문 — 상태와 상관없이."""
+
+    @abstractmethod
+    async def last_completed_before(
+        self, ctx: ShopContext, customer_id: int, pet_id: int | None, before: datetime
+    ) -> Visit | None:
+        """before 전에 시작한 마지막 완료 방문. pet_id 가 있으면 그 아이의, 없으면 보호자만의 방문 가운데서."""
+
+    @abstractmethod
+    async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int: ...
+
     @abstractmethod
     async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
         """시작 시각이 [start, end) 인 방문 — 상태와 상관없이, 시작 순으로."""
```

`backend/apps/visit/app/services/visit_locking.py`:
```python
"""방문을 쓰는 유스케이스의 공통 순서 — 고객 행(허브 포트) → 방문 행(ID 오름차순) 잠금 뒤 다시 읽기(설계 4.2)."""
from __future__ import annotations

from hub.app.dtos.shop_context import ShopContext
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import Visit
from visit.domain.errors import VisitGroupMismatchError, VisitNotFoundError


async def lock_visits(
    ctx: ShopContext, visit_ids: list[int], visits: VisitRepository, directory: CustomerDirectoryPort,
    pet_ids: tuple[int, ...] = (),
) -> list[Visit]:
    """visit_ids 의 방문을 잠그고 다시 읽은 목록(ID 순)을 돌려준다.

    모두 이 매장의 방문이어야 하고(아니면 VISIT_NOT_FOUND), 같은 보호자의 방문이어야 한다(아니면
    VISIT_GROUP_MISMATCH). pet_ids 는 가족 확인에 넘길 반려동물 — 새로 시간을 차지하게 되는 아이만 넘긴다.
    """
    found = await visits.get_many(ctx, visit_ids)
    if len(found) != len(set(visit_ids)):
        raise VisitNotFoundError("방문을 찾을 수 없습니다.")
    customers = {v.customer_id for v in found}
    if len(customers) != 1:
        raise VisitGroupMismatchError("같은 보호자의 방문만 한 번에 다룰 수 있습니다.")
    await directory.lock_family(ctx, customers.pop(), pet_ids)
    return sorted(await visits.lock(ctx, visit_ids), key=lambda v: v.id)
```

`backend/apps/visit/app/services/visit_warnings.py`:
```python
"""저장한 뒤 돌려줄 경고(설계 6.3) — 겹침·휴무·영업시간 밖. 막지 않는다."""
from __future__ import annotations

from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.services.visit_schedule import Occupied, day_bounds, local_date, warnings_for
from visit.domain.value_objects.schedule_settings import ScheduleSettings


async def warnings_after_save(
    ctx: ShopContext, customer_id: int, starts_at: datetime, duration_minutes: int, settings: ScheduleSettings,
    visits: VisitRepository, schedule: ScheduleRepository,
) -> list[str]:
    """방금 저장한 묶음(같은 보호자 + 같은 시작 시각)의 경고. 저장한 방문 자신은 같은 묶음이라 겹침에서 빠진다."""
    tz = ctx.timezone
    day = local_date(starts_at, tz)
    start, end = day_bounds(day, tz)
    occupied = [Occupied(v.starts_at, v.ends_at, v.group_key) for v in await visits.list_occupied(ctx, start, end)]
    closed = frozenset(c.day for c in await schedule.list_closed_dates(ctx, day, day))
    return warnings_for(starts_at, duration_minutes, (customer_id, starts_at), tz, settings, closed, occupied)
```

`backend/apps/visit/app/use_cases/get_visit_interactor.py`:
```python
from __future__ import annotations

from zoneinfo import ZoneInfo

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.get_visit_dto import GetVisitQuery, PreviousVisitView, VisitDetailView
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_reader import describe_visits


class GetVisitInteractor(GetVisitUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, directory: CustomerDirectoryPort
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._directory = directory

    async def get_visit(self, query: GetVisitQuery) -> VisitDetailView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        group = [v for v in await self._visits.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.id != visit.id]
        previous = await self._visits.last_completed_before(ctx, visit.customer_id, visit.pet_id, visit.starts_at)
        [view, *group_views] = await describe_visits(ctx, [visit, *group], self._directory, self._menus)
        return VisitDetailView(
            visit=view,
            group=group_views,
            previous_visit=PreviousVisitView(
                visit_id=previous.id, starts_at=previous.starts_at.astimezone(ZoneInfo(ctx.timezone))
            ) if previous else None,
            no_show_count=await self._visits.count_no_show(ctx, visit.customer_id),
        )
```

`backend/apps/visit/app/use_cases/register_visit_interactor.py` (수정):
```diff
@@ -10,17 +10,14 @@ from visit.app.ports.output.menu_repository import MenuRepository
 from visit.app.ports.output.schedule_repository import ScheduleRepository
 from visit.app.ports.output.visit_repository import VisitRepository
 from visit.app.services.visit_reader import describe_visits
+from visit.app.services.visit_warnings import warnings_after_save
 from visit.domain.entities.visit import IN_PROGRESS, RESERVED
 from visit.domain.errors import MenuNotAvailableError, VisitInputError
 from visit.domain.services.visit_schedule import (
-    Occupied,
     check_duration,
     check_same_day,
     check_start,
-    day_bounds,
     floor_to_step,
-    local_date,
-    warnings_for,
 )
 from visit.domain.value_objects.new_visit import NewVisit
 
@@ -69,13 +66,9 @@ class RegisterVisitInteractor(RegisterVisitUseCase):
             ],
         )
 
-        day = local_date(starts_at, tz)
-        start, end = day_bounds(day, tz)
-        occupied = [Occupied(v.starts_at, v.ends_at, v.group_key)
-                    for v in await self._visits.list_occupied(ctx, start, end)]
-        closed = frozenset(c.day for c in await self._schedule.list_closed_dates(ctx, day, day))
-        warnings = warnings_for(starts_at, duration, (command.customer_id, starts_at), tz, settings, closed,
-                                occupied)
+        warnings = await warnings_after_save(
+            ctx, command.customer_id, starts_at, duration, settings, self._visits, self._schedule
+        )
         return RegisteredVisitsView(
             visits=await describe_visits(ctx, created, self._directory, self._menus), warnings=warnings
         )
```

`backend/apps/visit/app/use_cases/reschedule_visits_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView, RescheduleVisitsCommand
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_schedule import check_same_day, check_start


class RescheduleVisitsInteractor(RescheduleVisitsUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._now = now

    async def reschedule_visits(self, command: RescheduleVisitsCommand) -> RescheduledVisitsView:
        ctx, tz = command.ctx, command.ctx.timezone
        check_start(command.starts_at, self._now(), tz)
        locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory)
        if any(v.status != RESERVED for v in locked):
            raise VisitStateConflictError("예약됨인 방문만 옮길 수 있습니다.")
        longest = max(v.duration_minutes for v in locked)
        check_same_day(command.starts_at, longest, tz)
        moved = await self._visits.reschedule(ctx, [v.id for v in locked], command.starts_at)
        settings = await self._schedule.ensure(ctx)
        warnings = await warnings_after_save(
            ctx, locked[0].customer_id, command.starts_at, longest, settings, self._visits, self._schedule
        )
        return RescheduledVisitsView(
            visits=await describe_visits(ctx, moved, self._directory, self._menus), warnings=warnings
        )
```

`backend/apps/visit/app/use_cases/update_visit_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.update_visit_dto import UpdatedVisitView, UpdateVisitCommand
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.app.services.visit_warnings import warnings_after_save
from visit.domain.entities.visit import RESERVED
from visit.domain.errors import MenuNotAvailableError, VisitStateConflictError
from visit.domain.services.visit_schedule import check_duration, check_same_day, check_start


class UpdateVisitInteractor(UpdateVisitUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository,
        directory: CustomerDirectoryPort, now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule
        self._directory = directory
        self._now = now

    async def update_visit(self, command: UpdateVisitCommand) -> UpdatedVisitView:
        ctx, tz = command.ctx, command.ctx.timezone
        check_duration(command.duration_minutes)
        # 새로 고른 아이만 가족 확인에 넘긴다(같은 보호자의 아이인지, 무지개다리가 아닌지 — V13).
        # 그대로인 아이는 넘기지 않는다 — 완료한 방문의 아이가 나중에 무지개다리를 건넜어도 메모는 고친다.
        before = await self._visits.get(ctx, command.visit_id)
        changed_pet = command.pet_id is not None and command.pet_id != before.pet_id
        new_pet = (command.pet_id,) if changed_pet else ()
        [current] = await lock_visits(ctx, [command.visit_id], self._visits, self._directory, new_pet)
        if current.pet_id != before.pet_id:
            raise VisitStateConflictError("다른 기기가 먼저 방문을 바꿨습니다. 다시 불러와 주세요.")

        moved = command.starts_at != current.starts_at or command.pet_id != current.pet_id
        if moved and current.status != RESERVED:
            raise VisitStateConflictError("날짜·시간·반려동물은 예약됨일 때만 바꿀 수 있습니다.")
        if command.starts_at != current.starts_at:
            check_start(command.starts_at, self._now(), tz)
        check_same_day(command.starts_at, command.duration_minutes, tz)
        # 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다(완료한 방문의 메모만 고치는 경우).
        chosen = set(command.menu_ids)
        allowed = {m.id for m in await self._menus.list_active_by_ids(ctx, list(chosen))} | set(current.menu_ids)
        if not chosen <= allowed:
            raise MenuNotAvailableError("고를 수 없는 메뉴가 있습니다.")

        updated = await self._visits.update_details(
            ctx, current.id, command.starts_at, command.pet_id, command.duration_minutes, command.menu_ids,
            command.memo,
        )
        warnings = []
        if updated.is_active:
            settings = await self._schedule.ensure(ctx)
            warnings = await warnings_after_save(
                ctx, updated.customer_id, updated.starts_at, updated.duration_minutes, settings, self._visits,
                self._schedule,
            )
        [view] = await describe_visits(ctx, [updated], self._directory, self._menus)
        return UpdatedVisitView(visit=view, warnings=warnings)
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py`:
```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.get_visit_dto import VisitDetailView


class PreviousVisitSchema(BaseModel):
    visit_id: int
    starts_at: datetime


class VisitDetailSchema(BaseModel):
    visit: VisitSchema
    group: list[VisitSchema]
    previous_visit: PreviousVisitSchema | None
    no_show_count: int

    @classmethod
    def of(cls, view: VisitDetailView) -> VisitDetailSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py` (수정):
```diff
@@ -26,7 +26,7 @@ Memo = Annotated[
 ] | None
 
 
-def _unique(ids: list[int]) -> list[int]:
+def unique_ids(ids: list[int]) -> list[int]:
     if len(set(ids)) != len(ids):
         raise ValueError("같은 ID 를 두 번 보낼 수 없습니다.")
     return ids
@@ -44,7 +44,7 @@ class RegisterVisitRequestSchema(BaseModel):
     memo: Memo = None
     walk_in: StrictBool = False
 
-    _pets_unique = field_validator("pet_ids", "menu_ids")(_unique)
+    _pets_unique = field_validator("pet_ids", "menu_ids")(unique_ids)
 
 
 class RegisteredVisitsSchema(BaseModel):
```

`backend/apps/visit/adapter/inbound/api/schemas/reschedule_visits_schema.py`:
```python
from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, unique_ids
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.reschedule_visits_dto import RescheduledVisitsView


class RescheduleVisitsRequestSchema(BaseModel):
    visit_ids: Annotated[list[EntityId], Field(min_length=1, max_length=10)]
    starts_at: AwareDatetime

    _ids_unique = field_validator("visit_ids")(unique_ids)


class RescheduledVisitsSchema(BaseModel):
    visits: list[VisitSchema]
    warnings: list[str]

    @classmethod
    def of(cls, view: RescheduledVisitsView) -> RescheduledVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/schemas/update_visit_schema.py`:
```python
from __future__ import annotations

from typing import Annotated

from pydantic import AwareDatetime, BaseModel, Field, StrictInt, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, Memo, unique_ids
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.update_visit_dto import UpdatedVisitView


class UpdateVisitRequestSchema(BaseModel):
    """PUT — 모든 칸을 보낸다. pet_id 가 null 이면 보호자만의 방문이다."""

    starts_at: AwareDatetime
    pet_id: EntityId | None
    duration_minutes: StrictInt
    menu_ids: Annotated[list[EntityId], Field(max_length=10)]
    memo: Memo

    _menus_unique = field_validator("menu_ids")(unique_ids)


class UpdatedVisitSchema(BaseModel):
    visit: VisitSchema
    warnings: list[str]

    @classmethod
    def of(cls, view: UpdatedVisitView) -> UpdatedVisitSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/get_visit_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_visit_schema import VisitDetailSchema
from visit.app.dtos.get_visit_dto import GetVisitQuery
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.dependencies.get_visit_provider import get_get_visit_use_case

get_visit_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_router.get("/{shop_id}/visits/{visit_id}", response_model=VisitDetailSchema)
async def get_visit(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitUseCase = Depends(get_get_visit_use_case),
) -> VisitDetailSchema:
    return VisitDetailSchema.of(await use_case.get_visit(GetVisitQuery(ctx=ctx, visit_id=visit_id)))
```

`backend/apps/visit/adapter/inbound/api/v1/reschedule_visits_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.reschedule_visits_schema import (
    RescheduledVisitsSchema,
    RescheduleVisitsRequestSchema,
)
from visit.app.dtos.reschedule_visits_dto import RescheduleVisitsCommand
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.dependencies.reschedule_visits_provider import get_reschedule_visits_use_case

reschedule_visits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@reschedule_visits_router.post("/{shop_id}/visits/reschedule", response_model=RescheduledVisitsSchema)
async def reschedule_visits(
    body: RescheduleVisitsRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: RescheduleVisitsUseCase = Depends(get_reschedule_visits_use_case),
) -> RescheduledVisitsSchema:
    view = await use_case.reschedule_visits(
        RescheduleVisitsCommand(ctx=ctx, visit_ids=tuple(body.visit_ids), starts_at=body.starts_at)
    )
    return RescheduledVisitsSchema.of(view)
```

`backend/apps/visit/adapter/inbound/api/v1/update_visit_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.update_visit_schema import UpdatedVisitSchema, UpdateVisitRequestSchema
from visit.app.dtos.update_visit_dto import UpdateVisitCommand
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.dependencies.update_visit_provider import get_update_visit_use_case

update_visit_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@update_visit_router.put("/{shop_id}/visits/{visit_id}", response_model=UpdatedVisitSchema)
async def update_visit(
    visit_id: VisitId,
    body: UpdateVisitRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: UpdateVisitUseCase = Depends(get_update_visit_use_case),
) -> UpdatedVisitSchema:
    view = await use_case.update_visit(
        UpdateVisitCommand(
            ctx=ctx, visit_id=visit_id, starts_at=body.starts_at, pet_id=body.pet_id,
            duration_minutes=body.duration_minutes, menu_ids=tuple(body.menu_ids), memo=body.memo or None,
        )
    )
    return UpdatedVisitSchema.of(view)
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py` (수정):
```diff
@@ -3,7 +3,7 @@ from __future__ import annotations
 from contextlib import asynccontextmanager
 from datetime import datetime, timedelta
 
-from sqlalchemy import func, insert, select
+from sqlalchemy import delete, func, insert, select, update
 from sqlalchemy.exc import IntegrityError
 from sqlalchemy.ext.asyncio import AsyncSession
 
@@ -11,8 +11,8 @@ from hub.app.dtos.shop_context import ShopContext
 from visit.adapter.outbound.mappers.visit_mapper import to_visit
 from visit.adapter.outbound.orm.visit_orm import VisitMenuOrm, VisitOrm
 from visit.app.ports.output.visit_repository import VisitRepository
-from visit.domain.entities.visit import ACTIVE_STATUSES, RESERVED, Visit
-from visit.domain.errors import VisitDuplicateError
+from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED, NO_SHOW, RESERVED, Visit
+from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
 from visit.domain.services.visit_schedule import MAX_DURATION
 from visit.domain.value_objects.new_visit import NewVisit
 
@@ -49,6 +49,80 @@ class VisitPgRepository(VisitRepository):
                 ids.append(visit_id)
         return await self._read(ctx, select(VisitOrm).where(VisitOrm.id.in_(ids)))
 
+    async def get(self, ctx: ShopContext, visit_id: int) -> Visit:
+        found = await self._read(ctx, select(VisitOrm).where(VisitOrm.id == visit_id))
+        if not found:
+            raise VisitNotFoundError("방문을 찾을 수 없습니다.")
+        return found[0]
+
+    async def get_many(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
+        return await self._read(ctx, select(VisitOrm).where(VisitOrm.id.in_(visit_ids)))
+
+    async def lock(self, ctx: ShopContext, visit_ids: list[int]) -> list[Visit]:
+        # ID 오름차순으로 잠근다 — 가족 묶음을 서로 다른 순서로 잠그는 두 요청이 교착에 빠지지 않는다.
+        await self._session.execute(
+            select(VisitOrm.id)
+            .where(VisitOrm.id.in_(visit_ids), VisitOrm.shop_id == ctx.shop_id)
+            .order_by(VisitOrm.id)
+            .with_for_update()
+        )
+        return await self.get_many(ctx, visit_ids)
+
+    async def update_details(
+        self, ctx: ShopContext, visit_id: int, starts_at: datetime, pet_id: int | None,
+        duration_minutes: int, menu_ids: tuple[int, ...], memo: str | None,
+    ) -> Visit:
+        async with self._duplicate_guard():
+            await self._session.execute(
+                update(VisitOrm)
+                .where(VisitOrm.id == visit_id, VisitOrm.shop_id == ctx.shop_id)
+                .values(starts_at=starts_at, pet_id=pet_id, duration_minutes=duration_minutes, memo=memo)
+            )
+        await self._session.execute(delete(VisitMenuOrm).where(VisitMenuOrm.visit_id == visit_id))
+        if menu_ids:
+            await self._session.execute(
+                insert(VisitMenuOrm), [dict(visit_id=visit_id, menu_id=m) for m in menu_ids]
+            )
+        return await self.get(ctx, visit_id)
+
+    async def reschedule(self, ctx: ShopContext, visit_ids: list[int], starts_at: datetime) -> list[Visit]:
+        async with self._duplicate_guard():
+            await self._session.execute(
+                update(VisitOrm)
+                .where(VisitOrm.id.in_(visit_ids), VisitOrm.shop_id == ctx.shop_id)
+                .values(starts_at=starts_at)
+            )
+        return await self.get_many(ctx, visit_ids)
+
+    async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
+        return await self._read(
+            ctx, select(VisitOrm).where(VisitOrm.customer_id == customer_id, VisitOrm.starts_at == starts_at)
+        )
+
+    async def last_completed_before(
+        self, ctx: ShopContext, customer_id: int, pet_id: int | None, before: datetime
+    ) -> Visit | None:
+        whose = VisitOrm.pet_id == pet_id if pet_id is not None else VisitOrm.pet_id.is_(None)
+        found = await self._read(
+            ctx,
+            select(VisitOrm)
+            .where(VisitOrm.customer_id == customer_id, whose, VisitOrm.status == COMPLETED,
+                   VisitOrm.starts_at < before)
+            .order_by(VisitOrm.starts_at.desc())
+            .limit(1),
+        )
+        return found[0] if found else None
+
+    async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int:
+        return (
+            await self._session.execute(
+                select(func.count()).where(
+                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
+                    VisitOrm.status == NO_SHOW,
+                )
+            )
+        ).scalar_one()
+
     async def list_between(self, ctx: ShopContext, start: datetime, end: datetime) -> list[Visit]:
         return await self._read(
             ctx, select(VisitOrm).where(VisitOrm.starts_at >= start, VisitOrm.starts_at < end)
```

`backend/apps/visit/dependencies/get_visit_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.get_visit_use_case import GetVisitUseCase
from visit.app.use_cases.get_visit_interactor import GetVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository


def get_get_visit_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> GetVisitUseCase:
    return GetVisitInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db), directory=directory
    )
```

`backend/apps/visit/dependencies/reschedule_visits_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.reschedule_visits_use_case import RescheduleVisitsUseCase
from visit.app.use_cases.reschedule_visits_interactor import RescheduleVisitsInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_reschedule_visits_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> RescheduleVisitsUseCase:
    return RescheduleVisitsInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
    )
```

`backend/apps/visit/dependencies/update_visit_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.update_visit_use_case import UpdateVisitUseCase
from visit.app.use_cases.update_visit_interactor import UpdateVisitInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)
from visit.domain.services.visit_schedule import utc_now


def get_update_visit_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> UpdateVisitUseCase:
    return UpdateVisitInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db),
        schedule=build_schedule_repository(db), directory=directory, now=utc_now,
    )
```

`backend/main.py` (수정):
```diff
@@ -62,13 +62,16 @@ from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
 from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
 from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
 from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
+from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
 from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
 from visit.adapter.inbound.api.v1.list_day_visits_router import list_day_visits_router
 from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
 from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
+from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
+from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 from visit.dependencies.hub_ports import get_customer_directory
 
@@ -129,6 +132,9 @@ app.include_router(get_visit_calendar_router)
 app.include_router(list_visit_slots_router)
 app.include_router(list_day_visits_router)
 app.include_router(register_visit_router)
+app.include_router(reschedule_visits_router)
+app.include_router(get_visit_router)
+app.include_router(update_visit_router)
 install_error_handlers(
     app,
     {
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **584 passed**, 통합 **234 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `UpdateVisitInteractor`의 `new_pet = (command.pet_id,) if changed_pet else ()`를 `new_pet = (command.pet_id,) if command.pet_id is not None else ()`로 바꾼다 → `test_완료한_방문은_메모와_메뉴만_고친다`가 실패한다(무지개다리 아이라 가족 확인이 거절) — 되돌린다.
- `lock_visits`의 `if len(customers) != 1:` 검사를 지운다 → `test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다`가 실패한다 — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/api/schemas/get_visit_schema.py backend/apps/visit/adapter/inbound/api/schemas/register_visit_schema.py backend/apps/visit/adapter/inbound/api/schemas/reschedule_visits_schema.py backend/apps/visit/adapter/inbound/api/schemas/update_visit_schema.py backend/apps/visit/adapter/inbound/api/v1/get_visit_router.py backend/apps/visit/adapter/inbound/api/v1/reschedule_visits_router.py backend/apps/visit/adapter/inbound/api/v1/update_visit_router.py backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py backend/apps/visit/app/dtos/get_visit_dto.py backend/apps/visit/app/dtos/reschedule_visits_dto.py backend/apps/visit/app/dtos/update_visit_dto.py backend/apps/visit/app/ports/input/get_visit_use_case.py backend/apps/visit/app/ports/input/reschedule_visits_use_case.py backend/apps/visit/app/ports/input/update_visit_use_case.py backend/apps/visit/app/ports/output/visit_repository.py backend/apps/visit/app/services/visit_locking.py backend/apps/visit/app/services/visit_warnings.py backend/apps/visit/app/use_cases/get_visit_interactor.py backend/apps/visit/app/use_cases/register_visit_interactor.py backend/apps/visit/app/use_cases/reschedule_visits_interactor.py backend/apps/visit/app/use_cases/update_visit_interactor.py backend/apps/visit/dependencies/get_visit_provider.py backend/apps/visit/dependencies/reschedule_visits_provider.py backend/apps/visit/dependencies/update_visit_provider.py backend/apps/visit/tests/adapter/test_get_visit_router.py backend/apps/visit/tests/adapter/test_reschedule_visits_router.py backend/apps/visit/tests/adapter/test_update_visit_router.py backend/apps/visit/tests/adapter/test_visit_pg_repository.py backend/apps/visit/tests/app/use_cases/test_get_visit_interactor.py backend/apps/visit/tests/app/use_cases/test_reschedule_visits_interactor.py backend/apps/visit/tests/app/use_cases/test_update_visit_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/apps/visit/tests/helpers/rows.py backend/main.py
git commit -m "feat(visit): 방문 상세·수정·가족 한꺼번에 옮기기 — 고객 행 → 방문 행 잠금, 같은 보호자의 아이로만"
```

---

### Task 10: 상태 전이 — `POST /visits/transitions`, 가족 묶음 한 번에, 최근 방문 알림

같은 보호자의 방문 여러 개에 같은 행동 하나를 적용한다. 잠근 뒤 다시 읽은 상태로 **모두 판정한 다음에** 쓴다 — 하나라도 안 되면 아무것도 바꾸지 않는다(V6). 되돌리기는 끝난 방문을 다시 시간을 차지하는 예약으로 만들므로 그 아이들도 가족 확인에 넘긴다 — 무지개다리 아이면 `PET_PASSED_AWAY`(V7). 다른 전이는 보호자만 잠근다. 되돌리기가 중복 예약이 되면(취소한 자리에 새 예약이 이미 있음) 409 `VISIT_DUPLICATE`. 전이는 상태를 바꾼 멤버를 찍는다(③-B 의 노쇼 근거). 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각을 원본에서 다시 계산해 `set_last_visit`로 같은 트랜잭션에서 넘긴다("새로 정한 것" 6).

**Files:**
- Create: `backend/apps/visit/app/dtos/transition_visits_dto.py`
- Create: `backend/apps/visit/app/ports/input/transition_visits_use_case.py`
- Modify: `backend/apps/visit/app/ports/output/visit_repository.py`
- Create: `backend/apps/visit/app/use_cases/transition_visits_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/transition_visits_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/transition_visits_router.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/dependencies/transition_visits_provider.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_transition_visits_router.py`
- Modify (test): `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: Task 2 의 `transition`, Task 9 의 `lock_visits`
- Produces: `VisitRepository.apply_changes(ctx, changes: list[tuple[int, StatusChange]], member_id) -> list[Visit]`, `latest_completed_start(ctx, customer_id) -> datetime | None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_transition_visits_router.py`:
```python
from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView
from visit.dependencies.transition_visits_provider import get_transition_visits_use_case
from visit.domain.errors import VisitNotYetError, VisitStateConflictError
from visit.tests.helpers.api import READ_ONLY, STAFF, Recorder, build_app, client, error_of
from visit.tests.helpers.views import visit_view

DONE = TransitionedVisitsView(visits=[visit_view(status="completed")])


async def _post(body, stub=None, access=STAFF):
    stub = stub or Recorder(DONE)
    async with client(build_app(transition_visits_router, get_transition_visits_use_case, stub, access)) as c:
        return await c.post("/v1/shops/3/visits/transitions", json=body), stub


async def test_직원도_상태를_바꾼다():
    response, stub = await _post({"visit_ids": [1, 2], "action": "cancel", "cancel_reason": "shop_reason"})
    assert response.json()["visits"][0]["status"] == "completed"
    command = stub.calls[0]
    assert (command.visit_ids, command.action, command.cancel_reason) == ((1, 2), "cancel", "shop_reason")


async def test_모르는_행동과_사유_빈_목록은_422_다():
    for bad in ({"visit_ids": [1], "action": "teleport"},
                {"visit_ids": [1], "action": "cancel", "cancel_reason": "weather"},
                {"visit_ids": [], "action": "start"},
                {"visit_ids": [1, 1], "action": "start"}):
        response, _ = await _post(bad)
        assert error_of(response) == (422, "VALIDATION_ERROR"), bad


async def test_권한과_상태_오류():
    response, _ = await _post({"visit_ids": [1], "action": "start"}, access=READ_ONLY)
    assert error_of(response) == (403, "PERMISSION_DENIED")
    for error, expected in ((VisitStateConflictError("충돌"), (409, "VISIT_STATE_CONFLICT")),
                            (VisitNotYetError("아직"), (409, "VISIT_NOT_YET"))):
        response, _ = await _post({"visit_ids": [1], "action": "start"}, stub=Recorder(error=error))
        assert error_of(response) == expected
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py` (수정):
```diff
@@ -6,6 +6,7 @@ from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
 from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
 from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
 from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
+from visit.domain.state.visit_state import StatusChange
 from visit.domain.value_objects.new_visit import NewVisit
 from visit.tests.helpers.builders import ctx, kst
 from visit.tests.helpers.rows import insert_visit
@@ -137,3 +138,26 @@ async def test_묶음_지난_완료_노쇼_수(db_session):
     assert (await repo.last_completed_before(A, 1, None, kst(10, 2, 14))).starts_at == kst(8, 20, 14)
     assert await repo.last_completed_before(A, 1, 102, kst(10, 2, 14)) is None
     assert await repo.count_no_show(A, 1) == 1
+
+
+async def test_상태_칸을_통째로_바꾸고_바꾼_멤버를_찍는다(db_session):
+    repo = VisitPgRepository(db_session)
+    kong, bori = await repo.create_many(A, [new(101), new(102)])
+    changed = await repo.apply_changes(
+        A, [(kong.id, StatusChange("completed", started_at=kst(10, 2, 14), completed_at=kst(10, 2, 15))),
+            (bori.id, StatusChange("canceled", canceled_at=kst(10, 2, 9), cancel_reason="shop_reason"))], 12)
+    assert [(v.status, v.status_changed_by_member_id) for v in changed] == [("completed", 12), ("canceled", 12)]
+    assert await repo.latest_completed_start(A, 1) == kst(10, 2, 14)
+    assert await repo.latest_completed_start(B, 1) is None
+    back = await repo.apply_changes(A, [(kong.id, StatusChange("reserved"))], 11)
+    assert (back[0].status, back[0].started_at, back[0].completed_at) == ("reserved", None, None)
+    assert await repo.latest_completed_start(A, 1) is None
+
+
+async def test_되돌리기가_중복이_되면_VISIT_DUPLICATE_이고_모두_그대로다(db_session):
+    repo = VisitPgRepository(db_session)
+    canceled = await insert_visit(db_session, kst(10, 2, 14), "canceled")
+    await repo.create_many(A, [new(101)])   # 같은 아이·같은 시각의 새 예약
+    with pytest.raises(VisitDuplicateError):
+        await repo.apply_changes(A, [(canceled, StatusChange("reserved"))], 11)
+    assert (await repo.get(A, canceled)).status == "canceled"
```

`backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py`:
```python
import pytest

from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.domain.errors import (
    VisitDuplicateError,
    VisitGroupMismatchError,
    VisitInputError,
    VisitNotYetError,
    VisitStateConflictError,
)
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeDirectory, FakeMenus, FakeVisits, FamilyRejected, Journal

NOW = kst(9, 23, 15)


def _setup():
    journal = Journal()
    visits, directory = FakeVisits(journal), FakeDirectory(journal)
    directory.family(1, pets=(101, 102, 103), passed=(103,))
    directory.family(2, pets=(201,))
    return journal, visits, TransitionVisitsInteractor(visits, FakeMenus(), directory, now=lambda: NOW)


def _act(ids, action, reason=None, member_id=11):
    return TransitionVisitsCommand(ctx=ctx(member_id=member_id), visit_ids=tuple(ids), action=action,
                                   cancel_reason=reason)


async def test_가족_묶음을_한_번에_완료하고_최근_방문을_알린다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13))
    result = await interactor.transition_visits(_act([kong.id, bori.id], "complete", member_id=12))
    assert [(v.status, v.status_changed_by_member_id) for v in result.visits] == [("completed", 12)] * 2
    assert visits.rows[kong.id].completed_at == NOW
    names = [entry[0] for entry in journal]
    assert names == ["lock_family", "lock_visits", "apply_changes", "set_last_visit"]
    assert journal[0] == ("lock_family", 1, ())   # 되돌리기가 아니면 보호자만 잠근다
    assert journal[-1] == ("set_last_visit", 1, kst(9, 23, 13))


async def test_완료를_되돌리면_최근_방문을_다시_계산한다():
    journal, visits, interactor = _setup()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 2, 14), status="completed",
                started_at=kst(9, 2, 14), completed_at=kst(9, 2, 15))
    today = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13), status="completed",
                        started_at=kst(9, 23, 13), completed_at=kst(9, 23, 14))
    await interactor.transition_visits(_act([today.id], "revert"))
    assert visits.rows[today.id].status == "reserved"
    assert journal[0] == ("lock_family", 1, (101,))   # 되돌리기는 아이도 확인한다
    assert journal[-1] == ("set_last_visit", 1, kst(9, 2, 14))


async def test_완료와_상관없는_전이는_최근_방문을_건드리지_않는다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    await interactor.transition_visits(_act([kong.id], "cancel", "customer_request"))
    assert "set_last_visit" not in [entry[0] for entry in journal]
    assert (visits.rows[kong.id].status, visits.rows[kong.id].cancel_reason) == ("canceled", "customer_request")


async def test_하나라도_안_되면_아무것도_바꾸지_않는다():
    """V6 — 미용 중과 예약됨이 섞인 묶음에 '시작'을 누르면 둘 다 그대로다."""
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    bori = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 13), status="in_progress",
                       started_at=kst(9, 23, 13))
    with pytest.raises(VisitStateConflictError):
        await interactor.transition_visits(_act([kong.id, bori.id], "start"))
    assert (visits.rows[kong.id].status, visits.rows[bori.id].status) == ("reserved", "in_progress")
    assert "apply_changes" not in [entry[0] for entry in journal]


async def test_상태_규칙은_도메인이_정한다():
    _, visits, interactor = _setup()
    tomorrow = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 24, 10))
    with pytest.raises(VisitNotYetError):
        await interactor.transition_visits(_act([tomorrow.id], "start"))
    later_today = visits.seed(customer_id=1, pet_id=102, starts_at=kst(9, 23, 18))
    with pytest.raises(VisitNotYetError):
        await interactor.transition_visits(_act([later_today.id], "no_show"))
    with pytest.raises(VisitInputError):
        await interactor.transition_visits(_act([later_today.id], "cancel"))


async def test_무지개다리_아이의_방문은_되돌리지_못한다():
    """V7 — 되돌리면 다시 앞으로의 예약이 된다."""
    _, visits, interactor = _setup()
    canceled = visits.seed(customer_id=1, pet_id=103, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="shop_reason")
    with pytest.raises(FamilyRejected):
        await interactor.transition_visits(_act([canceled.id], "revert"))


async def test_되돌린_자리에_이미_새_예약이_있으면_VISIT_DUPLICATE_다():
    _, visits, interactor = _setup()
    canceled = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14), status="canceled",
                           canceled_at=NOW, cancel_reason="customer_request")
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 30, 14))
    with pytest.raises(VisitDuplicateError):
        await interactor.transition_visits(_act([canceled.id], "revert"))


async def test_다른_보호자의_방문을_섞으면_VISIT_GROUP_MISMATCH_다():
    journal, visits, interactor = _setup()
    kong = visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 23, 13))
    other = visits.seed(customer_id=2, pet_id=201, starts_at=kst(9, 23, 13))
    with pytest.raises(VisitGroupMismatchError):
        await interactor.transition_visits(_act([kong.id, other.id], "complete"))
    assert journal == []
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -214,6 +214,24 @@ class FakeVisits:
         self.journal.append(("reschedule", sorted(visit_ids)))
         return [self.rows[i] for i in sorted(visit_ids)]
 
+    async def apply_changes(self, ctx, changes, member_id):
+        for visit_id, change in changes:
+            current = self._owned(ctx, visit_id)
+            if change.status in ACTIVE_STATUSES and self._clash(
+                    ctx, current.customer_id, current.pet_id, current.starts_at, ignore=(visit_id,)):
+                raise VisitDuplicateError("같은 시각에 이미 저장된 예약이 있습니다.")
+        for visit_id, change in changes:
+            self.rows[visit_id] = replace(
+                self.rows[visit_id], status=change.status, started_at=change.started_at,
+                completed_at=change.completed_at, canceled_at=change.canceled_at,
+                cancel_reason=change.cancel_reason, status_changed_by_member_id=member_id)
+        self.journal.append(("apply_changes", [(i, c.status) for i, c in changes]))
+        return [self.rows[i] for i, _ in changes]
+
+    async def latest_completed_start(self, ctx, customer_id):
+        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.status == "completed"]
+        return max(done) if done else None
+
     async def list_group(self, ctx, customer_id, starts_at):
         return [v for v in self._mine(ctx) if v.customer_id == customer_id and v.starts_at == starts_at]
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해 전이 테스트가 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/dtos/transition_visits_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import VisitView


@dataclass(frozen=True)
class TransitionVisitsCommand:
    """같은 보호자의 방문 여러 개(가족 묶음)에 같은 행동 하나. 전부 되거나 전부 안 된다(V6).

    action: start · complete · cancel · no_show · revert. cancel_reason 은 cancel 일 때만, 반드시.
    """

    ctx: ShopContext
    visit_ids: tuple[int, ...]
    action: str
    cancel_reason: str | None


@dataclass(frozen=True)
class TransitionedVisitsView:
    visits: list[VisitView]
```

`backend/apps/visit/app/ports/input/transition_visits_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand


class TransitionVisitsUseCase(ABC):
    @abstractmethod
    async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView: ...
```

`backend/apps/visit/app/ports/output/visit_repository.py` (수정):
```diff
@@ -5,6 +5,7 @@ from datetime import datetime
 
 from hub.app.dtos.shop_context import ShopContext
 from visit.domain.entities.visit import Visit
+from visit.domain.state.visit_state import StatusChange
 from visit.domain.value_objects.new_visit import NewVisit
 
 
@@ -40,6 +41,16 @@ class VisitRepository(ABC):
     async def reschedule(self, ctx: ShopContext, visit_ids: list[int], starts_at: datetime) -> list[Visit]:
         """여러 방문의 시작 시각을 한 번에 바꾼다. 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""
 
+    @abstractmethod
+    async def apply_changes(
+        self, ctx: ShopContext, changes: list[tuple[int, StatusChange]], member_id: int
+    ) -> list[Visit]:
+        """상태 칸을 통째로 바꾸고 바꾼 멤버를 찍는다. 되돌리기가 중복 예약이 되면 VisitDuplicateError(전부 되돌린다)."""
+
+    @abstractmethod
+    async def latest_completed_start(self, ctx: ShopContext, customer_id: int) -> datetime | None:
+        """그 보호자의 마지막 완료 방문의 시작 시각 — 고객 목록 '최근 방문순'의 원본."""
+
     @abstractmethod
     async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
         """같은 가족 묶음(같은 보호자 + 같은 시작 시각)의 방문 — 상태와 상관없이."""
```

`backend/apps/visit/app/use_cases/transition_visits_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView, TransitionVisitsCommand
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.app.services.visit_locking import lock_visits
from visit.app.services.visit_reader import describe_visits
from visit.domain.entities.visit import COMPLETED
from visit.domain.state.visit_state import transition


class TransitionVisitsInteractor(TransitionVisitsUseCase):
    def __init__(
        self, visits: VisitRepository, menus: MenuRepository, directory: CustomerDirectoryPort,
        now: Callable[[], datetime],
    ) -> None:
        self._visits = visits
        self._menus = menus
        self._directory = directory
        self._now = now

    async def transition_visits(self, command: TransitionVisitsCommand) -> TransitionedVisitsView:
        ctx = command.ctx
        # 되돌리기는 끝난 방문을 다시 시간을 차지하는 예약으로 만든다 — 그 아이가 무지개다리를 건넜으면
        # 가족 확인이 막는다(V7). 다른 행동은 새로 시간을 차지하지 않아 보호자만 잠근다.
        pet_ids: tuple[int, ...] = ()
        if command.action == "revert":
            pet_ids = tuple(sorted({
                v.pet_id for v in await self._visits.get_many(ctx, list(command.visit_ids)) if v.pet_id is not None
            }))
        locked = await lock_visits(ctx, list(command.visit_ids), self._visits, self._directory, pet_ids)

        now = self._now()
        # 잠근 뒤 다시 읽은 상태로 모두 판정한 다음에 쓴다 — 하나라도 안 되면 아무것도 바꾸지 않는다.
        changes = [(v.id, transition(v, command.action, now, ctx.timezone, command.cancel_reason)) for v in locked]
        changed = await self._visits.apply_changes(ctx, changes, ctx.member_id)

        if any(v.status == COMPLETED for v in locked) or any(c.status == COMPLETED for _, c in changes):
            customer_id = locked[0].customer_id
            latest = await self._visits.latest_completed_start(ctx, customer_id)
            await self._directory.set_last_visit(ctx, customer_id, latest)
        return TransitionedVisitsView(
            visits=await describe_visits(ctx, changed, self._directory, self._menus)
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/transition_visits_schema.py`:
```python
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from visit.adapter.inbound.api.schemas.register_visit_schema import EntityId, unique_ids
from visit.adapter.inbound.api.schemas.visit_view_schema import VisitSchema
from visit.app.dtos.transition_visits_dto import TransitionedVisitsView


class TransitionVisitsRequestSchema(BaseModel):
    """cancel_reason 은 cancel 일 때만, 반드시(어기면 422)."""

    visit_ids: Annotated[list[EntityId], Field(min_length=1, max_length=10)]
    action: Literal["start", "complete", "cancel", "no_show", "revert"]
    cancel_reason: Literal["customer_request", "shop_reason"] | None = None

    _ids_unique = field_validator("visit_ids")(unique_ids)


class TransitionedVisitsSchema(BaseModel):
    visits: list[VisitSchema]

    @classmethod
    def of(cls, view: TransitionedVisitsView) -> TransitionedVisitsSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/v1/transition_visits_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import require_permission
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.transition_visits_schema import (
    TransitionedVisitsSchema,
    TransitionVisitsRequestSchema,
)
from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.dependencies.transition_visits_provider import get_transition_visits_use_case

transition_visits_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@transition_visits_router.post("/{shop_id}/visits/transitions", response_model=TransitionedVisitsSchema)
async def transition_visits(
    body: TransitionVisitsRequestSchema,
    ctx: ShopContext = Depends(require_permission("reservation:write")),
    use_case: TransitionVisitsUseCase = Depends(get_transition_visits_use_case),
) -> TransitionedVisitsSchema:
    view = await use_case.transition_visits(
        TransitionVisitsCommand(ctx=ctx, visit_ids=tuple(body.visit_ids), action=body.action,
                                cancel_reason=body.cancel_reason)
    )
    return TransitionedVisitsSchema.of(view)
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py` (수정):
```diff
@@ -14,6 +14,7 @@ from visit.app.ports.output.visit_repository import VisitRepository
 from visit.domain.entities.visit import ACTIVE_STATUSES, COMPLETED, NO_SHOW, RESERVED, Visit
 from visit.domain.errors import VisitDuplicateError, VisitNotFoundError
 from visit.domain.services.visit_schedule import MAX_DURATION
+from visit.domain.state.visit_state import StatusChange
 from visit.domain.value_objects.new_visit import NewVisit
 
 _DUPLICATE = {"uq_visits_pet_start_active", "uq_visits_customer_start_active"}
@@ -94,6 +95,30 @@ class VisitPgRepository(VisitRepository):
             )
         return await self.get_many(ctx, visit_ids)
 
+    async def apply_changes(
+        self, ctx: ShopContext, changes: list[tuple[int, StatusChange]], member_id: int
+    ) -> list[Visit]:
+        async with self._duplicate_guard():
+            for visit_id, change in changes:
+                await self._session.execute(
+                    update(VisitOrm)
+                    .where(VisitOrm.id == visit_id, VisitOrm.shop_id == ctx.shop_id)
+                    .values(status=change.status, started_at=change.started_at,
+                            completed_at=change.completed_at, canceled_at=change.canceled_at,
+                            cancel_reason=change.cancel_reason, status_changed_by_member_id=member_id)
+                )
+        return await self.get_many(ctx, [visit_id for visit_id, _ in changes])
+
+    async def latest_completed_start(self, ctx: ShopContext, customer_id: int) -> datetime | None:
+        return (
+            await self._session.execute(
+                select(func.max(VisitOrm.starts_at)).where(
+                    VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
+                    VisitOrm.status == COMPLETED,
+                )
+            )
+        ).scalar_one()
+
     async def list_group(self, ctx: ShopContext, customer_id: int, starts_at: datetime) -> list[Visit]:
         return await self._read(
             ctx, select(VisitOrm).where(VisitOrm.customer_id == customer_id, VisitOrm.starts_at == starts_at)
```

`backend/apps/visit/dependencies/transition_visits_provider.py`:
```python
from __future__ import annotations

from fastapi import Depends

from core.database import DbSession
from hub.app.ports.customer_directory_port import CustomerDirectoryPort
from visit.app.ports.input.transition_visits_use_case import TransitionVisitsUseCase
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.dependencies.hub_ports import get_customer_directory
from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_transition_visits_use_case(
    db: DbSession, directory: CustomerDirectoryPort = Depends(get_customer_directory)
) -> TransitionVisitsUseCase:
    return TransitionVisitsInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db), directory=directory, now=utc_now
    )
```

`backend/main.py` (수정):
```diff
@@ -70,6 +70,7 @@ from visit.adapter.inbound.api.v1.list_menus_router import list_menus_router
 from visit.adapter.inbound.api.v1.list_visit_slots_router import list_visit_slots_router
 from visit.adapter.inbound.api.v1.register_visit_router import register_visit_router
 from visit.adapter.inbound.api.v1.reschedule_visits_router import reschedule_visits_router
+from visit.adapter.inbound.api.v1.transition_visits_router import transition_visits_router
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
@@ -133,6 +134,7 @@ app.include_router(list_visit_slots_router)
 app.include_router(list_day_visits_router)
 app.include_router(register_visit_router)
 app.include_router(reschedule_visits_router)
+app.include_router(transition_visits_router)
 app.include_router(get_visit_router)
 app.include_router(update_visit_router)
 install_error_handlers(
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **595 passed**, 통합 **236 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `TransitionVisitsInteractor`의 `if command.action == "revert":`를 `if False:`로 바꿔 되돌리기도 보호자만 잠그게 한다 → `test_무지개다리_아이의_방문은_되돌리지_못한다`와 `test_완료를_되돌리면_최근_방문을_다시_계산한다`(journal)가 실패한다 — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/api/schemas/transition_visits_schema.py backend/apps/visit/adapter/inbound/api/v1/transition_visits_router.py backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py backend/apps/visit/app/dtos/transition_visits_dto.py backend/apps/visit/app/ports/input/transition_visits_use_case.py backend/apps/visit/app/ports/output/visit_repository.py backend/apps/visit/app/use_cases/transition_visits_interactor.py backend/apps/visit/dependencies/transition_visits_provider.py backend/apps/visit/tests/adapter/test_transition_visits_router.py backend/apps/visit/tests/adapter/test_visit_pg_repository.py backend/apps/visit/tests/app/use_cases/test_transition_visits_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/main.py
git commit -m "feat(visit): 상태 전이 — POST /visits/transitions, 가족 묶음 한 번에, 최근 방문 알림"
```

---

### Task 11: 지난번처럼 기본값, 다음 예약 초안, 자기소개

`GET /visits/defaults?pet_id=`는 그 아이의 마지막 완료 방문의 메뉴(보관한 메뉴는 뺀다)와 소요를, 없으면 빈 메뉴와 매장 기본 소요를 준다. 반려동물 ID 만으로 이 매장의 방문을 보므로 다른 매장의 아이 ID 는 빈 기본값이 될 뿐이다 — 가족 확인을 부르지 않는다. `GET /visits/{visit_id}/next-draft`는 완료한 방문에서만(아니면 409) 같은 묶음에서 완료한 아이들 전체로, 그 아이의 주기 뒤 같은 요일·같은 시각의 초안을 준다. 저장하지 않는다. `GET /visits/myself`는 이 묶음의 엔드포인트·데이터·제약을 실제대로 적는다(번호 5).

**Files:**
- Create: `backend/apps/visit/app/dtos/get_next_visit_draft_dto.py`
- Create: `backend/apps/visit/app/dtos/get_visit_defaults_dto.py`
- Create: `backend/apps/visit/app/dtos/visit_myself_dto.py`
- Create: `backend/apps/visit/app/ports/input/get_next_visit_draft_use_case.py`
- Create: `backend/apps/visit/app/ports/input/get_visit_defaults_use_case.py`
- Create: `backend/apps/visit/app/ports/input/visit_myself_use_case.py`
- Create: `backend/apps/visit/app/ports/output/visit_myself_record_port.py`
- Modify: `backend/apps/visit/app/ports/output/visit_repository.py`
- Create: `backend/apps/visit/app/use_cases/get_next_visit_draft_interactor.py`
- Create: `backend/apps/visit/app/use_cases/get_visit_defaults_interactor.py`
- Create: `backend/apps/visit/app/use_cases/visit_myself_interactor.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_next_visit_draft_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/get_visit_defaults_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/schemas/visit_myself_schema.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_next_visit_draft_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/get_visit_defaults_router.py`
- Create: `backend/apps/visit/adapter/inbound/api/v1/visit_myself_router.py`
- Create: `backend/apps/visit/adapter/outbound/log_visit_myself_record_adapter.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Create: `backend/apps/visit/dependencies/get_next_visit_draft_provider.py`
- Create: `backend/apps/visit/dependencies/get_visit_defaults_provider.py`
- Create: `backend/apps/visit/dependencies/visit_myself_provider.py`
- Modify: `backend/main.py`
- Test: `backend/apps/visit/tests/adapter/test_get_next_visit_draft_router.py`
- Test: `backend/apps/visit/tests/adapter/test_get_visit_defaults_router.py`
- Test: `backend/apps/visit/tests/adapter/test_visit_myself_router.py`
- Modify (test): `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_get_next_visit_draft_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_get_visit_defaults_interactor.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`

**Interfaces:**
- Consumes: Task 2 의 `visit_cycle`, Task 7~10 의 저장소
- Produces: `VisitRepository.last_completed_of_pet(ctx, pet_id)`, `completed_starts(ctx, customer_id, pet_id, limit)`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/visit/tests/adapter/test_get_next_visit_draft_router.py`:
```python
from datetime import datetime
from zoneinfo import ZoneInfo

from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
from visit.app.dtos.get_next_visit_draft_dto import NextVisitDraftView
from visit.dependencies.get_next_visit_draft_provider import get_get_next_visit_draft_use_case
from visit.domain.errors import VisitStateConflictError
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

DRAFT = NextVisitDraftView(customer_id=1, pet_ids=[101, 102],
                           starts_at=datetime(2026, 10, 21, 14, tzinfo=ZoneInfo("Asia/Seoul")),
                           duration_minutes=150, menus=[], interval_weeks=4)


async def test_다음_예약_초안을_준다():
    stub = Recorder(DRAFT)
    async with client(build_app(get_next_visit_draft_router, get_get_next_visit_draft_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/9/next-draft")
    assert response.json() == {"customer_id": 1, "pet_ids": [101, 102], "starts_at": "2026-10-21T14:00:00+09:00",
                               "duration_minutes": 150, "menus": [], "interval_weeks": 4}
    assert stub.calls[0].visit_id == 9


async def test_완료하지_않은_방문이면_409():
    stub = Recorder(error=VisitStateConflictError("완료 아님"))
    async with client(build_app(get_next_visit_draft_router, get_get_next_visit_draft_use_case, stub)) as c:
        assert error_of(await c.get("/v1/shops/3/visits/9/next-draft")) == (409, "VISIT_STATE_CONFLICT")
```

`backend/apps/visit/tests/adapter/test_get_visit_defaults_router.py`:
```python
from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
from visit.app.dtos.get_visit_defaults_dto import VisitDefaultsView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.dependencies.get_visit_defaults_provider import get_get_visit_defaults_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client, error_of

DEFAULTS = VisitDefaultsView(source_visit_id=7, duration_minutes=150, menus=[MenuBriefView(menu_id=4, name="전체 미용")])


async def test_지난번처럼_채울_값을_준다():
    stub = Recorder(DEFAULTS)
    async with client(build_app(get_visit_defaults_router, get_get_visit_defaults_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/defaults?pet_id=101")
        assert error_of(await c.get("/v1/shops/3/visits/defaults")) == (422, "VALIDATION_ERROR")
    assert response.json() == {"source_visit_id": 7, "duration_minutes": 150,
                               "menus": [{"menu_id": 4, "name": "전체 미용"}]}
    assert stub.calls[0].pet_id == 101
```

`backend/apps/visit/tests/adapter/test_visit_myself_router.py`:
```python
from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
from visit.app.dtos.visit_myself_dto import VisitMyselfResponse
from visit.dependencies.visit_myself_provider import get_visit_myself_use_case
from visit.tests.helpers.api import STAFF, Recorder, build_app, client


async def test_멤버는_자기소개를_본다():
    stub = Recorder(VisitMyselfResponse(id=5, name="방문 (visit)", introduction="소개"))
    async with client(build_app(visit_myself_router, get_visit_myself_use_case, stub, STAFF)) as c:
        response = await c.get("/v1/shops/3/visits/myself")
    assert response.json() == {"id": 5, "name": "방문 (visit)", "introduction": "소개"}
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py` (수정):
```diff
@@ -161,3 +161,16 @@ async def test_되돌리기가_중복이_되면_VISIT_DUPLICATE_이고_모두_
     with pytest.raises(VisitDuplicateError):
         await repo.apply_changes(A, [(canceled, StatusChange("reserved"))], 11)
     assert (await repo.get(A, canceled)).status == "canceled"
+
+
+async def test_아이의_지난_완료와_완료_시각들(db_session):
+    repo = VisitPgRepository(db_session)
+    await insert_visit(db_session, kst(8, 1, 14), "completed")
+    last = await insert_visit(db_session, kst(9, 2, 14), "completed")
+    await insert_visit(db_session, kst(9, 9, 14), "canceled")
+    await insert_visit(db_session, kst(9, 3, 14), "completed", shop_id=2)
+    await insert_visit(db_session, kst(9, 4, 14), "completed", pet_id=None)
+    assert (await repo.last_completed_of_pet(A, 101)).id == last
+    assert await repo.last_completed_of_pet(A, 999) is None
+    assert await repo.completed_starts(A, 1, 101, limit=2) == [kst(9, 2, 14), kst(8, 1, 14)]
+    assert await repo.completed_starts(A, 1, None, limit=2) == [kst(9, 4, 14)]
```

`backend/apps/visit/tests/app/use_cases/test_get_next_visit_draft_interactor.py`:
```python
import pytest

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery
from visit.app.use_cases.get_next_visit_draft_interactor import GetNextVisitDraftInteractor
from visit.domain.errors import VisitNotFoundError, VisitStateConflictError
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeMenus, FakeVisits


def _setup():
    visits, menus = FakeVisits(), FakeMenus()
    return visits, menus, GetNextVisitDraftInteractor(visits, menus)


def _done(visits, **fields):
    starts = fields.pop("starts_at")
    return visits.seed(status="completed", starts_at=starts, started_at=starts, completed_at=starts, **fields)


async def test_주기_뒤_같은_요일_시각_같은_메뉴로_가족_전체():
    visits, menus, interactor = _setup()
    trim = menus.seed("전체 미용")
    _done(visits, pet_id=101, starts_at=kst(8, 19, 14))
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14), duration_minutes=150, menu_ids=(trim.id,))
    _done(visits, pet_id=102, starts_at=kst(9, 23, 14))
    visits.seed(pet_id=103, starts_at=kst(9, 23, 14), status="no_show")   # 같은 묶음이라도 완료가 아니면 빠진다
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=kong.id))
    assert draft.interval_weeks == 5   # 8/19 → 9/23 은 5주
    assert (draft.customer_id, draft.pet_ids, draft.duration_minutes, [m.name for m in draft.menus]) == (
        1, [101, 102], 150, ["전체 미용"])
    assert draft.starts_at.isoformat() == "2026-10-28T14:00:00+09:00"


async def test_처음_완료했으면_4주_뒤다():
    visits, _, interactor = _setup()
    kong = _done(visits, pet_id=101, starts_at=kst(9, 23, 14))
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=kong.id))
    assert (draft.interval_weeks, draft.starts_at.isoformat()) == (4, "2026-10-21T14:00:00+09:00")


async def test_보호자만의_방문이면_반려동물_없이():
    visits, _, interactor = _setup()
    solo = _done(visits, pet_id=None, starts_at=kst(9, 23, 14))
    draft = await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=solo.id))
    assert draft.pet_ids == []


async def test_완료하지_않은_방문이나_다른_매장_방문은_안_된다():
    visits, _, interactor = _setup()
    reserved = visits.seed(pet_id=101, starts_at=kst(9, 30, 14))
    with pytest.raises(VisitStateConflictError):
        await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(), visit_id=reserved.id))
    theirs = _done(visits, pet_id=201, starts_at=kst(9, 23, 14), shop_id=2)
    with pytest.raises(VisitNotFoundError):
        await interactor.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx(shop_id=1), visit_id=theirs.id))
```

`backend/apps/visit/tests/app/use_cases/test_get_visit_defaults_interactor.py`:
```python
from datetime import time

from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery
from visit.app.use_cases.get_visit_defaults_interactor import GetVisitDefaultsInteractor
from visit.domain.value_objects.schedule_settings import ScheduleSettings
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeMenus, FakeSchedule, FakeVisits


def _setup():
    visits, menus = FakeVisits(), FakeMenus()
    schedule = FakeSchedule(settings=ScheduleSettings(time(10), time(19), 90, frozenset()))
    return visits, menus, GetVisitDefaultsInteractor(visits, menus, schedule)


def _done(visits, **fields):
    starts = fields.pop("starts_at")
    return visits.seed(status="completed", starts_at=starts, started_at=starts, completed_at=starts, **fields)


async def test_지난_완료_방문의_메뉴와_소요로_채운다():
    visits, menus, interactor = _setup()
    bath, trim, old = menus.seed("목욕"), menus.seed("전체 미용"), menus.seed("옛 메뉴", archived=True)
    _done(visits, pet_id=101, starts_at=kst(8, 1, 14), duration_minutes=60, menu_ids=(bath.id,))
    last = _done(visits, pet_id=101, starts_at=kst(9, 2, 14), duration_minutes=150,
                 menu_ids=(trim.id, old.id))
    visits.seed(pet_id=101, starts_at=kst(10, 2, 14), duration_minutes=30)   # 아직 오지 않은 예약은 아니다
    view = await interactor.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx(), pet_id=101))
    assert (view.source_visit_id, view.duration_minutes, [m.name for m in view.menus]) == (
        last.id, 150, ["전체 미용"])   # 보관한 메뉴는 뺀다


async def test_처음_온_아이는_빈_메뉴와_매장_기본_소요():
    _, _, interactor = _setup()
    view = await interactor.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx(), pet_id=101))
    assert (view.source_visit_id, view.duration_minutes, view.menus) == (None, 90, [])


async def test_다른_매장의_방문은_보지_않는다():
    visits, _, interactor = _setup()
    _done(visits, pet_id=101, starts_at=kst(9, 2, 14), shop_id=2)
    view = await interactor.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx(shop_id=1), pet_id=101))
    assert view.source_visit_id is None
```

`backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py`:
```python
from visit.app.dtos.visit_myself_dto import VisitMyselfQuery
from visit.app.use_cases.visit_myself_interactor import VisitMyselfInteractor


class _Record:
    def __init__(self):
        self.calls = []

    async def record(self, subject, note):
        self.calls.append((subject, note))


async def test_자기소개는_묶음의_경로와_권한을_적는다():
    record = _Record()
    result = await VisitMyselfInteractor(record).introduce_myself(VisitMyselfQuery(id=5, name="방문 (visit)"))
    assert (result.id, result.name) == (5, "방문 (visit)")
    for words in ("POST /visits/transitions", "reservation:write", "shop:update", "/visit-settings", "10분 단위"):
        assert words in result.introduction
    assert record.calls == [("introduce_myself", "방문 (visit) 자기소개 조회")]
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -240,6 +240,15 @@ class FakeVisits:
                  and v.status == "completed" and v.starts_at < before]
         return found[-1] if found else None
 
+    async def last_completed_of_pet(self, ctx, pet_id):
+        done = [v for v in self._mine(ctx) if v.pet_id == pet_id and v.status == "completed"]
+        return done[-1] if done else None
+
+    async def completed_starts(self, ctx, customer_id, pet_id, limit):
+        done = [v.starts_at for v in self._mine(ctx) if v.customer_id == customer_id and v.pet_id == pet_id
+                and v.status == "completed"]
+        return sorted(done, reverse=True)[:limit]
+
     async def count_no_show(self, ctx, customer_id):
         return sum(v.customer_id == customer_id and v.status == "no_show" for v in self._mine(ctx))
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 새 모듈을 찾지 못해 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/visit/app/dtos/get_next_visit_draft_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import MenuBriefView


@dataclass(frozen=True)
class GetNextVisitDraftQuery:
    ctx: ShopContext
    visit_id: int


@dataclass(frozen=True)
class NextVisitDraftView:
    """완료한 방문 기준의 다음 예약 초안. 저장하지 않는다 — 앱이 예약 ② 화면을 이 값으로 채워 연다."""

    customer_id: int
    pet_ids: list[int]           # 같은 묶음으로 완료한 아이들(보호자만이면 빈 목록)
    starts_at: datetime          # 매장 시간대, 주기 뒤 같은 요일·같은 시각
    duration_minutes: int
    menus: list[MenuBriefView]   # 보관한 메뉴는 뺀다
    interval_weeks: int
```

`backend/apps/visit/app/dtos/get_visit_defaults_dto.py`:
```python
from __future__ import annotations

from dataclasses import dataclass

from hub.app.dtos.shop_context import ShopContext
from visit.app.dtos.visit_view_dto import MenuBriefView


@dataclass(frozen=True)
class GetVisitDefaultsQuery:
    ctx: ShopContext
    pet_id: int


@dataclass(frozen=True)
class VisitDefaultsView:
    """예약 ② 화면에 미리 채울 값 — 그 아이의 지난 완료 방문('지난번처럼'). 없으면 빈 메뉴와 매장 기본 소요."""

    source_visit_id: int | None
    duration_minutes: int
    menus: list[MenuBriefView]   # 보관한 메뉴는 뺀다
```

`backend/apps/visit/app/dtos/visit_myself_dto.py`:
```python
from dataclasses import dataclass


@dataclass(frozen=True)
class VisitMyselfQuery:
    id: int
    name: str


@dataclass(frozen=True)
class VisitMyselfResponse:
    id: int
    name: str
    introduction: str
```

`backend/apps/visit/app/ports/input/get_next_visit_draft_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, NextVisitDraftView


class GetNextVisitDraftUseCase(ABC):
    @abstractmethod
    async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView: ...
```

`backend/apps/visit/app/ports/input/get_visit_defaults_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery, VisitDefaultsView


class GetVisitDefaultsUseCase(ABC):
    @abstractmethod
    async def get_visit_defaults(self, query: GetVisitDefaultsQuery) -> VisitDefaultsView: ...
```

`backend/apps/visit/app/ports/input/visit_myself_use_case.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from visit.app.dtos.visit_myself_dto import VisitMyselfQuery, VisitMyselfResponse


class VisitMyselfUseCase(ABC):
    @abstractmethod
    async def introduce_myself(self, query: VisitMyselfQuery) -> VisitMyselfResponse: ...
```

`backend/apps/visit/app/ports/output/visit_myself_record_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod


class VisitMyselfRecordPort(ABC):
    """자기소개 조회 기록. 구현(로그 또는 DB)은 어댑터가 제공한다."""

    @abstractmethod
    async def record(self, subject: str, note: str) -> None: ...
```

`backend/apps/visit/app/ports/output/visit_repository.py` (수정):
```diff
@@ -61,6 +61,16 @@ class VisitRepository(ABC):
     ) -> Visit | None:
         """before 전에 시작한 마지막 완료 방문. pet_id 가 있으면 그 아이의, 없으면 보호자만의 방문 가운데서."""
 
+    @abstractmethod
+    async def last_completed_of_pet(self, ctx: ShopContext, pet_id: int) -> Visit | None:
+        """그 아이의 마지막 완료 방문('지난번처럼'의 원본)."""
+
+    @abstractmethod
+    async def completed_starts(
+        self, ctx: ShopContext, customer_id: int, pet_id: int | None, limit: int
+    ) -> list[datetime]:
+        """그 아이(pet_id 가 None 이면 보호자만의 방문)의 완료 방문 시작 시각, 최근 것부터 limit 개."""
+
     @abstractmethod
     async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int: ...
```

`backend/apps/visit/app/use_cases/get_next_visit_draft_interactor.py`:
```python
from __future__ import annotations

from zoneinfo import ZoneInfo

from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery, NextVisitDraftView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.entities.visit import COMPLETED
from visit.domain.errors import VisitStateConflictError
from visit.domain.services.visit_cycle import interval_weeks, next_start


class GetNextVisitDraftInteractor(GetNextVisitDraftUseCase):
    def __init__(self, visits: VisitRepository, menus: MenuRepository) -> None:
        self._visits = visits
        self._menus = menus

    async def get_next_visit_draft(self, query: GetNextVisitDraftQuery) -> NextVisitDraftView:
        ctx = query.ctx
        visit = await self._visits.get(ctx, query.visit_id)
        if visit.status != COMPLETED:
            raise VisitStateConflictError("완료한 방문에서만 다음 예약을 잡을 수 있습니다.")
        group = [v for v in await self._visits.list_group(ctx, visit.customer_id, visit.starts_at)
                 if v.status == COMPLETED]
        starts = await self._visits.completed_starts(ctx, visit.customer_id, visit.pet_id, limit=2)
        weeks = interval_weeks(starts)
        active = {m.id: m for m in await self._menus.list_active_by_ids(ctx, list(visit.menu_ids))}
        return NextVisitDraftView(
            customer_id=visit.customer_id,
            pet_ids=sorted(v.pet_id for v in group if v.pet_id is not None),
            starts_at=next_start(visit.starts_at, weeks, ctx.timezone).astimezone(ZoneInfo(ctx.timezone)),
            duration_minutes=visit.duration_minutes,
            menus=[MenuBriefView(menu_id=m, name=active[m].name) for m in visit.menu_ids if m in active],
            interval_weeks=weeks,
        )
```

`backend/apps/visit/app/use_cases/get_visit_defaults_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery, VisitDefaultsView
from visit.app.dtos.visit_view_dto import MenuBriefView
from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
from visit.app.ports.output.menu_repository import MenuRepository
from visit.app.ports.output.schedule_repository import ScheduleRepository
from visit.app.ports.output.visit_repository import VisitRepository


class GetVisitDefaultsInteractor(GetVisitDefaultsUseCase):
    """다른 매장의 반려동물 ID 를 넣어도 이 매장의 방문만 보므로 빈 기본값이 된다 — 아무것도 새지 않는다."""

    def __init__(self, visits: VisitRepository, menus: MenuRepository, schedule: ScheduleRepository) -> None:
        self._visits = visits
        self._menus = menus
        self._schedule = schedule

    async def get_visit_defaults(self, query: GetVisitDefaultsQuery) -> VisitDefaultsView:
        settings = await self._schedule.ensure(query.ctx)
        last = await self._visits.last_completed_of_pet(query.ctx, query.pet_id)
        if last is None:
            return VisitDefaultsView(source_visit_id=None, duration_minutes=settings.default_duration_minutes,
                                     menus=[])
        active = {m.id: m for m in await self._menus.list_active_by_ids(query.ctx, list(last.menu_ids))}
        return VisitDefaultsView(
            source_visit_id=last.id,
            duration_minutes=last.duration_minutes,
            menus=[MenuBriefView(menu_id=m, name=active[m].name) for m in last.menu_ids if m in active],
        )
```

`backend/apps/visit/app/use_cases/visit_myself_interactor.py`:
```python
from __future__ import annotations

from visit.app.dtos.visit_myself_dto import VisitMyselfQuery, VisitMyselfResponse
from visit.app.ports.input.visit_myself_use_case import VisitMyselfUseCase
from visit.app.ports.output.visit_myself_record_port import VisitMyselfRecordPort


class VisitMyselfInteractor(VisitMyselfUseCase):
    def __init__(self, record: VisitMyselfRecordPort) -> None:
        self._record = record

    async def introduce_myself(self, query: VisitMyselfQuery) -> VisitMyselfResponse:
        await self._record.record(subject="introduce_myself", note=f"{query.name} 자기소개 조회")
        return VisitMyselfResponse(
            id=query.id,
            name=query.name,
            introduction=(
                "매장의 방문(예약부터 완료까지)과 매장 일정·메뉴표를 관리합니다. "
                "경로는 모두 /v1/shops/{shop_id} 아래이고 매 요청마다 매장 소속을 확인합니다. "
                "방문 하나는 반려동물 한 마리의 방문이고, 반려동물 없이 보호자만의 방문도 있습니다. "
                "상태는 reserved → in_progress → completed 이고 canceled·no_show 로 끝날 수 있습니다. "
                "GET /visits?date= 는 하루 목록(가족 묶음 group_key, 겹침, 정리 안 된 예약), "
                "GET /visits/calendar?month=YYYY-MM 은 월 달력, GET /visits/slots?date=&duration=&at=&exclude= 는 "
                "시간 칸의 경고(overlap·closed_day·outside_hours — 막지 않음)입니다. "
                "GET /visits/defaults?pet_id= 는 그 아이의 지난 완료 방문으로 채운 메뉴·소요입니다. "
                "POST /visits 는 예약 등록(pet_ids 마다 방문 하나, 빈 목록이면 보호자만, walk_in 이면 지금 시작), "
                "GET·PUT /visits/{visit_id} 는 상세·수정, POST /visits/reschedule 는 같은 보호자의 예약을 함께 옮기기, "
                "POST /visits/transitions 는 start·complete·cancel·no_show·revert(같은 보호자의 방문만, 전부 되거나 "
                "전부 안 됨), GET /visits/{visit_id}/next-draft 는 완료한 방문의 다음 예약 초안입니다. "
                "GET·PUT /visit-settings(영업시간·기본 소요·쉬는 요일), GET·POST /closed-dates, "
                "DELETE /closed-dates/{date}(임시 휴무), GET·POST /menus, PUT /menus/{menu_id}, "
                "POST /menus/{menu_id}/archive(메뉴표 — 지우지 않고 보관)도 있습니다. "
                "방문 쓰기와 상태 전이는 reservation:write(사장·직원), 일정·메뉴 수정은 shop:update(사장)가 필요합니다. "
                "시각은 시간대를 붙여 받고 매장 시간대로 돌려줍니다. 예약 시각은 10분 단위, 오늘 기준 앞뒤 1년, "
                "끝나는 시각이 그날 자정을 넘으면 안 됩니다. 같은 아이의 같은 시각에 살아 있는 예약은 하나입니다(409). "
                "다른 매장의 방문·메뉴 ID 는 404 입니다."
            ),
        )
```

`backend/apps/visit/adapter/inbound/api/schemas/get_next_visit_draft_schema.py`:
```python
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import MenuBriefSchema
from visit.app.dtos.get_next_visit_draft_dto import NextVisitDraftView


class NextVisitDraftSchema(BaseModel):
    customer_id: int
    pet_ids: list[int]
    starts_at: datetime
    duration_minutes: int
    menus: list[MenuBriefSchema]
    interval_weeks: int

    @classmethod
    def of(cls, view: NextVisitDraftView) -> NextVisitDraftSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/schemas/get_visit_defaults_schema.py`:
```python
from __future__ import annotations

from pydantic import BaseModel

from visit.adapter.inbound.api.schemas.visit_view_schema import MenuBriefSchema
from visit.app.dtos.get_visit_defaults_dto import VisitDefaultsView


class VisitDefaultsSchema(BaseModel):
    source_visit_id: int | None
    duration_minutes: int
    menus: list[MenuBriefSchema]

    @classmethod
    def of(cls, view: VisitDefaultsView) -> VisitDefaultsSchema:
        return cls.model_validate(view, from_attributes=True)
```

`backend/apps/visit/adapter/inbound/api/schemas/visit_myself_schema.py`:
```python
from pydantic import BaseModel


class VisitMyselfResponseSchema(BaseModel):
    id: int
    name: str
    introduction: str
```

`backend/apps/visit/adapter/inbound/api/v1/get_next_visit_draft_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.path_params import VisitId
from visit.adapter.inbound.api.schemas.get_next_visit_draft_schema import NextVisitDraftSchema
from visit.app.dtos.get_next_visit_draft_dto import GetNextVisitDraftQuery
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.dependencies.get_next_visit_draft_provider import get_get_next_visit_draft_use_case

get_next_visit_draft_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_next_visit_draft_router.get("/{shop_id}/visits/{visit_id}/next-draft", response_model=NextVisitDraftSchema)
async def get_next_visit_draft(
    visit_id: VisitId,
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetNextVisitDraftUseCase = Depends(get_get_next_visit_draft_use_case),
) -> NextVisitDraftSchema:
    return NextVisitDraftSchema.of(
        await use_case.get_next_visit_draft(GetNextVisitDraftQuery(ctx=ctx, visit_id=visit_id))
    )
```

`backend/apps/visit/adapter/inbound/api/v1/get_visit_defaults_router.py`:
```python
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from core.shop_guard import get_shop_context
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.inbound.api.schemas.get_visit_defaults_schema import VisitDefaultsSchema
from visit.app.dtos.get_visit_defaults_dto import GetVisitDefaultsQuery
from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
from visit.dependencies.get_visit_defaults_provider import get_get_visit_defaults_use_case

get_visit_defaults_router = APIRouter(prefix="/v1/shops", tags=["visits"])


@get_visit_defaults_router.get("/{shop_id}/visits/defaults", response_model=VisitDefaultsSchema)
async def get_visit_defaults(
    pet_id: Annotated[int, Query(ge=1, le=9_223_372_036_854_775_807)],
    ctx: ShopContext = Depends(get_shop_context),
    use_case: GetVisitDefaultsUseCase = Depends(get_get_visit_defaults_use_case),
) -> VisitDefaultsSchema:
    return VisitDefaultsSchema.of(
        await use_case.get_visit_defaults(GetVisitDefaultsQuery(ctx=ctx, pet_id=pet_id))
    )
```

`backend/apps/visit/adapter/inbound/api/v1/visit_myself_router.py`:
```python
from fastapi import APIRouter, Depends

from core.shop_guard import get_shop_context
from visit.adapter.inbound.api.schemas.visit_myself_schema import VisitMyselfResponseSchema
from visit.app.dtos.visit_myself_dto import VisitMyselfQuery
from visit.app.ports.input.visit_myself_use_case import VisitMyselfUseCase
from visit.dependencies.visit_myself_provider import get_visit_myself_use_case

visit_myself_router = APIRouter(prefix="/v1/shops", tags=["visits"])


# 경로에 {shop_id} 가 있어 매장 소속을 확인한다(라우트 구조 검사 규칙). 매장 정보는 쓰지 않는다.
@visit_myself_router.get(
    "/{shop_id}/visits/myself", response_model=VisitMyselfResponseSchema,
    dependencies=[Depends(get_shop_context)],
)
async def introduce_myself(
    use_case: VisitMyselfUseCase = Depends(get_visit_myself_use_case),
) -> VisitMyselfResponseSchema:
    result = await use_case.introduce_myself(VisitMyselfQuery(id=5, name="방문 (visit)"))
    return VisitMyselfResponseSchema(id=result.id, name=result.name, introduction=result.introduction)
```

`backend/apps/visit/adapter/outbound/log_visit_myself_record_adapter.py`:
```python
from __future__ import annotations

import logging

from visit.app.ports.output.visit_myself_record_port import VisitMyselfRecordPort

logger = logging.getLogger(__name__)


class LogVisitMyselfRecordAdapter(VisitMyselfRecordPort):
    """기록을 로그로 남기는 구현. 고객·방문 정보는 담지 않는다."""

    async def record(self, subject: str, note: str) -> None:
        logger.info("[visit-myself-record] %s | %s", subject, note)
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py` (수정):
```diff
@@ -138,6 +138,32 @@ class VisitPgRepository(VisitRepository):
         )
         return found[0] if found else None
 
+    async def last_completed_of_pet(self, ctx: ShopContext, pet_id: int) -> Visit | None:
+        found = await self._read(
+            ctx,
+            select(VisitOrm)
+            .where(VisitOrm.pet_id == pet_id, VisitOrm.status == COMPLETED)
+            .order_by(VisitOrm.starts_at.desc())
+            .limit(1),
+        )
+        return found[0] if found else None
+
+    async def completed_starts(
+        self, ctx: ShopContext, customer_id: int, pet_id: int | None, limit: int
+    ) -> list[datetime]:
+        whose = VisitOrm.pet_id == pet_id if pet_id is not None else VisitOrm.pet_id.is_(None)
+        return list(
+            (
+                await self._session.execute(
+                    select(VisitOrm.starts_at)
+                    .where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id, whose,
+                           VisitOrm.status == COMPLETED)
+                    .order_by(VisitOrm.starts_at.desc())
+                    .limit(limit)
+                )
+            ).scalars()
+        )
+
     async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int:
         return (
             await self._session.execute(
```

`backend/apps/visit/dependencies/get_next_visit_draft_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_next_visit_draft_use_case import GetNextVisitDraftUseCase
from visit.app.use_cases.get_next_visit_draft_interactor import GetNextVisitDraftInteractor
from visit.dependencies.visit_wiring import build_menu_repository, build_visit_repository


def get_get_next_visit_draft_use_case(db: DbSession) -> GetNextVisitDraftUseCase:
    return GetNextVisitDraftInteractor(visits=build_visit_repository(db), menus=build_menu_repository(db))
```

`backend/apps/visit/dependencies/get_visit_defaults_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from visit.app.ports.input.get_visit_defaults_use_case import GetVisitDefaultsUseCase
from visit.app.use_cases.get_visit_defaults_interactor import GetVisitDefaultsInteractor
from visit.dependencies.visit_wiring import (
    build_menu_repository,
    build_schedule_repository,
    build_visit_repository,
)


def get_get_visit_defaults_use_case(db: DbSession) -> GetVisitDefaultsUseCase:
    return GetVisitDefaultsInteractor(
        visits=build_visit_repository(db), menus=build_menu_repository(db), schedule=build_schedule_repository(db)
    )
```

`backend/apps/visit/dependencies/visit_myself_provider.py`:
```python
from __future__ import annotations

from visit.adapter.outbound.log_visit_myself_record_adapter import LogVisitMyselfRecordAdapter
from visit.app.ports.input.visit_myself_use_case import VisitMyselfUseCase
from visit.app.use_cases.visit_myself_interactor import VisitMyselfInteractor


def get_visit_myself_use_case() -> VisitMyselfUseCase:
    return VisitMyselfInteractor(record=LogVisitMyselfRecordAdapter())
```

`backend/main.py` (수정):
```diff
@@ -61,7 +61,9 @@ from visit.adapter.inbound.api.v1.add_closed_date_router import add_closed_date_
 from visit.adapter.inbound.api.v1.archive_menu_router import archive_menu_router
 from visit.adapter.inbound.api.v1.create_menu_router import create_menu_router
 from visit.adapter.inbound.api.v1.delete_closed_date_router import delete_closed_date_router
+from visit.adapter.inbound.api.v1.get_next_visit_draft_router import get_next_visit_draft_router
 from visit.adapter.inbound.api.v1.get_visit_calendar_router import get_visit_calendar_router
+from visit.adapter.inbound.api.v1.get_visit_defaults_router import get_visit_defaults_router
 from visit.adapter.inbound.api.v1.get_visit_router import get_visit_router
 from visit.adapter.inbound.api.v1.get_visit_settings_router import get_visit_settings_router
 from visit.adapter.inbound.api.v1.list_closed_dates_router import list_closed_dates_router
@@ -74,6 +76,7 @@ from visit.adapter.inbound.api.v1.transition_visits_router import transition_vis
 from visit.adapter.inbound.api.v1.update_menu_router import update_menu_router
 from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
+from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
 from visit.dependencies.hub_ports import get_customer_directory
 
 
@@ -128,15 +131,18 @@ app.include_router(list_menus_router)
 app.include_router(create_menu_router)
 app.include_router(update_menu_router)
 app.include_router(archive_menu_router)
-# /visits/calendar 와 /visits/slots 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
+# /visits/myself·calendar·slots·defaults 는 /visits/{visit_id} 보다 먼저 붙인다(정수 변환 실패 422 를 피한다).
+app.include_router(visit_myself_router)
 app.include_router(get_visit_calendar_router)
 app.include_router(list_visit_slots_router)
+app.include_router(get_visit_defaults_router)
 app.include_router(list_day_visits_router)
 app.include_router(register_visit_router)
 app.include_router(reschedule_visits_router)
 app.include_router(transition_visits_router)
 app.include_router(get_visit_router)
 app.include_router(update_visit_router)
+app.include_router(get_next_visit_draft_router)
 install_error_handlers(
     app,
     {
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **607 passed**, 통합 **237 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `GetNextVisitDraftInteractor`의 `if visit.status != COMPLETED:` 검사를 지운다 → `test_완료하지_않은_방문이나_다른_매장_방문은_안_된다`가 실패한다 — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/visit/adapter/inbound/api/schemas/get_next_visit_draft_schema.py backend/apps/visit/adapter/inbound/api/schemas/get_visit_defaults_schema.py backend/apps/visit/adapter/inbound/api/schemas/visit_myself_schema.py backend/apps/visit/adapter/inbound/api/v1/get_next_visit_draft_router.py backend/apps/visit/adapter/inbound/api/v1/get_visit_defaults_router.py backend/apps/visit/adapter/inbound/api/v1/visit_myself_router.py backend/apps/visit/adapter/outbound/log_visit_myself_record_adapter.py backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py backend/apps/visit/app/dtos/get_next_visit_draft_dto.py backend/apps/visit/app/dtos/get_visit_defaults_dto.py backend/apps/visit/app/dtos/visit_myself_dto.py backend/apps/visit/app/ports/input/get_next_visit_draft_use_case.py backend/apps/visit/app/ports/input/get_visit_defaults_use_case.py backend/apps/visit/app/ports/input/visit_myself_use_case.py backend/apps/visit/app/ports/output/visit_myself_record_port.py backend/apps/visit/app/ports/output/visit_repository.py backend/apps/visit/app/use_cases/get_next_visit_draft_interactor.py backend/apps/visit/app/use_cases/get_visit_defaults_interactor.py backend/apps/visit/app/use_cases/visit_myself_interactor.py backend/apps/visit/dependencies/get_next_visit_draft_provider.py backend/apps/visit/dependencies/get_visit_defaults_provider.py backend/apps/visit/dependencies/visit_myself_provider.py backend/apps/visit/tests/adapter/test_get_next_visit_draft_router.py backend/apps/visit/tests/adapter/test_get_visit_defaults_router.py backend/apps/visit/tests/adapter/test_visit_myself_router.py backend/apps/visit/tests/adapter/test_visit_pg_repository.py backend/apps/visit/tests/app/use_cases/test_get_next_visit_draft_interactor.py backend/apps/visit/tests/app/use_cases/test_get_visit_defaults_interactor.py backend/apps/visit/tests/app/use_cases/test_visit_myself_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/main.py
git commit -m "feat(visit): 지난번처럼 기본값, 다음 예약 초안, 자기소개"
```

---

### Task 12: 허브 포트 `VisitLedgerPort`와 customer 쪽 변경 — 409 셋, 방문 메모 비우기, 노쇼·다가오는 예약, 최근 방문순

반대 방향 허브 포트. visit 이 구현하고(HTTP 없는 슬라이스 `visit_ledger`) customer 가 `dependencies/hub_ports.get_visit_ledger` 자리로 받는다. customer 는 **고객 행을 잠근 뒤에** 묻는다 — 예약 쓰기도 같은 고객 행을 먼저 잠그므로 확인과 쓰기 사이에 예약이 새로 생기지 않는다. 반려동물 삭제는 방문이 하나라도 있으면(취소 포함) 409 `PET_HAS_VISITS`(`LAST_PET`보다 먼저), 무지개다리는 앞으로의 예약이 남았으면 409 `PET_HAS_UPCOMING_VISITS`, 익명화는 409 `CUSTOMER_HAS_UPCOMING_VISITS`(V7). 익명화는 방문 메모도 비운다(V11). '앞으로의 예약'은 예약됨·미용 중이다(날짜가 지났어도). 고객 상세(GET)만 노쇼 횟수와 다가오는 예약(오늘 이후, 최대 3건, 아이 이름·매장 시간대)을 더한다 — 등록·수정 응답은 그대로다. 고객 목록에 `sort=last_visit`(마지막 방문 내림차순, 방문 없는 가족은 맨 뒤 — 커서의 빈 문자열 키가 "방문 없음")을 더한다. 인터랙터 생성자가 바뀌어 기존 customer 테스트 넷과 경합 테스트(`tests/integration/test_customer_locking.py`)를 고친다 — 경합 테스트에는 진입점이 꽂는 것과 같은 실제 장부 구현을 넘긴다.

**Files:**
- Modify: `backend/apps/customer/domain/errors.py`
- Create: `backend/apps/hub/app/dtos/upcoming_visit.py`
- Create: `backend/apps/hub/app/ports/visit_ledger_port.py`
- Modify: `backend/apps/customer/app/dtos/customer_search_dto.py`
- Modify: `backend/apps/customer/app/dtos/customer_view_dto.py`
- Modify: `backend/apps/customer/app/ports/input/get_customer_use_case.py`
- Modify: `backend/apps/customer/app/use_cases/customer_myself_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/delete_customer_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/delete_pet_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/get_customer_interactor.py`
- Modify: `backend/apps/customer/app/use_cases/mark_pet_passed_away_interactor.py`
- Modify: `backend/apps/visit/app/ports/output/visit_repository.py`
- Create: `backend/apps/visit/app/use_cases/visit_ledger_interactor.py`
- Modify: `backend/apps/customer/adapter/inbound/api/error_map.py`
- Modify: `backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py`
- Modify: `backend/apps/customer/adapter/inbound/api/v1/get_customer_router.py`
- Modify: `backend/apps/customer/adapter/inbound/api/v1/list_customers_router.py`
- Modify: `backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py`
- Modify: `backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py`
- Modify: `backend/apps/customer/dependencies/delete_customer_provider.py`
- Modify: `backend/apps/customer/dependencies/delete_pet_provider.py`
- Modify: `backend/apps/customer/dependencies/get_customer_provider.py`
- Create: `backend/apps/customer/dependencies/hub_ports.py`
- Modify: `backend/apps/customer/dependencies/mark_pet_passed_away_provider.py`
- Create: `backend/apps/visit/dependencies/visit_ledger_provider.py`
- Modify: `backend/main.py`
- Modify (test): `backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py`
- Modify (test): `backend/apps/customer/tests/adapter/test_get_customer_router.py`
- Modify (test): `backend/apps/customer/tests/adapter/test_list_customers_router.py`
- Modify (test): `backend/apps/customer/tests/app/use_cases/test_delete_customer_interactor.py`
- Modify (test): `backend/apps/customer/tests/app/use_cases/test_delete_pet_interactor.py`
- Modify (test): `backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py`
- Modify (test): `backend/apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py`
- Modify (test): `backend/apps/customer/tests/helpers/fakes.py`
- Modify (test): `backend/apps/visit/tests/adapter/test_visit_pg_repository.py`
- Test: `backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py`
- Modify (test): `backend/apps/visit/tests/helpers/fakes.py`
- Modify (test): `backend/tests/integration/test_customer_locking.py`

**Interfaces:**
- Consumes: Task 7~11 의 `VisitRepository`, Task 4 의 검색 포트
- Produces:
  - `hub.app.dtos.upcoming_visit.UpcomingVisit(visit_id, pet_id, starts_at)`
  - `hub.app.ports.visit_ledger_port.VisitLedgerPort`: `pet_has_visits`, `pet_has_upcoming`, `customer_has_upcoming`, `no_show_count`, `upcoming_for_customer(ctx, customer_id, limit)`, `clear_customer_memos`
  - `visit.dependencies.visit_ledger_provider.get_visit_ledger_use_case(db)`, `customer.dependencies.hub_ports.get_visit_ledger`(자리)
  - `VisitRepository.pet_has_visits(ctx, pet_id, active_only)`, `customer_has_active`, `list_active_from(ctx, customer_id, since, limit)`, `clear_memos`
  - customer: 오류 `PetHasVisitsError`·`PetHasUpcomingVisitsError`·`CustomerHasUpcomingVisitsError`(409), `CustomerOverviewView`·`UpcomingVisitView`, `CustomerOverviewSchema`, `SortKey`에 `"last_visit"`, 테스트 스텁 `FakeLedger`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py` (수정):
```diff
@@ -1,5 +1,6 @@
 import base64
 import json
+from datetime import datetime, timezone
 
 import pytest
 from sqlalchemy import text
@@ -184,8 +185,6 @@ async def _last_visit(session, customer_id):
 
 async def test_마지막_방문_시각을_바꾸고_다시_만들어도_지킨다(db_session):
     """원본은 visits 라 검색 줄을 다시 만들 때(가족 수정) 이 칸은 건드리지 않는다."""
-    from datetime import datetime, timezone
-
     customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
     at = datetime(2026, 9, 23, 5, tzinfo=timezone.utc)
     search = CustomerSearchPgAdapter(db_session)
@@ -198,9 +197,33 @@ async def test_마지막_방문_시각을_바꾸고_다시_만들어도_지킨
 
 
 async def test_다른_매장_컨텍스트로는_마지막_방문_시각을_바꾸지_못한다(db_session):
-    from datetime import datetime, timezone
-
     customer_id = await _family(db_session, "김민지", "01012345678", ["콩이"])
     await CustomerSearchPgAdapter(db_session).set_last_visit(
         B, customer_id, datetime(2026, 9, 23, tzinfo=timezone.utc))
     assert await _last_visit(db_session, customer_id) is None
+
+
+async def test_최근_방문순은_마지막_방문_시각_내림차순이고_방문_없는_가족은_맨_뒤다(db_session):
+    """쪽을 1가족씩 넘겨도 빠지거나 겹치지 않는다 — 같은 시각, 방문 없음(NULL) 경계 포함."""
+    search = CustomerSearchPgAdapter(db_session)
+    ids = [await _family(db_session, f"가족{i}", f"0101234{i:04d}", ["콩이"]) for i in range(6)]
+    at = lambda day: datetime(2026, 9, day, 5, tzinfo=timezone.utc)   # noqa: E731
+    for customer_id, day in zip(ids, (2, 20, 20, None, 9, None)):
+        await search.set_last_visit(A, customer_id, at(day) if day else None)
+
+    seen, cursor = [], None
+    while True:
+        page = await _find(db_session, "", sort="last_visit", cursor=cursor, limit=1)
+        seen += page.customer_ids
+        if page.next_cursor is None:
+            break
+        cursor = page.next_cursor
+    assert seen == [ids[2], ids[1], ids[4], ids[0], ids[5], ids[3]]
+
+
+async def test_최근_방문순의_커서를_다른_정렬에_쓰면_VALIDATION_ERROR_다(db_session):
+    for i in range(3):
+        await _family(db_session, f"이름{i}", f"0101234{i:04d}", ["콩이"])
+    page = await _find(db_session, "", sort="last_visit", limit=1)
+    with pytest.raises(CustomerInputError):
+        await _find(db_session, "", sort="recent", cursor=page.next_cursor)
```

`backend/apps/customer/tests/adapter/test_get_customer_router.py` (수정):
```diff
@@ -2,16 +2,21 @@ from httpx import ASGITransport, AsyncClient
 
 from customer.adapter.inbound.api.v1.get_customer_router import get_customer_router
 from customer.dependencies.get_customer_provider import get_get_customer_use_case
+from customer.app.dtos.customer_view_dto import CustomerOverviewView, UpcomingVisitView
 from customer.domain.errors import (
+    CustomerHasUpcomingVisitsError,
     CustomerInputError,
     CustomerNotFoundError,
     CustomerPhoneTakenError,
     LastPetError,
+    PetHasUpcomingVisitsError,
+    PetHasVisitsError,
     PetHealthConflictError,
     PetHealthRequiredError,
     PetNotFoundError,
+    PetPassedAwayError,
 )
-from customer.tests.helpers.api import NO_WRITE, build_app, customer_detail_view
+from customer.tests.helpers.api import NOW, NO_WRITE, build_app, customer_detail_view
 
 
 class _StubUseCase:
@@ -23,7 +28,11 @@ class _StubUseCase:
         self.queries.append(query)
         if self.error:
             raise self.error
-        return customer_detail_view()
+        detail = customer_detail_view()
+        return CustomerOverviewView(
+            customer=detail.customer, pets=detail.pets, no_show_count=2,
+            upcoming_visits=[UpcomingVisitView(visit_id=7, pet_id=101, pet_name="콩이", starts_at=NOW)],
+        )
 
 
 async def _get(stub, path="/v1/shops/3/customers/1"):
@@ -37,6 +46,9 @@ async def test_멤버는_전체_번호가_든_고객_상세를_본다():
     response = await _get(stub)
     assert response.status_code == 200
     assert response.json()["customer"]["phone"] == "01012345678"
+    assert response.json()["no_show_count"] == 2
+    assert response.json()["upcoming_visits"] == [
+        {"visit_id": 7, "pet_id": 101, "pet_name": "콩이", "starts_at": "2026-09-22T01:00:00Z"}]
     assert (stub.queries[0].ctx.shop_id, stub.queries[0].customer_id) == (3, 1)
 
 
@@ -58,6 +70,10 @@ async def test_도메인_오류는_설계의_상태_코드와_코드로_나간
         (CustomerInputError("x"), 422, "VALIDATION_ERROR"),
         (PetHealthRequiredError("x"), 422, "PET_HEALTH_REQUIRED"),
         (PetHealthConflictError("x"), 422, "PET_HEALTH_CONFLICT"),
+        (PetHasVisitsError("x"), 409, "PET_HAS_VISITS"),
+        (PetHasUpcomingVisitsError("x"), 409, "PET_HAS_UPCOMING_VISITS"),
+        (CustomerHasUpcomingVisitsError("x"), 409, "CUSTOMER_HAS_UPCOMING_VISITS"),
+        (PetPassedAwayError("x"), 422, "PET_PASSED_AWAY"),
     ]
     for error, status, code in cases:
         response = await _get(_StubUseCase(error))
```

`backend/apps/customer/tests/adapter/test_list_customers_router.py` (수정):
```diff
@@ -43,6 +43,12 @@ async def test_검색어_정렬_포함_여부_커서를_넘긴다():
     assert (query.q, query.sort, query.include_passed, query.cursor) == ("5678 콩", "name", True, "abc")
 
 
+async def test_최근_방문순_정렬을_받는다():
+    stub = _StubUseCase()
+    assert (await _get(stub, "/v1/shops/3/customers?sort=last_visit")).status_code == 200
+    assert stub.queries[0].sort == "last_visit"
+
+
 async def test_모르는_정렬이나_너무_긴_검색어는_422_다():
     for path in ("/v1/shops/3/customers?sort=visit", "/v1/shops/3/customers?q=" + "가" * 51):
         response = await _get(_StubUseCase(), path)
```

`backend/apps/customer/tests/app/use_cases/test_delete_customer_interactor.py` (수정):
```diff
@@ -2,25 +2,40 @@ import pytest
 
 from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
 from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
-from customer.domain.errors import CustomerNotFoundError
-from customer.tests.helpers.fakes import family
+from customer.domain.errors import CustomerHasUpcomingVisitsError, CustomerNotFoundError
+from customer.tests.helpers.fakes import FakeLedger, family
 from customer.tests.helpers.profiles import ctx
 
 
-async def test_잠근_뒤_익명화하고_검색_줄을_정리한다():
+async def test_잠근_뒤_익명화하고_방문_메모와_검색_줄을_정리한다():
     journal, customers, _, _, search = family()
     customer = customers.seed()
-    await DeleteCustomerInteractor(customers, search).delete_customer(
+    await DeleteCustomerInteractor(customers, search, FakeLedger(journal)).delete_customer(
         DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
     )
-    assert journal == [("lock_customer", customer.id), ("anonymize", customer.id), ("rebuild", customer.id)]
+    assert journal == [("lock_customer", customer.id), ("anonymize", customer.id),
+                       ("clear_visit_memos", customer.id), ("rebuild", customer.id)]
+
+
+async def test_앞으로의_예약이_남았으면_CUSTOMER_HAS_UPCOMING_VISITS_다():
+    """V7 — 익명화한 고객에게 앞으로의 예약이 남지 않게 한다. 고객 행을 잠근 뒤에 묻는다."""
+    journal, customers, _, _, search = family()
+    customer = customers.seed()
+    ledger = FakeLedger(journal)
+    ledger.customers_with_upcoming.add(customer.id)
+    with pytest.raises(CustomerHasUpcomingVisitsError):
+        await DeleteCustomerInteractor(customers, search, ledger).delete_customer(
+            DeleteCustomerCommand(ctx=ctx(), customer_id=customer.id)
+        )
+    assert journal == [("lock_customer", customer.id)]
+    assert customer.id in customers.rows
 
 
 async def test_이미_삭제했거나_다른_매장이면_404_다():
     journal, customers, _, _, search = family()
     customer = customers.seed(shop_id=2)
     with pytest.raises(CustomerNotFoundError):
-        await DeleteCustomerInteractor(customers, search).delete_customer(
+        await DeleteCustomerInteractor(customers, search, FakeLedger(journal)).delete_customer(
             DeleteCustomerCommand(ctx=ctx(shop_id=1), customer_id=customer.id)
         )
     assert [entry[0] for entry in journal] == ["lock_customer"]
```

`backend/apps/customer/tests/app/use_cases/test_delete_pet_interactor.py` (수정):
```diff
@@ -2,8 +2,8 @@ import pytest
 
 from customer.app.dtos.delete_pet_dto import DeletePetCommand
 from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
-from customer.domain.errors import LastPetError, PetNotFoundError
-from customer.tests.helpers.fakes import family
+from customer.domain.errors import LastPetError, PetHasVisitsError, PetNotFoundError
+from customer.tests.helpers.fakes import FakeLedger, family
 from customer.tests.helpers.profiles import ctx
 
 
@@ -12,7 +12,7 @@ async def test_고객을_잠근_뒤_세고_지우고_검색_줄을_다시_만든
     customer = customers.seed()
     kong = pets.seed(customer.id, "콩이")
     pets.seed(customer.id, "두부")
-    await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
+    await DeletePetInteractor(pets, search, FakeLedger(journal)).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
     assert journal == [("lock_customer", customer.id), ("delete_pet", kong.id), ("rebuild", customer.id)]
 
 
@@ -20,7 +20,7 @@ async def test_마지막_반려동물이면_LAST_PET_이다():
     journal, customers, pets, _, search = family()
     only = pets.seed(customers.seed().id)
     with pytest.raises(LastPetError):
-        await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=only.id))
+        await DeletePetInteractor(pets, search, FakeLedger(journal)).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=only.id))
     assert only.id in pets.rows
     assert [entry[0] for entry in journal] == ["lock_customer"]
 
@@ -31,7 +31,7 @@ async def test_무지개다리인_아이도_수에_들어간다():
     customer = customers.seed()
     kong = pets.seed(customer.id, "콩이")
     pets.seed(customer.id, "별이", passed_away=True)
-    await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
+    await DeletePetInteractor(pets, search, FakeLedger(journal)).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
     assert kong.id not in pets.rows
 
 
@@ -39,4 +39,18 @@ async def test_다른_매장의_반려동물은_404_다():
     journal, customers, pets, _, search = family()
     pet = pets.seed(customers.seed(shop_id=2).id)
     with pytest.raises(PetNotFoundError):
-        await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=ctx(shop_id=1), pet_id=pet.id))
+        await DeletePetInteractor(pets, search, FakeLedger(journal)).delete_pet(DeletePetCommand(ctx=ctx(shop_id=1), pet_id=pet.id))
+
+
+async def test_방문_기록이_있는_반려동물은_PET_HAS_VISITS_다():
+    """취소된 방문만 있어도 지우지 않는다 — 무지개다리를 쓴다. 고객 행을 잠근 뒤에 묻는다."""
+    journal, customers, pets, _, search = family()
+    customer = customers.seed()
+    kong = pets.seed(customer.id, "콩이")
+    pets.seed(customer.id, "두부")
+    ledger = FakeLedger(journal)
+    ledger.pets_with_visits.add(kong.id)
+    with pytest.raises(PetHasVisitsError):
+        await DeletePetInteractor(pets, search, ledger).delete_pet(DeletePetCommand(ctx=ctx(), pet_id=kong.id))
+    assert kong.id in pets.rows
+    assert journal == [("lock_customer", customer.id)]
```

`backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py` (수정):
```diff
@@ -1,28 +1,50 @@
+from datetime import datetime, timezone
+
 import pytest
 
 from customer.app.dtos.get_customer_dto import GetCustomerQuery
 from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
 from customer.domain.errors import CustomerNotFoundError
-from customer.tests.helpers.fakes import family, today
+from customer.tests.helpers.fakes import FakeLedger, family, today
 from customer.tests.helpers.profiles import ctx
+from hub.app.dtos.upcoming_visit import UpcomingVisit
 
 
 async def test_보호자_전체와_반려동물_전체를_돌려준다():
-    _, customers, pets, _, _ = family()
+    journal, customers, pets, _, _ = family()
     customer = customers.seed()
     pets.seed(customer.id, "콩이")
     pets.seed(customer.id, "별이", passed_away=True)
-    view = await GetCustomerInteractor(customers, pets, today).get_customer(
+    view = await GetCustomerInteractor(customers, pets, FakeLedger(journal), today).get_customer(
         GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
     )
     assert view.customer.phone == "01012345678"   # 상세는 전체 번호다
     assert [(p.name, p.passed_away_at is not None) for p in view.pets] == [("콩이", False), ("별이", True)]
+    assert (view.no_show_count, view.upcoming_visits) == (0, [])
+
+
+async def test_노쇼_횟수와_다가오는_예약을_아이_이름과_함께_매장_시간대로():
+    journal, customers, pets, _, _ = family()
+    customer = customers.seed()
+    kong = pets.seed(customer.id, "콩이")
+    ledger = FakeLedger(journal)
+    ledger.no_shows[customer.id] = 2
+    ledger.upcoming[customer.id] = [
+        UpcomingVisit(visit_id=7, pet_id=kong.id, starts_at=datetime(2026, 10, 2, 5, tzinfo=timezone.utc)),
+        UpcomingVisit(visit_id=8, pet_id=None, starts_at=datetime(2026, 10, 3, 5, tzinfo=timezone.utc)),
+    ]
+    view = await GetCustomerInteractor(customers, pets, ledger, today).get_customer(
+        GetCustomerQuery(ctx=ctx(), customer_id=customer.id)
+    )
+    assert view.no_show_count == 2
+    assert [(u.visit_id, u.pet_name, u.starts_at.isoformat()) for u in view.upcoming_visits] == [
+        (7, "콩이", "2026-10-02T14:00:00+09:00"), (8, None, "2026-10-03T14:00:00+09:00")]
 
 
 async def test_다른_매장의_고객은_404_다():
-    _, customers, pets, _, _ = family()
+    journal, customers, pets, _, _ = family()
     customer = customers.seed(shop_id=2)
     with pytest.raises(CustomerNotFoundError):
-        await GetCustomerInteractor(customers, pets, today).get_customer(
+        await GetCustomerInteractor(customers, pets, FakeLedger(journal), today).get_customer(
             GetCustomerQuery(ctx=ctx(shop_id=1), customer_id=customer.id)
         )
```

`backend/apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py` (수정):
```diff
@@ -2,15 +2,15 @@ import pytest
 
 from customer.app.dtos.mark_pet_passed_away_dto import MarkPetPassedAwayCommand
 from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
-from customer.domain.errors import PetNotFoundError
-from customer.tests.helpers.fakes import family, today
+from customer.domain.errors import PetHasUpcomingVisitsError, PetNotFoundError
+from customer.tests.helpers.fakes import FakeLedger, family, today
 from customer.tests.helpers.profiles import ctx
 
 
 async def test_고객을_잠근_뒤_무지개다리를_표시한다():
     journal, customers, pets, _, search = family()
     pet = pets.seed(customers.seed().id)
-    view = await MarkPetPassedAwayInteractor(customers, pets, search, today).mark_pet_passed_away(
+    view = await MarkPetPassedAwayInteractor(customers, pets, search, FakeLedger(journal), today).mark_pet_passed_away(
         MarkPetPassedAwayCommand(ctx=ctx(), pet_id=pet.id)
     )
     assert view.pet.passed_away_at is not None
@@ -22,7 +22,20 @@ async def test_다른_매장의_반려동물은_404_다():
     journal, customers, pets, _, search = family()
     pet = pets.seed(customers.seed(shop_id=2).id)
     with pytest.raises(PetNotFoundError):
-        await MarkPetPassedAwayInteractor(customers, pets, search, today).mark_pet_passed_away(
+        await MarkPetPassedAwayInteractor(customers, pets, search, FakeLedger(journal), today).mark_pet_passed_away(
             MarkPetPassedAwayCommand(ctx=ctx(shop_id=1), pet_id=pet.id)
         )
     assert journal == []
+
+
+async def test_앞으로의_예약이_남은_아이는_PET_HAS_UPCOMING_VISITS_다():
+    journal, customers, pets, _, search = family()
+    pet = pets.seed(customers.seed().id)
+    ledger = FakeLedger(journal)
+    ledger.pets_with_upcoming.add(pet.id)
+    with pytest.raises(PetHasUpcomingVisitsError):
+        await MarkPetPassedAwayInteractor(customers, pets, search, ledger, today).mark_pet_passed_away(
+            MarkPetPassedAwayCommand(ctx=ctx(), pet_id=pet.id)
+        )
+    assert pets.rows[pet.id].passed_away_at is None
+    assert journal == [("lock_customer", pet.customer_id)]
```

`backend/apps/customer/tests/helpers/fakes.py` (수정):
```diff
@@ -183,6 +183,36 @@ class FakeSearch:
         return self.pet_count
 
 
+class FakeLedger:
+    """VisitLedgerPort 스텁. 반려동물·고객마다 방문이 있는지, 앞으로의 예약이 있는지를 정해 둔다."""
+
+    def __init__(self, journal: Journal) -> None:
+        self.journal = journal
+        self.pets_with_visits: set[int] = set()
+        self.pets_with_upcoming: set[int] = set()
+        self.customers_with_upcoming: set[int] = set()
+        self.no_shows: dict[int, int] = {}
+        self.upcoming: dict[int, list] = {}
+
+    async def pet_has_visits(self, ctx, pet_id):
+        return pet_id in self.pets_with_visits | self.pets_with_upcoming
+
+    async def pet_has_upcoming(self, ctx, pet_id):
+        return pet_id in self.pets_with_upcoming
+
+    async def customer_has_upcoming(self, ctx, customer_id):
+        return customer_id in self.customers_with_upcoming
+
+    async def no_show_count(self, ctx, customer_id):
+        return self.no_shows.get(customer_id, 0)
+
+    async def upcoming_for_customer(self, ctx, customer_id, limit):
+        return self.upcoming.get(customer_id, [])[:limit]
+
+    async def clear_customer_memos(self, ctx, customer_id):
+        self.journal.append(("clear_visit_memos", customer_id))
+
+
 def family():
     """스텁 한 벌을 같은 호출 기록으로 묶어 만든다."""
     journal = Journal()
```

`backend/apps/visit/tests/adapter/test_visit_pg_repository.py` (수정):
```diff
@@ -174,3 +174,18 @@ async def test_아이의_지난_완료와_완료_시각들(db_session):
     assert await repo.last_completed_of_pet(A, 999) is None
     assert await repo.completed_starts(A, 1, 101, limit=2) == [kst(9, 2, 14), kst(8, 1, 14)]
     assert await repo.completed_starts(A, 1, None, limit=2) == [kst(9, 4, 14)]
+
+
+async def test_장부_질문들(db_session):
+    repo = VisitPgRepository(db_session)
+    await insert_visit(db_session, kst(9, 1, 14), "canceled", pet_id=101)
+    await insert_visit(db_session, kst(9, 20, 14), "reserved", pet_id=102, memo="메모")
+    await insert_visit(db_session, kst(10, 2, 14), "reserved", pet_id=102)
+    await insert_visit(db_session, kst(10, 2, 14), "reserved", shop_id=2, customer_id=1, pet_id=103, memo="남의")
+    assert (await repo.pet_has_visits(A, 101, active_only=False), await repo.pet_has_visits(A, 101, active_only=True)) == (True, False)
+    assert await repo.pet_has_visits(A, 103, active_only=False) is False
+    assert (await repo.customer_has_active(A, 1), await repo.customer_has_active(A, 2)) == (True, False)
+    assert [v.starts_at for v in await repo.list_active_from(A, 1, kst(9, 23), 5)] == [kst(10, 2, 14)]
+    await repo.clear_memos(A, 1)
+    assert {v.memo for v in await repo.list_between(A, kst(9, 1), kst(11, 1))} == {None}
+    assert [v.memo for v in await repo.list_between(B, kst(9, 1), kst(11, 1))] == ["남의"]
```

`backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py`:
```python
from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.tests.helpers.builders import ctx, kst
from visit.tests.helpers.fakes import FakeVisits

NOW = kst(9, 23, 15)


def _ledger():
    visits = FakeVisits()
    return visits, VisitLedgerInteractor(visits, now=lambda: NOW)


async def test_반려동물의_방문과_앞으로의_예약():
    visits, ledger = _ledger()
    visits.seed(pet_id=101, status="canceled", canceled_at=NOW, cancel_reason="shop_reason")
    visits.seed(pet_id=102, starts_at=kst(9, 20, 10))   # 정리 안 된 지난 예약도 앞으로의 예약이다
    visits.seed(pet_id=103, shop_id=2)
    assert (await ledger.pet_has_visits(ctx(), 101), await ledger.pet_has_upcoming(ctx(), 101)) == (True, False)
    assert (await ledger.pet_has_visits(ctx(), 102), await ledger.pet_has_upcoming(ctx(), 102)) == (True, True)
    assert await ledger.pet_has_visits(ctx(), 103) is False   # 다른 매장


async def test_고객의_앞으로의_예약과_노쇼():
    visits, ledger = _ledger()
    visits.seed(customer_id=1, status="no_show")
    visits.seed(customer_id=2, starts_at=kst(9, 23, 16), status="in_progress", started_at=kst(9, 23, 16))
    assert (await ledger.customer_has_upcoming(ctx(), 1), await ledger.no_show_count(ctx(), 1)) == (False, 1)
    assert await ledger.customer_has_upcoming(ctx(), 2) is True


async def test_다가오는_예약은_오늘부터_시작_순으로():
    visits, ledger = _ledger()
    visits.seed(customer_id=1, pet_id=101, starts_at=kst(9, 20, 10))       # 정리 안 된 지난 예약 — 보이지 않는다
    later = visits.seed(customer_id=1, pet_id=101, starts_at=kst(10, 2, 14))
    today = visits.seed(customer_id=1, pet_id=None, starts_at=kst(9, 23, 10))
    visits.seed(customer_id=1, pet_id=102, starts_at=kst(10, 9, 14))
    found = await ledger.upcoming_for_customer(ctx(), 1, limit=2)
    assert [(u.visit_id, u.pet_id) for u in found] == [(today.id, None), (later.id, 101)]


async def test_메모를_비운다():
    visits, ledger = _ledger()
    mine = visits.seed(customer_id=1, memo="010-1234-5678 로 연락")
    other = visits.seed(customer_id=2, memo="남의 메모")
    await ledger.clear_customer_memos(ctx(), 1)
    assert (visits.rows[mine.id].memo, visits.rows[other.id].memo) == (None, "남의 메모")
```

`backend/apps/visit/tests/helpers/fakes.py` (수정):
```diff
@@ -249,6 +249,22 @@ class FakeVisits:
                 and v.status == "completed"]
         return sorted(done, reverse=True)[:limit]
 
+    async def pet_has_visits(self, ctx, pet_id, active_only):
+        return any(v.pet_id == pet_id and (v.is_active or not active_only) for v in self._mine(ctx))
+
+    async def customer_has_active(self, ctx, customer_id):
+        return any(v.customer_id == customer_id and v.is_active for v in self._mine(ctx))
+
+    async def list_active_from(self, ctx, customer_id, since, limit):
+        return [v for v in self._mine(ctx) if v.customer_id == customer_id and v.is_active
+                and v.starts_at >= since][:limit]
+
+    async def clear_memos(self, ctx, customer_id):
+        for v in self._mine(ctx):
+            if v.customer_id == customer_id:
+                self.rows[v.id] = replace(v, memo=None)
+        self.journal.append(("clear_memos", customer_id))
+
     async def count_no_show(self, ctx, customer_id):
         return sum(v.customer_id == customer_id and v.status == "no_show" for v in self._mine(ctx))
```

`backend/tests/integration/test_customer_locking.py` (수정):
```diff
@@ -26,6 +26,9 @@ from customer.domain.errors import CustomerNotFoundError, CustomerPhoneTakenErro
 from customer.tests.helpers.fakes import today
 from customer.tests.helpers.inputs import customer_input, pet_input
 from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
+from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
+from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
+from visit.domain.services.visit_schedule import utc_now
 
 pytestmark = pytest.mark.integration
 
@@ -38,6 +41,11 @@ def _repos(session):
             ConditionTypePgRepository(session), CustomerSearchPgAdapter(session))
 
 
+def _ledger(session):
+    """customer 유스케이스가 묻는 방문 장부 — 진입점이 꽂는 것과 같은 실제 구현(visit)."""
+    return VisitLedgerInteractor(VisitPgRepository(session), now=utc_now)
+
+
 def _register(session, name):
     customers, pets, types, search = _repos(session)
     return RegisterCustomerInteractor(customers, pets, types, search, today).register_customer(
@@ -89,7 +97,7 @@ async def test_익명화가_고객을_쥔_동안_반려동물_추가는_기다
 
     async with factory() as deleting, factory() as adding:
         customers, _, _, search = _repos(deleting)
-        await DeleteCustomerInteractor(customers, search).delete_customer(
+        await DeleteCustomerInteractor(customers, search, _ledger(deleting)).delete_customer(
             DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id)
         )
         customers, pets, types, search = _repos(adding)
@@ -140,10 +148,10 @@ async def test_마지막_두_마리를_동시에_지우면_하나는_LAST_PET_
 
     async with factory() as first, factory() as second:
         _, pets, _, search = _repos(first)
-        await DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=kong))
+        await DeletePetInteractor(pets, search, _ledger(first)).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=kong))
         _, pets, _, search = _repos(second)
         late = asyncio.create_task(
-            DeletePetInteractor(pets, search).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=dubu))
+            DeletePetInteractor(pets, search, _ledger(second)).delete_pet(DeletePetCommand(ctx=SHOP, pet_id=dubu))
         )
         assert await _still_waiting(late)
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests apps/customer/tests tests/integration/test_customer_locking.py tests/test_hub_port_binding.py -q -p no:cacheprovider
```

Expected: `TypeError: ... unexpected keyword argument 'ledger'`·`ModuleNotFoundError` 등으로 실패한다.

- [ ] **Step 3: 구현한다**

`backend/apps/customer/domain/errors.py` (수정):
```diff
@@ -34,6 +34,24 @@ class PetHealthConflictError(CustomerError):
     code = "PET_HEALTH_CONFLICT"
 
 
+class PetHasVisitsError(CustomerError):
+    """방문 기록이 있는 반려동물은 지우지 않는다 — 무지개다리를 쓴다."""
+
+    code = "PET_HAS_VISITS"
+
+
+class PetHasUpcomingVisitsError(CustomerError):
+    """앞으로의 예약이 남은 아이는 무지개다리로 표시하지 않는다 — 예약을 먼저 취소한다."""
+
+    code = "PET_HAS_UPCOMING_VISITS"
+
+
+class CustomerHasUpcomingVisitsError(CustomerError):
+    """앞으로의 예약이 남은 고객은 익명화하지 않는다 — 예약을 먼저 취소한다."""
+
+    code = "CUSTOMER_HAS_UPCOMING_VISITS"
+
+
 class PetPassedAwayError(CustomerError):
     """무지개다리 아이에게 예약을 잡으려 했다."""
```

`backend/apps/hub/app/dtos/upcoming_visit.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class UpcomingVisit:
    """다가오는 예약 한 건(고객 상세에 보여 줄 것). pet_id 가 None 이면 보호자만의 방문이다."""

    visit_id: int
    pet_id: int | None
    starts_at: datetime
```

`backend/apps/hub/app/ports/visit_ledger_port.py`:
```python
from __future__ import annotations

from abc import ABC, abstractmethod

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.upcoming_visit import UpcomingVisit


class VisitLedgerPort(ABC):
    """구현: visit. 사용: customer (반려동물 삭제·무지개다리·고객 익명화의 규칙, 고객 상세).

    '앞으로의 예약'은 예약됨·미용 중인 방문이다 — 날짜가 지났어도 정리하지 않았으면 여기에 든다.
    customer 는 고객 행을 잠근 **뒤에** 부른다(잠금 순서: 고객 행 → 방문 행). 방문을 쓰는 visit 유스케이스도
    같은 고객 행을 먼저 잠그므로, 확인과 쓰기 사이에 예약이 새로 생기지 않는다.
    """

    @abstractmethod
    async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
        """상태와 상관없이 방문이 하나라도 있는가(취소 포함)."""

    @abstractmethod
    async def pet_has_upcoming(self, ctx: ShopContext, pet_id: int) -> bool: ...

    @abstractmethod
    async def customer_has_upcoming(self, ctx: ShopContext, customer_id: int) -> bool: ...

    @abstractmethod
    async def no_show_count(self, ctx: ShopContext, customer_id: int) -> int: ...

    @abstractmethod
    async def upcoming_for_customer(self, ctx: ShopContext, customer_id: int, limit: int) -> list[UpcomingVisit]:
        """오늘(매장 시간대) 이후에 시작하는 앞으로의 예약, 시작 순으로 limit 개."""

    @abstractmethod
    async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
        """그 고객 방문들의 메모를 비운다 — 익명화 때 방문 메모에 남은 개인정보를 지운다(V11)."""
```

`backend/apps/customer/app/dtos/customer_search_dto.py` (수정):
```diff
@@ -5,7 +5,7 @@ from typing import Literal
 
 from customer.domain.services.search_terms import SearchWord
 
-SortKey = Literal["recent", "name"]
+SortKey = Literal["recent", "name", "last_visit"]
 PAGE_SIZE = 30
```

`backend/apps/customer/app/dtos/customer_view_dto.py` (수정):
```diff
@@ -81,6 +81,24 @@ class CustomerDetailView:
     pets: list[PetView]
 
 
+@dataclass(frozen=True)
+class UpcomingVisitView:
+    visit_id: int
+    pet_id: int | None      # None 이면 보호자만의 방문
+    pet_name: str | None
+    starts_at: datetime     # 매장 시간대
+
+
+@dataclass(frozen=True)
+class CustomerOverviewView:
+    """고객 상세 화면 — 보호자·반려동물에 방문 요약(노쇼 횟수, 다가오는 예약)을 더한다."""
+
+    customer: CustomerView
+    pets: list[PetView]
+    no_show_count: int
+    upcoming_visits: list[UpcomingVisitView]
+
+
 @dataclass(frozen=True)
 class OwnerSummaryView:
     """반려동물 화면의 보호자 요약. 번호는 가린다 — 전체 번호는 고객 상세에서만 준다."""
```

`backend/apps/customer/app/ports/input/get_customer_use_case.py` (수정):
```diff
@@ -2,10 +2,10 @@ from __future__ import annotations
 
 from abc import ABC, abstractmethod
 
-from customer.app.dtos.customer_view_dto import CustomerDetailView
+from customer.app.dtos.customer_view_dto import CustomerOverviewView
 from customer.app.dtos.get_customer_dto import GetCustomerQuery
 
 
 class GetCustomerUseCase(ABC):
     @abstractmethod
-    async def get_customer(self, query: GetCustomerQuery) -> CustomerDetailView: ...
+    async def get_customer(self, query: GetCustomerQuery) -> CustomerOverviewView: ...
```

`backend/apps/customer/app/use_cases/customer_myself_interactor.py` (수정):
```diff
@@ -18,7 +18,7 @@ class CustomerMyselfInteractor(CustomerMyselfUseCase):
                 "매장의 고객(보호자)과 반려동물, 반려동물의 질병을 관리합니다. "
                 "경로는 모두 /v1/shops/{shop_id} 아래이고 매 요청마다 매장 소속을 확인합니다. "
                 "GET /customers 는 가족 카드 목록입니다(q 검색: 전화 뒷자리·보호자 이름·반려동물 이름·한글 초성, "
-                "sort=recent|name, include_passed, cursor, 한 쪽에 30 가족). "
+                "sort=recent|name|last_visit, include_passed, cursor, 한 쪽에 30 가족). "
                 "GET /customers/lookup?phone= 는 등록 전 번호 조회, POST /customers 는 보호자와 첫 반려동물 등록, "
                 "GET·PUT·DELETE /customers/{customer_id} 는 고객 상세·수정·삭제, "
                 "POST /customers/{customer_id}/pets 는 반려동물 추가입니다. "
@@ -31,6 +31,9 @@ class CustomerMyselfInteractor(CustomerMyselfUseCase):
                 "고객 삭제는 이름·전화·메모와 반려동물 이름·메모·질병을 지우는 익명화이고, "
                 "삭제한 고객은 조회·검색·번호 조회에서 없는 것으로 봅니다. "
                 "반려동물은 질병을 하나 이상 고르거나 '질병 없음'을 직접 확인해야 저장됩니다. "
+                "고객 상세는 노쇼 횟수와 다가오는 예약(최대 3건)도 줍니다. "
+                "방문 기록이 있는 반려동물은 지우지 않고(409 PET_HAS_VISITS), 앞으로의 예약이 남은 아이의 "
+                "무지개다리와 고객 삭제는 막습니다(409 PET_HAS_UPCOMING_VISITS·CUSTOMER_HAS_UPCOMING_VISITS). "
                 "다른 매장의 고객·반려동물 ID 는 404 입니다."
             ),
         )
```

`backend/apps/customer/app/use_cases/delete_customer_interactor.py` (수정):
```diff
@@ -4,16 +4,24 @@ from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
 from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
+from customer.domain.errors import CustomerHasUpcomingVisitsError
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 class DeleteCustomerInteractor(DeleteCustomerUseCase):
     """고객 삭제는 익명화다. 개인정보만 지우고 행은 남긴다(③·④의 기록이 가리킬 틀)."""
 
-    def __init__(self, customers: CustomerRepository, search: CustomerSearchPort) -> None:
+    def __init__(
+        self, customers: CustomerRepository, search: CustomerSearchPort, ledger: VisitLedgerPort
+    ) -> None:
         self._customers = customers
         self._search = search
+        self._ledger = ledger
 
     async def delete_customer(self, command: DeleteCustomerCommand) -> None:
         await self._customers.lock_active(command.ctx, command.customer_id)
+        if await self._ledger.customer_has_upcoming(command.ctx, command.customer_id):
+            raise CustomerHasUpcomingVisitsError("앞으로의 예약이 남아 있습니다. 예약을 먼저 취소해 주세요.")
         await self._customers.anonymize(command.ctx, command.customer_id)
+        await self._ledger.clear_customer_memos(command.ctx, command.customer_id)   # 방문 메모의 개인정보(V11)
         await self._search.rebuild_search_entry(command.ctx, command.customer_id)   # 익명화한 고객이라 줄이 지워진다
```

`backend/apps/customer/app/use_cases/delete_pet_interactor.py` (수정):
```diff
@@ -4,19 +4,24 @@ from customer.app.dtos.delete_pet_dto import DeletePetCommand
 from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
 from customer.app.ports.output.pet_repository import PetRepository
-from customer.domain.errors import LastPetError
+from customer.domain.errors import LastPetError, PetHasVisitsError
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 class DeletePetInteractor(DeletePetUseCase):
     """잘못 등록한 반려동물을 지운다. 세상을 떠난 아이는 지우지 않고 무지개다리로 둔다."""
 
-    def __init__(self, pets: PetRepository, search: CustomerSearchPort) -> None:
+    def __init__(self, pets: PetRepository, search: CustomerSearchPort, ledger: VisitLedgerPort) -> None:
         self._pets = pets
         self._search = search
+        self._ledger = ledger
 
     async def delete_pet(self, command: DeletePetCommand) -> None:
         # 고객 행을 잠근 뒤 센다. 잠금이 없으면 마지막 두 마리를 동시에 지워 반려동물 없는 가족이 남는다.
         customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
+        # 고객 행을 쥔 뒤에 묻는다 — 예약 등록도 같은 고객 행을 먼저 잠그므로 그 사이 방문이 생기지 않는다.
+        if await self._ledger.pet_has_visits(command.ctx, command.pet_id):
+            raise PetHasVisitsError("방문 기록이 있는 반려동물은 지울 수 없습니다. 무지개다리를 이용해 주세요.")
         if await self._pets.count_for_customer(command.ctx, customer_id) <= 1:
             raise LastPetError("마지막 반려동물은 지울 수 없습니다. 고객 삭제를 이용해 주세요.")
         await self._pets.delete(command.ctx, command.pet_id)
```

`backend/apps/customer/app/use_cases/get_customer_interactor.py` (수정):
```diff
@@ -2,24 +2,42 @@ from __future__ import annotations
 
 from collections.abc import Callable
 from datetime import date
+from zoneinfo import ZoneInfo
 
-from customer.app.dtos.customer_view_dto import CustomerDetailView
+from customer.app.dtos.customer_view_dto import CustomerOverviewView, UpcomingVisitView
 from customer.app.dtos.get_customer_dto import GetCustomerQuery
 from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
 from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.app.services.detail_reader import read_customer_detail
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
+
+UPCOMING_LIMIT = 3
 
 
 class GetCustomerInteractor(GetCustomerUseCase):
     def __init__(
-        self, customers: CustomerRepository, pets: PetRepository, today: Callable[[], date]
+        self, customers: CustomerRepository, pets: PetRepository, ledger: VisitLedgerPort,
+        today: Callable[[], date],
     ) -> None:
         self._customers = customers
         self._pets = pets
+        self._ledger = ledger
         self._today = today
 
-    async def get_customer(self, query: GetCustomerQuery) -> CustomerDetailView:
-        return await read_customer_detail(
-            query.ctx, query.customer_id, self._customers, self._pets, self._today()
+    async def get_customer(self, query: GetCustomerQuery) -> CustomerOverviewView:
+        ctx = query.ctx
+        detail = await read_customer_detail(ctx, query.customer_id, self._customers, self._pets, self._today())
+        names = {pet.pet_id: pet.name for pet in detail.pets}
+        zone = ZoneInfo(ctx.timezone)
+        upcoming = await self._ledger.upcoming_for_customer(ctx, query.customer_id, UPCOMING_LIMIT)
+        return CustomerOverviewView(
+            customer=detail.customer,
+            pets=detail.pets,
+            no_show_count=await self._ledger.no_show_count(ctx, query.customer_id),
+            upcoming_visits=[
+                UpcomingVisitView(visit_id=u.visit_id, pet_id=u.pet_id, pet_name=names.get(u.pet_id),
+                                  starts_at=u.starts_at.astimezone(zone))
+                for u in upcoming
+            ],
         )
```

`backend/apps/customer/app/use_cases/mark_pet_passed_away_interactor.py` (수정):
```diff
@@ -10,6 +10,8 @@ from customer.app.ports.output.customer_repository import CustomerRepository
 from customer.app.ports.output.customer_search_port import CustomerSearchPort
 from customer.app.ports.output.pet_repository import PetRepository
 from customer.app.services.detail_reader import read_pet_detail
+from customer.domain.errors import PetHasUpcomingVisitsError
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
 class MarkPetPassedAwayInteractor(MarkPetPassedAwayUseCase):
@@ -17,15 +19,18 @@ class MarkPetPassedAwayInteractor(MarkPetPassedAwayUseCase):
 
     def __init__(
         self, customers: CustomerRepository, pets: PetRepository, search: CustomerSearchPort,
-        today: Callable[[], date],
+        ledger: VisitLedgerPort, today: Callable[[], date],
     ) -> None:
         self._customers = customers
         self._pets = pets
         self._search = search
+        self._ledger = ledger
         self._today = today
 
     async def mark_pet_passed_away(self, command: MarkPetPassedAwayCommand) -> PetDetailView:
         customer_id = await self._pets.lock_owner(command.ctx, command.pet_id)
+        if await self._ledger.pet_has_upcoming(command.ctx, command.pet_id):
+            raise PetHasUpcomingVisitsError("앞으로의 예약이 남아 있습니다. 예약을 먼저 취소해 주세요.")
         await self._pets.set_passed_away(command.ctx, command.pet_id, passed_away=True)
         await self._search.rebuild_search_entry(command.ctx, customer_id)
         return await read_pet_detail(
```

`backend/apps/visit/app/ports/output/visit_repository.py` (수정):
```diff
@@ -71,6 +71,21 @@ class VisitRepository(ABC):
     ) -> list[datetime]:
         """그 아이(pet_id 가 None 이면 보호자만의 방문)의 완료 방문 시작 시각, 최근 것부터 limit 개."""
 
+    @abstractmethod
+    async def pet_has_visits(self, ctx: ShopContext, pet_id: int, active_only: bool) -> bool: ...
+
+    @abstractmethod
+    async def customer_has_active(self, ctx: ShopContext, customer_id: int) -> bool: ...
+
+    @abstractmethod
+    async def list_active_from(
+        self, ctx: ShopContext, customer_id: int, since: datetime, limit: int
+    ) -> list[Visit]:
+        """since 이후에 시작하는 살아 있는 방문, 시작 순으로 limit 개."""
+
+    @abstractmethod
+    async def clear_memos(self, ctx: ShopContext, customer_id: int) -> None: ...
+
     @abstractmethod
     async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int: ...
```

`backend/apps/visit/app/use_cases/visit_ledger_interactor.py`:
```python
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from hub.app.dtos.shop_context import ShopContext
from hub.app.dtos.upcoming_visit import UpcomingVisit
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from visit.app.ports.output.visit_repository import VisitRepository
from visit.domain.services.visit_schedule import day_bounds, local_date


class VisitLedgerInteractor(VisitLedgerPort):
    """허브의 VisitLedgerPort 구현. 입력 포트가 곧 허브 포트다(HTTP 표면 없음)."""

    def __init__(self, visits: VisitRepository, now: Callable[[], datetime]) -> None:
        self._visits = visits
        self._now = now

    async def pet_has_visits(self, ctx: ShopContext, pet_id: int) -> bool:
        return await self._visits.pet_has_visits(ctx, pet_id, active_only=False)

    async def pet_has_upcoming(self, ctx: ShopContext, pet_id: int) -> bool:
        return await self._visits.pet_has_visits(ctx, pet_id, active_only=True)

    async def customer_has_upcoming(self, ctx: ShopContext, customer_id: int) -> bool:
        return await self._visits.customer_has_active(ctx, customer_id)

    async def no_show_count(self, ctx: ShopContext, customer_id: int) -> int:
        return await self._visits.count_no_show(ctx, customer_id)

    async def upcoming_for_customer(self, ctx: ShopContext, customer_id: int, limit: int) -> list[UpcomingVisit]:
        today_start, _ = day_bounds(local_date(self._now(), ctx.timezone), ctx.timezone)
        found = await self._visits.list_active_from(ctx, customer_id, today_start, limit)
        return [UpcomingVisit(visit_id=v.id, pet_id=v.pet_id, starts_at=v.starts_at) for v in found]

    async def clear_customer_memos(self, ctx: ShopContext, customer_id: int) -> None:
        await self._visits.clear_memos(ctx, customer_id)
```

`backend/apps/customer/adapter/inbound/api/error_map.py` (수정):
```diff
@@ -1,10 +1,13 @@
 """customer 도메인 오류 → HTTP 상태 코드. 유스케이스는 HTTP 를 모른다."""
 from customer.domain.errors import (
+    CustomerHasUpcomingVisitsError,
     CustomerInputError,
     CustomerNotFoundError,
     CustomerPhoneTakenError,
     LastPetError,
     PetHealthConflictError,
+    PetHasUpcomingVisitsError,
+    PetHasVisitsError,
     PetHealthRequiredError,
     PetNotFoundError,
     PetPassedAwayError,
@@ -15,6 +18,9 @@ CUSTOMER_ERROR_STATUS: dict[type[Exception], int] = {
     PetNotFoundError: 404,
     CustomerPhoneTakenError: 409,
     LastPetError: 409,
+    PetHasVisitsError: 409,
+    PetHasUpcomingVisitsError: 409,
+    CustomerHasUpcomingVisitsError: 409,
     CustomerInputError: 422,
     PetHealthRequiredError: 422,
     PetHealthConflictError: 422,
```

`backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py` (수정):
```diff
@@ -4,7 +4,12 @@ from datetime import date, datetime
 
 from pydantic import BaseModel
 
-from customer.app.dtos.customer_view_dto import CustomerDetailView, CustomerView, PetView
+from customer.app.dtos.customer_view_dto import (
+    CustomerDetailView,
+    CustomerOverviewView,
+    CustomerView,
+    PetView,
+)
 
 
 class ConditionSchema(BaseModel):
@@ -76,3 +81,25 @@ class CustomerDetailSchema(BaseModel):
     @classmethod
     def of(cls, view: CustomerDetailView) -> CustomerDetailSchema:
         return cls(customer=CustomerSchema.of(view.customer), pets=[PetSchema.of(p) for p in view.pets])
+
+
+class UpcomingVisitSchema(BaseModel):
+    visit_id: int
+    pet_id: int | None
+    pet_name: str | None
+    starts_at: datetime
+
+
+class CustomerOverviewSchema(CustomerDetailSchema):
+    """고객 상세(GET) — 방문 요약을 더한다. 등록·수정 응답은 방문 요약 없는 CustomerDetailSchema 다."""
+
+    no_show_count: int
+    upcoming_visits: list[UpcomingVisitSchema]
+
+    @classmethod
+    def of(cls, view: CustomerOverviewView) -> CustomerOverviewSchema:
+        return cls(
+            customer=CustomerSchema.of(view.customer), pets=[PetSchema.of(p) for p in view.pets],
+            no_show_count=view.no_show_count,
+            upcoming_visits=[UpcomingVisitSchema.model_validate(u, from_attributes=True) for u in view.upcoming_visits],
+        )
```

`backend/apps/customer/adapter/inbound/api/v1/get_customer_router.py` (수정):
```diff
@@ -2,7 +2,7 @@ from fastapi import APIRouter, Depends
 
 from core.shop_guard import get_shop_context
 from customer.adapter.inbound.api.path_params import CustomerId
-from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerDetailSchema
+from customer.adapter.inbound.api.schemas.get_customer_schema import CustomerOverviewSchema
 from customer.app.dtos.get_customer_dto import GetCustomerQuery
 from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
 from customer.dependencies.get_customer_provider import get_get_customer_use_case
@@ -11,12 +11,12 @@ from hub.app.dtos.shop_context import ShopContext
 get_customer_router = APIRouter(prefix="/v1/shops", tags=["customers"])
 
 
-@get_customer_router.get("/{shop_id}/customers/{customer_id}", response_model=CustomerDetailSchema)
+@get_customer_router.get("/{shop_id}/customers/{customer_id}", response_model=CustomerOverviewSchema)
 async def get_customer(
     customer_id: CustomerId,
     ctx: ShopContext = Depends(get_shop_context),
     use_case: GetCustomerUseCase = Depends(get_get_customer_use_case),
-) -> CustomerDetailSchema:
-    return CustomerDetailSchema.of(
+) -> CustomerOverviewSchema:
+    return CustomerOverviewSchema.of(
         await use_case.get_customer(GetCustomerQuery(ctx=ctx, customer_id=customer_id))
     )
```

`backend/apps/customer/adapter/inbound/api/v1/list_customers_router.py` (수정):
```diff
@@ -17,7 +17,7 @@ list_customers_router = APIRouter(prefix="/v1/shops", tags=["customers"])
 @list_customers_router.get("/{shop_id}/customers", response_model=CustomerListSchema)
 async def list_customers(
     q: Annotated[str | None, Query(max_length=50), AfterValidator(reject_control_chars)] = None,
-    sort: Literal["recent", "name"] = "recent",
+    sort: Literal["recent", "name", "last_visit"] = "recent",
     include_passed: bool = False,
     cursor: Annotated[str | None, Query(max_length=500)] = None,
     ctx: ShopContext = Depends(get_shop_context),
```

`backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py` (수정):
```diff
@@ -5,7 +5,7 @@ import binascii
 import json
 from datetime import datetime
 
-from sqlalchemy import delete, exists, func, select, tuple_, update
+from sqlalchemy import and_, delete, exists, func, or_, select, tuple_, update
 from sqlalchemy.dialects.postgresql import insert
 from sqlalchemy.ext.asyncio import AsyncSession
 from sqlalchemy.orm import aliased
@@ -30,7 +30,8 @@ def _encode_cursor(sort: SortKey, key: str, customer_id: int) -> str:
     return base64.urlsafe_b64encode(raw).decode().rstrip("=")
 
 
-def _decode_cursor(cursor: str, sort: SortKey) -> tuple[str | datetime, int]:
+def _decode_cursor(cursor: str, sort: SortKey) -> tuple[str | datetime | None, int]:
+    """최근 방문순의 빈 문자열 키는 '방문한 적 없음'(마지막 방문 시각 NULL)이다."""
     try:
         raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
         cursor_sort, key, customer_id = json.loads(raw)
@@ -42,7 +43,11 @@ def _decode_cursor(cursor: str, sort: SortKey) -> tuple[str | datetime, int]:
             or not (1 <= customer_id <= 2**63 - 1)
         ):
             raise ValueError
-        return (datetime.fromisoformat(key) if sort == "recent" else key), customer_id
+        if sort == "name":
+            return key, customer_id
+        if sort == "last_visit" and key == "":
+            return None, customer_id
+        return datetime.fromisoformat(key), customer_id
     except (ValueError, TypeError, binascii.Error, UnicodeDecodeError):
         raise CustomerInputError("목록 위치(cursor)가 올바르지 않습니다.") from None
 
@@ -109,16 +114,20 @@ class CustomerSearchPgAdapter(CustomerSearchPort):
         return conditions
 
     async def search(self, ctx: ShopContext, request: SearchRequest) -> SearchPage:
-        key_column = Entry.last_activity_at if request.sort == "recent" else Entry.sort_name
+        key_column = {
+            "recent": Entry.last_activity_at, "name": Entry.sort_name, "last_visit": Entry.last_visit_at,
+        }[request.sort]
         stmt = select(Entry.customer_id, key_column).where(
             *self._matching(ctx, request.words, request.include_passed)
         )
         if request.cursor is not None:
             key, after_id = _decode_cursor(request.cursor, request.sort)
-            position, after = tuple_(key_column, Entry.customer_id), tuple_(key, after_id)
-            stmt = stmt.where(position < after if request.sort == "recent" else position > after)
+            stmt = stmt.where(self._after(request.sort, key_column, key, after_id))
         if request.sort == "recent":
             stmt = stmt.order_by(key_column.desc(), Entry.customer_id.desc())
+        elif request.sort == "last_visit":
+            # 방문한 적 없는 가족은 맨 뒤에 모은다.
+            stmt = stmt.order_by(key_column.desc().nulls_last(), Entry.customer_id.desc())
         else:
             stmt = stmt.order_by(key_column, Entry.customer_id)
         rows = (await self._session.execute(stmt.limit(request.limit + 1))).all()
@@ -127,10 +136,29 @@ class CustomerSearchPgAdapter(CustomerSearchPort):
         next_cursor = None
         if len(rows) > request.limit:
             last_id, last_key = page[-1]
-            key_text = last_key.isoformat() if request.sort == "recent" else last_key
+            if request.sort == "name":
+                key_text = last_key
+            else:
+                key_text = last_key.isoformat() if last_key is not None else ""
             next_cursor = _encode_cursor(request.sort, key_text, last_id)
         return SearchPage(customer_ids=[customer_id for customer_id, _ in page], next_cursor=next_cursor)
 
+    @staticmethod
+    def _after(sort: SortKey, key_column, key, after_id: int):
+        """커서 다음 줄의 조건 — 정렬 순서 그대로."""
+        if sort == "name":
+            return tuple_(key_column, Entry.customer_id) > tuple_(key, after_id)
+        if sort == "recent":
+            return tuple_(key_column, Entry.customer_id) < tuple_(key, after_id)
+        # 최근 방문순: 시각 내림차순, 같은 시각이면 ID 내림차순, NULL 은 맨 뒤.
+        if key is None:
+            return and_(key_column.is_(None), Entry.customer_id < after_id)
+        return or_(
+            key_column < key,
+            and_(key_column == key, Entry.customer_id < after_id),
+            key_column.is_(None),
+        )
+
     async def count_pets(
         self, ctx: ShopContext, words: tuple[SearchWord, ...], include_passed: bool
     ) -> int:
```

`backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py` (수정):
```diff
@@ -164,6 +164,38 @@ class VisitPgRepository(VisitRepository):
             ).scalars()
         )
 
+    async def pet_has_visits(self, ctx: ShopContext, pet_id: int, active_only: bool) -> bool:
+        stmt = select(VisitOrm.id).where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.pet_id == pet_id)
+        if active_only:
+            stmt = stmt.where(VisitOrm.status.in_(ACTIVE_STATUSES))
+        return (await self._session.execute(select(stmt.exists()))).scalar_one()
+
+    async def customer_has_active(self, ctx: ShopContext, customer_id: int) -> bool:
+        stmt = select(VisitOrm.id).where(
+            VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id,
+            VisitOrm.status.in_(ACTIVE_STATUSES),
+        )
+        return (await self._session.execute(select(stmt.exists()))).scalar_one()
+
+    async def list_active_from(
+        self, ctx: ShopContext, customer_id: int, since: datetime, limit: int
+    ) -> list[Visit]:
+        return await self._read(
+            ctx,
+            select(VisitOrm)
+            .where(VisitOrm.customer_id == customer_id, VisitOrm.status.in_(ACTIVE_STATUSES),
+                   VisitOrm.starts_at >= since)
+            .order_by(VisitOrm.starts_at, VisitOrm.id)
+            .limit(limit),
+        )
+
+    async def clear_memos(self, ctx: ShopContext, customer_id: int) -> None:
+        await self._session.execute(
+            update(VisitOrm)
+            .where(VisitOrm.shop_id == ctx.shop_id, VisitOrm.customer_id == customer_id)
+            .values(memo=None)
+        )
+
     async def count_no_show(self, ctx: ShopContext, customer_id: int) -> int:
         return (
             await self._session.execute(
```

`backend/apps/customer/dependencies/delete_customer_provider.py` (수정):
```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
 from customer.app.ports.input.delete_customer_use_case import DeleteCustomerUseCase
 from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
@@ -7,9 +9,13 @@ from customer.dependencies.customer_wiring import (
     build_customer_repository,
     build_customer_search,
 )
+from customer.dependencies.hub_ports import get_visit_ledger
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
-def get_delete_customer_use_case(db: DbSession) -> DeleteCustomerUseCase:
+def get_delete_customer_use_case(
+    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
+) -> DeleteCustomerUseCase:
     return DeleteCustomerInteractor(
-        customers=build_customer_repository(db), search=build_customer_search(db),
+        customers=build_customer_repository(db), search=build_customer_search(db), ledger=ledger,
     )
```

`backend/apps/customer/dependencies/delete_pet_provider.py` (수정):
```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
 from customer.app.ports.input.delete_pet_use_case import DeletePetUseCase
 from customer.app.use_cases.delete_pet_interactor import DeletePetInteractor
@@ -7,9 +9,13 @@ from customer.dependencies.customer_wiring import (
     build_customer_search,
     build_pet_repository,
 )
+from customer.dependencies.hub_ports import get_visit_ledger
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
-def get_delete_pet_use_case(db: DbSession) -> DeletePetUseCase:
+def get_delete_pet_use_case(
+    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
+) -> DeletePetUseCase:
     return DeletePetInteractor(
-        pets=build_pet_repository(db), search=build_customer_search(db),
+        pets=build_pet_repository(db), search=build_customer_search(db), ledger=ledger,
     )
```

`backend/apps/customer/dependencies/get_customer_provider.py` (수정):
```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
 from customer.app.ports.input.get_customer_use_case import GetCustomerUseCase
 from customer.app.use_cases.get_customer_interactor import GetCustomerInteractor
@@ -7,10 +9,15 @@ from customer.dependencies.customer_wiring import (
     build_customer_repository,
     build_pet_repository,
 )
+from customer.dependencies.hub_ports import get_visit_ledger
 from customer.domain.services.pet_age import seoul_today
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
-def get_get_customer_use_case(db: DbSession) -> GetCustomerUseCase:
+def get_get_customer_use_case(
+    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
+) -> GetCustomerUseCase:
     return GetCustomerInteractor(
-        customers=build_customer_repository(db), pets=build_pet_repository(db), today=seoul_today,
+        customers=build_customer_repository(db), pets=build_pet_repository(db), ledger=ledger,
+        today=seoul_today,
     )
```

`backend/apps/customer/dependencies/hub_ports.py`:
```python
"""허브 포트 자리 — customer 가 쓰는, 다른 스포크가 구현한 포트.

진입점(main.py)이 app.dependency_overrides 로 구현을 꽂는다. 여기서 다른 스포크를 import 하지 않는다.
"""
from __future__ import annotations

from hub.app.ports.visit_ledger_port import VisitLedgerPort


def get_visit_ledger() -> VisitLedgerPort:
    raise RuntimeError("VisitLedgerPort 자리가 비어 있습니다. 진입점에서 조립해야 합니다.")
```

`backend/apps/customer/dependencies/mark_pet_passed_away_provider.py` (수정):
```diff
@@ -1,5 +1,7 @@
 from __future__ import annotations
 
+from fastapi import Depends
+
 from core.database import DbSession
 from customer.app.ports.input.mark_pet_passed_away_use_case import MarkPetPassedAwayUseCase
 from customer.app.use_cases.mark_pet_passed_away_interactor import MarkPetPassedAwayInteractor
@@ -8,11 +10,15 @@ from customer.dependencies.customer_wiring import (
     build_customer_search,
     build_pet_repository,
 )
+from customer.dependencies.hub_ports import get_visit_ledger
 from customer.domain.services.pet_age import seoul_today
+from hub.app.ports.visit_ledger_port import VisitLedgerPort
 
 
-def get_mark_pet_passed_away_use_case(db: DbSession) -> MarkPetPassedAwayUseCase:
+def get_mark_pet_passed_away_use_case(
+    db: DbSession, ledger: VisitLedgerPort = Depends(get_visit_ledger)
+) -> MarkPetPassedAwayUseCase:
     return MarkPetPassedAwayInteractor(
         customers=build_customer_repository(db), pets=build_pet_repository(db),
-        search=build_customer_search(db), today=seoul_today,
+        search=build_customer_search(db), ledger=ledger, today=seoul_today,
     )
```

`backend/apps/visit/dependencies/visit_ledger_provider.py`:
```python
from __future__ import annotations

from core.database import DbSession
from hub.app.ports.visit_ledger_port import VisitLedgerPort
from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.dependencies.visit_wiring import build_visit_repository
from visit.domain.services.visit_schedule import utc_now


def get_visit_ledger_use_case(db: DbSession) -> VisitLedgerPort:
    return VisitLedgerInteractor(visits=build_visit_repository(db), now=utc_now)
```

`backend/main.py` (수정):
```diff
@@ -39,6 +39,7 @@ from customer.adapter.inbound.api.v1.unmark_pet_passed_away_router import (
 from customer.adapter.inbound.api.v1.update_customer_router import update_customer_router
 from customer.adapter.inbound.api.v1.update_pet_router import update_pet_router
 from customer.dependencies.customer_directory_provider import get_customer_directory_use_case
+from customer.dependencies.hub_ports import get_visit_ledger
 from platform_admin.adapter.inbound.api.error_map import PLATFORM_ADMIN_ERROR_STATUS
 from platform_admin.adapter.inbound.api.v1.create_shop_router import create_shop_router
 from platform_admin.adapter.inbound.api.v1.platform_myself_router import platform_myself_router
@@ -78,6 +79,7 @@ from visit.adapter.inbound.api.v1.update_visit_router import update_visit_router
 from visit.adapter.inbound.api.v1.update_visit_settings_router import update_visit_settings_router
 from visit.adapter.inbound.api.v1.visit_myself_router import visit_myself_router
 from visit.dependencies.hub_ports import get_customer_directory
+from visit.dependencies.visit_ledger_provider import get_visit_ledger_use_case
 
 
 @asynccontextmanager
@@ -159,6 +161,7 @@ app.dependency_overrides[get_user_directory] = get_get_user_profiles_use_case
 app.dependency_overrides[get_membership_directory] = get_list_memberships_use_case
 app.dependency_overrides[get_active_user_guard] = get_guard_active_user_use_case
 app.dependency_overrides[get_customer_directory] = get_customer_directory_use_case
+app.dependency_overrides[get_visit_ledger] = get_visit_ledger_use_case
 
 
 @app.get("/health")
```

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps/visit/tests apps/customer/tests tests/integration/test_customer_locking.py tests/test_hub_port_binding.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **616 passed**, 통합 **240 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 4 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `DeleteCustomerInteractor`에서 `customer_has_upcoming` 검사를 지운다 → `test_앞으로의_예약이_남았으면_CUSTOMER_HAS_UPCOMING_VISITS_다`가 실패한다 — 되돌린다.
- `customer_search_pg_adapter._after`의 최근 방문순 분기에서 `key_column.is_(None),` 한 줄을 지운다 → `test_최근_방문순은_마지막_방문_시각_내림차순이고_방문_없는_가족은_맨_뒤다`가 실패한다(방문 없는 가족이 쪽 넘김에서 빠진다) — 되돌린다.

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/apps/customer/adapter/inbound/api/error_map.py backend/apps/customer/adapter/inbound/api/schemas/get_customer_schema.py backend/apps/customer/adapter/inbound/api/v1/get_customer_router.py backend/apps/customer/adapter/inbound/api/v1/list_customers_router.py backend/apps/customer/adapter/outbound/pg/customer_search_pg_adapter.py backend/apps/customer/app/dtos/customer_search_dto.py backend/apps/customer/app/dtos/customer_view_dto.py backend/apps/customer/app/ports/input/get_customer_use_case.py backend/apps/customer/app/use_cases/customer_myself_interactor.py backend/apps/customer/app/use_cases/delete_customer_interactor.py backend/apps/customer/app/use_cases/delete_pet_interactor.py backend/apps/customer/app/use_cases/get_customer_interactor.py backend/apps/customer/app/use_cases/mark_pet_passed_away_interactor.py backend/apps/customer/dependencies/delete_customer_provider.py backend/apps/customer/dependencies/delete_pet_provider.py backend/apps/customer/dependencies/get_customer_provider.py backend/apps/customer/dependencies/hub_ports.py backend/apps/customer/dependencies/mark_pet_passed_away_provider.py backend/apps/customer/domain/errors.py backend/apps/customer/tests/adapter/test_customer_search_pg_adapter.py backend/apps/customer/tests/adapter/test_get_customer_router.py backend/apps/customer/tests/adapter/test_list_customers_router.py backend/apps/customer/tests/app/use_cases/test_delete_customer_interactor.py backend/apps/customer/tests/app/use_cases/test_delete_pet_interactor.py backend/apps/customer/tests/app/use_cases/test_get_customer_interactor.py backend/apps/customer/tests/app/use_cases/test_mark_pet_passed_away_interactor.py backend/apps/customer/tests/helpers/fakes.py backend/apps/hub/app/dtos/upcoming_visit.py backend/apps/hub/app/ports/visit_ledger_port.py backend/apps/visit/adapter/outbound/pg/visit_pg_repository.py backend/apps/visit/app/ports/output/visit_repository.py backend/apps/visit/app/use_cases/visit_ledger_interactor.py backend/apps/visit/dependencies/visit_ledger_provider.py backend/apps/visit/tests/adapter/test_visit_pg_repository.py backend/apps/visit/tests/app/use_cases/test_visit_ledger_interactor.py backend/apps/visit/tests/helpers/fakes.py backend/main.py backend/tests/integration/test_customer_locking.py
git commit -m "feat(customer): 허브 포트 VisitLedgerPort — 방문 있는 반려동물 삭제·예약 남은 무지개다리·익명화 409, 방문 메모 비우기, 노쇼·다가오는 예약, 최근 방문순"
```

---

### Task 13: 실제 배선 통합 테스트 — 테넌트 격리부터, 예약 흐름, customer 규칙, 권한, 경로 순서

두 프로세스의 실제 앱 객체에 붙어 프로바이더·허브 포트 조립·DB 커밋·매장 접근 확인까지 통과한다(`tests/integration/`). 첫 테스트는 테넌트 격리다: B매장 경로 스무 개는 403 `NOT_A_MEMBER`, 내 매장 경로에 B매장의 방문·메뉴·보호자·반려동물 ID 를 넣으면 404(본문의 메뉴는 422), B매장의 값은 그대로다(V1·V2). 그다음 예약 → 하루 목록·시간 칸 → 시작·완료 → 최근 방문순 → 다음 예약 → 취소·되돌리기 → 노쇼 → 고객 상세, customer 규칙(V7·V11), 직원 권한(V8), `/visits/{visit_id}`보다 먼저 붙인 경로들. 허브 포트 너머(customer)의 도메인 오류도 같은 `{code, message}`로 나오는지 여기서 확인한다. 시각은 테스트를 돌리는 날 기준으로 만든다(`_at(days, hour)`).

**Files:**
- Test: `backend/tests/integration/test_visit_flow_wiring.py`

**Interfaces:**
- Consumes: Task 1~12 전부
- Produces: 없음(테스트만)

- [ ] **Step 1: 코드가 이미 있는지 확인하고 테스트를 쓴다**

`backend/tests/integration/test_visit_flow_wiring.py`:
```python
"""방문·예약을 실제 배선(프로바이더·허브 포트 조립·DB 커밋·매장 접근 확인)으로 확인한다. 첫 테스트는 테넌트 격리다."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

SEOUL = ZoneInfo("Asia/Seoul")
CUSTOMER = {"name": "김민지", "phone": "010-1234-5678", "marketing_consent": True}
PET = {
    "name": "콩이", "species": "dog", "breed": "말티즈", "sex": "female", "neutered": True,
    "birth_year": 2021, "weight_kg": 3.2, "no_known_conditions": True,
}


def _at(days: int, hour: int) -> str:
    """오늘(한국 시각)에서 days 날 뒤의 hour 시 — 시간대가 붙은 문자열."""
    day = datetime.now(SEOUL).date() + timedelta(days=days)
    return datetime(day.year, day.month, day.day, hour, tzinfo=SEOUL).isoformat()


async def _family(wired, shop_id, headers, phone="010-1234-5678", pets=("콩이", "두부")):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/customers",
        json={"customer": {**CUSTOMER, "phone": phone}, "pet": {**PET, "name": pets[0]}}, headers=headers,
    )
    assert response.status_code == 201, response.text
    customer_id = response.json()["customer"]["customer_id"]
    pet_ids = [response.json()["pets"][0]["pet_id"]]
    for name in pets[1:]:
        added = await wired.api.post(
            f"/v1/shops/{shop_id}/customers/{customer_id}/pets", json={**PET, "name": name}, headers=headers
        )
        assert added.status_code == 201, added.text
        pet_ids.append(added.json()["pet"]["pet_id"])
    return customer_id, pet_ids


async def _book(wired, shop_id, headers, customer_id, pet_ids, starts_at, **extra):
    response = await wired.api.post(
        f"/v1/shops/{shop_id}/visits",
        json={"customer_id": customer_id, "pet_ids": pet_ids, "starts_at": starts_at, **extra}, headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _act(wired, shop_id, headers, visit_ids, action, reason=None):
    body = {"visit_ids": visit_ids, "action": action}
    if reason:
        body["cancel_reason"] = reason
    return await wired.api.post(f"/v1/shops/{shop_id}/visits/transitions", json=body, headers=headers)


async def test_다른_매장의_방문과_메뉴에는_손댈_수_없다(wired):
    """V1 — B매장 경로는 403 NOT_A_MEMBER, 내 매장 경로에 B매장의 ID 를 넣으면 404(본문의 메뉴는 422)다."""
    operator = await make_operator(wired)
    a_shop, a_owner = await shop_with_owner(wired, operator, "A 매장", "A사장")
    b_shop, b_owner = await shop_with_owner(wired, operator, "B 매장", "B사장")
    a, b = bearer(a_owner["access_token"]), bearer(b_owner["access_token"])
    b_customer, b_pets = await _family(wired, b_shop, b)
    b_menu = (await wired.api.get(f"/v1/shops/{b_shop}/menus", headers=b)).json()["items"][0]["menu_id"]
    b_visit = (await _book(wired, b_shop, b, b_customer, b_pets[:1], _at(3, 14), memo="B 메모"))["visits"][0]
    b_id = b_visit["visit_id"]

    their_shop = [
        await wired.api.get(f"/v1/shops/{b_shop}/visits?date=2026-10-02", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/calendar?month=2026-10", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/slots?date=2026-10-02", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/defaults?pet_id={b_pets[0]}", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/myself", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits", json={"customer_id": b_customer, "walk_in": True},
                             headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_id}", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/visits/{b_id}", json={}, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits/transitions",
                             json={"visit_ids": [b_id], "action": "cancel", "cancel_reason": "shop_reason"}, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/visits/reschedule",
                             json={"visit_ids": [b_id], "starts_at": _at(4, 14)}, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_id}/next-draft", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/visit-settings", headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/visit-settings", json={}, headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/closed-dates?from=2026-10-01&to=2026-10-31", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/closed-dates", json={"date": "2026-10-09"}, headers=a),
        await wired.api.delete(f"/v1/shops/{b_shop}/closed-dates/2026-10-09", headers=a),
        await wired.api.get(f"/v1/shops/{b_shop}/menus", headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/menus", json={"name": "침입"}, headers=a),
        await wired.api.put(f"/v1/shops/{b_shop}/menus/{b_menu}", json={}, headers=a),
        await wired.api.post(f"/v1/shops/{b_shop}/menus/{b_menu}/archive", headers=a),
    ]
    assert [error_of(r) for r in their_shop] == [(403, "NOT_A_MEMBER")] * len(their_shop)

    # 경로의 매장은 내 매장이라 소속 확인은 통과한다. 대상은 컨텍스트의 매장 안에서만 찾는다.
    update_body = {"starts_at": _at(5, 11), "pet_id": None, "duration_minutes": 60, "menu_ids": [], "memo": "침입"}
    own_shop = [
        (await wired.api.get(f"/v1/shops/{a_shop}/visits/{b_id}", headers=a), (404, "VISIT_NOT_FOUND")),
        (await wired.api.put(f"/v1/shops/{a_shop}/visits/{b_id}", json=update_body, headers=a),
         (404, "VISIT_NOT_FOUND")),
        (await _act(wired, a_shop, a, [b_id], "cancel", "shop_reason"), (404, "VISIT_NOT_FOUND")),
        (await wired.api.post(f"/v1/shops/{a_shop}/visits/reschedule",
                              json={"visit_ids": [b_id], "starts_at": _at(4, 14)}, headers=a),
         (404, "VISIT_NOT_FOUND")),
        (await wired.api.get(f"/v1/shops/{a_shop}/visits/{b_id}/next-draft", headers=a), (404, "VISIT_NOT_FOUND")),
        (await wired.api.put(f"/v1/shops/{a_shop}/menus/{b_menu}",
                             json={"name": "침입", "default_duration_minutes": 10, "sort_order": 1}, headers=a),
         (404, "MENU_NOT_FOUND")),
        (await wired.api.post(f"/v1/shops/{a_shop}/menus/{b_menu}/archive", headers=a), (404, "MENU_NOT_FOUND")),
        # V2 — 남의 매장 보호자로 예약을 잡으면 customer 가 404 로 막는다(허브 포트 너머의 오류도 같은 형식).
        (await wired.api.post(f"/v1/shops/{a_shop}/visits",
                              json={"customer_id": b_customer, "pet_ids": b_pets[:1], "starts_at": _at(3, 15)},
                              headers=a), (404, "CUSTOMER_NOT_FOUND")),
    ]
    assert [error_of(r) for r, _ in own_shop] == [expected for _, expected in own_shop]
    a_customer, a_pets = await _family(wired, a_shop, a, phone="010-9999-0000", pets=("보리",))
    borrowed_menu = await wired.api.post(
        f"/v1/shops/{a_shop}/visits",
        json={"customer_id": a_customer, "pet_ids": a_pets, "starts_at": _at(3, 15), "menu_ids": [b_menu]}, headers=a,
    )
    assert error_of(borrowed_menu) == (422, "MENU_NOT_FOUND")
    borrowed_pet = await wired.api.post(
        f"/v1/shops/{a_shop}/visits",
        json={"customer_id": a_customer, "pet_ids": b_pets[:1], "starts_at": _at(3, 15)}, headers=a,
    )
    assert error_of(borrowed_pet) == (404, "PET_NOT_FOUND")
    defaults = await wired.api.get(f"/v1/shops/{a_shop}/visits/defaults?pet_id={b_pets[0]}", headers=a)
    assert defaults.json()["source_visit_id"] is None

    # B 매장의 방문과 메뉴는 그대로다.
    detail = (await wired.api.get(f"/v1/shops/{b_shop}/visits/{b_id}", headers=b)).json()["visit"]
    assert (detail["status"], detail["memo"], detail["starts_at"]) == ("reserved", "B 메모", b_visit["starts_at"])
    menus = (await wired.api.get(f"/v1/shops/{b_shop}/menus", headers=b)).json()["items"]
    assert (menus[0]["menu_id"], menus[0]["archived"]) == (b_menu, False)


async def test_예약부터_완료_다음_예약_취소_노쇼_되돌리기까지_돈다(wired):
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, (kong, dubu) = await _family(wired, shop_id, headers)
    menus = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=headers)).json()["items"]
    assert [m["name"] for m in menus] == ["목욕", "위생", "부분 미용", "전체 미용", "스포팅"]
    bath = menus[0]["menu_id"]

    # 두 마리를 오늘 13시에 — 방문 둘, 메뉴 기본 소요(목욕 60분).
    booked = await _book(wired, shop_id, headers, customer_id, [kong, dubu], _at(0, 13), menu_ids=[bath])
    visit_ids = [v["visit_id"] for v in booked["visits"]]
    assert [(v["pet"]["name"], v["duration_minutes"], v["status"]) for v in booked["visits"]] == [
        ("콩이", 60, "reserved"), ("두부", 60, "reserved")]
    assert booked["visits"][0]["customer"]["phone_masked"] == "010-12··-5678"
    again = await wired.api.post(
        f"/v1/shops/{shop_id}/visits",
        json={"customer_id": customer_id, "pet_ids": [kong], "starts_at": _at(0, 13)}, headers=headers,
    )
    assert error_of(again) == (409, "VISIT_DUPLICATE")   # V5

    today = datetime.now(SEOUL).date().isoformat()
    day = (await wired.api.get(f"/v1/shops/{shop_id}/visits?date={today}", headers=headers)).json()
    assert (day["counts"]["visit_count"], len({i["group_key"] for i in day["items"]})) == (2, 1)
    slots = (await wired.api.get(f"/v1/shops/{shop_id}/visits/slots?date={today}&duration=60", headers=headers)).json()
    assert [s["warnings"] for s in slots["slots"] if s["starts_at"].startswith(f"{today}T13")] == [["overlap"]]

    # 가족 묶음을 한 번에 시작 → 완료. 고객 목록의 최근 방문순 맨 앞에 온다.
    assert (await _act(wired, shop_id, headers, visit_ids, "start")).status_code == 200
    done = await _act(wired, shop_id, headers, visit_ids, "complete")
    assert [v["status"] for v in done.json()["visits"]] == ["completed", "completed"]
    other_id, _ = await _family(wired, shop_id, headers, phone="010-5555-0000", pets=("보리",))
    order = (await wired.api.get(f"/v1/shops/{shop_id}/customers?sort=last_visit", headers=headers)).json()
    assert [c["customer_id"] for c in order["items"]] == [customer_id, other_id]

    # 다음 예약 초안 — 처음 완료했으니 4주 뒤 같은 시각, 같은 메뉴, 가족 전체.
    draft = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_ids[0]}/next-draft", headers=headers)).json()
    assert (draft["pet_ids"], draft["interval_weeks"], draft["starts_at"]) == ([kong, dubu], 4, _at(28, 13))
    assert [m["menu_id"] for m in draft["menus"]] == [bath]
    defaults = (await wired.api.get(f"/v1/shops/{shop_id}/visits/defaults?pet_id={kong}", headers=headers)).json()
    assert (defaults["source_visit_id"], defaults["duration_minutes"]) == (visit_ids[0], 60)

    # 다음 예약을 잡고, 취소(사유)·되돌리기, 지난 예약은 노쇼.
    next_visits = await _book(wired, shop_id, headers, customer_id, draft["pet_ids"], draft["starts_at"],
                              menu_ids=[bath])
    next_ids = [v["visit_id"] for v in next_visits["visits"]]
    canceled = await _act(wired, shop_id, headers, next_ids, "cancel", "customer_request")
    assert {v["cancel_reason"] for v in canceled.json()["visits"]} == {"customer_request"}
    assert (await _act(wired, shop_id, headers, next_ids, "revert")).status_code == 200
    past = await _book(wired, shop_id, headers, customer_id, [kong], _at(-2, 10))
    past_id = past["visits"][0]["visit_id"]
    calendar_month = _at(-2, 10)[:7]
    calendar = (await wired.api.get(f"/v1/shops/{shop_id}/visits/calendar?month={calendar_month}",
                                    headers=headers)).json()
    assert calendar["unresolved_total"] == 1   # 지난 날인데 아직 예약됨
    assert (await _act(wired, shop_id, headers, [past_id], "no_show")).status_code == 200

    overview = (await wired.api.get(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).json()
    assert overview["no_show_count"] == 1
    assert [u["visit_id"] for u in overview["upcoming_visits"]] == next_ids


async def test_customer_의_규칙이_방문을_본다(wired):
    """V7·V11 — 방문 있는 아이는 지우지 않고, 예약 남은 아이·고객은 무지개다리·익명화를 막는다.
    익명화하면 방문 메모도 비우고, 하루 목록에는 이름 없이 틀만 남는다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    customer_id, (kong, dubu) = await _family(wired, shop_id, headers)
    booked = await _book(wired, shop_id, headers, customer_id, [kong], _at(2, 14), memo="010-1234-5678 로 연락")
    visit_id = booked["visits"][0]["visit_id"]

    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/pets/{kong}", headers=headers)) == (
        409, "PET_HAS_VISITS")
    assert error_of(await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)) == (
        409, "PET_HAS_UPCOMING_VISITS")
    assert error_of(await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)) == (
        409, "CUSTOMER_HAS_UPCOMING_VISITS")
    assert (await wired.api.delete(f"/v1/shops/{shop_id}/pets/{dubu}", headers=headers)).status_code == 204

    assert (await _act(wired, shop_id, headers, [visit_id], "cancel", "customer_request")).status_code == 200
    passed = await wired.api.post(f"/v1/shops/{shop_id}/pets/{kong}/passed-away", headers=headers)
    assert passed.status_code == 200
    # 무지개다리 아이의 취소를 되돌려 다시 앞으로의 예약을 만들 수 없다.
    assert error_of(await _act(wired, shop_id, headers, [visit_id], "revert")) == (422, "PET_PASSED_AWAY")
    assert error_of(await wired.api.post(
        f"/v1/shops/{shop_id}/visits",
        json={"customer_id": customer_id, "pet_ids": [kong], "starts_at": _at(5, 14)}, headers=headers,
    )) == (422, "PET_PASSED_AWAY")

    assert (await wired.api.delete(f"/v1/shops/{shop_id}/customers/{customer_id}", headers=headers)).status_code == 204
    detail = (await wired.api.get(f"/v1/shops/{shop_id}/visits/{visit_id}", headers=headers)).json()["visit"]
    assert (detail["memo"], detail["customer"]["name"], detail["customer"]["phone_masked"], detail["pet"]["name"]) == (
        None, None, None, None)


async def test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다(wired):
    """V8"""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    staff = await wired.login("직원")
    assert (await accept_invite(wired, staff, await staff_invite(wired, shop_id, owner))).status_code == 200
    s = bearer(staff["access_token"])
    customer_id, (kong, _) = await _family(wired, shop_id, s)

    booked = await _book(wired, shop_id, s, customer_id, [kong], _at(1, 11))
    assert (await _act(wired, shop_id, s, [booked["visits"][0]["visit_id"]], "cancel", "shop_reason")).status_code == 200
    walk_in = await wired.api.post(f"/v1/shops/{shop_id}/visits",
                                   json={"customer_id": customer_id, "pet_ids": [kong], "walk_in": True}, headers=s)
    assert walk_in.json()["visits"][0]["status"] == "in_progress"
    assert (await wired.api.get(f"/v1/shops/{shop_id}/visit-settings", headers=s)).status_code == 200

    settings = {"opens_at": "09:00", "closes_at": "18:00", "default_duration_minutes": 90, "closed_weekdays": [0]}
    menu_id = (await wired.api.get(f"/v1/shops/{shop_id}/menus", headers=s)).json()["items"][0]["menu_id"]
    denied = [
        await wired.api.put(f"/v1/shops/{shop_id}/visit-settings", json=settings, headers=s),
        await wired.api.post(f"/v1/shops/{shop_id}/closed-dates", json={"date": "2026-10-09"}, headers=s),
        await wired.api.delete(f"/v1/shops/{shop_id}/closed-dates/2026-10-09", headers=s),
        await wired.api.post(f"/v1/shops/{shop_id}/menus", json={"name": "발톱"}, headers=s),
        await wired.api.put(f"/v1/shops/{shop_id}/menus/{menu_id}",
                            json={"name": "목욕", "default_duration_minutes": 60, "sort_order": 1}, headers=s),
        await wired.api.post(f"/v1/shops/{shop_id}/menus/{menu_id}/archive", headers=s),
    ]
    assert [error_of(r) for r in denied] == [(403, "PERMISSION_DENIED")] * len(denied)
    o = bearer(owner["access_token"])
    changed = await wired.api.put(f"/v1/shops/{shop_id}/visit-settings", json=settings, headers=o)
    assert changed.json()["closed_weekdays"] == [0]


async def test_자기소개와_경로_순서(wired):
    """/visits/myself·calendar·slots·defaults 가 /visits/{visit_id} 에 먼저 걸리면 422 가 된다."""
    operator = await make_operator(wired)
    shop_id, owner = await shop_with_owner(wired, operator, "Hiss Haus", "사장님")
    headers = bearer(owner["access_token"])
    myself = await wired.api.get(f"/v1/shops/{shop_id}/visits/myself", headers=headers)
    assert (myself.status_code, myself.json()["id"]) == (200, 5)
    for path in ("visits/calendar?month=2026-10", "visits/slots?date=2026-10-02",
                 "visits/defaults?pet_id=1"):
        assert (await wired.api.get(f"/v1/shops/{shop_id}/{path}", headers=headers)).status_code == 200, path
```

- [ ] **Step 2: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest tests/integration/test_visit_flow_wiring.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 3: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **616 passed**, 통합 **245 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 4: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 2 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `main.py`에서 `visit_myself_router`를 `get_visit_router` 뒤로 옮긴다 → `test_자기소개와_경로_순서`가 실패한다(`/visits/myself`가 `{visit_id}`에 걸려 422) — 되돌린다.

- [ ] **Step 5: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/tests/integration/test_visit_flow_wiring.py
git commit -m "test(visit): 실제 배선 통합 테스트 — 테넌트 격리부터, 예약 흐름, customer 규칙, 권한, 경로 순서"
```

---

### Task 14: 두 세션 경합 — 익명화×예약 양방향, 동시 중복 예약, 동시 완료×노쇼

막힌 호출을 `create_task`로 들고 있다가 앞선 세션이 커밋한 뒤의 결과를 본다(결정 003 의 교훈). 방문 표에는 고객으로 가는 외래 키가 없어 외래 키의 암묵적 잠금도 없다 — 그래서 가족 잠금이 판별된다. 완료×노쇼는 잠금이 둘(고객 행, 방문 행)이라 하나만 빼면 다른 하나가 막는다 — 테스트 설명에 적은 대로 둘 다 빼야 실패한다.

**Files:**
- Test: `backend/tests/integration/test_visit_locking.py`

**Interfaces:**
- Consumes: Task 4·7·10·12 의 인터랙터와 저장소
- Produces: 없음(테스트만)

- [ ] **Step 1: 코드가 이미 있는지 확인하고 테스트를 쓴다**

`backend/tests/integration/test_visit_locking.py`:
```python
"""visit 의 경합 — 실제 두 세션으로 확인한다.

막힌 호출을 create_task 로 들고 있다가, 앞선 세션이 커밋한 뒤의 결과를 본다(결정 기록 003 의 교훈).
판별은 '기다렸다'와 '커밋 뒤의 결과' 두 단언이 함께 한다. 테스트마다 어느 코드를 빼면 실패하는지 적었다.
"""
import asyncio

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from customer.adapter.outbound.pg.condition_type_pg_repository import ConditionTypePgRepository
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.family_brief_pg_repository import FamilyBriefPgRepository
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.app.dtos.delete_customer_dto import DeleteCustomerCommand
from customer.app.use_cases.customer_directory_interactor import CustomerDirectoryInteractor
from customer.app.use_cases.delete_customer_interactor import DeleteCustomerInteractor
from customer.domain.errors import CustomerHasUpcomingVisitsError, CustomerNotFoundError
from customer.tests.helpers.profiles import customer_profile, pet_profile
from visit.adapter.outbound.pg.menu_pg_repository import MenuPgRepository
from visit.adapter.outbound.pg.schedule_pg_repository import SchedulePgRepository
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository
from visit.app.dtos.register_visit_dto import RegisterVisitCommand
from visit.app.dtos.transition_visits_dto import TransitionVisitsCommand
from visit.app.use_cases.register_visit_interactor import RegisterVisitInteractor
from visit.app.use_cases.transition_visits_interactor import TransitionVisitsInteractor
from visit.app.use_cases.visit_ledger_interactor import VisitLedgerInteractor
from visit.domain.errors import VisitDuplicateError, VisitStateConflictError
from visit.tests.helpers.builders import ctx, kst

pytestmark = pytest.mark.integration

SHOP = ctx(shop_id=1)
NOW = kst(9, 23, 15)
BLOCKED = 0.5   # 이만큼 기다려도 끝나지 않으면 잠금에서 기다리는 것으로 본다


def _directory(session):
    return CustomerDirectoryInteractor(
        CustomerPgRepository(session), PetPgRepository(session), FamilyBriefPgRepository(session),
        CustomerSearchPgAdapter(session),
    )


def _register(session, customer_id, pet_ids, starts_at=kst(10, 2, 14)):
    interactor = RegisterVisitInteractor(
        VisitPgRepository(session), MenuPgRepository(session), SchedulePgRepository(session),
        _directory(session), now=lambda: NOW,
    )
    return interactor.register_visit(RegisterVisitCommand(
        ctx=SHOP, customer_id=customer_id, pet_ids=tuple(pet_ids), starts_at=starts_at, duration_minutes=None,
        menu_ids=(), memo=None, walk_in=False,
    ))


def _transition(session, visit_ids, action, reason=None):
    interactor = TransitionVisitsInteractor(
        VisitPgRepository(session), MenuPgRepository(session), _directory(session), now=lambda: NOW
    )
    return interactor.transition_visits(TransitionVisitsCommand(
        ctx=SHOP, visit_ids=tuple(visit_ids), action=action, cancel_reason=reason,
    ))


def _anonymize(session, customer_id):
    ledger = VisitLedgerInteractor(VisitPgRepository(session), now=lambda: NOW)
    return DeleteCustomerInteractor(CustomerPgRepository(session), CustomerSearchPgAdapter(session), ledger) \
        .delete_customer(DeleteCustomerCommand(ctx=SHOP, customer_id=customer_id))


async def _still_waiting(task) -> bool:
    await asyncio.sleep(BLOCKED)
    return not task.done()


async def _family(factory, pet_names=("콩이",)):
    async with factory() as setup:
        customer = await CustomerPgRepository(setup).create(SHOP, customer_profile())
        pets = [await PetPgRepository(setup).add(SHOP, customer.id, pet_profile(name=n)) for n in pet_names]
        await CustomerSearchPgAdapter(setup).rebuild_search_entry(SHOP, customer.id)
        await SchedulePgRepository(setup).ensure(SHOP)
        await setup.commit()
    return customer.id, [p.id for p in pets]


async def _scalar(factory, sql, **params):
    async with factory() as check:
        return (await check.execute(text(sql), params)).scalar_one()


async def test_익명화가_고객을_쥔_동안_예약은_기다리고_뒤에는_404_다(db_engine):
    """V3 — 방문 표에는 고객으로 가는 외래 키가 없다. 가족 잠금(lock_family)이 없으면 예약이 기다리지 않고
    들어가, 익명화한 고객에게 앞으로의 예약이 생긴다. RegisterVisitInteractor 의 lock_family 호출을 빼면 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)

    async with factory() as deleting, factory() as booking:
        await _anonymize(deleting, customer_id)
        book = asyncio.create_task(_register(booking, customer_id, [kong]))
        assert await _still_waiting(book)

        await deleting.commit()
        with pytest.raises(CustomerNotFoundError):
            await book
        await booking.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM visits") == 0


async def test_예약이_고객을_쥔_동안_익명화는_기다리고_뒤에는_409_다(db_engine):
    """V3 반대 방향 — 예약의 가족 잠금이 커밋될 때까지 익명화가 기다렸다가 그 예약을 보고 막는다.
    CustomerDirectoryInteractor.lock_family 의 lock_active 를 get_active 로 바꾸면(잠그지 않으면) 익명화가
    기다리지 않고 아직 커밋 전인 예약을 못 본 채 지나가 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)

    async with factory() as booking, factory() as deleting:
        await _register(booking, customer_id, [kong])
        anonymize = asyncio.create_task(_anonymize(deleting, customer_id))
        assert await _still_waiting(anonymize)

        await booking.commit()
        with pytest.raises(CustomerHasUpcomingVisitsError):
            await anonymize
        await deleting.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM customers WHERE deleted_at IS NULL") == 1
    assert await _scalar(factory, "SELECT count(*) FROM visits") == 1


async def test_같은_예약을_두_기기가_동시에_잡으면_하나만_된다(db_engine):
    """V5 — 늦은 쪽은 고객 잠금에서 기다렸다가 유일 색인에 걸려 VISIT_DUPLICATE 를 받는다.
    uq_visits_pet_start_active 를 일반 색인으로 바꾸면 둘 다 들어가 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)

    async with factory() as first, factory() as second:
        await _register(first, customer_id, [kong])
        late = asyncio.create_task(_register(second, customer_id, [kong]))
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(VisitDuplicateError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT count(*) FROM visits") == 1


async def test_두_기기가_같은_방문에_완료와_노쇼를_누르면_늦은_쪽은_409_다(db_engine):
    """V4 — 늦은 쪽은 잠금에서 기다렸다가 다시 읽은 '완료'를 보고 거절한다.
    잠금이 둘(고객 행, 방문 행) 있어 하나만 빼면 다른 하나가 막는다 — lock_visits 의 lock_family 호출과
    VisitPgRepository.lock 의 with_for_update 를 **둘 다** 빼면 늦은 쪽이 옛 '예약됨'을 보고 노쇼로 덮어 실패한다."""
    factory = async_sessionmaker(db_engine, expire_on_commit=False, autoflush=False)
    customer_id, (kong,) = await _family(factory)
    async with factory() as setup:
        [visit] = (await _register(setup, customer_id, [kong], starts_at=kst(9, 23, 13))).visits
        await setup.commit()

    async with factory() as first, factory() as second:
        await _transition(first, [visit.visit_id], "complete")
        late = asyncio.create_task(_transition(second, [visit.visit_id], "no_show"))
        assert await _still_waiting(late)

        await first.commit()
        with pytest.raises(VisitStateConflictError):
            await late
        await second.rollback()

    assert await _scalar(factory, "SELECT status FROM visits") == "completed"
    assert await _scalar(factory, "SELECT last_visit_at FROM customer_search_entries") == kst(9, 23, 13)
```

- [ ] **Step 2: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest tests/integration/test_visit_locking.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 3: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **616 passed**, 통합 **249 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 4: 판별력을 확인한다(변이)**

하나씩 적용하고 Step 2 의 테스트를 돌린 뒤 **반드시 되돌린다**(`git checkout -- <파일>`).

- `RegisterVisitInteractor`의 `lock_family` 호출을 지운다 → 익명화×예약 두 테스트가 실패한다 — 되돌린다.
- `CustomerDirectoryInteractor.lock_family`의 `lock_active`를 `get_active`로 바꾼다 → 익명화×예약 두 테스트가 실패한다 — 되돌린다.
- 마이그레이션의 `uq_visits_pet_start_active`를 `unique=False`로 바꾼다 → `test_같은_예약을_두_기기가_동시에_잡으면_하나만_된다`가 실패한다 — 되돌린다.
- `lock_visits`의 `lock_family` 호출**과** `VisitPgRepository.lock`의 `.with_for_update()`를 함께 지운다 → `test_두_기기가_같은_방문에_완료와_노쇼를_누르면_늦은_쪽은_409_다`가 실패한다(하나만 지우면 통과 — 겹쳐 지킨다) — 되돌린다.

- [ ] **Step 5: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add backend/tests/integration/test_visit_locking.py
git commit -m "test(visit): 두 세션 경합 — 익명화×예약 양방향, 동시 중복 예약, 동시 완료×노쇼"
```

---

### Task 15: 최근 방문순 복구 스크립트, 흐름 확인 스크립트, 규칙 문서, 결정 기록 006, 최종 검증

`scripts/rebuild_last_visit.py`는 `last_visit_at`을 원본(visits)에서 다시 맞춘다 — 고객마다 고객 행을 먼저 잠그고 짧게 커밋한다(customer 재생성 스크립트와 같은 모양). `scripts/check_visit_flow.sh`는 게이트웨이 경유로 29단계를 확인한다. 문서: `CLAUDE.md` 잠금 순서, `_docs/architecture.md` 대응표, `_docs/harness.md`, visit 스포크의 `_docs/CLAUDE.md`(+ 심볼릭 링크), customer 스포크 문서의 허브 포트 줄, 결정 기록 006. 마지막으로 개발 DB 에 0006 을 올리고(표를 더할 뿐이다) 흐름 스크립트를 실제 게이트웨이로 돌린다.

**Files:**
- Create: `backend/scripts/check_visit_flow.sh`
- Modify: `backend/scripts/rebuild_customer_search.py`
- Create: `backend/scripts/rebuild_last_visit.py`
- Modify: `_docs/architecture.md`
- Create: `_docs/decisions/006-visit-reservation.md`
- Modify: `_docs/harness.md`
- Modify: `backend/apps/customer/_docs/CLAUDE.md`
- Create: `backend/apps/visit/_docs/CLAUDE.md`
- Modify: `CLAUDE.md`
- Test: `backend/tests/test_rebuild_last_visit.py`
- Create: `backend/apps/visit/CLAUDE.md` (심볼릭 링크)

**Interfaces:**
- Consumes: 전부
- Produces: `scripts.rebuild_last_visit.rebuild_all(session) -> int`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_rebuild_last_visit.py`:
```python
"""'최근 방문순' 복구 스크립트 — 어긋난 마지막 방문 시각을 원본(visits)대로 되돌린다."""
import pytest
from sqlalchemy import text

import scripts.rebuild_last_visit as rebuild_last_visit
from customer.adapter.outbound.pg.customer_pg_repository import CustomerPgRepository
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from customer.adapter.outbound.pg.pet_pg_repository import PetPgRepository
from customer.tests.helpers.profiles import ctx, customer_profile, pet_profile
from scripts.rebuild_last_visit import rebuild_all
from visit.tests.helpers.builders import kst
from visit.tests.helpers.rows import insert_visit

pytestmark = pytest.mark.integration


async def test_복구_스크립트의_엔진도_hide_parameters를_켠다(migrated_test_db, monkeypatch):
    captured = {}
    original_create = rebuild_last_visit.create_async_engine

    def _spy(url, **kwargs):
        captured.update(kwargs)
        return original_create(url, **kwargs)

    monkeypatch.setattr(rebuild_last_visit, "create_async_engine", _spy)
    monkeypatch.setattr(rebuild_last_visit, "DATABASE_URL", migrated_test_db)

    await rebuild_last_visit._run()

    assert captured.get("hide_parameters") is True


async def _customer(session, shop_id, phone):
    customer = await CustomerPgRepository(session).create(ctx(shop_id=shop_id), customer_profile(phone=phone))
    await PetPgRepository(session).add(ctx(shop_id=shop_id), customer.id, pet_profile())
    await CustomerSearchPgAdapter(session).rebuild_search_entry(ctx(shop_id=shop_id), customer.id)
    return customer.id


async def test_어긋난_마지막_방문_시각을_원본에서_다시_맞춘다(db_session):
    visited = await _customer(db_session, 1, "01012345678")
    never = await _customer(db_session, 2, "01099998888")
    await insert_visit(db_session, kst(9, 2, 14), "completed", customer_id=visited)
    await insert_visit(db_session, kst(9, 9, 14), "canceled", customer_id=visited)
    # 어긋난 상태: 방문한 고객은 비어 있고, 방문한 적 없는 고객에게 값이 있다.
    await db_session.execute(text("UPDATE customer_search_entries SET last_visit_at = now() WHERE customer_id = :id"),
                             {"id": never})
    await db_session.commit()

    assert await rebuild_all(db_session) == 2
    rows = dict((await db_session.execute(
        text("SELECT customer_id, last_visit_at FROM customer_search_entries"))).all())
    assert rows == {visited: kst(9, 2, 14), never: None}
```

- [ ] **Step 2: 실패를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest tests/test_rebuild_last_visit.py -q -p no:cacheprovider
```

Expected: `ModuleNotFoundError: No module named 'scripts.rebuild_last_visit'`로 실패한다.

- [ ] **Step 3: 구현한다**

`backend/scripts/check_visit_flow.sh`:
```bash
#!/usr/bin/env bash
# 개발 환경에서 예약 등록 → 하루 목록·시간 칸 → 시작·완료 → 다음 예약 → 취소·되돌리기 → 노쇼 → customer 규칙까지 확인한다.
# 사용: cd infra && docker compose up -d && bash ../backend/scripts/check_visit_flow.sh
# infra/ 에서 실행해야 한다 (운영자 지정을 docker compose 로 한다). 개발 DB 에 확인용 매장·유저·고객·방문이 남는다.
set -euo pipefail
BASE="${BASE:-http://127.0.0.1:8080}"
STAMP="$(date +%s)"
PHONE="010$(printf '%08d' $((STAMP % 100000000)))"   # 실행마다 다른 번호
TODAY="$(TZ=Asia/Seoul date +%Y-%m-%d)"
at() { TZ=Asia/Seoul python3 -c "import datetime as d,sys; t=d.date.today()+d.timedelta(days=int(sys.argv[1])); print(f'{t}T{int(sys.argv[2]):02d}:00:00+09:00')" "$1" "$2"; }

# field <경로> — JSON 응답에서 값을 꺼낸다. 예: field "['visits'][0]['visit_id']"
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(d$1)"; }
# calc <식> — JSON 응답(d)으로 식을 계산한다. 예: calc "len(d['visits'])"
calc() { python3 -c "import json,sys; d=json.load(sys.stdin); print($1)"; }
expect() { if [ "$2" = "$3" ]; then echo "통과  $1"; else echo "실패  $1 (기대 $3, 실제 $2)"; exit 1; fi; }
login() { curl -s -X POST "$BASE/v1/auth/social" -H 'Content-Type: application/json' -d "{\"provider\":\"dev\",\"token\":\"$1\"}"; }
call() { curl -s -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
status() { curl -s -o /dev/null -w '%{http_code}' -X "$1" "$BASE$2" -H "Authorization: Bearer $3" -H 'Content-Type: application/json' ${4:+-d "$4"}; }
pet() { echo "{\"name\":\"$1\",\"species\":\"dog\",\"breed\":\"말티즈\",\"sex\":\"female\",\"neutered\":true,\"birth_year\":2021,\"weight_kg\":3.2,\"no_known_conditions\":true}"; }
act() { call POST "$S/visits/transitions" "$1" "{\"visit_ids\":$2,\"action\":\"$3\"${4:+,\"cancel_reason\":\"$4\"}}"; }

op=$(login "vflow-op-$STAMP"); op_token=$(echo "$op" | field "['access_token']"); op_id=$(echo "$op" | field "['user_id']")
docker compose run --rm backend python scripts/grant_operator.py "$op_id" >/dev/null
shop=$(call POST /v1/platform/shops "$op_token" "{\"name\":\"방문흐름-$STAMP\"}")
shop_id=$(echo "$shop" | field "['shop_id']"); owner_code=$(echo "$shop" | field "['owner_invite_code']")
owner_token=$(login "vflow-owner-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$owner_token" "{\"code\":\"$owner_code\"}" >/dev/null
staff_code=$(call POST "/v1/shops/$shop_id/invites" "$owner_token" | field "['code']")
staff_token=$(login "vflow-staff-$STAMP" | field "['access_token']")
call POST /v1/invites/accept "$staff_token" "{\"code\":\"$staff_code\"}" >/dev/null
echo "통과  매장 $shop_id 에 사장과 직원이 있다"
S="/v1/shops/$shop_id"

registered=$(call POST "$S/customers" "$staff_token" \
  "{\"customer\":{\"name\":\"김민지\",\"phone\":\"$PHONE\",\"marketing_consent\":true},\"pet\":$(pet 콩이)}")
customer_id=$(echo "$registered" | field "['customer']['customer_id']")
kong=$(echo "$registered" | field "['pets'][0]['pet_id']")
dubu=$(call POST "$S/customers/$customer_id/pets" "$staff_token" "$(pet 두부)" | field "['pet']['pet_id']")
echo "통과  고객 $customer_id 과 반려동물 $kong, $dubu"

expect "기본 메뉴가 준비된다" "$(call GET "$S/menus" "$staff_token" | calc "[m['name'] for m in d['items']]")" \
  "['목욕', '위생', '부분 미용', '전체 미용', '스포팅']"
bath=$(call GET "$S/menus" "$staff_token" | field "['items'][0]['menu_id']")
booked=$(call POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$kong,$dubu],\"starts_at\":\"$(at 0 13)\",\"menu_ids\":[$bath]}")
visits=$(echo "$booked" | calc "[v['visit_id'] for v in d['visits']]")
expect "두 마리를 한 번에 예약하면 방문이 둘" "$(echo "$booked" | calc "len(d['visits'])")" "2"
expect "메뉴 기본 소요로 채운다" "$(echo "$booked" | field "['visits'][0]['duration_minutes']")" "60"
expect "같은 예약을 또 누르면 409" "$(status POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at 0 13)\"}")" "409"
expect "하루 목록의 마릿수" "$(call GET "$S/visits?date=$TODAY" "$staff_token" | field "['counts']['visit_count']")" "2"
expect "13시 칸은 겹침" "$(call GET "$S/visits/slots?date=$TODAY&duration=60&at=13:00" "$staff_token" | field "['slots'][0]['warnings']")" "['overlap']"

expect "가족 묶음을 한 번에 시작" "$(act "$staff_token" "$visits" start | calc "[v['status'] for v in d['visits']]")" "['in_progress', 'in_progress']"
expect "가족 묶음을 한 번에 완료" "$(act "$staff_token" "$visits" complete | calc "[v['status'] for v in d['visits']]")" "['completed', 'completed']"
first=$(echo "$booked" | field "['visits'][0]['visit_id']")
draft=$(call GET "$S/visits/$first/next-draft" "$staff_token")
expect "다음 예약은 4주 뒤 같은 시각" "$(echo "$draft" | field "['starts_at']")" "$(at 28 13)"
expect "지난번처럼 소요를 채운다" "$(call GET "$S/visits/defaults?pet_id=$kong" "$staff_token" | field "['duration_minutes']")" "60"
expect "최근 방문순 맨 앞" "$(call GET "$S/customers?sort=last_visit" "$staff_token" | field "['items'][0]['customer_id']")" "$customer_id"

later=$(call POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$kong],\"starts_at\":\"$(at 3 11)\"}" | field "['visits'][0]['visit_id']")
expect "취소에는 사유" "$(act "$staff_token" "[$later]" cancel | field "['code']")" "VALIDATION_ERROR"
expect "보호자 요청으로 취소" "$(act "$staff_token" "[$later]" cancel customer_request | field "['visits'][0]['cancel_reason']")" "customer_request"
expect "되돌리면 다시 예약됨" "$(act "$staff_token" "[$later]" revert | field "['visits'][0]['status']")" "reserved"
expect "예약 시각 전에는 노쇼 불가" "$(act "$staff_token" "[$later]" no_show | field "['code']")" "VISIT_NOT_YET"
past=$(call POST "$S/visits" "$staff_token" \
  "{\"customer_id\":$customer_id,\"pet_ids\":[$dubu],\"starts_at\":\"$(at -1 10)\"}" | field "['visits'][0]['visit_id']")
expect "지난 예약은 노쇼 처리" "$(act "$staff_token" "[$past]" no_show | field "['visits'][0]['status']")" "no_show"
expect "고객 상세에 노쇼 횟수" "$(call GET "$S/customers/$customer_id" "$staff_token" | field "['no_show_count']")" "1"

expect "방문 있는 아이는 지우지 못한다" "$(status DELETE "$S/pets/$dubu" "$staff_token")" "409"
expect "예약 남은 아이는 무지개다리 불가" "$(status POST "$S/pets/$kong/passed-away" "$staff_token")" "409"
expect "예약 남은 고객은 삭제 불가" "$(status DELETE "$S/customers/$customer_id" "$owner_token")" "409"

settings='{"opens_at":"10:00","closes_at":"19:00","default_duration_minutes":120,"closed_weekdays":[0]}'
expect "직원은 일정을 못 바꾼다" "$(status PUT "$S/visit-settings" "$staff_token" "$settings")" "403"
expect "사장은 일정을 바꾼다" "$(call PUT "$S/visit-settings" "$owner_token" "$settings" | field "['closed_weekdays']")" "[0]"
expect "직원은 메뉴를 못 만든다" "$(status POST "$S/menus" "$staff_token" '{"name":"발톱"}')" "403"
expect "사장은 메뉴를 만든다" "$(status POST "$S/menus" "$owner_token" '{"name":"발톱"}')" "201"
expect "달력 한 달" "$(call GET "$S/visits/calendar?month=${TODAY:0:7}" "$staff_token" | calc "len(d['days']) >= 28")" "True"

echo "전체 흐름 확인 완료"
```

`backend/scripts/rebuild_customer_search.py` (수정):
```diff
@@ -1,6 +1,7 @@
 """고객 검색 줄(customer_search_entries)을 원본(customers·pets)에서 모두 다시 만든다. 여러 번 실행해도 결과가 같다.
 
 검색 줄은 역정규화 표라 원본과 어긋나면 이 스크립트로 복구한다(설계 6.4). 익명화한 고객의 줄은 지운다.
+마지막 방문 시각(last_visit_at)은 원본이 visits 라 건드리지 않는다 — scripts/rebuild_last_visit.py 가 맞춘다.
 고객마다 고객 행을 먼저 FOR UPDATE 로 잠근 뒤 다시 만든다 — "가족을 바꾸는 쓰기는 고객 행을 먼저
 잠근다"는 전역 잠금 순서와 맞춘다. 살아 있는 고객만 잠그는 CustomerRepository.lock_active 는 익명화한
 고객에게 쓸 수 없어(찾지 못해 CustomerNotFoundError) 여기서는 익명화 여부와 상관없이 고객 행을 직접
```

`backend/scripts/rebuild_last_visit.py`:
```python
"""고객 목록 '최근 방문순'의 키(customer_search_entries.last_visit_at)를 원본(visits)에서 모두 다시 맞춘다.

이 칸은 역정규화다(설계 5.3). 원본이 visit 스포크의 방문이라 복구 스크립트도 visit 쪽 값으로 계산한다 —
customer 의 검색 줄 재생성(rebuild_customer_search.py)은 이 칸을 건드리지 않는다. 여러 번 실행해도 결과가 같다.
고객마다 고객 행을 먼저 FOR UPDATE 로 잠근다 — 방문을 쓰는 유스케이스와 같은 순서(고객 행 → 방문 행)다.
고객 하나가 끝날 때마다 커밋해 잠금을 짧게 쥔다. 익명화한 고객은 검색 줄이 없어 아무것도 하지 않는다.
사용: cd infra && docker compose run --rm backend python scripts/rebuild_last_visit.py
"""
from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import DATABASE_URL
from customer.adapter.outbound.orm.customer_orm import CustomerOrm
from customer.adapter.outbound.pg.customer_search_pg_adapter import CustomerSearchPgAdapter
from hub.app.dtos.shop_context import ShopContext
from visit.adapter.outbound.pg.visit_pg_repository import VisitPgRepository


async def rebuild_all(session: AsyncSession) -> int:
    """모든 고객의 마지막 방문 시각을 원본에서 다시 넣고, 다룬 고객 수를 돌려준다. 고객마다 짧게 커밋한다."""
    search, visits = CustomerSearchPgAdapter(session), VisitPgRepository(session)
    rows = (await session.execute(select(CustomerOrm.id, CustomerOrm.shop_id).order_by(CustomerOrm.id))).all()
    for customer_id, shop_id in rows:
        # 사람의 요청이 아니라 운영 작업이다. 멤버·권한 없이 그 고객의 매장으로만 범위를 정한다.
        ctx = ShopContext(shop_id=shop_id, member_id=0, role="system", permissions=frozenset())
        await session.execute(
            select(CustomerOrm.id)
            .where(CustomerOrm.id == customer_id, CustomerOrm.shop_id == shop_id)
            .with_for_update()
        )
        await search.set_last_visit(ctx, customer_id, await visits.latest_completed_start(ctx, customer_id))
        await session.commit()
    return len(rows)


async def _run() -> int:
    engine = create_async_engine(DATABASE_URL, hide_parameters=True)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            return await rebuild_all(session)
    finally:
        await engine.dispose()


def main() -> None:
    print(f"고객 {asyncio.run(_run())}명의 마지막 방문 시각을 다시 맞췄습니다.")


if __name__ == "__main__":
    main()
```

`_docs/architecture.md` (수정):
```diff
@@ -59,7 +59,7 @@
 | `core/singleton/` | Singleton | 비밀값 관리자처럼 프로세스에 하나만 있는 객체 |
 | `auth/adapter/outbound/strategy/` | Strategy | 제공자별 `SocialProviderPort` 구현 |
 | `auth/adapter/outbound/factory/` | Factory | 설정에 따라 제공자 구현을 만들어 담아 두고 이름으로 골라 준다 |
-| `visit/domain/state/` (예정) | State | 방문 상태 전이 |
+| `visit/domain/state/` | State | 방문 상태 전이(예약됨·미용 중·완료·취소·노쇼) |
 | `core/observer/`, `<app>/adapter/inbound/observer/` (예정) | Observer | 도메인 이벤트 발행과 구독 |
 | `visit/domain/chain/` (예정) | Chain of Responsibility | 예약 체크리스트 규칙 |
 | `search/adapter/outbound/decorator/` (예정) | Decorator | LLM 포트를 감싼 개인정보 마스킹 |
```

`_docs/decisions/006-visit-reservation.md`:
```markdown
# 006 — 예약·방문(③-A)에서 내린 결정

- 날짜: 2026-09-23(③-A1 백엔드)
- 대상 브랜치: `feat/visit-3a1-backend` (③-A1 백엔드)
- 근거: 설계 `docs/superpowers/specs/2026-09-23-visit-reservation-design.md`, 계획 `docs/superpowers/plans/2026-09-23-visit-3a1-backend.md`

## 무엇을 만들었나 (③-A1)

`backend/apps/visit` 스포크를 API 프로세스에 붙였다. 엔드포인트 20개(설계 8절 표에서 ③-A3 몫인 `POST /visit-drafts`를 뺀 전부 — 하루 목록·월 달력·시간 칸·지난번처럼·예약 등록·상세·수정·가족 옮기기·상태 전이·다음 예약 초안·자기소개, 일정 설정 조회·수정, 임시 휴무 조회·추가·삭제, 메뉴표 조회·추가·수정·보관), 마이그레이션 `0006`(표 6개와 검색 줄의 `last_visit_at` 칸), 허브 포트 둘(`CustomerDirectoryPort`는 customer 가, `VisitLedgerPort`는 visit 이 구현), `ShopContext.timezone`, customer 쪽 변경(409 셋, 익명화 때 방문 메모 비우기, 고객 상세의 노쇼 횟수·다가오는 예약, 최근 방문순), 복구 스크립트 `rebuild_last_visit.py`, 흐름 확인 스크립트 `check_visit_flow.sh`. 상태 전이는 `visit/domain/state/`(State 패턴)다.

## 방문을 쓰는 경로는 고객 행부터 잠근다

방문 표에는 고객·반려동물로 가는 외래 키가 없다(스포크를 넘는 ID). 그래서 외래 키의 암묵적 잠금도 없다 — 익명화와 예약 등록이 서로를 전혀 기다리지 않는다. 잠금이 없으면 익명화한 고객에게 앞으로의 예약이 생기거나(익명화가 먼저 커밋), 예약을 보지 못한 익명화가 지나간다(예약이 커밋 전).

그래서 방문을 쓰는 모든 유스케이스(등록·수정·옮기기·상태 전이)는 맨 앞에서 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행을 `FOR UPDATE` 잠그고, 그다음 방문 행을 ID 오름차순으로 잠근 뒤 다시 읽는다(`visit/app/services/visit_locking.py`). customer 쪽 익명화·무지개다리·반려동물 삭제는 원래 고객 행을 먼저 잠그고(②의 규칙) 그 안에서 `VisitLedgerPort`로 방문을 묻는다 — 같은 순서다. `CLAUDE.md`의 잠금 순서에 "고객 행 → 방문 행"을 더했다.

경합 테스트(`tests/integration/test_visit_locking.py`)의 판별력은 변이로 확인했다. 등록의 `lock_family` 호출을 빼거나 `lock_family`가 잠그지 않게(`get_active`) 바꾸면 익명화×예약 두 테스트가 실패한다. 유일 색인을 일반 색인으로 바꾸면 동시 중복 예약 테스트가 실패한다. 완료×노쇼 테스트는 잠금이 둘(고객 행, 방문 행)이라 하나만 빼면 다른 하나가 막아 통과하고, 둘 다 빼야 실패한다 — 방문 행 잠금은 고객 잠금이 있는 한 겹쳐 지키는 것이다.

## 계획에서 새로 정한 것

설계와 모순되는 것은 없다. 설계의 빈틈을 가장 작게 메운 것과 코드를 쓰며 찾은 것이다.

1. **`ShopContext.timezone`의 기본값은 `"Asia/Seoul"`이다**(`shops.timezone`의 기본값과 같다). 매장 접근 확인은 언제나 DB 값을 채우고, 기본값은 이미 있는 테스트의 컨텍스트 생성 20여 곳을 건드리지 않으려는 것이다.
2. **시각은 시간대를 붙여 받고 매장 시간대로 돌려준다.** 요청의 `starts_at`은 `AwareDatetime`(시간대 없는 시각은 422), 응답의 모든 시각은 매장 시간대(`+09:00`)다.
3. **경고 판단은 서버 한 곳(`visit_schedule.warnings_for`)에만 있다.** 등록·수정·옮기기 응답과 시간 칸 조회가 같은 함수를 쓴다. 같은 가족 묶음(같은 보호자 + 같은 시작 시각)끼리는 겹침이 아니고, 시간 칸 조회는 묶음 없이 묻는 것이라 누구의 방문과도 겹친다. 옮기기 화면을 위해 시간 칸 조회에 `exclude`(옮길 방문)를 더했다.
4. **수정에서 가족 확인에 넘기는 아이는 새로 고른 아이뿐이다.** 그대로인 아이를 넘기면 완료한 방문의 아이가 나중에 무지개다리를 건넌 경우 메모조차 못 고친다(`PET_PASSED_AWAY`). 지금 붙어 있는 메뉴는 보관됐어도 그대로 둘 수 있다.
5. **되돌리기는 아이도 확인한다.** 취소·노쇼·완료를 되돌리면 다시 시간을 차지하는 예약이 되므로, 무지개다리 아이의 방문이면 `PET_PASSED_AWAY`(422)로 막는다(V7). 다른 전이는 보호자만 잠근다.
6. **'최근 방문순'의 키는 마지막 완료 방문의 시작 시각이다**(완료 시각이 아니라 예약 날짜). 완료가 생기거나 풀리는 전이 뒤에 원본에서 다시 계산해 같은 트랜잭션에서 넘긴다. 방문한 적 없는 가족은 맨 뒤(NULLS LAST)이고, 커서의 빈 문자열 키가 "방문 없음"이다.
7. **가족 옮기기는 묶음에서 가장 긴 소요로** 자정 넘김과 경고를 본다.
8. **하루 목록은 취소·노쇼까지 모두 보인다.** 마릿수(`visit_count`)는 예약됨·미용 중·완료만 센다. 달력 위쪽의 "정리 안 된 예약 N건"(`unresolved_total`)은 달과 상관없이 매장 전체이고 가장 이른 날(`oldest_unresolved_date`)을 함께 준다.
9. **"앞으로의 예약"은 예약됨·미용 중인 방문이다** — 날짜가 지났어도 정리하지 않았으면 든다(익명화·무지개다리를 막는다). 고객 상세의 "다가오는 예약"은 그중 오늘(매장 시간대) 이후에 시작하는 것만, 최대 3건이다.
10. **반려동물 삭제는 `PET_HAS_VISITS`를 `LAST_PET`보다 먼저 본다.** 취소된 방문만 있어도 지우지 않는다.
11. **고객 상세(GET)만 방문 요약을 더한다**(`CustomerOverviewSchema` — `no_show_count`, `upcoming_visits`). 등록·수정 응답은 그대로다.
12. **일정 설정 수정은 설정 행 UPDATE 를 맨 먼저 한다.** 두 사장이 동시에 바꾸면 늦은 쪽이 그 행에서 기다렸다가 앞선 쪽이 커밋한 쉬는 요일을 지우고 넣는다 — 따로 잠그는 SELECT 가 필요 없다.
13. **설정·쉬는 요일·임시 휴무·메뉴는 설정 행을 외래 키로 가리킨다**(스포크 안의 관계). 그래서 휴무 추가와 메뉴 추가는 먼저 설정을 준비(`ensure`)한다. 메뉴 이름은 보관하지 않은 메뉴끼리만 겹치지 않는다 — 보관한 이름은 다시 쓸 수 있다.
14. **'지난번처럼'은 반려동물 ID 만으로 이 매장의 방문을 본다.** 다른 매장의 아이 ID 를 넣어도 빈 기본값이 될 뿐 아무것도 새지 않아 가족 확인(허브 포트)을 부르지 않는다.
15. **다음 예약 초안은 완료한 방문에서만**(아니면 409), 같은 묶음에서 완료한 아이들 전체로, 주기는 그 아이의 완료 방문 시작 시각 두 개로 계산한다.
16. **칸 형식.** ID 는 `bigint`, 상태·취소 사유는 `varchar(20)`, 메모 `varchar(500)`, 메뉴 이름 `varchar(30)`, 휴무 메모 `varchar(30)`. 임시 휴무 표의 칸 이름은 설계대로 `date`이고 ORM 속성은 `day`다(주석의 `date` 형과 부딪혀서). 요청 본문의 목록(반려동물·메뉴·방문 ID)은 10개까지, 같은 ID 두 번은 422 다.
17. **자기소개의 번호는 5번**(auth 1, tenancy 2, platform_admin 3, customer 4 다음).

## 검증

- 단위 테스트 기준 411 → 이 계획 뒤 616, 통합 테스트 기준 197 → 이 계획 뒤 251, 구조 계약 6종 유지(새 스포크를 계약 여섯에 모두 더했다).
- 흐름 확인 스크립트 29단계는 작업 트리의 인증·API 앱을 한 포트에 묶은 대역 서버(테스트 DB, Redis db 14)에서 통과했다. 실제 게이트웨이 경유 실행은 구현 브랜치에서 한다.
- 라우트 표에 visit 경로 20개가 API 프로세스로 나온다.

## 남는 것 — 알고 미룬다

- **낡은 `ShopContext`로 끝나는 쓰기**(005 의 "남는 것" 그대로). 방문 쓰기도 매장 행을 잠그지 않는다.
- **영업시간이 모든 요일에 하나다.** 요일별 시간은 필요해지면 `visit_weekly_closures`를 요일별 시간 표로 넓힌다(설계 13절).
- **복구 스크립트는 고객마다 커밋한다.** 중간에 멈추면 일부만 맞춰진 채로 남는다 — 다시 돌리면 같은 결과다.
- **처음 여는 GET 이 쓰기를 한다.** 설정·기본 메뉴는 매장을 처음 쓸 때 만든다(조회에서도). 읽기 전용 복제 DB 로 조회를 돌리게 되면 이 준비를 따로 떼어야 한다.

## ③-A2(앱)로 넘기는 것

- 응답의 시각은 매장 시간대가 붙어 있다 — 기기 시간대로 바꾸지 말고 그대로 보인다.
- 저장 버튼 두 번 → `VISIT_DUPLICATE`(409)는 "이미 저장됐어요"로 처리하고 그날 목록을 다시 읽는다.
- 상태 전이 뒤에는 그날 목록과 그 달 요약을 다시 읽는다(낙관적 갱신을 하지 않는다 — 409 가 나면 화면이 서버와 어긋난다).
- 가족 카드의 버튼은 묶음 전체의 `visit_ids`로 한 번에 부른다. 묶음은 하루 목록의 `group_key`다.
- 옮기기 화면의 시간 칸은 `exclude`에 옮길 방문을 넣어 부른다.
- 새 오류 코드 12개(설계 8절) — 앱의 오류 문구 표에 더한다.
```

`_docs/harness.md` (수정):
```diff
@@ -13,6 +13,8 @@
 | 회원 탈퇴 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_account_flow.sh` — 개발 DB에 "탈퇴한 사용자" 행이 남는다 |
 | 고객·반려동물 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_customer_flow.sh` — 개발 DB에 확인용 매장·유저와 익명화한 고객이 남는다 |
 | 고객 검색 줄 재생성 | `docker compose run --rm backend python scripts/rebuild_customer_search.py` (검색 줄이 원본과 어긋났을 때) |
+| 예약·방문 흐름 (게이트웨이 경유) | `bash ../backend/scripts/check_visit_flow.sh` — 개발 DB에 확인용 매장·유저·고객·방문이 남는다 |
+| 최근 방문순 키 복구 | `docker compose run --rm backend python scripts/rebuild_last_visit.py` (고객 목록 '최근 방문순'이 방문 기록과 어긋났을 때) |
 | 플랫폼 운영자 지정 | `docker compose run --rm backend python scripts/grant_operator.py <user_id>` |
 | 앱 정적 분석 | `flutter analyze` (`app/`에서, 경고 0) |
 | 앱 테스트 (위젯·골든·`ApiClient` 포함) | `flutter test` (`app/`에서) |
```

`backend/apps/customer/_docs/CLAUDE.md` (수정):
```diff
@@ -13,4 +13,5 @@
 - 목록과 반려동물 상세의 번호는 가린다(`010-12··-5678`). 전체 번호는 고객 상세에서만 준다. 전화번호·이름을 로그에 남기지 않는다. 검색어와 번호 조회는 쿼리 문자열로 오므로 API 프로세스가 접근 로그의 쿼리를 가린다(`core/access_log.py`).
 - 고객 삭제는 익명화다: 고객의 이름·전화·보조 연락처·메모, 반려동물의 이름·메모, 질병 행을 지우고 `deleted_at`을 찍는다. 행과 틀(종류·품종·성별 등)은 남긴다. 익명화한 고객은 모든 조회·검색·번호 조회에서 없는 것으로 본다.
 - 반려동물은 질병을 하나 이상 고르거나 "질병 없음"을 직접 확인해야 저장된다(두 표에 걸친 규칙이라 도메인이 확인한다). 질병 종류는 마이그레이션 시드다 — 코드에서 만들거나 고치지 않는다.
-- 새 허브 포트는 없다. 다른 스포크와 협력할 일이 생기면 허브에 포트를 둔다.
+- 허브 포트 둘. `CustomerDirectoryPort`는 이 스포크가 구현한다(`app/use_cases/customer_directory_interactor.py` — visit 의 가족 잠금·요약·마지막 방문 시각). `VisitLedgerPort`는 visit 이 구현하고 이 스포크가 `dependencies/hub_ports.py`의 자리로 받는다 — 방문 기록이 있는 반려동물은 지우지 않고(409 `PET_HAS_VISITS`), 앞으로의 예약이 남은 아이의 무지개다리와 고객 익명화는 막고(409), 익명화 때 방문 메모도 비운다. 모두 고객 행을 잠근 **뒤에** 묻는다.
+- 검색 줄의 `last_visit_at`(최근 방문순)은 원본이 visits 다 — 검색 줄을 다시 만들 때 건드리지 않고, visit 이 `set_last_visit`로 알려 준다.
```

`backend/apps/visit/_docs/CLAUDE.md`:
```markdown
# visit — 방문(예약부터 완료까지), 매장 일정, 메뉴표

소유 데이터: `visits`, `visit_menus`, `visit_shop_settings`, `visit_weekly_closures`, `visit_closed_dates`, `service_menus`.

- 방문 하나는 반려동물 한 마리의 방문이다. `pet_id`가 NULL 이면 보호자만의 방문이다. 두 마리를 한 번에 잡으면 방문이 둘이고, 같은 보호자 + 같은 시작 시각이 가족 묶음이다(저장하지 않고 계산한다).
- `visits`의 `shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID 라 외래 키가 없다. 이름·품종 같은 보호자·반려동물 정보는 복사하지 않고 허브 포트 `CustomerDirectoryPort.briefs`로 읽는다(`app/services/visit_reader.py`).
- 상태는 `domain/state/`(State 패턴)가 정한다: 예약됨 → (미용 중) → 완료 / 취소(사유 필수) / 노쇼, 되돌리기는 예약됨으로. 상태가 원본이고 시각·사유 칸은 그 상태일 때만 있다(CHECK).
- **방문을 쓰는 유스케이스는 맨 앞에서 고객 행을 잠근다** — `CustomerDirectoryPort.lock_family`(customer 구현) → 방문 행(ID 오름차순 `FOR UPDATE`) → 다시 읽기. `app/services/visit_locking.py`가 이 순서를 한 곳에 둔다. 외래 키가 없어 이 잠금이 없으면 익명화·무지개다리·반려동물 삭제와 겹친다.
- customer 는 반대 방향 허브 포트 `VisitLedgerPort`(이 스포크 구현, `app/use_cases/visit_ledger_interactor.py`)로 방문을 묻는다. '앞으로의 예약'은 예약됨·미용 중인 방문이다(날짜가 지났어도).
- 같은 아이(보호자만이면 같은 보호자)의 같은 시각에 살아 있는 예약은 하나다(부분 유일 색인 — 409 `VISIT_DUPLICATE`, 세이브포인트라 트랜잭션은 계속 쓴다).
- 겹침·휴무·영업시간 밖은 **막지 않는 경고**다. 판단은 `domain/services/visit_schedule.warnings_for` 한 곳에만 있다.
- "오늘"과 하루의 경계는 매장 시간대(`ShopContext.timezone`)로 센다. 요청 시각은 시간대가 붙어 와야 하고, 응답 시각은 매장 시간대로 나간다.
- 완료가 생기거나 풀리면 그 보호자의 마지막 완료 방문 시작 시각을 `CustomerDirectoryPort.set_last_visit`로 같은 트랜잭션에서 넘긴다(고객 목록 '최근 방문순'). 어긋나면 `scripts/rebuild_last_visit.py`로 복구한다.
- 매장 일정 설정 행은 매장을 처음 쓸 때(조회에서도) 기본값으로 만들고 같은 트랜잭션에서 기본 메뉴를 넣는다. 메뉴는 지우지 않고 보관한다.
```

`CLAUDE.md` (수정):
```diff
@@ -24,7 +24,7 @@
 - 스포크의 `dependencies/`도 다른 스포크를 import하지 않는다. 다른 스포크가 구현한 허브 포트는 `dependencies/hub_ports.py`의 자리로 받고, `main.py`가 구현을 꽂는다.
 - 매장 범위의 경로는 `core/shop_guard.py`의 `get_shop_context` 또는 `require_permission`으로 `ShopContext`를 받는다. 매장 범위의 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.
 - 인증 프로세스 전용 비밀값(JWT 개인키, `IDENTITY_TOKEN_ENC_KEY`, `KAKAO_ADMIN_KEY`)은 `core/auth_config.py`에만 있고 인증 프로세스(`auth_main.py`)만 읽는다. 이 모듈은 함수 안에서만 import한다. API 프로세스 경로에서 import하지 않는다.
-- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
+- 잠금 순서는 유저 행 → 매장 행(ID 오름차순) → 멤버 행 → 초대 행이다. 고객·방문 쪽은 고객 행 → 방문 행(ID 오름차순)이다 — 방문을 쓰는 유스케이스는 허브 포트 `CustomerDirectoryPort.lock_family`로 고객 행부터 잠근다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
 - `load_dotenv`·`os.getenv`·`os.environ`은 `core/singleton/secret_manager.py`에서만 쓴다.
 - 비밀값을 로그·커밋·문서에 남기지 않는다. `.env*` 파일 내용을 그대로 출력하지 않는다.
 - 커밋과 푸시는 사용자가 요청할 때만 한다. CI는 없다. 검증은 로컬에서 한다.
```

심볼릭 링크 — Run (저장소 루트에서):
```bash
ln -s _docs/CLAUDE.md backend/apps/visit/CLAUDE.md
```

> 흐름 스크립트에 실행 권한을 준다(다른 `check_*_flow.sh`와 같다): `chmod +x backend/scripts/check_visit_flow.sh`.

- [ ] **Step 4: 통과를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest tests/test_rebuild_last_visit.py -q -p no:cacheprovider
```

Expected: 모두 통과.

- [ ] **Step 5: 전체를 확인한다**

Run (`infra/`에서):
```bash
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m "not integration and not network"
docker compose run --rm backend pytest apps tests -q -p no:cacheprovider -m integration
docker compose run --rm --no-deps backend lint-imports --config .importlinter
```

Expected: 단위 **616 passed**, 통합 **251 passed**, `Contracts: 6 kept, 0 broken.`

- [ ] **Step 6: 개발 DB 에 0006 을 올리고 흐름 스크립트를 게이트웨이로 돌린다**

Run (`infra/`에서):
```bash
docker compose restart backend       # 시작 명령이 alembic upgrade head 를 돈다 — 표를 더할 뿐이다
docker compose run --rm backend alembic current      # 0006 (head)
bash ../backend/scripts/check_visit_flow.sh
bash ../backend/scripts/check_customer_flow.sh      # customer 흐름이 그대로인지(방문이 없어 409 규칙에 걸리지 않는다)
docker compose run --rm --no-deps auth python scripts/print_routes.py | grep -cE 'visit|menus|closed-dates'
```

Expected: `0006 (head)`, 흐름 스크립트 둘 다 마지막 줄 `전체 흐름 확인 완료`, 라우트 표에 visit 경로 **20**줄이 모두 `backend`(API 프로세스).

- [ ] **Step 7: 커밋한다**

사용자가 작업 단위 커밋을 허용했을 때만 한다.

```bash
git add CLAUDE.md _docs/architecture.md _docs/decisions/006-visit-reservation.md _docs/harness.md backend/apps/customer/_docs/CLAUDE.md backend/apps/visit/CLAUDE.md backend/apps/visit/_docs/CLAUDE.md backend/scripts/check_visit_flow.sh backend/scripts/rebuild_customer_search.py backend/scripts/rebuild_last_visit.py backend/tests/test_rebuild_last_visit.py
git commit -m "docs(visit): 최근 방문순 복구 스크립트, 흐름 확인 스크립트, 잠금 순서·대응표·하네스, 결정 기록 006"
```

---

