import 'package:chagocnote/core/error/api_exception.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final options = RequestOptions(path: '/v1/x');

  test('연결 실패는 NETWORK 이고 시간 초과가 아니다', () {
    final e = ApiException.fromDioException(
      DioException.connectionError(requestOptions: options, reason: '끊김'),
    );
    expect(e.code, 'NETWORK');
    expect(e.isNetwork, isTrue);
    expect(e.timedOut, isFalse);
  });

  test('연결·송신·수신 시간 초과는 NETWORK 이면서 timedOut 이다 — 백엔드에 닿지 못한 것은 같다', () {
    final errors = [
      DioException.connectionTimeout(requestOptions: options, timeout: const Duration(seconds: 10)),
      DioException.sendTimeout(requestOptions: options, timeout: const Duration(seconds: 10)),
      DioException.receiveTimeout(requestOptions: options, timeout: const Duration(seconds: 30)),
    ];
    for (final dio in errors) {
      final e = ApiException.fromDioException(dio);
      expect(e.code, 'NETWORK', reason: dio.type.name);
      expect(e.isNetwork, isTrue, reason: dio.type.name);
      expect(e.timedOut, isTrue, reason: dio.type.name);
    }
  });

  test('취소는 CANCELLED, 응답이 있으면 바디의 코드다', () {
    final cancelled = ApiException.fromDioException(
      DioException.requestCancelled(requestOptions: options, reason: 'x'),
    );
    expect(cancelled.isCancelled, isTrue);
    expect(cancelled.timedOut, isFalse);

    final rejected = ApiException.fromDioException(
      DioException.badResponse(
        statusCode: 409,
        requestOptions: options,
        response: Response(
          requestOptions: options,
          statusCode: 409,
          data: {'code': 'VISIT_STATE_CONFLICT', 'message': '어긋났어요.'},
        ),
      ),
    );
    expect(rejected.code, 'VISIT_STATE_CONFLICT');
    expect(rejected.statusCode, 409);
    expect(rejected.timedOut, isFalse);
  });
}
