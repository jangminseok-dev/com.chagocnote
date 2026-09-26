// 계정 화면을 실제 라우터 + 가짜 HTTP 어댑터로 검증한다. 매장 설정 화면
// 테스트와 같은 방식(FakeSessionGateway + apiClientProvider 를 가짜 어댑터로
// 문 실제 AccountApi/AccountController)을 쓴다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_card.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';
import '../../../support/fake_social_sign_in.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

String _labelFor(String provider) => switch (provider) {
      'kakao' => AppStrings.providerKakao,
      'google' => AppStrings.providerGoogle,
      'apple' => AppStrings.providerApple,
      'dev' => AppStrings.providerDev,
      _ => provider,
    };

/// [provider] 행의 해제 버튼. 화면에 로그인 수단마다 같은 "해제" 라벨이
/// 반복되므로, provider 라벨(카카오 등)을 담은 카드 안에서만 찾는다.
Finder _unlinkRowButton(String provider) => find.descendant(
      of: find.ancestor(
        of: find.text(_labelFor(provider)),
        matching: find.byType(AppCard),
      ),
      matching: find.text(AppStrings.unlink),
    );

/// 해제 확인 시트의 확정 버튼. 행의 해제 버튼과 라벨이 같아서(`filled`만
/// 다르다) 위젯 속성으로 구분한다.
final Finder _confirmUnlinkButton = find.byWidgetPredicate(
  (widget) => widget is AppButton && widget.label == AppStrings.unlink && widget.filled,
);

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle, {
  List<FakeSocialSignIn> signIns = const [],
}) {
  final adapter = FakeHttpClientAdapter(handle);
  // 리프레시 요청은 별도의 Dio 인스턴스로 보내야 한다 — 같은 인스턴스를
  // 재사용하면 리프레시 요청 자체가 401을 받았을 때 다시 리프레시를
  // 시도하는 재귀에 빠진다.
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  // `accountApiProvider`는 `apiClientProvider`와 별개로 `tokenStoreProvider`를
  // 직접 읽는다 — 오버라이드하지 않으면 실제 `SecureTokenStore`(플랫폼
  // 채널)로 떨어져 테스트에서 던진다.
  final tokenStore = _NoopTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      socialSignInsProvider.overrideWithValue(signIns),
      tokenStoreProvider.overrideWithValue(tokenStore),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: tokenStore,
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
  return (container: container, adapter: adapter);
}

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(
          routerConfig: router,
          theme: appTheme(),
          builder: (context, child) => GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: child!,
          ),
        );
      },
    ),
  );
}

