import 'dart:convert';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/visit/api/media_api.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

({MediaApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: dio);
  return (api: MediaApi(client), adapter: adapter);
}

void main() {
  test('사진 발급은 JPEG·바이트 수·가로세로를 보내고 올릴 곳 셋을 받는다', () async {
    final s = _build(
      (options, body) =>
          FakeResponse(statusCode: 201, data: issuedUploadJson(mediaId: 51)),
    );

    final issued = await s.api.issuePhoto(
      3,
      byteSize: 1834221,
      width: 3000,
      height: 2000,
    );

    expect(s.adapter.requests.last.path, '/v1/shops/3/media/uploads');
    expect(
      jsonDecode(
        utf8.decode(s.adapter.lastBodyByPath['/v1/shops/3/media/uploads']!),
      ),
      {
        'kind': 'photo',
        'content_type': 'image/jpeg',
        'byte_size': 1834221,
        'width': 3000,
        'height': 2000,
      },
    );
    expect(issued.mediaId, 51);
    expect(issued.puts.original, contains('original/shops/3/51.jpg'));
    expect(issued.puts.display, contains('display/shops/3/51.jpg'));
    expect(issued.puts.thumb, contains('thumb/shops/3/51.jpg'));
    expect(issued.expiresAt, DateTime.utc(2026, 9, 25, 1, 15));
  });

  test('확인은 그 미디어의 confirm 을 부른다', () async {
    final s = _build(
      (options, body) =>
          const FakeResponse(statusCode: 200, data: {'media_id': 51}),
    );

    await s.api.confirm(3, 51);

    expect(
      '${s.adapter.requests.last.method} ${s.adapter.requests.last.path}',
      'POST /v1/shops/3/media/51/confirm',
    );
  });
}
