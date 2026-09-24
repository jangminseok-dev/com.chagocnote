import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

/// 두부(101)·보리(102) 묶음. [status]는 두부의 상태.
VisitTestBackend _backend({String status = 'reserved', bool group = true}) {
  final dubu = visitJson(status: status);
  final bori = visitJson(
    visitId: 102,
    pet: visitPetJson(petId: 12, name: '보리'),
  );
  final backend = VisitTestBackend({
    'GET /v1/shops/3/visits/101': (o, b) => FakeResponse(
      statusCode: 200,
      // 서버 계약 — group 은 자기(두부)를 뺀 형제만 준다.
      data: visitDetailJson(visit: dubu, group: group ? [bori] : []),
    ),
    'GET /v1/shops/3/customers/7': (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(name: '이수진'),
        pets: [
          petJson(petId: 11, name: '두부'),
          petJson(petId: 12, name: '보리'),
        ],
      ),
    ),
    'PUT /v1/shops/3/visits/101': (o, b) => FakeResponse(
      statusCode: 200,
      data: {'visit': visitJson(), 'warnings': <String>[]},
    ),
    'POST /v1/shops/3/visits/reschedule': (o, b) =>
        FakeResponse(statusCode: 200, data: savedJson([visitJson()])),
  });
  return backend;
}

Future<Closed<Object?>> _open(WidgetTester tester, CustomerTestSetup setup) {
  useTallView(tester);
  return pushOnHome<Object?>(tester, setup, '/visits/101/edit');
}

Future<void> _tapLabel(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(label).first);
  await settle(tester);
}

Finder _saveButton() =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == AppStrings.save);

Future<void> _save(WidgetTester tester) async {
  await tester.tap(_saveButton());
  await settle(tester);
}

