import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _openSheet(WidgetTester tester, {double keyboard = 0}) async {
  tester.view.physicalSize = const Size(390, 700);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  // 키보드는 창의 viewInsets 로 흉내 낸다 — 시트는 루트 내비게이터의
  // MediaQuery 를 보므로 화면 안쪽에서 MediaQuery 를 덮어써서는 닿지 않는다.
  tester.view.viewInsets = FakeViewPadding(bottom: keyboard);
  addTearDown(tester.view.resetViewInsets);

  // 실제 글래스 팩토리(기본값) 아래에서 연다 — 시트가 글래스를 쓰면 여기서 드러난다.
  await tester.pumpWidget(
    MaterialApp(
      theme: appTheme(),
      home: Scaffold(
        resizeToAvoidBottomInset: false,
        body: Builder(
          builder: (context) => Center(
            child: ElevatedButton(
              onPressed: () => AppSheet.show<void>(
                context,
                builder: (context) => const Text('시트 내용'),
              ),
              child: const Text('열기'),
            ),
          ),
        ),
      ),
    ),
  );
  await tester.tap(find.text('열기'));
  await tester.pumpAndSettle();
}

void main() {
  // 설계 6.2 + 사용자 발견(초대 코드 시트의 보조 문구가 안 읽힌다): 시트는
  // 불투명 흰 면 위에 그리고, 막은 옅게 깐다(최종 검토 D).
  testWidgets('AppSheet 는 글래스 없이 불투명 흰 면으로 그린다', (tester) async {
    await _openSheet(tester);

    expect(find.text('시트 내용'), findsOneWidget);
    expect(find.byType(GlassSurface), findsNothing);
    expect(find.byType(BackdropFilter), findsNothing);
  });

  testWidgets('AppSheet 의 막은 이름 있는 옅은 토큰(AppColors.scrim)이다', (tester) async {
    await _openSheet(tester);

    final barrier = tester
        .widgetList<ModalBarrier>(find.byType(ModalBarrier))
        .last;
    expect(barrier.color, AppColors.scrim);
  });

  testWidgets('키보드가 올라오면 시트 내용이 키보드 위로 올라간다(F3)', (tester) async {
    await _openSheet(tester, keyboard: 300);

    final bottom = tester.getBottomLeft(find.text('시트 내용')).dy;
    expect(bottom, lessThanOrEqualTo(700 - 300));
  });
}
