import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';

/// 홈을 띄우고 고객 탭으로 옮긴다.
Future<void> _openTab(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  await tester.tap(find.text(AppStrings.tabCustomers));
  await tester.pumpAndSettle();
}

/// 조건을 바꾼 뒤 새 요청이 어댑터에 닿을 때까지 돌린다. dio 는 요청을
/// 0초 타이머 뒤에 보내므로, 앞선 결과를 그대로 보여 주느라 그릴 프레임이
/// 없으면 `pumpAndSettle`만으로는 시계가 가지 않는다.
Future<void> _settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

List<Map<String, dynamic>> _listQueries(CustomerTestSetup setup) => [
  for (final r in setup.adapter.requests)
    if (r.path == '/v1/shops/3/customers') r.queryParameters,
];

final _twoFamilies = pageJson(
  items: [
    familyJson(
      customerId: 7,
      pets: [
        petSummaryJson(petId: 11, name: '콩이', hasConditions: true),
        petSummaryJson(petId: 12, name: '두부', breed: '푸들', ageLabel: '3살'),
      ],
    ),
    familyJson(
      customerId: 8,
      name: '박서준',
      phoneMasked: '010-98··-1122',
      pets: [
        petSummaryJson(petId: 13, name: '초코', breed: '비숑', ageLabel: '7살'),
      ],
    ),
  ],
);

