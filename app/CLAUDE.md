# CLAUDE.md — 차곡노트 앱 (Flutter)

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 앱에만 해당하는 규칙이다.

## 꼭 지킬 것

- **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
- 폴더는 `lib/core/{config,proxy,storage,router,error,time,plugs}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
- **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`의 `buildRoot`가 채운다(지금은 반려동물 상세의 [기록] 탭 `petRecordsPlugProvider` ← visit 의 `PetRecordsView`, 그 탭을 다시 읽는 `petRecordsRefreshPlugProvider` ← `petRecordsRefresher`). 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
- **매장 범위 화면**은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다. 매장 선택 전(account·auth 화면: 로그인·스플래시·초대·매장 선택·계정)은 세션 전체를 봐야 하므로 이 규칙 밖이다.
- 플러그인은 `lib/core/proxy/`의 프로바이더로만 부른다 — 클립보드 `clipboardProvider`, 사진 고르기·찍기 `mediaPickerProvider`, 렌디션(리사이즈·EXIF 제거) `photoRenditionMakerProvider`, 인터넷 복귀 신호 `networkWatcherProvider`, 업로드 폴더 `uploadsDirProvider`, 서명 URL 사진 보이기와 원본 받기 `mediaImagesProvider`, 앨범에 저장 `photoAlbumProvider`(마이크·음성은 ④-3). 화면은 `Clipboard`·`ImagePicker`·`Image.network`를 직접 부르지 않는다. 테스트는 프로바이더를 override 한다(`test/support/upload_fakes.dart`). 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 하고, 사용자가 취소한 업로드는 `ApiException`의 `CANCELLED`라 문구를 띄우지 않는다.
- **서버에서 읽는 화면 본문은 `core/error/async_body.dart`의 `AsyncBody`로 그린다**(`test/design/async_body_usage_test.dart`). 불러오는 중·처음 실패(원인 문구와 [다시 시도], 권한·없음은 뒤로 갈 수 있으면 [돌아가기])·받은 데이터 위 띠·인터넷 복귀 때 스스로 다시 불러오기·`onRefresh`의 당겨서 새로고침을 한 곳에서 한다. 화면은 `AppErrorRetry`의 가운데·inline 모양을 직접 만들지 않는다(한 줄 `AppErrorRetry.row`는 다음 쪽 실패 같은 좁은 자리에만). 오류 문구는 누른 일이면 `messageFor`, 화면을 불러오지 못했으면 `loadMessageFor`(원인은 `core/error/error_kind.dart`의 `kindOf`). 앱 문구는 해요체다(`test/design/copy_tone_test.dart`).
- **사진 올리기는 업로드 대기열(`features/visit/state/upload_queue.dart`)로만 한다.** 화면은 `uploadQueueProvider.notifier`의 `addPhotos`·`remove`·`retry`만 부르고, 다시 해도 안 되는 실패(`stopsUpload`)로 멈춘 항목은 스스로 다시 하지 않는다 — 사용자가 [다시 시도]하거나 [올리기 취소]한다. 대기 중인 사진은 `visitUploadsProvider(visitId)`로 본다. 대기열이 발급 → 올리기 셋 → 확인 → 덧붙이기를 하고 기기에 남긴다(설계 10.2). 기록 전체 교체(`saveRecord`)는 이미 붙은 사진만 보낸다 — 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 새 사진을 더해 한 번 더 보낸다(`record_screen.dart`).
- **사진을 보이는 순서는 대표 규칙이다**(`features/visit/state/photo_edits.dart`의 `galleryOrder` — 후 → 전 → 영상, 첫 장이 대표). 크게 보기의 전/후 바꾸기·대표로·삭제는 `applyPhotoEdit` + `recordInputOf`로 기록 전체 교체 한 번이고, 409 `RECORD_VERSION_CONFLICT`면 다시 읽어 같은 바꾸기를 한 번 더 보낸다.
- 글래스는 떠 있는 조작 계층에만 쓴다(`test/design/glass_boundary_test.dart`). 예외는 피드 카드의 이름 카드 하나(④ 설계 10.1 ②) — 실제 글래스는 비쳐 보이므로 그 위 글자는 잉크색으로 쓴다.
- 서버의 상태 문자열은 `fromJson`에서 enum(`VisitStatus`·`VisitAction`)으로 한 번만 바꾼다. 화면의 `switch`는 `_ =>` 폴백 없이 완전 열거한다 — 상태·행동을 더하면 컴파일러가 빠진 곳을 찾는다.
- 서버 응답의 필드명은 변환하지 않는다. 모델은 평범한 클래스에 `fromJson` 을 직접 쓴다. 코드 생성기를 도입하지 않는다.
- `liquid_glass_widgets` 는 `lib/design/bridge/` 안에서만 import 한다. 화면은 `lib/design/widgets` 만 쓴다.
- 토큰을 로그에 남기지 않는다. `print`·`debugPrint`·dio `LogInterceptor` 를 쓰지 않는다(`avoid_print` 는 오류다).
- 리프레시 토큰 재사용에는 유예가 없다. 갱신 요청은 동시에 하나만, 실패한 갱신은 자동으로 다시 보내지 않는다. `ProviderScope` 의 `retry` 는 꺼 둔다.
- Hiss Haus 는 첫 입점 매장 이름이다. 앱 이름은 "차곡노트"다.

## 명령어 (`app/` 에서)

    flutter analyze                     # 경고 0
    flutter test                        # 골든 포함
    flutter test --update-goldens       # 골든을 의도해서 바꿀 때만
    tool/run_dev.sh                     # 개발용 실행 (APP_ENV=dev, 게이트웨이 http://127.0.0.1:8080)
