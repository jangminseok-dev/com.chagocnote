import '../../../core/error/api_exception.dart';
import '../../../core/proxy/api_client.dart';
import '../../../core/storage/token_store.dart';
import '../../auth/api/social_sign_in.dart';

/// 계정 화면 전용 API — 로그인 수단 연결/해제, 회원 탈퇴.
class AccountApi {
  AccountApi({required this._client, required this._tokenStore});

  final ApiClient _client;
  final TokenStore _tokenStore;

  /// 로그인 수단을 연결한다. `display_name`은 로그인(가입)에서만 쓰는
  /// 필드라 연결 요청 본문에서는 뺀다.
  Future<List<String>> link(SocialCredential credential) async {
    final body = credential.toJson()..remove('display_name');
    final data = await _client.post('/v1/auth/identities', data: body)
        as Map<String, dynamic>;
    return (data['identities'] as List).cast<String>();
  }

  /// 로그인 수단을 해제한다. 서버가 이 순간 발급하는 토큰이 유일하게 유효한
  /// 토큰이 되므로(다른 모든 세션은 폐기된다), 다른 무엇을 하기도 전에
  /// 가장 먼저 저장한다(S5) — 그다음에야 `identities`를 돌려준다.
  Future<List<String>> unlink(String provider) async {
    final data = await _client.delete('/v1/auth/identities/$provider')
        as Map<String, dynamic>;
    await _tokenStore.save(
      access: data['access_token'] as String,
      refresh: data['refresh_token'] as String,
    );
    return (data['identities'] as List).cast<String>();
  }

  /// 회원 탈퇴. 경합하는 두 번째 요청이 401을 받는 것도(이미 다른 요청이
  /// 탈퇴를 완료시킨 것) 성공으로 취급한다(S12) — 그 외 오류는 그대로
  /// 던진다.
  Future<void> withdraw({bool confirmCloseShops = false}) async {
    try {
      await _client.delete(
        '/v1/auth/account',
        data: confirmCloseShops ? {'confirm_close_shops': true} : null,
      );
    } on ApiException catch (e) {
      if (e.statusCode == 401) return;
      rethrow;
    }
  }
}
