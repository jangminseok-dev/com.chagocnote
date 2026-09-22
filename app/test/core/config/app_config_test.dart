import 'package:chagocnote/core/config/app_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('아무 값도 주지 않으면 닫힌 쪽이 기본값이다', () {
    final config = AppConfig.fromEnvironment();
    expect(config.apiBaseUrl, 'http://127.0.0.1:8080');
    expect(config.appEnv, 'prod');
    expect(config.isDev, isFalse);
    expect([config.kakaoEnabled, config.googleEnabled, config.appleSignInEnabled], [false, false, false]);
  });

  test('dev 환경과 키가 있으면 해당 로그인 수단이 켜진다', () {
    const config = AppConfig(
      apiBaseUrl: 'http://10.0.2.2:8080',
      appEnv: 'dev',
      kakaoNativeAppKey: 'k',
      googleServerClientId: 'g',
      appleSignInEnabled: true,
    );
    expect(config.isDev, isTrue);
    expect([config.kakaoEnabled, config.googleEnabled, config.appleSignInEnabled], [true, true, true]);
  });
}
