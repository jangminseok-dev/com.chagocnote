// 월 목표 쓰기 — 성공하든 실패하든 요약을 다시 읽게 한다.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/sales/api/sales_models.dart';
import 'package:chagocnote/features/sales/state/sales_commands.dart';
import 'package:chagocnote/features/sales/state/sales_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/sales_fixtures.dart';

const SalesKey _november = (shopId: customerTestShopId, span: SalesSpan.month, anchor: '2026-11-14');

void main() {
  test('목표를 정하면 요약을 다시 읽는다', () async {
    int? goal;
    final setup = CustomerTestSetup((options, body) {
      if (options.method == 'PUT') {
        goal = (jsonDecode(utf8.decode(body!)) as Map)['monthly_amount'] as int?;
        return FakeResponse(statusCode: 200, data: {'monthly_amount': goal});
      }
      return FakeResponse(statusCode: 200, data: salesSummaryJson(goal: goal));
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesSummaryProvider(_november), (_, _) {});
    expect((await setup.container.read(salesSummaryProvider(_november).future)).goalAmount, isNull);

    final saved = await setup.container.read(salesCommandsProvider).setGoal(customerTestShopId, 5000000);

    expect(saved, 5000000);
    expect((await setup.container.read(salesSummaryProvider(_november).future)).goalAmount, 5000000);
    expect(
      setup.adapter.requests.map((r) => '${r.method} ${r.path}'),
      [
        'GET /v1/shops/3/sales/summary',
        'PUT /v1/shops/3/sales/goal',
        'GET /v1/shops/3/sales/summary',
      ],
    );
  });

  test('실패해도 요약을 다시 읽고 오류는 그대로 던진다', () async {
    final setup = CustomerTestSetup((options, body) {
      if (options.method == 'PUT') return const FakeResponse(statusCode: 503, data: {});
      return FakeResponse(statusCode: 200, data: salesSummaryJson());
    });
    addTearDown(setup.container.dispose);
    setup.container.listen(salesSummaryProvider(_november), (_, _) {});
    await setup.container.read(salesSummaryProvider(_november).future);

    await expectLater(
      setup.container.read(salesCommandsProvider).setGoal(customerTestShopId, null),
      throwsA(isA<ApiException>()),
    );
    await setup.container.read(salesSummaryProvider(_november).future);

    expect(setup.adapter.requests.where((r) => r.path.endsWith('/summary')), hasLength(2));
  });
}
