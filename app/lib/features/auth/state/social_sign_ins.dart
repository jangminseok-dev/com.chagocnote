import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/proxy/providers.dart';
import '../api/apple_sign_in.dart';
import '../api/google_sign_in_adapter.dart';
import '../api/kakao_sign_in.dart';
import '../api/social_sign_in.dart';

/// 사용 가능한 소셜 로그인 구현체 목록. `AppConfig`(빌드 시 주입된 키)와
/// 플랫폼에 따라 달라진다 — 키가 없는 공급자는 목록에 아예 없다(예: 개발
/// 환경에서 키를 안 넣으면 개발용 로그인만 남는다). Apple은 안드로이드에서는
/// 웹 플로우가 되어 버려 제공하지 않는다 — iOS에서만 넣는다.
final socialSignInsProvider = Provider<List<SocialSignIn>>((ref) {
  final config = ref.watch(appConfigProvider);
  return [
    if (config.kakaoEnabled) const KakaoSignIn(),
    if (config.googleEnabled)
      GoogleSignInAdapter(
        clientId:
            config.googleIosClientId.isEmpty ? null : config.googleIosClientId,
        serverClientId: config.googleServerClientId,
      ),
    if (config.appleSignInEnabled &&
        defaultTargetPlatform == TargetPlatform.iOS)
      const AppleSignIn(),
  ];
});

/// 구글 로그인 수단을 해제한 뒤 구글 SDK 쪽 연결도 끊는다(베스트 에포트 —
/// 실패해도 해제 자체는 이미 서버에서 끝났으므로 삼킨다). 계정 화면과
/// 탈퇴 화면(Task 13)이 같은 로직을 공유하기 위해 여기 둔다.
Future<void> disconnectGoogle(Ref ref) async {
  for (final signIn in ref.read(socialSignInsProvider)) {
    if (signIn.provider != 'google') continue;
    try {
      await signIn.disconnect();
    } catch (_) {
      // 베스트 에포트 — 해제 자체는 이미 서버에서 끝났다.
    }
    return;
  }
}
