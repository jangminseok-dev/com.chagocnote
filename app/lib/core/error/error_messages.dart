import 'api_exception.dart';
import 'error_kind.dart';

/// 서버 오류 코드를 사용자에게 보여 줄 한국어 문구(해요체)로 바꾼다.
///
/// 문구는 서버의 `message` 가 아니라 `code` 로 고른다. 모르는 코드일 때만 서버 문구를 쓴다.
const Map<String, String> _messages = {
  'UNAUTHENTICATED': '보안을 위해 다시 로그인해 주세요.',
  'REAUTH_REQUIRED': '보안을 위해 다시 로그인해 주세요.',
  'PROVIDER_VERIFICATION_FAILED': '로그인 정보를 확인하지 못했어요. 다시 시도해 주세요.',
  'PROVIDER_NOT_SUPPORTED': '지원하지 않는 로그인 방식이에요.',
  'ACCOUNT_SUSPENDED': '이용이 정지된 계정이에요. 고객센터에 문의해 주세요.',
  'NOT_A_MEMBER': '이 매장의 멤버가 아니거나 역할이 바뀌었어요.',
  'PERMISSION_DENIED': '이 작업을 할 권한이 없어요.',
  'SHOP_CLOSED': '닫힌 매장이에요.',
  'SHOP_SUSPENDED': '이용이 정지된 매장이에요.',
  'MEMBER_NOT_FOUND': '멤버를 찾을 수 없어요.',
  'IDENTITY_NOT_FOUND': '연결되어 있지 않은 로그인 수단이에요.',
  'INVITE_INVALID': '초대 코드를 확인해 주세요.',
  'INVITE_EXPIRED': '만료된 초대 코드예요. 새 코드를 받아 주세요.',
  'INVITE_EXHAUSTED': '이미 사용된 초대 코드예요. 새 코드를 받아 주세요.',
  'LAST_OWNER': '매장에는 사장이 한 명 이상 있어야 해요.',
  'ALREADY_A_MEMBER': '이미 이 매장의 멤버예요.',
  'IDENTITY_ALREADY_LINKED': '다른 계정에 연결된 로그인 수단이에요. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
  'PROVIDER_ALREADY_LINKED': '같은 종류의 로그인 수단이 이미 연결되어 있어요.',
  'LAST_IDENTITY': '마지막 로그인 수단은 해제할 수 없어요.',
  'OWNERSHIP_TRANSFER_REQUIRED': '혼자 사장인 매장에 다른 멤버가 있어요. 먼저 다른 사장을 지정해 주세요.',
  'SHOP_CLOSE_CONFIRM_REQUIRED': '탈퇴하면 혼자 운영하는 매장도 함께 닫혀요.',
  'VALIDATION_ERROR': '입력한 내용을 확인해 주세요.',
  'TOO_MANY_ATTEMPTS': '시도가 너무 잦아요. 잠시 뒤에 다시 해 주세요.',
  'CUSTOMER_NOT_FOUND': '고객을 찾을 수 없어요. 이미 삭제되었을 수 있어요.',
  'PET_NOT_FOUND': '반려동물을 찾을 수 없어요. 이미 삭제되었을 수 있어요.',
  'CUSTOMER_PHONE_TAKEN': '이미 등록된 전화번호예요.',
  'LAST_PET': '마지막 반려동물은 삭제할 수 없어요. 고객 삭제를 이용해 주세요.',
  'PET_HEALTH_REQUIRED': '질병을 고르거나 "질병 없음"을 눌러 주세요.',
  'PET_HEALTH_CONFLICT': '질병과 "질병 없음"을 함께 고를 수 없어요.',
  'PET_HAS_VISITS': '방문 기록이 있는 반려동물은 삭제할 수 없어요. 무지개다리 표시를 이용해 주세요.',
  'PET_HAS_UPCOMING_VISITS': '앞으로의 예약이 있어요. 예약을 먼저 취소해 주세요.',
  'CUSTOMER_HAS_UPCOMING_VISITS': '앞으로의 예약이 있는 고객은 삭제할 수 없어요. 예약을 먼저 취소해 주세요.',
  'PET_PASSED_AWAY': '무지개다리를 건넌 반려동물은 예약할 수 없어요.',
  'VISIT_NOT_FOUND': '방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.',
  'VISIT_STATE_CONFLICT': '다른 기기에서 먼저 바뀌었어요. 화면을 새로 불러왔어요.',
  'VISIT_NOT_YET': '아직 할 수 없어요. 예약한 날(노쇼는 예약 시각)이 지나야 해요.',
  'VISIT_DUPLICATE': '이미 저장된 예약이에요.',
  'VISIT_CROSSES_MIDNIGHT': '끝나는 시각이 자정을 넘어요. 소요를 줄여 주세요.',
  'VISIT_GROUP_MISMATCH': '같은 보호자의 방문만 함께 바꿀 수 있어요.',
  'MENU_NOT_FOUND': '없거나 보관된 메뉴예요. 메뉴를 다시 골라 주세요.',
  'MENU_NAME_TAKEN': '같은 이름의 메뉴가 이미 있어요.',
  // 미용 기록·사진(④ 설계 9절)
  'VISIT_NO_RECORD_YET': '미용을 시작한 방문에만 기록을 쓸 수 있어요.',
  'RECORD_NOT_FOUND': '기록이 없어요. 이미 지워졌을 수 있어요.',
  'RECORD_VERSION_CONFLICT': '다른 기기에서 기록이 먼저 바뀌었어요. 화면을 새로 불러왔어요.',
  'RECORD_WEIGHT_WITHOUT_PET': '보호자만의 방문에는 몸무게를 적을 수 없어요.',
  'RECORD_ITEM_DUPLICATE': '같은 메뉴를 두 번 적을 수 없어요.',
  'MEDIA_NOT_FOUND': '사진을 찾을 수 없어요. 다시 올려 주세요.',
  'MEDIA_NOT_UPLOADED': '사진이 아직 다 올라가지 않았어요.',
  'MEDIA_NOT_READY': '사진이 아직 다 올라가지 않았어요.',
  'MEDIA_ALREADY_ATTACHED': '이미 다른 기록에 붙은 사진이에요.',
  'MEDIA_TOO_LARGE': '사진은 20MB, 영상은 200MB까지 올릴 수 있어요.',
  'MEDIA_TYPE_UNSUPPORTED': '올릴 수 없는 형식의 파일이에요.',
  'MEDIA_LIMIT_EXCEEDED': '방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있어요.',
  // 미용 알림장(⑤ 설계 6.1·6.2)
  'VISIT_REPORT_SENT': '알림장을 보낸 방문이에요. 링크를 먼저 끊어 주세요.',
  'VISIT_NOT_COMPLETED': '완료한 방문만 알림장을 보낼 수 있어요.',
  'REPORT_EMPTY': '보여 줄 사진·영상이나 케어 메모가 있어야 보낼 수 있어요.',
  'REPORT_NOT_FOUND': '이미 닫힌 알림장이에요.',
  // 앱이 만든 코드 — 영상 재생이 서명 URL 만료(403)로 실패했다(④-3a 설계 5.4).
  'MEDIA_URL_EXPIRED': '보기 링크가 만료됐어요. 다시 시도해 주세요.',
};

