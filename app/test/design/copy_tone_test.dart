import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 오류 화면 다듬기 설계 2.1: 앱 문구는 해요체다. 화면에 닿는 문구가 모인 두 파일의 문자열에
/// 합니다체(…니다)가 없어야 한다. 주석은 보지 않는다.
void main() {
  test('화면 문구와 오류 문구는 해요체다(…니다 없음)', () {
    const files = [
      'lib/l10n/app_strings.dart',
      'lib/core/error/error_messages.dart',
    ];
    final literal = RegExp(r"'[^']*니다[^']*'");
    final violations = [
      for (final path in files)
        for (final line in File(path).readAsLinesSync())
          if (!line.trimLeft().startsWith('//') && literal.hasMatch(line))
            '$path: ${line.trim()}',
    ];

    expect(violations, isEmpty, reason: '합니다체 문구: $violations');
  });
}
