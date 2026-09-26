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

/// 폼이 길어 한 화면에 다 들어오게 세로로 긴 화면을 쓴다.
void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

/// 홈에서 [location]을 쌓아 연다(뒤로 가면 홈).
Future<void> _open(
  WidgetTester tester,
  CustomerTestSetup setup,
  String location,
) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push(location);
  await tester.pumpAndSettle();
}

/// 생일 검증의 "오늘"을 고정한다.
final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 22))];

Finder _field(String label) => find.widgetWithText(TextField, label);

Finder _save() =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == AppStrings.save);

Future<void> _tapChip(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(label));
  await tester.pump();
}

Map<String, dynamic> _sent(CustomerTestSetup setup, String path) =>
    jsonDecode(utf8.decode(setup.adapter.lastBodyByPath[path]!))
        as Map<String, dynamic>;

FakeHandler _routes({FutureOr<FakeResponse> Function()? write}) =>
    (options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pet-condition-types':
          return const FakeResponse(statusCode: 200, data: conditionTypesJson);
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/pets/21':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(petId: 21, name: '보리', noKnownConditions: true),
            ),
          );
        case 'PUT /v1/shops/3/pets/11':
        case 'PUT /v1/shops/3/pets/21':
        case 'POST /v1/shops/3/customers/7/pets':
          if (write != null) return write();
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(petId: 21, name: '보리', noKnownConditions: true),
            ),
          );
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    };

