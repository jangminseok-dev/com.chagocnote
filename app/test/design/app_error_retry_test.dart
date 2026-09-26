import 'package:chagocnote/design/widgets/app_error_retry.dart';
import 'package:chagocnote/design/widgets/app_search_field.dart';
import 'package:chagocnote/design/widgets/app_sheet_action.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child) => MaterialApp(
  home: Scaffold(body: Center(child: child)),
);

void main() {
  testWidgets('AppErrorRetry 는 문구와 [다시 시도]를 보이고, 누르면 onRetry 를 부른다', (
    tester,
  ) async {
    var retried = 0;
    await tester.pumpWidget(
      _wrap(AppErrorRetry(message: '문제가 생겼어요', onRetry: () => retried++)),
    );
    expect(find.text('문제가 생겼어요'), findsOneWidget);
    await tester.tap(find.text(AppStrings.retry));
    expect(retried, 1);
  });

  testWidgets('onRetry 없이 onBack 만 주면 [돌아가기]만, 둘 다 없으면 문구만 보인다', (tester) async {
    var back = 0;
    await tester.pumpWidget(
      _wrap(AppErrorRetry(message: '권한이 없어요', onBack: () => back++)),
    );
    expect(find.text(AppStrings.retry), findsNothing);
    await tester.tap(find.text(AppStrings.goBack));
    expect(back, 1);

    await tester.pumpWidget(_wrap(const AppErrorRetry(message: '권한이 없어요')));
    expect(find.text('권한이 없어요'), findsOneWidget);
    expect(find.text(AppStrings.retry), findsNothing);
    expect(find.text(AppStrings.goBack), findsNothing);
  });

  testWidgets('row 변형은 한 줄에 문구와 버튼을 나란히 놓는다', (tester) async {
    await tester.pumpWidget(
      _wrap(AppErrorRetry.row(message: '못 읽었어요', onRetry: () {})),
    );
    final text = tester.getTopLeft(find.text('못 읽었어요'));
    final button = tester.getTopLeft(find.text(AppStrings.retry));
    expect(button.dx, greaterThan(text.dx));
    expect((button.dy - text.dy).abs(), lessThan(24));
  });

  testWidgets('AppSheetAction 은 누르면 onTap 을 부른다', (tester) async {
    var tapped = 0;
    await tester.pumpWidget(
      _wrap(AppSheetAction(label: '수정', onTap: () => tapped++)),
    );
    await tester.tap(find.text('수정'));
    expect(tapped, 1);
  });

  testWidgets('AppSearchField 는 힌트를 보이고 컨트롤러에 글을 넣는다', (tester) async {
    final controller = TextEditingController();
    addTearDown(controller.dispose);
    await tester.pumpWidget(
      _wrap(AppSearchField(controller: controller, hintText: '이름·번호')),
    );
    expect(find.text('이름·번호'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '콩이');
    expect(controller.text, '콩이');
  });
}