/// 인터넷 없음 — 누른 일(저장·삭제 등)이 실패했을 때.
const String offlineActionMessage = '인터넷에 연결되지 않았어요. 연결을 확인해 주세요.';

/// 인터넷 없음 — 화면을 불러오지 못했을 때. 인터넷이 돌아오면 화면이 스스로 다시 불러온다.
const String offlineLoadMessage = '인터넷에 연결되지 않았어요. 연결되면 다시 불러올게요.';

/// 인터넷 없음 — 받은 데이터 위의 띠.
const String offlineBannerMessage = '인터넷에 연결되지 않았어요 · 이전 내용이에요';

const String _server = '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.';

const String _fallback = '문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.';

/// 누른 일이 실패했을 때 보일 문구 한 줄.
String messageFor(Object error) => _message(error, offlineActionMessage);

/// 화면을 불러오지 못했을 때 보일 문구 한 줄(`AsyncBody`·스플래시).
String loadMessageFor(Object error) => _message(error, offlineLoadMessage);

String _message(Object error, String offline) {
  switch (kindOf(error)) {
    case ErrorKind.offline:
      return offline;
    case ErrorKind.server:
      return _server;
    case ErrorKind.denied:
    case ErrorKind.gone:
    case ErrorKind.other:
      break;
  }
  if (error is! ApiException) return _fallback;
  final known = _messages[error.code];
  if (known != null) return known;
  if (error.message.isEmpty) return _fallback;
  return error.message;
}