void main() {
  testWidgets('매장이 없는 사용자도 계정 화면을 열 수 있고, 로그인 수단이 하나면 해제 버튼 대신 안내를 보여준다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsAccount), findsOneWidget);
    expect(find.text(AppStrings.unlink), findsNothing);
    expect(find.text(AppStrings.unlinkOnlyOneCaption), findsOneWidget);
  });

  testWidgets('해제 확인 시트를 취소하면 요청을 보내지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'kakao']);
    final setup = _setUp(
      gateway,
      (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(_unlinkRowButton('kakao'));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.unlinkConfirmMessage), findsOneWidget);

    await tester.tap(find.text(AppStrings.cancel));
    await tester.pumpAndSettle();

    expect(setup.adapter.requests, isEmpty);
  });

  testWidgets('해제를 확정하면 DELETE 요청을 보내고 목록을 갱신한다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(['apple', 'kakao'])
      ..meOnRefresh = _me(['apple']);
    final setup = _setUp(gateway, (options, body) {
      expect(options.method, 'DELETE');
      expect(options.path, '/v1/auth/identities/kakao');
      return const FakeResponse(
        statusCode: 200,
        data: {
          'identities': ['apple'],
          'access_token': 'new-access',
          'refresh_token': 'new-refresh',
          'token_type': 'Bearer',
          'expires_in': 3600,
        },
      );
    });
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(_unlinkRowButton('kakao'));
    await tester.pumpAndSettle();
    await tester.tap(_confirmUnlinkButton);
    await tester.pumpAndSettle();

    expect(setup.adapter.requests, hasLength(1));
    expect(gateway.refreshMeCallCount, 1);
    expect(find.text(AppStrings.unlinkOnlyOneCaption), findsOneWidget);
  });

  testWidgets(
    '탈퇴 화면을 열었다가 뒤로 와도 계정 화면의 재인증 프롬프트가 살아 있다(fix round 1)',
    (tester) async {
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(['apple', 'kakao'])
        ..meOnRefresh = _me(['apple']);
      final apple = FakeSocialSignIn('apple')
        ..credentialToReturn =
            const SocialCredential(provider: 'apple', token: 'tok');
      var unlinkCallCount = 0;
      final setup = _setUp(
        gateway,
        (options, body) {
          if (options.path == '/v1/auth/social') {
            return const FakeResponse(
              statusCode: 200,
              data: {
                'access_token': 'reauth-access',
                'refresh_token': 'reauth-refresh',
                'token_type': 'Bearer',
                'expires_in': 3600,
                'user_id': 1,
                'is_new_user': false,
              },
            );
          }
          if (options.path == '/v1/auth/identities/kakao' &&
              options.method == 'DELETE') {
            unlinkCallCount++;
            if (unlinkCallCount == 1) {
              return const FakeResponse(
                statusCode: 403,
                data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인'},
              );
            }
            return const FakeResponse(
              statusCode: 200,
              data: {
                'identities': ['apple'],
                'access_token': 'unlink-access',
                'refresh_token': 'unlink-refresh',
                'token_type': 'Bearer',
                'expires_in': 3600,
              },
            );
          }
          fail('예상하지 못한 요청: ${options.method} ${options.path}');
        },
        signIns: [apple],
      );
      addTearDown(setup.container.dispose);

      await tester.pumpWidget(_appWith(setup.container));
      await tester.pumpAndSettle();
      setup.container.read(routerProvider).go('/settings/account');
      await tester.pumpAndSettle();

      // 탈퇴 화면을 열었다가 뒤로 온다 — 계정 화면은 dispose되지 않는다
      // (go_router 가 push한 화면 밑에 그대로 남아 있다).
      await tester.tap(find.text(AppStrings.withdraw));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.settingsAccountWithdraw), findsOneWidget);

      setup.container.read(routerProvider).pop();
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.settingsAccount), findsOneWidget);

      await tester.tap(_unlinkRowButton('kakao'));
      await tester.pumpAndSettle();
      await tester.tap(_confirmUnlinkButton);
      // 재인증 시트를 기다리는 동안 계속 busy(스피너)라 pumpAndSettle이
      // 절대 안 멈춘다 — 정해진 만큼만 pump한다.
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pump(const Duration(milliseconds: 1000));

      // 탈퇴 화면이 dispose되며 프롬프트를 비워버렸다면(고치기 전 버그)
      // 여기서 시트가 뜨지 않고 REAUTH_REQUIRED 오류 문구만 보인다.
      expect(find.text(AppStrings.reauthPromptTitle), findsOneWidget);

      final sheetAppleButton = find.byWidgetPredicate(
        (widget) => widget is AppButton && widget.label == AppStrings.providerApple,
      );
      await tester.tap(sheetAppleButton);
      await tester.pump(const Duration(milliseconds: 50));
      await tester.pump(const Duration(milliseconds: 1000));

      expect(unlinkCallCount, 2);
      expect(gateway.refreshMeCallCount, 1);
    },
  );

  testWidgets('연결 요청이 IDENTITY_ALREADY_LINKED 를 받으면 문구를 보여준다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final kakao = FakeSocialSignIn('kakao')
      ..credentialToReturn = const SocialCredential(provider: 'kakao', token: 'tok');
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'IDENTITY_ALREADY_LINKED', 'message': '다른 계정'},
      ),
      signIns: [kakao],
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.providerKakao));
    await tester.pumpAndSettle();

    expect(
      find.text('다른 계정에 연결된 로그인 수단이에요. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.'),
      findsOneWidget,
    );
  });

  testWidgets('해제 확정이 LAST_IDENTITY 를 받으면 문구를 보여주고 목록은 그대로다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple', 'kakao']);
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'LAST_IDENTITY', 'message': '마지막 수단'},
      ),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(_unlinkRowButton('kakao'));
    await tester.pumpAndSettle();
    await tester.tap(_confirmUnlinkButton);
    await tester.pumpAndSettle();

    expect(find.text('마지막 로그인 수단은 해제할 수 없어요.'), findsOneWidget);
    expect(gateway.refreshMeCallCount, 0);
  });

  testWidgets('로그아웃하면 로그인 화면으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => fail('예상하지 못한 요청: ${options.path}'),
    );
    addTearDown(setup.container.dispose);

    await tester.pumpWidget(_appWith(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.logout));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
    expect(gateway.signOutCalled, isTrue);
  });
}

class _NoopTokenStore implements TokenStore {
  @override
  Future<void> clear() async {}

  @override
  Future<String?> readAccess() async => null;

  @override
  Future<String?> readRefresh() async => null;

  @override
  Future<void> save({required String access, required String refresh}) async {}
}
