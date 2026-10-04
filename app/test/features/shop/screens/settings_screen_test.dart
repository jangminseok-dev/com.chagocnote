import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/fake_session_gateway.dart';

const _hissHaus = ShopMembership(shopId: 3, shopName: 'Hiss Haus', role: 'owner');
const _staffShop = ShopMembership(shopId: 4, shopName: 'B매장', role: 'staff');

/// 이 화면 자체(설정 허브)는 매장 API를 부르지 않지만, 화면 전환 테스트가
/// 실제로 멤버 화면까지 들어가므로 그쪽이 부르는 매장 API를 가짜로 채워
/// 실제 네트워크 호출(그리고 그로 인한 pumpAndSettle 무한 대기)을 막는다.
ProviderContainer _containerWith(Me me, {int? lastShopId}) {
  final gateway = FakeSessionGateway()
    ..meOnRestore = me
    ..lastShopId = lastShopId;
  final adapter = FakeHttpClientAdapter(
    (options, body) => const FakeResponse(statusCode: 200, data: <dynamic>[]),
  );
  // dio(원 요청)와 refreshDio(리프레시 전용)는 같은 인스턴스를 쓰지 않는다 —
  // ApiClient 문서에 적힌 재귀 위험(같은 인터셉터를 타는 하나의 Dio를 둘 다에
  // 쓰면 리프레시 요청 자체의 401이 다시 리프레시를 부를 수 있다) 때문이다.
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [
      sessionGatewayProvider.overrideWithValue(gateway),
      apiClientProvider.overrideWith(
        (ref) => ApiClient(
          tokenStore: _NoopTokenStore(),
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      ),
    ],
  );
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
  testWidgets('매장 이름과 역할 칩을 보여준다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
    expect(find.text('Hiss Haus'), findsOneWidget);
    expect(find.text(AppStrings.roleOwner), findsOneWidget);
  });

  testWidgets('매장이 하나뿐이면 매장 바꾸기가 안 보인다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.settingsSwitchShop), findsNothing);
  });

  testWidgets('매장이 둘 이상이면 매장 바꾸기를 눌러 매장 선택 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus, _staffShop],
      ),
      lastShopId: _hissHaus.shopId,
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.settingsSwitchShop), findsOneWidget);
    await tester.tap(find.text(AppStrings.settingsSwitchShop));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
  });

  testWidgets('설정 → 다른 매장으로 들어가면 뒤로 가기 버튼이 있고, 누르면 설정으로 돌아간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus, _staffShop],
      ),
      lastShopId: _hissHaus.shopId,
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsSwitchShop));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
    expect(find.byType(AppBackButton), findsOneWidget);

    await tester.tap(find.byType(AppBackButton));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
  });

  testWidgets('멤버를 누르면 멤버 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsMembers));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
  });

  testWidgets('사장에게는 일정이 보이고 누르면 일정 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsSchedule));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsSchedule), findsOneWidget);
  });

  testWidgets('사장에게는 메뉴가 보이고 누르면 메뉴 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsMenus));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsMenus), findsOneWidget);
  });

  testWidgets('직원에게는 일정·메뉴가 보이지 않는다(V8 — 보안 경계는 서버 403)', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_staffShop],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.settingsShopInfo), findsOneWidget);
    expect(find.text(AppStrings.settingsSchedule), findsNothing);
    expect(find.text(AppStrings.settingsMenus), findsNothing);
  });

  testWidgets('"알림장" 줄은 직원에게도 보이고 누르면 알림장 설정이 열린다(읽기 전용 — ⑤ 설계 9.1)', (
    tester,
  ) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_staffShop],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsReport));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.reportSettings), findsOneWidget);
  });

  testWidgets('초대 코드로 합류를 누르면 초대 화면으로 간다', (tester) async {
    final container = _containerWith(
      const Me(
        id: 1,
        displayName: '민석',
        profileImageUrl: null,
        identities: ['apple'],
        shops: [_hissHaus],
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsJoinByInvite));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
  });

  group('뒤로 가기 버튼은 머리 왼쪽에 붙는다(최종 재검토)', () {
    const me = Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_hissHaus, _staffShop],
    );

    void expectLeft(WidgetTester tester) {
      final width = tester.view.physicalSize.width / tester.view.devicePixelRatio;
      // 버튼 위젯 자체는 늘어나도 왼쪽 끝이 0 근처라, 실제로 그려지는 아이콘의
      // 가운데를 잰다.
      final icon = find.descendant(
        of: find.byType(AppBackButton),
        matching: find.byType(Icon),
      );
      expect(tester.getCenter(icon).dx, lessThan(width / 4));
    }

    testWidgets('설정 화면', (tester) async {
      final container = _containerWith(me, lastShopId: _hissHaus.shopId);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      container.read(routerProvider).go('/settings');
      await tester.pumpAndSettle();

      expectLeft(tester);
    });

    testWidgets('설정 → 다른 매장(매장 선택 화면)', (tester) async {
      final container = _containerWith(me, lastShopId: _hissHaus.shopId);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      container.read(routerProvider).go('/settings');
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.settingsSwitchShop));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
      expectLeft(tester);
    });

    testWidgets('설정 → 초대 코드로 합류: 검은 AppBar 없이 본문 머리에 있고, 누르면 설정으로 돌아간다', (
      tester,
    ) async {
      final container = _containerWith(me, lastShopId: _hissHaus.shopId);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      container.read(routerProvider).go('/settings');
      await tester.pumpAndSettle();
      await tester.tap(find.text(AppStrings.settingsJoinByInvite));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.invite), findsOneWidget);
      expect(find.byType(AppBar), findsNothing);
      expect(find.byType(AppBackButton), findsOneWidget);
      expectLeft(tester);

      await tester.tap(find.byType(AppBackButton));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.settings), findsOneWidget);
    });
  });
}
