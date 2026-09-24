# 차곡노트 — 서브 프로젝트 ④ 미용 기록·피드 뷰 설계

- 작성일: 2026-09-24
- 상태: 사용자 검토 대기
- 범위: 새 스포크 `media`(사진·영상 객체, S3 presigned 업로드), `visit` 스포크의 기록(사진·몸무게·실제 메뉴·가격·결제·메모), 피드·달력 대표 사진, `customer` 프로필 사진·몸무게 동기화, 메뉴 가격, Flutter 기록 화면·피드·사진 넘기기·크게 보기, 영상, 말로 기록하기. 그리고 ③까지의 코드에서 찾은 SOLID 위반 정리(④-0).
- 앞선 문서: `docs/superpowers/specs/2026-09-23-visit-reservation-design.md`(③-A), `_docs/decisions/006-visit-reservation.md`, `docs/superpowers/specs/2026-09-22-customer-pet-design.md`(②), `_docs/decisions/005-customer-pet.md`
- 목업: `.superpowers/brainstorm/67059-1789889527/content/mono-tone.html`(달력 칸 대표 사진, 미리보기 카드, "하루 기록" 화면 — 기울어진 사진 넘기기·글래스 이름 카드·오늘의 케어)
- 다음 단계: 이 문서가 승인되면 구현 계획을 다섯으로 작성한다(④-0 SOLID 정리 백엔드·앱 둘, ④-1 백엔드, ④-2 앱, ④-3 영상·음성).
- 고친 것(2026-09-24, ④-0 병합 뒤 사용자 결정): 업로드를 기기에 저장되는 **업로드 대기열**로(10.2), 사진 하나를 기록 끝에 붙이는 **덧붙이기 API**와 그것이 전체 교체 PUT에 덮이지 않게 하는 **기록 버전**(6.1·8·9), 업로드 취소는 오류가 아니다(10.2), ④-0 앱에서 미룬 것의 자리(4.2 끝), ④-2 뒤 **오류 화면 다듬기**(14).

---

## 1. 배경과 이미 정해진 것

①~③에서 넘어온 결정이다. 다시 묻지 않는다.

- 방문은 `visit` 한 애그리거트다. 예약 → 기록 → (⑤) 알림장이 그 위에 쌓인다. 기록은 방문에 붙는다.
- 미디어: AWS S3 서울 리전(개발은 MinIO), presigned URL로 앱이 직접 올린다. 썸네일은 앱이 만든다. 고객이 내려받아 SNS에 올리므로 사진은 고화질(긴 변 약 3000px), 영상은 1080p. S3 키는 `shops/{shop_id}/` 접두사. 영상 누적 저장에는 수명주기 정책이 필요하다.
- 메모는 내부 메모(비공개)와 알림장 내용(고객 공개)으로 나눈다. 공개 API는 공개 필드만 내보낸다(⑤).
- 권한은 ①의 시드에 있다: `record:write`(미용 기록·사진 업로드, 사장·직원), `sales:write`(기록할 때 매출 금액 입력, 사장·직원), `sales:read`(매출 통계, 사장만), `shop:update`(메뉴 가격, 사장만).
- 스포크끼리 import하지 않는다. 교차 협력은 허브 포트와 진입점의 자리 주입으로 한다(결정 기록 002). 잠금 순서는 고객 행 → 방문 행(ID 오름차순). 잠금을 쥔 채 외부 HTTP를 부르지 않는다.
- 006이 ④로 넘긴 판단: 사진·기록이 붙은 완료 방문의 되돌리기, 달력 칸의 대표 사진, 방문마다 몸무게, 실제 메뉴·가격·매출. 005가 넘긴 것: 반려동물 프로필 사진, 격자 보기를 기본으로 할지. 정기권 서브 프로젝트의 순서표 위치.
- CallGuard에서 옮기기로 한 "말로 기록하기": 기기 내장 STT 우선, LLM 분리는 외부 전송 전 마스킹 계층을 거친다(⑤·⑨).
- 디자인: 무채색 에디토리얼 톤, 사진은 흰 테두리의 둥근 사각형, 마릿수는 사진 안쪽 우측 하단 흰 동그라미, 글래스는 사진 위에 떠 있는 조작 층(탭바·시트·이름 카드)에만. 사용자가 준 레퍼런스를 재해석하지 않는다.
- 첫 매장 Hiss Haus는 1인샵이다. 사장님은 적는 걸 귀찮아한다. 입력은 최소, 사진이 중심.

## 2. 사용자와 정한 것 (2026-09-24)

| 주제 | 결정 |
|---|---|
| ③-B보다 ④ 먼저 | ③ 설계가 "③-A를 매장에서 써 본 뒤 ③-B 규칙을 정한다"고 했고, ④는 ⑤ 알림장·⑧ 통계의 전제다. |
| 기록 하나의 내용 | 사진 여러 장(전·후 구분) + 영상(1080p) + 몸무게 + 실제 메뉴·가격·총액·결제 수단 + 케어 메모(공개) + 내부 메모(비공개) + 말로 기록하기(기기 STT 받아쓰기). |
| 입력 시점 | **시작부터 열리고 완료 때 마무리.** [시작]을 누른 순간부터 방문 상세에 사진 추가가 열린다(전 사진). [완료]를 누르면 기록 화면(몸무게·메뉴·가격·메모)이 뜨고 저장하면 완료. 사진은 완료 뒤에도 더 넣을 수 있다. "나중에 적고 완료"로 기록 없이 완료할 수도 있다. |
| 메모 | 케어 메모(⑤ 알림장에 그대로 실림) + 내부 메모(매장만). 예약 단계의 `visits.memo`는 그대로 둔다. |
| 피드 자리 | 캘린더 탭 안 [달력 / 피드] 아이콘 토글. 탭바는 그대로. 반려동물 상세에도 그 아이의 기록 피드. |
| 매출 칸 | 항목별 금액(메뉴 정가에서 미리 채움, 고칠 수 있음) + **총액(따로 저장, 받은 돈이 원본)** + 결제 수단 [카드 / 현금 / 계좌이체]. 할인은 총액을 고쳐 표현한다. |
| 구조 | **새 스포크 `media` + presigned 직접 업로드.** visit 안에 미디어 표를 두는 안과 서버 경유 업로드 안은 기각. |
| 미디어 최적화 | 렌디션 셋(원본 3000·표시 1080·썸네일 400px), EXIF 제거, 프로그레시브 JPEG, 서명 URL 만료 하루 반올림, S3 수명주기 규칙, 앱 캐시 상한. WebP·중복 제거는 보류. CDN은 ⑤에서. |
| SOLID | **점검에서 나온 위반을 전부 고치면서 진행한다.** ④가 건드리는 곳만 고치는 안은 기각. 기능 작업과 섞이지 않게 ④-0 계획으로 앞에 둔다. 앱의 상태 문자열 → enum 전환도 포함. |
| 정기권 순서 | ④ → ⑤ 알림장 → **정기권** → ⑥ 알림톡. 정기권은 순수 소프트웨어라 알림톡 계약을 기다릴 필요가 없고, 매출(④)이 서 있어야 선불·차감이 성립한다. |

## 3. 범위

### 3.1 만드는 것

