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

  /// disconnect() 가 호출된 횟수. 계정 화면의 구글 해제 후 베스트 에포트
  /// 연결 끊기를 검증하는 데 쓴다.
  int disconnectCallCount = 0;
  Object? disconnectError;

  @override
  Future<SocialCredential?> signIn() async {
    signInCallCount++;
    if (signInError != null) throw signInError!;
    return credentialToReturn;
  }

  @override
  Future<void> disconnect() async {
    disconnectCallCount++;
    if (disconnectError != null) throw disconnectError!;
  }
}
