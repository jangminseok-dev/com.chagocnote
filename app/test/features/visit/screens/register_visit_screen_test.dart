import 'dart:async';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/tokens/app_colors.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/visit_prefill.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

Future<Closed<DateTime>> _open(
  WidgetTester tester,
  CustomerTestSetup setup, {
  String path = '/visits/new?date=2026-10-02',
  Object? extra,
}) {
  useTallView(tester);
  return pushOnHome<DateTime>(tester, setup, path, extra: extra);
}

Future<void> _pickCustomer(WidgetTester tester) async {
  await tester.tap(find.text('두부').first);
  await settle(tester);
}

Future<void> _tapLabel(WidgetTester tester, String label) async {
  await tester.tap(find.bySemanticsLabel(label).first);
  await settle(tester);
}

Finder _save() => find.byWidgetPredicate(
  (w) => w is AppButton && w.label.startsWith('예약 저장'),
);

List<String> _slotQueries(CustomerTestSetup setup) => [
  for (final r in setup.adapter.requests)
    if (r.path == '/v1/shops/3/visits/slots')
      '${r.queryParameters['date']} ${r.queryParameters['at'] ?? '-'}',
];

void main() {
  testWidgets('고객을 고르면 ②로 가고, 한 마리면 미리 골라 지난번 메뉴·소요로 채운다', (tester) async {
    final backend = VisitTestBackend();
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);
    await _pickCustomer(tester);

    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(find.text('이수진 · ··5678'), findsOneWidget);
    expect(setup.calls, contains('GET /v1/shops/3/visits/defaults'));
    expect(
      setup.adapter.requests
          .firstWhere((r) => r.path.endsWith('/defaults'))
          .queryParameters,
      {'pet_id': 11},
    );
    expect(find.text(AppStrings.prefilledFromLast), findsOneWidget);
    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
    expect(find.text(AppStrings.pickTimeFirst), findsOneWidget);
  });

  testWidgets('시간 칸을 누르면 그 시각을 서버에 묻고, 저장은 서버가 준 시각 그대로 보내고 날짜를 돌려주며 닫는다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? sent;
    backend.routes['POST /v1/shops/3/visits'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(statusCode: 201, data: savedJson([visitJson()]));
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(tester, setup);
    await _pickCustomer(tester);

    await _tapLabel(tester, '14:00');
    expect(_slotQueries(setup), contains('2026-10-02 14:00'));
    await tester.tap(_save());
    await settle(tester);

    expect(sent, {
      'customer_id': 7,
      'pet_ids': [11],
      'starts_at': '2026-10-02T14:00:00+09:00',
      'duration_minutes': 90,
      'menu_ids': [1],
      'memo': null,
      'walk_in': false,
    });
    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 10, 2));
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
  });

  testWidgets('겹치는 칸은 줄을 긋고, 눌러도 막지 않고 경고만 보인다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/visits/slots'] = (o, b) {
      final at = o.queryParameters['at'] as String?;
      return FakeResponse(
        statusCode: 200,
        data: at == null
            ? slotsJson(
                warnings: {
                  15: ['overlap'],
                  16: ['closed_day'],
                  17: ['overlap', 'outside_hours'],
                },
              )
            : slotAtJson(at: at, warnings: ['overlap']),
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    // 겹침은 흰 바탕에 잉크색 줄긋기, 휴무·영업 밖은 옅은 바탕에 옅은 글자 —
    // 둘이 구분된다(A2 잔여). 둘 다면 옅은 바탕에 줄긋기.
    Color tileColor(String at) =>
        (tester
                    .widget<Container>(
                      find.ancestor(
                        of: find.text(at),
                        matching: find.byType(Container),
                      ).first,
                    )
                    .decoration
                as BoxDecoration)
            .color!;
    final struck = tester.widget<Text>(find.text('15:00'));
    expect(struck.style!.decoration, TextDecoration.lineThrough);
    expect(struck.style!.color, AppColors.ink);
    expect(tileColor('15:00'), AppColors.white);
    final faint = tester.widget<Text>(find.text('16:00'));
    expect(faint.style!.decoration, isNot(TextDecoration.lineThrough));
    expect(faint.style!.color, AppColors.secondary);
    expect(tileColor('16:00'), AppColors.backgroundTop);
    final both = tester.widget<Text>(find.text('17:00'));
    expect(both.style!.decoration, TextDecoration.lineThrough);
    expect(tileColor('17:00'), AppColors.backgroundTop);
    final plain = tester.widget<Text>(find.text('14:00'));
    expect(plain.style!.decoration, isNot(TextDecoration.lineThrough));
    expect(tileColor('14:00'), AppColors.white);

    await _tapLabel(tester, '15:00');
    expect(find.text('· ${AppStrings.warningOverlap}'), findsOneWidget);
    expect(tester.widget<AppButton>(_save()).onPressed, isNotNull);
  });

  testWidgets('날짜를 바꾸면 그 날의 시간 칸과 고른 시각을 다시 묻는다', (tester) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);
    await _tapLabel(tester, '14:00');

    await _tapLabel(tester, '10월 3일 토');

    expect(
      _slotQueries(setup),
      containsAll(['2026-10-03 -', '2026-10-03 14:00']),
    );
    expect(
      find.text(AppStrings.saveReservation('10월 3일 토 14:00')),
      findsOneWidget,
    );
  });

  testWidgets('다음 주로 넘기면 그 주의 날짜가 보이고, 달이 바뀌면 그달의 휴무를 읽는다', (tester) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, path: '/visits/new?date=2026-09-23');
    await _pickCustomer(tester);
    expect(find.bySemanticsLabel('9월 21일 월'), findsOneWidget);

    await _tapLabel(tester, AppStrings.nextWeek);

    expect(find.bySemanticsLabel('9월 28일 월'), findsOneWidget);
    expect(find.bySemanticsLabel('10월 4일 일'), findsOneWidget);
    final months = [
      for (final r in setup.adapter.requests)
        if (r.path.endsWith('/calendar')) r.queryParameters['month'],
    ];
    expect(months, containsAll(['2026-09', '2026-10']));
  });

  testWidgets('시간 칸을 길게 누르면 10분 단위로 고른다', (tester) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    await tester.longPress(find.text('14:00'));
    await settle(tester);
    expect(find.text(AppStrings.pickMinuteTitle), findsOneWidget);
    await tester.tap(find.text('14:40'));
    await settle(tester);

    expect(_slotQueries(setup), contains('2026-10-02 14:40'));
    expect(
      find.text(AppStrings.saveReservation('10월 2일 금 14:40')),
      findsOneWidget,
    );
  });

  testWidgets('두 마리를 고르면 한 번에 둘을, "보호자만"이면 반려동물 없이 보낸다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/customers/7'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(name: '이수진'),
        pets: [
          petJson(petId: 11, name: '두부'),
          petJson(petId: 12, name: '보리'),
          petJson(petId: 13, name: '별이', passedAwayAt: '2026-01-01T00:00:00Z'),
        ],
      ),
    );
    final bodies = <Map<String, dynamic>>[];
    backend.routes['POST /v1/shops/3/visits'] = (o, body) {
      bodies.add(bodyOf(body));
      return const FakeResponse(
        statusCode: 422,
        data: {'code': 'VISIT_CROSSES_MIDNIGHT', 'message': 'x'},
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    // 여럿이면 미리 고르지 않는다. 무지개다리 아이는 칩이 없다.
    expect(find.text(AppStrings.pickPetFirst), findsOneWidget);
    expect(find.bySemanticsLabel('별이'), findsNothing);
    // 시각을 골라도 반려동물이나 "보호자만"을 고르기 전에는 저장할 수 없다.
    await _tapLabel(tester, '14:00');
    final blocked = find.byWidgetPredicate(
      (w) => w is AppButton && w.label == AppStrings.pickPetFirst,
    );
    expect(tester.widget<AppButton>(blocked).onPressed, isNull);
    await _tapLabel(tester, '두부');
    await _tapLabel(tester, '보리');
    await tester.tap(_save());
    await settle(tester);
    expect(bodies.last['pet_ids'], [11, 12]);

    await _tapLabel(tester, AppStrings.ownerOnly);
    await tester.tap(_save());
    await settle(tester);
    expect(bodies.last['pet_ids'], isEmpty);
  });

  testWidgets('두부·보리를 고른 뒤 두부를 풀면 남은 보리로 "지난번처럼"을 다시 묻는다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/customers/7'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(name: '이수진'),
        pets: [
          petJson(petId: 11, name: '두부'),
          petJson(petId: 12, name: '보리'),
        ],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    await _tapLabel(tester, '두부');
    await _tapLabel(tester, '보리');
    List<Object?> petIdsAsked() => [
      for (final r in setup.adapter.requests)
        if (r.path.endsWith('/defaults')) r.queryParameters['pet_id'],
    ];
    // 둘 다 고른 동안(하나만 남은 게 아니다)은 아직 보리를 묻지 않는다.
    expect(petIdsAsked(), isNot(contains(12)));

    await _tapLabel(tester, '두부');

    expect(petIdsAsked(), contains(12));
  });

  testWidgets('메뉴를 고르면 소요를 메뉴 합으로 채우고, 소요를 손대면 메뉴가 더는 바꾸지 않는다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/visits/defaults'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: defaultsJson(sourceVisitId: null, durationMinutes: 120, menus: []),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);
    expect(find.text(AppStrings.prefilledFromLast), findsNothing);
    expect(find.text(AppStrings.durationText(120)), findsOneWidget);

    await _tapLabel(tester, '목욕');
    await _tapLabel(tester, '부분 미용');
    expect(find.text(AppStrings.durationText(150)), findsOneWidget);

    await _tapLabel(tester, AppStrings.longer);
    expect(find.text(AppStrings.durationText(160)), findsOneWidget);
    await tester.longPress(find.bySemanticsLabel(AppStrings.longer));
    await settle(tester);
    expect(find.text(AppStrings.durationText(190)), findsOneWidget);
    await _tapLabel(tester, '위생');
    expect(find.text(AppStrings.durationText(190)), findsOneWidget);
  });

  testWidgets('늦게 온 옛 아이의 "지난번처럼"은 버린다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/customers/7'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        pets: [
          petJson(petId: 11, name: '두부'),
          petJson(petId: 12, name: '보리'),
        ],
      ),
    );
    final slow = Completer<FakeResponse>();
    backend.routes['GET /v1/shops/3/visits/defaults'] = (o, b) {
      if (o.queryParameters['pet_id'] == 11) return slow.future;
      return FakeResponse(
        statusCode: 200,
        data: defaultsJson(
          durationMinutes: 60,
          menus: [menuBriefJson(menuId: 2, name: '위생')],
        ),
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    await _tapLabel(tester, '두부');
    await _tapLabel(tester, '두부');
    await _tapLabel(tester, '보리');
    expect(find.text(AppStrings.durationText(60)), findsOneWidget);
    slow.complete(
      FakeResponse(statusCode: 200, data: defaultsJson(durationMinutes: 150)),
    );
    await settle(tester);

    expect(find.text(AppStrings.durationText(60)), findsOneWidget);
  });

  testWidgets('저장을 두 번 눌러 VISIT_DUPLICATE 면 이미 저장된 것으로 보고 닫는다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visits'] = (o, b) => const FakeResponse(
      statusCode: 409,
      data: {'code': 'VISIT_DUPLICATE', 'message': 'x'},
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(tester, setup);
    await _pickCustomer(tester);
    await _tapLabel(tester, '14:00');

    await tester.tap(_save());
    await settle(tester);

    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 10, 2));
    // 닫힌 뒤 홈 위에 스낵바로 알린다(A2 잔여 — 설계 6.2 "이미 저장됐어요").
    expect(find.text(AppStrings.duplicateVisitNotice), findsOneWidget);
  });

  testWidgets('다음 예약 초안의 저장이 VISIT_DUPLICATE 면(한 아이가 이미 예약됨) 문구를 보이고 닫는다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visits'] = (o, b) => const FakeResponse(
      statusCode: 409,
      data: {'code': 'VISIT_DUPLICATE', 'message': 'x'},
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(
      tester,
      setup,
      path: '/visits/new',
      extra: NextVisitDraft.fromJson(nextDraftJson(petIds: [11, 12])),
    );

    await tester.tap(_save());
    await settle(tester);

    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 10, 30));
    expect(find.text(AppStrings.duplicateVisitNotice), findsOneWidget);
    expect(find.byKey(ScreenKeys.registerVisit), findsNothing);
  });

  testWidgets('서버가 거절하면 문구를 보이고 폼에 남는다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visits'] = (o, b) => const FakeResponse(
      statusCode: 422,
      data: {'code': 'VISIT_CROSSES_MIDNIGHT', 'message': 'x'},
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);
    await _tapLabel(tester, '14:00');

    await tester.tap(_save());
    await settle(tester);

    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    expect(find.textContaining('자정을 넘습니다'), findsOneWidget);
  });

  testWidgets('저장 중에는 버튼을 막아 요청을 한 번만 보낸다', (tester) async {
    final backend = VisitTestBackend();
    final gate = Completer<FakeResponse>();
    backend.routes['POST /v1/shops/3/visits'] = (o, b) => gate.future;
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);
    await _tapLabel(tester, '14:00');

    await tester.tap(_save());
    await tester.pump();
    await tester.tap(_save(), warnIfMissed: false);
    await tester.pump();
    gate.complete(
      FakeResponse(statusCode: 201, data: savedJson([visitJson()])),
    );
    await tester.pumpAndSettle();

    expect(
      setup.calls.where((c) => c == 'POST /v1/shops/3/visits'),
      hasLength(1),
    );
  });

  testWidgets('[지금 시작]은 시각 없이 walk_in 으로 보낸다', (tester) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? sent;
    backend.routes['POST /v1/shops/3/visits'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(statusCode: 201, data: savedJson([visitJson()]));
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup, path: '/visits/new?date=2026-09-23');
    await _pickCustomer(tester);

    await tester.tap(find.text(AppStrings.startNow));
    await settle(tester);

    expect(sent!['walk_in'], isTrue);
    expect(sent!.containsKey('starts_at'), isFalse);
    expect(sent!['duration_minutes'], 90);
  });

  testWidgets('다른 날을 보고 있어도 [지금 시작]이 보인다 — 예약 없이 온 손님은 지금 시작한다', (
    tester,
  ) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    expect(find.text(AppStrings.startNow), findsOneWidget);
  });

  testWidgets('다른 날을 보다가 [지금 시작]을 누르면 서버가 저장한 오늘 날짜를 돌려준다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visits'] = (o, b) => FakeResponse(
      statusCode: 201,
      data: savedJson([visitJson(date: '2026-09-23', start: '10:00')]),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(tester, setup);
    await _pickCustomer(tester);

    await tester.tap(find.text(AppStrings.startNow));
    await settle(tester);

    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 9, 23));
  });

  testWidgets('다른 날을 보다가 [지금 시작]이 VISIT_DUPLICATE 면 오늘 날짜를 돌려주며 닫는다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    backend.routes['POST /v1/shops/3/visits'] = (o, b) => const FakeResponse(
      statusCode: 409,
      data: {'code': 'VISIT_DUPLICATE', 'message': 'x'},
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(tester, setup);
    await _pickCustomer(tester);

    await tester.tap(find.text(AppStrings.startNow));
    await settle(tester);

    expect(result.closed, isTrue);
    expect(result.value, DateTime(2026, 9, 23));
  });

  testWidgets('새 고객 등록으로 가서 등록하면 그 고객의 ②로 바로 온다', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/customers/8'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(
          customerId: 8,
          name: '한지우',
          phone: '01098761122',
        ),
        pets: [petJson(petId: 21, customerId: 8, name: '두부')],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);

    await tester.tap(find.text(AppStrings.registerNewCustomer));
    await settle(tester);
    expect(find.byKey(ScreenKeys.registerCustomer), findsOneWidget);
    // 등록 화면이 고객 ID 를 돌려주며 닫힌 것처럼 한다.
    setup.container.read(routerProvider).pop(8);
    await settle(tester);

    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(find.text('한지우 · ··1122'), findsOneWidget);
  });

  testWidgets('다음 예약 초안으로 열면 ①을 건너뛰고 채워 열며, "지난번처럼"을 부르지 않는다', (tester) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(
      tester,
      setup,
      path: '/visits/new',
      extra: NextVisitDraft.fromJson(nextDraftJson()),
    );

    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(find.text(AppStrings.changeCustomer), findsNothing);
    expect(
      find.text(AppStrings.saveReservation('10월 30일 금 14:00')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
    expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
  });

  testWidgets('카톡 초안(보호자 있음)으로 열면 ①을 건너뛰고 날짜·시각·메뉴로 채우며, 뒤로 가면 닫힌다', (
    tester,
  ) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    final result = await _open(
      tester,
      setup,
      path: '/visits/new',
      extra: VisitPrefill(
        customerId: 7,
        date: DateTime(2026, 10, 2),
        at: '14:30',
        petIds: const {11},
        menus: const [MenuBrief(menuId: 3, name: '부분 미용')],
      ),
    );

    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(find.text(AppStrings.changeCustomer), findsNothing);
    expect(
      find.text(AppStrings.saveReservation('10월 2일 금 14:30')),
      findsOneWidget,
    );
    // 소요는 메뉴 기본 소요의 합(부분 미용 90분)이고, "지난번처럼"은 부르지 않는다.
    expect(find.text(AppStrings.durationText(90)), findsOneWidget);
    expect(find.text(AppStrings.prefilledFromLast), findsNothing);
    expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
    expect(_slotQueries(setup), contains('2026-10-02 14:30'));

    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await settle(tester);
    expect(result.closed, isTrue);
    expect(result.value, isNull);
  });

  testWidgets('카톡 초안(보호자 없음)으로 열면 ①에서 고른 뒤 ②가 초안의 날짜·시각·메뉴로 채워진다', (
    tester,
  ) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(
      tester,
      setup,
      path: '/visits/new',
      extra: VisitPrefill(
        date: DateTime(2026, 10, 3),
        at: '11:00',
        menus: const [MenuBrief(menuId: 1, name: '목욕')],
      ),
    );

    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);
    await _pickCustomer(tester);

    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(
      find.text(AppStrings.saveReservation('10월 3일 토 11:00')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.durationText(60)), findsOneWidget);
    expect(setup.calls, isNot(contains('GET /v1/shops/3/visits/defaults')));
    // 보호자를 골랐으니 [바꾸기]와 뒤로 가기는 ①로 돌아간다.
    expect(find.text(AppStrings.changeCustomer), findsOneWidget);
  });

  testWidgets('카톡 초안이 넘긴 아이가 이 보호자의 아이가 아니면 버리고, 하나뿐인 아이를 고른다', (
    tester,
  ) async {
    final backend = VisitTestBackend();
    Map<String, dynamic>? sent;
    backend.routes['POST /v1/shops/3/visits'] = (o, body) {
      sent = bodyOf(body);
      return FakeResponse(statusCode: 201, data: savedJson([visitJson()]));
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(
      tester,
      setup,
      path: '/visits/new',
      extra: VisitPrefill(
        customerId: 7,
        date: DateTime(2026, 10, 2),
        at: '14:00',
        petIds: const {99},
        menus: const [MenuBrief(menuId: 1, name: '목욕')],
      ),
    );

    await tester.tap(_save());
    await settle(tester);
    expect(sent?['pet_ids'], [11]);
  });

  testWidgets('카톡 초안에 메뉴가 없으면 "지난번처럼"으로 채운다', (tester) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(
      tester,
      setup,
      path: '/visits/new',
      extra: VisitPrefill(customerId: 7, date: DateTime(2026, 10, 2)),
    );

    expect(find.text(AppStrings.reserveWhenTitle), findsOneWidget);
    expect(setup.calls, contains('GET /v1/shops/3/visits/defaults'));
    expect(find.text(AppStrings.prefilledFromLast), findsOneWidget);
    expect(find.text(AppStrings.pickTimeFirst), findsOneWidget);
  });

  testWidgets('[바꾸기]와 뒤로 가기는 ①로 돌아간다', (tester) async {
    final setup = CustomerTestSetup(VisitTestBackend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);

    await tester.tap(find.text(AppStrings.changeCustomer));
    await settle(tester);
    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);

    await _pickCustomer(tester);
    await tester.tap(find.bySemanticsLabel(AppStrings.back));
    await settle(tester);
    expect(find.text(AppStrings.reserveWhoTitle), findsOneWidget);
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
  });

  testWidgets('예약 ② 골든', (tester) async {
    final backend = VisitTestBackend();
    backend.routes['GET /v1/shops/3/customers/7'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(name: '이수진'),
        pets: [
          petJson(petId: 11, name: '두부'),
          petJson(petId: 12, name: '보리'),
        ],
      ),
    );
    backend.routes['GET /v1/shops/3/visits/slots'] = (o, b) {
      final at = o.queryParameters['at'] as String?;
      return FakeResponse(
        statusCode: 200,
        data: at == null
            ? slotsJson(
                warnings: {
                  15: ['overlap'],
                  16: ['overlap'],
                },
              )
            : slotAtJson(at: at),
      );
    };
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _open(tester, setup);
    await _pickCustomer(tester);
    await _tapLabel(tester, '두부');
    await _tapLabel(tester, '14:00');
    tester.view.physicalSize = const Size(390, 1100);
    await tester.pumpAndSettle();

    await expectLater(
      find.byKey(ScreenKeys.registerVisit),
      matchesGoldenFile('goldens/register_visit_form.png'),
    );
  });
}
