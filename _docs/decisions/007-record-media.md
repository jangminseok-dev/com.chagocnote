# 007 — 미용 기록·미디어(④)에서 내린 결정

설계: `docs/superpowers/specs/2026-09-24-record-media-design.md`. 이 기록은 계획마다 절을 더한다.

## ④-0 SOLID 정리(백엔드)에서 정한 것

2026-09-24 감사(설계 4.1절 B1~B10)를 기능 코드 없이 먼저 적용했다. 검증 기준은 "기존 단위·통합·구조 계약이 전후로 통과하고 라우트 표가 같다"였고, 그대로 지켰다(단위 727 → 766, 통합 262 → 260 — 재인증 테스트 8개가 auth 로 옮겨 6개가 되고 도메인 단위 4개가 생겼다, 계약 6종, 라우트 표 동일).

### 설계와 다르게 간 것

- **찾기·잠금 포트 이름과 범위.** 설계 B1 은 `get_many`·`lock` 둘만 가진 `VisitLockRepository`를 말했다. 실제로는 `get`도 같은 축(ID 로 찾기)이고 상세·초안 조회가 `get`만 쓰므로, 셋을 가진 `VisitLookupRepository`로 두고 `VisitWriteRepository`가 이를 상속한다. 조회 유스케이스가 쓰기 포트를 받지 않게 하는 것이 목적이었고 그 목적은 지켰다(`apps/visit/tests/app/test_visit_port_segregation.py`가 쓰기 포트를 받는 유스케이스를 넷으로 고정한다).
- **허브 오류는 포트 셋.** 설계 B2 는 `CustomerDirectoryPort`와 "기존 포트 둘"을 말했지만, 감사에서 같은 누수가 `ShopAccessPort`(tenancy 오류가 core 로)와 `MembershipLifecyclePort`(tenancy 오류가 auth 로)에도 있었다. 셋 다 허브 오류로 바꿨다. 탈퇴 오류 둘(`OWNERSHIP_TRANSFER_REQUIRED`·`SHOP_CLOSE_CONFIRM_REQUIRED`)은 tenancy 도메인에서 지우고 허브로 옮겼다(그 유스케이스만 던졌다). 매장 접근 거절 셋은 tenancy 가 자기 라우터에서도 쓰므로 tenancy 오류는 남기고, 포트 구현만 허브 오류를 던진다.
- **허브 오류의 HTTP 상태는 `core/hub_errors.py` 한 곳.** 설계는 소비 스포크의 `error_map.py`에 매핑하라고 했다. core 자신이 `ShopAccessPort`를 소비하고, 같은 오류가 두 프로세스에서 같은 상태로 나가야 하므로 맵을 core 에 두고 `install_error_handlers`가 자동으로 등록한다. `tests/test_hub_errors.py`가 HubPortError 의 모든 하위 클래스가 맵에 있고 두 진입점에 핸들러가 있는지 확인한다.
- **재인증 가드의 위치(설계 B8 의 두 갈래).** 연결·해제·탈퇴 라우터는 모두 인증 프로세스에 있었다. 그래서 자리 없이 `auth/dependencies/recent_login_guard.py`로 옮기고, 창(300초)·시계 차 허용폭은 `auth/domain/services/recent_login.py`가 정한다. core 는 `get_access_claims`(토큰 검증 + 계정 상태)만 남았고 `get_current_user_id`의 서명은 그대로다.
- **스텁 ABC 상속은 공용 스텁만.** 테스트 파일 안의 부분 스텁(`_Stub*`)은 그 테스트가 부르는 메서드만 가지므로 상속하지 않는다(하네스 문서에 적었다).

### 계획서 코드와 실행이 다르지 않았던 것

작업 8개 모두 참조 작업 트리에서 먼저 돌려 검증한 코드다. 실행 중 작업 5 의 검토가 하나를 더했다 — `apps/visit/tests/app/test_day_counts_view.py`(하루 집계 칸 집합이 상태 표와 같은지; 상태를 더하고 칸을 잊으면 걸린다). 참조 브랜치 `ref/record-4-0-be`와 다른 파일은 이것뿐이다. 상태 집합의 단일 원천은 `domain/state/visit_status.py` 표이고, 상태 클래스(`visit_state.py`)·`ACTIVE_STATUSES`·`COUNTED_STATUSES`·ORM CHECK·부분 색인·`DayCountsView.of`가 거기서 파생한다. ORM 문자열은 마이그레이션 0006 과 글자까지 같아 스키마 드리프트가 없다.

