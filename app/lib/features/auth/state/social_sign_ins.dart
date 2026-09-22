import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/social_sign_in.dart';

/// 사용 가능한 소셜 로그인 구현체 목록. 실제 카카오/구글/애플 구현체는
/// 이후 슬라이스에서 채운다 — 지금은 빈 목록이다.
final socialSignInsProvider = Provider<List<SocialSignIn>>((ref) => const []);
