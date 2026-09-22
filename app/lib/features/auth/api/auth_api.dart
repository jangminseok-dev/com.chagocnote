import '../../../core/proxy/api_client.dart';
import 'social_sign_in.dart';

/// 로그인으로 받은 토큰 쌍. 토큰 값을 로그에 남기지 않도록 `toString`을
/// 오버라이드하지 않는다(기본 `toString`은 필드를 나열하지 않는다).
class AuthTokens {
  const AuthTokens({
    required this.accessToken,
    required this.refreshToken,
    required this.userId,
  });

  final String accessToken;
  final String refreshToken;
  final int? userId;
}

/// 로그인·로그아웃 전용 API. 둘 다 인증 토큰 없이(`public: true`) 호출한다 —
/// 로그인은 아직 토큰이 없고, 로그아웃은 만료된 토큰이어도 서버에 알려야 하기
/// 때문이다.
class AuthApi {
  AuthApi(this._client);

  final ApiClient _client;

  Future<AuthTokens> socialLogin(SocialCredential credential) async {
    final data = await _client.post(
      '/v1/auth/social',
      data: credential.toJson(),
      public: true,
    ) as Map<String, dynamic>;
    return AuthTokens(
      accessToken: data['access_token'] as String,
      refreshToken: data['refresh_token'] as String,
      userId: data['user_id'] as int?,
    );
  }

  Future<void> logout(String refreshToken) async {
    await _client.post(
      '/v1/auth/logout',
      data: {'refresh_token': refreshToken},
      public: true,
    );
  }
}
