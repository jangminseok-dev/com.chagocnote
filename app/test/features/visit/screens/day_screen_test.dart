import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/storage/prefs_store.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

const _date = '2026-09-23';

Map<String, dynamic> _v(
  int id,
  String start, {
  int duration = 60,
  String status = 'reserved',
  String pet = '콩이',
  int petId = 11,
  String owner = '김민지',
  int customerId = 7,
  List<Map<String, dynamic>>? menus,
}) => visitJson(
  visitId: id,
  date: _date,
  start: start,
  durationMinutes: duration,
  status: status,
  pet: visitPetJson(petId: petId, name: pet),
  customer: visitCustomerJson(customerId: customerId, name: owner),
  menus: menus,
);

/// 목업의 하루 — 콩이 완료, 두부·보리 미용 중(묶음), 1시간 빈 뒤 몽이 예약,
/// 겹치는 코코 예약.
List<Map<String, dynamic>> _mockupItems({String duoStatus = 'in_progress'}) => [
  dayItemJson(
    _v(
      1,
      '10:00',
      duration: 150,
      status: 'completed',
      menus: [menuBriefJson(menuId: 4, name: '전체 미용')],
    ),
  ),
  dayItemJson(
    _v(
      2,
      '13:00',
      duration: 90,
      status: duoStatus,
      pet: '두부',
      owner: '이수진',
      customerId: 8,
    ),
    groupKey: 'duo',
  ),
  dayItemJson(
    _v(
      3,
      '13:00',
      duration: 90,
      status: duoStatus,
      pet: '보리',
      petId: 12,
      owner: '이수진',
      customerId: 8,
    ),
    groupKey: 'duo',
  ),
  dayItemJson(
    _v(
      4,
      '15:30',
      duration: 120,
      pet: '몽이',
      owner: '박하늘',
      customerId: 9,
      menus: [menuBriefJson(menuId: 2, name: '위생')],
    ),
    overlapping: true,
  ),
  dayItemJson(
    _v(5, '17:00', pet: '코코', owner: '최유리', customerId: 10, menus: []),
    overlapping: true,
  ),
];

VisitTestBackend _backend([List<Map<String, dynamic>>? items]) =>
    VisitTestBackend({
      'GET /v1/shops/3/visits': (o, b) => FakeResponse(
        statusCode: 200,
        data: dayJson(date: _date, items: items ?? _mockupItems()),
      ),
      'POST /v1/shops/3/visits/transitions': (o, b) => FakeResponse(
        statusCode: 200,
        data: {
          'visits': [_v(2, '13:00', status: 'completed')],
        },
      ),
      'GET /v1/shops/3/visits/2': (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(visit: _v(2, '13:00', pet: '두부')),
      ),
      'GET /v1/shops/3/visits/2/next-draft': (o, b) => FakeResponse(
        statusCode: 200,
        data: nextDraftJson(
          petIds: [11, 12],
          startsAt: '2026-10-21T13:00:00+09:00',
        ),
      ),
      'POST /v1/shops/3/closed-dates': (o, b) =>
          FakeResponse(statusCode: 200, data: {'date': _date, 'note': null}),
      'DELETE /v1/shops/3/closed-dates/$_date': (o, b) =>
          const FakeResponse(statusCode: 204),
    });

