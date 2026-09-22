import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_glass_bar.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const items = [
    AppGlassBarItem(icon: Icons.calendar_today, label: '캘린더'),
    AppGlassBarItem(icon: Icons.people_outline, label: '고객'),
    AppGlassBarItem(icon: Icons.bar_chart, label: '매출'),
  ];

  testWidgets('탭하면 해당 인덱스로 onTap이 불린다', (tester) async {
    int? tappedIndex;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppGlassBar(
            items: items,
            currentIndex: 0,
            onTap: (i) => tappedIndex = i,
          ),
        ),
      ),
    );

    final gesture = await tester.startGesture(tester.getCenter(find.text('매출')));
    await tester.pump(const Duration(milliseconds: 100));
    await gesture.up();
    await tester.pumpAndSettle();

    expect(tappedIndex, 2);
  });

  testWidgets('선택된 슬롯은 잉크 색, 나머지는 보조 색이다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AppGlassBar(items: items, currentIndex: 1, onTap: (_) {}),
        ),
      ),
    );

    final selectedText = tester.widget<Text>(find.text('고객'));
    final unselectedText = tester.widget<Text>(find.text('캘린더'));

    expect(selectedText.style!.color, AppColors.ink);
    expect(unselectedText.style!.color, AppColors.secondary);
  });
}
