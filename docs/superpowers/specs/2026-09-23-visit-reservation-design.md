# 차곡노트 — 서브 프로젝트 ③-A 예약·방문 설계

- 작성일: 2026-09-23
- 상태: 사용자 검토 대기
- 범위: 백엔드 `visit` 스포크(방문·예약·상태 전이·매장 일정·메뉴표·카톡 예약 초안), 허브 포트 둘, `customer` 스포크 변경, Flutter 캘린더 탭·예약·방문·설정 화면, 카톡 공유 받기
- 앞선 문서: `docs/superpowers/specs/2026-09-20-foundation-design.md`(① 기반), `docs/superpowers/specs/2026-09-22-customer-pet-design.md`(② 고객), `_docs/decisions/005-customer-pet.md`
- 목업: `.superpowers/brainstorm/90957-1790135431/content/calendar-day.html`(달력·하루 화면), `reserve-flow.html`(예약 흐름·방문 상세)
- 다음 단계: 이 문서가 승인되면 구현 계획을 셋(③-A1 백엔드, ③-A2 앱, ③-A3 카톡 초안)으로 작성한다.

---

## 1. 배경과 이미 정해진 것

①·②에서 넘어온 결정이다. 다시 묻지 않는다.

- 방문 애그리거트: 예약 → 미용 중 → 완료 → (⑤) 알림장 발송됨은 하나의 애그리거트이고 스포크는 `visit`이다. 상태 전이는 `visit/domain/state/`(State 패턴)에 둔다.
- 고객(사람)이 기본이고 반려동물은 선택적인 하위 대상이다. 방문은 반려동물 없이도 성립한다.
- 권한은 ①의 시드에 있다: `reservation:write`(사장·직원), `shop:update`(사장만).
- 스포크끼리 import하지 않는다. 교차 협력은 허브 포트와 진입점의 자리 주입으로 한다(결정 기록 002).
- ②에서 넘어온 것: 방문 기록이 붙은 반려동물의 삭제 규칙, "최근 방문순" 정렬. 결정 기록 004에서 넘어온 것: 달력 머리말의 연도·월 이동 화살표, `flutter_animate`를 계속 둘지.
- 첫 매장 Hiss Haus는 1인샵이고 예약을 카카오톡으로 받는다. 합격 기준은 "카톡보다 쉬운가"다.

## 2. 사용자와 정한 것 (2026-09-23)

| 주제 | 결정 |
|---|---|
| ③ 나누기 | ③-A(예약·달력·방문 상태·노쇼 기록·카톡 초안)와 ③-B(체크리스트 자동 판정·주의 고객). ③-A를 매장에서 먼저 써 보고 ③-B 규칙을 정한다. |
| 예약 단위 | 방문 하나 = 반려동물 한 마리. 두 마리면 등록 화면에서 함께 골라 방문 둘을 만들고, 화면에서는 가족으로 묶어 보인다. **반려동물 없이 보호자만의 예약도 받는다.** |
| 시간 | 시작 시각(10분 단위) + 예상 소요(기본 2시간). 겹치면 경고만 하고 막지 않는다. |
| 메뉴 | 매장 메뉴표를 두되 **선택 사항**이다. 기본 메뉴를 미리 넣어 두고, 반려동물을 고르면 **지난 방문의 메뉴·소요로 미리 채운다.** 가격은 ④에서. |
| 다음 예약 | 완료 시트에서 "완료하고 다음 예약 잡기" — 그 아이의 주기(없으면 4주) 뒤 같은 요일·시간·메뉴로 채운 예약 화면을 연다. |
| 상태 | 예약됨 → (미용 중, 건너뛸 수 있음) → 완료 / 취소 / 노쇼. 예약 없이 온 손님은 "지금 시작". 되돌리기 허용. |
| 취소 사유 | [보호자 요청 / 매장 사정] 중 하나 필수. 당일 취소 여부는 계산한다. |
| 오프라인 캐시 | **넣지 않는다.** ①의 설계 2.2절 "오프라인 캐시는 ③에서 넣는다"를 이 결정이 대체한다(②와 같은 방향 — 개인정보를 기기에 쌓지 않는다). |
| 영업시간·휴무 | 영업시간 하나(기본 10:00~19:00), 매주 쉬는 요일, 임시 휴무일. 벗어나면 경고만. |
| 달력 | 기준 목업 그대로. 사진이 생기기 전(④ 전)에는 지난날 칸을 회색 사진 자리 + 마릿수로, 예약만 있는 날은 점선 칸 + 예약 수, 휴무일은 옅은 "휴무". 연·월 이동 화살표를 되살린다. |
| 하루 화면 | **목록이 기본, 아이콘으로 시간표 전환**(마지막 선택을 기기에 기억). 목록 카드에 바로 누르는 상태 버튼. |
| 예약 흐름 | ① 고객 찾기(②의 검색 그대로) → ② 날짜·시간·반려동물 칩·메뉴(미리 채움)·경고. 방문 상세는 상태에 맞는 버튼만, `···`에 수정·되돌리기·바로 완료. |
| 담당 미용사 | 넣지 않는다. 방문에는 만든 멤버만 남긴다. |
| 반복 예약 | **정기권 서브 프로젝트에서 함께 다룬다**(정기권 구매와 묶이는 흐름). ③-A는 "다음 예약"만. |
| 카톡 예약 초안 | 넣는다. 외부 전송 없는 규칙 기반 해석. **붙여넣기 버튼과 카톡 공유 받기 둘 다**(공유는 같은 초안 화면에 연결). 초안은 저장하지 않고 사람이 확인한 뒤 저장한다. |

