import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/proxy/providers.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';
import '../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'A매장', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me({List<ShopMembership> shops = const []}) => Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: const ['apple'],
      shops: shops,
    );

/// `MaterialApp.router`로 실제 앱과 같은 방식으로 라우터를 꽂는다.
/// [container]를 직접 받아서, 위젯 트리 바깥에서도 컨트롤러/라우터를
/// 조작할 수 있게 한다.
Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(routerProvider);
        return MaterialApp.router(routerConfig: router);
      },
    ),
  );
}

ProviderContainer _containerWith(
  SessionGateway gateway, {
  ApiClient Function(Ref ref)? apiClientBuilder,
}) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        if (apiClientBuilder != null)
          apiClientProvider.overrideWith(apiClientBuilder),
      ],
    );

void main() {
  testWidgets('로그아웃 상태면 로그인 화면으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('매장이 없으면 초대 화면으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: const []);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
  });

  testWidgets('매장이 하나면 바로 홈으로 간다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets(
    '매장이 둘이고 선택된 게 없으면 매장 선택 화면으로 가고, 고른 뒤 홈으로 이동하면 그대로 머무른다',
    (tester) async {
      // `/shops/select`는 매장을 이미 가진 사용자도 다시 열 수 있어야 하므로
      // (설정에서 매장 전환) 선택만으로 라우터가 자동으로 홈으로 밀어내지
      // 않는다 — 실제 화면이라면 선택 버튼의 onPressed가 `/home`으로 이동
      // 시킬 것이다. 지금은 자리 표시 화면이라 그 이동을 직접 흉내낸다.
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB]);
      final container = _containerWith(gateway);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);

      await container
          .read(sessionControllerProvider.notifier)
          .selectShop(_staffB.shopId);
      container.read(routerProvider).go('/home');
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
      expect(gateway.writtenShopId, _staffB.shopId);
    },
  );

  testWidgets('기억해둔 매장 id 가 있으면 매장 선택 화면을 건너뛰고 홈으로 간다', (tester) async {
    final gateway = FakeSessionGateway()
      ..meOnRestore = _me(shops: [_ownerA, _staffB])
      ..lastShopId = _staffB.shopId;
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byKey(ScreenKeys.shopSelect), findsNothing);
  });

  testWidgets(
    '복원이 네트워크 오류로 실패하면 스플래시에 머무르고, '
    '다시 시도해서 성공하면 홈으로 간다',
    (tester) async {
      final gateway = FakeSessionGateway()
        ..restoreError = Exception('네트워크 오류');
      final container = _containerWith(gateway);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.splash), findsOneWidget);

      gateway.restoreError = null;
      gateway.meOnRestore = _me(shops: [_ownerA]);
      container.invalidate(sessionControllerProvider);
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
    },
  );

  testWidgets('홈에 있는 중 endSession 이 호출되면 로그인 화면으로 밀려난다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);

    container.read(sessionControllerProvider.notifier).endSession();
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('로그아웃 상태로 /settings/members 딥링크를 열어도 로그인 화면으로 간다', (
    tester,
  ) async {
    final gateway = FakeSessionGateway()..meOnRestore = null;
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.login), findsOneWidget);

    container.read(routerProvider).go('/settings/members');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.login), findsOneWidget);
  });

  testWidgets('매장이 없는 사용자도 /settings/account 는 열 수 있다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: const []);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.invite), findsOneWidget);

    container.read(routerProvider).go('/settings/account');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settingsAccount), findsOneWidget);
  });

  testWidgets('매장이 있는 사용자는 /invite 를 열어도 홈으로 밀려나지 않는다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final container = _containerWith(gateway);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);

    container.read(routerProvider).go('/invite');
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.invite), findsOneWidget);
  });

  testWidgets(
    '매장 전환 뒤에도 라우터는 다시 만들어지지 않고 현재 화면에 그대로 머무른다',
    (tester) async {
      // 이 테스트는 "redirect 안에서는 ref.read만 쓴다" 규칙을 지킨다.
      // routerProvider 본문에서 세션을 ref.watch 하면 세션이 바뀔 때마다
      // GoRouter가 새로 만들어지므로(=내비게이션 스택이 리셋되므로) 이
      // identical 비교가 실패한다.
      final gateway = FakeSessionGateway()
        ..meOnRestore = _me(shops: [_ownerA, _staffB])
        ..lastShopId = _ownerA.shopId;
      // `/settings/members`는 이제 실제 화면이라 매장 API를 부른다. 실제
      // 네트워크로 나가 pumpAndSettle이 멎지 않도록 가짜 어댑터를 문
      // apiClientProvider로 덮어쓴다.
      final adapter = FakeHttpClientAdapter(
        (options, body) =>
            const FakeResponse(statusCode: 200, data: <dynamic>[]),
      );
      final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
      final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
      final container = _containerWith(
        gateway,
        apiClientBuilder: (ref) => ApiClient(
          tokenStore: MemoryTokenStore(),
          dio: dio,
          refreshDio: refreshDio,
          onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
        ),
      );

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();

      final router = container.read(routerProvider);
      router.go('/settings/members');
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);

      await container
          .read(sessionControllerProvider.notifier)
          .selectShop(_staffB.shopId);
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.settingsMembers), findsOneWidget);
      expect(identical(container.read(routerProvider), router), isTrue);
    },
  );

  testWidgets(
    '홈 → 설정 버튼 → 설정 화면 → 뒤로 → 홈 (홈은 쌓인 채라 탭 상태를 유지한다)',
    (tester) async {
      // 설정으로 갈 때 push(쌓기)를 쓰는지 확인하려고, 홈에서 탭을 바꿔 둔
      // 뒤 설정에 들어갔다 돌아왔을 때도 그 탭이 그대로인지를 본다. go로
      // 이동했다면 홈이 통째로 다시 만들어져 탭이 첫 화면으로 리셋된다.
      final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
      final container = _containerWith(gateway);
      addTearDown(container.dispose);

      await tester.pumpWidget(_appWith(container));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.home), findsOneWidget);

      await tester.tap(find.text(AppStrings.tabCustomers));
      await tester.pumpAndSettle();
      expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(AppStrings.settingsLabel));
      await tester.pumpAndSettle();
      expect(find.byKey(ScreenKeys.settings), findsOneWidget);

      // 설정의 뒤로 가기는 목록 행 안에서 왼쪽에 붙는다 — 의미 노드는 행 전체라
      // 그 가운데를 누르면 버튼이 아니다. 위젯을 직접 누른다.
      await tester.tap(find.byType(AppBackButton));
      await tester.pumpAndSettle();

      expect(find.byKey(ScreenKeys.home), findsOneWidget);
      expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
    },
  );

  testWidgets('설정 → 멤버 → 뒤로 → 설정', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final adapter = FakeHttpClientAdapter(
      (options, body) =>
          const FakeResponse(statusCode: 200, data: <dynamic>[]),
    );
    final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
    final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
    final container = _containerWith(
      gateway,
      apiClientBuilder: (ref) => ApiClient(
        tokenStore: MemoryTokenStore(),
        dio: dio,
        refreshDio: refreshDio,
        onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
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

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
  });

  testWidgets('설정 → 매장 정보 → 뒤로 → 설정', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me(shops: [_ownerA]);
    final adapter = FakeHttpClientAdapter((options, body) {
      if (options.path == '/v1/shops/1/settings' && options.method == 'GET') {
        return const FakeResponse(
          statusCode: 200,
          data: {
            'shop_id': 1,
            'name': 'A매장',
            'business_type': 'grooming',
            'phone': null,
            'address': null,
            'timezone': 'Asia/Seoul',
          },
        );
      }
      fail('예상하지 못한 경로: ${options.method} ${options.path}');
    });
    final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
    final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
    final container = _containerWith(
      gateway,
      apiClientBuilder: (ref) => ApiClient(
        tokenStore: MemoryTokenStore(),
        dio: dio,
        refreshDio: refreshDio,
        onSessionEnded: ref.read(sessionEndedSignalProvider).fire,
      ),
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();
    container.read(routerProvider).go('/settings');
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.settingsShopInfo));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.settingsShop), findsOneWidget);

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
  });
}
