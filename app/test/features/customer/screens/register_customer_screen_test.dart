import 'dart:async';
import 'dart:convert';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 22))];

void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

/// 보이는 단계(IndexedStack 의 앞면)의 위젯만 찾는다.
Finder _onStage(Finder finder) => find
    .descendant(
      of: find.byWidgetPredicate((w) => w is IndexedStack),
      matching: finder,
    )
    .hitTestable();

/// 홈의 고객 탭에서 + 버튼으로 등록을 연다.
Future<void> _openFromFab(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  await tester.tap(find.text(AppStrings.tabCustomers));
  await tester.pumpAndSettle();
  await tester.tap(find.bySemanticsLabel(AppStrings.registerCustomer));
  await tester.pumpAndSettle();
}

/// 조회가 나갈 시간을 준다(dio 는 0초 타이머 뒤에 보낸다).
Future<void> _settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

Future<void> _tapChip(WidgetTester tester, String label) async {
  await tester.tap(_onStage(find.bySemanticsLabel(label)));
  await tester.pump();
}

FakeHandler _routes({
  FutureOr<FakeResponse> Function(String phone)? lookup,
  FakeResponse? register,
}) => (options, body) {
  switch ('${options.method} ${options.path}') {
    case 'GET /v1/shops/3/customers':
      return FakeResponse(statusCode: 200, data: pageJson(items: []));
    case 'GET /v1/shops/3/customers/lookup':
      final phone = options.queryParameters['phone'] as String;
      if (lookup != null) return lookup(phone);
      return const FakeResponse(
        statusCode: 404,
        data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
      );
    case 'GET /v1/shops/3/pet-condition-types':
      return const FakeResponse(statusCode: 200, data: conditionTypesJson);
    case 'POST /v1/shops/3/customers':
      return register ??
          FakeResponse(
            statusCode: 201,
            data: customerDetailJson(pets: [petJson(petId: 31, name: '보리')]),
          );
    case 'GET /v1/shops/3/pets/31':
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(pet: petJson(petId: 31, name: '보리')),
      );
    case 'GET /v1/shops/3/pets/new':
      fail('pets/new 는 없는 경로다');
  }
  fail('예상하지 못한 요청: ${options.method} ${options.path}');
};

Future<void> _fillPet(WidgetTester tester) async {
  await tester.enterText(
    _onStage(find.widgetWithText(TextField, AppStrings.petNameLabel)),
    '보리',
  );
  await _tapChip(tester, AppStrings.speciesDog);
  await _tapChip(tester, '푸들');
  await _tapChip(tester, AppStrings.sexFemale);
  await _tapChip(tester, AppStrings.neuteredYes);
  await _tapChip(tester, AppStrings.ageUnknown);
  await tester.enterText(
    _onStage(find.widgetWithText(TextField, AppStrings.weightLabel)),
    '2.8',
  );
  await _tapChip(tester, '슬개골 탈구');
}

