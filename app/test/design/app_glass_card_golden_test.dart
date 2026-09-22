import 'package:chagocnote/design/widgets/app_glass_card.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppGlassCard 골든 — 투명도 줄이기라 불투명 표면으로 그린다', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const SizedBox(
        width: 240,
        height: 120,
        child: AppGlassCard(
          child: Text(
            '차곡노트',
            style: TextStyle(fontFamily: 'Pretendard', fontSize: 24),
          ),
        ),
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_glass_card.png'));
  });
}
