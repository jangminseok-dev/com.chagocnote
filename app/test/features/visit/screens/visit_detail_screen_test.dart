import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_card.dart';
import 'package:chagocnote/features/home/state/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 10, 2))];

/// 방문 101(두부)을 [status]로 보이는 서버. 전이를 받으면 상태를 바꿔 다음
/// 조회에 반영한다. [withBori]면 102(보리)가 같은 묶음·같은 상태다.
class _Server {
  _Server({this.status = 'reserved', this.withBori = false}) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(
          visit: _dubu(),
          group: [_dubu(), if (withBori) _bori()],
        ),
      ),
      'GET /v1/shops/3/visits/102': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(visit: _bori(), group: [_dubu(), _bori()]),
      ),
      'POST /v1/shops/3/visits/transitions': (o, body) {
        final sent = bodyOf(body);
        transitions.add(sent);
        cancelReason = sent['cancel_reason'] as String?;
        status = switch (sent['action']) {
          'start' => 'in_progress',
          'complete' => 'completed',
          'cancel' => 'canceled',
          'no_show' => 'no_show',
          _ => 'reserved',
        };
        return FakeResponse(
          statusCode: 200,
          data: {
            'visits': [_dubu()],
          },
        );
      },
      'GET /v1/shops/3/visits/101/next-draft': (o, b) =>
          FakeResponse(statusCode: 200, data: nextDraftJson()),
    });
  }

  String status;
  String? cancelReason;
  final bool withBori;
  final transitions = <Map<String, dynamic>>[];
  late final VisitTestBackend backend;

  Map<String, dynamic> _dubu() =>
      visitJson(status: status, cancelReason: cancelReason);
  Map<String, dynamic> _bori() => visitJson(
    visitId: 102,
    status: status,
    pet: visitPetJson(petId: 12, name: '보리'),
  );
}

Future<void> _open(WidgetTester tester, CustomerTestSetup setup) async {
  useTallView(tester, height: 1200);
  await pushOnHome<Object?>(tester, setup, '/visits/101');
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await settle(tester);
}

Future<void> _more(WidgetTester tester, String label) async {
  await _tap(tester, find.bySemanticsLabel(AppStrings.more));
  await _tap(tester, find.text(label));
}

