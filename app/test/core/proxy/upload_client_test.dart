import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/upload_client.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_http_client_adapter.dart';

final _url = Uri.parse('https://media.example/bucket/key?X-Amz-Signature=abc');
final _bytes = Uint8List.fromList(List<int>.generate(2048, (i) => i % 251));

({UploadClient client, FakeHttpClientAdapter adapter}) _setUp(
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  return (client: UploadClient(dio: dio), adapter: adapter);
}

void main() {
  test('PUT 은 인증 헤더 없이 바디·content-type·길이를 보내고 진행률을 알린다', () async {
    final setup = _setUp(
      (options, body) => const FakeResponse(statusCode: 200),
    );
    final progress = <(int, int)>[];

    await setup.client.put(
      _url,
      body: Stream.value(_bytes),
      length: _bytes.length,
      contentType: 'image/jpeg',
      onSendProgress: (sent, total) => progress.add((sent, total)),
    );

    final request = setup.adapter.requests.single;
    expect(request.method, 'PUT');
    expect(request.uri, _url);
    expect(
      request.headers.keys.map((k) => k.toLowerCase()),
      isNot(contains('authorization')),
    );
    expect(request.headers[Headers.contentTypeHeader], 'image/jpeg');
    expect(request.headers[Headers.contentLengthHeader], _bytes.length);
    expect(setup.adapter.lastBodyByPath[request.path], _bytes);
    expect(progress, isNotEmpty);
    expect(progress.last, (_bytes.length, _bytes.length));
  });

  test('저장소가 거절하면 ApiException 으로 던지고 다시 보내지 않는다', () async {
    final setup = _setUp(
      (options, body) => const FakeResponse(
        statusCode: 403,
        data: '<Error><Code>AccessDenied</Code></Error>',
      ),
    );

    await expectLater(
      setup.client.put(
        _url,
        body: Stream.value(_bytes),
        length: _bytes.length,
        contentType: 'image/jpeg',
      ),
      throwsA(
        isA<ApiException>().having((e) => e.statusCode, 'statusCode', 403),
      ),
    );
    expect(setup.adapter.requests, hasLength(1));
  });

  test('연결 오류는 NETWORK 로 던진다', () async {
    final setup = _setUp(
      (options, body) => throw DioException.connectionError(
        requestOptions: options,
        reason: '끊김',
      ),
    );

    await expectLater(
      setup.client.put(
        _url,
        body: Stream.value(_bytes),
        length: _bytes.length,
        contentType: 'video/mp4',
      ),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'NETWORK')),
    );
  });
}
