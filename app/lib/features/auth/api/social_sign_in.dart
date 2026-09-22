/// 소셜 로그인 공급자가 돌려주는 자격 증명.
///
/// `toJson`은 서버가 기대하는 스네이크케이스 키로 바꾸고, 값이 없는 필드는
/// 아예 생략한다(서버가 `null`과 "필드 없음"을 다르게 취급할 수 있어서).
class SocialCredential {
  const SocialCredential({
    required this.provider,
    required this.token,
    this.authorizationCode,
    this.nonce,
    this.displayName,
  });

  final String provider;
  final String token;
  final String? authorizationCode;
  final String? nonce;
  final String? displayName;

  Map<String, dynamic> toJson() => {
        'provider': provider,
        'token': token,
        if (authorizationCode != null) 'authorization_code': authorizationCode,
        if (nonce != null) 'nonce': nonce,
        if (displayName != null) 'display_name': displayName,
      };
}

/// 소셜 로그인 공급자 하나를 다루는 포트. 카카오/구글/애플 구현체는
/// `kakao_sign_in.dart`·`google_sign_in_adapter.dart`·`apple_sign_in.dart`에
/// 있다.
abstract class SocialSignIn {
  String get provider;

  /// 사용자가 로그인을 취소하면 `null`을 반환한다.
  Future<SocialCredential?> signIn();

  Future<void> disconnect();
}