1. `media` 스포크: 미디어 객체 표, S3 아웃바운드 포트와 boto3 어댑터, 발급·확인 API, 허브 포트 `MediaLibraryPort` 구현, 정리 스크립트, 버킷 준비 스크립트(수명주기 규칙 포함).
2. `visit` 기록: 표 셋(`visit_records`·`visit_record_items`·`visit_record_media`), 메뉴 가격, 기록 PUT/DELETE, 피드, 상세·하루·달력 응답에 사진, 몸무게 동기화, `VisitLedgerPort.latest_covers`.
3. `customer` 변경: 프로필 사진(가장 최근 완료 기록의 대표 사진), `CustomerDirectoryPort.set_pet_weight`, 익명화 때 기록 메모 비우기.
4. 허브: `MediaLibraryPort`, 허브 포트 오류 바탕 클래스.
5. 앱: 기록 화면(완료 흐름), 방문 상세 사진 넘기기·크게 보기, 사진 업로드(리사이즈·EXIF 제거·진행 상태), 캘린더 [달력/피드] 토글, 달력 대표 사진·미리보기 겹친 사진, 고객 탭 프로필 사진·[기록] 탭, 메뉴 가격 칸.
6. 영상(압축·포스터·재생·저장)과 말로 기록하기(기기 STT 받아쓰기).
7. SOLID 정리(4절).

### 3.2 만들지 않는 것

- CDN(CloudFront) — ⑤에서. 공개 페이지용 URL 수명도 ⑤.
- WebP·AVIF 전송, 해시 중복 제거 — 규모가 커지면.
- 서버 측 이미지 디코딩(썸네일 생성·EXIF 검증) — 앱이 만든다. ⑤ 공개 전에 서버 검증 재검토.
- 음성의 LLM 분리(미용 내용·내부 메모·매출 자동 분리) — ⑨ 이후, 마스킹 계층 뒤에서.
- 반려동물 프로필 사진의 별도 업로드 — 기록의 대표 사진을 쓴다.
- 오프라인·목록 캐시(③ 결정 유지). 사진 캐시는 표시용일 뿐이다.
- 통계 화면(⑧). 이 설계는 원본 칸(`total_amount`·`payment_method`)만 둔다.
- 알림장 보낸 방문의 되돌리기 금지(⑤).

## 4. SOLID 점검 결과와 정리 (④-0)

2026-09-24에 ①~③ 코드를 다섯 원칙으로 감사했다. 구조를 흔드는 위반은 없었다. 백엔드는 의존 역전이 명령으로 확인해 예외 없이 지켜지고(app·domain이 sqlalchemy·fastapi·pydantic을 import하는 곳 0건, 조립은 `dependencies/`와 `main.py`뿐), 앱도 `lib/features`에 dio·secure storage·MethodChannel 직접 import가 0건이다. 약한 축은 백엔드의 인터페이스 분리·리스코프, 앱의 개방·폐쇄·인터페이스 분리다. 아래 항목을 **전부** ④-0에서 고친다. 기능 코드를 더하기 전이라 검증은 "기존 테스트가 전후로 통과하고 라우트 표·API JSON이 같다"이다.

### 4.1 백엔드

| # | 원칙 | 발견 | 처방 |
|---|---|---|---|
| B1 | I | `VisitRepository`가 메서드 20개(쓰기·잠금 / 원장 / 달력 / 이력 네 축). 메서드 하나만 쓰는 인터랙터도 20개짜리를 받는다. | 포트 넷으로 나눈다: `VisitWriteRepository`(create_many·get·get_many·lock·update_details·reschedule·apply_changes), `VisitLedgerRepository`(pet_has_visits·customer_has_active·list_active_from·clear_memos·count_no_show), `VisitBoardRepository`(list_between·unresolved_before·list_occupied), `VisitHistoryRepository`(latest_completed_start·list_group·last_completed_before·last_completed_of_pet·completed_starts). pg 구현은 클래스 하나가 넷을 다 상속한다. `visit_wiring.py`는 그대로 한 인스턴스를 돌려주되 반환 타입이 좁다. `lock_visits`는 `get_many`·`lock`만 가진 `VisitLockRepository`를 받고 `VisitWriteRepository`가 이를 상속한다. |
| B2 | L | 허브 포트가 예외 타입을 계약에 넣지 않는다. customer 구현이 던지는 `PetNotFoundError` 등을 visit은 모른 채 전파하고 `main.py`가 전 스포크 오류 맵을 합쳐 동작만 맞춘다. 테스트 스텁은 다른 예외를 던진다. | `hub/app/errors.py`에 `HubPortError(code, message)` 바탕과 포트별 하위 예외(`FamilyNotFoundError`, `PetPassedAwayError`, `MediaNotReadyError`, `MediaAlreadyAttachedError` …)를 둔다. 포트 구현은 자기 도메인 오류를 잡아 허브 예외로 바꿔 던진다. 소비 스포크의 `error_map.py`는 허브 예외를 매핑한다. 스텁도 같은 예외를 던진다. `main.py`의 오류 맵 합치기는 유지하되 허브 예외 맵이 더해진다. |
| B3 | L | 테스트 스텁이 포트 ABC를 상속하지 않아 메서드 누락이 `AttributeError`로 늦게 잡힌다. | 모든 스텁(`apps/*/tests/helpers/fakes.py`)이 ABC를 상속한다. |
| B4 | S | `transition_visits_interactor`에 되돌리기 전용 분기 둘(잠금 전 pet_ids 수집, 잠금 뒤 재검증)과 완료 후속 동기화(`set_last_visit`)가 쌓여 있다. ④의 몸무게 동기화가 더해지면 또 붙는다. | 되돌리기 전 확인은 `domain/state/`가 "이 전이에 필요한 확인"을 돌려주게 하고, 완료 후속 처리는 `app/services/completion_effects.py` 하나로 뺀다(최근 방문 갱신, ④의 몸무게 동기화는 기록 슬라이스가 같은 서비스를 부른다). 인터랙터는 잠금·전이·후속 호출만 남는다. |
| B5 | O | 새 상태를 더하면 다섯 곳(`ACTIVE_STATUSES`, `COUNTED`, ORM CHECK, 부분 색인, `DayCountsView` 상태별 칸)을 고친다. | 상태 집합의 단일 원천은 `domain/state/`다. 각 상태 클래스가 `is_active`·`counts_as_visit` 속성을 갖고 `ACTIVE_STATUSES`·`COUNTED`는 거기서 파생한다. `DayCountsView.of(counts)`가 매핑 한 곳에서 만든다(JSON 모양은 그대로). ORM CHECK·부분 색인은 마이그레이션이라 남기되 `tests/test_schema_drift.py` 옆에 "도메인 상태 집합 = CHECK 목록" 대조 테스트를 둔다. |
| B6 | O | 행동 축이 닫혀 있지 않다: `ACTIONS` 집합, 바탕 클래스 메서드 다섯, `transition()`의 if 체인, 스키마 `Literal`, 인터랙터의 `"revert"` 분기. | `transition()`은 `ACTIONS` 검증 뒤 `getattr(state, action)`으로 보낸다. 스키마 `Literal`은 API 계약이라 남긴다. 인터랙터 분기는 B4로 사라진다. |
| B7 | S | 도메인 규칙이 인터랙터에 있다: 소요 시간 기본값(메뉴 합산), 초안 후보 순위(rank 0~3). 상수가 import 사이에 끼어 있다. | `visit/domain/services/visit_duration.py`, `customer/domain/services/draft_ranking.py`로 옮기고 도메인 단위 테스트를 붙인다. |
| B8 | S | `core/security.py`가 서명 검증·users 상태 확인(의도한 예외)·재인증 정책(`require_recent_login`, 300초) 셋을 맡는다. 재인증은 auth 도메인 규칙이다. | 재인증 창(300초)과 판단을 auth 스포크의 도메인 서비스로 옮기고, `core/security.py`는 토큰 검증과 라우터 의존성만 남긴다. 연결·해제·탈퇴 라우터가 인증 프로세스에 있으면 그대로 auth에서 import하고, API 프로세스 라우터도 쓰면 core에 "자리"를 두고 `auth_main.py`가 꽂는다(계획 ④-0에서 실제 위치를 확인해 정한다). |
| B9 | D | app DTO(`VisitView.of`)가 `ZoneInfo`로 시간대 변환을 한다. | 유지. "응답 시각은 매장 시간대"가 스포크 규칙이고 표준 라이브러리다. 기록한다. |
| B10 | S | `ScheduleRepository.ensure`가 기본 메뉴를 넣는다. | 유지. `visit/CLAUDE.md`가 명시한 의도다(설정 행과 기본 메뉴는 같은 트랜잭션). 기록한다. |

