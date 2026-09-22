import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/auth_api.dart';
import '../api/me_api.dart';
import '../api/social_sign_in.dart';
import 'session.dart';
import 'session_gateway.dart';

/// [SessionGateway] 구현을 주입하는 자리. 기본값은 실제 HTTP 구현이다 —
/// 테스트만 `overrideWithValue`로 가짜 게이트웨이를 꽂는다.
final sessionGatewayProvider = Provider<SessionGateway>((ref) {
  final client = ref.watch(apiClientProvider);
  return HttpSessionGateway(
    authApi: AuthApi(client),
    meApi: MeApi(client),
    tokenStore: ref.watch(tokenStoreProvider),
    prefsStore: ref.watch(prefsStoreProvider),
  );
});

/// 세션 상태를 소유하는 컨트롤러. 코드 생성 없이 plain `AsyncNotifier`로
/// 작성한다.
class SessionController extends AsyncNotifier<Session> {
  SessionGateway get _gateway => ref.read(sessionGatewayProvider);

  /// build() 가 실행되는 동안에는 true. 그 사이 endSession 이 불려도 `state`를
  /// 직접 바꿔봐야 build()의 반환값이 곧 그 위를 덮어써 버리므로(반환값이 이
  /// 프로바이더의 첫 상태가 된다), `_endedDuringBuild`에 대신 기록해 뒀다가
  /// build()의 반환값에 반영한다.
  bool _building = false;
  bool _endedDuringBuild = false;

  @override
  FutureOr<Session> build() async {
    _building = true;
    _endedDuringBuild = false;
    try {
      // `core/proxy`가 `features`를 모르는 채로 "세션 종료"를 알릴 수 있도록,
      // 이 신호에 콜백을 등록한다. 컨트롤러가 폐기되면 등록을 해제한다.
      final signal = ref.read(sessionEndedSignalProvider);
      signal.listener = endSession;
      ref.onDispose(() => signal.listener = null);

      final me = await _gateway.restore();
      if (me == null) return SignedOut(sessionExpired: _endedDuringBuild);
      return _resolveFromStorage(me);
    } finally {
      _building = false;
    }
  }

  /// 부팅 시점처럼 "현재 상태"가 없을 때 쓰는 선택 규칙: 저장소에 기억해둔
  /// 매장 id를 우선 쓴다.
  Future<Session> _resolveFromStorage(Me me) async {
    final lastShopId = await _gateway.readLastShopId();
    return _resolveWith(me, lastShopId);
  }

  /// 매장 선택 규칙: [candidateShopId]가 아직 [me]의 소속 목록에 있으면 그것,
  /// 없고 매장이 정확히 하나면 그것, 그 외에는 미선택(null).
  Session _resolveWith(Me me, int? candidateShopId) {
    int? selectedShopId;
    if (candidateShopId != null &&
        me.shops.any((shop) => shop.shopId == candidateShopId)) {
      selectedShopId = candidateShopId;
    } else if (me.shops.length == 1) {
      selectedShopId = me.shops.single.shopId;
    }
    return SignedIn(me: me, selectedShopId: selectedShopId);
  }

  /// 로그인. 로딩 상태로 바꾸지 않고, 실패해도 상태를 바꾸지 않는다 —
  /// 로그인 화면이 예외를 받아 문구를 보여준다.
  Future<void> signIn(SocialCredential credential) async {
    final me = await _gateway.signIn(credential);
    state = AsyncData(await _resolveFromStorage(me));
  }

  /// 로그아웃. 게이트웨이의 `signOut`은 서버 통보 실패를 스스로 삼키므로
  /// 이 메서드는 던지지 않는다.
  Future<void> signOut() async {
    await _gateway.signOut();
    state = const AsyncData(SignedOut());
  }

  /// 매장 전환. [shopId]가 현재 소속 목록에 없으면 아무 일도 하지 않는다.
  Future<void> selectShop(int shopId) async {
    final current = state.value;
    if (current is! SignedIn) return;
    if (!current.me.shops.any((shop) => shop.shopId == shopId)) return;

    await _gateway.writeLastShopId(shopId);
    if (!ref.mounted) return;
    state = AsyncData(current.copyWith(selectedShopId: shopId));
  }

  /// 본인 정보를 다시 불러온다. 실패하면 상태를 그대로 두고 예외를 던진다.
  Future<void> reloadMe() async {
    final me = await _gateway.refreshMe();
    if (!ref.mounted) return;
    replaceMe(me);
  }

  /// HTTP 계층이 리프레시 실패를 감지했을 때 호출한다. 즉시 로그아웃 상태로
  /// 만든다. build()가 진행 중이면 그 반환값이 상태를 덮어쓰므로 여기서
  /// state를 바꾸지 않고 표시만 해 둔다(build() 참고). 이미 로그아웃
  /// 상태면 그대로 둔다 — 직접 로그아웃한 뒤에 뒤늦게 도착한 리프레시
  /// 실패가 만료 띠를 새로 띄우면 안 되기 때문이다.
  void endSession() {
    if (_building) {
      _endedDuringBuild = true;
      return;
    }
    if (state.value is SignedOut) return;
    state = const AsyncData(SignedOut(sessionExpired: true));
  }

  /// 회원 탈퇴 완료 처리. 계정이 이미 사라졌으므로 서버에 통보하지 않고
  /// 로컬 토큰·설정만 지운다. `sessionExpired`는 세우지 않는다 — 탈퇴
  /// 직후에 "보안을 위해 다시 로그인해 주세요" 배너를 보여주는 건 맞지
  /// 않다. (갱신까지 실패해 `endSession()`이 세션을 끝낸 401은 탈퇴 완료가
  /// 아니므로 이 메서드까지 오지 않는다 — 최종 검토 B.)
  ///
  /// (fix round 1 — Task 13 검토) `state`를 먼저 덮어쓴 뒤에 `clearLocal()`을
  /// 부른다. 실기기의 `clearLocal()`은 flutter_secure_storage·SharedPreferences
  /// 플랫폼 채널 I/O라 수~수십 ms 걸린다 — 그동안 이미 탈퇴한 계정의 화면이
  /// 남아 있지 않도록 `state`를 먼저 바꿔 둔다.
  Future<void> completeWithdrawal() async {
    state = const AsyncData(SignedOut());
    await _gateway.clearLocal();
  }

  /// 이미 가지고 있는 [Me]로 상태를 교체한다. `reloadMe`와 같은 선택 규칙을
  /// 쓰지만, 네트워크 호출이 없으므로 동기로 끝낼 수 있다: 현재 선택된
  /// 매장이 새 소속 목록에도 있으면 유지하고, 없으면 매장이 하나뿐일 때만
  /// 자동 선택하며, 그 외에는 미선택으로 되돌린다. 현재 상태가 SignedIn이
  /// 아니면(응답을 기다리는 동안 로그아웃되거나 세션이 끝났으면) 아무 일도
  /// 하지 않는다 — 늦게 도착한 응답이 이미 끝난 세션을 되살리면 안 된다.
  void replaceMe(Me me) {
    final current = state.value;
    if (current is! SignedIn) return;
    state = AsyncData(_resolveWith(me, current.selectedShopId));
  }
}

final sessionControllerProvider =
    AsyncNotifierProvider<SessionController, Session>(SessionController.new);
