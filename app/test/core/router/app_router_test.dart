import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/placeholder_screens.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

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

ProviderContainer _containerWith(SessionGateway gateway) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
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
}