## 3. 범위

### 3.1 만드는 것

1. 백엔드 `visit` 스포크: 방문 등록·수정·상태 전이·되돌리기·가족 한 번에 옮기기, 하루 목록, 월 요약, 시간 칸, "지난번처럼", 다음 예약 초안, 매장 일정 설정, 임시 휴무, 메뉴표, 카톡 초안 해석.
2. 허브 포트 `CustomerDirectoryPort`(customer 구현)와 `VisitLedgerPort`(visit 구현), 진입점 조립.
3. `ShopContext`에 `timezone`(tenancy의 매장 접근 확인이 이미 읽는 매장 행에서 채운다).
4. `customer` 변경: 반려동물 삭제 409 `PET_HAS_VISITS`, 무지개다리 409 `PET_HAS_UPCOMING_VISITS`, 익명화 409 `CUSTOMER_HAS_UPCOMING_VISITS`, 익명화 때 방문 메모 비우기, 검색 줄 `last_visit_at`과 "최근 방문순" 정렬, 고객 상세의 노쇼 횟수·다가오는 예약.
5. 앱: 캘린더 탭, 하루 화면(목록·시간표), 예약 2단계, 방문 상세, 완료·취소 사유 시트, 수정, 설정의 일정·메뉴 화면, 고객 탭 변경, 카톡 붙여넣기, iOS 공유 확장·안드로이드 텍스트 인텐트.
6. 규칙 문서: `CLAUDE.md` 잠금 순서에 "고객 행 → 방문 행", `_docs/architecture.md` 대응표에서 `visit/domain/state/`의 "(예정)" 제거.

### 3.2 만들지 않는 것

- 체크리스트 자동 판정, 주의 고객(③-B).
- 사진·기록·매출(④), 알림장(⑤), 알림(⑥).
- 반복 예약(정기권 서브 프로젝트), 담당 미용사 지정, 요일별 영업시간, 오프라인 캐시, LLM 해석(⑨ 이후).
- 자동 노쇼 처리 — 잘못 찍히면 고객 평판에 닿으므로 사람이 정리한다.

## 4. 백엔드 구조

- 새 스포크 `backend/apps/visit/`, API 프로세스(`main.py`)에 장착. 경로 앞부분 `/v1/shops/{shop_id}`.
- 폴더와 수직 슬라이스 1:1은 `_docs/architecture.md` 그대로다. 모든 라우터는 `require_permission("…")` 또는 `get_shop_context`로 `ShopContext`를 받고, 매장 범위 리포지토리 메서드는 `ShopContext`를 첫 인자로 받는다.
- 도메인(표준 라이브러리만):
  - `domain/state/`: 방문 상태별 클래스와 전이 규칙(6.1절). 잘못된 전이는 도메인 예외.
  - `domain/services/visit_schedule`: 끝 시각, 겹침, 영업시간·휴무 판정, 자정 넘김 검사, 매장 시간대의 하루 경계.
  - `domain/services/visit_cycle`: 다음 예약 주기(마지막 두 완료 방문 간격을 주 단위로 반올림, 없으면 4주, 1~12주로 자름).
  - `domain/services/draft_parser`: 카톡 글 해석(7절).
- 카톡 초안 해석은 아웃바운드 포트 `VisitDraftParserPort` 뒤에 둔다. 구현은 위 도메인 서비스를 부르는 어댑터이고, ⑨ 뒤에 LLM 어댑터로 바꿀 수 있다.
- 구조 계약(import-linter 6종)은 그대로다. 새 스포크는 "스포크 상호 독립"과 "core는 스포크를 import하지 않는다"에 자동으로 들어간다.

### 4.1 허브 포트

**`CustomerDirectoryPort`** — customer가 구현, visit이 쓴다. visit의 `dependencies/hub_ports.py`에 자리, `main.py`가 주입.

