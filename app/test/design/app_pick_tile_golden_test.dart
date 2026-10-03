import 'package:chagocnote/design/widgets/app_pick_tile.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';
import '../support/upload_fakes.dart';

void main() {
  testWidgets('AppPickTile 골든 — 고른 사진, 고른 영상, 뺀 사진', (tester) async {
    final image = FakeMediaImages().image;
    AppPickTile tile({required bool picked, bool video = false}) => AppPickTile(
      image: image,
      size: 96,
      picked: picked,
      offLabel: '뺌',
      semanticLabel: '후 사진 1',
      video: video,
      durationSeconds: video ? 18 : null,
      onTap: () {},
    );
    final target = await pumpGoldenFrame(
      tester,
      Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          spacing: 8,
          children: [
            tile(picked: true),
            tile(picked: true, video: true),
            tile(picked: false),
          ],
        ),
      ),
      surfaceSize: const Size(390, 200),
    );
    await tester.runAsync(
      () => precacheImage(image, tester.element(target)),
    );
    await tester.pumpAndSettle();

    await expectLater(target, matchesGoldenFile('goldens/app_pick_tile.png'));
  });
}
