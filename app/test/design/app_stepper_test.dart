import 'package:chagocnote/design/widgets/app_stepper.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('[−]·[+] 로 한 칸씩 바꾸고, 끝에서는 그쪽 단추가 눌리지 않는다', (tester) async {
    var value = 2;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: StatefulBuilder(
            builder: (context, setState) => AppStepper(
              value: value,
              min: 1,
              max: 3,
              label: (v) => '$v주',
              decreaseLabel: '줄이기',
              increaseLabel: '늘리기',
              onChanged: (v) => setState(() => value = v),
            ),
          ),
        ),
      ),
    );

    expect(find.text('2주'), findsOneWidget);
    await tester.tap(find.bySemanticsLabel('늘리기'));
    await tester.pumpAndSettle();
    expect(value, 3);
    await tester.tap(find.bySemanticsLabel('늘리기'));
    await tester.pumpAndSettle();
    expect(value, 3);
    for (var i = 0; i < 3; i++) {
      await tester.tap(find.bySemanticsLabel('줄이기'));
      await tester.pumpAndSettle();
    }
    expect(value, 1);
    expect(find.text('1주'), findsOneWidget);
  });
}
