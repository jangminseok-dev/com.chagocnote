# 네이티브 설정 — 키가 생기면 할 일

**지금은 적용하지 않는다.** 카카오/구글/애플 어느 쪽도 아직 실제 앱/서비스
등록을 하지 않았고(애플은 유료 개발자 멤버십도 필요하다), 진짜 키 없이는
검증할 수 없다. 이 문서는 키가 생겼을 때 무엇을, 어느 파일에, 왜 넣어야
하는지를 패키지 캐시의 실제 소스로 근거를 남겨 둔 것이다.

각 항목은 `~/.pub-cache/hosted/pub.dev/<패키지>/<경로>`를 인용한다 —
버전은 Task 14 기준(kakao 2.0.1, google_sign_in 7.2.0/이오에스 6.3.5/안드로이드
7.2.17, sign_in_with_apple 8.2.0)이다.

## 공통 — `--dart-define`

`lib/core/config/app_config.dart`(`AppConfig.fromEnvironment`)가 읽는 이름
그대로다. 값이 비어 있으면(카카오/구글) 또는 `false`면(애플) 그 공급자는
`socialSignInsProvider` 목록에서 아예 빠진다.

| 이름 | 의미 |
|---|---|
| `KAKAO_NATIVE_APP_KEY` | 카카오 개발자 콘솔의 네이티브 앱 키 |
| `GOOGLE_IOS_CLIENT_ID` | iOS OAuth 클라이언트 ID (`GoogleService-Info.plist`의 `CLIENT_ID`) |
| `GOOGLE_SERVER_CLIENT_ID` | 백엔드가 id 토큰을 검증할 웹 OAuth 클라이언트 ID |
| `APPLE_SIGN_IN_ENABLED` | `true`/`false`. iOS에서만 실제로 버튼이 뜬다(안드로이드에서 애플은 웹 플로우라 이 브랜치에서 제공하지 않는다) |

예: `flutter run --dart-define=KAKAO_NATIVE_APP_KEY=xxxx --dart-define=GOOGLE_SERVER_CLIENT_ID=yyyy.apps.googleusercontent.com --dart-define=APPLE_SIGN_IN_ENABLED=true`

---

## 카카오 (`kakao_flutter_sdk_user` 2.0.1 / `kakao_flutter_sdk_common` 2.0.1)

패키지 자체 `README.md`(`~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_user-2.0.1/README.md`)는
설정 방법을 전부 외부 문서(developers.kakao.com)로만 링크해 두어서, 아래
항목은 README 대신 **플러그인의 실제 소스**를 근거로 삼았다(경로를 각각
적었다).

### iOS `Info.plist`

- `CFBundleURLTypes`에 `kakao{NATIVE_APP_KEY}` 스킴을 등록한다. 이 스킴은
  카카오계정 로그인의 콜백(redirect) 주소로 쓰인다 — 근거:
  `~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/lib/src/kakao_sdk.dart:68`
  (`_customScheme = customScheme ?? 'kakao$appKey';`)와 `:32`
  (`redirectUri => '$customScheme://oauth'`).
  ```xml
  <key>CFBundleURLTypes</key>
  <array>
    <dict>
      <key>CFBundleTypeRole</key>
      <string>Editor</string>
      <key>CFBundleURLSchemes</key>
      <array>
        <string>kakao{NATIVE_APP_KEY}</string>
      </array>
    </dict>
  </array>
  ```
