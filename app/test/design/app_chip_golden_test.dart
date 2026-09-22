import 'package:chagocnote/design/widgets/app_chip.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppChip 골든 — 완료', (tester) async {
    final target = await pumpGoldenFrame(tester, const AppChip(label: '완료'));

    await expectLater(target, matchesGoldenFile('goldens/app_chip.png'));
  });
}
