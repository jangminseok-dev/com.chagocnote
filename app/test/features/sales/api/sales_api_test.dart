// SalesApi 를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로, 질의, 응답 해석.
import 'dart:convert';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/sales/api/sales_api.dart';
import 'package:chagocnote/features/sales/api/sales_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/sales_fixtures.dart';

({SalesApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: SalesApi(client), adapter: adapter);
}

SalesSummary _parse(Map<String, dynamic> json, [SalesSpan asked = SalesSpan.month]) =>
    SalesSummary.fromJson(json, asked);

void main() {
  test('요약을 읽는다 — 경로와 질의', () async {
    final s = _build(
      (options, body) => FakeResponse(statusCode: 200, data: salesSummaryJson()),
    );

    final summary = await s.api.summary(3, SalesSpan.month, DateTime(2026, 11, 14));

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'GET /v1/shops/3/sales/summary');
    expect(request.queryParameters, {'span': 'month', 'anchor': '2026-11-14'});
    expect(summary.revenue, 3250000);
  });

  test('기간 넷을 이름 그대로 보낸다', () async {
    final s = _build(
      (options, body) => FakeResponse(statusCode: 200, data: salesSummaryJson()),
    );
    for (final span in SalesSpan.values) {
      await s.api.summary(3, span, DateTime(2026, 1, 5));
    }
    expect(
      [for (final r in s.adapter.requests) r.queryParameters['span']],
      ['day', 'week', 'month', 'year'],
    );
    expect(s.adapter.requests.first.queryParameters['anchor'], '2026-01-05');
  });

  test('목업의 11월을 칸 하나하나 읽는다', () {
    final s = _parse(salesSummaryJson(goal: 5000000));

    expect(s.span, SalesSpan.month);
    expect((s.start, s.end, s.elapsedEnd), (
      DateTime(2026, 11, 1),
      DateTime(2026, 11, 30),
      DateTime(2026, 11, 14),
    ));
    expect((s.revenue, s.visitCount, s.pricedCount, s.average), (3250000, 48, 48, 67708));
    expect((s.previous!.start, s.previous!.end, s.previous!.revenue), (
      DateTime(2026, 10, 1),
      DateTime(2026, 10, 14),
      2830000,
    ));
    expect(s.yearAgo, isNull);
    expect(s.goalAmount, 5000000);
    expect((s.petCount, s.newPetCount, s.returningPetCount), (41, 6, 35));
    expect([for (final p in s.faces) (p.petId, p.name, p.photoUrl)], [
      (101, '보리', 'https://media.test/101.jpg'),
      (102, '코코', null),
      (103, '두부', 'https://media.test/103.jpg'),
    ]);
    expect(s.newPets.single.name, '몽이');
    expect(s.returningPets.single.petId, 101);
    expect(s.buckets, hasLength(30));
    final day14 = s.buckets[13];
    expect((day14.key, day14.revenue, day14.future, day14.pets.length), ('2026-11-14', 510000, false, 3));
    expect(s.buckets[14].future, isTrue);
    expect(s.buckets.fold<int>(0, (sum, b) => sum + b.revenue), 3250000);
    expect([for (final p in s.payments) (p.method, p.amount)], [
      ('card', 2400000),
      ('cash', 550000),
      ('transfer', 300000),
    ]);
    expect([for (final m in s.menus) (m.menuId, m.name, m.amount, m.count, m.pet?.name)], [
      (1, '전체 미용', 2100000, 30, '두부'),
      (2, '목욕', 750000, 15, null),
      (3, '스파', 400000, 8, null),
    ]);
    expect([for (final r in s.regulars) (r.pet.name, r.visitCount)], [('보리', 9), ('코코', 7)]);
    expect((s.remaining, s.expectedAmount, s.noShow, s.canceled), (12, 840000, 2, 3));
    expect(s.weekdays, [100000, 180000, 380000, 420000, 550000, 890000, 730000]);
    expect((s.report!.completed, s.report!.sent, s.report!.opened), (48, 40, 31));
    expect((s.unrecordedCount, s.duePetCount), (3, 7));
  });

  test('없을 수 있는 칸은 null 로 읽는다', () {
    final s = _parse(
      salesSummaryJson(
        elapsedEnd: null,
        average: null,
        previous: null,
        weekdays: null,
        report: null,
        bookings: {'remaining': null, 'expected_amount': null, 'no_show': 0, 'canceled': 0},
        buckets: [],
        payments: [],
        menus: [],
        regulars: [],
      ),
    );

    expect((s.elapsedEnd, s.average, s.previous, s.yearAgo, s.goalAmount), (null, null, null, null, null));
    expect((s.weekdays, s.report, s.remaining, s.expectedAmount), (null, null, null, null));
    expect([...s.buckets, ...s.payments, ...s.menus, ...s.regulars], isEmpty);
  });

  test('작년 창과 조정 줄(메뉴 ID 없음, 음수 금액)을 읽는다', () {
    final s = _parse(
      salesSummaryJson(
        yearAgo: {'start': '2025-11-01', 'end': '2025-11-14', 'revenue': 2000000},
        menus: [
          {'menu_id': 1, 'name': '전체 미용', 'amount': 100000, 'count': 2, 'pet': null},
          {'menu_id': null, 'name': '조정', 'amount': -10000, 'count': 0, 'pet': null},
        ],
      ),
    );

    expect(s.yearAgo!.revenue, 2000000);
    expect((s.menus.last.menuId, s.menus.last.name, s.menus.last.amount), (null, '조정', -10000));
  });

  test('모르는 칸과 모르는 값이 와도 읽는다', () {
    final json = salesSummaryJson(
      span: 'decade',
      payments: [
        {'method': 'point', 'amount': 5000, 'extra': 1},
      ],
    )..['unknown_field'] = {'x': 1};

    final s = _parse(json, SalesSpan.week);

    expect(s.span, SalesSpan.week, reason: '모르는 기간이 오면 요청한 기간을 쓴다');
    expect((s.payments.single.method, s.payments.single.amount), ('point', 5000));
  });

  test('목록 칸이 통째로 없어도 빈 목록이다', () {
    final json = salesSummaryJson()
      ..remove('buckets')
      ..remove('payments')
      ..remove('menus')
      ..remove('regulars');
    (json['pets'] as Map<String, dynamic>)
      ..remove('faces')
      ..remove('new')
      ..remove('returning');

    final s = _parse(json);

    expect([...s.buckets, ...s.payments, ...s.menus, ...s.regulars], isEmpty);
    expect([...s.faces, ...s.newPets, ...s.returningPets], isEmpty);
  });

  test('방문 목록 — 경로와 질의, 메뉴와 커서는 있을 때만', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: salesPageJson([
          salesVisitJson(7, pet: petCardJson(101, '보리'), amount: 45000),
          salesVisitJson(6, date: '2026-11-02'),
        ], nextCursor: 'c1'),
      ),
    );

    final page = await s.api.visits(3, SalesSpan.month, DateTime(2026, 11, 14), SalesVisitFilter.noShow);
    await s.api.visits(
      3, SalesSpan.week, DateTime(2026, 11, 14), SalesVisitFilter.menu, menuId: 2, cursor: 'c1',
    );

    final first = s.adapter.requests.first;
    expect('${first.method} ${first.path}', 'GET /v1/shops/3/sales/visits');
    expect(first.queryParameters, {'span': 'month', 'anchor': '2026-11-14', 'filter': 'no_show'});
    expect(s.adapter.requests.last.queryParameters, {
      'span': 'week', 'anchor': '2026-11-14', 'filter': 'menu', 'menu_id': 2, 'cursor': 'c1',
    });
    expect(page.nextCursor, 'c1');
    expect((page.items[0].visitId, page.items[0].pet!.name, page.items[0].amount), (7, '보리', 45000));
    expect((page.items[1].date, page.items[1].pet, page.items[1].amount), (DateTime(2026, 11, 2), null, null));
  });

  test('목록 종류 넷의 글자', () {
    expect([for (final f in SalesVisitFilter.values) f.wire], ['unrecorded', 'no_show', 'canceled', 'menu']);
    expect(SalesVisitFilter.of('no_show'), SalesVisitFilter.noShow);
    expect(SalesVisitFilter.of('nope'), isNull);
    expect(SalesVisitFilter.of(null), isNull);
  });

  test('목표를 정하고 지운다 — PUT 본문과 저장된 값', () async {
    final bodies = <Object?>[];
    final s = _build((options, body) {
      final sent = jsonDecode(utf8.decode(body!)) as Map;
      bodies.add(sent);
      return FakeResponse(statusCode: 200, data: {'monthly_amount': sent['monthly_amount']});
    });

    expect(await s.api.setGoal(3, 5000000), 5000000);
    expect(await s.api.setGoal(3, null), isNull);

    final request = s.adapter.requests.first;
    expect('${request.method} ${request.path}', 'PUT /v1/shops/3/sales/goal');
    expect(bodies, [{'monthly_amount': 5000000}, {'monthly_amount': null}]);
  });
}
