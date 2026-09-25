import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/state/customer_list_controller.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/feed_controller.dart';
import 'package:chagocnote/features/visit/state/visit_commands.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

const _shop = customerTestShopId;
final _dayKey = (shopId: _shop, date: DateTime(2026, 10, 2));
final _monthKey = monthKeyOf(_shop, DateTime(2026, 10, 2));
const _visitKey = (shopId: _shop, visitId: 101);
const _customerKey = (shopId: _shop, customerId: 7);
const _petKey = (shopId: _shop, petId: 11);
const FeedQuery _feedQuery = (shopId: _shop, petId: null);
const _listQuery = (
  shopId: _shop,
  q: '',
  sort: 'last_visit',
  includePassed: false,
);

/// 하루 목록·월 요약·방문 상세·고객 상세·고객 목록을 모두 보고 있는 상태를 만든다.
Future<CustomerTestSetup> _watchingEverything(FakeHandler writes) async {
  final setup = CustomerTestSetup((options, body) {
    switch ('${options.method} ${options.path}') {
      case 'GET /v1/shops/3/visits':
        return FakeResponse(
          statusCode: 200,
          data: dayJson(items: [dayItemJson(visitJson())]),
        );
      case 'GET /v1/shops/3/visits/calendar':
        return FakeResponse(
          statusCode: 200,
          data: calendarJson(year: 2026, month: 10),
        );
      case 'GET /v1/shops/3/visits/101':
        return FakeResponse(statusCode: 200, data: visitDetailJson());
      case 'GET /v1/shops/3/visits/feed':
        return FakeResponse(statusCode: 200, data: feedJson());
      case 'GET /v1/shops/3/customers/7':
        return FakeResponse(statusCode: 200, data: customerDetailJson());
      case 'GET /v1/shops/3/pets/11':
        return FakeResponse(statusCode: 200, data: petDetailJson());
      case 'GET /v1/shops/3/customers':
        return FakeResponse(statusCode: 200, data: pageJson());
    }
    return writes(options, body);
  });
  final c = setup.container;
  c.listen(dayVisitsProvider(_dayKey), (_, _) {});
  c.listen(calendarMonthProvider(_monthKey), (_, _) {});
  c.listen(visitDetailProvider(_visitKey), (_, _) {});
  c.listen(feedControllerProvider(_feedQuery), (_, _) {});
  c.listen(customerDetailProvider(_customerKey), (_, _) {});
  c.listen(petDetailProvider(_petKey), (_, _) {});
  c.listen(customerListControllerProvider(_listQuery), (_, _) {});
  await _settle(setup);
  setup.adapter.requests.clear();
  return setup;
}

Future<void> _settle(CustomerTestSetup setup) async {
  final c = setup.container;
  await c.read(dayVisitsProvider(_dayKey).future);
  await c.read(calendarMonthProvider(_monthKey).future);
  await c.read(visitDetailProvider(_visitKey).future);
  await c.read(feedControllerProvider(_feedQuery).future);
  await c.read(customerDetailProvider(_customerKey).future);
  await c.read(petDetailProvider(_petKey).future);
  await c.read(customerListControllerProvider(_listQuery).future);
}

const _reads = [
  'GET /v1/shops/3/visits',
  'GET /v1/shops/3/visits/calendar',
  'GET /v1/shops/3/visits/101',
  'GET /v1/shops/3/visits/feed',
  'GET /v1/shops/3/customers/7',
  'GET /v1/shops/3/pets/11',
  'GET /v1/shops/3/customers',
];

