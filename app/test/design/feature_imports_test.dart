import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 기능 폴더(`lib/features/<기능>/`) 사이의 import 규칙 — 백엔드의 허브-스포크처럼 방향을 하나로 둔다.
///
/// - `auth`는 공용이다(세션·매장 선택·`runShopScoped`). 누구나 import 할 수 있다.
/// - `home`은 조립 껍데기다. 다른 기능을 import 할 수 있고, 아무도 `home`을 import 하지 않는다.
/// - `visit → customer`는 허용한다(예약 ①이 고객 검색을 재사용한다).
/// - 그 밖의 기능 간 import 는 금지다. 반대 방향이 필요하면 `lib/core/plugs/`의 자리를 `app.dart`가 채운다
///   (백엔드의 `dependencies/hub_ports.py`와 같은 꼴).
/// - 여러 기능이 함께 쓰는 것(시각·날짜 도우미, 오늘 날짜)은 `lib/core/`에 둔다.
void main() {
  const allowed = <String, Set<String>>{
    'visit': {'customer'},
  };
  const shared = {'auth'};
  const shell = {'home'};
  // import 뿐 아니라 export 지시문도 같은 규칙을 받는다.
  final directive = RegExp(
    r"^(?:import|export) '(\.\.?/[^']+)'",
    multiLine: true,
  );
  // 패키지 절대 경로(`package:chagocnote/features/...`)도 상대 경로와 같은 규칙을
  // 받는다 — IDE 자동 import 가 이 형태를 쓸 수 있다.
  final packageDirective = RegExp(
    "^(?:import|export) 'package:chagocnote/([^']+)'",
    multiLine: true,
  );

  test('기능 폴더끼리는 정해진 방향으로만 import 한다', () {
    final root = Directory('lib/features');
    final violations = <String>[];

    for (final entity in root.listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final normalized = entity.path.replaceAll(r'\', '/');
      final from = normalized.split('lib/features/')[1].split('/')[0];
      if (shell.contains(from)) continue;

      final content = entity.readAsStringSync();

      for (final match in directive.allMatches(content)) {
        // 상대 경로를 파일 위치 기준으로 풀어 어느 기능 폴더로 가는지 본다.
        final target = Uri.file(normalized).resolve(match.group(1)!).path;
        final marker = target.indexOf('lib/features/');
        if (marker < 0) continue; // core·design·l10n 은 기능이 아니다
        final to = target
            .substring(marker + 'lib/features/'.length)
            .split('/')[0];
        if (to == from) continue;
        if (shared.contains(to)) continue;
        if (allowed[from]?.contains(to) ?? false) continue;
        violations.add('$normalized → $to');
      }

      for (final match in packageDirective.allMatches(content)) {
        final targetPath = match.group(1)!;
        if (!targetPath.startsWith('features/')) continue;
        final to = targetPath.substring('features/'.length).split('/')[0];
        if (to == from) continue;
        if (shared.contains(to)) continue;
        if (allowed[from]?.contains(to) ?? false) continue;
        violations.add('$normalized → $to (package:)');
      }
    }

    expect(violations, isEmpty, reason: '허용되지 않은 기능 간 import: $violations');
  });

  test('아무도 home 을 import 하지 않는다', () {
    final violations = <String>{};

    for (final entity in Directory('lib').listSync(recursive: true)) {
      if (entity is! File || !entity.path.endsWith('.dart')) continue;
      final normalized = entity.path.replaceAll(r'\', '/');
      if (normalized.contains('lib/features/home/')) continue;
      if (normalized == 'lib/core/router/app_router.dart') {
        continue; // 라우터는 조립 지점이다
      }

      final content = entity.readAsStringSync();

      final hitsByRelative = directive.allMatches(content).any((match) {
        // 상대 경로를 파일 위치 기준으로 풀어 home 기능 폴더를 가리키는지 본다.
        final target = Uri.file(normalized).resolve(match.group(1)!).path;
        return target.contains('lib/features/home/');
      });
      final hitsByPackage = packageDirective
          .allMatches(content)
          .any((match) => match.group(1)!.startsWith('features/home/'));

      if (hitsByRelative || hitsByPackage) violations.add(normalized);
    }
    expect(violations, isEmpty, reason: 'home 을 import 함: $violations');
  });
}