Future<void> _open(WidgetTester tester, CustomerTestSetup setup) async {
  useTallView(tester, height: 1100);
  await pushOnHome<Object?>(tester, setup, '/visits/day/$_date');
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

void main() {
  testWidgets('묶음을 카드 하나로, 상태에 맞는 버튼과 빈 시간·겹침 표시를 보인다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.byKey(ScreenKeys.day), findsOneWidget);
    expect(
      setup.adapter.requests
          .firstWhere((r) => r.path == '/v1/shops/3/visits')
          .queryParameters,
      {'date': _date},
    );
    expect(find.text('5마리 · 완료 1 · 미용 중 2 · 예약 2'), findsOneWidget);
    expect(find.text('두부 · 보리'), findsOneWidget);
    expect(find.text('~14:30'), findsOneWidget);
    expect(find.text('목욕 · 이수진'), findsOneWidget);
    expect(find.text(AppStrings.gapText(60)), findsOneWidget);
    expect(find.text('위생 · 박하늘 · ${AppStrings.markOverlap}'), findsOneWidget);
    expect(
      find.text('${AppStrings.noMenu} · 최유리 · ${AppStrings.markOverlap}'),
      findsOneWidget,
    );
    expect(_button(AppStrings.actionCompleteShort), findsOneWidget);
    expect(_button(AppStrings.actionStart), findsNWidgets(2));
    expect(find.text(AppStrings.statusCompleted), findsOneWidget);
  });

  testWidgets('상태가 섞인 가족 카드는 아이별 상태를 적고, 아직 진행 가능한 아이만 버튼으로 보낸다', (
    tester,
  ) async {
    final backend = _backend([
      dayItemJson(
        _v(
          2,
          '13:00',
          status: 'completed',
          pet: '두부',
          owner: '이수진',
          customerId: 8,
        ),
        groupKey: 'duo',
      ),
      dayItemJson(
        _v(
          3,
          '13:00',
          status: 'in_progress',
          pet: '보리',
          petId: 12,
          owner: '이수진',
          customerId: 8,
        ),
        groupKey: 'duo',
      ),
      dayItemJson(
        _v(
          4,
          '15:00',
          status: 'canceled',
          pet: '몽이',
          owner: '박하늘',
          customerId: 9,
        ),
        groupKey: 'trio',
      ),
      dayItemJson(
        _v(
          5,
          '15:00',
          status: 'completed',
          pet: '코코',
          petId: 13,
          owner: '박하늘',
          customerId: 9,
        ),
        groupKey: 'trio',
      ),
    ]);
    Map<String, dynamic>? sent;
    backend.routes['POST /v1/shops/3/visits/transitions'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(
        statusCode: 200,
        data: {
          'visits': [_v(3, '13:00', status: 'completed', pet: '보리', petId: 12)],
        },
      );
    };
    backend.routes['GET /v1/shops/3/visits/3/next-draft'] = (o, b) =>
        FakeResponse(statusCode: 200, data: nextDraftJson(petIds: [12]));
    // 기록 화면은 보리(3)의 상세를 읽는다 — 묶음의 두부(2)는 이미 완료라 함께 보내지 않는다.
    backend.routes['GET /v1/shops/3/visits/3'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDetailJson(
        visit: _v(3, '13:00', status: 'in_progress', pet: '보리', petId: 12),
        group: [_v(2, '13:00', status: 'completed', pet: '두부')],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.text('두부 완료 · 보리 미용 중'), findsOneWidget);
    // 진행 가능한 아이가 없는 묶음(취소·완료)은 칩만.
    expect(find.text('몽이 취소 · 코코 완료'), findsOneWidget);
    expect(_button(AppStrings.actionCompleteShort), findsOneWidget);
    expect(_button(AppStrings.actionStart), findsNothing);

    await tester.tap(_button(AppStrings.actionCompleteShort));
    await settle(tester);
    await tester.tap(_button(AppStrings.completeWithoutRecord));
    await settle(tester);
    expect(sent, {
      'visit_ids': [3],
      'action': 'complete',
    });
    expect(setup.calls, contains('GET /v1/shops/3/visits/3/next-draft'));
  });

  testWidgets('카드의 [시작]은 묶음 전체를 한 번에 보내고 그날 목록을 다시 불러온다', (tester) async {
    final backend = _backend(_mockupItems(duoStatus: 'reserved'));
    Map<String, dynamic>? sent;
    backend.routes['POST /v1/shops/3/visits/transitions'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(
        statusCode: 200,
        data: {
          'visits': [_v(2, '13:00', status: 'in_progress')],
        },
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    setup.adapter.requests.clear();

    await tester.tap(_button(AppStrings.actionStart).first);
    await settle(tester);

    expect(sent, {
      'visit_ids': [2, 3],
      'action': 'start',
    });
    expect(setup.calls, contains('GET /v1/shops/3/visits'));
  });

  testWidgets(
    '카드의 [완료하기]는 묶음 첫 아이의 기록 화면을 열고, 완료하면 묶음을 함께 완료한 뒤 다음 예약 시트를 띄운다',
    (tester) async {
      final backend = _backend();
      Map<String, dynamic>? sent;
      backend.routes['GET /v1/shops/3/visits/2'] = (o, b) => FakeResponse(
        statusCode: 200,
        data: visitDetailJson(
          visit: _v(2, '13:00', status: 'in_progress', pet: '두부'),
          group: [_v(3, '13:00', status: 'in_progress', pet: '보리', petId: 12)],
        ),
      );
      backend.routes['POST /v1/shops/3/visits/transitions'] = (o, body) {
        sent = bodyOf(body);
        return FakeResponse(
          statusCode: 200,
          data: {
            'visits': [_v(2, '13:00', status: 'completed')],
          },
        );
      };
      final setup = CustomerTestSetup(backend.call, overrides: _today);
      addTearDown(setup.container.dispose);
      await _open(tester, setup);

      await tester.tap(_button(AppStrings.actionCompleteShort));
      await settle(tester);
      expect(find.byKey(ScreenKeys.visitRecord), findsOneWidget);
      await tester.tap(_button(AppStrings.completeWithoutRecord));
      await settle(tester);

      expect(sent, {
        'visit_ids': [2, 3],
        'action': 'complete',
      });
      expect(find.text(AppStrings.completeTitle), findsOneWidget);
      expect(
        find.text(AppStrings.nextPreview('10월 21일 수 13:00')),
        findsOneWidget,
      );
      await tester.tap(_button(AppStrings.close));
      await settle(tester);
      expect(find.byKey(ScreenKeys.day), findsOneWidget);
    },
  );

  testWidgets('한 카드를 보내는 동안 다른 카드의 버튼도 막는다', (tester) async {
    final backend = _backend(_mockupItems(duoStatus: 'reserved'));
    final gate = Completer<FakeResponse>();
    backend.routes['POST /v1/shops/3/visits/transitions'] = (o, b) =>
        gate.future;
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.actionStart).first);
    await tester.pump();

    final buttons = tester.widgetList<AppButton>(
      _button(AppStrings.actionStart),
    );
    expect(buttons.every((b) => b.onPressed == null), isTrue);
    gate.complete(
      FakeResponse(
        statusCode: 200,
        data: {
          'visits': [_v(2, '13:00', status: 'in_progress')],
        },
      ),
    );
    await settle(tester);
  });

  testWidgets('서버가 거절하면 문구를 보인다', (tester) async {
    final backend = _backend(_mockupItems(duoStatus: 'reserved'));
    backend.routes['POST /v1/shops/3/visits/transitions'] = (o, b) =>
        const FakeResponse(
          statusCode: 409,
          data: {'code': 'VISIT_STATE_CONFLICT', 'message': 'x'},
        );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(_button(AppStrings.actionStart).first);
    await settle(tester);

    expect(find.textContaining('다른 기기에서 먼저'), findsOneWidget);
  });

  testWidgets('카드를 누르면 묶음의 첫 방문 상세로 간다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(find.text('두부 · 보리'));
    await settle(tester);

    expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
  });

  testWidgets('정리 안 된 예약과 취소는 표시하고, 취소는 빈 시간으로 센다', (tester) async {
    final setup = CustomerTestSetup(
      _backend([
        dayItemJson(_v(1, '10:00'), unresolved: true),
        dayItemJson(
          _v(2, '11:00', status: 'canceled', pet: '두부', customerId: 8),
        ),
        dayItemJson(_v(3, '12:00', pet: '몽이', customerId: 9)),
      ]).call,
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(
      find.text('목욕 · 김민지 · ${AppStrings.markUnresolved}'),
      findsOneWidget,
    );
    expect(find.text(AppStrings.statusCanceled), findsOneWidget);
    expect(find.text(AppStrings.gapText(60)), findsOneWidget);
    expect(find.text('2마리 · 예약 2 · 취소 1'), findsOneWidget);
  });

  testWidgets('시간표로 바꾸면 기기에 기억하고 시간 줄 위에 묶음을 그린다(취소는 그리지 않는다)', (tester) async {
    final setup = CustomerTestSetup(
      _backend([
        ..._mockupItems(),
        dayItemJson(
          _v(6, '11:00', status: 'canceled', pet: '별이', customerId: 11),
        ),
      ]).call,
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.viewAsTimeline));
    await settle(tester);

    expect(await setup.prefs.read(PrefsKeys.dayViewMode), 'timeline');
    expect(find.text('10:00'), findsOneWidget);
    expect(find.text('19:00'), findsOneWidget);
    expect(find.text('Wednesday'), findsOneWidget);
    expect(find.text('두부 · 보리'), findsOneWidget);
    expect(find.text('별이'), findsNothing);
    expect(_button(AppStrings.actionStart), findsNothing);
    // 겹치는 몽이·코코는 옆 칸이다.
    final mong = tester.getRect(find.text('몽이'));
    final coco = tester.getRect(find.text('코코'));
    expect(coco.left, greaterThan(mong.left));
  });

  testWidgets('기억한 것이 시간표면 시간표로 연다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
    await _open(tester, setup);

    expect(find.text('10:00'), findsOneWidget);
    expect(_button(AppStrings.actionStart), findsNothing);
  });

  testWidgets('30분 방문도 시간표에서 넘치지 않는다', (tester) async {
    final setup = CustomerTestSetup(
      _backend([dayItemJson(_v(1, '10:00', duration: 30))]).call,
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
    await _open(tester, setup);

    expect(tester.takeException(), isNull);
    // 이름만으로는 아쉽다 — 메뉴를 같은 줄에 잇는다(A2 잔여).
    expect(find.text('콩이 · 목욕', findRichText: true), findsOneWidget);
    expect(find.text('콩이'), findsNothing);
  });

  testWidgets('마감이 19:30 이면 시간표가 20:00 까지 그린다', (tester) async {
    final backend = _backend([dayItemJson(_v(1, '10:00', duration: 60))]);
    backend.routes['GET /v1/shops/3/visit-settings'] = (o, b) =>
        FakeResponse(statusCode: 200, data: settingsJson(closesAt: '19:30:00'));
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
    await _open(tester, setup);

    expect(find.text('19:00'), findsOneWidget);
    expect(find.text('20:00'), findsOneWidget);
  });

  testWidgets('사장은 ··· 로 이 날을 휴무로 표시하고 해제한다', (tester) async {
    var closed = false;
    final backend = _backend([]);
    backend.routes['GET /v1/shops/3/visits'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: dayJson(date: _date, closedDay: closed),
    );
    backend.routes['POST /v1/shops/3/closed-dates'] = (o, b) {
      closed = true;
      return FakeResponse(statusCode: 200, data: {'date': _date, 'note': null});
    };
    backend.routes['DELETE /v1/shops/3/closed-dates/$_date'] = (o, b) {
      closed = false;
      return const FakeResponse(statusCode: 204);
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.more));
    await settle(tester);
    await tester.tap(find.text(AppStrings.markClosedDate));
    await settle(tester);
    expect(setup.calls, contains('POST /v1/shops/3/closed-dates'));
    expect(find.text('${AppStrings.closedDayNote} · 0마리'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel(AppStrings.more));
    await settle(tester);
    await tester.tap(find.text(AppStrings.unmarkClosedDate));
    await settle(tester);
    expect(setup.calls, contains('DELETE /v1/shops/3/closed-dates/$_date'));
    expect(find.text('0마리'), findsOneWidget);
  });

  testWidgets('직원에게는 ··· 가 없다(V8)', (tester) async {
    final setup = CustomerTestSetup(
      _backend().call,
      role: 'staff',
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.bySemanticsLabel(AppStrings.more), findsNothing);
  });

  testWidgets('예약이 없으면 안내하고, 휴무일은 머리에 적는다', (tester) async {
    final backend = _backend();
    backend.routes['GET /v1/shops/3/visits'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: dayJson(date: _date, closedDay: true),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.text(AppStrings.dayEmpty), findsOneWidget);
    expect(find.text('${AppStrings.closedDayNote} · 0마리'), findsOneWidget);
  });

  testWidgets('+ 는 그 날짜로 예약 등록을 연다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.addReservation));
    await settle(tester);
    await tester.tap(find.text('이수진 · 010-12··-5678'));
    await settle(tester);

    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    final slotDates = {
      for (final r in setup.adapter.requests)
        if (r.path.endsWith('/slots')) r.queryParameters['date'],
    };
    expect(slotDates, {_date});
  });

  testWidgets('불러오지 못하면 다시 시도한다', (tester) async {
    var fail = true;
    final backend = _backend();
    final ok = backend.routes['GET /v1/shops/3/visits']!;
    backend.routes['GET /v1/shops/3/visits'] = (o, b) =>
        fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    expect(_button(AppStrings.retry), findsOneWidget);

    fail = false;
    await tester.tap(_button(AppStrings.retry));
    await settle(tester);

    expect(find.text('두부 · 보리'), findsOneWidget);
  });

  testWidgets('하루 목록 골든', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.day),
      matchesGoldenFile('goldens/day_list.png'),
    );
  });

  testWidgets('하루 시간표 골든', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await setup.prefs.write(PrefsKeys.dayViewMode, 'timeline');
    await _open(tester, setup);
    tester.view.physicalSize = const Size(390, 844);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.day),
      matchesGoldenFile('goldens/day_timeline.png'),
    );
  });
}