void main() {
  test('상태 전이가 끝나면 하루·달·상세·피드와 고객 쪽을 다시 불러온다', () async {
    final setup = await _watchingEverything((options, body) {
      expect(
        '${options.method} ${options.path}',
        'POST /v1/shops/3/visits/transitions',
      );
      return FakeResponse(
        statusCode: 200,
        data: {
          'visits': [visitJson(status: 'completed')],
        },
      );
    });
    addTearDown(setup.container.dispose);

    await setup.container
        .read(visitCommandsProvider)
        .transition(_shop, visitIds: [101], action: VisitAction.complete);
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals(['POST /v1/shops/3/visits/transitions', ..._reads]),
    );
  });

  test('다른 기기가 먼저 바꿔 409 가 나도 다시 불러온다(낙관적 갱신 없음)', () async {
    final setup = await _watchingEverything(
      (options, body) => const FakeResponse(
        statusCode: 409,
        data: {'code': 'VISIT_STATE_CONFLICT', 'message': 'x'},
      ),
    );
    addTearDown(setup.container.dispose);

    await expectLater(
      setup.container
          .read(visitCommandsProvider)
          .transition(_shop, visitIds: [101], action: VisitAction.start),
      throwsA(isA<ApiException>()),
    );
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals(['POST /v1/shops/3/visits/transitions', ..._reads]),
    );
  });

  test('쓰기가 NOT_A_MEMBER 면 내 정보를 다시 불러온다', () async {
    final setup = await _watchingEverything(
      (options, body) => const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      ),
    );
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container
          .read(visitCommandsProvider)
          .register(
            _shop,
            const VisitRequest(
              customerId: 7,
              petIds: [11],
              startsAt: '2026-10-02T14:00:00+09:00',
              durationMinutes: 90,
              menuIds: [],
              memo: null,
            ),
          ),
      throwsA(isA<ApiException>()),
    );

    expect(setup.gateway.refreshMeCallCount, 1);
  });

  test('다음 예약 초안은 읽기라 아무것도 다시 부르지 않는다', () async {
    final setup = await _watchingEverything(
      (options, body) => FakeResponse(statusCode: 200, data: nextDraftJson()),
    );
    addTearDown(setup.container.dispose);

    await setup.container.read(visitCommandsProvider).nextDraft(_shop, 101);
    await _settle(setup);

    expect(setup.calls, ['GET /v1/shops/3/visits/101/next-draft']);
  });

  test('임시 휴무를 더하면 설정·휴무·하루·달을 다시 불러오고 고객 쪽은 두지 않는다', () async {
    final setup = await _watchingEverything(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: {'date': '2026-10-02', 'note': null},
      ),
    );
    addTearDown(setup.container.dispose);

    await setup.container
        .read(visitCommandsProvider)
        .addClosedDate(_shop, DateTime(2026, 10, 2));
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals([
        'POST /v1/shops/3/closed-dates',
        'GET /v1/shops/3/visits',
        'GET /v1/shops/3/visits/calendar',
      ]),
    );
  });

  test('메뉴를 더하면 메뉴표를 다시 불러온다', () async {
    final setup = CustomerTestSetup((options, body) {
      if (options.method == 'GET') {
        return FakeResponse(
          statusCode: 200,
          data: {'items': defaultMenusJson()},
        );
      }
      return FakeResponse(statusCode: 201, data: menuJson(menuId: 9));
    });
    addTearDown(setup.container.dispose);
    const key = (shopId: _shop, includeArchived: false);
    setup.container.listen(menusProvider(key), (_, _) {});
    await setup.container.read(menusProvider(key).future);
    setup.adapter.requests.clear();

    await setup.container
        .read(visitCommandsProvider)
        .createMenu(_shop, name: '발톱');
    await setup.container.read(menusProvider(key).future);

    expect(setup.calls, ['POST /v1/shops/3/menus', 'GET /v1/shops/3/menus']);
  });

  test(
    '기록 저장·삭제가 끝나면 하루·달·상세·피드와 고객 쪽을 다시 불러온다 — 몸무게·프로필 사진이 고객 쪽으로 넘어갈 수 있다',
    () async {
      final setup = await _watchingEverything(
        (options, body) => options.method == 'DELETE'
            ? const FakeResponse(statusCode: 204)
            : FakeResponse(statusCode: 200, data: recordJson(weightKg: 4.2)),
      );
      addTearDown(setup.container.dispose);
      final commands = setup.container.read(visitCommandsProvider);

      await commands.saveRecord(
        _shop,
        101,
        const RecordInput(
          version: null,
          weightKg: 4.2,
          careNote: null,
          internalNote: null,
          paymentMethod: null,
          totalAmount: null,
          items: [],
          media: [],
        ),
      );
      await _settle(setup);
      expect(
        setup.calls,
        unorderedEquals(['PUT /v1/shops/3/visits/101/record', ..._reads]),
      );

      setup.adapter.requests.clear();
      await commands.deleteRecord(_shop, 101);
      await _settle(setup);
      expect(
        setup.calls,
        unorderedEquals(['DELETE /v1/shops/3/visits/101/record', ..._reads]),
      );
    },
  );
}
