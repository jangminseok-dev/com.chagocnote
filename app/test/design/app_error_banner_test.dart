import 'package:chagocnote/design/widgets/app_error_banner.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: child));

void main() {
  testWidgets('문구를 보이고, onRetry 가 있으면 [다시 시도]를 누를 수 있다', (tester) async {
    var retried = 0;
    await tester.pumpWidget(
      _wrap(AppErrorBanner(message: '서버에 잠시 문제가 있어요', onRetry: () => retried++)),
    );
    expect(find.text('서버에 잠시 문제가 있어요'), findsOneWidget);
    await tester.tap(find.text(AppStrings.retry));
    expect(retried, 1);
  });

  testWidgets('onRetry 가 없으면 [다시 시도]가 없고, offline 이면 끊김 아이콘이다', (tester) async {
    await tester.pumpWidget(
      _wrap(const AppErrorBanner(message: '인터넷에 연결되지 않았어요', offline: true)),
    );
    expect(find.text(AppStrings.retry), findsNothing);
    expect(find.byIcon(Icons.wifi_off_rounded), findsOneWidget);
  });

  testWidgets('AppErrorBanner 골든 — 인터넷 없음 한 줄, 서버 오류와 [다시 시도] 한 줄', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const AppErrorBanner(
            message: '인터넷에 연결되지 않았어요 · 이전 내용이에요',
            offline: true,
          ),
          const SizedBox(height: 8),
          AppErrorBanner(
            message: '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.',
            onRetry: () {},
          ),
        ],
      ),
      surfaceSize: const Size(390, 160),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_error_banner.png'));
  });
}
