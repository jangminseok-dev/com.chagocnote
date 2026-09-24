import 'package:dio/dio.dart';

import '../error/api_exception.dart';

/// 서명(presigned) URL 로 파일을 올리는 전용 클라이언트.
///
/// [ApiClient]와 다른 점 세 가지가 이 클래스가 따로 있는 이유다.
/// - 인증 헤더가 없다. 서명 URL 이 곧 권한이라 액세스 토큰이 붙으면 저장소가 거절한다.
/// - 진행률([onSendProgress])을 준다. 사진·영상은 몇 초씩 걸린다.
/// - 재시도가 없다. 서명 URL 은 수명이 있어 다시 올릴지는 호출자가 정한다.
///
/// 오류는 [ApiException]으로 던진다(연결·타임아웃은 `NETWORK`, 저장소 거절은 상태 코드).
class UploadClient {
  UploadClient({Dio? dio})
    : _dio = dio ?? Dio(BaseOptions(connectTimeout: connectTimeout));

  /// 송신 타임아웃은 두지 않는다 — dio 의 송신 타임아웃은 바이트 전체에 걸려 큰 영상이
  /// 느린 망에서 끊긴다. 연결과 응답 대기만 제한한다.
  static const connectTimeout = Duration(seconds: 10);
  static const receiveTimeout = Duration(seconds: 30);

  final Dio _dio;

  /// [url]에 [body]를 PUT 한다. [length]는 바이트 수(서명에 들어가므로 정확해야 한다).
  Future<void> put(
    Uri url, {
    required Stream<List<int>> body,
    required int length,
    required String contentType,
    ProgressCallback? onSendProgress,
    CancelToken? cancelToken,
  }) async {
    try {
      await _dio.putUri<void>(
        url,
        data: body,
        options: Options(
          headers: {
            Headers.contentTypeHeader: contentType,
            Headers.contentLengthHeader: length,
          },
          receiveTimeout: receiveTimeout,
        ),
        onSendProgress: onSendProgress,
        cancelToken: cancelToken,
      );
    } on DioException catch (e) {
      throw ApiException.fromDioException(e);
    }
  }
}
