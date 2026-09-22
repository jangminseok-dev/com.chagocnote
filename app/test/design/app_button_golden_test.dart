import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void _noop() {}

void main() {
  testWidgets('AppButton 골든 — 아웃라인 / 채움 / busy / 비활성', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          AppButton(label: '기록 수정', onPressed: _noop),
          SizedBox(height: 12),
          AppButton(label: '저장', onPressed: _noop, filled: true),
          SizedBox(height: 12),
          AppButton(label: '저장 중', onPressed: _noop, busy: true),
          SizedBox(height: 12),
          AppButton(label: '저장', onPressed: null),
        ],
      ),
    );

    // busy 버튼의 CircularProgressIndicator는 첫 프레임(t=0)에 호(arc)가
    // 거의 안 보인다. 고정된 시간만큼 더 진행시켜서(항상 같은 위상이라
    // 결정적이다) 스피너가 실제로 보이는 골든을 찍는다.
    await tester.pump(const Duration(milliseconds: 300));

    await expectLater(target, matchesGoldenFile('goldens/app_button.png'));
  });
}
