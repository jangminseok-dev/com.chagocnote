# CLAUDE.md — 차곡노트 앱 (Flutter)

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 앱에만 해당하는 규칙이다.

## 꼭 지킬 것

- **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
- 폴더는 `lib/core/{config,proxy,storage,router,error,time,plugs}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
- **기능 폴더 사이의 import 는 방향이 하나다**(`test/design/feature_imports_test.dart`가 잡는다). `auth`는 공용(세션·`selectedShopIdProvider` 등 매장 선택 값·`runShopScoped`)이라 누구나 import 한다. `home`은 조립 껍데기라 다른 기능을 import 하고 아무도 `home`을 import 하지 않는다. `visit → customer`만 허용한다(예약 ①의 고객 검색 재사용). 그 밖은 금지 — 반대 방향이 필요하면 `lib/core/plugs/`에 자리를 두고 `app.dart`가 채운다. 여러 기능이 함께 쓰는 것(시각·날짜 도우미 `core/time`, 오늘 날짜)은 `lib/core/`에 둔다. 화면·상태는 소유하는 기능 폴더에 둔다(메뉴·일정 설정은 `visit/screens/settings/`).
- **매장 범위 화면**은 세션 전체(`sessionControllerProvider`)를 watch 하지 않는다. `auth/state/shop_selection.dart`의 파생 프로바이더(`selectedShopIdProvider`·`isOwnerProvider`·`shopNameProvider`·`shopCountProvider`·`currentUserIdProvider`)만 watch 한다. 매장 선택 전(account·auth 화면: 로그인·스플래시·초대·매장 선택·계정)은 세션 전체를 봐야 하므로 이 규칙 밖이다.
- 플러그인(클립보드, 앞으로의 사진 선택기·카메라·마이크)은 `lib/core/proxy/`의 프로바이더(`clipboardProvider` 등)로만 부른다. 화면은 `flutter/services`의 `Clipboard`를 직접 부르지 않는다. 테스트는 프로바이더를 override 한다. 서명 URL 업로드는 `core/proxy/upload_client.dart`(인증 헤더 없음·진행률·재시도 없음)로 한다.
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
