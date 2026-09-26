import 'package:chagocnote/core/config/app_config.dart';
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/screens/login_screen.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

const _prodConfig = AppConfig(apiBaseUrl: '', appEnv: 'prod');
const _devConfig = AppConfig(apiBaseUrl: '', appEnv: 'dev');

Me _me() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [],
    );

ProviderContainer _containerWith({
  required SessionGateway gateway,
  List<FakeSocialSignIn> signIns = const [],
  AppConfig config = _prodConfig,
}) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        socialSignInsProvider.overrideWithValue(signIns),
        appConfigProvider.overrideWithValue(config),
      ],
    );

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: MaterialApp(
      theme: appTheme(),
      home: const GlassBridge(
        factory: OpaqueSurfaceFactory(),
        child: LoginScreen(),
      ),
    ),
  );
}

void main() {
  testWidgets('appEnv 가 dev 가 아니면 개발용 로그인 버튼이 없다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway: gateway, config: _prodConfig);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.devSignIn), findsNothing);
  });

  testWidgets(
    'appEnv 가 dev 면 개발용 로그인 버튼이 있고, 이름이 비어 있으면 요청 없이 검증만 한다',
    (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = null;
      final container = _containerWith(gateway: gateway, config: _devConfig);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();

      expect(find.text(AppStrings.devSignIn), findsOneWidget);

      await tester.tap(find.text(AppStrings.devSignIn));
      await tester.pump();

      expect(find.text(AppStrings.devNameRequired), findsOneWidget);
      expect(gateway.receivedCredential, isNull);
    },
  );

  testWidgets('개발용 로그인은 이름을 dev 자격 증명으로 보낸다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = null
      ..meOnSignIn = _me();
    final container = _containerWith(gateway: gateway, config: _devConfig);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '민석');
    await tester.tap(find.text(AppStrings.devSignIn));
    await tester.pump();
    await tester.pump();

    expect(gateway.receivedCredential?.provider, 'dev');
    expect(gateway.receivedCredential?.token, '민석');
  });

  testWidgets('소셜 로그인을 취소하면(null) 요청이 나가지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final kakao = FakeSocialSignIn('kakao')..credentialToReturn = null;
    final container = _containerWith(gateway: gateway, signIns: [kakao]);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.continueWithKakao));
    await tester.pump();
    await tester.pump();

    expect(kakao.signInCallCount, 1);
    expect(gateway.receivedCredential, isNull);
  });

  testWidgets('소셜 로그인이 실패하면 문구를 보여주고 로그인 화면에 머무른다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    gateway.signInError = ApiException(
      statusCode: 400,
      code: 'PROVIDER_VERIFICATION_FAILED',
      message: '실패',
    );
    final kakao = FakeSocialSignIn('kakao')
      ..credentialToReturn = const SocialCredential(
        provider: 'kakao',
        token: 'tok',
      );
    final container = _containerWith(gateway: gateway, signIns: [kakao]);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.continueWithKakao));
    await tester.pump();
    await tester.pump();

    expect(find.text('로그인 정보를 확인하지 못했어요. 다시 시도해 주세요.'), findsOneWidget);
    expect(find.text(AppStrings.continueWithKakao), findsOneWidget);
  });

  testWidgets('세션이 만료되어 로그아웃되면 배너를 보여준다', (tester) async {
    // endSession()은 직전 상태가 SignedIn일 때만 sessionExpired를 true로
    // 만든다(Task 6 fix round 1 — 이미 SignedOut이면 무시). 그래서 이 화면이
    // 그 배너를 실제로 그리는지 보려면 로그인된 상태에서 세션을 끝내야 한다.
    final gateway = FakeSessionGateway()..meOnRestore = _me();
    final container = _containerWith(gateway: gateway);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.sessionExpiredBanner), findsNothing);

    container.read(sessionControllerProvider.notifier).endSession();
    await tester.pump();

    expect(find.text(AppStrings.sessionExpiredBanner), findsOneWidget);
  });
}
