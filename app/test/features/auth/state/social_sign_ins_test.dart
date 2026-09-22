// 실제 SDK 어댑터는 플랫폼 채널 없이는 단위 테스트할 수 없다(Task 14 브리프).
// 여기서는 `socialSignInsProvider`가 설정 조합·플랫폼에 따라 올바른
// provider 목록을 구성하는지만 검증한다.
import 'package:chagocnote/core/config/app_config.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/features/auth/api/apple_sign_in.dart';
import 'package:chagocnote/features/auth/api/google_sign_in_adapter.dart';
import 'package:chagocnote/features/auth/api/kakao_sign_in.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _empty = AppConfig(apiBaseUrl: '', appEnv: 'dev');
const _kakaoOnly = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  kakaoNativeAppKey: 'kakao-key',
);
const _googleOnly = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  googleServerClientId: 'server-client-id',
);
const _appleOnly = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  appleSignInEnabled: true,
);
const _all = AppConfig(
  apiBaseUrl: '',
  appEnv: 'dev',
  kakaoNativeAppKey: 'kakao-key',
  googleServerClientId: 'server-client-id',
  appleSignInEnabled: true,
);

List<String> _providersOf(ProviderContainer container) =>
    container.read(socialSignInsProvider).map((s) => s.provider).toList();

void main() {
  tearDown(() {
    debugDefaultTargetPlatformOverride = null;
  });

  test('빈 설정이면 목록이 비어 있다(개발용 로그인만 남는다)', () {
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_empty)],
    );
    addTearDown(container.dispose);

    expect(container.read(socialSignInsProvider), isEmpty);
  });

  test('kakaoEnabled 면 카카오 어댑터가 포함된다', () {
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_kakaoOnly)],
    );
    addTearDown(container.dispose);

    final signIns = container.read(socialSignInsProvider);
    expect(signIns, hasLength(1));
    expect(signIns.single, isA<KakaoSignIn>());
  });

  test('googleEnabled 면 구글 어댑터가 포함된다', () {
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_googleOnly)],
    );
    addTearDown(container.dispose);

    final signIns = container.read(socialSignInsProvider);
    expect(signIns, hasLength(1));
    expect(signIns.single, isA<GoogleSignInAdapter>());
  });

  test('appleSignInEnabled 여도 안드로이드에서는 제공하지 않는다', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.android;
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_appleOnly)],
    );
    addTearDown(container.dispose);

    expect(container.read(socialSignInsProvider), isEmpty);
  });

  test('appleSignInEnabled 고 iOS 면 애플 어댑터가 포함된다', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_appleOnly)],
    );
    addTearDown(container.dispose);

    final signIns = container.read(socialSignInsProvider);
    expect(signIns, hasLength(1));
    expect(signIns.single, isA<AppleSignIn>());
  });

  test('전부 켜져 있고 iOS 면 카카오·구글·애플 순서로 셋 다 포함된다', () {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;
    final container = ProviderContainer.test(
      overrides: [appConfigProvider.overrideWithValue(_all)],
    );
    addTearDown(container.dispose);

    expect(_providersOf(container), ['kakao', 'google', 'apple']);
  });
}
