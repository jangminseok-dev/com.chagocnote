import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

/// 오류 화면 다듬기 설계 3.2: 화면을 불러오지 못했을 때의 오류는 `AsyncBody`가 그린다(원인 문구·
/// 다시 시도/돌아가기·받은 데이터 위 띠·인터넷 복귀 때 다시). 기능 화면이 `AppErrorRetry`의 가운데·
/// inline 모양을 직접 만들면 이 규칙을 빠뜨린다. 한 줄 모양(`AppErrorRetry.row` — 다음 쪽 실패, 시간 칸,
/// 휴무일 목록)은 좁은 자리라 화면이 직접 쓴다.
void main() {
  test('기능 화면은 AppErrorRetry 의 가운데·inline 모양을 직접 만들지 않는다', () {
    final direct = RegExp(r'AppErrorRetry(\.inline)?\(');
    final violations = [
      for (final entity in Directory('lib/features').listSync(recursive: true))
        if (entity is File &&
            entity.path.endsWith('.dart') &&
            direct.hasMatch(entity.readAsStringSync()))
          entity.path,
    ];

    expect(violations, isEmpty, reason: 'AsyncBody 를 쓰지 않음: $violations');
  });
}
