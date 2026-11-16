import 'dart:typed_data';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/plugs/care_marks_plug.dart';
import 'package:chagocnote/features/customer/state/consent_commands.dart';
import 'package:chagocnote/features/customer/state/consent_providers.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/consent_fixtures.dart';
import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

const _shop = customerTestShopId;
const _petKey = (shopId: _shop, petId: 11);

/// 보낸 서류와 반려동물 상세를 보고 있는 상태를 만든다.
Future<({CustomerTestSetup setup, List<int> careMarks})> _watching(FakeHandler writes) async {
  final careMarks = <int>[];
  final setup = CustomerTestSetup(
    overrides: [careMarksChangedPlugProvider.overrideWithValue(() => careMarks.add(1))],
    (options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/forms':
          return FakeResponse(statusCode: 200, data: {'items': [sentFormJson()]});
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
      }
      return writes(options, body);
    },
  );
  final c = setup.container;
  c.listen(sentFormsProvider(_shop), (_, _) {});
  c.listen(petDetailProvider(_petKey), (_, _) {});
  await c.read(sentFormsProvider(_shop).future);
  await c.read(petDetailProvider(_petKey).future);
  setup.adapter.requests.clear();
  return (setup: setup, careMarks: careMarks);
}

Future<void> _settle(CustomerTestSetup setup) async {
  await setup.container.read(sentFormsProvider(_shop).future);
  await setup.container.read(petDetailProvider(_petKey).future);
}

void main() {
  test('보내면 보낸 서류와 반려동물 상세를 다시 읽고 방문 쪽에 알린다', () async {
    final w = await _watching((o, b) => FakeResponse(statusCode: 201, data: formLinkJson()));
    addTearDown(w.setup.container.dispose);

    final link = await w.setup.container.read(consentCommandsProvider).send(_shop, [11], forDate: DateTime(2026, 11, 20));
    await _settle(w.setup);

    expect(link.url, fakeConsentUrl);
    expect(w.setup.calls, unorderedEquals([
      'POST /v1/shops/3/consent-forms', 'GET /v1/shops/3/forms', 'GET /v1/shops/3/pets/11',
    ]));
    expect(w.careMarks, hasLength(1));
  });

  test('실패해도 다시 읽고 알린다 — 서버에는 반영됐을 수 있다', () async {
    final w = await _watching(
      (o, b) => const FakeResponse(statusCode: 409, data: {'code': 'CONSENT_UP_TO_DATE', 'message': 'x'}),
    );
    addTearDown(w.setup.container.dispose);

    await expectLater(
      w.setup.container.read(consentCommandsProvider).send(_shop, [11]),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'CONSENT_UP_TO_DATE')),
    );
    await _settle(w.setup);

    expect(w.setup.calls, containsAll(['GET /v1/shops/3/forms', 'GET /v1/shops/3/pets/11']));
    expect(w.careMarks, hasLength(1));
  });

  test('끊기와 현장 서명도 다시 읽는다', () async {
    final w = await _watching(
      (o, b) => o.method == 'DELETE'
          ? const FakeResponse(statusCode: 204)
          : const FakeResponse(statusCode: 201, data: {'signature_id': 91}),
    );
    addTearDown(w.setup.container.dispose);
    final commands = w.setup.container.read(consentCommandsProvider);

    await commands.revoke(_shop, 31);
    await _settle(w.setup);
    final id = await commands.signInShop(
      _shop, petIds: [11], digest: 'digest-1', signerName: '김민지', png: Uint8List.fromList([1]),
    );
    await _settle(w.setup);

    expect(id, 91);
    expect(w.setup.calls.where((c) => c == 'GET /v1/shops/3/forms'), hasLength(2));
    expect(w.setup.calls, containsAll(['DELETE /v1/shops/3/forms/31', 'POST /v1/shops/3/consent-signatures']));
    expect(w.careMarks, hasLength(2));
  });
}
