import 'dart:async';

import 'package:chagocnote/features/auth/api/social_sign_in.dart';
import 'package:chagocnote/features/auth/state/session.dart';
import 'package:chagocnote/features/auth/state/session_gateway.dart';

/// 테스트 전용 메모리 기반 [SessionGateway]. 시나리오별로 필드를 채워 넣고,
/// 컨트롤러가 호출한 내용은 필드에 그대로 기록해 둔다.
class FakeSessionGateway implements SessionGateway {
  Me? meOnRestore;
  Object? restoreError;
  int? lastShopId;

  /// restore() 가 호출된 횟수. 재시도 여부를 세는 데 쓴다.
  int restoreCallCount = 0;

  Me? meOnSignIn;
  Object? signInError;

  /// signIn에 실제로 넘어온 자격 증명. 인자를 제대로 전달했는지 검증한다.
  SocialCredential? receivedCredential;

  Me? meOnRefresh;
  Object? refreshMeError;

  /// refreshMe() 가 호출된 횟수. 게이트를 기다리기 전에 센다.
  int refreshMeCallCount = 0;

  /// 설정되어 있으면 refreshMe()는 이 completer가 끝날 때까지 기다린다.
  /// 갱신 응답을 기다리는 동안 다른 이벤트(예: endSession)가 끼어드는 경합을
  /// 결정적으로 재현할 때 쓴다.
  Completer<Me>? refreshMeGate;

  bool signOutCalled = false;
  int? writtenShopId;

  @override
  Future<Me?> restore() async {
    restoreCallCount++;
    if (restoreError != null) throw restoreError!;
    return meOnRestore;
  }

  @override
  Future<Me> signIn(SocialCredential credential) async {
    receivedCredential = credential;
    if (signInError != null) throw signInError!;
    return meOnSignIn!;
  }

  @override
  Future<void> signOut() async {
    signOutCalled = true;
  }

  @override
  Future<Me> refreshMe() async {
    refreshMeCallCount++;
    if (refreshMeGate != null) return refreshMeGate!.future;
    if (refreshMeError != null) throw refreshMeError!;
    return meOnRefresh!;
  }

  @override
  Future<int?> readLastShopId() async => lastShopId;

  @override
  Future<void> writeLastShopId(int shopId) async {
    writtenShopId = shopId;
    lastShopId = shopId;
  }
}
