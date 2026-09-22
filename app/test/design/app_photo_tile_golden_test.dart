import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('AppPhotoTile 골든 — 플레이스홀더 + 개수', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const AppPhotoTile(image: null, count: 3),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_photo_tile.png'));
  });
}
