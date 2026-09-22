import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/social_sign_in.dart';

/// 사용 가능한 소셜 로그인 구현체 목록. 실제 카카오/구글/애플 구현체는
/// 이후 슬라이스에서 채운다 — 지금은 빈 목록이다.
final socialSignInsProvider = Provider<List<SocialSignIn>>((ref) => const []);

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
