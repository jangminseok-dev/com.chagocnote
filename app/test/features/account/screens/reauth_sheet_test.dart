// 재인증 시트를 위젯 트리 없이 최소 구성으로 검증한다. fix round 1 —
// signIn.signIn()이 던지면 처리되지 않은 비동기 예외가 되던 문제를 잡는다.
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/features/account/screens/reauth_sheet.dart';
import 'package:chagocnote/features/auth/state/social_sign_ins.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_social_sign_in.dart';

Widget _appWith(ProviderContainer container) {
  return UncontrolledProviderScope(
    container: container,
    child: MaterialApp(
      builder: (context, child) => GlassBridge(
        factory: const OpaqueSurfaceFactory(),
        child: child!,
      ),
      home: Consumer(
        builder: (context, ref, _) => Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => showReauthPrompt(context, ref, ['apple']),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('signIn()이 예외를 던지면 처리되지 않은 비동기 오류 없이 시트에 문구를 보여준다', (
    tester,
  ) async {
    final apple = FakeSocialSignIn('apple')..signInError = Exception('네이티브 SDK 오류');
    final container = ProviderContainer(
      overrides: [socialSignInsProvider.overrideWithValue([apple])],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(_appWith(container));
    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    await tester.tap(find.text(AppStrings.providerApple));
    await tester.pumpAndSettle();

    // 예외가 위로 새지 않았다 — 시트가 그대로 열려 있고, 토큰/예외 원문이
    // 아니라 공용 문구가 보인다(messageFor의 fallback).
    expect(tester.takeException(), isNull);
    expect(apple.signInCallCount, 1);
    expect(find.text(AppStrings.reauthPromptTitle), findsOneWidget);
    expect(find.text('문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.'), findsOneWidget);
  });
}