- `LSApplicationQueriesSchemes`에 `kakaokompassauth`를 추가한다 — 카카오톡
  설치 여부를 `canOpenURL`로 확인할 때 쓰는 스킴이다. 근거:
  `~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/ios/kakao_flutter_sdk_common/Sources/kakao_flutter_sdk_common/CommonHostApiImpl.swift:23-27`
  (`isKakaoTalkAvailable`가 기본값 `"kakaokompassauth://authorize"`로
  `UIApplication.shared.canOpenURL`을 부른다). `LSApplicationQueriesSchemes`에
  없는 스킴은 iOS 9+에서 `canOpenURL`이 항상 false를 돌려주므로, `isKakaoTalkInstalled()`가
  카카오톡이 있어도 없다고 오판한다.
  ```xml
  <key>LSApplicationQueriesSchemes</key>
  <array>
    <string>kakaokompassauth</string>
  </array>
  ```
  - **참고(정확히 확인한 것)**: `kakaolink` 스킴은 인바운드 딥링크 처리에서만
    쓰인다 — `~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/ios/kakao_flutter_sdk_common/Sources/kakao_flutter_sdk_common/KakaoFlutterSdkCommonPlugin.swift:52-58`의
    `handleIncomingDeepLinks`가 들어오는 URL의 `host == "kakaolink"`인지만
    본다 — 이건 앱이 "받는" URL이라 `LSApplicationQueriesSchemes`(앱이
    "여는" URL을 미리 선언하는 목록)에 넣을 필요가 없다. 로그인 전용
    (`kakao_flutter_sdk_user`)인 이 브랜치에서는 `kakaokompassauth` 하나면
    충분하다 — 카카오톡 공유/메시지 기능까지 붙이면 그때 다시 확인한다.

### 카카오톡 앱 실행 후 되돌아오는 경로 (Android)

`AuthCodeHandlerActivity`가 플러그인 자체 매니페스트(`exported="true"`)에는
있지만 인텐트 필터가 없다 — 근거:
`~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_auth-2.0.1/android/src/main/AndroidManifest.xml`.
앱의 `android/app/src/main/AndroidManifest.xml`의 `<application>` 안에
같은 액티비티를 스킴 딸린 인텐트 필터로 다시 선언해서(매니페스트 병합)
`kakao{NATIVE_APP_KEY}` 스킴의 콜백을 받게 해야 한다:
```xml
<activity
    android:name="com.kakao.sdk.flutter.auth.AuthCodeHandlerActivity"
    android:exported="true">
  <intent-filter>
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="kakao{NATIVE_APP_KEY}" android:host="oauth" />
  </intent-filter>
</activity>
```
(패키지 소스 자체에는 이 인텐트 필터 예시가 없다 — 카카오 개발자 문서의
표준 안내를 그대로 따른 것이니, 실제 키가 생기면 developers.kakao.com의
최신 안드로이드 가이드로 한 번 더 대조해야 한다.)

### `KakaoSdk.init`

`lib/main.dart`에 이미 `config.kakaoEnabled`로 감싼 초기화를 배선해
두었다(`KakaoSdk.init(nativeAppKey: config.kakaoNativeAppKey)`) — 근거:
`~/.pub-cache/hosted/pub.dev/kakao_flutter_sdk_common-2.0.1/lib/src/kakao_sdk.dart:50`
(`static Future<void> init({String? nativeAppKey, ...})`).

---

## 구글 (`google_sign_in` 7.2.0)

### iOS `Info.plist`

근거: `~/.pub-cache/hosted/pub.dev/google_sign_in_ios-6.3.5/README.md`
("iOS integration" 절, 그대로 인용).
```xml
<key>GIDClientID</key>
<string>{GOOGLE_IOS_CLIENT_ID}</string>

<!-- 백엔드 검증용 서버 클라이언트 ID -->
<key>GIDServerClientID</key>
<string>{GOOGLE_SERVER_CLIENT_ID}</string>

<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleTypeRole</key>
    <string>Editor</string>
    <key>CFBundleURLSchemes</key>
    <array>
      <!-- GoogleService-Info.plist 의 REVERSED_CLIENT_ID -->
      <string>com.googleusercontent.apps.XXXXXXXXX-yyyyyyyy</string>
    </array>
  </dict>
</array>
```
`GIDClientID`/`GIDServerClientID`는 우리 앱처럼 `GoogleSignIn.instance.initialize(clientId:, serverClientId:)`를
Dart 코드에서 직접 넘기면 생략해도 된다고 README가 명시한다(단, `CFBundleURLTypes`의
`REVERSED_CLIENT_ID`는 Info.plist에 그대로 필요하다 — 이건 코드로 대체할
수 없는 URL 스킴 등록이다).

### Android