### 남는 것 — 알고 미룬다

- `transition_visits`가 잠그기 전에 `get_many`를 한 번 더 읽는다(되돌리기가 아니어도). `lock_visits`도 같은 것을 읽으므로 방문당 조회 하나가 늘었다. 조회 결과를 `lock_visits`에 넘기는 인자를 두면 없앨 수 있으나 잠금 순서 서비스의 서명을 늘리는 값어치가 없다고 봤다.
- 행동 축의 스키마 `Literal`(`transition_visits_schema.py`)은 API 계약이라 남긴다. 행동을 더하면 `ACTIONS`·바탕 메서드·스키마 셋을 고친다.
- 상태를 더하면 여전히 새 마이그레이션을 손으로 써야 한다(CHECK·부분 색인). `test_schema_drift`는 이를 잡지 못하므로(compare_metadata 는 CHECK·부분 색인 WHERE 를 비교하지 않는다 — 최종 검토가 확인) `tests/integration/test_visit_status_schema.py`가 실제 DB 를 표와 대조한다.

### 최종 검토(2026-09-24, 브랜치 전체)에서 고친 것

- `tests/test_schema_drift.py`의 `compare_metadata`는 CHECK·부분 색인의 WHERE 를 비교하지 않는다(개발 DB 에서 확인). 설계 B5 가 요구한 "도메인 상태 집합 = CHECK 목록" 대조가 빠져 있어 `tests/integration/test_visit_status_schema.py`를 더했다 — 실제 DB 의 `pg_get_constraintdef`·`pg_get_expr`에서 상태 이름을 뽑아 표와 순서까지 대조한다. 거짓이던 문서 네 곳을 사실로 고쳤다.
- `completion_changed`를 `touches_completion`으로 바꿨다. 판정은 "전후 어느 쪽에든 완료 방문이 있는가"이고 둘 다 완료여도 참이다(후속 처리는 멱등). ④-1 의 기록 유스케이스가 이 함수를 부를 때 "최근 방문일 때만 몸무게 동기화" 같은 조건은 `apply_completion_effects` 안에서 따로 판정한다. 계획서(작업 4)의 코드 블록은 옛 이름 그대로다 — 계획서는 실행 기록이라 고치지 않았다.
- 탈퇴 인터랙터 테스트의 스텁이 자체 예외 대신 허브 오류 `WithdrawalOwnershipTransferRequiredError`를 던진다(설계 B2 "스텁도 같은 예외"). 오류 배선 통합 테스트의 docstring 이 "리포지토리 오류가 샐 수도 있다"고 하던 것을 사실("포트 구현은 도메인 오류를 내보내지 않는다; tenancy 맵 등록은 방어용")로 고쳤다.
- 미룬 것(최종 검토 판정): import 정렬 세 테스트 파일, `membership_lifecycle_port.py` 긴 docstring 줄, `test_포트끼리_메서드가_겹치지_않는다` docstring, `visit_orm.py`의 상태별 칸 CHECK 에 남은 `'canceled'`·`'completed'` 리터럴, `test_visit_status.py`의 비공개 `_STATES` import, `visit_board.COUNTED` 별칭, `RecentLogin(auth_time=…)`의 정적 타입 `int | None`. 기각한 것: 분리 구조 테스트의 사용 차원 검사(타입 힌트가 계약), 서비스 함수 둘의 포트 검사, `X | None` 힌트, `phone_digits` 재계산, 가드 테스트의 키 쌍 직접 생성(`now` 고정에 필요).

## ④-0 SOLID 정리(앱)에서 정한 것

2026-09-24 감사(설계 4.2절 A1~A13)를 기능 코드 없이 적용했다. 검증 기준은 "`flutter analyze` 0, 테스트 전부 통과, 골든은 의도한 것만 갱신"이었고 그대로 지켰다(테스트 502 → 542, 골든 변경 없음, 새 의존성 없음).

### 설계와 다르게 간 것

