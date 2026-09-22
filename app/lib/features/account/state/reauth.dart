import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/error/api_exception.dart';
import '../../../core/proxy/providers.dart';
import '../../../l10n/app_strings.dart';
import '../../auth/api/social_sign_in.dart';
import '../../auth/state/auth_providers.dart';
import '../../auth/state/session.dart';
import '../../auth/state/session_controller.dart';

/// [linkedProviders](현재 계정에 연결된 로그인 수단)를 받아 사용자가 고른
/// 자격 증명을 돌려준다. 사용자가 시트를 닫기만 하면(취소) `null`.
typedef ReauthPrompt = Future<SocialCredential?> Function(
  List<String> linkedProviders,
);

/// `ReauthCoordinator`가 부를 프롬프트를 담아 두는 자리. 계정/탈퇴 화면이
/// `initState`에서 `prompt`를 채우고 `dispose`에서 비운다 — 화면이 없을 때
/// (이론상 불가능하지만) 프롬프트가 없으면 재인증 없이 원래 오류를 그대로
/// 던진다.
///
/// 실제 시트 UI(`_ReauthSheetContent`, `showReauthPrompt`)는 위젯이라
/// `features/account/screens/reauth_sheet.dart`에 있다 — 기능 폴더는
/// 화면·상태·API 세 층만 두므로, 위젯 코드를 상태 층에 두지 않는다.
class ReauthPromptHolder {
  ReauthPrompt? prompt;
}

final reauthPromptProvider = Provider<ReauthPromptHolder>(
  (ref) => ReauthPromptHolder(),
);

/// 재인증 뒤 소셜 로그인이 다른 계정으로 이어졌을 때 던진다. 저장된 토큰은
/// 건드리지 않는다(S6) — 그 세션은 서버에도 베스트 에포트로 로그아웃
/// 통보만 하고 버린다.
class ReauthMismatchException implements Exception {
  const ReauthMismatchException();

  String get message => AppStrings.reauthMismatch;
}

/// `REAUTH_REQUIRED`를 만나면 프롬프트 → 소셜 로그인 → 원 요청 재시도
/// 흐름을 한 번만 수행한다(두 번째 `REAUTH_REQUIRED`는 그대로 던져서
/// 무한 루프를 막는다).
class ReauthCoordinator {
  ReauthCoordinator(this._ref);

  final Ref _ref;

  Future<T> run<T>(Future<T> Function() action) async {
    try {
      return await action();
    } on ApiException catch (e) {
      if (e.code != 'REAUTH_REQUIRED') rethrow;

      final session = _ref.read(sessionControllerProvider).value;
      final me = session is SignedIn ? session.me : null;
      final linkedProviders = me?.identities ?? const <String>[];

      final prompt = _ref.read(reauthPromptProvider).prompt;
      final credential = prompt == null ? null : await prompt(linkedProviders);
      if (credential == null) rethrow;

      // 방어: 세션이 SignedIn이 아니면(예: 그 사이 로그아웃됨) 비교할 계정이
      // 없다 — user_id 비교를 건너뛰고 새 토큰을 그대로 저장하면 S6 방어가
      // 무력화된다. socialLogin을 부르기 전에 원래 오류를 그대로 던진다
      // (fix round 1).
      if (me == null) rethrow;

      final tokens = await _ref.read(authApiProvider).socialLogin(credential);
      if (tokens.userId != me.id) {
        // 다른 계정의 세션이다 — 여기 머물게 두면 안 되니 베스트 에포트로
        // 로그아웃시키고, 우리 쪽 토큰은 그대로 둔다(S6).
        try {
          await _ref.read(authApiProvider).logout(tokens.refreshToken);
        } catch (_) {
          // 통보 실패는 무시한다 — 어차피 우리 계정과 무관한 세션이다.
        }
        throw const ReauthMismatchException();
      }

      await _ref.read(tokenStoreProvider).save(
            access: tokens.accessToken,
            refresh: tokens.refreshToken,
          );

      return await action();
    }
  }
}

final reauthCoordinatorProvider = Provider<ReauthCoordinator>(
  (ref) => ReauthCoordinator(ref),
);
