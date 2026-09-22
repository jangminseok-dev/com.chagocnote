import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';

/// 골든 테스트가 "Ahem" 대체 폰트 대신 실제 글꼴 글리프로 렌더링하도록,
/// 번들된 TTF 파일들을 한 번만 로드해 등록한다.
///
/// `flutter test`는 기본적으로 실제 폰트를 로드하지 않고 테스트용
/// Ahem 폰트(글자마다 사각형 박스)를 쓴다. 골든에 진짜 글리프가
/// 보이도록 하려면 [FontLoader]로 TTF를 직접 등록해야 한다.
///
/// [test/flutter_test_config.dart]의 `testExecutable`에서 모든 테스트가
/// 시작되기 전에 딱 한 번 호출한다.
Future<void> loadTestFonts() async {
  await _loadFont('Pretendard', 'assets/fonts/PretendardVariable.ttf');
  await _loadFont('BodoniModa', 'assets/fonts/BodoniModa-VariableFont.ttf');
  await _loadFont('MaruBuri', 'assets/fonts/MaruBuri-Regular.ttf');
  await _loadMaterialIconsFont();
}

Future<void> _loadFont(String family, String path) async {
  final file = File(path);
  if (!file.existsSync()) {
    // 폰트 파일이 없어도 테스트 스위트 전체가 죽지 않게 한다 — 대신 그
    // 폰트를 쓰는 골든은 Ahem으로 실패해 원인을 바로 알 수 있다.
    debugPrint('[loadTestFonts] 폰트 파일을 찾을 수 없음: $path');
    return;
  }
  final bytes = await file.readAsBytes();
  final loader = FontLoader(family)
    ..addFont(Future.value(ByteData.view(bytes.buffer)));
  await loader.load();
}

/// `Icon(Icons.xxx)`는 "MaterialIcons"라는 폰트의 글리프다. `uses-material-
/// design: true`면 Flutter 툴이 엔진 캐시의 `MaterialIcons-Regular.otf`를
/// 자동으로 앱 폰트 매니페스트(`fonts/MaterialIcons-Regular.otf`)에 넣어
/// 주지만, `flutter test`는 이걸 자동으로 로드하지 않는다(커스텀 폰트와
/// 같은 이유) — 안 불러오면 골든에 아이콘이 빈 사각형(tofu)으로 찍힌다.
/// SDK 캐시 경로를 직접 하드코딩하지 않고, 이미 번들된 에셋 키를
/// `rootBundle`로 읽어서 그대로 등록한다.
Future<void> _loadMaterialIconsFont() async {
  try {
    final data = await rootBundle.load('fonts/MaterialIcons-Regular.otf');
    final loader = FontLoader('MaterialIcons')..addFont(Future.value(data));
    await loader.load();
  } catch (e) {
    debugPrint('[loadTestFonts] MaterialIcons 폰트를 불러오지 못함: $e');
  }
}
