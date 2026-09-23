import 'package:chagocnote/design/widgets/app_dashed_tile.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppDashedTile 골든 — 점선 자리 + 예약 수', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const AppDashedTile(count: 4, size: 72),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_dashed_tile.png'));
  });
}
