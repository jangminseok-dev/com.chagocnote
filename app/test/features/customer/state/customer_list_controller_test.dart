import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/state/customer_list_controller.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

const _query = (
  shopId: customerTestShopId,
  q: '',
  sort: 'recent',
  includePassed: false,
);

/// 컨트롤러를 붙잡아 두는 구독(autoDispose 가 중간에 버리지 않게).
ProviderSubscription<AsyncValue<CustomerListState>> _listen(
  ProviderContainer container,
  CustomerListQuery query,
) => container.listen(customerListControllerProvider(query), (_, _) {});

void main() {
  test('첫 페이지를 불러오고, 다음 페이지를 이어 붙인다', () async {
    final setup = CustomerTestSetup((options, body) {
      final cursor = options.queryParameters['cursor'];
      if (cursor == null) {
        return FakeResponse(
          statusCode: 200,
          data: pageJson(
            items: [familyJson(customerId: 1)],
            nextCursor: 'c1',
            petCount: 2,
          ),
        );
      }
      expect(cursor, 'c1');
      return FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 2)], petCount: 2),
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);

    final first = await setup.container.read(
      customerListControllerProvider(_query).future,
    );
    expect(first.items.map((c) => c.customerId), [1]);
    expect(first.hasMore, isTrue);
    expect(first.petCount, 2);

    await setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();

    final state = setup.container
        .read(customerListControllerProvider(_query))
        .value!;
    expect(state.items.map((c) => c.customerId), [1, 2]);
    expect(state.hasMore, isFalse);
    expect(state.loadingMore, isFalse);
  });

  test('다음 페이지를 불러오는 중에 또 부르면 요청을 하나만 보낸다', () async {
    final gate = Completer<FakeResponse>();
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(statusCode: 200, data: pageJson(nextCursor: 'c1'));
      }
      return gate.future;
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);
    final notifier = setup.container.read(
      customerListControllerProvider(_query).notifier,
    );

    final first = notifier.loadMore();
    await notifier.loadMore();
    expect(
      setup.container
          .read(customerListControllerProvider(_query))
          .value!
          .loadingMore,
      isTrue,
    );
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 9)]),
      ),
    );
    await first;

    expect(
      setup.adapter.requests.where((r) => r.queryParameters['cursor'] == 'c1'),
      hasLength(1),
    );
  });

  test('다음 페이지가 실패하면 이미 보인 목록을 두고 오류만 기억한다', () async {
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(statusCode: 200, data: pageJson(nextCursor: 'c1'));
      }
      return const FakeResponse(
        statusCode: 500,
        data: {'code': 'INTERNAL', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);

    await setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();

    final state = setup.container
        .read(customerListControllerProvider(_query))
        .value!;
    expect(state.items, hasLength(1));
    expect(state.hasMore, isTrue);
    expect(state.loadMoreError, isA<ApiException>());
  });

  test('다음 페이지가 인터넷 없음으로 실패했으면 인터넷이 돌아올 때 한 번 다시 부른다', () async {
    var online = false;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: pageJson(items: [familyJson(customerId: 1)], nextCursor: 'c1'),
        );
      }
      if (!online) {
        throw DioException.connectionError(
          requestOptions: options,
          reason: 'offline',
        );
      }
      return FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 2)]),
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);

    await setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();
    expect(
      setup.container.read(customerListControllerProvider(_query)).value!.loadMoreError,
      isA<ApiException>().having((e) => e.isNetwork, 'isNetwork', isTrue),
    );

    online = true;
    setup.network.restore();
    await pumpEventQueue();
    final state = setup.container.read(customerListControllerProvider(_query)).value!;
    expect(state.items.map((c) => c.customerId), [1, 2]);
    expect(state.loadMoreError, isNull);
  });

  test('다음 페이지를 기다리는 사이 다시 불러오면 옛 목록에 이어 붙이지 않는다', () async {
    final gate = Completer<FakeResponse>();
    var firstPages = 0;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        firstPages++;
        return FakeResponse(
          statusCode: 200,
          data: pageJson(
            items: [familyJson(customerId: firstPages)],
            nextCursor: 'c1',
          ),
        );
      }
      return gate.future;
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _query);
    await setup.container.read(customerListControllerProvider(_query).future);

    final pending = setup.container
        .read(customerListControllerProvider(_query).notifier)
        .loadMore();
    setup.container.invalidate(customerListControllerProvider);
    final reloaded = await setup.container.read(
      customerListControllerProvider(_query).future,
    );
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 99)]),
      ),
    );
    await pending;

    expect(reloaded.items.map((c) => c.customerId), [2]);
    expect(
      setup.container
          .read(customerListControllerProvider(_query))
          .value!
          .items
          .map((c) => c.customerId),
      [2],
    );
  });

  test('조건마다 따로 불러온다 — 검색어·정렬·무지개다리 포함이 쿼리에 실린다', () async {
    final setup = CustomerTestSetup((options, body) {
      return FakeResponse(statusCode: 200, data: pageJson(items: []));
    });
    addTearDown(setup.container.dispose);
    const query = (
      shopId: customerTestShopId,
      q: 'ㅋㅇ',
      sort: 'name',
      includePassed: true,
    );
    _listen(setup.container, query);

    await setup.container.read(customerListControllerProvider(query).future);

    expect(setup.adapter.requests.single.queryParameters, {
      'q': 'ㅋㅇ',
      'sort': 'name',
      'include_passed': true,
    });
  });

  test('NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)', () async {
    final setup = CustomerTestSetup((options, body) {
      return const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);
    _listen(setup.container, _query);

    await expectLater(
      setup.container.read(customerListControllerProvider(_query).future),
      throwsA(isA<ApiException>()),
    );
    expect(setup.gateway.refreshMeCallCount, 1);
  });
}
