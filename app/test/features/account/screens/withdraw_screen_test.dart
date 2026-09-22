// 탈퇴 화면을 실제 라우터 + 가짜 HTTP 어댑터로 검증한다. AccountApi/
// WithdrawController/SessionController는 모두 진짜를 쓰고, 세션 게이트웨이만
// FakeSessionGateway로 문다.
import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/config/app_config.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

Me _me(List<String> identities) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: identities,
      shops: const [],
    );

final Finder _submitButton = find.byWidgetPredicate(
  (widget) => widget is AppButton && widget.label == AppStrings.withdrawSubmit,
);

({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUp(
  FakeSessionGateway gateway,
  FakeHandler handle, {
  AppConfig? config,
}) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final tokenStore = _NoopTokenStore();
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      tokenStoreProvider.overrideWithValue(tokenStore),
      if (config != null) appConfigProvider.overrideWithValue(config),
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

/// 진짜 리프레시 토큰이 든 저장소로 구성한다 — 갱신이 실제로 나가는 경로를
/// 볼 때 쓴다.
({ProviderContainer container, FakeHttpClientAdapter adapter}) _setUpWithStore(
  FakeSessionGateway gateway,
  TokenStore tokenStore,
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final container = ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
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

Future<void> _openWithdrawScreen(WidgetTester tester, ProviderContainer container) async {
  await tester.pumpWidget(_appWith(container));
  await tester.pumpAndSettle();
  container.read(routerProvider).go('/settings/account/withdraw');
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('체크박스를 누르기 전에는 탈퇴하기 버튼이 비활성화된다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(gateway, (options, body) => fail('예상하지 못한 요청: ${options.path}'));
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);

    final button = tester.widget<AppButton>(_submitButton);
    expect(button.onPressed, isNull);

    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();

    final enabledButton = tester.widget<AppButton>(_submitButton);
    expect(enabledButton.onPressed, isNotNull);
  });

  testWidgets('204 는 탈퇴 완료로 처리하고 로그인 화면으로 간다(첫 요청은 본문이 없다)', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    Uint8List? sentBody;
    final setup = _setUp(gateway, (options, body) {
      expect(options.method, 'DELETE');
      expect(options.path, '/v1/auth/account');
      sentBody = body;
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(sentBody, isNull);
    expect(find.byKey(ScreenKeys.login), findsOneWidget);
    expect(gateway.clearLocalCalled, isTrue);
    expect(setup.adapter.requests.where((r) => r.path == '/v1/auth/logout'), isEmpty);
  });

  testWidgets('리프레시 토큰이 없어 갱신 없이 401 이어도 탈퇴 완료로 끝난다(S12)', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 401,
        data: {'code': 'UNAUTHENTICATED', 'message': '이미 탈퇴됨'},
      ),
    );
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
    expect(find.text(AppStrings.sessionExpiredBanner), findsNothing);
    expect(setup.adapter.requests.where((r) => r.path == '/v1/auth/logout'), isEmpty);
  });

  testWidgets(
    '탈퇴 401 → 갱신도 401 이면 탈퇴 완료가 아니라 세션 만료다 — 만료 띠가 보이고 '
    'completeWithdrawal 을 부르지 않는다(최종 검토 B)',
    (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
      final tokenStore = MemoryTokenStore();
      await tokenStore.save(access: 'access-1', refresh: 'refresh-1');
      final setup = _setUpWithStore(
        gateway,
        tokenStore,
        (options, body) => const FakeResponse(
          statusCode: 401,
          data: {'code': 'UNAUTHENTICATED', 'message': '거절'},
        ),
      );
      addTearDown(setup.container.dispose);

      await _openWithdrawScreen(tester, setup.container);
      await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
      await tester.pumpAndSettle();
      await tester.tap(_submitButton);
      await tester.pumpAndSettle();

      // DELETE /v1/auth/account 401 → 갱신(진짜 리프레시 토큰이 있으므로
      // 실제로 나간다)도 401 → ApiClient 가 토큰을 지우고 endSession() 이
      // SignedOut(sessionExpired: true)를 세운다. 탈퇴 경로는 이 상태를
      // 덮어쓰지 않는다.
      expect(
        setup.adapter.requests.where((r) => r.path == '/v1/auth/refresh'),
        hasLength(1),
      );
      expect(find.byKey(ScreenKeys.login), findsOneWidget);
      expect(find.text(AppStrings.sessionExpiredBanner), findsOneWidget);
      expect(gateway.clearLocalCalled, isFalse);
      expect(
        setup.container.read(sessionControllerProvider).value,
        isA<SignedOut>().having((s) => s.sessionExpired, 'sessionExpired', isTrue),
      );
    },
  );

  testWidgets(
    '204 경로에서 clearLocal() 이 오래 걸려도 그동안 이미 로그인 화면이다 — '
    'completeWithdrawal 이 상태를 먼저 바꾼다(fix round 1 — S12 순서 판정)',
    (tester) async {
      final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
      final clearLocalGate = Completer<void>();
      gateway.clearLocalGate = clearLocalGate;
      final tokenStore = MemoryTokenStore();
      await tokenStore.save(access: 'access-1', refresh: 'refresh-1');
      final setup = _setUpWithStore(
        gateway,
        tokenStore,
        (options, body) => const FakeResponse(statusCode: 204),
      );
      addTearDown(setup.container.dispose);

      await _openWithdrawScreen(tester, setup.container);
      await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
      await tester.pumpAndSettle();
      await tester.tap(_submitButton);

      // 실기기의 clearLocal() 은 플랫폼 채널 I/O 라 수~수십 ms 걸린다. 여기서는
      // 게이트에 막혀 끝나지 않는다 — 그래도 state 는 이미 SignedOut() 이라
      // 라우터가 로그인 화면으로 보냈어야 한다.
      await tester.pumpAndSettle();
      expect(gateway.clearLocalCalled, isTrue);
      expect(find.byKey(ScreenKeys.login), findsOneWidget);
      expect(find.text(AppStrings.sessionExpiredBanner), findsNothing);

      clearLocalGate.complete();
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.login), findsOneWidget);
      expect(find.text(AppStrings.sessionExpiredBanner), findsNothing);
    },
  );

  testWidgets('SHOP_CLOSE_CONFIRM_REQUIRED 를 확정하면 confirm_close_shops:true 인 두 번째 요청을 보낸다(S7)', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    var callCount = 0;
    final setup = _setUp(gateway, (options, body) {
      callCount++;
      if (callCount == 1) {
        expect(body, isNull);
        return const FakeResponse(
          statusCode: 409,
          data: {'code': 'SHOP_CLOSE_CONFIRM_REQUIRED', 'message': '확인 필요'},
        );
      }
      expect(jsonDecode(utf8.decode(body!)), {'confirm_close_shops': true});
      expect(options.headers['content-type'], contains('application/json'));
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.withdrawShopCloseTitle), findsOneWidget);
    await tester.tap(find.text(AppStrings.withdrawShopCloseConfirm));
    await tester.pumpAndSettle();

    expect(callCount, 2);
    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('매장 함께 닫기 시트를 취소하면 두 번째 요청을 보내지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    var callCount = 0;
    final setup = _setUp(gateway, (options, body) {
      callCount++;
      if (callCount > 1) fail('취소했는데 두 번째 요청이 나갔다');
      return const FakeResponse(
        statusCode: 409,
        data: {'code': 'SHOP_CLOSE_CONFIRM_REQUIRED', 'message': '확인 필요'},
      );
    });
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.cancel));
    await tester.pumpAndSettle();

    expect(callCount, 1);
    expect(find.byKey(ScreenKeys.settingsAccountWithdraw), findsOneWidget);
  });

  testWidgets('OWNERSHIP_TRANSFER_REQUIRED 면 안내와 멤버 관리 버튼만 보여주고 재시도하지 않는다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['apple']);
    final setup = _setUp(
      gateway,
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'OWNERSHIP_TRANSFER_REQUIRED', 'message': '소유권 이전 필요'},
      ),
    );
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    await tester.pumpAndSettle();

    expect(find.text('혼자 사장인 매장에 다른 멤버가 있습니다. 먼저 다른 사장을 지정해 주세요.'), findsOneWidget);
    expect(find.text(AppStrings.goToMembers), findsOneWidget);
    expect(setup.adapter.requests, hasLength(1));
  });

  testWidgets('REAUTH_REQUIRED 를 받으면 재인증 시트에서 dev 로 다시 로그인해 탈퇴를 끝낸다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(['dev']);
    var withdrawCallCount = 0;
    final setup = _setUp(
      gateway,
      (options, body) {
        if (options.path == '/v1/auth/social') {
          expect(jsonDecode(utf8.decode(body!)), {
            'provider': 'dev',
            'token': '민석',
          });
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
        if (options.path == '/v1/auth/account') {
          withdrawCallCount++;
          if (withdrawCallCount == 1) {
            return const FakeResponse(
              statusCode: 403,
              data: {'code': 'REAUTH_REQUIRED', 'message': '다시 로그인해 주세요'},
            );
          }
          return const FakeResponse(statusCode: 204);
        }
        fail('예상하지 못한 요청: ${options.path}');
      },
      config: const AppConfig(apiBaseUrl: '', appEnv: 'dev'),
    );
    addTearDown(setup.container.dispose);

    await _openWithdrawScreen(tester, setup.container);
    await tester.tap(find.text(AppStrings.withdrawConfirmCheckbox));
    await tester.pumpAndSettle();
    await tester.tap(_submitButton);
    // 재인증 시트를 기다리는 동안 탈퇴 버튼이 계속 busy(스피너)라
    // pumpAndSettle이 절대 안 멈춘다 — 정해진 만큼만 pump 한다.
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 1000));

    expect(find.text(AppStrings.reauthPromptTitle), findsOneWidget);
    await tester.enterText(find.byType(TextField), '민석');
    await tester.tap(find.text(AppStrings.devSignIn));
    await tester.pump(const Duration(milliseconds: 50));
    await tester.pump(const Duration(milliseconds: 1000));

    expect(withdrawCallCount, 2);
    expect(find.byKey(ScreenKeys.login), findsOneWidget);
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