| 메서드 | 하는 일 |
|---|---|
| `lock_family(ctx, customer_id, pet_ids)` | 고객 행을 `FOR UPDATE`로 잠그고 살아 있는 고객인지, 반려동물이 모두 그 보호자의 아이이고 무지개다리가 아닌지 확인한다. 아니면 `CUSTOMER_NOT_FOUND`·`PET_NOT_FOUND`·`PET_PASSED_AWAY`. |
| `summaries(ctx, customer_ids, pet_ids)` | 이름·가린 번호·반려동물 이름·종류·품종 요약. 익명화한 고객은 이름 null. |
| `set_last_visit(ctx, customer_id, at)` | 검색 줄의 `last_visit_at`을 바꾼다(`at`은 null 가능). |
| `find_draft_candidates(ctx, words)` | 카톡 초안의 낱말로 고객·반려동물 후보를 찾는다(②의 검색 재사용, 최대 5 가족). |

**`VisitLedgerPort`** — visit이 구현, customer가 쓴다. customer의 `dependencies/hub_ports.py`에 자리, `main.py`가 주입.

| 메서드 | 하는 일 |
|---|---|
| `pet_has_visits(ctx, pet_id)` | 상태와 무관하게 방문이 하나라도 있는가. |
| `pet_has_upcoming(ctx, pet_id)` | 예약됨·미용 중 방문이 있는가. |
| `customer_has_upcoming(ctx, customer_id)` | 같은 질문을 고객 단위로. |
| `no_show_count(ctx, customer_id)` | 노쇼 횟수. |
| `upcoming_for_customer(ctx, customer_id, limit)` | 다가오는 예약(날짜·시각·반려동물 ID)을 시작 순으로 최대 `limit`개. 고객 상세가 쓴다. |
| `clear_customer_memos(ctx, customer_id)` | 그 고객 방문들의 `memo`를 비운다(익명화). |

### 4.2 잠금 순서

방문을 쓰는 모든 경로는 **고객 행(`lock_family`) → 방문 행(ID 오름차순 `FOR UPDATE`)** 순서로 잠근 뒤 상태를 다시 읽는다. customer 쪽 익명화·무지개다리·반려동물 삭제는 고객 행을 먼저 잠그고(②의 규칙) 그 안에서 `VisitLedgerPort`를 부른다 — 같은 순서다. 기존 규칙(유저 → 매장 → 멤버 → 초대)과 겹치는 경로는 없다. 잠금을 쥔 채 외부 HTTP를 부르지 않는다(초안 해석도 외부 호출 없음).

## 5. 데이터 모델 (3NF)

`shop_id`·`customer_id`·`pet_id`는 다른 스포크의 ID라 외래 키 없이 인덱스만 둔다. 스포크 안의 관계는 외래 키를 건다.

### 5.1 표

**`visit_shop_settings`** — 매장마다 한 줄

| 칸 | 형식 | 비고 |
|---|---|---|
| `shop_id` | bigint PK | |
| `opens_at`, `closes_at` | time | 기본 10:00, 19:00. CHECK `opens_at < closes_at` |
| `default_duration_minutes` | smallint | 기본 120. CHECK 10~600, 10의 배수 |
| `created_at`, `updated_at` | timestamptz | |

- 매장을 처음 쓸 때(설정·메뉴·예약 등록의 첫 호출) 기본값으로 만들고 **같은 트랜잭션에서 기본 메뉴를 넣는다**(`INSERT … ON CONFLICT DO NOTHING` — 동시에 열어도 한 번만). 설정 행이 있다는 것이 곧 기본 메뉴를 넣었다는 뜻이라 따로 표시 칸을 두지 않는다. tenancy의 매장 개설은 건드리지 않는다.

**`visit_weekly_closures`** — `(shop_id, weekday)` PK, `weekday` smallint CHECK 0~6(월=0). 쉬는 요일마다 한 행.

**`visit_closed_dates`** — `(shop_id, date)` PK, `note` text null(30자).

**`service_menus`**

| 칸 | 형식 | 비고 |
|---|---|---|
| `id` | bigint PK | |
| `shop_id` | bigint, 인덱스 | |
| `name` | text | 30자 |
| `default_duration_minutes` | smallint, null 가능 | null이면 매장 기본값 |
| `sort_order` | smallint | |
| `archived_at` | timestamptz, null 가능 | 지우지 않고 보관(지난 방문이 가리킴) |
| `created_at` | timestamptz | |

- 부분 유일: `UNIQUE (shop_id, name) WHERE archived_at IS NULL`.
- 기본 메뉴: 목욕 60분, 위생 60분, 부분 미용 90분, 전체 미용 150분, 스포팅 120분(첫 짐작, 사장이 바꾼다).

**`visits`** — 반려동물 한 마리(또는 보호자만)의 방문 하나

