import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';

import 'support/load_fonts.dart';

/// CI(리눅스)는 `--dart-define=SKIP_GOLDEN_COMPARE=true`로 골든 비교를 건너뛴다.
/// 골든은 맥에서 만들어 리눅스의 글꼴 렌더링과 다르다 — 골든은 맥에서 로컬로 확인한다.
const _skipGoldenCompare = bool.fromEnvironment('SKIP_GOLDEN_COMPARE');

/// `flutter test`가 이 디렉터리 아래 모든 테스트 파일보다 먼저 실행하는
/// 특수 진입점. 여기서 한 번만 폰트를 로드해두면 개별 테스트 파일에서
/// 매번 `setUpAll(loadTestFonts)`를 쓸 필요가 없다.
Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  // MaterialIcons 폰트를 rootBundle로 읽으려면(load_fonts.dart 참고) 바인딩이
  // 먼저 떠 있어야 한다 — 커스텀 TTF는 dart:io File로 직접 읽어서 필요
  // 없지만, 에셋 번들 조회는 ServicesBinding.instance가 필요하다.
  TestWidgetsFlutterBinding.ensureInitialized();
  await loadTestFonts();
  // flutter test 가 파일마다 LocalFileComparator 를 꽂은 뒤 이 함수를 부르므로 여기서 덮어쓴다.
  if (_skipGoldenCompare) goldenFileComparator = _SkippingGoldenComparator();
  await testMain();
}

/// 골든을 비교하지 않고 통과시킨다. 위젯을 그리는 데까지는 그대로 돈다.
class _SkippingGoldenComparator extends GoldenFileComparator {
  @override
  Future<bool> compare(Uint8List imageBytes, Uri golden) async => true;

  @override
  Future<void> update(Uri golden, Uint8List imageBytes) async {}
}
