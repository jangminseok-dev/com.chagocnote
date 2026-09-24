import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_big_date.dart';
import 'package:chagocnote/features/customer/screens/customer_list_tab.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/features/visit/screens/calendar_tab.dart';
import 'package:chagocnote/features/visit/state/calendar_selection.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 22))];

/// 캘린더(월 요약·하루)와 고객 목록을 주는 가짜 서버.
CustomerTestSetup _setup() {
  final backend = VisitTestBackend({
    'POST /v1/shops/3/visits': (o, b) =>
        FakeResponse(statusCode: 201, data: savedJson([visitJson()])),
  });
  return CustomerTestSetup(backend.call, overrides: _today);
}

Future<void> _pumpHome(WidgetTester tester, CustomerTestSetup setup) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await settle(tester);
}

void main() {
  testWidgets('홈은 캘린더 탭으로 열리고, 매장 이름은 매출 탭 머리에 보인다', (tester) async {
    final setup = _setup();
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    expect(find.byKey(ScreenKeys.home), findsOneWidget);
    expect(find.byType(CalendarTab), findsOneWidget);
    expect(find.text('September'), findsOneWidget);
    // 캘린더 탭은 자기 머리를 쓴다 — 큰 날짜 머리와 매장 이름은 없다.
    expect(find.byType(AppBigDate), findsNothing);
    expect(find.text('Hiss Haus'), findsNothing);

    await tester.tap(find.text(AppStrings.tabSales));
    await settle(tester);

    expect(find.text('Hiss Haus'), findsOneWidget);
    expect(find.byType(AppBigDate), findsOneWidget);
    expect(find.text(AppStrings.comingSoonEmptyTitle), findsOneWidget);
  });

  testWidgets('탭을 바꾸면 본문이 바뀐다', (tester) async {
    final setup = _setup();
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    await tester.tap(find.text(AppStrings.tabCustomers));
    await settle(tester);
    expect(find.byType(CalendarTab), findsNothing);
    expect(find.byType(CustomerListTab), findsOneWidget);
    expect(find.text('이수진 · ··5678'), findsOneWidget);

    await tester.tap(find.text(AppStrings.tabCalendar));
    await settle(tester);
    expect(find.byType(CalendarTab), findsOneWidget);
  });

  testWidgets('설정 버튼을 누르면 설정 화면으로 이동한다', (tester) async {
    final setup = _setup();
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.settingsLabel));
    await settle(tester);

    expect(find.byKey(ScreenKeys.settings), findsOneWidget);
  });

  testWidgets('매출 탭의 + 는 준비 중 안내 시트를 띄운다', (tester) async {
    final setup = _setup();
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);
    await tester.tap(find.text(AppStrings.tabSales));
    await settle(tester);

    await tester.tap(find.byIcon(Icons.add));
    await settle(tester);

    expect(find.text(AppStrings.comingSoonSheetText), findsOneWidget);
  });

  testWidgets('캘린더 탭의 + 는 고른 날로 예약 등록을 열고, 저장한 날을 고른다', (tester) async {
    final setup = _setup();
    addTearDown(setup.container.dispose);
    useTallView(tester);
    await _pumpHome(tester, setup);
    await tester.tap(find.bySemanticsLabel('9월 25일 금'));
    await settle(tester);

    await tester.tap(find.bySemanticsLabel(AppStrings.addReservation));
    await settle(tester);
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    await tester.tap(find.text('이수진 · 010-12··-5678'));
    await settle(tester);
    expect(find.bySemanticsLabel('9월 25일 금'), findsOneWidget);
    // 다음 달의 날에 저장하면 달력도 그달로 옮겨 간다.
    await tester.tap(find.bySemanticsLabel(AppStrings.nextWeek));
    await settle(tester);
    await tester.tap(find.bySemanticsLabel('10월 2일 금'));
    await settle(tester);
    await tester.tap(find.bySemanticsLabel('14:00'));
    await settle(tester);
    await tester.tap(find.text(AppStrings.saveReservation('10월 2일 금 14:00')));
    await settle(tester);

    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
    expect(setup.container.read(selectedDateProvider), DateTime(2026, 10, 2));
    expect(find.text('October'), findsOneWidget);
    expect(find.text(AppStrings.dayHeading(2, 5)), findsOneWidget);
  });
}