| 칸 | 형식 | 비고 |
|---|---|---|
| `id` | bigint PK | |
| `shop_id` | bigint, 인덱스 | 5.3절 |
| `customer_id` | bigint, 인덱스 | 필수. 5.3절 |
| `pet_id` | bigint, null 가능, 인덱스 | null이면 보호자만 |
| `starts_at` | timestamptz | 10분 단위 |
| `duration_minutes` | smallint | CHECK 10~600, 10의 배수 |
| `status` | text | CHECK `reserved`·`in_progress`·`completed`·`canceled`·`no_show` |
| `started_at` | timestamptz, null 가능 | 실제 시작 |
| `completed_at` | timestamptz, null 가능 | 실제 완료 |
| `canceled_at` | timestamptz, null 가능 | |
| `cancel_reason` | text, null 가능 | CHECK `customer_request`·`shop_reason` |
| `memo` | text, null 가능 | 500자 |
| `created_by_member_id` | bigint | |
| `status_changed_by_member_id` | bigint, null 가능 | 마지막으로 상태를 바꾼 멤버(③-B의 노쇼 근거) |
| `created_at`, `updated_at` | timestamptz | |

- CHECK:
  - `(status = 'canceled') = (canceled_at IS NOT NULL)` 그리고 `(status = 'canceled') = (cancel_reason IS NOT NULL)`
  - `(status = 'completed') = (completed_at IS NOT NULL)`
  - `status IN ('in_progress','completed') = (started_at IS NOT NULL)`
- 부분 유일(중복 예약 방지):
  - `UNIQUE (pet_id, starts_at) WHERE pet_id IS NOT NULL AND status IN ('reserved','in_progress')`
  - `UNIQUE (customer_id, starts_at) WHERE pet_id IS NULL AND status IN ('reserved','in_progress')`
- 색인: `(shop_id, starts_at)`, `(shop_id, customer_id)`, `(shop_id, pet_id)`.
- 겹침은 막지 않으므로 배타 제약을 두지 않는다.

**`visit_menus`** — `(visit_id FK → visits 삭제 시 함께, menu_id FK → service_menus)` PK.

### 5.2 3NF 점검

- **1NF:** 쉬는 요일·메뉴 선택은 배열이 아니라 행이다.
- **2NF:** 복합 키 표(`visit_weekly_closures`, `visit_closed_dates`, `visit_menus`)는 키 전체에만 종속하는 칸만 가진다.
- **3NF:**
  - 상태를 원본으로 두고, 시각 칸은 "언제 일어났는가"라는 사실만 담는다. 상태에서 계산되는 칸(취소 여부 등)을 두지 않고, 상태와 시각의 어긋남은 CHECK가 막는다.
  - 저장하지 않고 계산하는 것: 끝 시각, "지난번처럼"(그 아이의 마지막 완료 방문), 다음 예약 주기, 노쇼 횟수, 가족 묶음(같은 보호자 + 같은 시작 시각), 당일 취소 여부, 정리 안 된 예약.
  - 설정 행 존재가 기본 메뉴 준비를 뜻하므로 따로 칸을 두지 않는다.

### 5.3 역정규화 — 이유와 정합성

**`visits.customer_id`와 `visits.shop_id`.** 반려동물이 있는 방문이면 `pet_id`로 보호자가, 보호자로 매장이 정해진다(이행 종속). ②는 같은 이유로 `pets`에 `shop_id`를 두지 않았다. 여기서는 둔다.
- 왜: 다른 스포크라 조인할 수 없다. 반려동물 없는 방문에서는 보호자가 원본이다. 매장 격리 조회와 "이 고객의 앞으로의 예약·노쇼 횟수"에 색인이 필요하다.
- 정합성: 반려동물을 다른 보호자로 옮기는 API가 없다. 어긋날 수 있는 곳은 생성과 반려동물 변경 두 경로뿐이고, 둘 다 `lock_family`가 "이 반려동물은 이 보호자·이 매장의 아이"임을 잠금과 함께 확인한다. 수정에서 반려동물은 같은 보호자의 아이로만 바꿀 수 있다.

**`customer_search_entries.last_visit_at`(customer 스포크).** "최근 방문순" 정렬에 색인이 필요하다.
- 정합성: 완료·완료 되돌리기가 같은 트랜잭션에서 그 고객의 최신 완료 시각을 다시 계산해 `set_last_visit`로 넘긴다. 원본이 `visits`이므로 복구 스크립트는 visit 쪽(`scripts/rebuild_last_visit.py`)에 둔다. customer의 검색 줄 재생성 스크립트는 이 칸을 건드리지 않게 고친다.

### 5.4 익명화와의 관계

- 익명화한 고객의 방문은 남는다. `summaries`가 이름을 null로 돌려주고 앱은 "삭제된 고객"으로 표시한다.
- 앞으로의 예약이 있으면 익명화를 막는다(409). 지난 방문의 `memo`는 `clear_customer_memos`로 비운다.

## 6. 동작 규칙

### 6.1 상태 전이 (`visit/domain/state/`)

