import 'package:chagocnote/design/widgets/app_icon_toggle.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../support/golden_frame.dart';

void main() {
  testWidgets('아이콘을 누르면 그 인덱스로 onChanged 가 불리고, 탭 영역은 44×44 다', (tester) async {
    int? changed;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Center(
            child: AppIconToggle(
              icons: const [Icons.view_list, Icons.grid_view],
              labels: const ['목록', '격자'],
              currentIndex: 0,
              onChanged: (i) => changed = i,
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.bySemanticsLabel('격자'));
    await tester.pumpAndSettle();

    expect(changed, 1);
    expect(tester.getSize(find.bySemanticsLabel('격자')), const Size(44, 44));
    expect(
      tester.getSemantics(find.bySemanticsLabel('목록')),
      matchesSemantics(
        label: '목록',
        isButton: true,
        hasTapAction: true,
        hasSelectedState: true,
        isSelected: true,
      ),
    );
  });

  testWidgets('AppIconToggle 골든 — 목록 선택', (tester) async {
    final target = await pumpGoldenFrame(
      tester,
      AppIconToggle(
        icons: const [Icons.view_list, Icons.grid_view],
        labels: const ['목록', '격자'],
        currentIndex: 0,
        onChanged: (_) {},
      ),
    );

    await expectLater(target, matchesGoldenFile('goldens/app_icon_toggle.png'));
  });
}
