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

2026-09-24 감사(설계 4.2절 A1~A13)를 기능 코드 없이 적용했다. 검증 기준은 "`flutter analyze` 0, 테스트 전부 통과, 골든은 의도한 것만 갱신"이었고 그대로 지켰다(테스트 502 → 543, 골든 변경 없음, 새 의존성 없음).

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
- 테스트 수: 계획서는 542 였으나 작업 8(739c98e)의 정각 끝 테스트 하나가 더해져 543 이다.

## ④-1 백엔드에서 정한 것

새 스포크 media(발급·확인·`MediaLibraryPort`), visit 의 미용 기록(쓰기·덧붙이기·삭제·읽기 넓히기·피드), 메뉴 정가, customer 의 프로필 사진·익명화, 스크립트 셋(버킷 준비·정리·흐름 확인). 새 라우트 7개(media 셋, visit 넷 — 라우트 표의 나머지는 그대로), 마이그레이션 셋(0007 미디어 · 0008 메뉴 정가 · 0009 기록), 새 의존성 `boto3`. 단위 767 → 883, 통합 264 → 300, 구조 계약 6종(media 를 모든 계약에 더했다). 최종 검토 수정(I-1·m-1)이 단위·통합 테스트를 하나씩 더했다(계획서의 끝 수는 882·299).

### 설계와 다르게 간 것

- **빠진 미디어를 바로 지우지 않는다.** 설계 8절은 "빠진 미디어는 release + 커밋 뒤 discard"였다. 커밋 뒤 백그라운드 삭제는 요청 세션이 닫힌 뒤 자기 세션을 여는 장치가 따로 필요하고, 사진을 뺐다가 되돌리거나 업로드 대기열이 다시 보내는 여유도 없앤다. 그래서 `MediaLibraryPort`에 `discard`를 두지 않고, 놓인 미디어는 정리 스크립트가 하루 뒤 지운다(가져가지 않은 미디어와 같은 규칙). 하루는 놓인 시각부터 센다 — 놓기(`detach`)가 `ready_at`을 다시 찍는다(최종 검토 I-1 에서 고쳤다. 전에는 확인 시각부터라 확인한 지 하루 지난 사진은 빼자마자 다음 정리에서 지워졌다). 그래서 `ready_at`의 뜻은 "준비됐거나 마지막으로 놓인 시각"이다. 스키마·CHECK 는 그대로다. 앱에는 빼는 즉시 보이지 않는다. 운영에서는 정리 스크립트를 주기적으로 돌려야 한다.
- **객체 키는 렌디션이 앞이다**(`original/shops/{매장}/{ID}.jpg` 등, 설계 6.1 은 `shops/{매장}/media/{ID}/original.jpg`). S3 수명주기 규칙은 접두사로만 거르기 때문에, 원본만 싼 계층으로 옮기려면 원본이 한 접두사 아래 모여야 한다. 영상 원본은 `original-video/`로 따로 둔다.
- **읽기 서명은 직접 만든다.** 하루 동안 같은 URL(설계 7.3)은 서명 시각을 고정해야 하는데 botocore 는 늘 지금으로 찍는다. 서명 시각을 매장 시간대 가장 최근 04:00, 유효 48시간으로 두는 SigV4 쿼리 서명을 표준 라이브러리로 만들었고(`media/adapter/outbound/s3/sigv4_query.py`), 같은 시각의 botocore URL 과 글자까지 같은지 테스트한다. 경로 방식 주소를 쓴다.
- **설정 이름은 `S3_*`.** 설계는 `MEDIA_S3_*`였지만 개발 `.env`에 이미 `S3_ENDPOINT_URL`·`S3_ACCESS_KEY`·`S3_SECRET_KEY`·`S3_BUCKET`이 있어 그대로 쓰고 `S3_PUBLIC_ENDPOINT_URL`(기본 `http://127.0.0.1:9010`)·`S3_REGION`(기본 `us-east-1`)을 더했다. 운영은 S3 서울 리전 주소와 `ap-northeast-2`를 넣는다.
- **`claim`이 종류를 돌려주고, visit 이 연결 표에 적는다**(`visit_record_media.kind`). 대표 사진(후 → 전 → 영상 포스터)과 방문당 한도를 visit 표만으로 계산하려는 것이다. 종류는 바뀌지 않는 사실이라 옮겨 적어도 어긋나지 않는다. 허브 오류는 `MediaClaimNotFoundError`·`MediaClaimNotReadyError`·`MediaClaimAlreadyAttachedError`(media 도메인 오류와 이름을 나눴다).
- **`set_pet_weight(ctx, pet_id, weight_kg)`** — 설계의 `at` 인자는 쓸 곳이 없어 뺐다.
- **전이는 몸무게를 넘기지 않는다.** 설계 8절은 전이·기록이 둘 다 완료 후속 처리(몸무게 동기화 포함)를 부른다고 했지만, 전이는 최근 방문 갱신(`apply_completion_effects`)만, 기록 쓰기는 몸무게 동기화(`sync_pet_weight`)만 부른다. 기록은 시작한 방문에만 쓰므로 대개 쓰는 순간 동기화된다. 드물게 더 최근 방문을 되돌려 옛 방문이 '가장 최근'이 되어도 현재 몸무게는 따라가지 않는다.
- **몸무게는 바뀌었을 때만 현재 몸무게가 된다.** 기록 전체 교체는 처음 쓰거나 몸무게가 이전 기록과 다를 때만 `sync_pet_weight`를 부른다(가장 최근 시작한 방문일 때만이라는 규칙은 그대로). 같은 몸무게로 메모만 고쳐 저장하거나 대기열이 409 뒤 다시 보내도, 반려동물 화면에서 고친 현재 몸무게를 덮지 않는다(최종 검토 m-1).
- **기록 삭제는 `record:delete`(사장).** 설계 9절은 `record:write`였지만 권한 시드(0002)가 `record:delete`를 "기록 삭제"로 두고 사장에게만 줬다. 사진 한 장 빼기는 전체 교체(`record:write`)로 한다.
- **메뉴 정가의 CHECK 는 0~1억**(설계는 ≥0) — 기록 금액의 입력 경계와 맞췄다. `PUT /menus/{id}`의 `price`는 빠지면 가격 미정이다(④ 이전 앱이 그대로 불러도 된다).
- **프로필 사진은 조회 응답 셋에만.** 목록·고객 상세·반려동물 상세(GET)에 `photo`가 있고 쓰기 응답(`PetDetailSchema`·`CustomerDetailSchema`)에는 없다 — 쓰기 뒤 다시 읽는 규칙(③)이라 쓰기 인터랙터 일곱에 포트를 더하지 않았다. 프로필 사진은 "사진이 붙은 가장 최근 완료 방문의 대표"다(가장 최근 완료 기록에 사진이 없으면 그 전 것).

