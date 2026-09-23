import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

VisitTestBackend _backend() => VisitTestBackend({
  'GET /v1/shops/3/closed-dates': (o, b) => FakeResponse(
    statusCode: 200,
    data: {
      'items': [
        {'date': '2026-10-09', 'note': '한글날'},
      ],
    },
  ),
  'PUT /v1/shops/3/visit-settings': (o, b) => FakeResponse(
    statusCode: 200,
    data: settingsJson(opensAt: '09:30:00', closedWeekdays: [0, 6]),
  ),
  'POST /v1/shops/3/closed-dates': (o, b) =>
      FakeResponse(statusCode: 200, data: {'date': '2026-12-25', 'note': null}),
  'DELETE /v1/shops/3/closed-dates/2026-10-09': (o, b) =>
      const FakeResponse(statusCode: 204),
});

Future<CustomerTestSetup> _open(
  WidgetTester tester, {
  VisitTestBackend? backend,
  String role = 'owner',
}) async {
  final setup = CustomerTestSetup(
    (backend ?? _backend()).call,
    role: role,
    overrides: _today,
  );
  addTearDown(setup.container.dispose);
  useTallView(tester);
  await pushOnHome<Object?>(tester, setup, '/settings/schedule');
  return setup;
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await settle(tester);
}

void main() {
  testWidgets('영업시간·기본 소요·쉬는 요일·임시 휴무를 서버 값으로 보인다', (tester) async {
    await _open(tester);

    expect(find.byKey(ScreenKeys.settingsSchedule), findsOneWidget);
    expect(find.text('10:00'), findsOneWidget);
    expect(find.text('19:00'), findsOneWidget);
    expect(find.text(AppStrings.durationText(120)), findsOneWidget);
    final monday = tester.widget<AppChoiceChip>(
      find.byWidgetPredicate((w) => w is AppChoiceChip && w.label == '월'),
    );
    expect(monday.selected, isTrue);
    expect(find.text('10월 9일 금 · 한글날'), findsOneWidget);
  });

  testWidgets('시각을 시트에서 고르고 요일·소요를 바꿔 저장하면 전체를 PUT 으로 보낸다', (tester) async {
    final backend = _backend();
    Map<String, dynamic>? sent;
    backend.routes['PUT /v1/shops/3/visit-settings'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(statusCode: 200, data: settingsJson());
    };
    await _open(tester, backend: backend);

    await _tap(tester, find.bySemanticsLabel(AppStrings.opensAtLabel));
    expect(find.text(AppStrings.pickTimeTitle), findsOneWidget);
    await _tap(tester, find.bySemanticsLabel('09'));
    await _tap(tester, find.bySemanticsLabel('30'));
    await _tap(tester, _button(AppStrings.confirm));
    expect(find.text('09:30'), findsOneWidget);
    await _tap(tester, find.bySemanticsLabel('일'));
    // 한 번 누르면 10분, 길게 누르면 30분.
    await _tap(tester, find.bySemanticsLabel(AppStrings.longer));
    expect(find.text(AppStrings.durationText(130)), findsOneWidget);
    await tester.longPress(find.bySemanticsLabel(AppStrings.shorter));
    await settle(tester);
    expect(find.text(AppStrings.durationText(100)), findsOneWidget);
    await tester.longPress(find.bySemanticsLabel(AppStrings.longer));
    await settle(tester);
    await tester.longPress(find.bySemanticsLabel(AppStrings.longer));
    await settle(tester);
    await _tap(tester, _button(AppStrings.save));

    expect(sent, {
      'opens_at': '09:30',
      'closes_at': '19:00',
      'default_duration_minutes': 160,
      'closed_weekdays': [0, 6],
    });
    expect(find.text(AppStrings.saved), findsOneWidget);
  });

  testWidgets('닫는 시각이 여는 시각보다 빠르면 보내지 않고 알린다', (tester) async {
    final setup = await _open(tester);

    await _tap(tester, find.bySemanticsLabel(AppStrings.closesAtLabel));
    await _tap(tester, find.bySemanticsLabel('09'));
    await _tap(tester, _button(AppStrings.confirm));
    await _tap(tester, _button(AppStrings.save));

    expect(find.text(AppStrings.closesBeforeOpens), findsOneWidget);
    expect(setup.calls, isNot(contains('PUT /v1/shops/3/visit-settings')));
  });

  testWidgets('임시 휴무를 더하고 지운다 — 잘못된 날짜는 보내지 않는다', (tester) async {
    final backend = _backend();
    Map<String, dynamic>? added;
    backend.routes['POST /v1/shops/3/closed-dates'] = (o, body) {
      added = bodyOf(body);
      return FakeResponse(
        statusCode: 200,
        data: {'date': '2026-12-25', 'note': '성탄절'},
      );
    };
    final setup = await _open(tester, backend: backend);

    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), '2026.09.01');
    await _tap(tester, _button(AppStrings.addClosedDate));
    expect(find.text(AppStrings.closedDateInvalid), findsOneWidget);
    expect(added, isNull);

    await tester.enterText(fields.at(0), '2026.12.25');
    await tester.enterText(fields.at(1), '성탄절');
    await _tap(tester, _button(AppStrings.addClosedDate));
    expect(added, {'date': '2026-12-25', 'note': '성탄절'});
    expect(
      setup.calls.where((c) => c == 'GET /v1/shops/3/closed-dates'),
      hasLength(2),
    );

    await _tap(tester, find.bySemanticsLabel('${AppStrings.delete} 10월 9일 금'));
    expect(setup.calls, contains('DELETE /v1/shops/3/closed-dates/2026-10-09'));
  });

  testWidgets('서버가 거절하면(직원의 403) 문구를 보이고 남는다', (tester) async {
    final backend = _backend();
    backend.routes['PUT /v1/shops/3/visit-settings'] = (o, b) =>
        const FakeResponse(
          statusCode: 403,
          data: {'code': 'PERMISSION_DENIED', 'message': 'x'},
        );
    await _open(tester, backend: backend);

    await _tap(tester, _button(AppStrings.save));

    expect(find.byKey(ScreenKeys.settingsSchedule), findsOneWidget);
    expect(find.textContaining('권한이 없습니다'), findsOneWidget);
  });

  testWidgets('설정을 불러오지 못하면 다시 시도한다', (tester) async {
    var fail = true;
    final backend = _backend();
    final ok = backend.routes['GET /v1/shops/3/visit-settings']!;
    backend.routes['GET /v1/shops/3/visit-settings'] = (o, b) =>
        fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
    await _open(tester, backend: backend);
    expect(_button(AppStrings.retry), findsOneWidget);

    fail = false;
    await _tap(tester, _button(AppStrings.retry));

    expect(find.text('10:00'), findsOneWidget);
  });
}
