import 'dart:async';

import 'package:flutter_test/flutter_test.dart';

import 'support/load_fonts.dart';

/// `flutter test`가 이 디렉터리 아래 모든 테스트 파일보다 먼저 실행하는
/// 특수 진입점. 여기서 한 번만 폰트를 로드해두면 개별 테스트 파일에서
/// 매번 `setUpAll(loadTestFonts)`를 쓸 필요가 없다.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  // MaterialIcons 폰트를 rootBundle로 읽으려면(load_fonts.dart 참고) 바인딩이
  // 먼저 떠 있어야 한다 — 커스텀 TTF는 dart:io File로 직접 읽어서 필요
  // 없지만, 에셋 번들 조회는 ServicesBinding.instance가 필요하다.
  TestWidgetsFlutterBinding.ensureInitialized();
  await loadTestFonts();
  await testMain();
}