void main() {
  testWidgets('예약됨이면 지금 값으로 채워 열고, 고친 값을 PUT 으로 모두 보낸 뒤 닫는다', (tester) async {
    final backend = _backend(group: false);
    Map<String, dynamic>? sent;
    backend.routes['PUT /v1/shops/3/visits/101'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(
        statusCode: 200,
        data: {'visit': visitJson(), 'warnings': <String>[]},
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final closed = await _open(tester, setup);

    expect(find.byKey(ScreenKeys.visitEdit), findsOneWidget);
    expect(find.text('이수진 · ${AppStrings.statusReserved}'), findsOneWidget);
    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
    await _tapLabel(tester, '15:00');
    await _tapLabel(tester, '보리');
    await tester.enterText(find.byType(TextField), '발톱 길게');
    await _save(tester);

    expect(sent, {
      'starts_at': '2026-10-02T15:00:00+09:00',
      'pet_id': 12,
      'duration_minutes': 90,
      'menu_ids': [1],
      'memo': '발톱 길게',
    });
    expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
    expect(closed.closed, isTrue);
  });

  testWidgets('방문 하나는 한 아이다 — 다른 아이를 고르면 바꿔 끼운다', (tester) async {
    final setup = CustomerTestSetup(
      _backend(group: false).call,
      overrides: _today,
    );
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tapLabel(tester, '보리');

    bool selected(String label) => tester
        .widget<AppChoiceChip>(
          find.byWidgetPredicate((w) => w is AppChoiceChip && w.label == label),
        )
        .selected;
    expect(selected('보리'), isTrue);
    expect(selected('두부'), isFalse);
  });

  testWidgets('미용 중이면 날짜·시간·반려동물은 막고, 메뉴는 고쳐 같은 시각으로 보낸다', (tester) async {
    final backend = _backend(status: 'in_progress', group: false);
    Map<String, dynamic>? sent;
    backend.routes['PUT /v1/shops/3/visits/101'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(
        statusCode: 200,
        data: {'visit': visitJson(), 'warnings': <String>[]},
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    AppChoiceChip chip(String label) => tester.widget<AppChoiceChip>(
      find.byWidgetPredicate((w) => w is AppChoiceChip && w.label == label),
    );
    expect(chip('보리').onTap, isNull);
    await tester.tap(find.text('15:00'));
    await tester.tap(find.bySemanticsLabel('10월 3일 토'));
    await settle(tester);
    await _tapLabel(tester, '위생');
    await _save(tester);

    expect(sent!['starts_at'], '2026-10-02T14:00:00+09:00');
    expect(sent!['pet_id'], 11);
    expect(sent!['menu_ids'], [1, 2]);
  });

  testWidgets('묶음의 시간을 바꾸면 같이 옮길지 묻고, 같이 옮기면 묶음을 한 번에 옮긴 뒤 이 방문을 고친다', (
    tester,
  ) async {
    final backend = _backend();
    Map<String, dynamic>? moved;
    backend.routes['POST /v1/shops/3/visits/reschedule'] = (o, body) {
      moved = bodyOf(body);
      return FakeResponse(statusCode: 200, data: savedJson([visitJson()]));
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tapLabel(tester, '16:00');
    await _save(tester);
    expect(find.text(AppStrings.moveTogetherQuestion('보리')), findsOneWidget);
    await tester.tap(find.text(AppStrings.moveTogether));
    await settle(tester);

    expect(moved, {
      'visit_ids': [101, 102],
      'starts_at': '2026-10-02T16:00:00+09:00',
    });
    final writes = [
      for (final c in setup.calls)
        if (!c.startsWith('GET')) c,
    ];
    expect(writes, [
      'POST /v1/shops/3/visits/reschedule',
      'PUT /v1/shops/3/visits/101',
    ]);
  });

  testWidgets('이 방문만 옮기면 PUT 하나만 보낸다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tapLabel(tester, '16:00');
    await _save(tester);
    await tester.tap(find.text(AppStrings.moveOnlyThis));
    await settle(tester);

    expect(setup.calls, isNot(contains('POST /v1/shops/3/visits/reschedule')));
    expect(setup.calls, contains('PUT /v1/shops/3/visits/101'));
  });

  testWidgets('시간을 그대로 두면 묻지 않는다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _save(tester);

    expect(find.text(AppStrings.moveTogetherQuestion('보리')), findsNothing);
    expect(setup.calls, contains('PUT /v1/shops/3/visits/101'));
  });

  testWidgets('묶음의 다른 방문이 예약됨이 아니면(완료 등) 묻지 않는다', (tester) async {
    final backend = _backend();
    final dubu = visitJson();
    final bori = visitJson(
      visitId: 102,
      status: 'completed',
      pet: visitPetJson(petId: 12, name: '보리'),
    );
    backend.routes['GET /v1/shops/3/visits/101'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDetailJson(visit: dubu, group: [bori]),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await _tapLabel(tester, '16:00');
    await _save(tester);

    expect(find.text(AppStrings.moveTogetherQuestion('보리')), findsNothing);
    expect(setup.calls, contains('PUT /v1/shops/3/visits/101'));
  });

  testWidgets('보관된 메뉴가 붙어 있으면 칩으로 보이고, 그대로 저장하면 남는다', (tester) async {
    final backend = _backend(group: false);
    final dubu = visitJson(menus: [menuBriefJson(menuId: 77, name: '옛 메뉴')]);
    backend.routes['GET /v1/shops/3/visits/101'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: visitDetailJson(visit: dubu, group: []),
    );
    Map<String, dynamic>? sent;
    backend.routes['PUT /v1/shops/3/visits/101'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(
        statusCode: 200,
        data: {'visit': dubu, 'warnings': <String>[]},
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.bySemanticsLabel('옛 메뉴'), findsOneWidget);
    await _save(tester);

    expect(sent!['menu_ids'], [77]);
  });

  testWidgets('시간 칸은 같은 묶음의 방문을 빼고 묻는다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    final slotQuery = setup.adapter.requests.firstWhere(
      (r) => r.path == '/v1/shops/3/visits/slots',
    );
    expect(slotQuery.uri.queryParametersAll['exclude'], ['101', '102']);
  });

  testWidgets('서버가 거절하면 문구를 보이고 남는다', (tester) async {
    final backend = _backend(group: false);
    backend.routes['PUT /v1/shops/3/visits/101'] = (o, b) => const FakeResponse(
      statusCode: 409,
      data: {'code': 'VISIT_STATE_CONFLICT', 'message': 'x'},
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final closed = await _open(tester, setup);

    await _save(tester);

    expect(closed.closed, isFalse);
    expect(find.textContaining('다른 기기에서 먼저'), findsOneWidget);
  });
}
