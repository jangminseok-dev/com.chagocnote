import 'package:chagocnote/design/widgets/app_glass_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop(int _) {}

void main() {
  testWidgets('AppGlassBar 골든 — 3슬롯, 가운데(고객) 선택', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      SizedBox(
        width: 320,
        child: AppGlassBar(
          items: const [
            AppGlassBarItem(icon: Icons.calendar_today, label: '캘린더'),
            AppGlassBarItem(icon: Icons.people_outline, label: '고객'),
            AppGlassBarItem(icon: Icons.bar_chart, label: '매출'),
          ],
          currentIndex: 1,
          onTap: _noop,
        ),
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_glass_bar.png'));
  });
}
