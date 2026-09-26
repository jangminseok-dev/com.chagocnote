import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_kind.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _error(String code, int? status) =>
    ApiException(statusCode: status, code: code, message: '서버 문구');

void main() {
  test('인터넷 없음·시간 초과는 offline 이다', () {
    expect(kindOf(ApiException.network('timeout')), ErrorKind.offline);
  });

  test('5xx 와 형식을 모르는 응답은 server 다', () {
    expect(kindOf(_error('INTERNAL', 500)), ErrorKind.server);
    expect(kindOf(_error('HTTP_ERROR', 502)), ErrorKind.server);
    expect(kindOf(_error('HTTP_ERROR', 413)), ErrorKind.server);
  });

  test('403 은 denied, 404 는 gone 이다 — 다시 해도 같다', () {
    expect(kindOf(_error('PERMISSION_DENIED', 403)), ErrorKind.denied);
    expect(kindOf(_error('VISIT_NOT_FOUND', 404)), ErrorKind.gone);
    expect(ErrorKind.denied.retryable, isFalse);
    expect(ErrorKind.gone.retryable, isFalse);
  });

  test('업무 규칙 4xx 와 ApiException 이 아닌 오류는 other 다', () {
    expect(kindOf(_error('VISIT_STATE_CONFLICT', 409)), ErrorKind.other);
    expect(kindOf(_error('VALIDATION_ERROR', 422)), ErrorKind.other);
    expect(kindOf(StateError('x')), ErrorKind.other);
    for (final kind in [ErrorKind.offline, ErrorKind.server, ErrorKind.other]) {
      expect(kind.retryable, isTrue, reason: kind.name);
    }
  });
}
