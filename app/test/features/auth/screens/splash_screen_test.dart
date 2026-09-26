import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/auth/screens/splash_screen.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_session_gateway.dart';

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: MaterialApp(
      theme: appTheme(),
      home: const GlassBridge(
        factory: OpaqueSurfaceFactory(),
        child: SplashScreen(),
      ),
    ),
  );
}

void main() {
  testWidgets('복원이 실패하면 문구와 다시 시도 버튼을 보여주고, 누르면 다시 시도한다', (tester) async {
    final gateway = FakeSessionGateway()..restoreError = Exception('네트워크 오류');
    final container = ProviderContainer.test(
      retry: (retryCount, error) => null,
      overrides: [sessionGatewayProvider.overrideWithValue(gateway)],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.pumpAndSettle();

    expect(find.text('문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
    expect(gateway.restoreCallCount, 1);

    gateway.restoreError = null;
    await tester.tap(find.text('다시 시도'));
    // 재시도 뒤 상태는 로딩(스피너)으로 끝없이 애니메이션되므로
    // pumpAndSettle 대신 고정 프레임만 진행한다.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(gateway.restoreCallCount, 2);
  });
}