void main() {
  testWidgets('가족 카드를 목록으로 보인다 — 보호자와 가린 뒷자리, 아이들, 질병 표시, 반려동물 수', (
    tester,
  ) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);

    await _openTab(tester, setup);

    expect(find.text(AppStrings.petCountText(3)), findsOneWidget);
    expect(find.text('김민지 · ··5678'), findsOneWidget);
    expect(find.text('박서준 · ··1122'), findsOneWidget);
    expect(find.byKey(const Key('pet_row_11')), findsOneWidget);
    expect(find.text('말티즈 · 5살'), findsOneWidget);
    expect(find.text('푸들 · 3살'), findsOneWidget);
    expect(find.text(AppStrings.conditionsBadge), findsOneWidget);
    expect(_listQueries(setup), [
      {'sort': 'recent', 'include_passed': false},
    ]);
  });

  testWidgets('격자로 바꾸면 타일로 보이고 기기에 기억한다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.viewAsGrid));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('pet_tile_11')), findsOneWidget);
    expect(find.byKey(const Key('pet_row_11')), findsNothing);
    expect(await setup.prefs.readCustomerViewMode(), 'grid');
  });

  testWidgets('기억한 보기가 격자면 격자로 시작한다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);
    await setup.prefs.writeCustomerViewMode('grid');

    await _openTab(tester, setup);

    expect(find.byKey(const Key('pet_tile_11')), findsOneWidget);
  });

  testWidgets('정렬과 무지개다리 포함을 바꾸면 그 조건으로 다시 부른다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
    );
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(find.text(AppStrings.sortName));
    await _settle(tester);
    await tester.tap(find.bySemanticsLabel(AppStrings.includePassed));
    await _settle(tester);

    expect(_listQueries(setup), [
      {'sort': 'recent', 'include_passed': false},
      {'sort': 'name', 'include_passed': false},
      {'sort': 'name', 'include_passed': true},
    ]);
  });

  testWidgets('검색은 0.3초 쉰 뒤 보내고, 새 검색을 보내면 늦게 온 옛 결과는 버린다(C12)', (
    tester,
  ) async {
    final slow = Completer<FakeResponse>();
    final setup = CustomerTestSetup((options, body) {
      switch (options.queryParameters['q']) {
        case null:
          return FakeResponse(statusCode: 200, data: _twoFamilies);
        case '콩':
          return slow.future;
        case '초코':
          return FakeResponse(
            statusCode: 200,
            data: pageJson(
              items: [_twoFamilies['items'][1] as Map<String, dynamic>],
            ),
          );
      }
      fail('예상하지 못한 검색어: ${options.queryParameters['q']}');
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.enterText(find.byType(TextField), '콩');
    await tester.pump(const Duration(milliseconds: 299));
    expect(_listQueries(setup), hasLength(1));
    await tester.pump(const Duration(milliseconds: 1));
    await tester.pump(
      const Duration(milliseconds: 1),
    ); // 검색어가 바뀐 화면이 새 조건으로 부른다.
    expect(_listQueries(setup).last['q'], '콩');

    await tester.enterText(find.byType(TextField), '초코');
    await tester.pump(const Duration(milliseconds: 300));
    await _settle(tester);
    expect(find.text('박서준 · ··1122'), findsOneWidget);

    slow.complete(FakeResponse(statusCode: 200, data: _twoFamilies));
    await _settle(tester);

    expect(find.text('김민지 · ··5678'), findsNothing);
    expect(find.text('박서준 · ··1122'), findsOneWidget);
  });

  testWidgets('검색 결과가 없으면 그렇게 말하고, 목록이 비었으면 등록을 안내한다', (tester) async {
    final setup = CustomerTestSetup(
      (options, body) =>
          FakeResponse(statusCode: 200, data: pageJson(items: [])),
    );
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);
    expect(find.text(AppStrings.customersEmpty), findsOneWidget);

    await tester.enterText(find.byType(TextField), '없는이름');
    await tester.pump(const Duration(milliseconds: 300));
    await _settle(tester);

    expect(find.text(AppStrings.customersNoMatch), findsOneWidget);
  });

  testWidgets('아이를 누르면 반려동물 상세로 간다', (tester) async {
    final setup = CustomerTestSetup((options, body) {
      if (options.path == '/v1/shops/3/pets/12') {
        return FakeResponse(
          statusCode: 200,
          data: petDetailJson(pet: petJson(petId: 12, name: '두부')),
        );
      }
      return FakeResponse(statusCode: 200, data: _twoFamilies);
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(find.byKey(const Key('pet_row_12')));
    await tester.pumpAndSettle();

    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('끝까지 내리면 다음 페이지를 붙이고, 실패하면 그 자리에서 다시 시도한다', (tester) async {
    var failNext = true;
    final setup = CustomerTestSetup((options, body) {
      if (options.queryParameters['cursor'] == null) {
        return FakeResponse(
          statusCode: 200,
          data: pageJson(
            items: [
              for (var i = 1; i <= 12; i++)
                familyJson(customerId: i, name: '보호자$i'),
            ],
            nextCursor: 'c1',
          ),
        );
      }
      if (failNext) {
        failNext = false;
        return const FakeResponse(
          statusCode: 500,
          data: {'code': 'INTERNAL', 'message': 'x'},
        );
      }
      return FakeResponse(
        statusCode: 200,
        data: pageJson(items: [familyJson(customerId: 99, name: '마지막보호자')]),
      );
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.fling(find.byType(ListView), const Offset(0, -3000), 3000);
    await tester.pumpAndSettle();
    // 실패한 뒤에는 더 내려도 스크롤로 다시 부르지 않는다.
    await tester.fling(find.byType(ListView), const Offset(0, -3000), 3000);
    await tester.pumpAndSettle();
    expect(_listQueries(setup).where((q) => q['cursor'] == 'c1'), hasLength(1));
    final retry = find.byWidgetPredicate(
      (w) => w is AppButton && w.label == AppStrings.retry,
    );
    // 검색창도 Scrollable 이라 목록의 것을 집어 준다.
    final list = find.descendant(
      of: find.byType(ListView),
      matching: find.byType(Scrollable),
    );
    await tester.scrollUntilVisible(retry, 300, scrollable: list);
    await tester.tap(retry);
    await tester.pumpAndSettle();

    await tester.scrollUntilVisible(
      find.text('마지막보호자 · ··5678'),
      300,
      scrollable: list,
    );

    expect(find.text('마지막보호자 · ··5678'), findsOneWidget);
    expect(_listQueries(setup).where((q) => q['cursor'] == 'c1'), hasLength(2));
  });

  testWidgets('첫 조회가 실패하면 다시 시도할 수 있다', (tester) async {
    var calls = 0;
    final setup = CustomerTestSetup((options, body) {
      calls++;
      if (calls == 1) {
        return const FakeResponse(
          statusCode: 500,
          data: {'code': 'INTERNAL', 'message': 'x'},
        );
      }
      return FakeResponse(statusCode: 200, data: _twoFamilies);
    });
    addTearDown(setup.container.dispose);
    await _openTab(tester, setup);

    await tester.tap(
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.retry,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('김민지 · ··5678'), findsOneWidget);
  });

  for (final grid in [false, true]) {
    testWidgets('고객 탭 골든 — ${grid ? '격자' : '목록'}', (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final setup = CustomerTestSetup(
        (options, body) => FakeResponse(statusCode: 200, data: _twoFamilies),
      );
      addTearDown(setup.container.dispose);
      if (grid) await setup.prefs.writeCustomerViewMode('grid');

      await _openTab(tester, setup);

      await expectLater(
        find.byKey(ScreenKeys.home),
        matchesGoldenFile(
          'goldens/customer_list_${grid ? 'grid' : 'list'}.png',
        ),
      );
    });
  }
}
