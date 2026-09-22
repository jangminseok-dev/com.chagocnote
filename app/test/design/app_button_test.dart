import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _tap(WidgetTester tester, Finder finder) async {
  final gesture = await tester.startGesture(tester.getCenter(finder));
  await tester.pump(const Duration(milliseconds: 100));
  await gesture.up();
  await tester.pumpAndSettle();
}

// busy 버튼은 CircularProgressIndicator가 계속 회전해서 pumpAndSettle이
// 끝나지 않는다 — 고정된 pump 몇 번으로 대신한다.
Future<void> _tapBusy(WidgetTester tester, Finder finder) async {
  final gesture = await tester.startGesture(tester.getCenter(finder));
  await tester.pump(const Duration(milliseconds: 100));
  await gesture.up();
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  testWidgets('활성 버튼을 누르면 onPressed가 호출된다', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: AppButton(label: '기록 수정', onPressed: () => tapped = true),
        ),
      ),
    );

    await _tap(tester, find.text('기록 수정'));
    expect(tapped, isTrue);
  });

  testWidgets('busy면 스피너를 보여주고 onPressed를 부르지 않는다', (tester) async {
    var tapped = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Center(
          child: AppButton(
            label: '저장',
            onPressed: () => tapped = true,
            busy: true,
          ),
        ),
      ),
    );

    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await _tapBusy(tester, find.text('저장'));
    expect(tapped, isFalse);
  });

  testWidgets('onPressed가 null이면(비활성) 탭해도 아무 일도 없다', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Center(child: AppButton(label: '저장', onPressed: null)),
      ),
    );

    await _tap(tester, find.text('저장'));
    expect(tester.takeException(), isNull);
    // 컨트롤러 판정(P6): 비활성일 때 안쪽 Pressable의 onTap이 null인지도
    // 직접 단언한다 — 예외가 없다는 것만으로는 실제로 탭이 막혔는지 알 수
    // 없다.
    expect(tester.widget<Pressable>(find.byType(Pressable)).onTap, isNull);
  });
}
