import 'package:chagocnote/design/app_theme.dart';
import 'package:chagocnote/design/bridge/glass_surface.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// 골든 테스트용 고정 프레임.
///
/// `MaterialApp(theme: appTheme())` + `GlassBridge(factory:
/// OpaqueSurfaceFactory())` + 배경 그라데이션(`AppBackground`)으로
/// 위젯을 감싸고, 표면 크기와 devicePixelRatio를 고정해 골든이 기기·환경마다
/// 달라지지 않게 한다. 유리 위젯은 항상 불투명 대체 표면으로 찍힌다 —
/// 스펙이 요구하는 "투명도 줄이기" 골든과 같은 모습이다.
///
/// `child`를 `RepaintBoundary`로 감싸서 반환한 [Finder]로
/// `matchesGoldenFile`을 찍으면, 화면 전체가 아니라 그 위젯 크기만큼만
/// 잘려서 찍힌다.
Future<Finder> pumpGoldenFrame(
  WidgetTester tester,
  Widget child, {
  Size surfaceSize = const Size(390, 500),
}) async {
  tester.view.physicalSize = surfaceSize;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  final key = GlobalKey();

  await tester.pumpWidget(
    MaterialApp(
      theme: appTheme(),
      debugShowCheckedModeBanner: false,
      home: GlassBridge(
        factory: const OpaqueSurfaceFactory(),
        child: AppBackground(
          child: Scaffold(
            backgroundColor: Colors.transparent,
            body: Center(child: RepaintBoundary(key: key, child: child)),
          ),
        ),
      ),
    ),
  );

  return find.byKey(key);
}
