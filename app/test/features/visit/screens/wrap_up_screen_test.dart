// 하루 마무리(⑬ 설계 3.6) — 정리 안 된 예약·결제 안 적음·알림장 안 보냄을 한 장씩 넘기며 끝낸다.
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_card.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 10, 2))];
const _wrapUp = '/v1/shops/3/days/2026-10-02/wrap-up';

/// 그날의 장 — 처리하면 서버가 그 장을 뺀다.
class _Server {
  _Server(this.cards) {
    backend = VisitTestBackend({
      'GET $_wrapUp': (o, b) => FakeResponse(statusCode: 200, data: wrapUpJson(cards: cards)),
      'POST /v1/shops/3/visits/transitions': (o, body) {
        final sent = bodyOf(body);
        transitions.add(sent);
        if (transitionFails) {
          return const FakeResponse(statusCode: 409, data: {'code': 'VISIT_STATE_CONFLICT', 'message': 'x'});
        }
        cards.removeWhere((c) => (c['visit'] as Map)['visit_id'] == (sent['visit_ids'] as List).first && c['kind'] == 'unresolved');
        return FakeResponse(statusCode: 200, data: {'visits': [visitJson(visitId: 101, status: 'no_show')]});
      },
      'GET /v1/shops/3/visits/102': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(
          visit: visitJson(visitId: 102, status: 'completed'),
          record: recordJson(visitId: 102, careNote: '잘 참았어요', version: version),
        ),
      ),
      'PUT /v1/shops/3/visits/102/record': (o, body) {
        final sent = bodyOf(body);
        recordPuts.add(sent);
        if (conflictOnce) {
          conflictOnce = false;
          version = 3;
          return const FakeResponse(statusCode: 409, data: {'code': 'RECORD_VERSION_CONFLICT', 'message': 'x'});
        }
        cards.removeWhere((c) => c['kind'] == 'unpaid');
        return FakeResponse(statusCode: 200, data: recordJson(visitId: 102, version: version + 1));
      },
      'PUT /v1/shops/3/visits/103/report-skip': (o, b) {
        skips.add(103);
        cards.removeWhere((c) => c['kind'] == 'report_unsent');
        return const FakeResponse(statusCode: 204);
      },
      'PUT /v1/shops/3/revisit-settings': (o, body) {
        settingsPuts.add(bodyOf(body));
        cards.removeWhere((c) => c['kind'] == 'report_unsent');
        return FakeResponse(statusCode: 200, data: revisitSettingsJson(countUnsent: false));
      },
      'GET /v1/shops/3/visits': (o, b) => FakeResponse(
        statusCode: 200,
        data: dayJson(
          date: o.queryParameters['date'] as String,
          items: [
            dayItemJson(visitJson(visitId: 102, status: 'completed'), reportSent: true),
            dayItemJson(visitJson(visitId: 103, status: 'completed')),
          ],
        ),
      ),
    });
  }

  late final VisitTestBackend backend;
  final List<Map<String, dynamic>> cards;
  final transitions = <Map<String, dynamic>>[];
  final recordPuts = <Map<String, dynamic>>[];
  final skips = <int>[];
  final settingsPuts = <Map<String, dynamic>>[];
  int version = 2;
  bool conflictOnce = false;
  bool transitionFails = false;
}

Map<String, dynamic> _unresolved() =>
    wrapUpCardJson(kind: 'unresolved', visit: visitJson(visitId: 101, status: 'reserved'));
Map<String, dynamic> _unpaid() => wrapUpCardJson(
  kind: 'unpaid',
  visit: visitJson(visitId: 102, status: 'completed', pet: visitPetJson(petId: 12, name: '보리')),
  totalAmount: 30000,
);
Map<String, dynamic> _report() => wrapUpCardJson(
  kind: 'report_unsent',
  visit: visitJson(visitId: 103, status: 'completed', pet: visitPetJson(petId: 13, name: '몽이')),
);