### 4.2 앱

| # | 원칙 | 발견 | 처방 |
|---|---|---|---|
| A1 | O | 방문 상태 문자열 `switch`가 다섯 파일에 흩어져 있고 `_ =>` 폴백 때문에 새 상태·행동이 UI에서 조용히 빠진다. `VisitStatus`가 문자열 상수다. 완료 후속 행동(`VisitChoice.thenNext`·`draft`)이 bool 둘이다. | `VisitStatus`를 enum으로(서버 문자열은 `fromJson`에서 한 번 변환, 모르는 값은 `unknown`). 완료 후속 행동을 sealed 타입 `AfterComplete { none, nextReservation, record }`로. 모든 `switch`는 폴백 없이 완전 열거. |
| A2 | I | 화면 14곳이 세션 컨트롤러 전체를 watch한다(`.select` 0건). `reloadMe`마다 화면 전체가 재빌드된다. `_shopId` getter가 15개 화면에 복붙. | `selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider` 파생 프로바이더 셋. 화면은 그것만 watch한다. |
| A3 | I | 기기 설정 저장소가 항목마다 read/write 쌍을 인터페이스와 두 구현에 요구한다. `day_view_mode`·`customer_view_mode`가 복사본이고 [달력/피드] 토글이 셋째가 된다. | `PrefsStore`를 `read(key)`·`write(key, value)`·`remove(key)`로 줄이고, 보기 모드 컨트롤러를 키를 받는 하나(`ViewModeController(key)`)로 합친다. |
| A4 | D | 화면이 `Clipboard`를 직접 부른다(예약 ①, 멤버 화면). 사진 선택기·카메라·마이크가 이 선례를 따르면 화면이 플러그인에 묶인다. | `core/proxy/`에 프로바이더로 감싼다: `clipboardProvider`, `mediaPickerProvider`(앨범·카메라), `speechRecognizerProvider`. 테스트는 프로바이더 override. |
| A5 | D | presigned PUT에는 인증 헤더가 붙으면 안 되고 진행률 콜백이 필요한데 `ApiClient`에 둘 다 없다. | `core/proxy/upload_client.dart`: 민짜 Dio, `onSendProgress`, 재시도 없음(호출자가 결정). |
| A6 | D | URL을 `ImageProvider`로 바꾸는 자리가 없다. 서명 URL은 매번 바뀌어 캐시가 깨진다. | `core/proxy/media_image.dart`: `media_id`를 캐시 키로 쓰는 로더, 캐시 상한 500MB. 화면은 `AppPhotoTile(image: mediaImage(...))`만 부른다. |
| A7 | O | 홈 셸은 탭 하나 더하면 네 곳(`_items`, FAB `switch`, 머리 조건, `_TabBody`)을 고친다. | 탭을 `HomeTab(icon, label, body, fab?, showsHeader)` 목록 하나로 정의한다. 추가는 한 줄. |
| A8 | O | 라우터의 매장 범위 가드가 접두사 목록 하드코딩이라 새 경로를 잊으면 가드가 빠진다. | 기본을 "매장 범위"로 뒤집고 예외(계정·인증)만 열거한다. 테스트는 "모든 경로가 가드 또는 예외 목록 중 하나"를 확인한다. |
| A9 | D | 기능 폴더끼리 서로 import한다(visit↔customer, shop→visit). 백엔드의 허브-스포크 규칙이 앱에는 없다. | 규칙을 세운다. ① 메뉴·일정 설정 화면은 소유가 visit이므로 `features/visit/screens/settings/`로 옮긴다. ② 방향은 **visit → customer만 허용**(예약 ①이 고객 검색 화면을 재사용). ③ customer → visit(반려동물 상세의 [기록] 탭)은 백엔드의 "자리"처럼 `core/plugs/`에 위젯 빌더 프로바이더 자리를 두고 `main.dart`가 visit 구현을 꽂는다. ④ 쓰기 뒤 교차 무효화(`visit_commands`가 customer 프로바이더를 무효화)는 `core/proxy/`의 `ShopDataChanged` 신호(`SessionEndedSignal` 선례)로 바꾸고 customer 프로바이더가 구독한다. ⑤ `test/structure/feature_imports_test.dart`가 `lib/features` 파일의 import를 읽어 규칙 위반을 잡는다. |
| A10 | S | "오류 문구 + 다시 시도" 블록 21곳, `_SheetAction` 위젯이 두 파일에 중복, 검색창 데코가 두 곳에 복제. | `design/widgets/app_error_retry.dart`, `app_sheet_action.dart`, `app_search_field.dart`로 걷어낸다. |
| A11 | S | `visit_form.dart`(879줄)의 `State`가 프리필 경쟁·메뉴→소요 산출·프로바이더 합성·시간 칸 재조회를 다 쥔다. `day_screen`의 시간표 범위 계산이 위젯 안에 있다. | 폼 규칙을 `visit_form_controller.dart`(Notifier)로 빼 단위 테스트를 붙이고, 시간표 범위 계산은 `day_layout.dart`로 옮긴다. |
| A12 | I | `visit_form`이 `customerDetailProvider` 전체를 watch하지만 `pets`만 쓴다. | `.select((d) => d.pets)`. |
| A13 | L | 글래스 표면 두 구현이 반지름을 다르게 쓴다(하나는 `topLeft.x`만, 하나는 네 모서리). | 계약을 `double radius`로 좁힌다. 비대칭 반지름은 쓰지 않는다. |

④-0 앱에서 쓸 곳이 생길 때로 미룬 것(결정 기록 007 앱 절): A4의 `mediaPickerProvider`와 A6 이미지 로더, A9 ③ `core/plugs/`, `AfterComplete.record`, `visit_form.dart` 나누기는 ④-2에서, A4의 `speechRecognizerProvider`는 ④-3에서 한다. A9 ④ `ShopDataChanged`는 허용 방향이라 하지 않는다. 그 밖에 미룬 것은 없다. ④-0의 검증 기준: 백엔드 단위·통합·구조 계약 통과, 라우트 표 전후 동일, API JSON 전후 동일(통합 테스트가 보장), 앱 `flutter analyze` 0·테스트 전부 통과·골든 변경 없음(A10 위젯화로 픽셀이 달라지면 의도한 것만 갱신).

## 5. 백엔드 구조

### 5.1 스포크와 허브 포트

