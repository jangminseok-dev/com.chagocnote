import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/l10n/app_strings.dart';
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

ProviderContainer _containerWith() {
  final gateway = FakeSessionGateway()..meOnRestore = _meWithHissHaus();
  return ProviderContainer.test(
    retry: (retryCount, error) => null,
    overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
  );
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
  testWidgets('매장 이름을 보여준다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.text('Hiss Haus'), findsOneWidget);
  });

  testWidgets('탭을 바꾸면 본문이 바뀐다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.calendarEmptyTitle), findsOneWidget);
    expect(find.text(AppStrings.comingSoonEmptyTitle), findsNothing);

    await tester.tap(find.text(AppStrings.tabCustomers));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.calendarEmptyTitle), findsNothing);
    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);

    await tester.tap(find.text(AppStrings.tabSales));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);

    await tester.tap(find.text(AppStrings.tabCalendar));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.calendarEmptyTitle), findsOneWidget);
  });

  testWidgets('설정 버튼을 누르면 설정 화면으로 이동한다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel(AppStrings.settingsLabel));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
  });

  testWidgets('FAB 을 누르면 준비 중 안내 시트가 뜬다', (tester) async {
    final container = _containerWith();
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.add));
    await tester.pumpAndSettle();

    expect(find.text(AppStrings.comingSoonSheetText), findsOneWidget);
  });
}