Future<CustomerTestSetup> _open(
  WidgetTester tester,
  _Server server, {
  String role = 'owner',
  String query = '',
}) async {
  final setup = CustomerTestSetup(server.backend.call, role: role, overrides: _today);
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 1400);
  await pushOnHome<Object?>(tester, setup, '/days/2026-10-02/wrap-up$query');
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
  testWidgets('위에 "N개 중 M번째", 장 위에 이름·시각·메뉴 — 정리 안 된 예약은 [노쇼]를 묻고 보내 다음 장으로 간다', (tester) async {
    final server = _Server([_unresolved(), _unpaid()]);
    await _open(tester, server);

    expect(find.byKey(ScreenKeys.wrapUp), findsOneWidget);
    expect(find.text(AppStrings.wrapUpProgress(1, 2)), findsOneWidget);
    expect(find.text(AppStrings.wrapUpKindUnresolved), findsOneWidget);
    expect(_button(AppStrings.actionNoShow), findsOneWidget);
    expect(_button(AppStrings.actionCancelVisit), findsOneWidget);

    await _tap(tester, _button(AppStrings.actionNoShow));
    await _tap(tester, _button(AppStrings.actionNoShow).last);

    expect(server.transitions.single, {
      'visit_ids': [101],
      'action': 'no_show',
    });
    expect(find.text(AppStrings.wrapUpProgress(2, 2)), findsOneWidget);
    expect(find.text(AppStrings.wrapUpKindUnpaid), findsOneWidget);
  });

  testWidgets('결제 장 — 채워 둔 총액에 수단을 고르고 [저장](누르기 둘), 기록의 다른 칸·버전은 그대로 보낸다', (tester) async {
    final server = _Server([_unpaid()]);
    await _open(tester, server);

    final total = find.byKey(const ValueKey('wrap-up-total'));
    expect(tester.widget<TextField>(total).controller!.text, '30000');
    expect(tester.widget<AppButton>(_button(AppStrings.save)).onPressed, isNull);

    await _tap(tester, find.text(AppStrings.paymentCard));
    await _tap(tester, _button(AppStrings.save));

    final sent = server.recordPuts.single;
    expect((sent['total_amount'], sent['payment_method'], sent['care_note'], sent['version']), (
      30000,
      'card',
      '잘 참았어요',
      2,
    ));
    expect(find.text(AppStrings.wrapUpDoneToday), findsOneWidget);
  });

  testWidgets('결제 장의 저장이 버전 충돌이면 다시 읽어 한 번 더 보낸다', (tester) async {
    final server = _Server([_unpaid()])..conflictOnce = true;
    await _open(tester, server);

    await _tap(tester, find.text(AppStrings.paymentCash));
    await _tap(tester, _button(AppStrings.save));

    expect([for (final p in server.recordPuts) p['version']], [2, 3]);
    expect(find.text(AppStrings.wrapUpDoneToday), findsOneWidget);
  });

  testWidgets('알림장 장 — [보내지 않음]으로 넘기고, [미리 보고 보내기]는 미리보기를 연다', (tester) async {
    final server = _Server([_report()]);
    await _open(tester, server);

    expect(_button(AppStrings.wrapUpReportPreview), findsOneWidget);
    await _tap(tester, _button(AppStrings.wrapUpReportSkip));

    expect(server.skips, [103]);
    expect(find.text(AppStrings.wrapUpDoneToday), findsOneWidget);
  });

  testWidgets('사장은 알림장 장 아래 "앞으로 세지 않기"로 매장 설정을 바꾼다 — 직원에게는 없다', (tester) async {
    final server = _Server([_report()]);
    await _open(tester, server);

    await _tap(tester, find.text(AppStrings.wrapUpStopCounting));
    expect(server.settingsPuts, [
      {'count_unsent_reports': false},
    ]);
    expect(find.text(AppStrings.wrapUpDoneToday), findsOneWidget);
  });

  testWidgets('직원에게는 "앞으로 세지 않기"가 없다', (tester) async {
    await _open(tester, _Server([_report()]), role: 'staff');
    expect(find.text(AppStrings.wrapUpStopCounting), findsNothing);
  });

  testWidgets('[건너뛰기]한 장은 남은 일에 그대로 — 끝 화면에 남겨 둔 수와 [다시 보기], 그날의 수에 금액이 없다', (tester) async {
    final server = _Server([_unpaid(), _report()]);
    await _open(tester, server);

    await _tap(tester, _button(AppStrings.wrapUpSkip));
    await _tap(tester, _button(AppStrings.wrapUpSkip));

    expect(find.text(AppStrings.wrapUpDoneToday), findsOneWidget);
    expect(find.text(AppStrings.wrapUpDoneCounts(2, 1)), findsOneWidget);
    expect(find.text(AppStrings.wrapUpSkipped(2)), findsOneWidget);
    expect(find.textContaining('원'), findsNothing);

    await _tap(tester, _button(AppStrings.wrapUpReview));
    expect(find.text(AppStrings.wrapUpProgress(1, 2)), findsOneWidget);
    expect(find.text(AppStrings.wrapUpKindUnpaid), findsOneWidget);
  });

  testWidgets('그 사이 다른 기기가 끝냈으면(409) 알리고 다시 읽어 다음 장으로 간다', (tester) async {
    final server = _Server([_unresolved(), _report()])..transitionFails = true;
    await _open(tester, server);

    // 서버에서는 이미 정리됐다.
    server.cards.removeWhere((c) => c['kind'] == 'unresolved');
    await _tap(tester, _button(AppStrings.actionNoShow));
    await _tap(tester, _button(AppStrings.actionNoShow).last);

    expect(find.byType(SnackBar), findsOneWidget);
    expect(find.text(AppStrings.wrapUpKindReport), findsOneWidget);
  });

  testWidgets('누른 종류부터 연다(?kind=report_unsent)', (tester) async {
    await _open(tester, _Server([_unpaid(), _report()]), query: '?kind=report_unsent');
    expect(find.text(AppStrings.wrapUpKindReport), findsOneWidget);
    expect(find.text(AppStrings.wrapUpProgress(1, 2)), findsOneWidget);
  });

  testWidgets('처음부터 장이 없으면 곧바로 끝 화면 — 지난 날이면 "이날"', (tester) async {
    final server = _Server([]);
    final setup = CustomerTestSetup(
      server.backend.call,
      overrides: [todayProvider.overrideWithValue(DateTime(2026, 10, 5))],
    );
    addTearDown(setup.container.dispose);
    useTallView(tester, height: 1400);
    await pushOnHome<Object?>(tester, setup, '/days/2026-10-02/wrap-up');

    expect(find.text(AppStrings.wrapUpDonePast), findsOneWidget);
    expect(find.text(AppStrings.wrapUpReview), findsNothing);
  });

  testWidgets('결제 장 골든', (tester) async {
    await _open(tester, _Server([_unpaid(), _report()]));
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.wrapUp),
      matchesGoldenFile('goldens/wrap_up_unpaid.png'),
    );
    expect(find.byType(AppCard), findsWidgets);
  });
}
