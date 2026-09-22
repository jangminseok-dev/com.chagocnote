import 'package:chagocnote/design/widgets/app_segment.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop(int _) {}

void main() {
  testWidgets('AppSegment 골든 — "캘린더" 선택', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      AppSegment(
        labels: const ['캘린더', '기록'],
        currentIndex: 0,
        onChanged: _noop,
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_segment.png'));
  });
}
