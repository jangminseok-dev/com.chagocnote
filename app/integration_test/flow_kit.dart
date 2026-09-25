// 시뮬레이터 흐름(실서버)의 공용 도구 — 확인마다 스크린샷을 찍고, 단언이 실패해도 다음 확인으로 넘어가며,
// 마지막에 모아 찍는다. `record_flow_test.dart`(④-2a)와 `photo_flow_test.dart`(④-2b)가 함께 쓴다.

import 'dart:io';
import 'dart:ui' as ui;

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';

late IntegrationTestWidgetsFlutterBinding binding;
late WidgetTester t;
final results = <String>[];
final softFails = <String>[];
String current = '-';

ProviderContainer get container =>
    ProviderScope.containerOf(t.element(find.byType(App)));
GoRouter get router => container.read(routerProvider);

void note(String text) {
  results.add('NOTE $current :: $text');
  debugPrint('NOTE $current :: $text');
}

void soft(bool ok, String what) {
  if (!ok) {
    softFails.add(what);
    note('어긋남: $what');
  }
}

void drain() {
  Object? ex;
  while ((ex = t.takeException()) != null) {
    final line = ex.toString().split('\n').take(6).join(' / ');
    results.add('EXC $current :: $line');
    debugPrint('EXC $current :: $line');
  }
}

Future<void> pumpFor(Duration d) async {
  final end = DateTime.now().add(d);
  while (DateTime.now().isBefore(end)) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
  }
}

/// 안드로이드는 첫 스크린샷 전에 화면을 이미지로 바꿔 두어야 찍힌다(한 번만).
var _surfaceConverted = false;

Future<void> shot(String name) async {
  await pumpFor(const Duration(milliseconds: 400));
  try {
    if (Platform.isAndroid && !_surfaceConverted) {
      await binding.convertFlutterSurfaceToImage();
      _surfaceConverted = true;
      await pumpFor(const Duration(milliseconds: 200));
    }
    await binding.takeScreenshot(name);
  } catch (e) {
    debugPrint('스크린샷 실패 $name: $e');
  }
}

Finder btn(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);
Finder p(String label) =>
    find.byWidgetPredicate((w) => w is Pressable && w.semanticLabel == label);

Future<void> waitFor(
  Finder f, {
  Duration timeout = const Duration(seconds: 20),
}) async {
  final end = DateTime.now().add(timeout);
  while (true) {
    await t.pump(const Duration(milliseconds: 50));
    drain();
    if (f.evaluate().isNotEmpty) return;
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('보이지 않는다: ${f.describeMatch(Plurality.zero)}');
    }
  }
}

/// 찾을 때까지 기다리고(목록이 게을러 아래는 안 그려지므로 없으면 조금씩 내려 본다), 보이게 옮긴다.
Future<void> reveal(Finder f) async {
  final end = DateTime.now().add(const Duration(seconds: 20));
  var waited = 0;
  while (f.evaluate().isEmpty) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('보이지 않는다: ${f.describeMatch(Plurality.zero)}');
    }
    await t.pump(const Duration(milliseconds: 50));
    drain();
    if (++waited % 20 == 0) {
      // 여러 줄 메모 칸도 세로 Scrollable 이라 화면의 세로 목록(ListView)을 끈다.
      final down = find.byWidgetPredicate(
        (w) => w is ListView && w.scrollDirection == Axis.vertical,
      );
      if (down.evaluate().isNotEmpty) {
        await t.drag(down.last, const Offset(0, -300), warnIfMissed: false);
        await t.pump(const Duration(milliseconds: 300));
      }
    }
  }
}

/// 찾아서 보이게 옮긴 뒤 누른다.
Future<void> tap(Finder f) async {
  await reveal(f);
  await t.ensureVisible(f.first);
  await t.pump(const Duration(milliseconds: 150));
  await t.tap(f.first);
  await pumpFor(const Duration(milliseconds: 500));
}