| 지금 | 행동 → 다음 | 조건 |
|---|---|---|
| 예약됨 | 시작 → 미용 중 | 예약일이 오늘이거나 지난 날(매장 시간대). 아니면 409 `VISIT_NOT_YET` |
| 예약됨 | 바로 완료 → 완료 | 같은 조건. 시작 시각 = 완료 시각 = 지금 |
| 예약됨 | 취소 → 취소 | 사유 필수 |
| 예약됨 | 노쇼 → 노쇼 | 예약 시각이 지난 뒤. 아니면 409 `VISIT_NOT_YET` |
| 미용 중 | 완료 → 완료 | |
| 미용 중·완료·취소·노쇼 | 되돌리기 → 예약됨 | 해당 시각·사유를 비운다. (⑤) 알림장을 보낸 뒤에는 불가 |
| — | 지금 시작 → 미용 중 | 예약 없이 온 손님. `starts_at` = 지금(10분 단위 내림), 시작 시각 = 지금 |

- 미용 중인 방문의 취소는 되돌린 뒤 취소한다.
- 전이는 `status_changed_by_member_id`를 찍는다.
- 되돌리기로 완료가 풀리거나 완료가 생기면 `set_last_visit`를 부른다.

### 6.2 등록·수정

- 등록: 반려동물 N마리 → 방문 N개를 한 트랜잭션으로. 빈 목록이면 보호자만의 방문 하나. 메뉴·소요를 비우면 소요는 메뉴 기본값의 합(메뉴가 있을 때) 또는 매장 기본값.
- 범위: `starts_at`은 오늘 기준 앞으로 1년·뒤로 1년. 지난 날짜도 받는다(카톡에 흩어진 지난 방문을 옮겨 적기 — 만들면 "정리 안 됨"이 된다). 끝 시각이 그날(매장 시간대) 24시를 넘으면 422 `VISIT_CROSSES_MIDNIGHT`.
- 수정: 날짜·시간·반려동물은 예약됨일 때만. 반려동물은 같은 보호자의 아이로만. 메뉴·소요·메모는 미용 중·완료일 때도.
- 가족 한 번에: `POST /visits/transitions`와 `POST /visits/reschedule`은 방문 ID 여러 개를 받고, 모두 같은 보호자의 방문이어야 하며(아니면 422), 전부 성공하거나 전부 실패한다.
- 중복: 5.1절의 부분 유일 색인에 걸리면 409 `VISIT_DUPLICATE`. 앱은 "이미 저장됐어요"로 처리하고 그날 목록을 다시 읽는다.
- 메뉴: 요청의 메뉴 ID가 이 매장의 보관되지 않은 메뉴가 아니면 422 `MENU_NOT_FOUND`.

### 6.3 경고와 시간 칸

- 경고는 막지 않는다. 종류: `overlap`(예약됨·미용 중 방문과 시간이 겹침), `closed_day`(쉬는 요일·임시 휴무), `outside_hours`(영업시간 밖).
- `GET /visits/slots`가 정시 칸마다 경고를 돌려준다. 앱의 줄긋기와 경고 문구는 이 응답만 쓴다 — 경고 판단은 서버 한 곳에만 있다. 10분 단위 시각을 고르면 그 시각으로 한 번 더 부른다.
- 등록·옮기기 응답에도 같은 경고 목록을 싣는다.

### 6.4 정리 안 된 예약

- 시작 시각이 지난 날(매장 시간대로 오늘 이전)인데 예약됨인 방문. 월 요약에 날마다 수를, 하루 목록에서 강조를, 캘린더 탭 위에 "정리 안 된 예약 N건" 줄을 띄운다(누르면 가장 오래된 날로).

### 6.5 "지난번처럼"과 다음 예약

- `GET /visits/defaults?pet_id=`: 그 아이의 마지막 완료 방문의 메뉴(보관된 메뉴는 뺀다)와 소요. 없으면 빈 메뉴와 매장 기본 소요.
- `GET /visits/{id}/next-draft`: 완료한 방문 기준, 주기(4절) 뒤 같은 요일·시간, 같은 메뉴·소요, 같은 반려동물(가족 묶음이면 가족 전체). 저장하지 않고 초안만 돌려준다.

## 7. 카톡 예약 초안

- `POST /visit-drafts {text}` → `{date, time, customer_candidates[], pet_ids[], menu_ids[], guessed: {date, time, who, menu}}`. 저장하지 않는다.
- 입력 1,000자 제한. 글은 DB·로그에 남기지 않고, 오류 응답에 되돌려주지 않는다(접근 로그는 본문을 쓰지 않는다 — 기존 규칙).
- 해석 규칙(매장 시간대의 오늘 기준):
  - 날짜: 오늘·내일·모레·글피, `(이번|다음) 주 X요일`, `X요일`(가장 가까운 앞날, 오늘 포함 안 함), `M/D`, `M월 D일`, `D일`(이번 달, 지났으면 다음 달). "다음 주"는 다음 달력 주(월요일 시작)이고 항상 짐작함으로 표시한다.
  - 시간: `(오전|오후|저녁|낮) H시( 반| M분)?`, `HH:MM`, `H시`. 오전·오후가 없으면 영업시간 안쪽 해석을 고르고 짐작함으로 표시한다.
  - 누구: 한글·숫자 낱말로 나눠 `find_draft_candidates`로 찾는다. 반려동물 이름 일치를 먼저 두고, 후보가 하나면 고른 상태로, 여럿이면 목록으로.
  - 메뉴: 매장의 보관되지 않은 메뉴 이름을 글이 포함하면.
  - 못 찾은 칸은 비운다. 모든 결과는 사람이 확인한 뒤 등록 API로 저장한다.
