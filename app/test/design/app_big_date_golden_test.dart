import 'package:chagocnote/design/widgets/app_big_date.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppBigDate 골든 — 2026-09-22', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      AppBigDate(date: DateTime(2026, 9, 22)),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_big_date.png'));
  });
}
