import 'api_exception.dart';

/// 서버 오류 코드를 사용자에게 보여 줄 한국어 문구로 바꾼다.
///
/// 문구는 서버의 `message` 가 아니라 `code` 로 고른다. 모르는 코드일 때만 서버 문구를 쓴다.
const Map<String, String> _messages = {
  'NETWORK': '네트워크 연결을 확인하고 다시 시도해 주세요.',
  'UNAUTHENTICATED': '보안을 위해 다시 로그인해 주세요.',
  'REAUTH_REQUIRED': '보안을 위해 다시 로그인해 주세요.',
  'PROVIDER_VERIFICATION_FAILED': '로그인 정보를 확인하지 못했습니다. 다시 시도해 주세요.',
  'PROVIDER_NOT_SUPPORTED': '지원하지 않는 로그인 방식입니다.',
  'ACCOUNT_SUSPENDED': '이용이 정지된 계정입니다. 고객센터에 문의해 주세요.',
  'NOT_A_MEMBER': '이 매장의 멤버가 아니거나 역할이 바뀌었습니다.',
  'PERMISSION_DENIED': '이 작업을 할 권한이 없습니다.',
  'SHOP_CLOSED': '닫힌 매장입니다.',
  'SHOP_SUSPENDED': '이용이 정지된 매장입니다.',
  'MEMBER_NOT_FOUND': '멤버를 찾을 수 없습니다.',
  'IDENTITY_NOT_FOUND': '연결되어 있지 않은 로그인 수단입니다.',
  'INVITE_INVALID': '초대 코드를 확인해 주세요.',
  'INVITE_EXPIRED': '만료된 초대 코드입니다. 새 코드를 받아 주세요.',
  'INVITE_EXHAUSTED': '이미 사용된 초대 코드입니다. 새 코드를 받아 주세요.',
  'LAST_OWNER': '매장에는 사장이 한 명 이상 있어야 합니다.',
  'ALREADY_A_MEMBER': '이미 이 매장의 멤버입니다.',
  'IDENTITY_ALREADY_LINKED': '다른 계정에 연결된 로그인 수단입니다. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
  'PROVIDER_ALREADY_LINKED': '같은 종류의 로그인 수단이 이미 연결되어 있습니다.',
  'LAST_IDENTITY': '마지막 로그인 수단은 해제할 수 없습니다.',
  'OWNERSHIP_TRANSFER_REQUIRED': '혼자 사장인 매장에 다른 멤버가 있습니다. 먼저 다른 사장을 지정해 주세요.',
  'SHOP_CLOSE_CONFIRM_REQUIRED': '탈퇴하면 혼자 운영하는 매장도 함께 닫힙니다.',
  'VALIDATION_ERROR': '입력한 내용을 확인해 주세요.',
  'TOO_MANY_ATTEMPTS': '시도가 너무 잦습니다. 잠시 뒤에 다시 해 주세요.',
};

const String _fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';

/// 어떤 오류든 화면에 보여 줄 문구 한 줄로 바꾼다.
String messageFor(Object error) {
  if (error is! ApiException) return _fallback;
  final known = _messages[error.code];
  if (known != null) return known;
  // HTTP_ERROR 는 서버가 {code, message} 를 주지 못한 경우라 기술적인 문구다. 보여 주지 않는다.
  if (error.code == 'HTTP_ERROR' || error.message.isEmpty) return _fallback;
  return error.message;
}
