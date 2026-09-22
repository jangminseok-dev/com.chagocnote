import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:google_sign_in/google_sign_in.dart';

import 'social_sign_in.dart';

/// 구글 로그인 어댑터. `GoogleSignIn.instance.initialize`는 앱 전체에서
/// 정확히 한 번, 다른 어떤 메서드보다 먼저 불러야 한다(패키지 문서 —
/// 아니면 동작이 정의되지 않는다). 그래서 초기화 호출은 이 어댑터의
/// 인스턴스가 아니라 클래스 전체에서 캐시한다 — `socialSignInsProvider`가
/// 다시 빌드되며 새 `GoogleSignInAdapter`를 만들어도 초기화가 두 번
/// 불리지 않게 하기 위해서다. 초기화가 실패하면 캐시를 비워 다음 시도에서
/// 다시 부를 수 있게 한다.
class GoogleSignInAdapter implements SocialSignIn {
  GoogleSignInAdapter({this.clientId, this.serverClientId, this.initialize});

  final String? clientId;
  final String? serverClientId;

  /// 테스트 전용 — 실제 SDK 호출 대신 쓸 초기화 함수. 운영 코드는 넘기지
  /// 않는다(그러면 [GoogleSignIn.instance.initialize]를 그대로 쓴다).
  @visibleForTesting
  final Future<void> Function()? initialize;

  static Future<void>? _initializeFuture;

  /// 테스트 전용 — 이전 테스트가 남긴 캐시를 다음 테스트가 물려받지
  /// 않게 한다.
  @visibleForTesting
  static void resetInitializeCache() => _initializeFuture = null;

  Future<void> _ensureInitialized() {
    return _initializeFuture ??= _runInitialize();
  }

  Future<void> _runInitialize() async {
    try {
      await (initialize ??
          () => GoogleSignIn.instance.initialize(
                clientId: clientId,
                serverClientId: serverClientId,
              ))();
    } catch (_) {
      _initializeFuture = null;
      rethrow;
    }
  }

  /// 테스트 전용 — 캐시 동작(여러 인스턴스가 한 번만 초기화하는지, 실패
  /// 뒤 재시도되는지)을 진짜 SDK 없이 확인한다.
  @visibleForTesting
  Future<void> ensureInitializedForTest() => _ensureInitialized();

  @override
  String get provider => 'google';

  @override
  Future<SocialCredential?> signIn() async {
    await _ensureInitialized();
    try {
      final account = await GoogleSignIn.instance.authenticate();
      final idToken = account.authentication.idToken;
      if (idToken == null) {
        throw StateError('구글 로그인에서 ID 토큰을 받지 못했습니다.');
      }
      return SocialCredential(provider: provider, token: idToken);
    } on GoogleSignInException catch (e) {
      if (e.code == GoogleSignInExceptionCode.canceled) return null;
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    await _ensureInitialized();
    return GoogleSignIn.instance.disconnect();
  }
}
