import 'dart:convert';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

void _tallView(WidgetTester tester) {
  tester.view.physicalSize = const Size(800, 1600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Future<void> _open(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/pets/11');
  await tester.pumpAndSettle();
  setup.container.read(routerProvider).push('/customers/7/edit');
  await tester.pumpAndSettle();
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

FakeHandler _routes({FakeResponse? put, FakeResponse? delete}) =>
    (options, body) {
      switch ('${options.method} ${options.path}') {
        case 'GET /v1/shops/3/customers':
          return FakeResponse(statusCode: 200, data: pageJson());
        case 'GET /v1/shops/3/pets/11':
          return FakeResponse(statusCode: 200, data: petDetailJson());
        case 'GET /v1/shops/3/customers/7':
          return FakeResponse(
            statusCode: 200,
            data: customerDetailJson(
              customer: customerJson(phoneAlt: '0212345678'),
            ),
          );
        case 'PUT /v1/shops/3/customers/7':
          return put ??
              FakeResponse(statusCode: 200, data: customerDetailJson());
        case 'DELETE /v1/shops/3/customers/7':
          return delete ?? const FakeResponse(statusCode: 204);
      }
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    };

void main() {
  testWidgets('지금 값을 채워 두고, 번호는 숫자만 보낸 뒤 상세로 돌아간다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes());
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
    expect(find.widgetWithText(TextField, '김민지'), findsOneWidget);
    expect(find.widgetWithText(TextField, '010-1234-5678'), findsOneWidget);
    expect(find.widgetWithText(TextField, '02-1234-5678'), findsOneWidget);

    await tester.enterText(
      find.widgetWithText(TextField, '010-1234-5678'),
      '010-9999-8888',
    );
    await tester.tap(find.bySemanticsLabel(AppStrings.marketingDeclined));
    await tester.pump();
    await tester.tap(_button(AppStrings.save));
    await tester.pumpAndSettle();

    expect(
      jsonDecode(
        utf8.decode(setup.adapter.lastBodyByPath['/v1/shops/3/customers/7']!),
      ),
      {
        'name': '김민지',
        'phone': '01099998888',
        'phone_alt': '0212345678',
        'marketing_consent': false,
        'memo': '오후 방문 선호',
      },
    );
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('번호·보조 연락처 형식이 틀리면 요청 없이 알린다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes());
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.enterText(
      find.widgetWithText(TextField, '010-1234-5678'),
      '010-12',
    );
    await tester.enterText(
      find.widgetWithText(TextField, '02-1234-5678'),
      '1234',
    );
    await tester.tap(_button(AppStrings.save));
    await tester.pump();

    expect(find.text(AppStrings.phoneInvalid), findsOneWidget);
    expect(find.text(AppStrings.phoneAltInvalid), findsOneWidget);
    expect(setup.calls, isNot(contains('PUT /v1/shops/3/customers/7')));
  });

  testWidgets('다른 고객의 번호면(CUSTOMER_PHONE_TAKEN) 문구를 보이고 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        put: const FakeResponse(
          statusCode: 409,
          data: {'code': 'CUSTOMER_PHONE_TAKEN', 'message': 'x'},
        ),
      ),
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.save));
    await tester.pumpAndSettle();

    expect(find.text('이미 등록된 전화번호예요.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
  });

  testWidgets('직원에게는 고객 삭제가 보이지 않는다(C4 — 경계는 서버 403)', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes(), role: 'staff');
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(_button(AppStrings.deleteCustomer), findsNothing);
  });

  testWidgets('사장은 확인을 거쳐 고객을 삭제하고, 홈의 고객 탭으로 돌아가 목록을 다시 부른다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(_routes());
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await tester.pumpAndSettle();
    await tester.tap(find.text(AppStrings.tabCustomers));
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).push('/pets/11');
    await tester.pumpAndSettle();
    setup.container.read(routerProvider).push('/customers/7/edit');
    await tester.pumpAndSettle();

    await tester.tap(_button(AppStrings.deleteCustomer));
    await tester.pumpAndSettle();
    expect(find.text(AppStrings.deleteCustomerConfirm), findsOneWidget);
    await tester.tap(_button(AppStrings.deleteCustomer).last);
    await tester.pump(const Duration(milliseconds: 1));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byKey(ScreenKeys.petDetail), findsNothing);
    final afterDelete = setup.calls.sublist(
      setup.calls.indexOf('DELETE /v1/shops/3/customers/7'),
    );
    expect(afterDelete, [
      'DELETE /v1/shops/3/customers/7',
      'GET /v1/shops/3/customers',
    ]);
  });

  testWidgets('서버가 삭제를 거절하면(PERMISSION_DENIED) 문구를 보이고 남는다', (tester) async {
    _tallView(tester);
    final setup = CustomerTestSetup(
      _routes(
        delete: const FakeResponse(
          statusCode: 403,
          data: {'code': 'PERMISSION_DENIED', 'message': 'x'},
        ),
      ),
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.deleteCustomer));
    await tester.pumpAndSettle();
    await tester.tap(_button(AppStrings.deleteCustomer).last);
    await tester.pumpAndSettle();

    expect(find.text('이 작업을 할 권한이 없어요.'), findsOneWidget);
    expect(find.byKey(ScreenKeys.customerEdit), findsOneWidget);
  });
}
