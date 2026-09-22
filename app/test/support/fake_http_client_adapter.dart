import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

/// 하나의 가짜 응답 정의. [FakeHttpClientAdapter]의 핸들러가 이 값을 돌려주면
/// 그대로 [ResponseBody]로 바뀐다.
///
/// - `data`가 `Map`/`List`면 JSON으로 인코딩하고 `content-type: application/json`을 단다.
/// - `data`가 `String`이면 그대로 보내고, 기본 content-type은 `text/plain`이다
///   (JSON이 아닌 에러 바디를 흉내내려면 이 경로를 쓴다).
class FakeResponse {
  const FakeResponse({
    required this.statusCode,
    this.data,
    this.headers,
  });

  final int statusCode;
  final Object? data;
  final Map<String, List<String>>? headers;
}

typedef FakeHandler = FutureOr<FakeResponse> Function(
  RequestOptions options,
  Uint8List? body,
);

/// 네트워크 없이 dio를 구동하는 가짜 [HttpClientAdapter].
///
/// [handler]가 예외(특히 [DioException])를 던지면 그대로 위로 전파되어
/// dio가 실제 어댑터 오류처럼 처리한다 — 타임아웃/연결 오류를 흉내낼 때 쓴다.
class FakeHttpClientAdapter implements HttpClientAdapter {
  FakeHttpClientAdapter(this.handler);

  final FakeHandler handler;

  /// 어댑터를 거쳐간 모든 요청(원 요청 + 재시도 + 리프레시 포함), 도착 순서대로.
  final List<RequestOptions> requests = [];

  /// 경로별 마지막 요청 바디(원문 바이트). DELETE 바디 전송 검증 등에 쓴다.
  final Map<String, Uint8List> lastBodyByPath = {};

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);

    Uint8List? bytes;
    if (requestStream != null) {
      final chunks = <int>[];
      await for (final chunk in requestStream) {
        chunks.addAll(chunk);
      }
      bytes = Uint8List.fromList(chunks);
      lastBodyByPath[options.path] = bytes;
    }

    final result = await handler(options, bytes);

    final headers = <String, List<String>>{...?result.headers};
    final data = result.data;
    if (data == null) {
      return ResponseBody.fromBytes(
        const <int>[],
        result.statusCode,
        headers: headers,
      );
    }
    if (data is String) {
      headers.putIfAbsent(
        'content-type',
        () => const ['text/plain; charset=utf-8'],
      );
      return ResponseBody.fromString(
        data,
        result.statusCode,
        headers: headers,
      );
    }
    headers['content-type'] = const ['application/json; charset=utf-8'];
    return ResponseBody.fromString(
      jsonEncode(data),
      result.statusCode,
      headers: headers,
    );
  }

  @override
  void close({bool force = false}) {}
}
