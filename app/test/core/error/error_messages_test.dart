import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _error(String code, {String message = '서버 문구', int? status = 400}) =>
    ApiException(statusCode: status, code: code, message: message);

void main() {
  test('아는 코드는 서버 문구가 아니라 앱의 문구를 쓴다', () {
    expect(messageFor(_error('INVITE_EXPIRED')), '만료된 초대 코드예요. 새 코드를 받아 주세요.');
    expect(messageFor(_error('REAUTH_REQUIRED', status: 403)), '보안을 위해 다시 로그인해 주세요.');
  });

  test('IDENTITY_ALREADY_LINKED 는 그 계정에서 탈퇴한 뒤 다시 연결하라고 안내한다(설계 5.6)', () {
    expect(
      messageFor(_error('IDENTITY_ALREADY_LINKED', status: 409)),
      '다른 계정에 연결된 로그인 수단이에요. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
    );
  });

  test('모르는 코드는 서버 문구를 쓴다', () {
    expect(messageFor(_error('SOMETHING_NEW', message: '새로 생긴 안내')), '새로 생긴 안내');
  });

  test('예외가 아닌 오류와 문구가 빈 오류는 일반 문구다', () {
    const fallback = '문제가 생겼어요. 잠시 뒤에 다시 시도해 주세요.';
    expect(messageFor(StateError('x')), fallback);
    expect(messageFor(_error('SOMETHING_NEW', message: '')), fallback);
  });

  test('서버 오류(5xx·형식을 모르는 응답)는 서버 문구다', () {
    const server = '서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.';
    expect(messageFor(_error('HTTP_ERROR', message: '상태 코드 502 응답을 처리할 수 없습니다.', status: 502)), server);
    expect(messageFor(_error('INTERNAL', status: 500)), server);
    expect(loadMessageFor(_error('INTERNAL', status: 500)), server);
  });

  test('인터넷 없음은 누른 일이면 연결 확인을, 화면을 불러올 때면 스스로 다시 불러온다고 안내한다', () {
    expect(messageFor(ApiException.network('timeout')), '인터넷에 연결되지 않았어요. 연결을 확인해 주세요.');
    expect(loadMessageFor(ApiException.network('timeout')), '인터넷에 연결되지 않았어요. 연결되면 다시 불러올게요.');
  });

  test('권한·없음·업무 오류는 불러올 때도 코드별 문구다', () {
    expect(loadMessageFor(_error('VISIT_NOT_FOUND', status: 404)), '방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.');
    expect(loadMessageFor(_error('PERMISSION_DENIED', status: 403)), '이 작업을 할 권한이 없어요.');
  });

  test('설계 문서 7절의 코드는 모두 앱의 문구가 있다', () {
    const codes = [
      'UNAUTHENTICATED', 'LAST_OWNER', 'ALREADY_A_MEMBER', 'NOT_A_MEMBER', 'PERMISSION_DENIED',
      'ACCOUNT_SUSPENDED', 'SHOP_CLOSED', 'SHOP_SUSPENDED', 'MEMBER_NOT_FOUND', 'IDENTITY_NOT_FOUND',
      'INVITE_INVALID', 'INVITE_EXPIRED', 'INVITE_EXHAUSTED', 'IDENTITY_ALREADY_LINKED',
      'PROVIDER_ALREADY_LINKED', 'LAST_IDENTITY', 'OWNERSHIP_TRANSFER_REQUIRED',
      'SHOP_CLOSE_CONFIRM_REQUIRED', 'TOO_MANY_ATTEMPTS', 'PROVIDER_VERIFICATION_FAILED',
      'REAUTH_REQUIRED', 'VALIDATION_ERROR', 'PROVIDER_NOT_SUPPORTED',
    ];
    for (final code in codes) {
      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
    }
  });

  test('고객·반려동물 코드(설계 5절)는 모두 앱의 문구가 있다', () {
    const codes = [
      'CUSTOMER_NOT_FOUND', 'PET_NOT_FOUND', 'CUSTOMER_PHONE_TAKEN', 'LAST_PET',
      'PET_HEALTH_REQUIRED', 'PET_HEALTH_CONFLICT',
    ];
    for (final code in codes) {
      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
    }
    expect(messageFor(_error('LAST_PET', status: 409)), contains('고객 삭제'));
  });

  test('예약·방문 코드(설계 8절)는 모두 앱의 문구가 있다', () {
    const codes = [
      'VISIT_NOT_FOUND', 'VISIT_STATE_CONFLICT', 'VISIT_NOT_YET', 'VISIT_DUPLICATE',
      'VISIT_CROSSES_MIDNIGHT', 'VISIT_GROUP_MISMATCH', 'PET_PASSED_AWAY', 'MENU_NOT_FOUND',
      'MENU_NAME_TAKEN', 'PET_HAS_VISITS', 'PET_HAS_UPCOMING_VISITS', 'CUSTOMER_HAS_UPCOMING_VISITS',
    ];
    for (final code in codes) {
      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
    }
    expect(messageFor(_error('VISIT_CROSSES_MIDNIGHT', status: 422)), contains('소요'));
    expect(messageFor(_error('PET_HAS_VISITS', status: 409)), contains('무지개다리'));
  });

  test('기록·사진 코드(④ 설계 9절)는 모두 앱의 문구가 있다', () {
    const codes = [
      'VISIT_NO_RECORD_YET', 'RECORD_NOT_FOUND', 'RECORD_VERSION_CONFLICT', 'RECORD_WEIGHT_WITHOUT_PET',
      'RECORD_ITEM_DUPLICATE', 'MEDIA_NOT_FOUND', 'MEDIA_NOT_UPLOADED', 'MEDIA_NOT_READY',
      'MEDIA_ALREADY_ATTACHED', 'MEDIA_TOO_LARGE', 'MEDIA_TYPE_UNSUPPORTED', 'MEDIA_LIMIT_EXCEEDED',
    ];
    for (final code in codes) {
      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
    }
  });

  test('알림장 코드(⑤ 설계 6.1·6.2)는 모두 앱의 문구가 있다 — VISIT_REPORT_SENT 는 설계 9.3 의 글자 그대로', () {
    const codes = ['VISIT_REPORT_SENT', 'VISIT_NOT_COMPLETED', 'REPORT_EMPTY', 'REPORT_NOT_FOUND'];
    for (final code in codes) {
      expect(messageFor(_error(code, message: '서버 문구')), isNot('서버 문구'), reason: code);
    }
    expect(messageFor(_error('VISIT_REPORT_SENT', status: 409)), '알림장을 보낸 방문이에요. 링크를 먼저 끊어 주세요.');
  });

  test('크기·한도 문구는 사진과 영상을 함께 안내한다 — 코드 하나를 둘이 같이 쓴다', () {
    expect(messageFor(_error('MEDIA_TOO_LARGE', status: 422)), '사진은 20MB, 영상은 200MB까지 올릴 수 있어요.');
    expect(
      messageFor(_error('MEDIA_LIMIT_EXCEEDED', status: 422)),
      '방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있어요.',
    );
  });
}
