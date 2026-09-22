import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// `liquid_glass_widgets`는 `lib/design/bridge/` 안에서만 import할 수
/// 있다 — 화면 코드가 실제 유리 렌더러를 직접 알면 안 된다는 경계를
/// grep으로 강제한다.
void main() {
  test('liquid_glass_widgets는 lib/design/bridge/ 밖에서 import되지 않는다', () {
    final libDir = Directory('lib');
    final violations = <String>[];

    for (final entity in libDir.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;

      final normalized = entity.path.replaceAll(r'\', '/');
      if (normalized.contains('lib/design/bridge/')) continue;

      final content = entity.readAsStringSync();
      if (content.contains('package:liquid_glass_widgets')) {
        violations.add(normalized);
      }
    }

    expect(
      violations,
      isEmpty,
      reason: 'lib/design/bridge/ 밖에서 liquid_glass_widgets를 import함: $violations',
    );
  });
}
