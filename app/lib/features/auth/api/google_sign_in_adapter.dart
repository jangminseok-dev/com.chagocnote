import 'package:google_sign_in/google_sign_in.dart';

import 'social_sign_in.dart';

/// 구글 로그인 어댑터. `GoogleSignIn.instance.initialize`는 한 번만 부르면
/// 되므로, 이 어댑터 인스턴스 안에서 지연 초기화(lazy)하고 캐시한다.
class GoogleSignInAdapter implements SocialSignIn {
  GoogleSignInAdapter({this.clientId, this.serverClientId});

  final String? clientId;
  final String? serverClientId;

  Future<void>? _initializeFuture;

  Future<void> _ensureInitialized() {
    return _initializeFuture ??= GoogleSignIn.instance.initialize(
      clientId: clientId,
      serverClientId: serverClientId,
    );
  }

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
  Future<void> disconnect() => GoogleSignIn.instance.disconnect();
}
