// SearchApi 와 모델을 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로, 질의, 응답 해석.
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/search/api/search_api.dart';
import 'package:chagocnote/features/search/api/search_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/search_fixtures.dart';

({SearchApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: SearchApi(client), adapter: adapter);
}

void main() {
  test('매장 전체에서 찾는다 — 경로와 질의', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: searchResultJson([searchItemJson()])));

    final result = await s.api.search(3, '귀 청소');

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'GET /v1/shops/3/search');
    expect(request.queryParameters, {'q': '귀 청소'});
    expect(result.items.single.snippet, '귀 청소할 때 예민하게 반응했어요');
  });

  test('아이로 좁히면 pet_id 를 함께 보낸다', () async {
    final s = _build((o, b) => FakeResponse(statusCode: 200, data: searchResultJson([])));

    await s.api.search(3, '발톱', petId: 101);

    expect(s.adapter.requests.single.queryParameters, {'q': '발톱', 'pet_id': 101});
  });

  test('한 줄의 칸을 읽는다', () {
    final item = SearchItem.tryParse(
      searchItemJson(photo: 'https://media.test/51.jpg', visitId: 7, date: '2026-11-03'),
    )!;
    expect(item.kind, SearchKind.careNote);
    expect((item.ownerId, item.ownerName), (1, '김민지'));
    expect((item.petId, item.petName, item.photoUrl), (101, '콩이', 'https://media.test/51.jpg'));
    expect((item.visitId, item.openPetId, item.date), (7, null, DateTime(2026, 11, 3)));
  });

  test('여섯 종류를 읽는다', () {
    for (final kind in SearchKind.values) {
      expect(SearchItem.tryParse(searchItemJson(kind: kind.wire))!.kind, kind);
    }
    expect(SearchKind.values.map((k) => k.wire), [
      'care_note', 'internal_note', 'visit_memo', 'pet_memo', 'condition_note', 'customer_memo',
    ]);
  });

  test('아이가 없는 줄은 보호자만 있다', () {
    final item = SearchItem.tryParse(searchOwnerItemJson(openPetId: 101))!;
    expect((item.petId, item.petName, item.photoUrl, item.openPetId), (null, null, null, 101));
  });

  test('모르는 종류와 모양이 깨진 줄은 버리고 나머지는 읽는다', () {
    final result = SearchResult.fromJson({
      'items': [
        searchItemJson(snippet: '첫 줄'),
        searchItemJson(kind: 'photo_caption'),
        {...searchItemJson(), 'owner': null},
        {...searchItemJson(), 'snippet': 7},
        {...searchItemJson(), 'pet': {'pet_id': 101}},
        '줄이 아닌 것',
        searchItemJson(snippet: '끝 줄'),
      ],
      'semantic': false,
    });
    expect(result.items.map((i) => i.snippet), ['첫 줄', '끝 줄']);
  });

  test('날짜가 깨져도 그 줄은 살린다', () {
    final item = SearchItem.tryParse(searchItemJson(date: '어제'))!;
    expect(item.date, isNull);
    expect(item.visitId, 7);
  });

  test('items 가 없으면 빈 결과다', () {
    expect(SearchResult.fromJson({'semantic': true}).items, isEmpty);
  });
}