- 앱 입구 둘:
  - 예약 ① 화면 위 [카톡 붙여넣기] — 클립보드를 읽는다(iOS 붙여넣기 허용 안내는 시스템이 한 번 띄운다).
  - 공유 받기 — iOS 공유 확장·안드로이드 `ACTION_SEND` 텍스트. **확장은 글만 앱 본체에 넘기고 앱을 연다.** 토큰에 접근하지 않으며 서버 호출은 앱 본체가 한다. 카톡이 넘기는 형태(글만인지, 보낸 사람·시각이 붙는지)는 실기기에서 확인한다.

## 8. API

모두 API 프로세스, 경로 앞부분 `/v1/shops/{shop_id}`. 오류 본문은 `{code, message}`.

| 메서드·경로 | 권한 | 하는 일 |
|---|---|---|
| `GET /visits?date=` | 멤버 | 하루 목록: 방문, 이름 요약, 가족 묶음, 겹침 표시, 정리 안 됨 표시, 상태별 수 |
| `GET /visits/calendar?month=` | 멤버 | 날마다 전체·완료·예약·정리 안 됨 수, 휴무일 |
| `GET /visits/slots?date=&duration=&at=` | 멤버 | 정시 칸(또는 `at` 한 시각)의 경고 |
| `GET /visits/defaults?pet_id=` | 멤버 | "지난번처럼" 메뉴와 소요 |
| `POST /visits` | `reservation:write` | `{customer_id, pet_ids, starts_at, duration_minutes?, menu_ids, memo?, walk_in}` → 방문들 + 경고 |
| `GET /visits/{visit_id}` | 멤버 | 상세, 같은 묶음, 지난 방문, 노쇼 횟수 |
| `PUT /visits/{visit_id}` | `reservation:write` | 수정(6.2절) |
| `POST /visits/transitions` | `reservation:write` | `{visit_ids, action, cancel_reason?}` |
| `POST /visits/reschedule` | `reservation:write` | `{visit_ids, starts_at}` → 경고 |
| `GET /visits/{visit_id}/next-draft` | 멤버 | 다음 예약 초안 |
| `GET /visit-settings` | 멤버 | 영업시간, 기본 소요, 쉬는 요일 |
| `PUT /visit-settings` | `shop:update` | 위 전체 교체 |
| `GET /closed-dates?from=&to=` | 멤버 | 임시 휴무 |
| `POST /closed-dates` | `shop:update` | 추가(이미 있으면 그대로 200) |
| `DELETE /closed-dates/{date}` | `shop:update` | 삭제 |
| `GET /menus?include_archived=false` | 멤버 | 메뉴표 |
| `POST /menus` | `shop:update` | 추가(이름 겹치면 409 `MENU_NAME_TAKEN`) |
| `PUT /menus/{menu_id}` | `shop:update` | 이름·기본 소요·순서 |
| `POST /menus/{menu_id}/archive` | `shop:update` | 보관 |
| `POST /visit-drafts` | `reservation:write` | 카톡 글 → 초안(7절) |
| `GET /visits/myself` | 멤버 | 이 묶음의 엔드포인트·데이터·제약 설명 |

규칙:
- 다른 매장의 방문·메뉴 ID는 404(메뉴를 요청 본문에 넣은 경우는 422 `MENU_NOT_FOUND`).
- 새 오류 코드 — visit: `VISIT_NOT_FOUND`(404), `VISIT_STATE_CONFLICT`(409), `VISIT_NOT_YET`(409), `VISIT_DUPLICATE`(409), `VISIT_CROSSES_MIDNIGHT`(422), `VISIT_GROUP_MISMATCH`(422), `PET_PASSED_AWAY`(422), `MENU_NOT_FOUND`(422), `MENU_NAME_TAKEN`(409). customer: `PET_HAS_VISITS`(409), `PET_HAS_UPCOMING_VISITS`(409), `CUSTOMER_HAS_UPCOMING_VISITS`(409). 앱의 오류 문구 표에 더한다.
- customer 쪽 변경: `GET /customers?sort=recent|name|last_visit`, `GET /customers/{id}`에 `no_show_count`와 `upcoming_visits`(`upcoming_for_customer`로 최대 3개 — 반려동물 이름은 customer가 자기 표에서 붙인다).

## 9. 앱

