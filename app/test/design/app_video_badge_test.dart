import 'package:chagocnote/design/widgets/app_video_badge.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  test('formatDuration 은 초를 m:ss 로, 한 시간부터는 h:mm:ss 로 쓴다', () {
    expect(formatDuration(5), '0:05');
    expect(formatDuration(65), '1:05');
    expect(formatDuration(3600), '1:00:00');
  });

  testWidgets('AppVideoBadge 골든 — 길이 있는 것과 작은 것', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      const Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppVideoBadge(durationSeconds: 42),
          SizedBox(width: 12),
          AppVideoBadge(durationSeconds: 42, compact: true),
        ],
      ),
      surfaceSize: const Size(200, 80),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_video_badge.png'));
  });
}
