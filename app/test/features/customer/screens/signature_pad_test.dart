// 서명 칸과 서명 그림 — 그리기, 한 번에 포인터 하나, 다시 쓰기, PNG.
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:chagocnote/features/customer/screens/signature_pad.dart';
import 'package:chagocnote/features/customer/state/signature_png.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<SignatureController> _pump(WidgetTester tester, {double width = 300}) async {
  final controller = SignatureController();
  addTearDown(controller.dispose);
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(
      // 서명 칸은 스크롤되는 화면 안에 있다 — 칸 위의 손짓이 화면을 굴리지 않아야 한다.
      body: ListView(
        children: [
          const SizedBox(height: 40),
          Center(child: SizedBox(width: width, child: SignaturePad(controller: controller))),
          const SizedBox(height: 2000),
        ],
      ),
    ),
  ));
  return controller;
}

Offset _at(WidgetTester tester, double fx, double fy) {
  final box = tester.getRect(find.byKey(SignaturePad.canvasKey));
  return Offset(box.left + box.width * fx, box.top + box.height * fy);
}

void main() {
  testWidgets('칸의 비율은 5:2 이고 빈 칸에는 안내가 있다', (tester) async {
    final controller = await _pump(tester);

    final size = tester.getSize(find.byKey(SignaturePad.canvasKey));
    expect((size.width, size.height), (300, 120));
    expect(find.text('여기에 서명해 주세요'), findsOneWidget);
    expect(controller.isEmpty, isTrue);
  });

  testWidgets('폰을 가로로 돌려도 칸은 보이는 높이의 반을 넘지 않는다 — 칸 밖을 끌어 화면을 굴릴 자리가 남는다', (tester) async {
    tester.view.physicalSize = const Size(844, 390);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await _pump(tester, width: 800);

    final size = tester.getSize(find.byKey(SignaturePad.canvasKey));
    expect(size.height, lessThanOrEqualTo(195));
    expect(size.width / size.height, closeTo(2.5, 0.01));
  });

  testWidgets('아이패드처럼 넓어도 칸의 폭은 560 을 넘지 않는다', (tester) async {
    tester.view.physicalSize = const Size(1366, 1024);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await _pump(tester, width: 1300);

    final size = tester.getSize(find.byKey(SignaturePad.canvasKey));
    expect((size.width, size.height), (560, 224));
  });

  testWidgets('그으면 선이 남고 점은 칸에 대한 비율로 적힌다', (tester) async {
    final controller = await _pump(tester);
    var changes = 0;
    controller.addListener(() => changes += 1);

    final gesture = await tester.startGesture(_at(tester, 0.25, 0.25));
    await gesture.moveTo(_at(tester, 0.5, 0.5));
    await gesture.moveTo(_at(tester, 0.75, 0.75));
    await gesture.up();
    await tester.pump();

    expect(controller.strokes, hasLength(1));
    final stroke = controller.strokes.single;
    expect(stroke.first.dx, closeTo(0.25, 0.001));
    expect(stroke.last.dy, closeTo(0.75, 0.001));
    expect(changes, greaterThanOrEqualTo(3));
    expect(find.text('여기에 서명해 주세요'), findsNothing);
  });

  testWidgets('칸 위에서 세로로 그어도 화면이 구르지 않는다', (tester) async {
    final controller = await _pump(tester);
    final before = tester.getTopLeft(find.byKey(SignaturePad.canvasKey));

    await tester.dragFrom(_at(tester, 0.5, 0.1), const Offset(0, 100));
    await tester.pump();

    expect(tester.getTopLeft(find.byKey(SignaturePad.canvasKey)), before);
    expect(controller.isEmpty, isFalse);
  });

  testWidgets('그리는 중에 닿은 둘째 손가락은 선을 긋지 않는다', (tester) async {
    final controller = await _pump(tester);

    final first = await tester.startGesture(_at(tester, 0.1, 0.2), pointer: 1);
    await first.moveTo(_at(tester, 0.2, 0.3));
    final second = await tester.startGesture(_at(tester, 0.9, 0.8), pointer: 2);
    await second.moveTo(_at(tester, 0.8, 0.7));
    await second.up();
    await first.moveTo(_at(tester, 0.3, 0.2));
    await first.up();

    expect(controller.strokes, hasLength(1));
    expect(controller.strokes.single.every((p) => p.dx < 0.5), isTrue);
    // 뗀 뒤에는 다음 손가락을 받는다.
    final third = await tester.startGesture(_at(tester, 0.6, 0.5), pointer: 3);
    await third.up();
    expect(controller.strokes, hasLength(2));
  });

  testWidgets('마우스의 오른쪽 단추로는 긋지 않는다', (tester) async {
    final controller = await _pump(tester);

    final gesture = await tester.startGesture(
      _at(tester, 0.5, 0.5), kind: PointerDeviceKind.mouse, buttons: kSecondaryButton,
    );
    await gesture.moveTo(_at(tester, 0.6, 0.6));
    await gesture.up();

    expect(controller.isEmpty, isTrue);
  });

  testWidgets('다시 쓰기는 지운다', (tester) async {
    final controller = await _pump(tester);
    await tester.dragFrom(_at(tester, 0.2, 0.5), const Offset(60, 0));
    expect(controller.isEmpty, isFalse);

    await tester.tap(find.text('다시 쓰기'));
    await tester.pump();

    expect(controller.isEmpty, isTrue);
    expect(find.text('여기에 서명해 주세요'), findsOneWidget);
  });

  testWidgets('서명 그림은 600×240 PNG 이고 흰 바탕에 그은 자리만 검다', (tester) async {
    // 그림을 만드는 일은 실제 비동기다 — runAsync 안에서 돈다.
    final (png, pixels) = (await tester.runAsync(() async {
      final bytes = await signaturePng([
        [const Offset(0.25, 0.5), const Offset(0.75, 0.5)],
      ]);
      final codec = await ui.instantiateImageCodec(bytes);
      final image = (await codec.getNextFrame()).image;
      final raw = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
      return (bytes, (image.width, image.height, raw!));
    }))!;

    expect(png.sublist(0, 8), [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]);
    expect(ByteData.sublistView(png, 16, 24).getUint32(0), 600);
    expect(ByteData.sublistView(png, 16, 24).getUint32(4), 240);
    expect(png.length, lessThanOrEqualTo(signatureMaxBytes));
    final (width, height, raw) = pixels;
    int red(int x, int y) => raw.getUint8((y * width + x) * 4);
    expect((width, height), (600, 240));
    expect(red(300, 120), lessThan(80));       // 가운데 — 선이 지난다
    expect(red(300, 30), greaterThan(240));    // 위쪽 — 흰 바탕
    expect(red(30, 120), greaterThan(240));    // 선의 왼쪽 밖
  });

  testWidgets('그림이 65,536바이트를 넘으면 300×120 으로 다시 만든다', (tester) async {
    // 실제 서명은 상한을 넘기 어렵다 — 상한을 낮춰 그 길을 지나게 한다.
    final png = (await tester.runAsync(() => signaturePng([
      [const Offset(0.25, 0.5), const Offset(0.75, 0.5)],
    ], maxBytes: 100)))!;

    expect(ByteData.sublistView(png, 16, 24).getUint32(0), 300);
    expect(ByteData.sublistView(png, 16, 24).getUint32(4), 120);
  });

  testWidgets('점 하나만 찍어도 그림에 남는다', (tester) async {
    final dark = await tester.runAsync(() async {
      final bytes = await signaturePng([
        [const Offset(0.5, 0.5)],
      ]);
      final image = (await (await ui.instantiateImageCodec(bytes)).getNextFrame()).image;
      final raw = (await image.toByteData(format: ui.ImageByteFormat.rawRgba))!;
      return raw.getUint8((120 * 600 + 300) * 4);
    });

    expect(dark, lessThan(80));
  });
}
