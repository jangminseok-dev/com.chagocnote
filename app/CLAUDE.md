# CLAUDE.md — 차곡노트 앱 (Flutter)

저장소 루트의 `CLAUDE.md` 를 먼저 읽는다. 여기는 앱에만 해당하는 규칙이다.

## 꼭 지킬 것

- **웹뷰 방식 금지.** 웹뷰 패키지를 넣지 않고, 어떤 화면도 인앱 웹뷰로 만들지 않는다. 소셜 로그인도 네이티브 경로다(Apple 버튼은 iOS 만).
- 폴더는 `lib/core/{config,proxy,storage,router,error}` · `lib/design/{tokens,bridge,widgets}` · `lib/features/<기능>/{screens,state,api}` · `lib/l10n` 다. 기능 폴더(`lib/features/<기능>/`) 안은 `screens/` · `state/` · `api/` 세 층만 둔다. 리포지토리·유스케이스·엔티티 계층을 만들지 않는다.
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
