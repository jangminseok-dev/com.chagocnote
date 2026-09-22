import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

BoxDecoration _decorationOf(WidgetTester tester, String label) {
  return tester
      .widgetList<Container>(
        find.descendant(
          of: find.widgetWithText(AppChoiceChip, label),
          matching: find.byType(Container),
        ),
      )
      .map((c) => c.decoration)
      .whereType<BoxDecoration>()
      .single;
}

void main() {
  testWidgets('누르면 onTap 이 불리고, 고른 칩만 잉크로 칠하고 선택됨으로 읽힌다', (tester) async {
    var taps = 0;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              AppChoiceChip(label: '강아지', selected: true, onTap: () {}),
              AppChoiceChip(label: '고양이', selected: false, onTap: () => taps++),
            ],
          ),
        ),
      ),
    );

    await tester.tap(find.text('고양이'));
    await tester.pumpAndSettle();

    expect(taps, 1);
    expect(_decorationOf(tester, '강아지').color, AppColors.ink);
    expect(_decorationOf(tester, '고양이').color, AppColors.white);
    expect(
      tester.getSemantics(find.bySemanticsLabel('강아지')),
      matchesSemantics(
        label: '강아지',
        isButton: true,
        hasTapAction: true,
        hasSelectedState: true,
        isSelected: true,
      ),
    );
  });

  testWidgets('Wrap 안에서도 글자 폭만큼만 차지하고, 높이는 누르기 좋은 44다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 390,
            child: Wrap(
              children: [
                AppChoiceChip(label: '강아지', selected: false, onTap: () {}),
              ],
            ),
          ),
        ),
      ),
    );

    final size = tester.getSize(find.byType(AppChoiceChip));
    expect(size.width, lessThan(120));
    expect(size.height, 44);
  });

  testWidgets('Center 같은 유한 높이 부모 아래서도 높이는 44, 폭은 글자 폭만큼이다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: AppChoiceChip(label: '강아지', selected: false, onTap: () {}),
          ),
        ),
      ),
    );

    final size = tester.getSize(find.byType(AppChoiceChip));
    expect(size.width, lessThan(120));
    expect(size.height, 44);
  });

  testWidgets('AppChoiceChip 골든 — 고른 칩과 안 고른 칩', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AppChoiceChip(label: '강아지', selected: true, onTap: () {}),
          const SizedBox(width: 8),
          AppChoiceChip(label: '고양이', selected: false, onTap: () {}),
        ],
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_choice_chip.png'));
  });
}
