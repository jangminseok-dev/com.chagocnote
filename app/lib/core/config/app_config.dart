/// 빌드 시점에 `--dart-define`으로 주입하는 앱 설정.
///
/// 비밀값이 아니라 클라이언트에 이미 공개되는 값(API 주소, 소셜 로그인의
/// 공개 클라이언트 id 등)만 담는다. 진짜 비밀(개인키 등)은 여기 두지 않는다.
class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    required this.appEnv,
    this.kakaoNativeAppKey = '',
    this.googleIosClientId = '',
    this.googleServerClientId = '',
    this.appleSignInEnabled = false,
  });

  /// `--dart-define`으로 넘어온 값을 읽는다. `APP_ENV`의 기본값이 `prod`인 것은
  /// 의도한 것이다 — 보안 게이트는 기본으로 닫혀 있어야 한다.
  factory AppConfig.fromEnvironment() => const AppConfig(
        apiBaseUrl: String.fromEnvironment(
          'API_BASE_URL',
          defaultValue: 'http://127.0.0.1:8080',
        ),
        appEnv: String.fromEnvironment('APP_ENV', defaultValue: 'prod'),
        kakaoNativeAppKey: String.fromEnvironment('KAKAO_NATIVE_APP_KEY'),
        googleIosClientId: String.fromEnvironment('GOOGLE_IOS_CLIENT_ID'),
        googleServerClientId: String.fromEnvironment(
          'GOOGLE_SERVER_CLIENT_ID',
        ),
        appleSignInEnabled: bool.fromEnvironment('APPLE_SIGN_IN_ENABLED'),
      );

  final String apiBaseUrl;
  final String appEnv;
  final String kakaoNativeAppKey;
  final String googleIosClientId;
  final String googleServerClientId;
  final bool appleSignInEnabled;

  bool get isDev => appEnv == 'dev';
  bool get kakaoEnabled => kakaoNativeAppKey.isNotEmpty;
  bool get googleEnabled => googleServerClientId.isNotEmpty;
}