### 이 계획에서 새로 정한 것

- 기록 버전(`visit_records.version`)과 409 `RECORD_VERSION_CONFLICT`, 덧붙이기 API — 업로드 대기열 결정(2026-09-24)에 따라 설계 문서에 먼저 더했다.
- 덧붙이기는 그 칸을 순서대로 0부터 다시 매기고 맨 뒤에 붙인다 — 빼고 붙이기를 거듭해도 순서 상한(99)에 닿지 않는다. 같은 칸·같은 순서는 유일 색인(`uq_visit_record_media_order`)이 막는다.
- 보관한 메뉴도 기록 항목에 적을 수 있다(`MenuRepository.list_by_ids`) — 옛 기록을 고칠 때 막히지 않게.
- 돈 칸의 403 은 잠그기 전에 판정한다(권한은 방문과 상관없다).
- 돈 칸 없이 보낸 전체 교체는 돈 칸(총액·항목·결제 수단)을 지운다. 지금 시드(0002)에서 `record:write`를 가진 역할(사장·직원)은 모두 `sales:write`도 있어 돈 칸 없이 보낼 일이 없다. 역할 편집이 생기는 서브 프로젝트에서 "보내지 않은 돈 칸은 유지"로 바꿀지 다시 본다.
- 기록 여러 개는 `VisitRecordRepository.list_many`가 방문 수와 상관없이 질의 셋으로 읽는다(상세·하루·달력·피드·프로필 사진). 피드는 방문 리포지토리의 여섯째 축 `VisitFeedRepository`다(`test_visit_port_segregation.py`의 포트 목록에 더했다).
- 정리 스크립트는 객체마다 행을 pending 으로 되돌려 커밋한 뒤(그사이 기록이 가져가지 못한다) 저장소에서 지우고 행을 지운다. 중간에 멈추면 행이 오래된 pending 으로 남아 다음 실행이 잡는다.
- 통합 테스트는 MinIO 를 쓴다(compose `backend`가 `minio`에 기댄다, 픽스처 `media_storage`).

