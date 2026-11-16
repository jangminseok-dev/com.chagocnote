import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../../support/customer_test_app.dart';
import '../../../../support/fake_http_client_adapter.dart';
import '../../../../support/visit_fixtures.dart';
import '../../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

/// 다시 올 때 설정을 읽고 쓰는 서버. PUT 은 받은 칸만 바꾼다(서버 계약).
class _Server {
  _Server() {
    backend = VisitTestBackend({
      'GET /v1/shops/3/closed-dates': (o, b) =>
          FakeResponse(statusCode: 200, data: {'items': <Object>[]}),
      'GET /v1/shops/3/revisit-settings': (o, b) =>
          FakeResponse(statusCode: 200, data: current),
      'PUT /v1/shops/3/revisit-settings': (o, body) {
        final sent = bodyOf(body);
        puts.add(sent);
        if (fail) {
          return const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL', 'message': 'x'});
        }
        current = {...current, ...sent};
        return FakeResponse(statusCode: 200, data: current);
      },
      'GET /v1/shops/3/revisits/counts': (o, b) =>
          FakeResponse(statusCode: 200, data: {'soon': 3, 'due': 2}),
    });
  }

  late final VisitTestBackend backend;
  Map<String, dynamic> current = revisitSettingsJson();
  final puts = <Map<String, dynamic>>[];
  bool fail = false;
}

Future<CustomerTestSetup> _open(WidgetTester tester, _Server server) async {
  final setup = CustomerTestSetup(server.backend.call, overrides: _today);
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 2400);
  await pushOnHome<Object?>(tester, setup, '/settings/schedule');
  return setup;
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await settle(tester);
}

void main() {
  testWidgets('예약 설정에 다시 올 때의 여섯 줄이 줄 이름과 지금 값으로 보인다', (tester) async {
    await _open(tester, _Server());

    for (final label in [
      AppStrings.revisitDefaultWeeksLabel,
      AppStrings.revisitSoonDaysLabel,
      AppStrings.revisitMessageLabel,
      AppStrings.revisitCountUnsentLabel,
      AppStrings.revisitSampleVisitsLabel,
      AppStrings.revisitMinGapLabel,
    ]) {
      expect(find.text(label), findsOneWidget, reason: label);
    }
    expect(find.text(AppStrings.revisitDefaultWeeksNote(4)), findsOneWidget);
    expect(find.text(AppStrings.revisitSoonCountNote(3)), findsOneWidget);
    expect(find.text(AppStrings.revisitCountUnsentNote), findsOneWidget);
    expect(find.text(AppStrings.revisitSampleVisitsNote(6)), findsOneWidget);
    expect(find.text(AppStrings.revisitMinGapNote(7)), findsOneWidget);
  });

  testWidgets('숫자 줄을 누르면 시트에서 올리고 저장한다 — 그 칸 하나만 보내고 다시 읽은 값으로 그린다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.text(AppStrings.revisitDefaultWeeksLabel));
    expect(find.text('4주'), findsWidgets);
    await _tap(tester, find.bySemanticsLabel(AppStrings.stepUp).last);
    await _tap(tester, find.bySemanticsLabel(AppStrings.stepUp).last);
    expect(find.text(AppStrings.revisitDefaultWeeksNote(6)), findsOneWidget);
    await _tap(tester, _button(AppStrings.save).last); // 시트의 [저장](화면의 일정 [저장] 말고)

    expect(server.puts, [
      {'default_cycle_weeks': 6},
    ]);
    expect(find.text(AppStrings.revisitDefaultWeeksNote(6)), findsOneWidget);
  });

  testWidgets('시트를 닫으면 보내지 않는다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.text(AppStrings.revisitMinGapLabel));
    await tester.tapAt(const Offset(10, 10));
    await settle(tester);

    expect(server.puts, isEmpty);
  });

  testWidgets('알림장을 남은 일로 세기는 누르면 바로 보낸다 — 실패하면 알리고 값은 그대로', (tester) async {
    final server = _Server();
    await _open(tester, server);

    final toggle = find.byWidgetPredicate(
      (w) => w is AppSwitch && w.semanticLabel == AppStrings.revisitCountUnsentLabel,
    );
    await _tap(tester, toggle);
    expect(server.puts.single, {'count_unsent_reports': false});
    expect(tester.widget<AppSwitch>(toggle).value, isFalse);

    server.fail = true;
    await _tap(tester, toggle);
    expect(find.byType(SnackBar), findsOneWidget);
    expect(tester.widget<AppSwitch>(toggle).value, isFalse);
  });

  testWidgets('보낼 글 줄을 누르면 안내 글 템플릿 화면으로 간다', (tester) async {
    await _open(tester, _Server());

    await _tap(tester, find.text(AppStrings.revisitMessageLabel));

    expect(find.byKey(ScreenKeys.revisitMessage), findsOneWidget);
  });
}