Future<void> enter(String key, String text) async {
  final f = find.byKey(ValueKey(key));
  await reveal(f);
  await t.ensureVisible(f);
  await t.enterText(f, text);
  // 키보드를 내린다 — 안드로이드는 키보드가 화면을 줄여, 다음에 누를 버튼이 목록에서 빠질 수 있다.
  FocusManager.instance.primaryFocus?.unfocus();
  await pumpFor(const Duration(milliseconds: 600));
}

String fieldText(String key) =>
    t.widget<TextField>(find.byKey(ValueKey(key))).controller!.text;

Future<void> step(String id, String title, Future<void> Function() body) async {
  current = id;
  debugPrint('STEP $id 시작 — $title');
  try {
    softFails.clear();
    await body();
    if (softFails.isNotEmpty) {
      throw TestFailure('어긋남 ${softFails.length}건: ${softFails.join(' | ')}');
    }
    results.add('PASS $id $title');
  } catch (e, st) {
    results.add(
      'FAIL $id $title :: ${e.toString().split('\n').take(8).join(' / ')}',
    );
    debugPrint('STEP $id 실패: $e\n$st');
    await shot('$id-FAIL');
  }
  drain();
}

Future<void> logout() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 500));
  router.push('/settings/account');
  await tap(btn(AppStrings.logout));
  await waitFor(
    find.byKey(ScreenKeys.login),
    timeout: const Duration(seconds: 30),
  );
}

Future<void> login(String name) async {
  await waitFor(
    find.byKey(ScreenKeys.login),
    timeout: const Duration(seconds: 30),
  );
  // 로그아웃 뒤 화면이 바뀌는 중이면 앞 화면의 칸에 들어간다 — 자리 잡은 뒤 로그인 화면의 칸에 넣는다.
  await pumpFor(const Duration(seconds: 1));
  await t.enterText(
    find.descendant(
      of: find.byKey(ScreenKeys.login),
      matching: find.byType(TextField),
    ),
    name,
  );
  await pumpFor(const Duration(milliseconds: 300));
  await tap(btn(AppStrings.devSignIn));
  try {
    await waitFor(
      find.byKey(ScreenKeys.home),
      timeout: const Duration(seconds: 30),
    );
  } on TestFailure {
    await shot('00-login-FAIL');
    rethrow;
  }
  await pumpFor(const Duration(seconds: 1));
}

Future<void> openVisit(int visitId) async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 300));
  router.push('/visits/$visitId');
  await waitFor(find.byKey(ScreenKeys.visitDetail));
  await pumpFor(const Duration(seconds: 1));
}

/// 서명 URL 로 저장소에서 바로 내려받는다.
Future<List<int>> download(String url) async {
  final client = HttpClient();
  try {
    final response = await (await client.getUrl(Uri.parse(url))).close();
    final bytes = <int>[];
    await for (final chunk in response) {
      bytes.addAll(chunk);
    }
    return bytes;
  } finally {
    client.close();
  }
}

/// 4000×3000 PNG 한 장을 임시 폴더에 만든다 — 앨범 대신 사진 선택기가 준다. [shade]마다 바탕이 다르다.
Future<String> makePhoto(String name, int shade) async {
  final recorder = ui.PictureRecorder();
  final canvas = ui.Canvas(recorder);
  canvas.drawRect(
    const ui.Rect.fromLTWH(0, 0, 4000, 3000),
    ui.Paint()..color = ui.Color(0xFF000000 + 0x303030 * (shade % 4 + 1)),
  );
  canvas.drawCircle(
    const ui.Offset(2000, 1500),
    900,
    ui.Paint()..color = const ui.Color(0xFFF0F0F0),
  );
  final image = await recorder.endRecording().toImage(4000, 3000);
  final png = await image.toByteData(format: ui.ImageByteFormat.png);
  final file = File('${Directory.systemTemp.path}/$name.png');
  await file.writeAsBytes(png!.buffer.asUint8List());
  return file.path;
}
