import 'package:dio/dio.dart';

/// 서버·네트워크에서 발생한 오류를 통일된 형태로 감싼다.
///
/// 서버 오류 바디는 `{"code": "...", "message": "..."}` 형태를 따른다.
/// 이 형태로 파싱되지 않으면 `HTTP_ERROR`로, 연결/타임아웃류 오류는
/// `NETWORK`로, 호출자가 취소한 요청은 `CANCELLED`로 코드를 매긴다.
class ApiException implements Exception {
  ApiException({
    required this.statusCode,
    required this.code,
    required this.message,
    this.sessionEnded = false,
    this.timedOut = false,
  });

  /// 네트워크 오류(연결 실패, 타임아웃)를 나타내는 [ApiException]을 만든다.
  /// 타임아웃이면 [timedOut]을 켠다 — 코드는 둘 다 `NETWORK`다(백엔드에 닿지 못한 것은 같다).
  factory ApiException.network(String message, {bool timedOut = false}) =>
      ApiException(
        statusCode: null,
        code: 'NETWORK',
        message: message,
        timedOut: timedOut,
      );

  /// [DioException]으로부터 [ApiException]을 만든다.
  factory ApiException.fromDioException(DioException error) {
    // 취소는 오류가 아니다(사용자가 업로드를 뺐다). 화면은 [isCancelled]면 아무 문구도 띄우지 않는다.
    if (error.type == DioExceptionType.cancel) {
      return ApiException(statusCode: null, code: 'CANCELLED', message: '취소했습니다.');
    }
    if (_isNetworkType(error.type)) {
      return ApiException.network(
        error.message ?? '네트워크 오류가 발생했습니다.',
        timedOut: _isTimeoutType(error.type),
      );
    }

    final response = error.response;
    if (response == null) {
      return ApiException.network(error.message ?? '네트워크 오류가 발생했습니다.');
    }

    return ApiException.fromResponseData(
      statusCode: response.statusCode,
      data: response.data,
    );
  }

  /// 응답 바디에서 `{code, message}`를 파싱한다. 실패하면 `HTTP_ERROR`로 대체한다.
  factory ApiException.fromResponseData({
    required int? statusCode,
    required Object? data,
  }) {
    if (data is Map) {
      final code = data['code'];
      final message = data['message'];
      if (code is String && message is String) {
        return ApiException(
          statusCode: statusCode,
          code: code,
          message: message,
        );
      }
    }
    return ApiException(
      statusCode: statusCode,
      code: 'HTTP_ERROR',
      message: '상태 코드 $statusCode 응답을 처리할 수 없습니다.',
    );
  }

  /// 연결은 됐는데 정해진 시간 안에 답이 없었다(연결·송신·수신 타임아웃).
  static bool _isTimeoutType(DioExceptionType type) {
    switch (type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return true;
      case DioExceptionType.connectionError:
      case DioExceptionType.badCertificate:
      case DioExceptionType.badResponse:
      case DioExceptionType.cancel:
      case DioExceptionType.unknown:
      case DioExceptionType.transformTimeout:
        return false;
    }
  }

  static bool _isNetworkType(DioExceptionType type) {
    switch (type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
      case DioExceptionType.connectionError:
        return true;
      case DioExceptionType.badCertificate:
      case DioExceptionType.badResponse:
      case DioExceptionType.cancel:
      case DioExceptionType.unknown:
      case DioExceptionType.transformTimeout:
        return false;
    }
  }

  final int? statusCode;
  final String code;
  final String message;

  /// `ApiClient` 가 이 요청의 갱신 실패(서버 거절·처리 실패)를 보고 이 기기의
  /// 세션을 끝냈으면 true. 그때의 401 은 "요청이 이미 처리됐다"가 아니라
  /// "세션이 만료됐다"는 뜻이다 — 예를 들어 탈퇴는 이 401 을 완료로 보지 않는다.
  final bool sessionEnded;

  /// 네트워크 오류 가운데 시간 초과인 것. 연결은 있으니 화면은 서버 문구와 [다시 시도]를 주고
  /// 인터넷 복귀를 기다리지 않는다(`kindOf`). 토큰 갱신·대기열은 [isNetwork]만 본다.
  final bool timedOut;

  bool get isNetwork => code == 'NETWORK';

  bool get isCancelled => code == 'CANCELLED';

  @override
  String toString() => 'ApiException(statusCode: $statusCode, code: $code, message: $message)';
}
