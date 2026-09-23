import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _error(String code, {String message = '서버 문구', int? status = 400}) =>
    ApiException(statusCode: status, code: code, message: message);

void main() {
  test('아는 코드는 서버 문구가 아니라 앱의 문구를 쓴다', () {
    expect(messageFor(_error('INVITE_EXPIRED')), '만료된 초대 코드입니다. 새 코드를 받아 주세요.');
    expect(messageFor(_error('REAUTH_REQUIRED', status: 403)), '보안을 위해 다시 로그인해 주세요.');
  });

  test('IDENTITY_ALREADY_LINKED 는 그 계정에서 탈퇴한 뒤 다시 연결하라고 안내한다(설계 5.6)', () {
    expect(
      messageFor(_error('IDENTITY_ALREADY_LINKED', status: 409)),
      '다른 계정에 연결된 로그인 수단입니다. 그 계정에서 탈퇴한 뒤 다시 연결해 주세요.',
    );
  });

  test('모르는 코드는 서버 문구를 쓴다', () {
    expect(messageFor(_error('SOMETHING_NEW', message: '새로 생긴 안내')), '새로 생긴 안내');
  });

  test('형식을 모르는 응답과 예외가 아닌 오류는 일반 문구다', () {
    const fallback = '문제가 생겼습니다. 잠시 뒤에 다시 시도해 주세요.';
    expect(messageFor(_error('HTTP_ERROR', message: '상태 코드 500 응답을 처리할 수 없습니다.')), fallback);
    expect(messageFor(StateError('x')), fallback);
  });

  test('네트워크 오류는 다시 시도를 안내한다', () {
    expect(messageFor(ApiException.network('timeout')), contains('다시 시도'));
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
}
