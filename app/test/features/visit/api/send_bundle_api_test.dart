// 보낼 것 묶음 — 경로와 응답 해석. 모르는 kind 의 토막도 글 그대로 싣는다.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/visit/api/visit_api.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/form_settings_fixtures.dart';

({VisitApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  return (api: VisitApi(ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio)), adapter: adapter);
}

void main() {
  test('묶음을 읽는다 — 토막의 순서 그대로', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: sendBundleJson(createdFormId: 31)));

    final bundle = await s.api.sendBundle(3, 21);
    final parts = bundle.parts;
    expect(bundle.createdFormId, 31);

    expect('${s.adapter.requests.single.method} ${s.adapter.requests.single.path}',
        'POST /v1/shops/3/visits/21/send-bundle');
    expect([for (final p in parts) p.kind], ['reservation', 'consent']);
    expect(parts.last.text.endsWith(fakeBundleUrl), isTrue);
  });

  test('모르는 kind 의 토막도 싣고, 글이 없는 토막과 모양이 깨진 토막은 버린다', () async {
    final s = _build((o, b) => const FakeResponse(statusCode: 200, data: {
      'parts': [
        {'kind': 'deposit', 'text': '예약금 안내'},
        {'kind': 'reservation', 'text': '  '},
        {'kind': 'consent'},
        '깨진 것',
      ],
    }));

    final bundle = await s.api.sendBundle(3, 21);

    expect([for (final p in bundle.parts) (p.kind, p.text)], [('deposit', '예약금 안내')]);
    expect(bundle.createdFormId, isNull);
  });
}
