import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 플러그인(기기 기능)은 `lib/core/proxy/`의 자리로만 부른다 — 화면(`lib/features/`)과
/// 모양 위젯(`lib/design/`)은 플러그인 패키지를 직접 import 하지 않는다(④-3a 설계 5.1).
/// 테스트가 자리를 대역으로 바꿀 수 있고, 플러그인을 바꿔도 자리 하나만 고친다.
void main() {
  const plugins = [
    'package:video_player/',
    'package:image_picker/',
    'package:gal/',
    'package:flutter_image_compress/',
    'package:connectivity_plus/',
  ];

  test('화면과 모양 위젯은 플러그인을 직접 import 하지 않고(core/proxy 만), 모양 위젯은 core 를 모른다', () {
    final violations = <String>[];
    for (final dir in ['lib/features', 'lib/design']) {
      for (final entity in Directory(dir).listSync(recursive: true)) {
        if (entity is! File || !entity.path.endsWith('.dart')) continue;
        final content = entity.readAsStringSync();
        for (final plugin in plugins) {
          if (content.contains(plugin)) {
            violations.add('${entity.path} → $plugin');
          }
        }
      }
    }

    expect(violations, isEmpty, reason: '플러그인 직접 import: $violations');

    // 방향은 core → design 하나다 — 모양 위젯은 core 를 모른다(재생 추상도 design 에 둔다).
    final core = RegExp(
      r"^(?:import|export) '(?:(?:\.\./)+core/|package:chagocnote/core/)",
      multiLine: true,
    );
    final upward = [
      for (final entity in Directory('lib/design').listSync(recursive: true))
        if (entity is File &&
            entity.path.endsWith('.dart') &&
            core.hasMatch(entity.readAsStringSync()))
          entity.path,
    ];
    expect(upward, isEmpty, reason: 'design → core import: $upward');
  });
}
