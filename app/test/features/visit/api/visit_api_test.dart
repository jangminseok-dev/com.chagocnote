// VisitApi 를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로,
// 쿼리, 본문 모양, 응답 해석(특히 매장 시간대 시각).
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/visit/api/visit_api.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

({VisitApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: VisitApi(client), adapter: adapter);
}

Map<String, dynamic> _json(List<int>? body) =>
    jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

void main() {
  group('ShopTime', () {
    test('매장 시간대의 벽시계를 그대로 쓰고 기기 시간대로 바꾸지 않는다', () {
      final t = ShopTime.parse('2026-10-02T23:50:00+09:00');

      expect(t.wall, DateTime(2026, 10, 2, 23, 50));
      expect(t.wall.isUtc, isFalse);
      expect(t.day, DateTime(2026, 10, 2));
      expect(t.iso, '2026-10-02T23:50:00+09:00');
    });

    test('초 아래 자리가 붙어도 읽는다', () {
      expect(
        ShopTime.parse('2026-09-23T10:03:12.123456+09:00').wall,
        DateTime(2026, 9, 23, 10, 3, 12),
      );
    });
  });

  test('하루 목록은 date 로 부르고 가족 묶음·상태별 수를 읽는다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: dayJson(
          items: [
            dayItemJson(visitJson(), groupKey: 'g1', overlapping: true),
            dayItemJson(
              visitJson(visitId: 102, pet: visitPetJson(petId: 12, name: '보리')),
              groupKey: 'g1',
            ),
            dayItemJson(
              visitJson(visitId: 103, ownerOnly: true),
              groupKey: 'g2',
            ),
          ],
        ),
      ),
    );

    final day = await s.api.day(3, DateTime(2026, 10, 2));

    final request = s.adapter.requests.single;
    expect(request.path, '/v1/shops/3/visits');
    expect(request.queryParameters, {'date': '2026-10-02'});
    expect(day.counts.visitCount, 3);
    expect(day.items.map((i) => i.groupKey), ['g1', 'g1', 'g2']);
    expect(day.items.first.overlapping, isTrue);
    expect(day.items.first.visit.startsAt.wall, DateTime(2026, 10, 2, 14));
    expect(day.items.first.visit.endsAt.wall, DateTime(2026, 10, 2, 15, 30));
    expect(day.items.first.visit.menus.single.name, '목욕');
    expect(day.items.last.visit.pet, isNull);
  });

  test('월 요약은 month=YYYY-MM 으로 부르고 날짜로 찾는다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: calendarJson(
          days: {
            23: {'visit_count': 5, 'completed_count': 1, 'open_count': 4},
          },
          closedDays: {21},
          unresolvedTotal: 2,
          oldestUnresolvedDate: '2026-08-30',
        ),
      ),
    );

    final month = await s.api.calendar(3, DateTime(2026, 9, 23));

    expect(s.adapter.requests.single.queryParameters, {'month': '2026-09'});
    expect(month.days, hasLength(30));
    expect(month.dayOf(DateTime(2026, 9, 23))!.visitCount, 5);
    expect(month.dayOf(DateTime(2026, 9, 21))!.closedDay, isTrue);
    expect(month.unresolvedTotal, 2);
    expect(month.oldestUnresolvedDate, DateTime(2026, 8, 30));
  });

  test('시간 칸은 소요를 싣고, 옮길 방문은 exclude 를 여러 번 붙인다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: slotsJson(
          warnings: {
            14: ['overlap'],
          },
        ),
      ),
    );

    final slots = await s.api.slots(
      3,
      date: DateTime(2026, 10, 2),
      durationMinutes: 90,
      at: '14:10',
      exclude: [101, 102],
    );

    final uri = s.adapter.requests.single.uri;
    expect(uri.path, '/v1/shops/3/visits/slots');
    expect(uri.queryParametersAll, {
      'date': ['2026-10-02'],
      'duration': ['90'],
      'at': ['14:10'],
      'exclude': ['101', '102'],
    });
    expect(slots.slots.first.startsAt.wall, DateTime(2026, 10, 2, 10));
    expect(slots.slots[4].warnings, [VisitWarning.overlap]);
  });

  test('시간 칸은 at·exclude 가 없으면 보내지 않는다', () async {
    final s = _build(
      (options, body) => FakeResponse(statusCode: 200, data: slotsJson()),
    );

    await s.api.slots(3, date: DateTime(2026, 10, 2), durationMinutes: 120);

    expect(s.adapter.requests.single.queryParameters, {
      'date': '2026-10-02',
      'duration': 120,
    });
  });

  test('예약 등록은 받은 시각 문자열을 그대로 보내고 경고를 읽는다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 201,
        data: savedJson([visitJson()], warnings: ['overlap']),
      ),
    );

    final saved = await s.api.register(
      3,
      const VisitRequest(
        customerId: 7,
        petIds: [11, 12],
        startsAt: '2026-10-02T14:00:00+09:00',
        durationMinutes: 90,
        menuIds: [1],
        memo: '발톱 짧게',
      ),
    );

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'POST /v1/shops/3/visits');
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/visits']), {
      'customer_id': 7,
      'pet_ids': [11, 12],
      'starts_at': '2026-10-02T14:00:00+09:00',
      'duration_minutes': 90,
      'menu_ids': [1],
      'memo': '발톱 짧게',
      'walk_in': false,
    });
    expect(saved.warnings, [VisitWarning.overlap]);
    expect(saved.visits.single.visitId, 101);
  });

  test('지금 시작은 시각을 보내지 않는다', () async {
    final s = _build(
      (options, body) =>
          FakeResponse(statusCode: 201, data: savedJson([visitJson()])),
    );

    await s.api.register(
      3,
      const VisitRequest(
        customerId: 7,
        petIds: [],
        startsAt: null,
        durationMinutes: 60,
        menuIds: [],
        memo: null,
        walkIn: true,
      ),
    );

    final body = _json(s.adapter.lastBodyByPath['/v1/shops/3/visits']);
    expect(body.containsKey('starts_at'), isFalse);
    expect(body['walk_in'], isTrue);
  });

  test('상세는 묶음(자기 제외)·지난 방문·노쇼 횟수를 읽는다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(
          group: [visitJson(visitId: 102)],
          noShowCount: 2,
        ),
      ),
    );

    final detail = await s.api.detail(3, 101);

    expect(s.adapter.requests.single.path, '/v1/shops/3/visits/101');
    expect(detail.group.single.visitId, 102);
    expect(detail.previousVisit!.startsAt.wall, DateTime(2026, 9, 2, 14));
    expect(detail.noShowCount, 2);
    expect(detail.visit.pet!.weightKg, 4.2);
  });

  test('수정은 PUT 으로 모든 칸을 보내고 방문 하나를 감싼다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: {'visit': visitJson(), 'warnings': <String>[]},
      ),
    );

    final saved = await s.api.update(
      3,
      101,
      const VisitUpdate(
        startsAt: '2026-10-02T14:00:00+09:00',
        petId: null,
        durationMinutes: 60,
        menuIds: [],
        memo: null,
      ),
    );

    expect(s.adapter.requests.single.method, 'PUT');
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/visits/101']), {
      'starts_at': '2026-10-02T14:00:00+09:00',
      'pet_id': null,
      'duration_minutes': 60,
      'menu_ids': <int>[],
      'memo': null,
    });
    expect(saved.visits.single.visitId, 101);
  });

  test('상태 전이는 묶음의 방문 ID 를 한 번에 보내고, 사유는 취소일 때만 싣는다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: {
          'visits': [visitJson(status: 'canceled')],
        },
      ),
    );
    const path = '/v1/shops/3/visits/transitions';

    await s.api.transition(3, visitIds: [101, 102], action: VisitAction.start);
    expect(_json(s.adapter.lastBodyByPath[path]), {
      'visit_ids': [101, 102],
      'action': 'start',
    });

    final visits = await s.api.transition(
      3,
      visitIds: [101],
      action: VisitAction.cancel,
      cancelReason: 'shop_reason',
    );
    expect(_json(s.adapter.lastBodyByPath[path]), {
      'visit_ids': [101],
      'action': 'cancel',
      'cancel_reason': 'shop_reason',
    });
    expect(visits.single.status, VisitStatus.canceled);
  });

  test('옮기기·다음 예약 초안', () async {
    final s = _build((options, body) {
      if (options.path.endsWith('/reschedule')) {
        return FakeResponse(statusCode: 200, data: savedJson([visitJson()]));
      }
      return FakeResponse(statusCode: 200, data: nextDraftJson());
    });

    await s.api.reschedule(
      3,
      visitIds: [101, 102],
      startsAt: '2026-10-03T11:00:00+09:00',
    );
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/visits/reschedule']), {
      'visit_ids': [101, 102],
      'starts_at': '2026-10-03T11:00:00+09:00',
    });

    final draft = await s.api.nextDraft(3, 101);
    expect(s.adapter.requests.last.path, '/v1/shops/3/visits/101/next-draft');
    expect(draft.startsAt.wall, DateTime(2026, 10, 30, 14));
    expect(draft.petIds, [11]);
    expect(draft.intervalWeeks, 4);
  });

  test('일정 설정은 HH:MM 으로 읽고 그대로 보낸다', () async {
    final s = _build((options, body) {
      return FakeResponse(statusCode: 200, data: settingsJson());
    });

    final settings = await s.api.settings(3);
    expect(settings.opensAt, '10:00');
    expect(settings.closesAt, '19:00');
    expect(settings.closedWeekdays, [0]);

    await s.api.updateSettings(
      3,
      const VisitSettings(
        opensAt: '09:30',
        closesAt: '20:00',
        defaultDurationMinutes: 90,
        closedWeekdays: [0, 6],
      ),
    );
    expect(s.adapter.requests.last.method, 'PUT');
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/visit-settings']), {
      'opens_at': '09:30',
      'closes_at': '20:00',
      'default_duration_minutes': 90,
      'closed_weekdays': [0, 6],
    });
  });

  test('임시 휴무 조회·추가·삭제', () async {
    final s = _build((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/closed-dates':
          return FakeResponse(
            statusCode: 200,
            data: {
              'items': [
                {'date': '2026-10-09', 'note': '한글날'},
              ],
            },
          );
        case 'POST /v1/shops/3/closed-dates':
          return FakeResponse(
            statusCode: 200,
            data: {'date': '2026-10-09', 'note': null},
          );
        case 'DELETE /v1/shops/3/closed-dates/2026-10-09':
          return const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });

    final list = await s.api.closedDates(
      3,
      from: DateTime(2026, 10, 1),
      to: DateTime(2026, 12, 31),
    );
    expect(s.adapter.requests.last.queryParameters, {
      'from': '2026-10-01',
      'to': '2026-12-31',
    });
    expect(list.single.date, DateTime(2026, 10, 9));
    expect(list.single.note, '한글날');

    await s.api.addClosedDate(3, DateTime(2026, 10, 9));
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/closed-dates']), {
      'date': '2026-10-09',
      'note': null,
    });

    await s.api.deleteClosedDate(3, DateTime(2026, 10, 9));
    expect(s.adapter.requests.last.method, 'DELETE');
  });

  test('메뉴표 조회·추가·수정·보관', () async {
    final s = _build((options, body) {
      if (options.method == 'GET') {
        return FakeResponse(
          statusCode: 200,
          data: {'items': defaultMenusJson()},
        );
      }
      return FakeResponse(statusCode: 200, data: menuJson(menuId: 9));
    });

    final menus = await s.api.menus(3);
    expect(s.adapter.requests.last.queryParameters, {
      'include_archived': false,
    });
    expect(menus.map((m) => m.name), ['목욕', '위생', '부분 미용', '전체 미용', '스포팅']);

    await s.api.createMenu(3, name: '발톱');
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/menus']), {
      'name': '발톱',
      'default_duration_minutes': null,
    });

    await s.api.updateMenu(
      3,
      9,
      name: '발톱 정리',
      defaultDurationMinutes: 20,
      sortOrder: 6,
    );
    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/menus/9']), {
      'name': '발톱 정리',
      'default_duration_minutes': 20,
      'sort_order': 6,
    });

    await s.api.archiveMenu(3, 9);
    expect(
      '${s.adapter.requests.last.method} ${s.adapter.requests.last.path}',
      'POST /v1/shops/3/menus/9/archive',
    );
  });

  test('서버 오류는 코드 그대로 ApiException 이 된다', () async {
    final s = _build(
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'VISIT_DUPLICATE', 'message': '이미 있습니다'},
      ),
    );

    await expectLater(
      s.api.register(
        3,
        const VisitRequest(
          customerId: 7,
          petIds: [11],
          startsAt: '2026-10-02T14:00:00+09:00',
          durationMinutes: 90,
          menuIds: [],
          memo: null,
        ),
      ),
      throwsA(
        isA<ApiException>().having((e) => e.code, 'code', 'VISIT_DUPLICATE'),
      ),
    );
  });
}
