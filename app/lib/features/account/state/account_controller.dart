import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';
import '../api/account_api.dart';

final accountApiProvider = Provider<AccountApi>(
  (ref) => AccountApi(
    client: ref.watch(apiClientProvider),
    tokenStore: ref.watch(tokenStoreProvider),
  ),
);

/// 현재 로그인 수단 목록. 세션의 `Me.identities`를 그대로 노출한다.
final accountIdentitiesProvider = Provider<List<String>>((ref) {
  final session = ref.watch(sessionControllerProvider).value;
  return session is SignedIn ? session.me.identities : const [];
});

/// 계정 화면의 동작(연결/해제/로그아웃)을 담당한다. 화면에 보여줄 상태는
/// [accountIdentitiesProvider]와 `sessionControllerProvider`에서 직접
/// 읽으므로, 이 컨트롤러는 별도의 데이터 상태를 갖지 않는다.
class AccountController extends Notifier<AsyncValue<void>> {
  AccountApi get _api => ref.read(accountApiProvider);

  SessionController get _session =>
      ref.read(sessionControllerProvider.notifier);

  @override
  AsyncValue<void> build() => const AsyncData(null);

  /// [signIn]으로 새 로그인 수단을 연결한다. 사용자가 취소하면(`null`)
  /// 요청을 보내지 않는다.
  Future<void> link(SocialSignIn signIn) async {
    final credential = await signIn.signIn();
    if (credential == null) return;
    await _api.link(credential);
    await _session.reloadMe();
  }

  /// 개발용 로그인 수단을 이름으로 연결한다.
  Future<void> linkDev(String name) async {
    await _api.link(SocialCredential(provider: 'dev', token: name));
    await _session.reloadMe();
  }

  /// [provider]를 해제한다. 해제 응답의 새 토큰은 `AccountApi.unlink` 안에서
  /// 이미 저장되었으므로, 그다음에 본인 정보를 다시 불러온다. 구글이었다면
  /// 마지막으로 구글 SDK 연결도 끊는다(베스트 에포트, `social_sign_ins.dart`의
  /// `disconnectGoogle`을 그대로 쓴다 — 탈퇴 화면과 같은 로직을 중복하지
  /// 않는다).
  Future<void> unlink(String provider) async {
    await _api.unlink(provider);
    await _session.reloadMe();
    if (provider == 'google') {
      await disconnectGoogle(ref);
    }
  }

  Future<void> logout() => _session.signOut();
}

final accountControllerProvider =
    NotifierProvider<AccountController, AsyncValue<void>>(
  AccountController.new,
);
