import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:chagocnote/design/widgets/app_sheet.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('AppSheet 골든 — 연 상태의 전체 화면', (tester) async {
    tester.view.physicalSize = const Size(390, 700);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: appTheme(),
        debugShowCheckedModeBanner: false,
        home: GlassBridge(
          factory: const OpaqueSurfaceFactory(),
          child: AppBackground(
            child: Scaffold(
              backgroundColor: Colors.transparent,
              body: Builder(
                builder: (context) => Center(
                  child: ElevatedButton(
                    onPressed: () => AppSheet.show<void>(
                      context,
                      builder: (context) => const Padding(
                        padding: EdgeInsets.only(bottom: 24),
                        child: Text(
                          '시트 내용',
                          style: TextStyle(fontFamily: 'Pretendard', fontSize: 16),
                        ),
                      ),
                    ),
                    child: const Text('열기'),
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );

    await tester.tap(find.text('열기'));
    await tester.pumpAndSettle();

    await expectLater(
      find.byType(MaterialApp),
      matchesGoldenFile('goldens/app_sheet.png'),
    );
  });
}
