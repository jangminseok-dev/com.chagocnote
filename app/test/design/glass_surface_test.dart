import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:liquid_glass_widgets/liquid_glass_widgets.dart';

void main() {
  testWidgets('투명도 줄이기가 켜지면 GlassSurface는 불투명 표면을 쓴다', (tester) async {
    await tester.pumpWidget(
      const CupertinoApp(
        home: GlassAccessibilityScope(
          reduceTransparency: true,
          child: Center(child: GlassSurface(child: Text('안녕'))),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(GlassContainer), findsNothing);
    expect(find.text('안녕'), findsOneWidget);
  });

  testWidgets('투명도 줄이기가 꺼져 있으면 GlassSurface는 실제 GlassContainer를 쓴다', (
    tester,
  ) async {
    await tester.pumpWidget(
      const CupertinoApp(home: Center(child: GlassSurface(child: Text('안녕')))),
    );
    await tester.pump();

    expect(find.byType(GlassContainer), findsOneWidget);
  });

  testWidgets('GlassBridge로 감싸면 그 팩토리를 쓴다', (tester) async {
    await tester.pumpWidget(
      const CupertinoApp(
        home: GlassBridge(
          factory: OpaqueSurfaceFactory(),
          child: Center(child: GlassSurface(child: Text('안녕'))),
        ),
      ),
    );
    await tester.pump();

    expect(find.byType(GlassContainer), findsNothing);
  });
}