- **완료 후속 행동은 둘.** 설계 A1 은 `AfterComplete { none, nextReservation, record }`를 말했다. `record`(기록 화면으로)는 기록 화면이 생기는 ④-2 의 것이라 지금은 `AfterNothing`·`AfterNextReservation(draft)` 둘만 두고 sealed 로 닫았다. ④-2 가 셋째를 더하면 `sendVisitAction`의 `switch`가 빠진 분기를 컴파일 오류로 알린다. 모르는 상태 문자열은 `VisitStatus.unknown`으로 받고 시간표에서는 자리를 차지한다(`occupiesTime`) — 새 상태가 서버에 먼저 들어와도 화면이 방문을 숨기지 않게.
- **`PrefsStore`에 `remove(key)`는 없다.** 설계 A3 이 말한 `remove`를 쓰는 곳이 없어 넣지 않았다. 대신 `clear()`는 "로그아웃 때 지우는 것"(마지막 매장)만 지우고 보기 방식은 남긴다 — 전에도 그랬다. 키는 `PrefsKeys`에 모아 두고, 컨트롤러는 `ViewModeController<T extends Enum>(key, values, fallback)` 하나다. [달력/피드] 토글(④-2)은 키 하나와 프로바이더 한 줄이다.
- **플러그인 프로바이더는 클립보드만.** 설계 A4 의 `mediaPickerProvider`·`speechRecognizerProvider`는 그 패키지가 들어오는 ④-2·④-3 에서 같은 모양(`core/proxy/<이름>.dart` 의 추상 + 실제 구현 + 프로바이더, 테스트는 `FakeX`로 override)으로 더한다. 지금 넣으면 아무도 부르지 않는 코드가 된다.
- **이미지 로더(A6)는 ④-2 로.** `media_id`를 캐시 키로 쓰는 로더는 이미지 캐시 패키지가 필요하고 부르는 화면도 ④-2 에 있다. 새 의존성 없음이 ④-0 의 제약이라 미뤘다.
- **`UploadClient`는 송신 타임아웃을 두지 않는다.** dio 의 `sendTimeout`은 바이트 전체에 걸려 큰 영상이 느린 망에서 끊긴다. 연결 10초·응답 30초만 제한한다. 오류는 `ApiException`으로 바꿔 던진다(저장소의 XML 오류 바디는 `HTTP_ERROR` + 상태 코드가 된다).
- **홈 탭 목록은 비공개 `_HomeTab`.** 설계 A7 의 `HomeTab`을 밖으로 내보낼 이유가 없어 `home_shell.dart` 안에 뒀다. 탭 추가는 목록에 한 줄이다.
- **라우터 가드는 목록이 아니라 규칙 하나다.** 설계 A8 은 "기본을 매장 범위로 뒤집고 예외만 열거"였다. 옛 `_isShopScoped`(접두사 목록) 분기는 매장이 하나면 세션이 자동으로 고르므로 닿을 수 없는 코드였다(변이 검사에서 가드를 꺼도 테스트가 통과해 드러났다). 지웠다. "선택 없음"은 매장이 둘 이상일 때뿐이고 그때는 계정 경로(`accountRoutes` 둘) 밖 전부가 매장 선택으로 밀린다. 테스트는 라우터의 모든 `GoRoute`를 돌며 이를 확인한다 — 경로를 더하면 자동으로 검사되고, 계정 경로에 매장 범위 경로를 넣거나 규칙을 지우면 실패한다.
- **기능 폴더 규칙(A9)에서 ③·④는 지금 필요 없다.** `customer → visit` import 는 시각 도우미뿐이라 `core/time`으로 옮기니 사라졌다 — `core/plugs/` 자리는 반려동물 상세의 [기록] 탭이 생기는 ④-2 에서 만든다. `visit_commands`가 customer 프로바이더를 무효화하는 것은 허용 방향(`visit → customer`)이라 `ShopDataChanged` 신호로 바꾸지 않았다. 구조 테스트는 `test/structure/`가 아니라 기존 폴더 `test/design/feature_imports_test.dart`에 뒀다(구조 테스트는 그 폴더의 `glass_boundary_test.dart`가 선례). 메뉴·일정 설정 화면은 `visit/screens/settings/`로 옮겼고, 오늘 날짜는 `core/time/today_provider.dart`, `runShopScoped`는 `auth/state/shop_scoped.dart`다.
- **폼 규칙은 Notifier 가 아니라 순수 객체 `VisitFormDraft`.** 설계 A11 은 `visit_form_controller.dart`(Notifier)를 말했다. 폼은 화면 인스턴스마다 하나이고 프로바이더로 공유할 이유가 없어, 위젯의 `State`가 쥐고 `setState`만 부르는 순수 객체로 뺐다. 반려동물 선택·"지난번처럼" 순서 번호·메뉴 → 소요·소요 단계·값 생성이 위젯 없이 단위 테스트된다. 시간표 범위는 `day_layout.timelineHours`.
- **세션 파생 프로바이더는 다섯.** 설계 A2 의 셋에 `shopCountProvider`(매장 선택 화면·설정)와 `currentUserIdProvider`(멤버 화면의 "나")를 더했다. 화면은 이 다섯만 `select`로 watch 한다(`app/CLAUDE.md`).

