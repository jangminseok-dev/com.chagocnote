import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

const _ownerA = ShopMembership(shopId: 1, shopName: 'Hiss Haus', role: 'owner');
const _staffB = ShopMembership(shopId: 2, shopName: 'B매장', role: 'staff');

Me _me() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [_ownerA, _staffB],
    );

ProviderContainer _containerWith(SessionGateway gateway) =>
    ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );

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
    final gateway = FakeSessionGateway()..meOnRestore = _me();
    final container = _containerWith(gateway);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.shopSelect), findsOneWidget);
    expect(find.text('Hiss Haus'), findsOneWidget);
    expect(find.text('B매장'), findsOneWidget);
    expect(find.text(AppStrings.roleOwner), findsOneWidget);
    expect(find.text(AppStrings.roleStaff), findsOneWidget);
  });

  testWidgets('매장을 고르면 선택 저장 후 홈으로 이동한다', (tester) async {
    final gateway = FakeSessionGateway()..meOnRestore = _me();
    final container = _containerWith(gateway);
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.text('B매장'));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(gateway.writtenShopId, _staffB.shopId);
  });
}
