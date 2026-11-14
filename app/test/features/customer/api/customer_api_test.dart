// CustomerApi 를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로,
// 쿼리, 본문 모양, 응답 해석.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/customer/api/customer_api.dart';
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/fake_http_client_adapter.dart';

({CustomerApi api, FakeHttpClientAdapter adapter}) _build(FakeHandler handle) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: CustomerApi(client), adapter: adapter);
}

Map<String, dynamic> _json(List<int>? body) =>
    jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

const _petFields = PetFields(
  name: '콩이',
  species: 'dog',
  breed: '말티즈',
  sex: 'female',
  neutered: true,
  birthDate: null,
  birthYear: 2021,
  weightKg: 3.2,
  noKnownConditions: false,
  conditions: [
    ConditionEntry(typeCode: 'patella_luxation', note: '2기'),
    ConditionEntry(typeCode: 'other', customLabel: '눈물 자국'),
  ],
  memo: null,
);

const _customerFields = CustomerFields(
  name: '김민지',
  phone: '01012345678',
  phoneAlt: null,
  marketingConsent: false,
  memo: '오후 방문 선호',
);

void main() {
  test('고객 상세 조회에는 노쇼 횟수·다가오는 예약이 있고, 없는 응답(등록·수정)은 0·빈 목록이다', () {
    final overview = CustomerDetail.fromJson(
      customerDetailJson(noShowCount: 1, upcomingVisits: [upcomingVisitJson()]),
    );
    expect(overview.noShowCount, 1);
    expect(overview.upcomingVisits.single.visitId, 101);
    expect(
      overview.upcomingVisits.single.startsAt,
      '2026-10-02T14:00:00+09:00',
    );

    final plain = CustomerDetail.fromJson({
      'customer': customerJson(),
      'pets': [petJson()],
    });
    expect(plain.noShowCount, 0);
    expect(plain.upcomingVisits, isEmpty);
  });

  group('list', () {
    test(
      '기본 쿼리는 sort=recent·include_passed=false 이고 빈 검색어와 커서는 보내지 않는다',
      () async {
        final s = _build((options, body) {
          return FakeResponse(
            statusCode: 200,
            data: pageJson(
              items: [
                familyJson(
                  pets: [
                    petSummaryJson(
                      photo: 'http://media.test/b/thumb/shops/3/51.jpg?sig=a',
                    ),
                  ],
                ),
              ],
              nextCursor: 'c1',
            ),
          );
        });

        final page = await s.api.list(3, q: '');

        final request = s.adapter.requests.single;
        expect(request.method, 'GET');
        expect(request.path, '/v1/shops/3/customers');
        expect(request.queryParameters, {
          'sort': 'recent',
          'include_passed': false,
        });
        expect(page.nextCursor, 'c1');
        expect(page.petCount, 1);
        final card = page.items.single;
        expect(card.name, '김민지');
        expect(card.phoneMasked, '010-12··-5678');
        expect(card.pets.single.name, '콩이');
        expect(card.pets.single.ageLabel, '5살');
        expect(
          card.pets.single.photo,
          'http://media.test/b/thumb/shops/3/51.jpg?sig=a',
        );
      },
    );

    test('검색어·정렬·무지개다리 포함·커서를 쿼리로 보낸다', () async {
      final s = _build((options, body) {
        return FakeResponse(statusCode: 200, data: pageJson(items: []));
      });

      await s.api.list(
        3,
        q: '5678 콩',
        sort: 'name',
        includePassed: true,
        cursor: 'c1',
      );

      expect(s.adapter.requests.single.queryParameters, {
        'q': '5678 콩',
        'sort': 'name',
        'include_passed': true,
        'cursor': 'c1',
      });
    });
  });

  group('lookup', () {
    test('있으면 보호자 이름과 반려동물 이름을 돌려준다', () async {
      final s = _build((options, body) {
        expect(options.path, '/v1/shops/3/customers/lookup');
        expect(options.queryParameters, {'phone': '01012345678'});
        return const FakeResponse(
          statusCode: 200,
          data: {
            'customer_id': 7,
            'name': '김민지',
            'pet_names': ['콩이', '두부'],
          },
        );
      });

      final found = await s.api.lookup(3, '01012345678');

      expect(found!.customerId, 7);
      expect(found.petNames, ['콩이', '두부']);
    });

    test('404 CUSTOMER_NOT_FOUND 면 null 이다', () async {
      final s = _build((options, body) {
        return const FakeResponse(
          statusCode: 404,
          data: {'code': 'CUSTOMER_NOT_FOUND', 'message': '없음'},
        );
      });

      expect(await s.api.lookup(3, '01012345678'), isNull);
    });

    test('다른 오류는 그대로 던진다', () async {
      final s = _build((options, body) {
        return const FakeResponse(
          statusCode: 422,
          data: {'code': 'VALIDATION_ERROR', 'message': '형식'},
        );
      });

      await expectLater(
        s.api.lookup(3, '0101'),
        throwsA(
          isA<ApiException>().having((e) => e.code, 'code', 'VALIDATION_ERROR'),
        ),
      );
    });
  });

  test('register 는 {customer, pet} 본문을 보내고 고객 상세를 돌려준다', () async {
    final s = _build((options, body) {
      expect(options.method, 'POST');
      expect(options.path, '/v1/shops/3/customers');
      return FakeResponse(statusCode: 201, data: customerDetailJson());
    });

    final detail = await s.api.register(
      3,
      customer: _customerFields,
      pet: _petFields,
    );

    expect(_json(s.adapter.lastBodyByPath['/v1/shops/3/customers']), {
      'customer': {
        'name': '김민지',
        'phone': '01012345678',
        'phone_alt': null,
        'marketing_consent': false,
        'memo': '오후 방문 선호',
      },
      'pet': {
        'name': '콩이',
        'species': 'dog',
        'breed': '말티즈',
        'sex': 'female',
        'neutered': true,
        'birth_date': null,
        'birth_year': 2021,
        'weight_kg': 3.2,
        'no_known_conditions': false,
        'conditions': [
          {'type_code': 'patella_luxation', 'custom_label': null, 'note': '2기'},
          {'type_code': 'other', 'custom_label': '눈물 자국', 'note': null},
        ],
        'memo': null,
      },
    });
    expect(detail.customer.phone, '01012345678');
    expect(
      detail.customer.marketingConsentChangedAt,
      DateTime.utc(2026, 9, 20, 12),
    );
    expect(detail.pets.single.conditions.single.displayLabel, '슬개골 탈구');
  });

  test('생일은 YYYY-MM-DD 로 보낸다', () async {
    final s = _build((options, body) {
      return FakeResponse(statusCode: 200, data: petDetailJson());
    });

    await s.api.updatePet(
      3,
      11,
      PetFields(
        name: '콩이',
        species: 'cat',
        breed: '코숏',
        sex: 'male',
        neutered: false,
        birthDate: DateTime(2021, 3, 4),
        birthYear: null,
        weightKg: 4,
        noKnownConditions: true,
        conditions: const [],
        memo: null,
      ),
    );

    final sent = _json(s.adapter.lastBodyByPath['/v1/shops/3/pets/11']);
    expect(s.adapter.requests.single.method, 'PUT');
    expect(sent['birth_date'], '2021-03-04');
    expect(sent['birth_year'], isNull);
    expect(sent['no_known_conditions'], isTrue);
    expect(sent['conditions'], isEmpty);
  });

  test('반려동물 상세를 해석한다 — 몸무게 정수, 기타 질병 이름, 무지개다리, 보호자 가린 번호', () async {
    final s = _build((options, body) {
      expect(options.path, '/v1/shops/3/pets/11');
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(
          pet: petJson(
            weightKg: 4,
            birthDate: null,
            birthYear: 2020,
            conditions: [
              conditionJson(
                typeCode: 'other',
                label: '기타',
                customLabel: '눈물 자국',
                note: null,
              ),
            ],
            passedAwayAt: '2026-09-21T03:00:00Z',
            photo: 'http://media.test/b/thumb/shops/3/51.jpg?sig=a',
          ),
          siblings: [siblingJson()],
        ),
      );
    });

    final detail = await s.api.pet(3, 11);

    expect(detail.pet.weightKg, 4.0);
    expect(detail.pet.birthDate, isNull);
    expect(detail.pet.birthYear, 2020);
    expect(detail.pet.conditions.single.displayLabel, '눈물 자국');
    expect(detail.pet.passedAway, isTrue);
    expect(detail.owner.phoneMasked, '010-12··-5678');
    expect(detail.siblings.single.name, '두부');
    expect(detail.pet.photo, 'http://media.test/b/thumb/shops/3/51.jpg?sig=a');
  });

  test('나머지 경로와 메서드', () async {
    final s = _build((options, body) {
      final key = '${options.method} ${options.path}';
      switch (key) {
        case 'GET /v1/shops/3/customers/7':
        case 'PUT /v1/shops/3/customers/7':
          return FakeResponse(statusCode: 200, data: customerDetailJson());
        case 'POST /v1/shops/3/customers/7/pets':
        case 'POST /v1/shops/3/pets/11/passed-away':
        case 'DELETE /v1/shops/3/pets/11/passed-away':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'DELETE /v1/shops/3/customers/7':
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(statusCode: 204);
        case 'GET /v1/shops/3/pet-condition-types':
          return const FakeResponse(statusCode: 200, data: conditionTypesJson);
      }
      fail('예상하지 못한 요청: $key');
    });

    await s.api.customer(3, 7);
    await s.api.updateCustomer(3, 7, _customerFields);
    await s.api.addPet(3, 7, _petFields);
    await s.api.markPassedAway(3, 11);
    await s.api.unmarkPassedAway(3, 11);
    await s.api.deleteCustomer(3, 7);
    await s.api.deletePet(3, 11);
    final types = await s.api.conditionTypes(3);

    expect(types.map((t) => t.code), [
      'patella_luxation',
      'heart_disease',
      'skin_disease',
      'other',
    ]);
    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), [
      'GET /v1/shops/3/customers/7',
      'PUT /v1/shops/3/customers/7',
      'POST /v1/shops/3/customers/7/pets',
      'POST /v1/shops/3/pets/11/passed-away',
      'DELETE /v1/shops/3/pets/11/passed-away',
      'DELETE /v1/shops/3/customers/7',
      'DELETE /v1/shops/3/pets/11',
      'GET /v1/shops/3/pet-condition-types',
    ]);
  });

  test('보호자 연결을 읽는다 — 경로와 응답', () async {
    final s = _build((options, body) {
      expect(body, isNull);
      return FakeResponse(statusCode: 200, data: guardianLinkJson());
    });

    final link = await s.api.guardianLink(3, 7);

    expect(link.linked, isTrue);
    expect(link.linkedAt, '2026-11-13T10:30:00+09:00');
    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), [
      'GET /v1/shops/3/customers/7/guardian-link',
    ]);
  });

  test('연결이 없으면 linked 가 false 이고 날짜가 null 이다', () {
    final link = GuardianLink.fromJson(guardianLinkJson(linked: false));
    expect(link.linked, isFalse);
    expect(link.linkedAt, isNull);
  });

  test('이은 날이 없거나 글자가 아니어도 연결됨으로 읽고 날짜는 null 이다', () {
    for (final json in <Map<String, dynamic>>[
      {'linked': true},
      {'linked': true, 'linked_at': null},
      {'linked': true, 'linked_at': 5},
    ]) {
      final link = GuardianLink.fromJson(json);
      expect(link.linked, isTrue, reason: '$json');
      expect(link.linkedAt, isNull, reason: '$json');
    }
  });

  test('linked 가 true 가 아니면(없음·글자·null) 연결 없음이다', () {
    for (final json in <Map<String, dynamic>>[
      {},
      {'linked': 'true'},
      {'linked': null},
      {'linked': 1},
    ]) {
      expect(GuardianLink.fromJson(json).linked, isFalse, reason: '$json');
    }
  });

  test('모르는 칸이 더 와도 읽는다', () {
    final link = GuardianLink.fromJson({
      ...guardianLinkJson(),
      'guardian_name': '누군가',
    });
    expect(link.linked, isTrue);
  });

  test('보호자 연결을 끊는다 — DELETE 이고 본문이 없다', () async {
    final s = _build((options, body) {
      expect(body, isNull);
      return const FakeResponse(statusCode: 204);
    });

    await s.api.endGuardianLink(3, 7);

    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), [
      'DELETE /v1/shops/3/customers/7/guardian-link',
    ]);
  });

  test('없는 연결을 끊으면 GUARDIAN_LINK_NOT_FOUND 를 던진다', () async {
    final s = _build(
      (options, body) => const FakeResponse(
        statusCode: 404,
        data: {'code': 'GUARDIAN_LINK_NOT_FOUND', 'message': 'x'},
      ),
    );

    await expectLater(
      s.api.endGuardianLink(3, 7),
      throwsA(
        isA<ApiException>().having(
          (e) => e.code,
          'code',
          'GUARDIAN_LINK_NOT_FOUND',
        ),
      ),
    );
  });

  test('미용 동의를 적는다 — 날짜를 주지 않으면 received_on 은 null', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: petDetailJson(pet: petJson(groomingConsentOn: '2026-11-14')),
      ),
    );

    final detail = await s.api.setGroomingConsent(3, 11);

    final request = s.adapter.requests.single;
    expect(
      '${request.method} ${request.path}',
      'PUT /v1/shops/3/pets/11/grooming-consent',
    );
    expect(_json(s.adapter.lastBodyByPath[request.path]), {'received_on': null});
    expect(detail.pet.groomingConsentOn, DateTime(2026, 11, 14));
  });

  test('미용 동의에 받은 날을 주면 날짜만 보낸다', () async {
    final s = _build(
      (options, body) => FakeResponse(statusCode: 200, data: petDetailJson()),
    );

    await s.api.setGroomingConsent(3, 11, receivedOn: DateTime(2026, 11, 3));

    expect(
      _json(s.adapter.lastBodyByPath['/v1/shops/3/pets/11/grooming-consent']),
      {'received_on': '2026-11-03'},
    );
  });

  test('미용 동의를 지운다', () async {
    final s = _build(
      (options, body) => FakeResponse(statusCode: 200, data: petDetailJson()),
    );

    final detail = await s.api.clearGroomingConsent(3, 11);

    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), [
      'DELETE /v1/shops/3/pets/11/grooming-consent',
    ]);
    expect(detail.pet.groomingConsentOn, isNull);
  });

  test('주의 표시를 적고 사유·기한을 읽는다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: customerDetailJson(
          customer: customerJson(caution: cautionJson(reason: '노쇼 2번')),
        ),
      ),
    );

    final detail = await s.api.setCaution(3, 7, '노쇼 2번');

    final request = s.adapter.requests.single;
    expect(
      '${request.method} ${request.path}',
      'PUT /v1/shops/3/customers/7/caution',
    );
    expect(_json(s.adapter.lastBodyByPath[request.path]), {'reason': '노쇼 2번'});
    expect(detail.customer.caution!.reason, '노쇼 2번');
    expect(detail.customer.caution!.until, DateTime(2027, 11, 14));
  });

  test('주의 표시를 지운다', () async {
    final s = _build(
      (options, body) =>
          FakeResponse(statusCode: 200, data: customerDetailJson()),
    );

    final detail = await s.api.clearCaution(3, 7);

    expect(s.adapter.requests.map((r) => '${r.method} ${r.path}'), [
      'DELETE /v1/shops/3/customers/7/caution',
    ]);
    expect(detail.customer.caution, isNull);
  });

  test('주의 칸이 없는 옛 응답도 읽는다 — 목록은 false, 상세는 null', () {
    final family = familyJson()..remove('caution');
    final customer = customerJson()..remove('caution');
    final petDetail = petDetailJson()..remove('caution');
    final pet = petJson()..remove('grooming_consent_on');

    expect(FamilyCard.fromJson(family).caution, isFalse);
    expect(Customer.fromJson(customer).caution, isNull);
    expect(PetDetail.fromJson(petDetail).caution, isNull);
    expect(Pet.fromJson(pet).groomingConsentOn, isNull);
  });

  test('목록 줄과 반려동물 상세의 주의를 읽는다', () {
    expect(FamilyCard.fromJson(familyJson(caution: true)).caution, isTrue);
    expect(
      PetDetail.fromJson(petDetailJson(caution: cautionJson())).caution!.reason,
      '노쇼 2번',
    );
  });
}
