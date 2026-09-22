import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import 'apple_nonce.dart';
import 'social_sign_in.dart';

/// Apple 로그인 어댑터. 웹뷰가 아니라 시스템 Apple 인증 시트를 쓴다.
///
/// 서버는 `sha256(rawNonce) == idToken.nonce`로 검증하므로, Apple에는 원문
/// nonce의 SHA-256 16진수 해시를 넘기고([hashNonce]), 서버에는 원문 nonce를
/// 그대로 보낸다([SocialCredential.nonce]).
class AppleSignIn implements SocialSignIn {
  const AppleSignIn();

  @override
  String get provider => 'apple';

  @override
  Future<SocialCredential?> signIn() async {
    final rawNonce = newRawNonce();
    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [
          AppleIDAuthorizationScopes.email,
          AppleIDAuthorizationScopes.fullName,
        ],
        nonce: hashNonce(rawNonce),
      );
      final identityToken = credential.identityToken;
      if (identityToken == null) {
        throw StateError('애플 로그인에서 ID 토큰을 받지 못했습니다.');
      }
      final displayName = [
        credential.givenName,
        credential.familyName,
      ].whereType<String>().join();
      return SocialCredential(
        provider: provider,
        token: identityToken,
        authorizationCode: credential.authorizationCode,
        nonce: rawNonce,
        displayName: displayName.isEmpty ? null : displayName,
      );
    } on SignInWithAppleAuthorizationException catch (e) {
      if (e.code == AuthorizationErrorCode.canceled) return null;
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    // Apple은 서버가 앱 전용 토큰을 폐기하는 방식으로 연결을 끊는다 — 이
    // 어댑터가 클라이언트에서 별도로 할 일이 없다.
  }
}