### 남는 것 — 알고 미룬다

- 확인(confirm)과 정리가 같은 오래된 pending 객체에 동시에 닿으면, 정리가 저장소에서 지운 뒤 확인이 ready 로 바꿀 수 있다(하루 넘게 확인하지 않은 객체를 그 순간 다시 확인하는 경우뿐). 앱의 대기열은 URL 이 만료되면 발급부터 다시 하므로 부딪힐 일이 드물다.
- 피드 질의(`shop_id, status='completed'` + `completed_at DESC, id DESC`)에 맞는 색인이 없다. 방문이 수만 건을 넘기 전에 부분 색인을 더한다.
- 운영 S3 설정(`S3_PUBLIC_ENDPOINT_URL`·`S3_REGION`)은 기본값이 있어 빠뜨려도 뜬다. 운영 배포 계획에서 필수 값을 확인하고 없으면 바로 멈추게 한다(fail-fast).
- 확인(confirm)은 `media.get`으로 트랜잭션을 연 채 HEAD 를 기다린다(행 잠금은 없다). 풀 고갈이 보이면 HEAD 를 먼저 하거나 `get` 뒤에 커밋한다.
- 정리 스크립트를 주기적으로 돌리는 장치(cron 등)는 운영 인프라 범위다.
- 서명 URL 은 경로 방식이다. 운영 S3 에서 가상 호스트 방식이 필요해지면 `sigv4_query`와 boto3 설정을 함께 바꾼다.
- 밤 22시 반 이후에는 `test_visit_flow_wiring.py::test_직원은_예약을_다루지만_일정과_메뉴는_못_바꾼다`가 실패한다(걷기 손님 기본 90분이 자정을 넘긴다). ③부터 있던 시각 의존 테스트이고 이 계획이 건드리지 않았다. 새 기록 테스트는 어제 11시 예약을 시작해 시각과 상관없이 돈다.

## ④-2a 앱(쓰기)에서 정한 것

사진을 고르면 기기에 남는 대기열이 렌디션을 만들어 올리고 기록에 붙이며, 기록 화면이 완료 흐름의 한가운데에 선다. ④-2 는 둘로 나눴다(설계 14절) — 보기(넘기기·크게 보기·피드·달력·고객 탭 사진)는 ④-2b 다.

### 설계와 다르게 간 것

- **프로그레시브 JPEG 가 아니다.** `flutter_image_compress`는 기본(baseline) JPEG 만 쓴다. 품질 85·80·75 와 긴 변 3000·1080·400 은 설계대로다.
- **렌디션은 두 단계.** 먼저 원래 크기로 방향을 픽셀에 적용하고 EXIF 를 지운 JPEG(품질 95)를 만들고, 그 가로·세로로 긴 변을 알아 셋을 만든 뒤 지운다 — 안드로이드 플러그인은 방향을 줄인 뒤에 적용해 원본에서 긴 변을 알 수 없다. 시뮬레이터에서 GPS·기기명·방향 6 이 든 JPEG 를 올려, 올라간 원본에 GPS·기기명이 없고 픽셀이 세워진 것(300×400)을 확인했다. 인코더가 쓰는 기본 칸(방향·해상도·색공간·픽셀 크기)은 남는다.
- **사진 캐시는 개수 상한 1500.** 캐시 패키지는 바이트로 제한하지 못한다. 썸네일·표시용이 대부분이라 설계 10.3 의 500MB 안쪽이다. 캐시 키는 `media_id`가 아니라 서명을 뺀 객체 주소다 — 달력·하루 목록의 대표 사진은 URL 만 오고, 객체 키가 사진·렌디션마다 하나라 같은 효과다.
- **완료 시트가 없어졌다.** [완료] → 기록 화면(완료 모드: [완료하기] = 기록 저장 → 묶음 완료, [나중에 적고 완료]) → 완료했으면 "미용을 마쳤어요" 시트([다음 예약 잡기]·[닫기], 미리보기). ④-0 의 `AfterComplete`는 쓸 곳이 없어 지웠다. 예약됨에서 바로 완료하면 기록 화면이 먼저 완료한 뒤 기록을 저장한다(기록은 미용 중·완료에만 쓴다). 기록 저장이 뒤에서 실패하면 다시 눌러 저장만 한다.
- **기록 화면에서 사진 순서를 끌어 바꾸지 않는다.** 붙은 사진은 눌러 전/후를 바꾸고 × 로 빼며, 올리는 중인 사진은 [빼기]만 있다. 순서는 ④-2b 크게 보기의 "대표로"가 맡는다. [사진 추가] 타일은 줄 맨 앞이다(사진이 많아도 보인다).
- **돈 칸을 숨기지 않는다.** 앱은 역할만 알고 시드상 사장·직원 모두 `sales:write`가 있다. 기록 삭제(`record:delete`)만 사장에게 보인다.