void main() {
  testWidgets('새 번호 — 번호 확인, 보호자, 반려동물을 거쳐 한 번에 등록하고 새 아이의 상세로 간다', (
    tester,
  ) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    expect(find.byKey(ScreenKeys.registerCustomer), findsOneWidget);
    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepPhone, 1)),
      findsOneWidget,
    );
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNull,
    );

    await tester.enterText(_onStage(find.byType(TextField)), '010-1234-5678');
    await _settle(tester);
    expect(setup.adapter.requests.last.queryParameters, {
      'phone': '01012345678',
    });
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2)),
      findsOneWidget,
    );
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepPet, 3)),
      findsOneWidget,
    );
    await _fillPet(tester);
    await tester.tap(_onStage(_button(AppStrings.save)));
    await tester.pumpAndSettle();

    final sent = jsonDecode(
      utf8.decode(setup.adapter.lastBodyByPath['/v1/shops/3/customers']!),
    );
    expect(sent, {
      'customer': {
        'name': '김민지',
        'phone': '01012345678',
        'phone_alt': null,
        'marketing_consent': true,
        'memo': null,
      },
      'pet': {
        'name': '보리',
        'species': 'dog',
        'breed': '푸들',
        'sex': 'female',
        'neutered': true,
        'birth_date': null,
        'birth_year': null,
        'weight_kg': 2.8,
        'no_known_conditions': false,
        'conditions': [
          {'type_code': 'patella_luxation', 'custom_label': null, 'note': null},
        ],
        'memo': null,
      },
    });
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    // 등록 화면은 상세로 바꿔 끼웠다 — 뒤로 가면 홈(고객 탭)이다.
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('예약 ①에서 열었으면(?pick=1) 등록한 고객 ID 를 돌려주며 닫는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await tester.pumpAndSettle();
    int? returned;
    setup.container
        .read(routerProvider)
        .push<int>('/customers/new?pick=1')
        .then((id) => returned = id);
    await tester.pumpAndSettle();

    await tester.enterText(_onStage(find.byType(TextField)), '010-1234-5678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await _fillPet(tester);
    await tester.tap(_onStage(_button(AppStrings.save)));
    await tester.pumpAndSettle();

    expect(returned, 7);
    expect(find.byKey(ScreenKeys.petDetail), findsNothing);
    expect(find.byKey(ScreenKeys.registerCustomer), findsNothing);
  });

  testWidgets('이미 있는 번호 — 알려 주고, 그 보호자에게 반려동물 추가로 건너뛴다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        lookup: (phone) => const FakeResponse(
          statusCode: 200,
          data: {
            'customer_id': 7,
            'name': '김민지',
            'pet_names': ['콩이', '두부'],
          },
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);

    expect(
      find.text(AppStrings.lookupFound('김민지', ['콩이', '두부'])),
      findsOneWidget,
    );
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNull,
    );
    await tester.tap(_button(AppStrings.addPetToExisting));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
    expect(find.text(AppStrings.addPetTitle), findsOneWidget);
  });

  testWidgets('번호가 완성되기 전에는 조회하지 않는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '010-1234');
    await _settle(tester);

    expect(setup.calls, isNot(contains('GET /v1/shops/3/customers/lookup')));
  });

  testWidgets('번호를 바꾸면 늦게 온 옛 번호의 조회 결과를 버린다', (tester) async {
    _tallView(tester);
    final slow = Completer<FakeResponse>();
    final setup = CustomerTestSetup(
      _routes(
        lookup: (phone) => phone == '01011112222'
            ? slow.future
            : const FakeResponse(
                statusCode: 404,
                data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
              ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '01011112222');
    // 느린 조회가 도는 동안은 진행 막대가 움직여 settle 하지 않는다 — 한 번만 돌린다.
    await tester.pump(const Duration(milliseconds: 1));
    await tester.enterText(_onStage(find.byType(TextField)), '01033334444');
    await _settle(tester);
    slow.complete(
      const FakeResponse(
        statusCode: 200,
        data: {
          'customer_id': 7,
          'name': '김민지',
          'pet_names': ['콩이'],
        },
      ),
    );
    await _settle(tester);

    expect(find.text(AppStrings.lookupFound('김민지', ['콩이'])), findsNothing);
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNotNull,
    );
  });

  testWidgets('번호를 형식 밖으로 줄이면 늦게 온 옛 번호의 조회 결과를 버린다(A2)', (tester) async {
    _tallView(tester);
    final slow = Completer<FakeResponse>();
    final setup = CustomerTestSetup(
      _routes(lookup: (phone) => slow.future),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);

    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    // 느린 조회가 도는 동안 번호를 형식 밖(9자리)으로 줄인다.
    await tester.pump(const Duration(milliseconds: 1));
    await tester.enterText(_onStage(find.byType(TextField)), '010123456');
    await _settle(tester);
    slow.complete(
      const FakeResponse(
        statusCode: 200,
        data: {
          'customer_id': 7,
          'name': '김민지',
          'pet_names': ['콩이'],
        },
      ),
    );
    await _settle(tester);

    expect(find.text(AppStrings.lookupFound('김민지', ['콩이'])), findsNothing);
    expect(
      tester.widget<AppButton>(_onStage(_button(AppStrings.next))).onPressed,
      isNull,
    );
  });

  testWidgets('앞 단계로 돌아가도 적은 값이 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingDeclined);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepOwner, 2)),
      findsOneWidget,
    );
    expect(_onStage(find.widgetWithText(TextField, '김민지')), findsOneWidget);
  });

  testWidgets('그사이 같은 번호가 등록됐으면(CUSTOMER_PHONE_TAKEN) 문구를 보이고 남는다(C2)', (
    tester,
  ) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        register: const FakeResponse(
          statusCode: 409,
          data: {'code': 'CUSTOMER_PHONE_TAKEN', 'message': 'x'},
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await _fillPet(tester);

    await tester.tap(_onStage(_button(AppStrings.save)));
    await tester.pumpAndSettle();

    expect(find.text('이미 등록된 전화번호예요.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.registerCustomer), findsOneWidget);
  });

  testWidgets('CUSTOMER_PHONE_TAKEN 뒤 1단계로 돌아가면 번호를 다시 조회한다', (tester) async {
    _tallView(tester);
    var lookupCalls = 0;
    final setup = CustomerTestSetup(
      _routes(
        lookup: (phone) {
          lookupCalls++;
          return const FakeResponse(
            statusCode: 404,
            data: {'code': 'CUSTOMER_NOT_FOUND', 'message': 'x'},
          );
        },
        register: const FakeResponse(
          statusCode: 409,
          data: {'code': 'CUSTOMER_PHONE_TAKEN', 'message': 'x'},
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _openFromFab(tester, setup);
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await _fillPet(tester);

    await tester.tap(_onStage(_button(AppStrings.save)));
    await tester.pumpAndSettle();
    expect(lookupCalls, 1);

    // 3단계 → 2단계 → 1단계로 돌아간다.
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();
    expect(
      find.text(AppStrings.registerStepTitle(AppStrings.registerStepPhone, 1)),
      findsOneWidget,
    );

    await tester.tap(_onStage(_button(AppStrings.next)));
    await _settle(tester);

    expect(lookupCalls, 2);
  });

  testWidgets('등록 3단계 골든', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).push('/customers/new');
    await tester.pumpAndSettle();
    await tester.enterText(_onStage(find.byType(TextField)), '01012345678');
    await _settle(tester);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.ownerNameLabel)),
      '김민지',
    );
    await _tapChip(tester, AppStrings.marketingAgreed);
    await tester.tap(_onStage(_button(AppStrings.next)));
    await tester.pumpAndSettle();
    await tester.enterText(
      _onStage(find.widgetWithText(TextField, AppStrings.petNameLabel)),
      '보리',
    );
    await _tapChip(tester, AppStrings.speciesDog);
    FocusManager.instance.primaryFocus?.unfocus();
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.registerCustomer),
      matchesGoldenFile('goldens/register_pet_step.png'),
    );
  });
}
