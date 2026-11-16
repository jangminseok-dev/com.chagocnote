import 'package:chagocnote/features/visit/api/wrap_up_models.dart';
import 'package:chagocnote/features/visit/state/wrap_up_controller.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

void main() {
  late List<Map<String, dynamic>> cards;
  late CustomerTestSetup setup;
  final key = (shopId: customerTestShopId, date: DateTime(2026, 10, 2), start: null as WrapUpKind?);

  Map<String, dynamic> card(String kind, int id) =>
      wrapUpCardJson(kind: kind, visit: visitJson(visitId: id, status: 'completed'));

  setUp(() {
    cards = [card('unpaid', 1), card('unpaid', 2), card('report_unsent', 1)];
    setup = CustomerTestSetup(
      (o, b) => FakeResponse(statusCode: 200, data: wrapUpJson(cards: cards)),
    );
    addTearDown(setup.container.dispose);
    setup.container.listen(wrapUpControllerProvider(key), (_, _) {});
  });

  WrapUpState state() => setup.container.read(wrapUpControllerProvider(key)).value!;
  WrapUpController ctl() => setup.container.read(wrapUpControllerProvider(key).notifier);

  test('처음 장부터, 건너뛰면 다음 장 — 건너뛴 장은 다시 읽어도 되살아나지 않는다', () async {
    await setup.container.read(wrapUpControllerProvider(key).future);
    expect((state().current!.visit.visitId, state().position, state().total), (1, 1, 3));

    ctl().skip();
    expect((state().current!.visit.visitId, state().position), (2, 2));

    // 둘째 장을 끝냈다 — 서버에서 빠졌다.
    cards = [card('unpaid', 1), card('report_unsent', 1)];
    await ctl().done();
    expect(state().current!.kind, WrapUpKind.reportUnsent);
    expect((state().position, state().total), (3, 3));

    cards = [card('unpaid', 1)];
    await ctl().done();
    expect(state().current, isNull);
    expect(state().skippedCount, 1);

    ctl().reviewSkipped();
    expect((state().current!.visit.visitId, state().position, state().total), (1, 1, 1));
  });

  test('처음부터 장이 없으면 곧바로 끝이다', () async {
    cards = [];
    await setup.container.read(wrapUpControllerProvider(key).future);
    expect(state().current, isNull);
    expect(state().skippedCount, 0);
  });
}
