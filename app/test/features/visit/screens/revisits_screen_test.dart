// 다시 올 때가 된 아이(⑬ 설계 3.3) — 지남·곧, [예약]·[안내], 주기 시트, 캘린더 탭의 줄.
import 'package:chagocnote/core/plugs/care_marks_plug.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/customer/screens/grooming_cycle_row.dart';
import 'package:chagocnote/features/visit/state/visit_commands.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 11, 17))];

/// 지남 둘(보리·두부)·곧 하나(콩이). 안내하면 그 아이의 안내한 날이 오늘이 된다.
class _Server {
  _Server() {
    backend = VisitTestBackend({
      'GET /v1/shops/3/revisits/counts': (o, b) =>
          FakeResponse(statusCode: 200, data: {'soon': soon.length, 'due': due.length}),
      'GET /v1/shops/3/revisits': (o, b) => FakeResponse(
        statusCode: 200,
        data: revisitPageJson(items: o.queryParameters['bucket'] == 'soon' ? soon : due),
      ),
      'GET /v1/shops/3/visits/501/next-draft': (o, b) => FakeResponse(
        statusCode: 200,
        data: nextDraftJson(petIds: [101], startsAt: '2026-11-10T14:00:00+09:00', cycleWeeks: 6, cycleSource: 'computed'),
      ),
      'PUT /v1/shops/3/pets/101/revisit-nudge': (o, b) {
        nudges.add(101);
        due = [
          revisitItemJson(petId: 101, name: '보리', lastVisitId: 501, nudgedOn: '2026-11-17', message: 'M-보리'),
          due.last,
        ];
        return const FakeResponse(statusCode: 204);
      },
      'GET /v1/shops/3/pets/101': (o, b) => FakeResponse(
        statusCode: 200,
        data: petDetailJson(pet: petJson(petId: 101, name: '보리'), revisit: petRevisitJson()),
      ),
      'GET /v1/shops/3/revisit-settings': (o, b) =>
          FakeResponse(statusCode: 200, data: revisitSettingsJson()),
      'PUT /v1/shops/3/revisit-settings': (o, body) {
        settingsPuts.add(bodyOf(body));
        return FakeResponse(statusCode: 200, data: revisitSettingsJson(soonDays: 10));
      },
    });
  }

  late final VisitTestBackend backend;
  List<Map<String, dynamic>> due = [
    revisitItemJson(petId: 101, name: '보리', lastVisitId: 501, message: 'M-보리'),
    revisitItemJson(
      petId: 102,
      name: '두부',
      lastVisitId: 502,
      cycleWeeks: 4,
      cycleSource: 'none',
      lastIntervalWeeks: null,
      estimated: true,
      lastVisitDate: '2026-10-12',
      dueDate: '2026-11-09',
    ),
  ];
  List<Map<String, dynamic>> soon = [
    revisitItemJson(petId: 103, name: '콩이', lastVisitId: 503, dueDate: '2026-11-20'),
  ];
  final nudges = <int>[];
  final settingsPuts = <Map<String, dynamic>>[];
}

