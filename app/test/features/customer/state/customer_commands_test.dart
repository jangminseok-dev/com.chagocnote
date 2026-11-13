import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:chagocnote/features/customer/state/customer_commands.dart';
import 'package:chagocnote/features/customer/state/customer_list_controller.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

const _shop = customerTestShopId;
const _query = (shopId: _shop, q: '', sort: 'recent', includePassed: false);
const _petKey = (shopId: _shop, petId: 11);
const _customerKey = (shopId: _shop, customerId: 7);

/// 목록·반려동물 상세·고객 상세를 모두 보고 있는 상태를 만든다.
Future<CustomerTestSetup> _watchingEverything(FakeHandler writes) async {
  final setup = CustomerTestSetup((options, body) {
    final key = '${options.method} ${options.path}';
    switch (key) {
      case 'GET /v1/shops/3/customers':
        return FakeResponse(statusCode: 200, data: pageJson());
      case 'GET /v1/shops/3/pets/11':
        return FakeResponse(statusCode: 200, data: petDetailJson());
      case 'GET /v1/shops/3/customers/7':
        return FakeResponse(statusCode: 200, data: customerDetailJson());
    }
    return writes(options, body);
  });
  final c = setup.container;
  c.listen(customerListControllerProvider(_query), (_, _) {});
  c.listen(petDetailProvider(_petKey), (_, _) {});
  c.listen(customerDetailProvider(_customerKey), (_, _) {});
  await c.read(customerListControllerProvider(_query).future);
  await c.read(petDetailProvider(_petKey).future);
  await c.read(customerDetailProvider(_customerKey).future);
  setup.adapter.requests.clear();
  return setup;
}

/// 다시 불러오기가 끝날 때까지 기다린다.
Future<void> _settle(CustomerTestSetup setup) async {
  final c = setup.container;
  await c.read(customerListControllerProvider(_query).future);
  await c.read(petDetailProvider(_petKey).future);
  await c.read(customerDetailProvider(_customerKey).future);
}

const _fields = PetFields(
  name: '콩이',
  species: 'dog',
  breed: '말티즈',
  sex: 'female',
  neutered: true,
  birthDate: null,
  birthYear: null,
  weightKg: 3.2,
  noKnownConditions: true,
  conditions: [],
  memo: null,
);

