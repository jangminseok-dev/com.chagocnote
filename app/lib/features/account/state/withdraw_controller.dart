import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../auth/state/session_controller.dart';
import '../../auth/state/social_sign_ins.dart';
import 'account_controller.dart';
import 'reauth.dart';

/// 탈퇴 화면의 동작을 담당한다. `AccountApi.withdraw`가 204/401을 모두
/// 성공으로 취급하므로, 이 메서드가 던지지 않고 끝나면 곧 탈퇴가 끝난
/// 것이다 — 세션을 로컬에서만 정리한다. 서버가 추가 확인을 요구하면
/// (매장 함께 닫기 등) 화면이 오류 코드를 보고 [confirmCloseShops]를 담아
/// 다시 부른다.
class WithdrawController extends Notifier<AsyncValue<void>> {
  SessionController get _session =>
      ref.read(sessionControllerProvider.notifier);

  @override
  AsyncValue<void> build() => const AsyncData(null);

  Future<void> withdraw({bool confirmCloseShops = false}) async {
    // 세션이 사라지기 전에 로그인 수단을 먼저 읽어 둔다 — 구글이 있었다면
    // 탈퇴 뒤에도 SDK 연결을 끊어야 하는데, 그때는 이미 로그아웃 상태라
    // `Me.identities`를 더 읽을 수 없다.
    final identities = ref.read(accountIdentitiesProvider);
    await ref.read(reauthCoordinatorProvider).run(
          () => ref
              .read(accountApiProvider)
              .withdraw(confirmCloseShops: confirmCloseShops),
        );
    await _session.completeWithdrawal();
    // 구글 연결 끊기는 계정 화면(unlink)과 같은 공용 함수를 쓴다
    // (social_sign_ins.dart) — 로직을 여기서 복제하지 않는다.
    if (identities.contains('google')) {
      await disconnectGoogle(ref);
    }
  }
}

final withdrawControllerProvider =
    NotifierProvider<WithdrawController, AsyncValue<void>>(
  WithdrawController.new,
);
