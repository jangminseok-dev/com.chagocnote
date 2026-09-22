import 'package:chagocnote/features/auth/api/social_sign_in.dart';

/// 테스트 전용 [SocialSignIn]. `signIn()`이 몇 번 호출됐는지와, 무엇을
/// 돌려줄지(취소=null, 성공=credential, 실패=예외)를 필드로 기록·조작한다.
class FakeSocialSignIn implements SocialSignIn {
  FakeSocialSignIn(this.provider);

  @override
  final String provider;

  int signInCallCount = 0;
  SocialCredential? credentialToReturn;
  Object? signInError;

  @override
  Future<SocialCredential?> signIn() async {
    signInCallCount++;
    if (signInError != null) throw signInError!;
    return credentialToReturn;
  }

  @override
  Future<void> disconnect() async {}
}