```
apps/media/                       # 새 스포크. 소유: media_objects
  domain/{entities,value_objects}/   # MediaObject, 렌디션 키 규칙, 한도
  app/ports/output/media_repository.py, object_storage_port.py
  app/use_cases/issue_upload_interactor.py, confirm_upload_interactor.py,
                media_library_interactor.py (MediaLibraryPort 구현, HTTP 없음), media_myself_interactor.py
  adapter/outbound/{orm,pg,mappers}/, adapter/outbound/boto3_object_storage_adapter.py
  adapter/inbound/api/v1/{issue_upload,confirm_upload,media_myself}_router.py
  dependencies/, tests/, CLAUDE.md
```

| 허브 포트 | 구현 | 소비 | 메서드 |
|---|---|---|---|
| `MediaLibraryPort`(새) | media | visit, customer | `claim(ctx, media_ids)` 준비됨·이 매장·미부착 확인 후 `attached_at` 기록(조건부 UPDATE, 개수 불일치면 `MediaNotReadyError`/`MediaAlreadyAttachedError`/`MediaNotFoundError`), `release(ctx, media_ids)` `attached_at` 해제, `read_urls(ctx, media_ids) -> dict[int, MediaUrls]` 원본·표시·썸네일 서명 URL + 종류·가로세로·길이, `discard(ctx, media_ids)` S3 삭제 뒤 행 삭제 — **커밋 뒤 백그라운드에서만** |
| `CustomerDirectoryPort`(확장) | customer | visit | `set_pet_weight(ctx, pet_id, weight_kg, at)` 추가 |
| `VisitLedgerPort`(확장) | visit | customer | `latest_covers(ctx, pet_ids) -> dict[int, int]` 가장 최근 완료 기록의 대표 `media_id` 추가. `clear_customer_memos`는 기록 메모도 비운다 |

자리는 관례대로 소비 스포크의 `dependencies/hub_ports.py`에 두고 `main.py`가 꽂는다. `tests/route_inspection.py`가 빈 자리를 잡는다.

### 5.2 잠금 순서

기록 쓰기는 방문 쓰기와 같다: `CustomerDirectoryPort.lock_family`(고객 행) → 방문 행 `FOR UPDATE` → 다시 읽어 상태 확인 → 기록 행 upsert. 미디어 `claim`·`release`는 방문 행 잠금 안에서 하는 조건부 UPDATE다(네트워크 없음). S3 HEAD(확인)·DELETE(폐기)는 잠금 밖·커밋 뒤에서만 부른다.

## 6. 데이터 모델 (3NF)

### 6.1 표

**`media_objects`** (media)

| 칸 | 형 | 뜻 |
|---|---|---|
| `id` | bigint PK | |
| `shop_id` | bigint, 색인 | tenancy ID, 외래 키 없음 |
| `kind` | text CHECK `photo`·`video` | |
| `status` | text CHECK `pending`·`ready` | |
| `object_key`, `display_key`, `thumb_key` | text, 각각 유일 | `shops/{shop_id}/media/{id}/original.{jpg\|mp4}`, `…/display.jpg`(사진만, 영상은 null), `…/thumb.jpg`(영상은 포스터) |
| `content_type` | text | `image/jpeg` 또는 `video/mp4` |
| `size_bytes` | bigint, null 가능 | 원본 크기. 확인 때 채움 |
| `width`, `height` | smallint | 앱 선언값 |
| `duration_seconds` | smallint, null 가능 | 영상만 |
| `uploaded_by_member_id` | bigint | |
| `attached_at` | timestamptz, null 가능 | 기록이 가져간 시각 |
| `created_at`, `ready_at` | timestamptz | CHECK `(status='ready') = (ready_at IS NOT NULL) = (size_bytes IS NOT NULL)` |

색인: `(shop_id, status, created_at)`(정리 스크립트), `(attached_at)` 부분 색인 `WHERE attached_at IS NULL`.

**`service_menus`** (visit) — `price` integer null 가능, CHECK ≥ 0 추가. null이면 가격 미정.

**`visit_records`** (visit)

| 칸 | 형 | 뜻 |
|---|---|---|
| `visit_id` | bigint PK, FK visits 삭제 시 함께 | |
| `weight_kg` | numeric(4,1), null 가능, CHECK > 0 | |
| `care_note` | varchar(1000), null 가능 | 공개. ⑤ 알림장에 실린다 |
| `internal_note` | varchar(1000), null 가능 | 비공개 |
| `payment_method` | text, null 가능, CHECK `card`·`cash`·`transfer` | |
| `total_amount` | integer, null 가능, CHECK ≥ 0 | 받은 돈. 원본 |
| `created_by_member_id`, `updated_by_member_id` | bigint | |
| `created_at`, `updated_at` | timestamptz | |
| `version` | integer NOT NULL, 기본 1, CHECK ≥ 1 | 기록을 바꿀 때마다(PUT·덧붙이기) 1씩 오른다. 전체 교체 PUT이 모르는 사이에 붙은 사진을 지우지 않게 한다(8절) |

**`visit_record_items`** — (`visit_id` FK visit_records 삭제 시 함께, `menu_id` FK service_menus) PK, `amount` integer NOT NULL CHECK ≥ 0.

**`visit_record_media`** — (`visit_id` FK visit_records 삭제 시 함께, `media_id` bigint) PK, `media_id` 유일(한 객체는 한 기록에만), `phase` text CHECK `before`·`after`, `sort_order` smallint. 색인 `(visit_id, phase, sort_order)`.

### 6.2 3NF 점검과 계산하는 것

- 1NF: 사진·항목은 배열이 아니라 행이다.
- 2NF: 복합 키 표 둘은 키 전체에만 종속하는 칸만 가진다.
- 3NF: `total_amount`는 항목 합에서 도출되는 값이 아니라 "실제 받은 돈"이라는 별개 사실이다(할인이 둘의 차이). 매장 사용량은 `size_bytes` 합으로 계산한다.
- 계산하는 것: **대표 사진**(후 사진 중 `sort_order` 첫 번째 → 없으면 전 사진 첫 번째 → 사진이 없으면 영상 포스터 → 없으면 null), "기록이 있다"(`visit_records` 행 존재), 항목 합(참고 표시), 매장 사용량, 반려동물 프로필 사진(가장 최근 완료 기록의 대표), 현재 몸무게 이력(원본은 `visit_records`, 현재 값은 `pets.weight_kg`).
- 예약 메뉴(`visit_menus`, 계획)와 실제 메뉴(`visit_record_items`, 실적)는 다른 사실이라 둘 다 둔다.

### 6.3 다른 스포크의 ID

`visit_record_media.media_id`와 `media_objects.shop_id`는 외래 키 없는 정수다. 정합성은 `claim`(매장·준비·미부착 확인)과 `discard`(연결을 지운 뒤에만)로 지킨다. 고아는 정리 스크립트가 회수한다(7.5절).

### 6.4 익명화와의 관계

`clear_customer_memos`가 `visits.memo`에 더해 `care_note`·`internal_note`도 비운다. 사진은 매장의 미용 기록이라 남긴다. 익명화한 고객의 방문은 기록 쓰기도 404 `CUSTOMER_NOT_FOUND`(006 규칙).

## 7. 업로드 흐름과 S3 규칙

### 7.1 3단계

1. **발급** `POST /media/uploads` `{kind, content_type, byte_size, width, height, duration_seconds?}` → `media_objects` 행(pending) + presigned PUT URL(원본·표시·썸네일, 사진은 셋, 영상은 원본·포스터 둘), 15분 유효. 발급은 계산만이라 DB 커밋 뒤 네트워크가 없다.
2. **PUT** 앱이 S3에 직접 올린다. 인증 헤더 없음.
3. **확인** `POST /media/{media_id}/confirm` → 서버가 객체마다 HEAD(존재·크기·content-type 대조) → `status='pending'` 조건부 UPDATE로 `ready`. 없으면 409 `MEDIA_NOT_UPLOADED`, 한도 초과면 객체를 지우고 422 `MEDIA_TOO_LARGE`. HEAD는 잠금 없이 한다.