### 9.1 화면

1. **캘린더 탭** — 큰 세리프 월·연도와 이동 화살표, 월 달력(지난날 회색 사진 자리 + 마릿수, 예약만 있는 날 점선 칸 + 수, 휴무 옅은 글자, 오늘 검정 테두리), 선택한 날 미리보기 글래스 카드(시간·이름·상태 줄), 위쪽 "정리 안 된 예약 N건" 줄. 미리보기를 누르면 하루 화면.
2. **하루 화면** — 큰 날짜, 상태별 수, [목록 / 시간표] 아이콘 토글(마지막 선택을 기기에 저장). 목록 카드: 시간·끝 시각·사진 자리·이름(가족은 겹친 사진 자리)·메뉴·보호자·상태 버튼(예약됨 [시작], 미용 중 [완료하기], 완료 표시). 빈 시간은 "— N시간 비어 있음 —", 겹침·정리 안 됨은 작은 표시.
3. **예약 등록** — ① 고객 찾기(② 검색 재사용, 없으면 새 고객 등록으로) ② 보호자 카드와 반려동물 칩(+ "보호자만"), 날짜 줄(휴무 옅게), 시간 칸(`slots`로 줄긋기, 눌러도 경고만, 길게 눌러 10분 단위), 메뉴·소요(미리 채움 + "지난번과 같게 채웠어요"), 메모, 저장 버튼에 날짜·시간. 달력에서 날짜를 고른 뒤 +면 그 날짜로 시작. ① 위 [카톡 붙여넣기].
4. **방문 상세** — 사진 자리와 상태 표시, 이름·품종·몸무게·보호자, 날짜·메뉴·메모·지난 방문·노쇼 횟수, 상태에 맞는 버튼, `···`에 수정·되돌리기·바로 완료. 취소 → 사유 시트. 완료 → [완료 / 완료하고 다음 예약 잡기] 시트.
5. **수정** — 등록 ②와 같은 폼. 묶음 방문의 시간을 바꾸면 "보리도 같이 옮길까요?".
6. **설정 → 일정·메뉴**(사장에게만 보임) — 영업시간, 기본 소요, 쉬는 요일 칩, 임시 휴무 목록, 메뉴 목록(추가·이름·기본 소요·순서·보관).
7. **고객 탭 변경** — 정렬에 "최근 방문순", 상세에 노쇼 횟수와 다가오는 예약, 새 409 문구.

### 9.2 상태와 규칙

- 기능 폴더 `lib/features/visit/{screens,state,api}`, 설정 화면은 `lib/features/shop`에 더한다. `design/widgets`만 쓰고 새 위젯이 필요하면 거기에 더한다.
- 매장 범위 컨트롤러는 `autoDispose.family` + 모든 서버 호출 `runShopScoped`. 저장 중 버튼 비활성, 오류 화면에 다시 시도·뒤로 가기, 하위 화면 머리에 `AppBackButton`.
- 스크롤 목록은 불투명 `AppCard`, 글래스는 떠 있는 층(탭바·미리보기 카드·시트)에만.
- 상태 전이 뒤에는 그날 목록과 그 달 요약을 다시 읽는다(낙관적 갱신을 하지 않는다 — 409가 나면 화면이 서버와 어긋나기 때문).
- 직원에게 일정·메뉴 수정을 보이지 않는다(보안 경계는 서버 403).
- `flutter_animate`: ③-A2에서 쓸 곳이 없으면 의존성에서 뺀다.

## 10. 위협 점검표

| # | 시나리오 | 막는 곳 |
|---|---|---|
| V1 | A매장 멤버가 B매장 방문·메뉴 ID를 부른다 | `ShopContext`로 거름 → 404, 요청 본문의 메뉴는 매장 대조 → 422 |
| V2 | 다른 보호자·다른 매장의 반려동물을 끼워 예약한다 | `lock_family`의 소속 확인 |
| V3 | 익명화와 예약 생성·되돌리기가 겹친다 | 고객 행을 먼저 잠금 → 익명화 뒤엔 404, 예약 뒤엔 익명화 409 |
| V4 | 두 기기가 같은 방문에 완료와 노쇼를 동시에 누른다 | 방문 행 잠금 + 재확인 → 한쪽 409 |
| V5 | 저장을 두 번 눌러 중복 예약 | 부분 유일 색인 → 409 `VISIT_DUPLICATE` |
| V6 | 가족 전이·옮기기가 절반만 된다 | 한 트랜잭션, 전부 아니면 전무 |
| V7 | 무지개다리·익명화 뒤에 앞으로의 예약이 남는다 | 409 두 가지 |
| V8 | 직원이 일정·메뉴를 바꾼다 | `shop:update` → 403 |
| V9 | 카톡 글(개인정보)이 로그·DB·오류 응답에 남는다 | 저장 없음, 오류에 되돌려주지 않음 |
| V10 | 시각 전 노쇼, 미래 날 시작 | 상태 규칙 → 409 |
| V11 | 익명화한 고객의 방문 메모에 개인정보가 남는다 | `clear_customer_memos` |
| V12 | 공유 확장이 토큰에 접근한다 | 확장은 글만 넘김 |
| V13 | 반려동물을 수정으로 다른 보호자의 아이로 바꾼다 | 같은 보호자로만, `lock_family` 재확인 |
| V14 | 묶음 전이에 다른 보호자의 방문 ID를 섞는다 | 422 `VISIT_GROUP_MISMATCH` |

