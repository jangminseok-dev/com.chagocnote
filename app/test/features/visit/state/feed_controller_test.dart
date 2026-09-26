import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:dio/dio.dart';
import 'package:chagocnote/features/visit/state/feed_controller.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

const FeedQuery _all = (shopId: customerTestShopId, petId: null);

/// 컨트롤러를 붙잡아 두는 구독(autoDispose 가 중간에 버리지 않게).
ProviderSubscription<AsyncValue<FeedState>> _listen(
  ProviderContainer container,
  FeedQuery query,
) => container.listen(feedControllerProvider(query), (_, _) {});

void main() {
  test('첫 쪽을 불러오고, 다음 쪽을 커서로 이어 붙인다', () async {
    final setup = CustomerTestSetup((options, body) {
      expect(options.path, '/v1/shops/3/visits/feed');
      final cursor = options.queryParameters['cursor'];
      return FakeResponse(
        statusCode: 200,
        data: cursor == null
            ? feedJson(items: [feedItemJson(visitId: 1)], nextCursor: 'c1')
            : feedJson(items: [feedItemJson(visitId: 2)]),
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _all);

    final first = await setup.container.read(
      feedControllerProvider(_all).future,
    );
    expect(first.items.map((i) => i.visitId), [1]);
    expect(first.hasMore, isTrue);

    await setup.container
        .read(feedControllerProvider(_all).notifier)
        .loadMore();
    await setup.container
        .read(feedControllerProvider(_all).notifier)
        .loadMore();

    final state = setup.container.read(feedControllerProvider(_all)).value!;
    expect(state.items.map((i) => i.visitId), [1, 2]);
    expect(state.hasMore, isFalse);
    expect(
      setup.adapter.requests.map((r) => r.queryParameters['cursor']),
      [null, 'c1'],
      reason: '마지막 쪽 뒤에는 더 부르지 않는다',
    );
  });

  test('아이를 주면 그 아이의 기록만 묻는다', () async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: feedJson()),
    );
    addTearDown(setup.container.dispose);
    const query = (shopId: customerTestShopId, petId: 11);
    _listen(setup.container, query);

    await setup.container.read(feedControllerProvider(query).future);

    expect(setup.adapter.requests.single.queryParameters, {'pet_id': 11});
  });

  test('다음 쪽이 실패하면 이미 보인 목록을 두고 오류만 기억한다', () async {
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: feedJson(items: [feedItemJson()], nextCursor: 'c1'),
        );
      }
      return const FakeResponse(
        statusCode: 500,
        data: {'code': 'INTERNAL', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _all);
    await setup.container.read(feedControllerProvider(_all).future);

    await setup.container
        .read(feedControllerProvider(_all).notifier)
        .loadMore();

    final state = setup.container.read(feedControllerProvider(_all)).value!;
    expect(state.items, hasLength(1));
    expect(state.hasMore, isTrue);
    expect(state.loadMoreError, isA<ApiException>());
  });

  test('다음 쪽이 인터넷 없음으로 실패했으면 인터넷이 돌아올 때 한 번 다시 부른다 — 서버 오류면 부르지 않는다', () async {
    var failure = 'offline';
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: feedJson(items: [feedItemJson(visitId: 1)], nextCursor: 'c1'),
        );
      }
      switch (failure) {
        case 'offline':
          throw DioException.connectionError(
            requestOptions: options,
            reason: 'offline',
          );
        case 'server':
          return const FakeResponse(statusCode: 503, data: 'x');
      }
      return FakeResponse(
        statusCode: 200,
        data: feedJson(items: [feedItemJson(visitId: 2)]),
      );
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _all);
    await setup.container.read(feedControllerProvider(_all).future);
    final notifier = setup.container.read(feedControllerProvider(_all).notifier);

    await notifier.loadMore();
    failure = 'server';
    setup.network.restore();
    await pumpEventQueue();
    expect(
      setup.container.read(feedControllerProvider(_all)).value!.loadMoreError,
      isA<ApiException>().having((e) => e.code, 'code', 'HTTP_ERROR'),
      reason: '인터넷 없음이었으니 돌아오자 한 번 다시 불렀다(이번엔 서버 오류)',
    );

    failure = 'none';
    setup.network.restore();
    await pumpEventQueue();
    expect(
      setup.adapter.requests.where((r) => r.queryParameters['cursor'] != null),
      hasLength(2),
      reason: '서버 오류는 인터넷이 돌아와도 스스로 다시 부르지 않는다',
    );
  });

  test('다음 쪽을 기다리는 사이 다시 불러오면(기록 저장 뒤) 옛 목록에 이어 붙이지 않는다', () async {
    final gate = Completer<FakeResponse>();
    var firstPages = 0;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        firstPages++;
        return FakeResponse(
          statusCode: 200,
          data: feedJson(
            items: [feedItemJson(visitId: firstPages)],
            nextCursor: 'c1',
          ),
        );
      }
      return gate.future;
    });
    addTearDown(setup.container.dispose);
    _listen(setup.container, _all);
    await setup.container.read(feedControllerProvider(_all).future);

    final pending = setup.container
        .read(feedControllerProvider(_all).notifier)
        .loadMore();
    setup.container.invalidate(feedControllerProvider);
    final reloaded = await setup.container.read(
      feedControllerProvider(_all).future,
    );
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: feedJson(items: [feedItemJson(visitId: 99)]),
      ),
    );
    await pending;

    expect(reloaded.items.map((i) => i.visitId), [2]);
    expect(
      setup.container
          .read(feedControllerProvider(_all))
          .value!
          .items
          .map((i) => i.visitId),
      [2],
    );
  });
}