void main() {
  testWidgets('예약됨이면 날짜·메뉴·메모·지난 방문·노쇼 횟수와 [노쇼 · 취소 · 시작]을 보인다', (
    tester,
  ) async {
    final server = _Server();
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
    expect(find.text('두부'), findsOneWidget);
    expect(find.text(AppStrings.statusReserved), findsOneWidget);
    expect(find.text('말티푸 · 4.2kg · 이수진'), findsOneWidget);
    expect(find.text('10월 2일 금 · 14:00 — 15:30'), findsOneWidget);
    expect(find.text('목욕'), findsOneWidget);
    expect(find.text('발톱 짧게'), findsOneWidget);
    expect(find.text('9월 2일 수 · ${AppStrings.noShowCount(0)}'), findsOneWidget);
    expect(_button(AppStrings.actionNoShow), findsOneWidget);
    expect(_button(AppStrings.actionCancelVisit), findsOneWidget);
    expect(_button(AppStrings.actionStart), findsOneWidget);
    expect(_button(AppStrings.actionComplete), findsNothing);
  });

  testWidgets('시작은 같은 묶음·같은 상태의 방문을 한 번에 보내고, 다시 불러와 미용 중으로 보인다', (
    tester,
  ) async {
    final server = _Server(withBori: true);
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(find.text(AppStrings.groupLabel), findsOneWidget);

    await _tap(tester, _button(AppStrings.actionStart));

    expect(server.transitions.single, {
      'visit_ids': [101, 102],
      'action': 'start',
    });
    expect(find.text(AppStrings.statusInProgress), findsWidgets);
    expect(_button(AppStrings.actionComplete), findsOneWidget);
  });

  testWidgets('묶음이라도 상태가 다른 방문은 함께 보내지 않는다', (tester) async {
    final server = _Server();
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) {
      final dubu = visitJson();
      final bori = visitJson(
        visitId: 102,
        status: 'canceled',
        pet: visitPetJson(petId: 12, name: '보리'),
      );
      return FakeResponse(
        statusCode: 200,
        data: visitDetailJson(visit: dubu, group: [dubu, bori]),
      );
    };
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionStart));

    expect(server.transitions.single['visit_ids'], [101]);
  });

  testWidgets('취소는 사유를 고른 뒤 보내고, 시트를 닫으면 보내지 않는다', (tester) async {
    final server = _Server();
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionCancelVisit));
    expect(find.text(AppStrings.cancelReasonTitle), findsOneWidget);
    await tester.tapAt(const Offset(10, 10));
    await settle(tester);
    expect(server.transitions, isEmpty);

    await _tap(tester, _button(AppStrings.actionCancelVisit));
    await _tap(tester, find.text(AppStrings.reasonShopReason));

    expect(server.transitions.single, {
      'visit_ids': [101],
      'action': 'cancel',
      'cancel_reason': 'shop_reason',
    });
    expect(find.text(AppStrings.reasonShopReason), findsOneWidget);
  });

  testWidgets('노쇼는 한 번 묻고 보낸다', (tester) async {
    final server = _Server();
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionNoShow));
    expect(find.text(AppStrings.noShowConfirm), findsOneWidget);
    await _tap(tester, _button(AppStrings.actionNoShow).last);

    expect(server.transitions.single['action'], 'no_show');
    expect(find.text(AppStrings.statusNoShow), findsOneWidget);
  });

  testWidgets('미용 중이면 [완료]만 있고, 완료 시트에서 완료를 고르면 완료한다', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(_button(AppStrings.actionStart), findsNothing);

    await _tap(tester, _button(AppStrings.actionComplete));
    expect(find.text(AppStrings.completeTitle), findsOneWidget);
    // 시트는 다음 예약이 언제로 잡히는지 미리 보인다(초안을 먼저 읽는다).
    expect(
      find.text(AppStrings.nextPreview('10월 30일 금 14:00')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.completeAndNextCaption(4)), findsOneWidget);
    await _tap(tester, _button(AppStrings.actionComplete).last);

    expect(server.transitions.single['action'], 'complete');
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
  });

  testWidgets('완료하고 다음 예약 잡기는 완료한 뒤 초안으로 예약 ②를 채워 연다', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionComplete));
    await _tap(tester, find.text(AppStrings.completeAndNext));

    final writes = [
      for (final c in setup.calls)
        if (c.contains('transitions') || c.contains('next-draft')) c,
    ];
    // 초안은 시트를 띄우기 전에 한 번만 읽고, 완료한 뒤 그 초안으로 연다.
    expect(writes, [
      'GET /v1/shops/3/visits/101/next-draft',
      'POST /v1/shops/3/visits/transitions',
    ]);
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    expect(
      find.text(AppStrings.saveReservation('10월 30일 금 14:00')),
      findsOneWidget,
    );
  });

  testWidgets('초안을 못 읽어도 완료 시트는 뜨고 완료할 수 있다', (tester) async {
    final server = _Server(status: 'in_progress');
    server.backend.routes['GET /v1/shops/3/visits/101/next-draft'] = (o, b) =>
        const FakeResponse(statusCode: 503, data: 'x');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionComplete));
    expect(find.text(AppStrings.completeTitle), findsOneWidget);
    expect(find.textContaining('→'), findsNothing);
    await _tap(tester, _button(AppStrings.actionComplete).last);

    expect(server.transitions.single['action'], 'complete');
  });

  testWidgets('··· 에서 바로 완료는 예약됨에서 완료 시트를 거쳐 보낸다', (tester) async {
    final server = _Server();
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _more(tester, AppStrings.actionCompleteNow);
    await _tap(tester, _button(AppStrings.actionComplete).last);

    expect(server.transitions.single['action'], 'complete');
  });

  testWidgets('완료한 방문은 버튼이 없고 ··· 에 되돌리기·다음 예약 잡기가 있다', (tester) async {
    final server = _Server(status: 'completed');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(_button(AppStrings.actionComplete), findsNothing);
    expect(_button(AppStrings.actionStart), findsNothing);

    await _tap(tester, find.bySemanticsLabel(AppStrings.more));
    expect(find.text(AppStrings.actionCompleteNow), findsNothing);
    expect(find.text(AppStrings.actionNextReservation), findsOneWidget);
    await _tap(tester, find.text(AppStrings.actionRevert));

    expect(server.transitions.single['action'], 'revert');
    expect(_button(AppStrings.actionStart), findsOneWidget);
  });

  testWidgets('취소한 방문의 ··· 에는 수정이 없고 되돌리기만 있다', (tester) async {
    final server = _Server(status: 'canceled');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, find.bySemanticsLabel(AppStrings.more));

    expect(find.text(AppStrings.edit), findsNothing);
    expect(find.text(AppStrings.actionRevert), findsOneWidget);
  });

  testWidgets('··· 의 수정은 수정 화면을 연다', (tester) async {
    final server = _Server();
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _more(tester, AppStrings.edit);

    expect(find.byKey(ScreenKeys.visitEdit), findsOneWidget);
  });

  testWidgets('서버가 거절하면(VISIT_NOT_YET) 문구를 보이고, 화면을 다시 불러온다', (tester) async {
    final server = _Server();
    server.backend.routes['POST /v1/shops/3/visits/transitions'] = (o, b) =>
        const FakeResponse(
          statusCode: 409,
          data: {'code': 'VISIT_NOT_YET', 'message': 'x'},
        );
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    setup.adapter.requests.clear();

    await _tap(tester, _button(AppStrings.actionStart));

    expect(find.textContaining('아직 할 수 없습니다'), findsOneWidget);
    expect(setup.calls, contains('GET /v1/shops/3/visits/101'));
  });

  testWidgets('보내는 동안 버튼과 ··· 를 막아 한 번만 보낸다', (tester) async {
    final server = _Server();
    final gate = Completer<FakeResponse>();
    server.backend.routes['POST /v1/shops/3/visits/transitions'] = (o, b) =>
        gate.future;
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.actionStart));
    await tester.pump();
    expect(
      tester.widget<AppButton>(_button(AppStrings.actionNoShow)).onPressed,
      isNull,
    );
    await tester.tap(find.bySemanticsLabel(AppStrings.more));
    await tester.pump();
    expect(find.text(AppStrings.actionCompleteNow), findsNothing);
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: {
          'visits': [visitJson(status: 'in_progress')],
        },
      ),
    );
    await settle(tester);

    expect(setup.calls.where((c) => c.endsWith('/transitions')), hasLength(1));
  });

  testWidgets('함께 온 아이를 누르면 그 방문으로 바꿔 끼운다', (tester) async {
    final server = _Server(withBori: true);
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, find.text('보리'));

    expect(setup.calls, contains('GET /v1/shops/3/visits/102'));
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
    await _tap(tester, find.bySemanticsLabel(AppStrings.back));
    expect(find.byKey(ScreenKeys.visitDetail), findsNothing);
  });

  testWidgets('익명화한 고객의 방문은 "삭제된 고객"으로 보인다', (tester) async {
    final server = _Server();
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) {
      final v = visitJson(
        customer: visitCustomerJson(name: null, phoneMasked: null),
        pet: visitPetJson(name: null),
        status: 'completed',
      );
      return FakeResponse(
        statusCode: 200,
        data: visitDetailJson(visit: v, previousVisit: null),
      );
    };
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(
      find.text('말티푸 · 4.2kg · ${AppStrings.deletedCustomer}'),
      findsOneWidget,
    );
    expect(
      find.text('${AppStrings.none} · ${AppStrings.noShowCount(0)}'),
      findsOneWidget,
    );
  });

  testWidgets('불러오지 못하면 다시 시도할 수 있고 뒤로 갈 수 있다', (tester) async {
    var fail = true;
    final server = _Server();
    final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) => fail
        ? const FakeResponse(
            statusCode: 404,
            data: {'code': 'VISIT_NOT_FOUND', 'message': 'x'},
          )
        : ok(o, b);
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(find.textContaining('방문을 찾을 수 없습니다'), findsOneWidget);
    expect(find.bySemanticsLabel(AppStrings.back), findsOneWidget);

    fail = false;
    await _tap(tester, _button(AppStrings.retry));

    expect(find.text('두부'), findsOneWidget);
  });

  testWidgets('방문 상세 골든', (tester) async {
    final server = _Server(withBori: true);
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    tester.view.physicalSize = const Size(390, 1000);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.visitDetail),
      matchesGoldenFile('goldens/visit_detail.png'),
    );
  });

  testWidgets('완료 시트 골든', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    tester.view.physicalSize = const Size(390, 844);
    await _tap(tester, _button(AppStrings.actionComplete));

    await expectLater(
      find
          .ancestor(
            of: find.text(AppStrings.completeTitle),
            matching: find.byType(AppCard),
          )
          .first,
      matchesGoldenFile('goldens/complete_sheet.png'),
    );
  });
}
