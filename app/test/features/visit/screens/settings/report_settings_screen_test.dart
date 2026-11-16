import 'dart:async';

import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/features/visit/state/report_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../../support/customer_test_app.dart';
import '../../../../support/fake_http_client_adapter.dart';
import '../../../../support/visit_fixtures.dart';
import '../../../../support/visit_test_backend.dart';

const _path = '/v1/shops/3/report-settings';

/// 알림장 설정 서버. GET 은 지금의 [settings]로 답한다. PUT 은 받은 본문을 [puts]에 적고 그대로 저장해
/// 돌려준다 — [putError]가 있으면 저장하지 않고 그것으로 답한다. [getGate]·[putGate]가 있으면 그것이
/// 끝날 때까지 답을 붙든다.
class _Server {
  Map<String, dynamic> settings = reportSettingsJson();
  FakeResponse? getError;
  FakeHandler? putError;
  Completer<void>? getGate;
  Completer<void>? putGate;
  final puts = <Map<String, dynamic>>[];

  late final backend = VisitTestBackend({
    'GET $_path': (o, b) async {
      await getGate?.future;
      return getError ?? FakeResponse(statusCode: 200, data: settings);
    },
    'PUT $_path': (o, body) async {
      final sent = bodyOf(body);
      puts.add(sent);
      await putGate?.future;
      if (putError case final error?) return error(o, body);
      settings = sent;
      return FakeResponse(statusCode: 200, data: settings);
    },
  });
}

Future<CustomerTestSetup> _open(
  WidgetTester tester,
  _Server server, {
  String role = 'owner',
}) async {
  final setup = CustomerTestSetup(server.backend.call, role: role);
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 844);
  await pushOnHome<Object?>(tester, setup, '/settings/report');
  return setup;
}

Finder _chip(String label) =>
    find.byWidgetPredicate((w) => w is AppChoiceChip && w.label == label);

Finder _switch(String label) =>
    find.byWidgetPredicate((w) => w is AppSwitch && w.semanticLabel == label);

/// 고른 기간 칩의 글자.
String _period(WidgetTester tester) => tester
    .widgetList<AppChoiceChip>(find.byType(AppChoiceChip))
    .where((chip) => chip.selected)
    .single
    .label;

/// 켜진 스위치의 이름들(화면 순서대로).
List<String> _on(WidgetTester tester) => [
  for (final s in tester.widgetList<AppSwitch>(find.byType(AppSwitch)))
    if (s.value) s.semanticLabel!,
];

int _reads(CustomerTestSetup setup) =>
    setup.calls.where((call) => call == 'GET $_path').length;

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await settle(tester);
}

/// 보낸 본문 — 받은 설정에서 읽기 전용인 기본 문구를 뺀 일곱 칸(⑫).
Map<String, dynamic> _sent(Map<String, dynamic> json) =>
    {...json}..remove('review_text_default');