### 남는 것 — 알고 미룬다

- `AppErrorRetry`가 걷어낸 21곳 가운데 문구가 화면마다 조금씩 다른 것은 그대로 두었다(문구 통일은 디자인 판단).
- `visit_form.dart`는 여전히 500줄이 넘는다. 규칙은 빠졌지만 프로바이더 합성과 시간 칸 재조회는 위젯에 남아 있다. ④-2 가 기록 입력을 붙일 때 다시 본다.
- `GlassSurface`의 기본 반지름 16 은 `AppRadius` 토큰이 아니라 리터럴이다. 두 사용처(`AppGlassCard`·`AppGlassBar`)가 모두 토큰을 넘기므로 기본값을 쓰는 곳이 없다 — 그대로 두었다.

### 실행(2026-09-24)에서 더한 것

- 구조 테스트 보강(작업 3): `test/design/feature_imports_test.dart`의 둘째 테스트("아무도 home 을 import 하지 않는다")가 리터럴 `features/home/`만 보아 기능 폴더 안의 상대 import(`../../home/…`)를 놓쳤다. 첫 테스트처럼 `Uri.file(...).resolve`로 풀어 판정하고 `package:chagocnote/features/home/…`도 잡게 했으며, 정규식이 `import`뿐 아니라 `export`도 본다. 커밋 4590c65.
- 상태 switch 폴백 둘 추가 열거(작업 4): 계획서 diff 밖에 남아 있던 `day_screen.dart`(`_GroupCard`)·`visit_detail_screen.dart`(`_StatusButtons`)의 `_ =>`를 `completed || canceled || noShow || unknown`(전자는 `null ||` 포함)으로 완전 열거했다. `visit_labels.dart`의 `warningLabel`은 서버 경고 코드 문자열이라 대상이 아니다. 커밋 f1e9882.
- 오류 상태 세 곳의 여백·배치가 달라졌다(작업 7, 사용자 판단): `AppErrorRetry`로 걷어내면서 `customer_list_tab`의 더 불러오기 오류(세로 Column → `.row` 가로), `splash_screen`(여백 xl·간격 lg → `.inline` lg·md), `pet_detail` 보호자 탭(여백 없음·간격 sm → `.inline` lg·md·가운데 정렬)은 원래 블록과 픽셀이 같지 않다. 골든이 이 오류 상태를 찍지 않아 골든은 바뀌지 않았다. 위젯 하나에 변형 셋으로 걷어내는 것이 A10 의 목적이라 의도한 변경으로 받아들였다 — 원래 모양이 필요하면 그 세 곳만 되돌린다.
- 폼 위임의 작은 정정(작업 8): `VisitFormValue.startsAt`의 주석을 옛 문구("지금 시작이면 null")로 되돌렸고, `_prefill`은 `applyPrefill`이 false(옛 응답·손댄 뒤)면 `setState`를 부르지 않아 옛 동작과 정확히 같다. `timelineHours`의 "끝이 정각이면 올리지 않는다" 분기에 테스트를 더했다. 커밋 739c98e.
- `UploadClient`의 취소(작업 10, 남는 것): `cancelToken`으로 취소하면 `DioExceptionType.cancel`이 응답 없는 오류라 `ApiException.network`(NETWORK)로 보인다. ④-2 에서 업로드 UI 를 붙이기 전에 `CANCELLED` 코드를 두거나 호출자가 `cancelToken.isCancelled`를 먼저 보는 규칙을 정한다. `receiveTimeout` 30초를 확인하는 단언도 없다.
- 테스트 수: 계획서는 542 였으나 4번의 테스트 하나가 더해져 543 이다.
