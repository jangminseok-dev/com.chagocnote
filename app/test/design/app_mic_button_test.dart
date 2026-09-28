import 'package:chagocnote/design/widgets/app_mic_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('누르면 onTap 이 불리고, 탭 영역은 44×44 다', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: AppMicButton(
              listening: false,
              onTap: () => taps++,
              semanticLabel: '말로 기록하기',
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.bySemanticsLabel('말로 기록하기'));
    await tester.pump(const Duration(milliseconds: 500));

    expect(taps, 1);
    expect(tester.getSize(find.bySemanticsLabel('말로 기록하기')), const Size(44, 44));
  });

  testWidgets('AppMicButton 골든 — 쉬는 것과 듣는 것', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppMicButton(listening: false, onTap: () {}),
          const SizedBox(width: 12),
          AppMicButton(listening: true, onTap: () {}),
        ],
      ),
      surfaceSize: const Size(160, 80),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_mic_button.png'));
  });
}
