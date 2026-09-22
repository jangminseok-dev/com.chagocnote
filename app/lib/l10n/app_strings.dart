/// 앱 전체에서 쓰는 사용자 노출 문자열. 전부 한국어다.
///
/// 화면은 이 파일의 상수만 쓰고, 문자열을 직접 쓰지 않는다. 오류 문구는
/// `messageFor`(`core/error/error_messages.dart`)를 대신 쓴다.
class AppStrings {
  const AppStrings._();

  static const appName = '차곡노트';
  static const retry = '다시 시도';

  // 로그인
  static const continueWithKakao = '카카오로 계속하기';
  static const continueWithGoogle = 'Google로 계속하기';
  static const continueWithApple = 'Apple로 계속하기';
  static const devNameLabel = '이름';
  static const devSignIn = '개발용 로그인';
  static const devNameRequired = '이름을 입력해 주세요.';
  static const sessionExpiredBanner = '보안을 위해 다시 로그인해 주세요.';

  // 초대 코드
  static const inviteCodeLabel = '초대 코드';
  static const inviteCodeRequired = '초대 코드를 입력해 주세요.';
  static const inviteSubmit = '참여하기';
  static const accountSettings = '계정 설정';
  static const logout = '로그아웃';

  // 매장 선택
  static const selectShopTitle = '매장 선택';
  static const roleOwner = '사장';
  static const roleStaff = '직원';
}