### 7.2 앱이 만드는 파일

| | 사진 | 영상 |
|---|---|---|
| 원본 | 긴 변 3000px, 프로그레시브 JPEG 품질 85, **EXIF 제거**(GPS 포함), 방향은 픽셀에 적용 | 1080p H.264 MP4, 60초, 앱이 압축 |
| 표시용 | 긴 변 1080px, 프로그레시브 JPEG 품질 80 | 없음 |
| 썸네일 | 긴 변 400px, JPEG 품질 75 | 포스터 프레임 JPEG 400px |
| 한도 | 20MB | 200MB, 60초 |
| 받는 형식 | `image/jpeg`만(HEIC는 앱이 변환) | `video/mp4`만 |

가로·세로·길이는 앱 선언값을 저장한다(표시용). 서버는 디코딩하지 않는다.

### 7.3 읽기

- 서명 GET URL. **만료는 매장 시간대 "다음 날 04:00 + 24시간"으로 반올림**한다 — 같은 객체는 하루 동안 같은 URL이라 앱 캐시가 맞고 ⑤의 CDN 캐시도 맞는다. 유출 시 노출은 최대 48시간이다(12절 M10).
- 앱은 `media_id`를 캐시 키로 쓴다. 목록·달력·피드·미리보기는 썸네일, 상세 넘기기는 표시용, 크게 보기·원본 저장은 원본.

### 7.4 서버 구조와 설정

- `media/app/ports/output/object_storage_port.py`: `presign_put(key, content_type, expires)`, `presign_get(key, expires_at)`, `head(key) -> ObjectInfo | None`, `delete(keys)`. 어댑터는 `boto3`(동기)를 `asyncio.to_thread`로 감싼다. 스텁 어댑터는 단위 테스트용.
- `core/config.py` 상수: `MEDIA_S3_ENDPOINT`(서버가 닿는 주소, 개발 `http://minio:9000`), `MEDIA_S3_PUBLIC_ENDPOINT`(앱이 닿는 주소, 개발 `http://127.0.0.1:9010`, 운영은 S3 서울 리전), `MEDIA_S3_BUCKET`(`chagocnote-media`), `MEDIA_S3_REGION`, `MEDIA_S3_ACCESS_KEY`, `MEDIA_S3_SECRET_KEY`. presigned URL은 호스트가 서명에 들어가므로 공개 주소로 서명하고, HEAD·DELETE는 내부 주소로 한다. 비밀값은 `secret_manager`로만 읽는다.
- `scripts/ensure_media_bucket.py`: 버킷 생성 + 수명주기 규칙(`original.*`은 30일 뒤 Standard-IA, `original.mp4`는 90일 뒤 Glacier Instant Retrieval, `display.*`·`thumb.*`는 Standard 유지). MinIO의 ILM은 같은 규칙을 받되 계층 이동은 무시한다.

### 7.5 정리

- `scripts/purge_stale_media.py`: ① `pending` 24시간 초과 ② `ready`이면서 `attached_at IS NULL` 24시간 초과 → S3 삭제 뒤 행 삭제. 매장·객체마다 커밋한다(중간에 멈춰도 다시 돌리면 같은 결과).
- 기록에서 사진을 빼면 같은 트랜잭션에서 연결 행 삭제 + `release`, 커밋 뒤 백그라운드 `discard`. 실패하면 ②가 회수한다.

## 8. 동작 규칙

- **기록은 미용 중·완료 방문에만 쓴다.** 예약됨·취소·노쇼면 409 `VISIT_NO_RECORD_YET`. 판단은 기록 인터랙터가 잠금 뒤 다시 읽은 상태로 한다. 상태 클래스에 행동을 더하지 않는다(4.1 B6와 같은 이유).
- **PUT은 전체 교체다.** 항목·미디어 목록은 보낸 대로 바뀐다. 새로 든 미디어는 `claim`, 빠진 미디어는 `release` + 커밋 뒤 `discard`. 순서는 `sort_order`대로.
- **PUT은 버전을 맞춰야 한다.** 요청의 `version`이 잠금 뒤 다시 읽은 기록의 `version`과 다르면 409 `RECORD_VERSION_CONFLICT`(기록이 없을 때는 `version`을 보내지 않는다; 기록이 있는데 안 보내도 409). 그 사이 대기열이 붙인 사진을 PUT이 모르고 지우는 일을 막는다. 앱은 409면 다시 읽어 폼에 없는 새 사진만 더한 뒤 다시 보낸다(사용자가 고친 칸은 그대로).
- **덧붙이기**(`POST /visits/{visit_id}/record/media`)는 미디어 하나를 그 `phase`의 맨 뒤(`sort_order` = 그 칸의 최댓값 + 1)에 붙인다. 기록 행이 없으면 빈 기록을 만든다. 잠금·상태 규칙은 PUT과 같다(미용 중·완료만). 같은 `media_id`가 이미 이 기록에 있으면 아무것도 바꾸지 않고 200을 준다(대기열이 응답을 못 받고 다시 보내도 안전 — 멱등). 다른 기록에 붙어 있으면 409 `MEDIA_ALREADY_ATTACHED`. 한도(방문당 사진 30장·영상 3편)를 넘으면 422 `MEDIA_LIMIT_EXCEEDED`. 버전은 받지 않고 올린다.
- **돈 칸**(`total_amount`·`items`·`payment_method`)이 비어 있지 않으면 인터랙터가 `ctx.permissions`에 `sales:write`가 있는지 확인한다(없으면 403). 라우터 가드는 `record:write`.
- **몸무게 → 현재 몸무게.** 기록의 `weight_kg`를 저장할 때 그 방문이 그 아이의 가장 최근 방문(미용 중·완료, `starts_at` 기준)이면 같은 트랜잭션에서 `set_pet_weight`를 부른다. 판단은 고객 행 잠금 안에서 한다. 옛 기록을 고쳐도 현재 값은 안 바뀐다. 보호자만의 방문은 몸무게 칸이 없다(422).
- **되돌리기는 막지 않는다.** 기록은 방문의 것이라 남는다. 피드·달력 대표 사진·프로필 사진·⑧은 완료 방문만 센다.
- **"나중에 적고 완료"**는 기록 없이 완료 전이만 한다. 이미 올린 사진은 기록 행이 있으므로 남는다.
- **완료 후속 처리**(4.1 B4의 `completion_effects`): 최근 방문 갱신(기존), 몸무게 동기화(새). 전이·기록 슬라이스 둘 다 여기를 부른다.
- **삭제** `DELETE /visits/{visit_id}/record`: 행·항목·연결을 지우고 미디어를 `release` + 커밋 뒤 `discard`. 방문은 남는다.
- **프로필 사진**: customer가 `latest_covers`로 받은 `media_id`를 `read_urls`로 바꿔 붙인다. 목록은 페이지의 반려동물 ID를 한 번에 묻는다(N+1 없음).

## 9. API

모두 API 프로세스, 경로 앞부분 `/v1/shops/{shop_id}`, 오류 본문 `{code, message}`.

**media**