Future<CustomerTestSetup> _open(
  WidgetTester tester,
  _Server server, {
  String role = 'owner',
  String path = '/revisits',
}) async {
  // 앱처럼 customer 의 쓰기가 방문 쪽을 다시 읽게 하는 자리를 꽂는다(`app.dart`).
  final setup = CustomerTestSetup(
    server.backend.call,
    role: role,
    overrides: [..._today, careMarksChangedPlugProvider.overrideWith(careMarksChanged)],
  );
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 1400);
  await pushOnHome<Object?>(tester, setup, path);
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
  testWidgets('지남이 먼저 열리고 세그먼트에 수, 줄에는 주기·지난 날 수·어림을 말한다', (tester) async {
    await _open(tester, _Server());

    expect(find.byKey(ScreenKeys.revisits), findsOneWidget);
    expect(find.text(AppStrings.revisitsDueTab(2)), findsOneWidget);
    expect(find.text(AppStrings.revisitsSoonTab(1)), findsOneWidget);
    expect(find.text('보리'), findsOneWidget);
    expect(find.text('6주마다 · 5일 지남'), findsOneWidget);
    expect(find.text('5주 전에 왔어요 · 어림'), findsOneWidget);
    expect(find.text('콩이'), findsNothing);

    await _tap(tester, find.text(AppStrings.revisitsSoonTab(1)));
    expect(find.text('콩이'), findsOneWidget);
    expect(find.text('6주마다 · 3일 뒤쯤'), findsOneWidget);
    expect(find.text(AppStrings.revisitSoonHeader(7)), findsOneWidget);
  });

  testWidgets('?bucket=soon 이면 곧으로 연다', (tester) async {
    await _open(tester, _Server(), path: '/revisits?bucket=soon');
    expect(find.text('콩이'), findsOneWidget);
  });

  testWidgets('[예약] — 마지막 방문의 초안을 내일 이후 같은 요일로 옮겨 예약 화면을 채워 연다', (tester) async {
    final setup = await _open(tester, _Server());

    await _tap(tester, _button(AppStrings.revisitBook).first);

    expect(setup.calls, contains('GET /v1/shops/3/visits/501/next-draft'));
    expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
    expect(find.text(AppStrings.saveReservation('11월 24일 화 14:00')), findsOneWidget);
  });

  testWidgets('[안내] — 서버가 만든 글이 써진 시트, [보내기]로 공유하고 안내한 날을 적는다', (tester) async {
    final server = _Server();
    final setup = await _open(tester, server);

    await _tap(tester, _button(AppStrings.revisitNudge).first);
    final field = find.byKey(const ValueKey('revisit-nudge-text'));
    expect(tester.widget<TextField>(field).controller!.text == 'M-보리', isTrue);
    await _tap(tester, _button(AppStrings.revisitNudgeSend));

    expect(setup.shareSheet.shared.length, 1);
    expect(setup.shareSheet.shared.single == 'M-보리', isTrue);
    expect(server.nudges, [101]);
    expect(find.text(AppStrings.revisitNudgedOn(DateTime(2026, 11, 17), DateTime(2026, 11, 17))), findsOneWidget);
  });

  testWidgets('이번만 고친 글로 보낸다 — 빈 글이면 [보내기]가 눌리지 않는다', (tester) async {
    final setup = await _open(tester, _Server());

    await _tap(tester, _button(AppStrings.revisitNudge).first);
    final field = find.byKey(const ValueKey('revisit-nudge-text'));
    await tester.enterText(field, '  ');
    await tester.pump();
    expect(tester.widget<AppButton>(_button(AppStrings.revisitNudgeSend)).onPressed, isNull);
    await tester.enterText(field, '고친 글');
    await tester.pump();
    await _tap(tester, _button(AppStrings.revisitNudgeSend));

    expect(setup.shareSheet.shared.single == '고친 글', isTrue);
  });

  testWidgets('공유 창을 열지 못하면 알리고 안내한 날을 적지 않는다', (tester) async {
    final server = _Server();
    final setup = await _open(tester, server);
    setup.shareSheet.error = Exception('채널');

    await _tap(tester, _button(AppStrings.revisitNudge).first);
    await _tap(tester, _button(AppStrings.revisitNudgeSend));

    expect(server.nudges, isEmpty);
    expect(find.text(AppStrings.revisitNudgeShareFailed), findsOneWidget);
  });

  testWidgets('사장은 곧의 날 수와 안내 글 템플릿을 그 자리에서 바꾼다 — 직원에게는 없다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, _button(AppStrings.revisitNudge).first);
    expect(find.text(AppStrings.revisitTemplateLink), findsOneWidget);
    await tester.tapAt(const Offset(10, 10));
    await settle(tester);

    await _tap(tester, find.text(AppStrings.revisitsSoonTab(1)));
    await _tap(tester, find.text(AppStrings.revisitChange));
    await _tap(tester, find.bySemanticsLabel(AppStrings.stepUp));
    await _tap(tester, _button(AppStrings.save));
    expect(server.settingsPuts, [
      {'revisit_soon_days': 8},
    ]);
  });

  testWidgets('직원에게는 바꾸는 줄이 없다', (tester) async {
    await _open(tester, _Server(), role: 'staff', path: '/revisits?bucket=soon');

    expect(find.text(AppStrings.revisitChange), findsNothing);
    await _tap(tester, _button(AppStrings.revisitNudge).first);
    expect(find.text(AppStrings.revisitTemplateLink), findsNothing);
  });

  testWidgets('줄의 주기 글을 누르면 그 아이의 주기 시트, 이름을 누르면 반려동물 상세', (tester) async {
    await _open(tester, _Server());

    await _tap(tester, find.text('6주마다 · 5일 지남'));
    expect(find.byType(GroomingCycleRow), findsNothing);
    expect(find.text(AppStrings.cycleLabel), findsWidgets);
    await tester.tapAt(const Offset(10, 10));
    await settle(tester);

    await _tap(tester, find.text('보리'));
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('[더 보기]로 이어 읽은 둘째 쪽의 아이에게 안내해도 목록이 첫 쪽으로 줄지 않는다', (tester) async {
    final server = _Server();
    // 첫 쪽은 보리 하나와 다음 쪽 표시, 둘째 쪽은 두부.
    var dubuNudged = false;
    server.backend.routes['GET /v1/shops/3/revisits'] = (o, b) {
      if (o.queryParameters['bucket'] == 'soon') return FakeResponse(statusCode: 200, data: revisitPageJson());
      final second = o.queryParameters['cursor'] == 'c1';
      return FakeResponse(
        statusCode: 200,
        data: second
            ? revisitPageJson(items: [
                revisitItemJson(petId: 102, name: '두부', lastVisitId: 502, nudgedOn: dubuNudged ? '2026-11-17' : null),
              ])
            : revisitPageJson(items: [revisitItemJson(petId: 101, name: '보리', lastVisitId: 501)], nextCursor: 'c1'),
      );
    };
    server.backend.routes['PUT /v1/shops/3/pets/102/revisit-nudge'] = (o, b) {
      dubuNudged = true;
      return const FakeResponse(statusCode: 204);
    };
    await _open(tester, server);
    await _tap(tester, _button(AppStrings.loadMore));
    expect(find.text('두부'), findsOneWidget);

    await _tap(tester, _button(AppStrings.revisitNudge).last);
    await _tap(tester, _button(AppStrings.revisitNudgeSend));

    expect(find.text('보리'), findsOneWidget);
    expect(find.text('두부'), findsOneWidget);
    expect(find.text(AppStrings.revisitNudgedOn(DateTime(2026, 11, 17), DateTime(2026, 11, 17))), findsOneWidget);
  });

  testWidgets('없으면 안내 한 줄', (tester) async {
    final server = _Server()..due = [];
    await _open(tester, server);
    expect(find.text(AppStrings.revisitsDueEmpty), findsOneWidget);
  });
}
