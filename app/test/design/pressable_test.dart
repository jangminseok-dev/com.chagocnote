import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';

// Transform.scale은 x/y만 스케일하고 z축은 그대로 둔다. 그래서
// `Matrix4.getMaxScaleOnAxis()`는 z축의 1.0을 최댓값으로 잡아 항상 1.0을
// 반환한다 — 실제 2D 스케일 값은 행렬의 (0,0) 성분을 직접 읽어야 한다.
double _readScaleX(WidgetTester tester) =>
    tester.widget<Transform>(find.byType(Transform)).transform.storage[0];

Opacity _findOpacity(WidgetTester tester) =>
    tester.widget<Opacity>(find.byType(Opacity));

void main() {
  testWidgets('누르는 중간에는 스케일이 1보다 작아진다', (tester) async {
    await tester.pumpWidget(
      CupertinoApp(
        home: Center(child: Pressable(onTap: () {}, child: const Text('버튼'))),
      ),
    );

    final center = tester.getCenter(find.text('버튼'));
    final gesture = await tester.startGesture(center);
    // TapGestureRecognizer는 onTapDown을 kPressTimeout(100ms) 뒤에야
    // 부르므로, 그 뒤로 스프링이 진행 중인 중간 지점까지 pump한다.
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 40));

    final scale = _readScaleX(tester);
    expect(scale, lessThan(1.0));
    expect(scale, greaterThanOrEqualTo(0.9));

    await gesture.up();
    await tester.pumpAndSettle();

    final settledScale = _readScaleX(tester);
    expect(settledScale, closeTo(1.0, 0.001));
  });

  testWidgets('disableAnimations가 true면 예외 없이 페이드로 대체한다', (tester) async {
    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(
          accessibleNavigation: false,
          disableAnimations: true,
        ),
        child: CupertinoApp(
          home: Center(
            child: Pressable(onTap: () {}, child: const Text('버튼')),
          ),
        ),
      ),
    );

    final center = tester.getCenter(find.text('버튼'));
    final gesture = await tester.startGesture(center);
    await tester.pump(const Duration(milliseconds: 100));
    await tester.pump(const Duration(milliseconds: 40));

    // 스케일 트랜스폼 대신 Opacity가 쓰인다 — Transform 자체가 트리에 없다.
    expect(_findOpacity(tester).opacity, lessThan(1.0));
    expect(find.byType(Transform), findsNothing);

    await gesture.up();
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('탭 영역은 시각적 크기가 작아도 최소 44x44를 확보한다', (tester) async {
    await tester.pumpWidget(
      CupertinoApp(
        home: Center(
          child: Pressable(onTap: () {}, child: const Text('X')),
        ),
      ),
    );

    final size = tester.getSize(find.byType(Pressable));
    expect(size.width, greaterThanOrEqualTo(44));
    expect(size.height, greaterThanOrEqualTo(44));
  });
}
