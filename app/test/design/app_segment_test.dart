import 'package:chagocnote/design/widgets/app_segment.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('탭을 누르면 그 인덱스로 onChanged가 불린다', (tester) async {
    int? changedIndex;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppSegment(
            labels: const ['캘린더', '기록'],
            currentIndex: 0,
            onChanged: (i) => changedIndex = i,
          ),
        ),
      ),
    );

    final gesture = await tester.startGesture(tester.getCenter(find.text('기록')));
    await tester.pump(const Duration(milliseconds: 100));
    await gesture.up();
    await tester.pumpAndSettle();

    expect(changedIndex, 1);
  });
}
