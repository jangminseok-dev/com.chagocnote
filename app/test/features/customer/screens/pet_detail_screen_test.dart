import 'dart:async';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

/// 홈에서 반려동물 상세를 쌓아 연다(뒤로 가면 홈).
Future<void> _openPet(
  WidgetTester tester,
  CustomerTestSetup setup,
  int petId,
) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/$petId');
  await tester.pumpAndSettle();
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Future<void> _chooseAction(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(AppStrings.more));
  await tester.pumpAndSettle();
  await tester.tap(find.text(label));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('이름·질병 수·요약과 탭 세 개를 보이고, 보호자 탭은 전체 번호를 고객 상세에서 받는다', (
    tester,
  ) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/customers/7':
          return FakeResponse(statusCode: 200, data: customerDetailJson());
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);

    await _openPet(tester, setup, 11);

    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    expect(find.text('콩이'), findsOneWidget);
    expect(find.text(AppStrings.conditionCount(1)), findsOneWidget);
    expect(find.text('강아지 · 말티즈 · 여아(중성화) · 5살 · 3.2kg'), findsOneWidget);
    expect(find.text('2021.03.04'), findsOneWidget);
    expect(find.text('귀 만지면 싫어함'), findsOneWidget);
    expect(setup.calls, isNot(contains('GET /v1/shops/3/customers/7')));

    await tester.tap(find.text(AppStrings.petTabConditions));
    await tester.pumpAndSettle();
    expect(find.text('슬개골 탈구'), findsOneWidget);
    expect(find.text('2기'), findsOneWidget);

    await tester.tap(find.text(AppStrings.petTabOwner));
    await tester.pumpAndSettle();
    expect(find.text('010-1234-5678'), findsOneWidget);
    expect(
      find.text('${AppStrings.marketingAgreed} · 2026.09.20'),
      findsOneWidget,
    );
    expect(find.text('오후 방문 선호'), findsOneWidget);
  });

  testWidgets('질병 없음을 확인한 아이는 질병 탭에 그렇게 보인다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(
          pet: petJson(noKnownConditions: true, birthDate: null),
        ),
      );
    });
    addTearDown(setup.container.dispose);

    await _openPet(tester, setup, 11);
    expect(find.text(AppStrings.conditionCount(0)), findsNothing);
    expect(find.text(AppStrings.ageUnknown), findsOneWidget);

    await tester.tap(find.text(AppStrings.petTabConditions));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.noKnownConditionsConfirmed), findsOneWidget);
  });

  testWidgets('무지개다리는 확인을 거쳐 표시하고, 다시 불러온 상세에 표시가 보인다', (tester) async {
    var passed = false;
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(
                passedAwayAt: passed ? '2026-09-22T01:00:00Z' : null,
              ),
            ),
          );
        case 'POST /v1/shops/3/pets/11/passed-away':
          passed = true;
          return FakeResponse(statusCode: 200, data: petDetailJson());
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.markPassedAway);
    expect(find.text(AppStrings.markPassedAwayConfirm), findsOneWidget);
    await tester.tap(_button(AppStrings.markPassedAway));
    await tester.pumpAndSettle();

    expect(setup.calls, contains('POST /v1/shops/3/pets/11/passed-away'));
    expect(find.text(AppStrings.passedAwayBadge), findsOneWidget);
  });

  testWidgets('무지개다리 되돌리기는 확인 없이 바로 보낸다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(passedAwayAt: '2026-09-22T01:00:00Z'),
            ),
          );
        case 'DELETE /v1/shops/3/pets/11/passed-away':
          return FakeResponse(statusCode: 200, data: petDetailJson());
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.unmarkPassedAway);

    expect(setup.calls, contains('DELETE /v1/shops/3/pets/11/passed-away'));
  });

  testWidgets('삭제는 확인을 거쳐 보내고, 끝나면 앞 화면으로 돌아간다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.deletePet);
    await tester.tap(_button(AppStrings.delete));
    await tester.pumpAndSettle();

    expect(
      setup.calls.where((c) => c == 'DELETE /v1/shops/3/pets/11'),
      hasLength(1),
    );
    expect(find.byKey(ScreenKeys.petDetail), findsNothing);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    // 지운 아이의 상세를 다시 부르지 않는다(404 가 잠깐 보이지 않게).
    expect(
      setup.calls.where((c) => c == 'GET /v1/shops/3/pets/11'),
      hasLength(1),
    );
  });

  testWidgets('마지막 반려동물이면(LAST_PET) 문구를 보이고 화면에 남는다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'DELETE /v1/shops/3/pets/11':
          return const FakeResponse(
            statusCode: 409,
            data: {'code': 'LAST_PET', 'message': 'x'},
          );
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.deletePet);
    await tester.tap(_button(AppStrings.delete));
    await tester.pumpAndSettle();

    expect(find.textContaining('고객 삭제'), findsOneWidget);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('쓰기가 도는 동안 수정·더 보기를 막는다(연타 방지)', (tester) async {
    final gate = Completer<FakeResponse>();
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(passedAwayAt: '2026-09-22T01:00:00Z'),
            ),
          );
        case 'DELETE /v1/shops/3/pets/11/passed-away':
          return gate.future;
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await _chooseAction(tester, AppStrings.unmarkPassedAway);
    await tester.tap(find.bySemanticsLabel(AppStrings.more));
    await tester.pumpAndSettle();

    expect(
      find.text(AppStrings.unmarkPassedAway),
      findsNothing,
      reason: '시트가 열리지 않는다',
    );
    expect(
      tester.widget<AppButton>(_button(AppStrings.edit)).onPressed,
      isNull,
    );
    gate.complete(FakeResponse(statusCode: 200, data: petDetailJson()));
    await tester.pumpAndSettle();
    expect(
      tester.widget<AppButton>(_button(AppStrings.edit)).onPressed,
      isNotNull,
    );
  });

  testWidgets('같은 보호자의 다른 아이로 옮기면 화면을 바꿔 끼워, 뒤로 가면 앞 화면이다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(siblings: [siblingJson(petId: 12, name: '두부')]),
          );
        case 'GET /v1/shops/3/pets/12':
          return FakeResponse(
            statusCode: 200,
            data: petDetailJson(
              pet: petJson(petId: 12, name: '두부', breed: '푸들'),
              siblings: [siblingJson(petId: 11, name: '콩이')],
            ),
          );
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    // 형제 줄은 목록 아래쪽에 있다 — 보일 때까지 내린다.
    await tester.scrollUntilVisible(find.text('두부'), 200);
    await tester.tap(find.text('두부'));
    await tester.pumpAndSettle();
    expect(find.textContaining('푸들'), findsOneWidget);

    await tester.tap(find.byType(AppBackButton));
    await tester.pumpAndSettle();
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('조회가 실패하면 뒤로 가기와 다시 시도가 보이고, 다시 시도하면 나온다', (tester) async {
    var calls = 0;
    final setup = CustomerTestSetup((options, body) {
      calls++;
      if (calls == 1) {
        throw DioException.connectionError(
          requestOptions: options,
          reason: '연결 실패',
        );
      }
      return FakeResponse(statusCode: 200, data: petDetailJson());
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    expect(find.byType(AppBackButton), findsOneWidget);
    expect(find.text('콩이'), findsNothing);

    await tester.tap(_button(AppStrings.retry));
    await tester.pumpAndSettle();
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('NOT_A_MEMBER 면 내 정보를 다시 불러온다(C5)', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      return const FakeResponse(
        statusCode: 403,
        data: {'code': 'NOT_A_MEMBER', 'message': 'x'},
      );
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    expect(setup.gateway.refreshMeCallCount, 1);
  });

  testWidgets('반려동물 상세 골든 — 기본 탭', (tester) async {
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    final setup = CustomerTestSetup((options, body) {
      return FakeResponse(
        statusCode: 200,
        data: petDetailJson(siblings: [siblingJson(petId: 12, name: '두부')]),
      );
    });
    addTearDown(setup.container.dispose);
    await _openPet(tester, setup, 11);

    await expectLater(
      find.byKey(ScreenKeys.petDetail),
      matchesGoldenFile('goldens/pet_detail.png'),
    );
  });
}