| 메서드·경로 | 권한 | 하는 일 |
|---|---|---|
| `POST /media/uploads` | `record:write` | 발급(7.1). 응답 `{media_id, puts: {original, display?, thumb}, expires_at}` |
| `POST /media/{media_id}/confirm` | `record:write` | 확인(7.1). 같은 매장 멤버면 발급자가 아니어도 됨 |
| `GET /media/myself` | 멤버 | 이 묶음의 엔드포인트·데이터·제약 |

**visit (추가)**

| 메서드·경로 | 권한 | 하는 일 |
|---|---|---|
| `PUT /visits/{visit_id}/record` | `record:write` (+돈 칸이면 `sales:write`) | `{version?, weight_kg?, care_note?, internal_note?, payment_method?, total_amount?, items: [{menu_id, amount}], media: [{media_id, phase, sort_order}]}` 전체 교체(`version`은 8절). 행이 없으면 만든다. 응답은 상세와 같은 `record` |
| `POST /visits/{visit_id}/record/media` | `record:write` | `{media_id, phase}` 덧붙이기(8절). 응답은 상세와 같은 `record` |
| `DELETE /visits/{visit_id}/record` | `record:write` | 기록 삭제. 없으면 404 `RECORD_NOT_FOUND` |
| `GET /visits/feed?cursor=&limit=&pet_id=` | 멤버 | 완료 방문을 `completed_at` 역순으로. 항목: `visit_id`, 아이·보호자 요약, `cover`(썸네일 URL, null 가능), `completed_at`, 메뉴 이름들, `care_note` 앞 80자, `media_count`. `pet_id`로 그 아이만. 커서는 `(completed_at, visit_id)` |

기존 응답에 더하는 것(사진은 **읽기 DTO에만** 붙인다 — `VisitView`는 건드리지 않는다):
- `GET /visits/{visit_id}` → `record`(전체: 몸무게·메모 둘·결제·총액·항목(메뉴 이름·금액)·미디어(종류·전/후·순서·원본·표시·썸네일 URL·가로세로·길이)) 또는 null, `cover`, `previous_visit.cover`.
- `GET /visits?date=` → 항목마다 `cover`·`has_record`.
- `GET /visits/calendar?month=` → 날마다 `cover`(그날 완료 방문 중 시작 순 첫 대표 사진), `covers`(미리보기 카드용 최대 4장).
- `GET /menus`·`POST /menus`·`PUT /menus/{id}` → `price`.

**customer (추가)**: `GET /customers`(반려동물 줄), `GET /customers/{id}`, `GET /pets/{id}` → `photo`(썸네일 URL, null 가능).

규칙과 오류 코드:
- 다른 매장의 미디어 ID는 404. 요청 본문의 메뉴는 매장 대조 → 422 `MENU_NOT_FOUND`(기존).
- media: `MEDIA_NOT_FOUND`(404), `MEDIA_NOT_UPLOADED`(409), `MEDIA_NOT_READY`(409), `MEDIA_ALREADY_ATTACHED`(409), `MEDIA_TOO_LARGE`(422), `MEDIA_TYPE_UNSUPPORTED`(422), `MEDIA_LIMIT_EXCEEDED`(422, 방문당 사진 30장·영상 3편).
- visit: `VISIT_NO_RECORD_YET`(409), `RECORD_NOT_FOUND`(404), `RECORD_VERSION_CONFLICT`(409), `RECORD_WEIGHT_WITHOUT_PET`(422), `RECORD_ITEM_DUPLICATE`(422).
- 입력 경계: `total_amount`·`amount` ≤ 100,000,000, `weight_kg` 0.1~999.9, `sort_order` 0~99, 메모 1000자, 미디어 목록 33개 이하, `phase`·`payment_method` Literal.

## 10. 앱

### 10.1 화면

1. **캘린더 탭** — 머리에 [달력 / 피드] 아이콘 토글(기기에 저장, A3의 컨트롤러). 달력 칸은 완료 방문이 있는 날에 대표 썸네일 + 우측 하단 흰 동그라미 마릿수, 사진 없는 완료 날은 회색 자리(지금과 같음). 미리보기 글래스 카드에 겹친 썸네일 최대 4장 + 이름.
2. **피드** — 완료 방문을 최신순으로 세로 스크롤. 카드마다 대표 사진 크게(둥근 사각형·흰 테두리), 그 위 글래스 이름 카드(이름·품종·몸무게), 아래에 날짜·메뉴·케어 메모 앞부분·사진 수. 사진 없는 완료 방문도 회색 자리로 나온다. 누르면 방문 상세. 커서로 이어 읽기. 불투명 `AppCard`, 글래스는 이름 카드에만.
3. **방문 상세** — 회색 자리가 기울어진 사진 넘기기로 바뀐다(전/후 칩, 페이저 `01 / 04`, 영상은 재생 아이콘). 미용 중·완료면 [사진 추가](카메라 / 앨범). "오늘의 케어" 블록: 실제 메뉴·시간·몸무게·케어 메모·총액·결제 수단, 내부 메모는 접힌 줄. [기록 수정]. 사진을 누르면 크게 보기.
4. **기록 화면**(완료 흐름과 [기록 수정]이 같은 폼) — 사진 줄(올린 것 + 추가, 전/후 토글, 길게 눌러 순서), 몸무게(현재 값 미리 채움), 실제 메뉴 칩(예약 메뉴 미리 선택, 정가 자동), 총액(항목 합 미리 채움, 고칠 수 있음), 결제 수단 세그먼트 [카드 / 현금 / 계좌], 케어 메모, 내부 메모, 메모 옆 마이크 버튼(④-3). 완료 흐름의 저장 버튼은 "완료하기": 기록 PUT → 완료 전이 → 기존 [다음 예약 잡기] 시트. 맨 아래 "나중에 적고 완료". [기록 수정]에서는 버튼이 "저장".
5. **크게 보기** — 전체 화면, 좌우 넘기기, 원본 저장(앨범), 전/후 바꾸기, 대표로(순서 맨 앞), 삭제. 바꾸기·삭제는 기록 PUT 한 번.
6. **설정 → 메뉴** — 가격 칸(사장에게만 보임, 기존 규칙).
7. **고객 탭** — 가족 카드·반려동물 상세의 회색 자리에 프로필 썸네일. 반려동물 상세 탭에 [기록] 추가(그 아이의 피드, `pet_id` 필터). A9의 자리 프로바이더로 꽂는다.

### 10.2 업로드 상태

업로드는 **기기에 저장되는 대기열**이다. 사진이 사라지지 않는 것이 이 앱의 첫째 약속이다.
- 사진을 고르거나 찍으면 바로 리사이즈·EXIF 제거·렌디션 셋을 만들어 앱 전용 폴더에 쓰고, 대기열 항목(방문 ID·전/후·파일 경로·단계)을 기기에 저장한다. 그다음 발급 → PUT 셋 → 확인 → **덧붙이기**(8절)까지 백그라운드로 간다. 기록 화면을 다 쓸 때쯤이면 사진은 이미 기록에 붙어 있다.
- 앱이 꺼지거나 인터넷이 끊겨도 다시 켜면 남은 단계부터 이어 간다. presigned URL이 만료됐거나(15분) 서버가 정리한 뒤면(24시간) 발급부터 다시 한다 — 로컬 파일이 원본이다. 실패하면 간격을 늘리며 스스로 다시 시도하고(1·2·4… 최대 5분), 인터넷이 돌아오면 바로 한 번 더 한다. 사진이 붙거나 사용자가 빼면 로컬 파일을 지운다.
- 타일에 진행 링. 몇 번 실패해도 타일은 "대기 중"으로 남고 [빼기]만 준다(오류 화면을 띄우지 않는다). **취소는 오류가 아니다**: 사용자가 빼서 취소된 업로드는 `ApiException`의 `CANCELLED` 코드로 구분하고 아무 문구도 띄우지 않는다.
- 업로드 중이어도 기록 저장·"완료하기"·"나중에 적고 완료"를 막지 않는다. 기록 PUT은 이미 붙은 사진 목록을 보내고, 남은 사진은 대기열이 덧붙이기로 붙인다. 폼이 모르는 사이 붙은 사진 때문에 PUT이 409 `RECORD_VERSION_CONFLICT`면 8절대로 다시 보낸다.
- 대기열은 로그인한 사용자·매장별이다. 로그아웃·탈퇴하면 대기열과 로컬 파일을 지운다.
- 업로드 전용 클라이언트(A5), 이미지 로더(A6), 플러그인 프로바이더(A4)를 쓴다. 화면은 플러그인을 모른다.

