import 'package:chagocnote/design/widgets/app_fab.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop() {}

void main() {
  testWidgets('AppFab 골든', (tester) async {
    final target = await pumpGoldenFrame(tester, AppFab(onPressed: _noop));

    await expectLater(target, matchesGoldenFile('goldens/app_fab.png'));
  });
}
