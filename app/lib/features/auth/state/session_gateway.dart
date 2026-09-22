import '../../../core/error/api_exception.dart';
import '../../../core/storage/prefs_store.dart';
import '../../../core/storage/token_store.dart';
import '../api/auth_api.dart';
import '../api/me_api.dart';
import '../api/social_sign_in.dart';
import 'session.dart';

/// 세션 컨트롤러가 실제 저장소/네트워크에 접근할 때 거치는 포트.
/// 프로덕션에서는 [HttpSessionGateway]로, 테스트에서는 메모리 기반 가짜
/// 구현으로 대체한다.
abstract class SessionGateway {
  Future<Me?> restore();
  Future<Me> signIn(SocialCredential credential);
  Future<void> signOut();
  Future<Me> refreshMe();
  Future<int?> readLastShopId();
  Future<void> writeLastShopId(int shopId);
}

/// [AuthApi]·[MeApi]·[TokenStore]·[PrefsStore]로 만든 실제 구현.
class HttpSessionGateway implements SessionGateway {
  HttpSessionGateway({
    required this._authApi,
    required this._meApi,
    required this._tokenStore,
    required this._prefsStore,
  });

  final AuthApi _authApi;
  final MeApi _meApi;
  final TokenStore _tokenStore;
  final PrefsStore _prefsStore;

  @override
  Future<Me?> restore() async {
    final refreshToken = await _tokenStore.readRefresh();
    if (refreshToken == null) return null;

    try {
      return await _meApi.fetch();
    } on ApiException catch (e) {
      if (e.code == 'UNAUTHENTICATED') {
        await _tokenStore.clear();
        return null;
      }
      // ApiClient 가 갱신 실패로 이미 이 기기의 세션을 끝냈을 수 있다(예: 정지된
      // 계정의 갱신이 403 ACCOUNT_SUSPENDED 로 끝난 경우 — 코드는
      // UNAUTHENTICATED 가 아니지만 토큰은 이미 지워졌다). 리프레시 토큰이 이미
      // 지워져 있으면 이 요청은 다시 시도해도 성공할 수 없으므로 복원 실패로
      // 본다. 네트워크 오류는 토큰이 남아 있으므로 이 분기를 타지 않고 아래에서
      // 다시 던져진다.
      if (await _tokenStore.readRefresh() == null) {
        return null;
      }
      // NETWORK 등 다른 오류는 그대로 전파한다. 스플래시 화면이 "다시 시도"를
      // 보여줄 수 있도록, 토큰은 지우지 않고 남겨 둔다.
      rethrow;
    }
  }

  @override
  Future<Me> signIn(SocialCredential credential) async {
    final tokens = await _authApi.socialLogin(credential);
    await _tokenStore.save(
      access: tokens.accessToken,
      refresh: tokens.refreshToken,
    );
    return _meApi.fetch();
  }

  @override
  Future<void> signOut() async {
    final refreshToken = await _tokenStore.readRefresh();
    if (refreshToken != null) {
      try {
        await _authApi.logout(refreshToken);
      } catch (_) {
        // 로그아웃은 오프라인에서도 되어야 한다 — 서버 통보 실패는 무시한다.
      }
    }
    await _tokenStore.clear();
    await _prefsStore.clear();
  }

  @override
  Future<Me> refreshMe() => _meApi.fetch();

  @override
  Future<int?> readLastShopId() => _prefsStore.readLastShopId();

  @override
  Future<void> writeLastShopId(int shopId) =>
      _prefsStore.writeLastShopId(shopId);
}