### 10.3 상태와 규칙

- 기능 폴더 `lib/features/visit/{screens,state,api}`에 더한다. 새 위젯은 `design/widgets`에: `AppPhotoStrip`(기울어진 넘기기), `AppPhotoPager`, `AppProgressRing`, `AppErrorRetry`·`AppSheetAction`·`AppSearchField`(A10).
- `record:write` 없으면 사진 추가·기록 수정을 숨기고, `sales:write` 없으면 돈 칸을 숨긴다(보안 경계는 서버 403).
- 기록 저장·전이 뒤 그날 목록·그 달 요약·피드·상세·고객 프로필을 다시 읽는다(낙관적 갱신 금지, ③ 규칙). 교차 무효화는 A9의 신호로.
- 오프라인·목록 캐시 없음(업로드 대기열만 기기에 저장한다, 10.2). 사진 캐시는 표시용이며 상한 500MB.
- 패키지 후보(계획 ④-2에서 버전·iOS 27 호환을 확인한 뒤 확정): 사진 선택 `image_picker`, 리사이즈·EXIF 제거 `flutter_image_compress`(또는 `image`), 캐시 `cached_network_image`(캐시 키 지정), 앨범 저장 `gal`, 영상 압축 `video_compress`, 재생 `video_player`, 음성 `speech_to_text`. 웹뷰 금지 규칙과 충돌하는 패키지는 쓰지 않는다.
- iOS 권한 문자열: 카메라, 사진 보관함(읽기·추가), 마이크, 음성 인식. 안드로이드: 카메라, 미디어 읽기, 마이크.

## 11. 영상과 말로 기록하기 (④-3)

- **영상**: 방문당 최대 3편, 60초, 1080p H.264 MP4, 200MB. 앱이 압축하고 포스터 프레임을 썸네일 자리에 올린다. 업로드는 사진과 같은 3단계, 단일 PUT. 실기기에서 실패율을 보고 멀티파트 여부를 정한다. 상세 넘기기에서 사진과 같은 줄에 재생 아이콘, 크게 보기에서 재생·원본 저장. 영상은 사진이 하나도 없을 때만 포스터가 대표다. 90일 뒤 Glacier Instant Retrieval로 내려가도 밀리초 접근이라 복원 절차가 없다.
- **말로 기록하기**: 기기 내장 음성 인식(iOS Speech, Android SpeechRecognizer)만 쓴다. 음성을 서버로 보내지 않는다. 마이크를 누르고 말하면 케어 메모·내부 메모의 커서 위치에 글이 들어가고, 사람이 고친 뒤 저장한다. 한국어 로케일 고정. 인식 실패·권한 거부는 문구로 안내하고 손 입력으로 이어진다. 시뮬레이터에 마이크가 없어 실기기에서 확인한다.
- LLM 분리(미용 내용·내부 메모·매출 자동 분리)는 ⑨ 이후, 외부 전송 전 마스킹 계층을 거친다.

## 12. 위협 점검표

계획서는 행마다 막는 코드와 테스트를 짝짓는다. 작업별 검토는 이 표를 기준으로 한다.

| # | 시나리오 | 막는 곳 |
|---|---|---|
| M1 | A매장 멤버가 B매장 미디어 ID를 기록에 붙인다 | `claim`이 `shop_id` 조건부 UPDATE, 개수 불일치 → 404 |
| M2 | presigned URL로 다른 키에 쓴다 | 서명에 키가 들어 있어 불가(S3 규칙) |
| M3 | 확인 안 한 객체를 붙인다 | `claim`은 `status='ready'`만 |
| M4 | 같은 객체를 두 기록에 붙인다 | `attached_at IS NULL` 조건부 UPDATE + `media_id` 유일 |
| M5 | 한도 넘는 파일을 PUT한다 | 확인 때 HEAD 크기 검사, 초과면 객체 삭제 + 422 |
| M6 | 발급만 하고 안 올린다·앱이 죽는다 | 24시간 뒤 정리 스크립트 |
| M7 | 기록 저장과 되돌리기·익명화·무지개다리가 겹친다 | 고객 행 → 방문 행 잠금, 잠근 뒤 상태 재확인 |
| M8 | `sales:write` 없는 멤버가 돈 칸을 보낸다 | 인터랙터 403 |
| M9 | 내보내진 멤버가 쥔 토큰으로 업로드한다 | 매장 접근 확인이 매 요청 DB 조회(기존) |
| M10 | 읽기 URL이 유출된다 | 서명 URL. 만료 하루 반올림으로 최대 48시간 유효 — 캐시 적중과 맞바꾼 것 |
| M11 | 사진 EXIF의 GPS가 남는다 | 앱이 제거. 서버는 디코딩하지 않으므로 ⑤ 공개 전 서버 검증 재검토 |
| M12 | 입력 경계 — 금액·몸무게·순서·목록 길이·항목 중복·시간대 없는 시각 | 9절 경계 → 422. 계획 점검표에 "파이썬/DB 범위 끝 입력" 행(006 교훈) |
| M13 | 확인 요청이 동시에 두 번 온다 | `status='pending'` 조건부 UPDATE, 둘째는 200(이미 준비) |
| M14 | 옛 방문의 기록 편집이 현재 몸무게를 덮는다 | "그 아이의 가장 최근 방문일 때만" 판단을 고객 행 잠금 안에서 |
| M15 | S3 삭제 실패로 고아 객체가 남는다 | 커밋 뒤 백그라운드, 실패해도 행이 남아 정리 스크립트가 회수 |
| M16 | 익명화한 고객의 기록 메모에 개인정보가 남는다 | `clear_customer_memos`가 기록 메모도 비운다 |
| M17 | 기록 삭제와 크게 보기·저장이 겹친다 | 저장 쪽 404. 무해 |
| M18 | 업로드 중인 앱을 죽이고 다시 연다 | 기기에 저장된 대기열이 남은 단계부터 이어 간다(10.2). URL 이 만료됐거나 서버가 정리했으면 발급부터 다시. 덧붙이기는 같은 미디어를 다시 보내도 한 번(멱등) |
| M19 | 폼이 기록을 읽은 뒤 대기열이 사진을 덧붙이고, 폼이 전체 교체로 저장해 그 사진을 지운다 | 기록 버전 — PUT 이 읽은 버전과 다르면 409 `RECORD_VERSION_CONFLICT`, 잠근 뒤 다시 읽은 버전으로 판정(8절) |

## 13. 테스트와 검증

