import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_snack_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('앱 톤(잉크 바탕·흰 글자)의 스낵바를 띄우고, 화면이 닫힌 뒤에도 남는다', (tester) async {
    final navigatorKey = GlobalKey<NavigatorState>();
    await tester.pumpWidget(
      MaterialApp(
        navigatorKey: navigatorKey,
        home: const Scaffold(body: SizedBox()),
      ),
    );
    navigatorKey.currentState!.push(
      MaterialPageRoute<void>(
        builder: (context) => Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () {
                AppSnackBar.show(context, '이미 저장됐어요');
                Navigator.of(context).pop();
              },
              child: const Text('닫기'),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.text('닫기'));
    await tester.pumpAndSettle();

    expect(find.text('닫기'), findsNothing);
    expect(find.text('이미 저장됐어요'), findsOneWidget);
    final bar = tester.widget<SnackBar>(find.byType(SnackBar));
    expect(bar.backgroundColor, AppColors.ink);
    expect(bar.behavior, SnackBarBehavior.floating);
    final text = tester.widget<Text>(find.text('이미 저장됐어요'));
    expect(text.style?.color, AppColors.white);
  });
}