void main() {
  testWidgets('수정은 지금 값을 채워 두고, 바꾼 값을 통째로 보낸 뒤 상세로 돌아간다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11');
    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.edit,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
    expect(find.text(AppStrings.editPetTitle), findsOneWidget);
    expect(find.widgetWithText(TextField, '콩이'), findsOneWidget);
    expect(find.widgetWithText(TextField, '2021.03.04'), findsOneWidget);
    expect(find.widgetWithText(TextField, '3.2'), findsOneWidget);
    expect(find.widgetWithText(TextField, '2기'), findsOneWidget);

    await tester.enterText(_field(AppStrings.weightLabel), '3.5');
    await tester.tap(_save());
    await tester.pumpAndSettle();

    expect(_sent(setup, '/v1/shops/3/pets/11'), {
      'name': '콩이',
      'species': 'dog',
      'breed': '말티즈',
      'sex': 'female',
      'neutered': true,
      'birth_date': '2021-03-04',
      'birth_year': null,
      'weight_kg': 3.5,
      'no_known_conditions': false,
      'conditions': [
        {'type_code': 'patella_luxation', 'custom_label': null, 'note': '2기'},
      ],
      'memo': '귀 만지면 싫어함',
    });
    expect(find.byKey(ScreenKeys.petForm), findsNothing);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('추가는 빈 폼에서 시작하고, 저장하면 새 아이의 상세로 바꿔 간다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/customers/7/pets/new');

    expect(find.text(AppStrings.addPetTitle), findsOneWidget);
    await tester.enterText(_field(AppStrings.petNameLabel), ' 보리 ');
    await _tapChip(tester, AppStrings.speciesCat);
    await _tapChip(tester, '코리안 숏헤어');
    await _tapChip(tester, AppStrings.sexMale);
    await _tapChip(tester, AppStrings.neuteredNo);
    await _tapChip(tester, AppStrings.ageByBirthYear);
    await tester.enterText(find.byKey(const Key('birth_year_field')), '2020');
    await tester.enterText(_field(AppStrings.weightLabel), '4');
    await _tapChip(tester, AppStrings.noKnownConditions);
    await tester.tap(_save());
    await tester.pumpAndSettle();

    expect(_sent(setup, '/v1/shops/3/customers/7/pets'), {
      'name': '보리',
      'species': 'cat',
      'breed': '코리안 숏헤어',
      'sex': 'male',
      'neutered': false,
      'birth_date': null,
      'birth_year': 2020,
      'weight_kg': 4.0,
      'no_known_conditions': true,
      'conditions': <dynamic>[],
      'memo': null,
    });
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    expect(find.text('보리'), findsOneWidget);
    // 추가 화면은 상세로 바꿔 끼웠다 — 뒤로 가면 홈이다.
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('빈 폼으로 저장하면 요청 없이 필수 항목을 모두 알린다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/customers/7/pets/new');

    await tester.tap(_save());
    await tester.pump();

    for (final message in [
      AppStrings.petNameRequired,
      AppStrings.speciesRequired,
      AppStrings.breedRequired,
      AppStrings.sexRequired,
      AppStrings.neuteredRequired,
      AppStrings.ageRequired,
      AppStrings.weightInvalid,
      AppStrings.healthRequired,
    ]) {
      expect(find.text(message), findsOneWidget, reason: message);
    }
    expect(setup.calls, isNot(contains('POST /v1/shops/3/customers/7/pets')));
  });

  testWidgets('질병 없음과 질병은 함께 설 수 없다 — 하나를 고르면 다른 쪽이 풀린다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await _tapChip(tester, AppStrings.noKnownConditions);
    expect(
      find.widgetWithText(TextField, '2기'),
      findsNothing,
      reason: '고른 질병이 비워진다',
    );

    await _tapChip(tester, '심장 질환');
    await tester.tap(_save());
    await tester.pumpAndSettle();

    final sent = _sent(setup, '/v1/shops/3/pets/11');
    expect(sent['no_known_conditions'], isFalse);
    expect(sent['conditions'], [
      {'type_code': 'heart_disease', 'custom_label': null, 'note': null},
    ]);
  });

  testWidgets('기타는 이름이 있어야 하고, 이름과 메모를 담아 보낸다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/21/edit');

    await _tapChip(tester, '+ ${AppStrings.conditionOther}');
    await tester.tap(_save());
    await tester.pump();
    expect(find.text(AppStrings.otherLabelRequired), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, AppStrings.conditionOtherHint),
      '눈물 자국',
    );
    await tester.enterText(
      find.widgetWithText(TextField, AppStrings.conditionNoteHint),
      '왼쪽',
    );
    await tester.tap(_save());
    await tester.pumpAndSettle();

    final sent = _sent(setup, '/v1/shops/3/pets/21');
    expect(sent['no_known_conditions'], isFalse);
    expect(sent['conditions'], [
      {'type_code': 'other', 'custom_label': '눈물 자국', 'note': '왼쪽'},
    ]);
  });

  testWidgets('생일·태어난 해·몸무게의 형식을 확인한다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await tester.enterText(
      find.byKey(const Key('birth_date_field')),
      '2099.01.01',
    );
    await tester.enterText(_field(AppStrings.weightLabel), '0');
    await tester.tap(_save());
    await tester.pump();
    expect(find.text(AppStrings.birthDateInvalid), findsOneWidget);
    expect(find.text(AppStrings.weightInvalid), findsOneWidget);

    await _tapChip(tester, AppStrings.ageByBirthYear);
    await tester.enterText(find.byKey(const Key('birth_year_field')), '1900');
    await tester.tap(_save());
    await tester.pump();
    expect(find.text(AppStrings.birthYearInvalid), findsOneWidget);
    expect(setup.calls, isNot(contains('PUT /v1/shops/3/pets/11')));
  });

  testWidgets('서버가 거절하면 그 문구를 보이고 폼에 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        write: () => const FakeResponse(
          statusCode: 422,
          data: {'code': 'PET_HEALTH_CONFLICT', 'message': 'x'},
        ),
      ),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await tester.tap(_save());
    await tester.pumpAndSettle();

    expect(find.text('질병과 "질병 없음"을 함께 고를 수 없어요.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.petForm), findsOneWidget);
  });

  testWidgets('저장 중에는 버튼을 막아 요청을 한 번만 보낸다', (tester) async {
    _tallView(tester);
    final gate = Completer<FakeResponse>();
    final setup = CustomerTestSetup(
      _routes(write: () => gate.future),
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup, '/pets/11/edit');

    await tester.tap(_save());
    await tester.pump();
    await tester.tap(_save());
    await tester.pump();
    gate.complete(FakeResponse(statusCode: 200, data: petDetailJson()));
    await tester.pumpAndSettle();

    expect(
      setup.calls.where((c) => c == 'PUT /v1/shops/3/pets/11'),
      hasLength(1),
    );
  });
}
