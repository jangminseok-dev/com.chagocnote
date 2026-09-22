import 'package:chagocnote/design/widgets/app_big_date.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('2026-09-22는 22, September, Tuesday로 보여준다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Center(child: AppBigDate(date: DateTime(2026, 9, 22))),
      ),
    );

    expect(find.text('22'), findsOneWidget);
    expect(find.text('September'), findsOneWidget);
    expect(find.text('Tuesday'), findsOneWidget);
  });
}