- **④-0**: 백엔드 단위·통합·구조 계약 전부 통과, 라우트 표 전후 동일, API JSON 전후 동일(통합 테스트가 보장). 앱 `flutter analyze` 0, 테스트 전부 통과, 골든은 의도한 것만 갱신. 새 테스트: 도메인 상태 집합 = CHECK 목록 대조, 스텁 ABC 상속(인스턴스화), `feature_imports_test.dart`, 라우터 가드 전수.
- **백엔드 ④-1**
  - 도메인 단위: 대표 사진 규칙, 렌디션 키 규칙, 한도, 서명 만료 반올림, 상태 조건.
  - 인터랙터: 스텁 포트. `claim` 개수 불일치 셋, 돈 칸 403, 몸무게 동기화 조건(최근 방문일 때만), 전체 교체의 release·discard 목록, 버전 불일치 409, 덧붙이기(맨 뒤 순서·빈 기록 생성·같은 미디어 멱등·한도).
  - 통합(실제 Postgres + compose의 MinIO): 첫 테스트는 테넌트 격리(M1). 발급 → 실제 PUT → 확인 → 기록 PUT → 상세·하루·달력·피드 → 사진 빼기 → 정리 스크립트. 잠금(M7)은 "막힌 호출을 `create_task`로 쥐고 결과를 본다" + 잠금을 빼는 변이로 실패 확인(① 교훈). 동시 확인(M13), 익명화(M16).
  - 스키마 드리프트, 구조 계약(import-linter가 새 스포크를 자동 포함, media→다른 스포크 0건), 라우트 구조 검사, `scripts/check_media_flow.sh`(게이트웨이 경유, curl로 PUT).
- **앱 ④-2**
  - 컨트롤러·API 테스트(가짜 어댑터): 업로드 대기열 상태 전이(발급→PUT→확인→덧붙이기, 실패·재시도·빼기·취소는 조용히, 앱 재시작 뒤 이어 가기, URL 만료 뒤 재발급, 버전 충돌 뒤 다시 보내기), 기록 폼 규칙(미리 채움·총액·권한별 칸), 피드 커서.
  - 위젯·골든: 기록 화면, 사진 넘기기, 피드 카드, 달력 칸(대표 사진), 미리보기 카드, 크게 보기.
  - `flutter analyze` 0.
- **완료 기준**(시뮬레이터 + 실서버, 앨범 사진으로): 시작 → 전 사진 2장 → 완료 → 기록 화면(몸무게·메뉴·총액·결제·메모) → 완료하기 → 다음 예약 시트 → 상세 넘기기·크게 보기·원본 저장 → 대표 바꾸기·전/후 바꾸기·삭제 → 피드 → 달력 대표 사진·미리보기 → 반려동물 상세 프로필·[기록] 탭 → 직원 계정에서 돈 칸 → 되돌리기 뒤 기록 유지 → "나중에 적고 완료". 카메라·마이크·영상은 실기기.

## 14. 구현 계획 나누기

- **④-0 SOLID 정리** — 백엔드(B1~B8)와 앱(A1~A13) 두 계획. 서로 독립이라 병렬 가능. 기능 코드 없음. 검증은 13절 첫 줄.
- **④-1 백엔드** — 허브 오류·포트 확장 → media 스포크(표·마이그레이션·S3 포트·boto3 어댑터·발급·확인·`MediaLibraryPort` 구현) → 메뉴 가격 → 기록 저장소 포트·기록 PUT(버전)/덧붙이기/DELETE·`completion_effects` 몸무게 → 상세·하루·달력·피드 → customer 프로필 사진·`set_pet_weight`·익명화 → 스크립트 둘(버킷 준비·정리) → 통합·흐름 스크립트 → 규칙 문서(`media/CLAUDE.md`, `visit/CLAUDE.md`, `_docs/harness.md`) → 결정 기록 007.
- **④-2 앱** — 플러그인 프로바이더·이미지 로더·`CANCELLED` 코드 → 메뉴 가격 → 업로드 대기열(기기 저장·이어 가기·자동 재시도·덧붙이기) → 기록 화면·완료 흐름 → 상세 넘기기·크게 보기 → 피드 토글·피드 → 달력 대표 사진·미리보기 → 고객 탭 프로필·[기록] 탭 → 시뮬레이터 흐름 → 결정 기록 007에 더함.
- **오류 화면 다듬기**(④-2 뒤, 작은 계획) — 원인별 문구(인터넷 없음·서버·권한), 인터넷이 돌아오면 자동 다시 불러오기, 이미 받은 데이터는 그대로 두고 위에 얇은 띠, 스플래시 오류 안내, `AppErrorRetry` 21곳 문구 통일. ④-0에서 모양이 달라진 오류 상태 세 곳은 이때 함께 본다.
- **④-3 영상·음성** — 영상 압축·포스터·업로드·재생·저장, 음성 받아쓰기, 권한 문자열, 실기기 확인(카메라·마이크·영상·멀티파트 판단).

계획서 코드는 ③처럼 참조 작업 트리(`.superpowers/ref/`)에서 먼저 돌려 검증한 뒤 옮긴다. 작업별 검토는 계획서 코드를 검토 안 된 것으로 보고 12절을 기준으로 판단한다.

## 15. 비용 근거

서울 리전 근사값(계획 ④-1에서 AWS 요금표로 확정): S3 Standard 약 $0.025/GB·월, Standard-IA 약 $0.0138, Glacier Instant 약 $0.005, 인터넷 전송 약 $0.126/GB(월 100GB 무료), CloudFront 월 1TB 전송 영구 무료.

매장 하나가 월 120방문, 방문마다 사진 4장(원본 2MB + 표시 0.25MB + 썸네일 0.03MB), 영상 월 20편(40MB)이면 월 약 1.9GB 증가, 1년 뒤 누적 약 23GB. 1년 뒤 저장비는 계층화 없이 약 $0.6/월, 계층화로 약 $0.3/월. 앱 열람 전송 월 5GB는 S3 직접 약 $0.6, CloudFront 0원. **매장당 월 1천 원 미만**이다. 알림톡(매장당 월 3~5천 원)이 훨씬 크므로 미디어는 비용보다 "경쟁사보다 빠르다"와 개인정보(EXIF)가 우선이다. 최적화 항목(렌디션·EXIF·프로그레시브·URL 반올림·수명주기·캐시 상한)은 그래서 넣었고, WebP·중복 제거·CDN은 그래서 미뤘다.

## 16. 이후 서브 프로젝트로 넘기는 것

- **⑤ 알림장**: CloudFront 서명 URL, 공개 페이지용 URL 수명, 알림장 보낸 방문의 되돌리기 금지(`CompletedState.revert` override + `Visit` 필드), 서버 측 EXIF 검증, 케어 메모·사진의 공개 필드 선별.
- **⑥ 알림톡**: 해당 없음.
- **⑦ 보호자 회원**: 기록 피드의 보호자 쪽 읽기(같은 `read_urls`).
- **⑧ 매출 통계**: `total_amount`·`payment_method`·항목이 원본. 열람은 `sales:read`. 완료 방문만 센다.
- **⑨ RAG**: 음성 받아쓰기 → LLM 분리(마스킹 뒤), 케어 메모·내부 메모 임베딩.
- **정기권**: ⑤ 뒤, ⑥ 앞. 선불·횟수 차감이 기록의 항목·총액과 만나는 지점(차감 방문의 총액 0원 표기)을 그때 정한다.
- **규모가 커지면**: WebP 표시용, 해시 중복 제거, 멀티파트 업로드, 매장 용량 상한과 과금.
