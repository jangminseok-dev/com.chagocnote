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
  /// 이미 저장되었으므로(S5), 구글이었다면 그 직후 곧바로 구글 SDK 연결도
  /// 끊는다(베스트 에포트, `social_sign_ins.dart`의 `disconnectGoogle`을
  /// 그대로 쓴다 — 탈퇴 화면과 같은 로직을 중복하지 않는다).
  ///
  /// (fix round 1 — Task 12 검토) `disconnectGoogle`을 `reloadMe` 보다 앞에
  /// 둔다: `reloadMe`가 네트워크 오류 등으로 던지면 뒤에 있는 구글 연결
  /// 끊기가 아예 실행되지 않아 "해제가 성공한 뒤 구글 연결을 끊는다"는
  /// 전역 제약을 어기게 된다. 또한 `reloadMe` 자체의 실패는 해제 실패로
  /// 보지 않는다 — 해제는 `_api.unlink`가 성공한 시점에 서버에서 이미
  /// 끝났으므로, 본인 정보 재조회가 실패했다고 화면에 오류를 보이거나
  /// 이 메서드를 실패로 끝내지 않는다.
  Future<void> unlink(String provider) async {
    await _api.unlink(provider);
    if (provider == 'google') {
      await disconnectGoogle(ref);
    }
    try {
      await _session.reloadMe();
    } catch (_) {
      // 해제 자체는 이미 끝났다 — 본인 정보 재조회 실패를 해제 실패로
      // 보지 않는다.
    }
  }

  Future<void> logout() => _session.signOut();
}

final accountControllerProvider =
    NotifierProvider<AccountController, AsyncValue<void>>(
  AccountController.new,
);
