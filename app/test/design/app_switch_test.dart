import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('누르면 지금 값의 반대로 onChanged 가 불리고, 켜짐·꺼짐으로 읽힌다', (tester) async {
    final changes = <bool>[];
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Row(
            children: [
              AppSwitch(value: true, onChanged: changes.add, semanticLabel: '금액'),
              AppSwitch(
                value: false,
                onChanged: changes.add,
                semanticLabel: '몸무게',
              ),
            ],
          ),
        ),
      ),
    );

    await tester.tap(find.bySemanticsLabel('금액'));
    await tester.tap(find.bySemanticsLabel('몸무게'));
    await tester.pumpAndSettle();

    expect(changes, [false, true]);
    // 그리는 알약은 40×24 지만 누르는 영역은 44×44 다.
    expect(tester.getSize(find.bySemanticsLabel('금액')), const Size(44, 44));
    for (final (label, on) in [('금액', true), ('몸무게', false)]) {
      expect(
        tester.getSemantics(find.bySemanticsLabel(label)),
        matchesSemantics(
          label: label,
          isButton: true,
          hasTapAction: true,
          hasToggledState: true,
          isToggled: on,
          hasEnabledState: true,
          isEnabled: true,
        ),
      );
    }
  });

  testWidgets('onChanged 가 null 이면 눌리지 않고 흐리다 — 값은 그대로 읽힌다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Center(
            child: AppSwitch(value: true, onChanged: null, semanticLabel: '금액'),
          ),
        ),
      ),
    );

    await tester.tap(find.byType(AppSwitch));
    await tester.pumpAndSettle();

    // 버튼이 아니고 "사용할 수 없음"으로 읽힌다. (누름 동작 표시는 보지 않는다 — Pressable 은 눌림
    // 애니메이션 때문에 onTap 이 없어도 그 표시를 남긴다.)
    expect(
      tester.getSemantics(find.bySemanticsLabel('금액')),
      isSemantics(
        label: '금액',
        isButton: false,
        hasToggledState: true,
        isToggled: true,
        hasEnabledState: true,
        isEnabled: false,
      ),
    );
    final opacity = tester.widget<Opacity>(
      find.descendant(
        of: find.byType(AppSwitch),
        matching: find.byType(Opacity),
      ),
    );
    expect(opacity.opacity, lessThan(1));
  });

  testWidgets('AppSwitch 골든 — 켜짐, 꺼짐, 읽기 전용(켜짐·꺼짐)', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      Padding(
        padding: const EdgeInsets.all(12),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          spacing: 8,
          children: [
            AppSwitch(value: true, onChanged: (_) {}),
            AppSwitch(value: false, onChanged: (_) {}),
            const AppSwitch(value: true, onChanged: null),
            const AppSwitch(value: false, onChanged: null),
          ],
        ),
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_switch.png'));
  });
}