## 11. 테스트와 검증

- **백엔드**
  - 도메인 단위: 상태 전이 표 전체(허용·거부), 일정 판정(겹침·휴무·영업시간 밖·자정 넘김·하루 경계), 주기 계산, 초안 해석기(날짜·시간 표현 표 기반, 모호한 표현의 짐작함 표시).
  - 인터랙터: 스텁 포트(①의 관례).
  - 통합(실제 Postgres): 첫 테스트는 테넌트 격리(V1). 잠금(V3·V4)은 "막힌 호출을 `create_task`로 쥐고 그 결과를 본다" 방식이고, 잠금을 빼는 변이로 실패를 확인한다(① 교훈: `asyncio.gather` 동시성 테스트는 판별력이 없다, FK의 `KEY SHARE` 암묵 차단이 거짓 통과를 만든다). 중복(V5), 묶음 원자성(V6), customer 409 셋(V7), 권한(V8), 초안이 로그에 남지 않음(V9).
  - 스키마 드리프트, 구조 계약 6종, 라우트 구조 검사(두 앱), 흐름 확인 스크립트 `backend/scripts/check_visit_flow.sh`.
- **앱**
  - 컨트롤러·API 테스트(가짜 어댑터), 화면 위젯 테스트, 골든(월 달력, 하루 목록·시간표, 예약 ②, 방문 상세, 완료 시트).
  - `flutter analyze` 0건.
- **완료 기준**(시뮬레이터에서 사용자와 함께): 두 마리 예약 → 달력 → 하루 목록·시간표 전환 → 시작 → 완료 + 다음 예약 → 취소 사유 → 노쇼 → 되돌리기 → 겹침·휴무 경고 → 카톡 붙여넣기 초안 → 고객 탭 최근 방문순 → 직원 계정에서 일정·메뉴 수정 없음. 공유 확장은 실기기에서 확인한다.

## 12. 구현 계획 나누기

설계는 이 문서 하나, 구현 계획은 셋이다. 계획마다 머리말에 위협 점검표의 해당 줄을 막는 코드·테스트와 짝지어 둔다(①의 교훈).

- **③-A1 백엔드** — `ShopContext.timezone` → 허브 포트 둘 → visit 도메인(상태·일정·주기) → 마이그레이션·ORM → 설정·메뉴 → 방문 등록·조회·전이·옮기기 → customer 변경 → 통합 테스트 → 흐름 스크립트, 규칙 문서(잠금 순서, 대응표).
- **③-A2 앱** — 캘린더 탭, 하루 화면, 예약 2단계, 방문 상세·시트, 설정 화면, 고객 탭 변경, 시뮬레이터 흐름 확인.
- **③-A3 카톡 초안** — 해석기(도메인·표 기반 테스트) → 초안 API → 앱 붙여넣기 → iOS 공유 확장·안드로이드 인텐트(실기기 확인), 결정 기록 006.

## 13. 이후 서브 프로젝트로 넘기는 것

- **③-B:** 체크리스트 자동 판정(`visit/domain/chain/`), 주의 고객(매장 안에서만) — 노쇼 횟수와 `status_changed_by_member_id`를 근거로 쓴다.
- **④:** 기록·사진이 붙은 완료 방문을 되돌릴 수 있는지, 달력 칸의 대표 사진, 방문마다 몸무게, 실제 메뉴·가격·매출.
- **⑤:** 알림장을 보낸 방문의 되돌리기 금지.
- **⑥:** 예약 확인·리마인드 알림(방문 등록·옮기기·취소가 발송 시점).
- **정기권(새 서브 프로젝트):** 선불·횟수 차감과 반복 예약("N주마다"). 순서표 위치는 ④ 설계 때 정한다. 이 설계에서 반복 규칙을 넣지 않은 이유: 정기권 구매와 묶이는 흐름이고, "이 예약만 / 이후 전부"·휴무와 겹치는 회차 처리가 함께 따라온다.
- **필요해지면:** 담당 미용사 지정(방문에 칸 하나), 요일별 영업시간(`visit_weekly_closures`를 요일별 시간 표로 넓힘).
- **⑨ 이후:** 카톡 초안의 LLM 해석 — `VisitDraftParserPort` 뒤에서 어댑터만 바꾸고, 외부 전송 전 마스킹 Decorator를 거친다.