void main() {
  testWidgets('서버의 설정대로 기간과 스위치 넷을 보인다', (tester) async {
    final server = _Server();
    final setup = await _open(tester, server);

    expect(find.byKey(ScreenKeys.reportSettings), findsOneWidget);
    expect(find.text('알림장 설정'), findsOneWidget);
    expect(find.text('7일'), findsOneWidget);
    expect(_period(tester), '30일');
    expect(
      tester
          .widgetList<AppSwitch>(find.byType(AppSwitch))
          .map((s) => s.semanticLabel),
      ['메뉴 이름', '금액', '몸무게', '매장 정보'],
    );
    expect(_on(tester), ['메뉴 이름', '매장 정보']);
    // 이름은 스위치만 읽는다 — 줄의 글자를 한 번 더 읽지 않는다.
    expect(find.bySemanticsLabel(RegExp('몸무게')), findsOneWidget);
    expect(find.text('사장만 바꿀 수 있어요.'), findsNothing);

    // 다른 값으로 다시 읽으면 그대로 따라 그린다 — 칸이 서로 바뀌어 읽히지 않는다.
    server.settings = reportSettingsJson(
      linkDays: null,
      showMenus: false,
      showWeight: true,
    );
    setup.container.invalidate(reportSettingsProvider);
    await settle(tester);

    expect(_period(tester), '계속');
    expect(_on(tester), ['몸무게', '매장 정보']);
  });

  testWidgets('7일을 누르면 다섯 칸을 모두 보내고(link_days: 7) 응답대로 다시 그린다', (tester) async {
    final server = _Server();
    final setup = await _open(tester, server);

    await _tap(tester, _chip('7일'));

    expect(server.puts, [_sent(reportSettingsJson(linkDays: 7))]);
    expect(_reads(setup), 2);
    expect(_period(tester), '7일');
    expect(_on(tester), ['메뉴 이름', '매장 정보']);

    // 이미 고른 기간은 다시 보내지 않는다.
    await _tap(tester, _chip('7일'));
    expect(server.puts, hasLength(1));
  });

  testWidgets('계속을 누르면 link_days: null 을 보낸다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, _chip('계속'));

    // 본문에 키가 있고 값이 null 이다 — 서버는 다섯 칸 모두를 요구한다.
    expect(server.puts.single.containsKey('link_days'), isTrue);
    expect(server.puts, [_sent(reportSettingsJson(linkDays: null))]);
    expect(_period(tester), '계속');
  });

  testWidgets('금액 스위치를 켜면 show_amount 만 바뀐 전체를 보낸다 — 나머지 스위치도 제 칸만 뒤집는다', (
    tester,
  ) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, _switch('금액'));

    expect(server.puts, [_sent(reportSettingsJson(showAmount: true))]);
    expect(_on(tester), ['메뉴 이름', '금액', '매장 정보']);

    // 다음 누름은 다시 읽은 서버 값(금액 켬) 위에서 제 칸만 뒤집는다.
    for (final (label, field) in [
      ('메뉴 이름', 'show_menus'),
      ('몸무게', 'show_weight'),
      ('매장 정보', 'show_shop_info'),
      ('금액', 'show_amount'),
    ]) {
      final before = server.settings;
      await _tap(tester, _switch(label));
      expect(server.puts.last, {
        ..._sent(before),
        field: !(before[field] as bool),
      });
    }
    expect(_on(tester), ['몸무게']);
  });

  testWidgets('보내는 동안 다른 조작이 눌리지 않아 한 번만 보낸다', (tester) async {
    final server = _Server()..putGate = Completer();
    await _open(tester, server);

    // pump 없이 잇달아 누른다 — 화면이 다시 그려지기 전의 누름도 막는다.
    await tester.tap(_switch('금액'));
    await tester.tap(_switch('몸무게'));
    await tester.tap(_chip('7일'));
    await settle(tester);
    await _tap(tester, _switch('매장 정보'));

    expect(server.puts, [_sent(reportSettingsJson(showAmount: true))]);
    // 낙관적으로 그리지 않는다 — 응답이 오기 전에는 서버의 값 그대로다.
    expect(_on(tester), ['메뉴 이름', '매장 정보']);

    server.putGate!.complete();
    await settle(tester);
    expect(_on(tester), ['메뉴 이름', '금액', '매장 정보']);

    // 끝나면 다시 눌린다.
    await _tap(tester, _switch('몸무게'));
    expect(server.puts, hasLength(2));
  });

  testWidgets('바꾼 뒤 다시 읽는 동안에도 눌리지 않는다 — 낡은 값 위에 덮어 방금 바꾼 칸을 되돌리지 않는다', (
    tester,
  ) async {
    final server = _Server();
    final setup = await _open(tester, server);

    // PUT 은 끝났고 다시 읽기(GET)가 아직 오지 않았다 — 화면은 금액이 꺼진 옛 값을 보이고 있다.
    server.getGate = Completer();
    await _tap(tester, _switch('금액'));
    expect(_reads(setup), 2);
    expect(_on(tester), ['메뉴 이름', '매장 정보']);

    await _tap(tester, _switch('몸무게'));
    expect(server.puts, hasLength(1));

    server.getGate!.complete();
    server.getGate = null;
    await settle(tester);
    await _tap(tester, _switch('몸무게'));
    expect(
      server.puts.last,
      _sent(reportSettingsJson(showAmount: true, showWeight: true)),
    );

    // 다시 읽기가 실패해 "이전 내용"을 보이는 동안에도 눌리지 않는다 — [다시 시도]로 읽은 뒤에 눌린다.
    server.getError = const FakeResponse(statusCode: 503, data: 'x');
    await _tap(tester, _chip('7일'));
    expect(server.puts, hasLength(3));
    expect(_period(tester), '30일');
    await _tap(tester, _switch('메뉴 이름'));
    expect(server.puts, hasLength(3));

    server.getError = null;
    await _tap(tester, find.text(AppStrings.retry));
    expect(_period(tester), '7일');
    await _tap(tester, _switch('메뉴 이름'));
    expect(server.puts.last['show_menus'], isFalse);
    expect(server.puts.last['link_days'], 7);
  });

  testWidgets('서버가 거절하면 문구를 보이고 값은 그대로다', (tester) async {
    final server = _Server()
      ..putError = (o, b) => const FakeResponse(
        statusCode: 403,
        data: {'code': 'PERMISSION_DENIED', 'message': 'x'},
      );
    final setup = await _open(tester, server);

    await _tap(tester, _switch('금액'));

    expect(find.text('이 작업을 할 권한이 없어요.'), findsOneWidget);
    expect(_on(tester), ['메뉴 이름', '매장 정보']);
    // 거절됐다면 화면의 값이 낡았을 수 있다 — 실패해도 설정을 다시 읽는다.
    expect(_reads(setup), 2);

    // 연결 실패.
    server.putError = (o, b) =>
        throw DioException.connectionError(requestOptions: o, reason: '끊김');
    await _tap(tester, _chip('7일'));

    expect(find.text('이 작업을 할 권한이 없어요.'), findsNothing);
    expect(find.text(offlineActionMessage), findsOneWidget);
    expect(_period(tester), '30일');
    expect(server.puts, hasLength(2));

    // 다시 누르면 보내는 동안 문구가 사라지고, 성공하면 그대로 없다.
    server
      ..putError = null
      ..putGate = Completer();
    await _tap(tester, _chip('7일'));
    expect(find.text(offlineActionMessage), findsNothing);

    server.putGate!.complete();
    await settle(tester);
    expect(find.text(offlineActionMessage), findsNothing);
    expect(_period(tester), '7일');
  });

  testWidgets('직원은 읽기 전용이다 — 눌러도 보내지 않고 안내가 보인다', (tester) async {
    final server = _Server();
    await _open(tester, server, role: 'staff');

    expect(find.text('사장만 바꿀 수 있어요.'), findsOneWidget);
    // 값은 보인다.
    expect(_period(tester), '30일');
    expect(_on(tester), ['메뉴 이름', '매장 정보']);

    for (final label in ['메뉴 이름', '금액', '몸무게', '매장 정보']) {
      await _tap(tester, _switch(label));
    }
    for (final label in ['7일', '30일', '계속']) {
      await _tap(tester, _chip(label));
    }

    expect(server.puts, isEmpty);
    expect(
      tester
          .widgetList<AppSwitch>(find.byType(AppSwitch))
          .every((s) => s.onChanged == null),
      isTrue,
    );
  });

  testWidgets('설정을 불러오지 못하면 다시 시도한다', (tester) async {
    final server = _Server()
      ..getError = const FakeResponse(statusCode: 503, data: 'x');
    await _open(tester, server);
    expect(find.byType(AppSwitch), findsNothing);

    server.getError = null;
    await _tap(
      tester,
      find.byWidgetPredicate(
        (w) => w is AppButton && w.label == AppStrings.retry,
      ),
    );

    expect(_period(tester), '30일');
  });

  testWidgets('알림장 설정 골든', (tester) async {
    await _open(tester, _Server());

    await expectLater(
      find.byKey(ScreenKeys.reportSettings),
      matchesGoldenFile('goldens/report_settings.png'),
    );
  });
}
