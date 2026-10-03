import 'dart:async';

import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/upload_job.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_card.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 10, 2))];

const _reportPath = '/v1/shops/3/visits/101/report';

/// 방문 101(두부)을 [status]로 보이는 서버. 전이를 받으면 상태를 바꿔 다음
/// 조회에 반영한다. [withBori]면 102(보리)가 같은 묶음·같은 상태다.
/// 서버 계약대로 `group`은 자기를 뺀 형제만 준다. [report]는 알림장 링크의 상태다 — 끊으면 '안 보냄'이 된다.
class _Server {
  _Server({this.status = 'reserved', this.withBori = false}) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(
          visit: _dubu(),
          group: [if (withBori) _bori()],
          record: record,
          report: report,
        ),
      ),
      'GET /v1/shops/3/visits/102': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(visit: _bori(), group: [_dubu()]),
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
      'DELETE /v1/shops/3/visits/101/record': (o, b) {
        record = null;
        return const FakeResponse(statusCode: 204);
      },
      'PUT /v1/shops/3/visits/101/record': (o, body) {
        recordPuts.add(bodyOf(body));
        return FakeResponse(statusCode: 200, data: recordJson());
      },
      // 알림장(⑤) — 미리보기 화면이 읽는 것과 링크 끊기.
      'GET $_reportPath': (o, b) =>
          FakeResponse(statusCode: 200, data: visitReportJson(link: report)),
      'DELETE $_reportPath': (o, b) {
        report = reportLinkJson();
        return const FakeResponse(statusCode: 204);
      },
    });
  }

  String status;
  String? cancelReason;
  Map<String, dynamic>? record;
  Map<String, dynamic> report = reportLinkJson();
  final bool withBori;
  final transitions = <Map<String, dynamic>>[];
  final recordPuts = <Map<String, dynamic>>[];
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
    // 이름 카드에 품종·몸무게, 넘기기 아래에 보호자.
    expect(find.text('말티푸 · 4.2kg'), findsOneWidget);
    expect(find.text(AppStrings.ownerLine('이수진')), findsOneWidget);
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
        data: visitDetailJson(visit: dubu, group: [bori]),
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

  testWidgets('미용 중이면 [완료]만 있고, 완료는 기록 화면(완료 모드)을 열어 완료한 뒤 다음 예약 시트를 띄운다', (
    tester,
  ) async {
    final server = _Server(status: 'in_progress', withBori: true);
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(_button(AppStrings.actionStart), findsNothing);

    await _tap(tester, _button(AppStrings.actionComplete));
    expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);
    expect(setup.calls.where((c) => c.endsWith('/next-draft')), isEmpty);
    await _tap(tester, _button(AppStrings.completeWithRecord));

    expect(server.recordPuts, hasLength(1));
    expect(server.transitions.single, {
      'visit_ids': [101, 102],
      'action': 'complete',
    });
    // 시트는 다음 예약이 언제로 잡히는지 미리 보인다(완료한 뒤 초안을 읽는다).
    expect(find.text(AppStrings.completeTitle), findsOneWidget);
    expect(
      find.text(AppStrings.nextPreview('10월 30일 금 14:00')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.completeAndNextCaption(4)), findsOneWidget);
    await _tap(tester, _button(AppStrings.close));

    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
    // 두부와 함께 온 보리 둘 다 완료다.
    expect(find.text(AppStrings.statusCompleted), findsNWidgets(2));
  });

  testWidgets('다음 예약 잡기를 고르면 완료 뒤 한 번 읽은 초안으로 예약 ②를 채워 연다', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionComplete));
    await _tap(tester, _button(AppStrings.completeWithoutRecord));
    await _tap(tester, _button(AppStrings.actionNextReservation));

    final writes = [
      for (final c in setup.calls)
        if (c.contains('transitions') ||
            c.contains('next-draft') ||
            c.contains('/record'))
          c,
    ];
    expect(writes, [
      'POST /v1/shops/3/visits/transitions',
      'GET /v1/shops/3/visits/101/next-draft',
    ]);
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    expect(
      find.text(AppStrings.saveReservation('10월 30일 금 14:00')),
      findsOneWidget,
    );
  });

  testWidgets('다음 예약 잡기를 골랐는데 초안을 다시 못 읽으면 문구를 보이고 예약 화면을 열지 않는다', (
    tester,
  ) async {
    final server = _Server(status: 'in_progress');
    server.backend.routes['GET /v1/shops/3/visits/101/next-draft'] = (o, b) =>
        const FakeResponse(statusCode: 503, data: 'x');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionComplete));
    await _tap(tester, _button(AppStrings.completeWithoutRecord));
    await _tap(tester, _button(AppStrings.actionNextReservation));

    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
  });

  testWidgets('초안을 못 읽어도 다음 예약 시트는 미리보기 없이 뜬다', (tester) async {
    final server = _Server(status: 'in_progress');
    server.backend.routes['GET /v1/shops/3/visits/101/next-draft'] = (o, b) =>
        const FakeResponse(statusCode: 503, data: 'x');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionComplete));
    await _tap(tester, _button(AppStrings.completeWithoutRecord));

    expect(server.transitions.single['action'], 'complete');
    expect(find.text(AppStrings.completeTitle), findsOneWidget);
    expect(find.textContaining('→'), findsNothing);
  });

  testWidgets('기록 화면에서 뒤로 가면 완료하지 않고 시트도 없다', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tap(tester, _button(AppStrings.actionComplete));
    await _tap(tester, find.bySemanticsLabel(AppStrings.back));

    expect(server.transitions, isEmpty);
    expect(find.text(AppStrings.completeTitle), findsNothing);
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
  });

  testWidgets('··· 에서 바로 완료는 예약됨이라 먼저 완료한 뒤 기록을 저장한다', (tester) async {
    final server = _Server();
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _more(tester, AppStrings.actionCompleteNow);
    await _tap(tester, _button(AppStrings.completeWithRecord));

    expect(
      [
        for (final c in setup.calls)
          if (c.contains('transitions') || c.contains('/record')) c,
      ],
      [
        'POST /v1/shops/3/visits/transitions',
        'PUT /v1/shops/3/visits/101/record',
      ],
    );
    expect(find.text(AppStrings.completeTitle), findsOneWidget);
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

    expect(find.textContaining('아직 할 수 없어요'), findsOneWidget);
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

  testWidgets('[완료]를 빠르게 두 번 눌러도 기록 화면은 한 장이다', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.actionComplete));
    await tester.tap(_button(AppStrings.actionComplete));
    await settle(tester);

    expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);
    await _tap(tester, find.bySemanticsLabel(AppStrings.back));
    expect(find.byKey(ScreenKeys.visitRecord), findsNothing);
    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
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

    expect(find.text('말티푸 · 4.2kg'), findsOneWidget);
    expect(
      find.text(AppStrings.ownerLine(AppStrings.deletedCustomer)),
      findsOneWidget,
    );
    expect(
      find.text('${AppStrings.none} · ${AppStrings.noShowCount(0)}'),
      findsOneWidget,
    );
  });

  testWidgets('서버 오류로 불러오지 못하면 다시 시도할 수 있고 뒤로 갈 수 있다', (tester) async {
    var fail = true;
    final server = _Server();
    final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) =>
        fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(find.textContaining('서버에 잠시 문제가 있어요'), findsOneWidget);
    expect(find.bySemanticsLabel(AppStrings.back), findsOneWidget);

    fail = false;
    await _tap(tester, _button(AppStrings.retry));

    expect(find.text('두부'), findsOneWidget);
  });

  testWidgets('지워진 방문(404)이면 [다시 시도] 대신 [돌아가기]로 앞 화면에 돌아간다', (tester) async {
    final server = _Server();
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) =>
        const FakeResponse(
          statusCode: 404,
          data: {'code': 'VISIT_NOT_FOUND', 'message': 'x'},
        );
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(find.text('방문을 찾을 수 없어요. 이미 지워졌을 수 있어요.'), findsOneWidget);
    expect(_button(AppStrings.retry), findsNothing);

    await _tap(tester, _button(AppStrings.goBack));

    expect(find.byKey(ScreenKeys.visitDetail), findsNothing);
  });

  testWidgets('당겨서 새로고침하면 다시 읽고, 실패하면 내용은 두고 위에 띠를 보인다', (tester) async {
    var fail = false;
    var reads = 0;
    final server = _Server();
    final ok = server.backend.routes['GET /v1/shops/3/visits/101']!;
    server.backend.routes['GET /v1/shops/3/visits/101'] = (o, b) {
      reads++;
      return fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
    };
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    fail = true;
    // '두부'는 오버레이 이름 카드(IgnorePointer) 안이라 히트테스트 경고가 난다 — 카드 밖 글자를 당긴다.
    await tester.fling(find.text(AppStrings.menuLabel), const Offset(0, 400), 1000);
    await tester.pumpAndSettle();

    expect(reads, 2);
    expect(find.text('두부'), findsOneWidget);
    expect(
      find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'),
      findsOneWidget,
    );
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

  testWidgets('다음 예약 시트 골든', (tester) async {
    final server = _Server(status: 'in_progress');
    final setup = CustomerTestSetup(server.backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _tap(tester, _button(AppStrings.actionComplete));
    await _tap(tester, _button(AppStrings.completeWithoutRecord));
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();

    await expectLater(
      find
          .ancestor(
            of: find.text(AppStrings.completeTitle),
            matching: find.byType(AppCard),
          )
          .first,
      matchesGoldenFile('goldens/next_reservation_sheet.png'),
    );
  });
  group('미용 기록(④)', () {
    Map<String, dynamic> filled() => recordJson(
      weightKg: 4.2,
      careNote: '발바닥 각질',
      internalNote: '예민함',
      paymentMethod: 'transfer',
      totalAmount: 50000,
      items: [
        {'menu_id': 4, 'name': '전체 미용', 'amount': 55000},
      ],
      media: [
        recordMediaJson(mediaId: 51, phase: 'before'),
        recordMediaJson(mediaId: 52, phase: 'after'),
      ],
    );

    ({
      CustomerTestSetup setup,
      FakeMediaImages images,
      FakeUploadQueue queue,
    })
    build(
      _Server server, {
      String role = 'owner',
      List<UploadJob> uploads = const [],
    }) {
      final images = FakeMediaImages();
      final queue = FakeUploadQueue(uploads);
      final setup = CustomerTestSetup(
        server.backend.call,
        role: role,
        overrides: [
          ..._today,
          mediaImagesProvider.overrideWithValue(images),
          uploadQueueProvider.overrideWith(() => queue),
          mediaPickerProvider.overrideWithValue(
            FakeMediaPicker(taken: '/camera/c.jpg'),
          ),
        ],
      );
      addTearDown(setup.container.dispose);
      return (setup: setup, images: images, queue: queue);
    }

    testWidgets('기록이 있으면 대표 사진(후)·사진 줄·오늘의 케어를 보이고, [기록 수정]은 기록 화면을 연다', (
      tester,
    ) async {
      final server = _Server(status: 'completed')..record = filled();
      final app = build(server);
      await _open(tester, app.setup);

      expect(app.images.urls, contains(contains('display/shops/3/52.jpg')));
      expect(find.bySemanticsLabel('전 사진 1'), findsOneWidget);
      expect(find.bySemanticsLabel('후 사진 1'), findsOneWidget);
      expect(find.text('전체 미용 · 55,000원'), findsOneWidget);
      expect(find.text('${AppStrings.weightLabel} 4.2kg'), findsOneWidget);
      expect(
        find.text(
          '${AppStrings.totalLabel} 50,000원 · ${AppStrings.paymentTransfer}',
        ),
        findsOneWidget,
      );
      expect(find.text('발바닥 각질'), findsOneWidget);
      expect(
        find.text('${AppStrings.internalNoteLabel} · 예민함'),
        findsOneWidget,
      );

      await _tap(tester, _button(AppStrings.editRecord));
      expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);
      expect(_button(AppStrings.completeWithRecord), findsNothing);
    });

    testWidgets('넘기기는 대표 사진(후)부터 표시용으로 보이고, 가운데 사진을 누르면 그 사진의 크게 보기를 연다', (
      tester,
    ) async {
      final server = _Server(status: 'completed')..record = filled();
      final app = build(server);
      await _open(tester, app.setup);

      expect(find.text('01 / 02'), findsOneWidget);
      expect(app.images.urls, contains(contains('display/shops/3/52.jpg')));
      expect(app.images.urls, contains(contains('display/shops/3/51.jpg')));

      await _tap(
        tester,
        find.bySemanticsLabel(AppStrings.openPhotoLabel('후', 1)),
      );

      expect(find.byKey(ScreenKeys.photoViewer), findsOneWidget);
      expect(find.text('후 · 1 / 2'), findsOneWidget);

      // 옆 사진(전)은 한 번 누르면 넘어가고, 다시 누르면 그 사진부터 연다.
      await _tap(tester, find.bySemanticsLabel(AppStrings.back));
      final before = find.bySemanticsLabel(AppStrings.openPhotoLabel('전', 1));
      await _tap(tester, before);
      expect(find.text('02 / 02'), findsOneWidget);
      await _tap(tester, before);
      expect(find.text('전 · 2 / 2'), findsOneWidget);
    });

    testWidgets('미용 중이면 기록이 없어도 사진 줄과 [기록 쓰기]가 있고, 사진 추가는 전 사진으로 대기열에 넣는다', (
      tester,
    ) async {
      final app = build(_Server(status: 'in_progress'));
      await _open(tester, app.setup);
      expect(_button(AppStrings.writeRecord), findsOneWidget);

      await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));
      await _tap(tester, _button(AppStrings.takePhoto));

      expect(app.queue.added.single.phase, MediaPhase.before);
      expect(app.queue.added.single.sources, ['/camera/c.jpg']);
    });

    testWidgets('사진 30장(붙은 것과 대기열)과 영상 3편이 다 차면 사진 추가는 시트 없이 한도 문구만 보인다(카메라도 막힌다)', (
      tester,
    ) async {
      final server = _Server(status: 'in_progress')
        ..record = recordJson(
          media: [
            for (var i = 0; i < 29; i++)
              recordMediaJson(mediaId: 100 + i, sortOrder: i),
            for (var i = 0; i < 3; i++)
              recordMediaJson(mediaId: 200 + i, sortOrder: 29 + i, kind: 'video'),
          ],
        );
      final app = build(
        server,
        uploads: [
          const UploadJob(
            id: 'j1',
            userId: 1,
            shopId: 3,
            visitId: 101,
            phase: MediaPhase.before,
            stage: UploadStage.prepared,
          ),
        ],
      );
      await _open(tester, app.setup);

      await _tap(tester, find.bySemanticsLabel(AppStrings.addPhoto));

      expect(find.text('방문 하나에 사진은 30장, 영상은 3편까지 붙일 수 있어요.'), findsOneWidget);
      expect(_button(AppStrings.takePhoto), findsNothing);
      expect(app.queue.added, isEmpty);
    });

    testWidgets('사진만 붙은 기록(대기열이 만든 것)은 케어 카드 없이 [기록 쓰기]다', (tester) async {
      final server = _Server(status: 'in_progress')
        ..record = recordJson(media: [recordMediaJson()]);
      final app = build(server);
      await _open(tester, app.setup);

      expect(find.bySemanticsLabel('전 사진 1'), findsOneWidget);
      expect(find.textContaining(AppStrings.todayCareLabel), findsNothing);
      expect(_button(AppStrings.writeRecord), findsOneWidget);
    });

    testWidgets('예약됨이면 사진 줄도 기록 버튼도 없다', (tester) async {
      final app = build(_Server());
      await _open(tester, app.setup);

      expect(find.bySemanticsLabel(AppStrings.addPhoto), findsNothing);
      expect(_button(AppStrings.writeRecord), findsNothing);
      expect(find.textContaining(AppStrings.todayCareLabel), findsNothing);
    });

    testWidgets('사장은 ··· 로 확인을 거쳐 기록을 삭제한다', (tester) async {
      final server = _Server(status: 'completed')..record = filled();
      final app = build(server);
      await _open(tester, app.setup);

      await _more(tester, AppStrings.deleteRecord);
      expect(find.text(AppStrings.deleteRecordConfirm), findsOneWidget);
      await _tap(tester, _button(AppStrings.deleteRecord));

      expect(
        app.setup.calls,
        contains('DELETE /v1/shops/3/visits/101/record'),
      );
      expect(find.text('발바닥 각질'), findsNothing);
      expect(_button(AppStrings.writeRecord), findsOneWidget);
    });

    testWidgets('직원의 ··· 에는 기록 삭제가 없다(record:delete 는 사장만)', (tester) async {
      final server = _Server(status: 'completed')..record = filled();
      final app = build(server, role: 'staff');
      await _open(tester, app.setup);

      await _tap(tester, find.bySemanticsLabel(AppStrings.more));
      expect(find.text(AppStrings.deleteRecord), findsNothing);
      expect(find.text(AppStrings.actionRevert), findsOneWidget);
    });
  });

  group('알림장(⑤)', () {
    // 가짜 서버가 주는 링크의 주소(픽스처의 가짜 주소).
    final url = reportLinkJson(live: true)['url'] as String;
    const revertBlocked = '알림장을 보낸 방문이에요. 링크를 먼저 끊어 주세요.';

    /// 완료한 방문 101 — 기록(케어 메모)이 있고 알림장은 아직 안 보냈다.
    _Server done() =>
        _Server(status: 'completed')..record = recordJson(careNote: '발바닥 각질');

    /// 알림장을 보낸 방문 — 링크가 살아 있다.
    _Server sent({
      String? firstViewedAt,
      String? expiresAt = '2026-11-01T15:30:00+09:00',
    }) => done()
      ..report = reportLinkJson(
        live: true,
        firstViewedAt: firstViewedAt,
        expiresAt: expiresAt,
      );

    Future<CustomerTestSetup> open(
      WidgetTester tester,
      _Server server, {
      String role = 'owner',
    }) async {
      final setup = CustomerTestSetup(
        server.backend.call,
        role: role,
        overrides: _today,
      );
      addTearDown(setup.container.dispose);
      await _open(tester, setup);
      return setup;
    }

    testWidgets('완료한 방문에 기록이 있으면 "아직 안 보냄"과 [알림장 보내기]가 있고, 누르면 미리보기를 연다', (
      tester,
    ) async {
      await open(tester, done());

      expect(find.text('알림장'), findsOneWidget);
      expect(find.text('아직 안 보냄'), findsOneWidget);
      expect(find.text(AppStrings.statusCompleted), findsOneWidget);
      expect(find.text('아직 안 열었어요'), findsNothing);
      expect(_button(AppStrings.reportShareAgain), findsNothing);

      await _tap(tester, _button(AppStrings.reportStart));

      expect(find.byKey(ScreenKeys.reportPreview), findsOneWidget);
      expect(_button(AppStrings.reportSend), findsOneWidget);
    });

    testWidgets('기록이 없는 완료 방문에는 [알림장 보내기]가 없고 안내 한 줄이 있다', (tester) async {
      await open(tester, _Server(status: 'completed'));

      expect(find.text('알림장'), findsOneWidget);
      expect(find.text('기록을 쓰면 보낼 수 있어요'), findsOneWidget);
      expect(find.text('아직 안 보냄'), findsNothing);
      expect(_button(AppStrings.reportStart), findsNothing);
    });

    for (final status in ['in_progress', 'reserved']) {
      testWidgets('미용 중·예약됨에는 알림장 줄이 없다 — $status', (tester) async {
        final server = _Server(status: status);
        // 미용 중에는 기록이 있어도 보낼 수 없다.
        if (status == 'in_progress') server.record = recordJson(careNote: '메모');
        await open(tester, server);

        expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
        expect(find.text('알림장'), findsNothing);
        expect(_button(AppStrings.reportStart), findsNothing);
      });
    }

    testWidgets(
      '보낸 방문은 꼬리표가 "완료 · 알림장 보냄"이고, 아직 안 열었으면 "아직 안 열었어요"와 기간을 보인다',
      (tester) async {
        await open(tester, sent());

        expect(find.text('완료 · 알림장 보냄'), findsOneWidget);
        expect(find.text(AppStrings.statusCompleted), findsNothing);
        expect(find.text('아직 안 열었어요'), findsOneWidget);
        expect(find.text('11월 1일까지 열려요.'), findsOneWidget);
        expect(find.byIcon(Icons.check), findsNothing);
        // "알림장" 줄과 [알림장 보내기] 대신 확인 카드와 [다시 공유]다.
        expect(find.text('알림장'), findsNothing);
        expect(_button(AppStrings.reportStart), findsNothing);
        expect(_button(AppStrings.reportShareAgain), findsOneWidget);
      },
    );

    testWidgets('보호자가 열었으면 "보호자가 확인했어요"와 처음 연 시각을 보인다', (tester) async {
      await open(tester, sent(firstViewedAt: '2026-10-02T15:20:00+09:00'));

      expect(find.text('보호자가 확인했어요'), findsOneWidget);
      expect(find.text('15:20 · 11월 1일까지 열려요.'), findsOneWidget);
      expect(find.byIcon(Icons.check), findsOneWidget);
      expect(find.text('아직 안 열었어요'), findsNothing);
    });

    testWidgets('처음 연 날이 오늘이 아니면 날짜도 붙인다', (tester) async {
      // 오늘은 10월 2일이다.
      await open(tester, sent(firstViewedAt: '2026-10-01T09:05:00+09:00'));

      expect(find.text('10월 1일 목 09:05 · 11월 1일까지 열려요.'), findsOneWidget);
    });

    testWidgets('기간이 없으면 "계속 열려 있어요"', (tester) async {
      await open(tester, sent(expiresAt: null));

      expect(find.text('아직 안 열었어요'), findsOneWidget);
      expect(find.text('계속 열려 있어요.'), findsOneWidget);
      expect(find.textContaining('까지 열려요'), findsNothing);
    });

    testWidgets('[다시 공유]는 서버를 부르지 않고 읽은 주소를 공유 시트에 넘긴다', (tester) async {
      final setup = await open(tester, sent());
      final before = [...setup.calls];
      final button = _button(AppStrings.reportShareAgain);

      await _tap(tester, button);

      expect(setup.calls, before);
      expect(setup.shareSheet.shared.single, url);
      // 공유 시트가 붙을 자리는 버튼의 화면 사각형이다(아이패드의 말풍선).
      final origin = setup.shareSheet.origins.single;
      expect(origin.isEmpty, isFalse);
      expect(origin, tester.getRect(button));
    });

    for (final error in <Exception>[
      PlatformException(code: 'NO_VIEW'),
      MissingPluginException(),
    ]) {
      testWidgets('[다시 공유]가 실패하면 안내를 보인다 — ${error.runtimeType}', (
        tester,
      ) async {
        final setup = await open(tester, sent());
        setup.shareSheet.error = error;

        await _tap(tester, _button(AppStrings.reportShareAgain));

        expect(find.text('공유 화면을 열지 못했어요. 다시 눌러 주세요.'), findsOneWidget);
        expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
      });
    }

    testWidgets('··· 의 [보낼 사진 고르기]는 미리보기를 고르기 모드로 연다', (tester) async {
      await open(tester, sent());

      await _more(tester, AppStrings.reportPickMedia);

      expect(find.byKey(ScreenKeys.reportPreview), findsOneWidget);
      expect(_button(AppStrings.save), findsOneWidget);
      expect(_button(AppStrings.reportSend), findsNothing);
    });

    testWidgets('[링크 끊기]는 한 번 묻고 끊은 뒤 "아직 안 보냄"으로 돌아온다', (tester) async {
      // 끊기는 record:write 라 직원도 한다.
      final setup = await open(tester, sent(), role: 'staff');

      await _more(tester, AppStrings.reportRevoke);
      expect(find.text('보호자가 받은 링크가 더는 열리지 않아요.'), findsOneWidget);
      expect(setup.calls, isNot(contains('DELETE $_reportPath')));
      await _tap(tester, _button(AppStrings.reportRevoke));

      expect(setup.calls.where((c) => c == 'DELETE $_reportPath'), hasLength(1));
      expect(find.text('아직 안 보냄'), findsOneWidget);
      expect(find.text(AppStrings.statusCompleted), findsOneWidget);
      expect(_button(AppStrings.reportStart), findsOneWidget);
      expect(_button(AppStrings.reportShareAgain), findsNothing);
    });

    testWidgets('확인 시트를 닫으면 끊지 않는다', (tester) async {
      final setup = await open(tester, sent());

      await _more(tester, AppStrings.reportRevoke);
      await _tap(tester, _button(AppStrings.cancel));
      await _more(tester, AppStrings.reportRevoke);
      await tester.tapAt(const Offset(10, 10));
      await settle(tester);

      expect(setup.calls, isNot(contains('DELETE $_reportPath')));
      expect(find.text('완료 · 알림장 보냄'), findsOneWidget);
    });

    testWidgets('끊는 동안에는 [다시 공유]와 ··· 를 막아 한 번만 보낸다', (tester) async {
      final server = sent();
      final gate = Completer<FakeResponse>();
      server.backend.routes['DELETE $_reportPath'] = (o, b) => gate.future;
      final setup = await open(tester, server);

      await _more(tester, AppStrings.reportRevoke);
      await _tap(tester, _button(AppStrings.reportRevoke));
      expect(
        tester
            .widget<AppButton>(_button(AppStrings.reportShareAgain))
            .onPressed,
        isNull,
      );
      await tester.tap(find.bySemanticsLabel(AppStrings.more));
      await tester.pump();
      expect(find.text(AppStrings.reportRevoke), findsNothing);
      server.report = reportLinkJson();
      gate.complete(const FakeResponse(statusCode: 204));
      await settle(tester);

      expect(setup.calls.where((c) => c == 'DELETE $_reportPath'), hasLength(1));
      expect(find.text('아직 안 보냄'), findsOneWidget);
    });

    testWidgets('안 보낸 방문의 ··· 에는 [보낼 사진 고르기]·[링크 끊기]가 없다', (tester) async {
      await open(tester, done());

      await _tap(tester, find.bySemanticsLabel(AppStrings.more));

      expect(find.text(AppStrings.actionRevert), findsOneWidget);
      expect(find.text(AppStrings.reportPickMedia), findsNothing);
      expect(find.text(AppStrings.reportRevoke), findsNothing);
    });

    testWidgets(
      '알림장을 보낸 방문을 되돌리면(409 VISIT_REPORT_SENT) "…링크를 먼저 끊어 주세요."를 보인다',
      (tester) async {
        final server = sent();
        server.backend.routes['POST /v1/shops/3/visits/transitions'] = (o, b) =>
            const FakeResponse(
              statusCode: 409,
              data: {'code': 'VISIT_REPORT_SENT', 'message': 'x'},
            );
        await open(tester, server);

        await _more(tester, AppStrings.actionRevert);

        expect(find.text(revertBlocked), findsOneWidget);
        expect(find.text('완료 · 알림장 보냄'), findsOneWidget);
      },
    );

    testWidgets('알림장을 보낸 방문의 기록 삭제도(409 VISIT_REPORT_SENT) 같은 문구를 보인다', (
      tester,
    ) async {
      final server = sent();
      server.backend.routes['DELETE /v1/shops/3/visits/101/record'] = (o, b) =>
          const FakeResponse(
            statusCode: 409,
            data: {'code': 'VISIT_REPORT_SENT', 'message': 'x'},
          );
      await open(tester, server);

      await _more(tester, AppStrings.deleteRecord);
      await _tap(tester, _button(AppStrings.deleteRecord));

      expect(find.text(revertBlocked), findsOneWidget);
      expect(find.text('발바닥 각질'), findsOneWidget);
    });

    testWidgets(
      '그 사이 닫힌 링크를 끊으면(404 REPORT_NOT_FOUND) 문구를 보이고 "아직 안 보냄"으로 돌아온다',
      (tester) async {
        final server = sent();
        // 다른 기기에서 이미 끊었다 — 화면이 읽은 뒤에 링크가 없어졌다.
        server.backend.routes['DELETE $_reportPath'] = (o, b) {
          server.report = reportLinkJson();
          return const FakeResponse(
            statusCode: 404,
            data: {'code': 'REPORT_NOT_FOUND', 'message': 'x'},
          );
        };
        await open(tester, server);

        await _more(tester, AppStrings.reportRevoke);
        await _tap(tester, _button(AppStrings.reportRevoke));

        expect(find.text('이미 닫힌 알림장이에요.'), findsOneWidget);
        expect(find.text('아직 안 보냄'), findsOneWidget);
        expect(_button(AppStrings.reportShareAgain), findsNothing);
      },
    );

    testWidgets('알림장을 보내기 전 골든', (tester) async {
      await open(tester, done());

      await expectLater(
        find.byKey(ScreenKeys.visitDetail),
        matchesGoldenFile('goldens/visit_detail_report_unsent.png'),
      );
    });

    testWidgets('알림장을 보낸 뒤 골든 — 보호자가 확인함', (tester) async {
      await open(tester, sent(firstViewedAt: '2026-10-02T15:20:00+09:00'));

      await expectLater(
        find.byKey(ScreenKeys.visitDetail),
        matchesGoldenFile('goldens/visit_detail_report_sent.png'),
      );
    });
  });
}