### 이 계획에서 새로 정한 것

- 대기열은 사용자의 것이다. 명시 로그아웃·탈퇴면 전부 지우고, 세션 만료는 남긴다(같은 사람이 다시 로그인하면 이어 간다). 다른 사람이 로그인하거나 이제 멤버가 아닌 매장의 항목은 지운다. 매장을 바꿔도 올리던 사진은 계속 올린다(항목이 매장을 안다).
- 모든 실패는 간격을 늘려(1·2·4…300초) 다시 한다 — 한도 초과 같은 영구 오류도 구분하지 않고 "대기 중" + [빼기]로 둔다. 그래서 한도는 고를 때 막는다 — [사진 추가]가 서버 기록에 붙은 사진과 대기열의 사진을 합쳐 30장이 차면 시트 없이 한도 문구만 보이고, 남은 자리만큼만 고르게 하고 받은 경로도 그만큼 자른다(카메라 포함). 확인된 사진을 덧붙일 때 `MEDIA_NOT_FOUND`(서버가 정리함)면 로컬 파일로 발급부터 다시 한다. 읽을 수 없는 사진은 조용히 뺀다.
- 기기에 남기는 것은 렌디션을 다 만든 항목뿐이고, 폴더는 항목 ID 다(iOS 는 앱 폴더의 절대 경로가 실행마다 바뀔 수 있다). 목록에 없는 폴더는 열 때 지운다.
- 대기열은 홈 셸이 깨운다 — 앱을 켜면 남은 사진을 바로 이어 올린다. 렌디션 셋은 동시에 올린다.
- 미리 채움은 기록이 비었을 때만(사진만 붙은 기록 포함): 몸무게는 반려동물의 현재 값, 메뉴는 예약 메뉴와 그 정가. 비운 금액은 0원으로 보내고, 금액을 하나도 적지 않았으면 총액은 비운다. 총액은 직접 고치기 전까지 항목 합을 따라간다.
- 기록 화면은 상세를 구독해, 대기열이 사진을 붙이면 열린 폼에도 바로 더한다(고친 칸은 그대로). 409 뒤 다시 보낼 때도 같은 구독이 새 사진을 더하고, 저장 쪽은 버전만 새로 받는다.
- 상세는 사진만 붙은 기록이면 케어 카드 없이 [기록 쓰기], 적은 기록이면 "오늘의 케어"와 [기록 수정]이다.
- 사진 캐시는 처음 사진을 보일 때 만든다 — 만들 때 캐시 폴더를 찾아 사진 없는 화면의 테스트가 플러그인을 건드리지 않게.
- [다음 예약 잡기]에서 초안을 다시 못 읽으면(두 번째 `nextDraft` 실패) 계획서 코드는 예외를 그대로 새 나가게 뒀다 — 이제 `messageFor(e)`를 스낵바로 보여주고 화면은 그대로 둔다(최종이 아닌 작업 7 검토에서 고침).

### 남는 것 — 알고 미룬다

- 앱이 떠 있을 때만 올린다(iOS 백그라운드 업로드 없음). 앱을 다시 켜면 이어 간다.
- 영구 오류(한도 초과·방문이 예약됨으로 되돌려짐)를 타일에서 따로 알리지 않는다 — 오류 화면 다듬기(④-2 뒤)에서 본다.
- 앱 재시작 뒤 이어 가기·URL 만료 뒤 재발급은 단위 테스트로만 확인했다(시뮬레이터 흐름에는 없다). 카메라는 실기기에서 본다(④-3 과 함께).
- 기록 화면의 금액 칸은 쉼표 없이 숫자만 보인다(상세·설정은 `35,000원`).
