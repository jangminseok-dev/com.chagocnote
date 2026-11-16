import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/visit/api/revisit_models.dart';
import 'package:chagocnote/features/visit/state/revisit_list.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

void main() {
  test('다음 쪽이 실패하면 보인 줄은 그대로 두고, 다시 부르면 이어 붙인다', () async {
    var failNext = true;
    final setup = CustomerTestSetup((options, body) async {
      expect(options.queryParameters['bucket'], 'due');
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: revisitPageJson(items: [revisitItemJson(petId: 101, name: '보리')], nextCursor: 'c1'),
        );
      }
      if (failNext) return const FakeResponse(statusCode: 503, data: {});
      return FakeResponse(
        statusCode: 200,
        data: revisitPageJson(items: [revisitItemJson(petId: 102, name: '코코')]),
      );
    });
    addTearDown(setup.container.dispose);
    final provider = revisitsProvider((shopId: customerTestShopId, bucket: RevisitBucket.due));
    setup.container.listen(provider, (_, _) {});
    await setup.container.read(provider.future);

    await setup.container.read(provider.notifier).loadMore();
    var state = setup.container.read(provider).value!;
    expect(state.items.map((i) => i.petName), ['보리']);
    expect(state.loadMoreError, isA<ApiException>());

    failNext = false;
    await setup.container.read(provider.notifier).loadMore();
    state = setup.container.read(provider).value!;
    expect(state.items.map((i) => i.petName), ['보리', '코코']);
    expect(state.hasMore, isFalse);
  });

  test('reload 는 불러온 만큼을 처음부터 다시 읽어 갈아 끼운다', () async {
    var round = 0;
    final setup = CustomerTestSetup((options, body) async {
      final first = options.queryParameters['cursor'] == null;
      final name = round == 0 ? (first ? '보리' : '코코') : (first ? '두부' : '몽이');
      return FakeResponse(
        statusCode: 200,
        data: revisitPageJson(items: [revisitItemJson(name: name)], nextCursor: first ? 'c1' : null),
      );
    });
    addTearDown(setup.container.dispose);
    final provider = revisitsProvider((shopId: customerTestShopId, bucket: RevisitBucket.soon));
    setup.container.listen(provider, (_, _) {});
    await setup.container.read(provider.future);
    await setup.container.read(provider.notifier).loadMore();

    round = 1;
    await setup.container.read(provider.notifier).reload();

    expect(setup.container.read(provider).value!.items.map((i) => i.petName), ['두부', '몽이']);
  });
}
