import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/home/screens/home_shell.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

Me _meWithHissHaus() => const Me(
      id: 1,
      displayName: '민석',
      profileImageUrl: null,
      identities: ['apple'],
      shops: [ShopMembership(shopId: 1, shopName: 'Hiss Haus', role: 'owner')],
    );

void main() {
  testWidgets('홈 셸 골든 — 2026-09-22, Hiss Haus', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final gateway = FakeSessionGateway()..meOnRestore = _meWithHissHaus();
    final container = ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [
        sessionGatewayProvider.overrideWithValue(gateway),
        todayProvider.overrideWithValue(DateTime(2026, 9, 22)),
      ],
    );
    addTearDown(container.dispose);

    // 세션이 해석될 때까지 미리 기다린다 — 골든 프레임 안에서는
    // 로딩(스피너) 프레임을 찍고 싶지 않다.
    await container.read(sessionControllerProvider.future);

    final key = GlobalKey();
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: MaterialApp(
          theme: appTheme(),
          debugShowCheckedModeBanner: false,
          home: GlassBridge(
            factory: const OpaqueSurfaceFactory(),
            child: RepaintBoundary(key: key, child: const HomeShell()),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(key),
      matchesGoldenFile('goldens/home_shell.png'),
    );
  });
}
