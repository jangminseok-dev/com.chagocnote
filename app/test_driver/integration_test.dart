import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

/// 통합 테스트가 찍은 스크린샷을 호스트에 저장한다.
const _shots =
    '/Users/jangminseok/Project/com.chagocnote/.superpowers/sdd/2026-09-23-visit-3a2-app/task12-shots';

Future<void> main() async {
  await integrationDriver(
    onScreenshot: (name, bytes, [args]) async {
      final file = File('$_shots/$name.png');
      await file.create(recursive: true);
      await file.writeAsBytes(bytes);
      return true;
    },
  );
}
