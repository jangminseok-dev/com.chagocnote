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
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 10, 2))];

/// 방문 101(두부)을 [status]로 보이는 서버. 전이를 받으면 상태를 바꿔 다음
/// 조회에 반영한다. [withBori]면 102(보리)가 같은 묶음·같은 상태다.
/// 서버 계약대로 `group`은 자기를 뺀 형제만 준다.
class _Server {
  _Server({this.status = 'reserved', this.withBori = false}) {
    backend = VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(
          visit: _dubu(),
          group: [if (withBori) _bori()],
          record: record,
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
    });
  }

  String status;
  String? cancelReason;
  Map<String, dynamic>? record;
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
    expect(find.textContaining('방문을 찾을 수 없어요'), findsOneWidget);
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

    testWidgets('붙은 사진과 대기열이 30장이면 사진 추가는 시트 없이 한도 문구만 보인다(카메라도 막힌다)', (
      tester,
    ) async {
      final server = _Server(status: 'in_progress')
        ..record = recordJson(
          media: [
            for (var i = 0; i < 29; i++)
              recordMediaJson(mediaId: 100 + i, sortOrder: i),
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

      expect(find.text('방문 하나에 사진은 30장까지 붙일 수 있어요.'), findsOneWidget);
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
}
