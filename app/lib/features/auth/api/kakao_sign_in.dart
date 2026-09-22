import 'package:flutter/services.dart';
import 'package:kakao_flutter_sdk_user/kakao_flutter_sdk_user.dart';

import 'social_sign_in.dart';

/// 카카오 로그인 어댑터. 카카오톡 앱이 있으면 앱 전환(`loginWithKakaoTalk`)으로,
/// 없으면 SDK의 시스템 인증 세션(`loginWithKakaoAccount`, iOS는
/// `ASWebAuthenticationSession`, 인앱 웹뷰가 아니다)으로 로그인한다.
///
/// 취소 신호가 흐름마다 다르다(SDK 소스로 직접 확인):
/// - 카카오톡 앱 전환 취소: `PlatformException(code: 'CANCELED')`
///   (android/ios 네이티브가 공통으로 이 코드를 보낸다).
/// - 카카오계정 동의 화면 취소: `KakaoAuthException(error:
///   AuthErrorCause.accessDenied)`.
/// - `KakaoClientException(reason: ClientErrorCause.cancelled)`도 SDK가
///   일반적인 취소 신호로 정의해 두어서, 혹시 모를 경우를 대비해 함께 잡는다.
class KakaoSignIn implements SocialSignIn {
  const KakaoSignIn();

  @override
  String get provider => 'kakao';

  @override
  Future<SocialCredential?> signIn() async {
    try {
      final installed = await isKakaoTalkInstalled();
      final token = installed
          ? await UserApi.instance.loginWithKakaoTalk()
          : await UserApi.instance.loginWithKakaoAccount();
      return SocialCredential(provider: provider, token: token.accessToken);
    } on PlatformException catch (e) {
      if (e.code == 'CANCELED') return null;
      rethrow;
    } on KakaoAuthException catch (e) {
      if (e.error == AuthErrorCause.accessDenied) return null;
      rethrow;
    } on KakaoClientException catch (e) {
      if (e.reason == ClientErrorCause.cancelled) return null;
      rethrow;
    }
  }

  @override
  Future<void> disconnect() async {
    // 카카오는 서버가 관리자 키로 연결을 끊으므로 앱에서는 할 일이 없다.
  }
}
