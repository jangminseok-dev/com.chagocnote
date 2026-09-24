// 공유로 받은 글은 로그인·매장 선택이 끝난 뒤 초안 화면으로 간다(③-A3).
// 앱 루트(App)에 붙은 관문을 실제 라우터·세션과 함께 본다.
import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/shared_text_channel.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/visit_test_backend.dart';

const _channel = MethodChannel(SharedTextChannel.name);
const _text = '내일 2시반 두부 부분미용';

void _mockPending(String? pending) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(
        _channel,
        (call) async => call.method == 'getPending' ? pending : null,
      );
  addTearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, null),
  );
}

Future<void> _nativeSends(String text) => TestDefaultBinaryMessengerBinding
    .instance
    .defaultBinaryMessenger
    .handlePlatformMessage(
      SharedTextChannel.name,
      const StandardMethodCodec().encodeMethodCall(
        MethodCall('onSharedText', text),
      ),
      (_) {},
    );

Future<CustomerTestSetup> _pumpApp(
  WidgetTester tester, {
  void Function(CustomerTestSetup setup)? before,
}) async {
  useTallView(tester);
  final setup = CustomerTestSetup(
    VisitTestBackend().call,
    overrides: [todayProvider.overrideWithValue(DateTime(2026, 9, 23))],
  );
  addTearDown(setup.container.dispose);
  before?.call(setup);
  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: setup.container,
      child: const GlassBridge(factory: OpaqueSurfaceFactory(), child: App()),
    ),
  );
  await settle(tester);
  return setup;
}

void main() {
  testWidgets('앱이 뜨기 전에 받아 둔 글(콜드 스타트)은 로그인·매장 선택 뒤 초안 화면으로 간다', (
    tester,
  ) async {
    _mockPending(_text);
    final setup = await _pumpApp(tester);

    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(find.text(_text), findsOneWidget);
    // 한 번 열었으면 비운다 — 다시 열리지 않게.
    expect(setup.container.read(pendingSharedTextProvider), isNull);
  });

  test('로그아웃 상태에서는 받아 둔 글을 열지 않고 들고 있다가, 로그인·매장 선택 뒤에 연다', () async {
    _mockPending(null);
    final setup = CustomerTestSetup(VisitTestBackend().call);
    addTearDown(setup.container.dispose);
    setup.gateway.meOnRestore = null;
    await setup.container.read(sessionControllerProvider.future);
    expect(
      setup.container.read(sessionControllerProvider).value,
      isA<SignedOut>(),
    );

    setup.container.read(pendingSharedTextProvider.notifier).set(_text);
    expect(setup.container.read(sharedTextToOpenProvider), isNull);
    expect(setup.container.read(pendingSharedTextProvider), _text);

    // 로그인해 매장이 골라지면 그때 연다.
    setup.gateway.meOnRestore = customerTestMe();
    setup.container.invalidate(sessionControllerProvider);
    await setup.container.read(sessionControllerProvider.future);
    expect(setup.container.read(sharedTextToOpenProvider), _text);
  });

  testWidgets('앱이 떠 있을 때 공유가 오면 초안 화면을 연다', (tester) async {
    _mockPending(null);
    await _pumpApp(tester);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);

    await _nativeSends(_text);
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
  });

  testWidgets('로그아웃 상태에서 받아 둔 글은 로그인(매장 하나) 뒤 홈 위에 초안 화면 하나로 열린다', (
    tester,
  ) async {
    _mockPending(_text);
    final setup = await _pumpApp(
      tester,
      before: (setup) => setup.gateway
        ..meOnRestore = null
        ..meOnSignIn = customerTestMe(),
    );
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);

    // 로그인하면 라우터가 /login → /home 으로 옮긴다. 관문은 그 이동이 끝난 뒤 연다.
    await setup.container
        .read(sessionControllerProvider.notifier)
        .signIn(const SocialCredential(provider: 'dev', token: '민석'));
    await settle(tester);

    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(setup.container.read(pendingSharedTextProvider), isNull);

    setup.container.read(routerProvider).pop();
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('매장이 둘인 계정은 매장 선택 화면에서는 글을 들고 기다리다가, 고른 뒤(go /home) 홈 위에 초안 화면을 연다', (
    tester,
  ) async {
    _mockPending(_text);
    final setup = await _pumpApp(
      tester,
      before: (setup) => setup.gateway.meOnRestore = _twoShopMe(),
    );
    final router = setup.container.read(routerProvider);
    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);

    await tester.tap(find.text('Hiss Haus'));
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(setup.container.read(pendingSharedTextProvider), isNull);
    router.pop();
    await settle(tester);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);

    // 매장이 골라진 채로 매장 선택 화면(설정 → 매장 전환)에 있을 때 공유가 와도
    // 그 위에 열지 않는다 — 고른 뒤 go('/home')이 스택을 갈면 사라지기 때문이다.
    router.push('/shops/select');
    await settle(tester);
    await _nativeSends(_text);
    await settle(tester);
    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
    expect(find.byKey(ScreenKeys.visitDraft), findsNothing);
    expect(setup.container.read(pendingSharedTextProvider), _text);

    await tester.tap(find.text('Hiss Haus'));
    await settle(tester);
    expect(find.byKey(ScreenKeys.visitDraft), findsOneWidget);
    expect(setup.container.read(pendingSharedTextProvider), isNull);
    router.pop();
    await settle(tester);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });
}

Me _twoShopMe() => Me(
  id: 1,
  displayName: '민석',
  profileImageUrl: null,
  identities: const ['apple'],
  shops: [
    ...customerTestMe().shops,
    const ShopMembership(shopId: 4, shopName: '둘째 매장', role: 'staff'),
  ],
);