매니페스트에 넣을 항목은 없다(구글 로그인은 Credential Manager를 쓰지,
카카오처럼 커스텀 스킴 액티비티를 등록하지 않는다) — 대신 콘솔 등록이
필요하다. 근거: `~/.pub-cache/hosted/pub.dev/google_sign_in_android-7.2.17/README.md`.
- Firebase 또는 Google Cloud Platform 콘솔에 앱의 **서명 SHA-1**을 등록한다
  (디버그·릴리스 키스토어 각각).
- `google-services.json`을 쓰지 않는다면 `serverClientId`(웹 OAuth 클라이언트
  ID)를 `GoogleSignIn.instance.initialize`에 직접 넘겨야 한다 — 우리
  `GoogleSignInAdapter`는 이미 `AppConfig.googleServerClientId`를 그렇게
  넘기고 있다.
- **README가 짚어 둔 트러블슈팅 gotcha**: SHA-1이나 `serverClientId`가
  잘못 설정되면, 사용자가 계정을 고른 **뒤에** `GoogleSignInExceptionCode.canceled`가
  올라올 수 있다 — 우리 어댑터는 이 코드를 "취소"로 보고 `null`을
  돌려주므로, 실제로는 설정 오류인데 조용히 로그인 화면에 남아 있는
  것처럼 보일 수 있다. 실기기에서 처음 연결할 때 이 gotcha를 염두에 둔다.

---

## 애플 (`sign_in_with_apple` 8.2.0)

이 브랜치는 iOS에서만 애플 로그인을 제공한다(`social_sign_ins.dart`가
`defaultTargetPlatform == TargetPlatform.iOS`로 막아 둔다) — 그래서
안드로이드/웹 설정은 여기 적지 않는다.

### 전제조건

- **유료 Apple Developer Program 멤버십이 필요하다** — 근거:
  `~/.pub-cache/hosted/pub.dev/sign_in_with_apple-8.2.0/README.md`
  ("Prerequisites" 절: "Sign in with Apple is one of the restricted
  services which is not available for free with just an Apple ID").
- App ID에 "Sign In with Apple" capability를 등록해야 한다(Apple Developer
  포털, App ID 설정).

### Xcode capability + entitlements

`Runner` 타깃 → Signing & Capabilities → "+ Capability" → "Sign in with
Apple"을 추가하면 Xcode가 entitlements 파일에 아래를 넣는다 — 근거(예시
파일 그대로): `~/.pub-cache/hosted/pub.dev/sign_in_with_apple-8.2.0/example/ios/Runner/Runner.entitlements`.
```xml
<key>com.apple.developer.applesignin</key>
<array>
  <string>Default</string>
</array>
```
README가 명시적으로 경고한다: 이 capability가 없으면 로그인이 "시각적
신호 없이" 실패한다(예외는 던져지지만 화면엔 아무것도 안 보일 수 있다) —
근거: 같은 README의 "Your App" 절.

### 서버 검증

`clientID`로 앱(App ID/Bundle ID)에서 받은 코드를 검증해야 한다 — 서비스
ID(Service ID)는 웹/안드로이드 플로우 전용이라 iOS 전용인 이 브랜치에는
필요 없다. 근거: 같은 README의 "Your App"(iOS) 절.

---

## 검증 방법 메모

키가 생기면:
1. 위 iOS 항목을 `ios/Runner/Info.plist` + Xcode capability로 넣는다.
2. `flutter build ios --simulator --debug`로 컴파일이 여전히 되는지 먼저
   확인한다(Task 1에서 이미 15.0으로 올린 `IPHONEOS_DEPLOYMENT_TARGET`
   기준으로는 통과했다).
3. 실기기(카카오톡 앱 전환은 시뮬레이터에서 확인 불가)에서 세 개 공급자를
   각각 로그인 → 취소 → 재로그인 순서로 눌러 보고, 이 문서의 취소 코드
   가정(카카오는 `PlatformException(code:'CANCELED')` 또는
   `KakaoAuthException(error: AuthErrorCause.accessDenied)`, 구글은
   `GoogleSignInException(code: GoogleSignInExceptionCode.canceled)`, 애플은
   `SignInWithAppleAuthorizationException(code: AuthorizationErrorCode.canceled)`)이
   실제 기기에서도 맞는지 재확인한다 — 지금은 플랫폼 채널이 없어 단위
   테스트로 확인할 수 없었던 부분이다.
