// 매출에서 이어지는 목록의 쪽 나눔 — 이어 붙이기, 다음 쪽 실패, 다시 불러오는 사이의 옛 쪽.
import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/sales/api/sales_models.dart';
import 'package:chagocnote/features/sales/state/sales_paged.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/sales_fixtures.dart';

const SalesVisitsKey _noShow = (
  shopId: customerTestShopId,
  span: SalesSpan.month,
  anchor: '2026-10-20',
  filter: SalesVisitFilter.noShow,
  menuId: null,
);

void main() {
  test('첫 쪽을 읽고 다음 쪽을 커서로 이어 붙인다 — 기간과 종류가 그대로 간다', () async {
    final setup = CustomerTestSetup((options, body) {
      final cursor = options.queryParameters['cursor'];
      return FakeResponse(
        statusCode: 200,
        data: cursor == null
            ? salesPageJson([salesVisitJson(9)], nextCursor: 'c1')
            : salesPageJson([salesVisitJson(8)]),
      );
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesVisitsProvider(_noShow), (_, _) {});

    final first = await setup.container.read(salesVisitsProvider(_noShow).future);
    expect(first.items.map((i) => i.visitId), [9]);
    expect(first.hasMore, isTrue);

    final notifier = setup.container.read(salesVisitsProvider(_noShow).notifier);
    await notifier.loadMore();
    await notifier.loadMore();

    final state = setup.container.read(salesVisitsProvider(_noShow)).value!;
    expect(state.items.map((i) => i.visitId), [9, 8]);
    expect(state.hasMore, isFalse);
    expect(setup.adapter.requests.map((r) => r.queryParameters['cursor']), [null, 'c1']);
    for (final r in setup.adapter.requests) {
      expect(r.path, '/v1/shops/3/sales/visits');
      expect(
        (r.queryParameters['span'], r.queryParameters['anchor'], r.queryParameters['filter']),
        ('month', '2026-10-20', 'no_show'),
      );
    }
  });

  test('메뉴의 방문은 메뉴 ID 를 싣는다', () async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: salesPageJson([])),
    );
    addTearDown(setup.container.dispose);
    const key = (
      shopId: customerTestShopId,
      span: SalesSpan.week,
      anchor: '2026-11-14',
      filter: SalesVisitFilter.menu,
      menuId: 2,
    );
    setup.container.listen(salesVisitsProvider(key), (_, _) {});

    final state = await setup.container.read(salesVisitsProvider(key).future);

    expect(state.items, isEmpty);
    expect(setup.adapter.requests.single.queryParameters['menu_id'], 2);
  });

  test('다음 쪽이 실패하면 보인 줄은 그대로이고, 다시 부르면 이어 붙는다', () async {
    var failNext = true;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: salesPageJson([salesVisitJson(1)], nextCursor: 'c1'),
        );
      }
      if (failNext) return const FakeResponse(statusCode: 503, data: {});
      return FakeResponse(statusCode: 200, data: salesPageJson([salesVisitJson(2)]));
    });
    addTearDown(setup.container.dispose);
    final provider = salesVisitsProvider(_noShow);
    setup.container.listen(provider, (_, _) {});
    await setup.container.read(provider.future);

    await setup.container.read(provider.notifier).loadMore();

    var state = setup.container.read(provider).value!;
    expect(state.items.map((i) => i.visitId), [1]);
    expect(state.loadMoreError, isA<ApiException>());
    expect((state.hasMore, state.loadingMore), (true, false));

    failNext = false;
    await setup.container.read(provider.notifier).loadMore();

    state = setup.container.read(provider).value!;
    expect(state.items.map((i) => i.visitId), [1, 2]);
    expect(state.loadMoreError, isNull);
    expect(setup.adapter.requests.last.path, '/v1/shops/3/sales/visits');
  });

  test('다음 쪽을 부르는 중에 또 부르면 요청은 하나다', () async {
    final gate = Completer<void>();
    final setup = CustomerTestSetup((options, body) async {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(statusCode: 200, data: salesPageJson([salesVisitJson(9)], nextCursor: 'c1'));
      }
      await gate.future;
      return FakeResponse(statusCode: 200, data: salesPageJson([salesVisitJson(8)]));
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesVisitsProvider(_noShow), (_, _) {});
    await setup.container.read(salesVisitsProvider(_noShow).future);
    final notifier = setup.container.read(salesVisitsProvider(_noShow).notifier);

    final a = notifier.loadMore();
    final b = notifier.loadMore();
    expect(setup.container.read(salesVisitsProvider(_noShow)).value!.loadingMore, isTrue);
    gate.complete();
    await Future.wait([a, b]);

    expect(setup.adapter.requests, hasLength(2));
    expect(setup.container.read(salesVisitsProvider(_noShow)).value!.items.map((i) => i.visitId), [9, 8]);
  });

  test('다시 불러오는 사이에 끝난 옛 다음 쪽은 새 목록에 붙지 않는다', () async {
    final gate = Completer<void>();
    var firstPages = 0;
    final setup = CustomerTestSetup((options, body) async {
      if (options.queryParameters['cursor'] == null) {
        firstPages++;
        return FakeResponse(
          statusCode: 200,
          data: salesPageJson([salesVisitJson(firstPages == 1 ? 9 : 20)], nextCursor: 'c$firstPages'),
        );
      }
      await gate.future;
      return FakeResponse(statusCode: 200, data: salesPageJson([salesVisitJson(8)]));
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesVisitsProvider(_noShow), (_, _) {});
    await setup.container.read(salesVisitsProvider(_noShow).future);

    final old = setup.container.read(salesVisitsProvider(_noShow).notifier).loadMore();
    setup.container.invalidate(salesVisitsProvider(_noShow));
    await setup.container.read(salesVisitsProvider(_noShow).future);
    gate.complete();
    await old;

    final state = setup.container.read(salesVisitsProvider(_noShow)).value!;
    expect(state.items.map((i) => i.visitId), [20]);
    expect(state.nextCursor, 'c2');
  });

  test('다시 읽기는 불러온 만큼을 처음부터 읽어 갈아 끼운다 — 이어 읽은 줄이 줄지 않는다', () async {
    var round = 1;
    final setup = CustomerTestSetup((options, body) {
      final cursor = options.queryParameters['cursor'];
      // 두 번째 읽기에서는 9 번 방문이 빠졌다(상세에서 금액을 적었다).
      if (round == 1) {
        return FakeResponse(
          statusCode: 200,
          data: cursor == null
              ? salesPageJson([salesVisitJson(9), salesVisitJson(8)], nextCursor: 'a')
              : salesPageJson([salesVisitJson(7), salesVisitJson(6)], nextCursor: 'b'),
        );
      }
      return FakeResponse(
        statusCode: 200,
        data: cursor == null
            ? salesPageJson([salesVisitJson(8), salesVisitJson(7)], nextCursor: 'x')
            : salesPageJson([salesVisitJson(6), salesVisitJson(5)], nextCursor: 'y'),
      );
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesVisitsProvider(_noShow), (_, _) {});
    await setup.container.read(salesVisitsProvider(_noShow).future);
    final notifier = setup.container.read(salesVisitsProvider(_noShow).notifier);
    await notifier.loadMore();
    expect(setup.container.read(salesVisitsProvider(_noShow)).value!.items, hasLength(4));

    round = 2;
    final reloading = notifier.reload();
    expect(
      setup.container.read(salesVisitsProvider(_noShow)).isLoading,
      isFalse,
      reason: '읽는 동안에도 보이던 줄이 그대로 있다',
    );
    await reloading;

    final state = setup.container.read(salesVisitsProvider(_noShow)).value!;
    expect(state.items.map((i) => i.visitId), [8, 7, 6, 5]);
    expect(state.nextCursor, 'y');
    expect(setup.adapter.requests.map((r) => r.queryParameters['cursor']), [null, 'a', null, 'x']);
  });

  test('다시 읽기가 실패하면 보이던 목록이 그대로다', () async {
    var fail = false;
    final setup = CustomerTestSetup((options, body) {
      if (fail) return const FakeResponse(statusCode: 503, data: {});
      return FakeResponse(statusCode: 200, data: salesPageJson([salesVisitJson(9)], nextCursor: 'a'));
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesVisitsProvider(_noShow), (_, _) {});
    await setup.container.read(salesVisitsProvider(_noShow).future);

    fail = true;
    await setup.container.read(salesVisitsProvider(_noShow).notifier).reload();

    final value = setup.container.read(salesVisitsProvider(_noShow));
    expect(value.hasError, isFalse);
    expect(value.value!.items.map((i) => i.visitId), [9]);
    expect(value.value!.nextCursor, 'a');
  });
}
