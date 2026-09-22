import 'package:chagocnote/app.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
    'buildRoot() 이 돌려주는 ProviderScope 는 재시도를 끈다(S2) — '
    '이 줄을 지우면 실패한다',
    () {
      final root = buildRoot();

      expect(root, isA<ProviderScope>());
      final scope = root as ProviderScope;

      expect(scope.retry, isNotNull);
      expect(scope.retry!(0, Exception('복원 실패')), isNull);
    },
  );
}