void main() {
  test('반려동물을 고치면 목록·반려동물 상세·고객 상세를 다시 불러온다', () async {
    final setup = await _watchingEverything((options, body) {
      expect('${options.method} ${options.path}', 'PUT /v1/shops/3/pets/11');
      return FakeResponse(statusCode: 200, data: petDetailJson());
    });
    addTearDown(setup.container.dispose);

    await setup.container
        .read(customerCommandsProvider)
        .updatePet(_shop, 11, _fields);
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals([
        'PUT /v1/shops/3/pets/11',
        'GET /v1/shops/3/customers',
        'GET /v1/shops/3/pets/11',
        'GET /v1/shops/3/customers/7',
      ]),
    );
  });

  test('반려동물을 지우면 그 아이의 상세는 다시 부르지 않는다', () async {
    final setup = await _watchingEverything((options, body) {
      expect('${options.method} ${options.path}', 'DELETE /v1/shops/3/pets/11');
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await setup.container.read(customerCommandsProvider).deletePet(_shop, 11);
    await _settle(setup);

    expect(
      setup.calls,
      unorderedEquals([
        'DELETE /v1/shops/3/pets/11',
        'GET /v1/shops/3/customers',
        'GET /v1/shops/3/customers/7',
      ]),
    );
  });

  test('반려동물을 지우면 siblingIds 로 넘긴 형제의 상세는 다시 부르고, 지운 아이의 상세는 다시 부르지 않는다', () async {
    final setup = CustomerTestSetup((options, body) {
      final key = '${options.method} ${options.path}';
      switch (key) {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/pets/12':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(pet: petJson(petId: 12, name: '두부')),
          );
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 요청: $key');
    });
    addTearDown(setup.container.dispose);
    final c = setup.container;
    const siblingKey = (shopId: _shop, petId: 12);
    c.listen(petDetailProvider(_petKey), (_, _) {});
    c.listen(petDetailProvider(siblingKey), (_, _) {});
    await c.read(petDetailProvider(_petKey).future);
    await c.read(petDetailProvider(siblingKey).future);
    setup.adapter.requests.clear();

    await c
        .read(customerCommandsProvider)
        .deletePet(_shop, 11, siblingIds: [12]);
    await c.read(petDetailProvider(siblingKey).future);

    expect(setup.calls, contains('GET /v1/shops/3/pets/12'));
    expect(setup.calls, isNot(contains('GET /v1/shops/3/pets/11')));
  });

  test('고객을 지우면 목록만 다시 부른다', () async {
    final setup = await _watchingEverything((options, body) {
      expect(
        '${options.method} ${options.path}',
        'DELETE /v1/shops/3/customers/7',
      );
      return const FakeResponse(statusCode: 204);
    });
    addTearDown(setup.container.dispose);

    await setup.container
        .read(customerCommandsProvider)
        .deleteCustomer(_shop, 7);
    await _settle(setup);

    expect(setup.calls, [
      'DELETE /v1/shops/3/customers/7',
      'GET /v1/shops/3/customers',
    ]);
  });

  test('실패한 쓰기는 아무것도 다시 부르지 않고 오류를 그대로 던진다', () async {
    final setup = await _watchingEverything((options, body) {
      return const FakeResponse(
        statusCode: 409,
        data: {'code': 'LAST_PET', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);

    await expectLater(
      setup.container.read(customerCommandsProvider).deletePet(_shop, 11),
      throwsA(isA<ApiException>().having((e) => e.code, 'code', 'LAST_PET')),
    );
    await _settle(setup);

    expect(setup.calls, ['DELETE /v1/shops/3/pets/11']);
  });

  test('쓰기가 NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)', () async {
    final setup = await _watchingEverything((options, body) {
      return const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    await setup.container.read(sessionControllerProvider.future);

    await expectLater(
      setup.container.read(customerCommandsProvider).markPassedAway(_shop, 11),
      throwsA(isA<ApiException>()),
    );
    expect(setup.gateway.refreshMeCallCount, 1);
  });

  test('번호 조회 — 없으면 null', () async {
    final setup = CustomerTestSetup((options, body) {
      return const FakeResponse(
        statusCode: 404,
        data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);

    expect(
      await setup.container
          .read(customerCommandsProvider)
          .lookup(_shop, '01012345678'),
      isNull,
    );
  });

  group('보호자 연결 끊기', () {
    const linkPath = '/v1/shops/3/customers/7/guardian-link';

    /// 목록·상세에 더해 연결도 보고 있는 상태. [onDelete]가 DELETE 의 응답을 정한다.
    Future<CustomerTestSetup> watchingLink(FakeResponse Function() onDelete) async {
      final setup = await _watchingEverything((options, body) {
        final key = '${options.method} ${options.path}';
        if (key == 'GET $linkPath') {
          return FakeResponse(statusCode: 200, data: guardianLinkJson());
        }
        expect(key, 'DELETE $linkPath');
        return onDelete();
      });
      final c = setup.container;
      c.listen(guardianLinkProvider(_customerKey), (_, _) {});
      await c.read(guardianLinkProvider(_customerKey).future);
      setup.adapter.requests.clear();
      return setup;
    }

    test('연결을 끊으면 그 고객의 연결만 다시 읽고 목록·상세는 다시 읽지 않는다', () async {
      final setup = await watchingLink(
        () => const FakeResponse(statusCode: 204),
      );
      addTearDown(setup.container.dispose);

      await setup.container
          .read(customerCommandsProvider)
          .endGuardianLink(_shop, 7);
      await setup.container.read(guardianLinkProvider(_customerKey).future);
      await _settle(setup);

      expect(setup.calls, ['DELETE $linkPath', 'GET $linkPath']);
    });

    test('끊기가 실패해도(404) 연결을 다시 읽고 예외는 그대로 던진다', () async {
      final setup = await watchingLink(
        () => const FakeResponse(
          statusCode: 404,
          data: {'code': 'GUARDIAN_LINK_NOT_FOUND', 'message': 'x'},
        ),
      );
      addTearDown(setup.container.dispose);

      await expectLater(
        setup.container
            .read(customerCommandsProvider)
            .endGuardianLink(_shop, 7),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'GUARDIAN_LINK_NOT_FOUND',
          ),
        ),
      );
      await setup.container.read(guardianLinkProvider(_customerKey).future);

      expect(setup.calls, ['DELETE $linkPath', 'GET $linkPath']);
    });

    test('끊기가 NOT_A_MEMBER 면 내 정보를 다시 불러온다', () async {
      final setup = await watchingLink(
        () => const FakeResponse(
          statusCode: 403,
          data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
        ),
      );
      addTearDown(setup.container.dispose);
      await setup.container.read(sessionControllerProvider.future);

      await expectLater(
        setup.container
            .read(customerCommandsProvider)
            .endGuardianLink(_shop, 7),
        throwsA(isA<ApiException>()),
      );
      expect(setup.gateway.refreshMeCallCount, 1);
    });

    test('messageFor 는 GUARDIAN_LINK_NOT_FOUND 를 "이미 끊긴 연결이에요." 로 바꾼다', () {
      expect(
        messageFor(
          ApiException(
            statusCode: 404,
            code: 'GUARDIAN_LINK_NOT_FOUND',
            message: 'x',
          ),
        ),
        '이미 끊긴 연결이에요.',
      );
    });
  });
}
