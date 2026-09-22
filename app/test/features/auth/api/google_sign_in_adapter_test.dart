// 초기화 캐시(메모이제이션) 동작만 확인한다 — 실제 SDK 호출은 플랫폼
// 채널이 필요해 단위 테스트할 수 없다(fix round 1). 초기화 함수를 주입해
// 캐시 로직만 떼어 검증한다.
import 'package:chagocnote/features/auth/api/google_sign_in_adapter.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  tearDown(GoogleSignInAdapter.resetInitializeCache);

  test('인스턴스가 여러 개여도 초기화 함수는 한 번만 불린다', () async {
    var calls = 0;
    Future<void> fakeInitialize() async => calls++;

    final first = GoogleSignInAdapter(initialize: fakeInitialize);
    final second = GoogleSignInAdapter(initialize: fakeInitialize);

    await first.ensureInitializedForTest();
    await second.ensureInitializedForTest();

    expect(calls, 1);
  });

  test('초기화가 실패하면 캐시가 풀려 다음 시도에서 다시 부른다', () async {
    var calls = 0;
    Future<void> flakyInitialize() async {
      calls++;
      if (calls == 1) throw StateError('첫 시도 실패');
    }

    final adapter = GoogleSignInAdapter(initialize: flakyInitialize);

    await expectLater(adapter.ensureInitializedForTest(), throwsStateError);
    await adapter.ensureInitializedForTest();

    expect(calls, 2);
  });
}
