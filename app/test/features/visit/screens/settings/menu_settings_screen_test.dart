import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../../support/customer_test_app.dart';
import '../../../../support/fake_http_client_adapter.dart';
import '../../../../support/visit_fixtures.dart';
import '../../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 23))];

/// 기본 메뉴 다섯을 들고, 추가·수정·보관을 받아 목록에 반영하는 서버.
class _Server {
  _Server() {
    backend = VisitTestBackend({
      'GET /v1/shops/3/menus': (o, b) =>
          FakeResponse(statusCode: 200, data: {'items': menus}),
      'POST /v1/shops/3/menus': (o, body) {
        final sent = bodyOf(body);
        writes.add('POST ${sent['name']} ${sent['price']}');
        if (menus.any((m) => m['name'] == sent['name'])) {
          return const FakeResponse(
            statusCode: 409,
            data: {'code': 'MENU_NAME_TAKEN', 'message': 'x'},
          );
        }
        final created = menuJson(
          menuId: 9,
          name: sent['name'] as String,
          defaultDurationMinutes: sent['default_duration_minutes'] as int?,
          sortOrder: 6,
          price: sent['price'] as int?,
        );
        menus.add(created);
        return FakeResponse(statusCode: 201, data: created);
      },
    });
    for (final m in defaultMenusJson()) {
      backend.routes['PUT /v1/shops/3/menus/${m['menu_id']}'] = (o, body) {
        final sent = bodyOf(body);
        writes.add('PUT ${m['menu_id']} ${sent['sort_order']}');
        final i = menus.indexWhere((x) => x['menu_id'] == m['menu_id']);
        menus[i] = menuJson(
          menuId: m['menu_id'] as int,
          name: sent['name'] as String,
          defaultDurationMinutes: sent['default_duration_minutes'] as int?,
          sortOrder: sent['sort_order'] as int,
          price: sent['price'] as int?,
        );
        prices[m['menu_id'] as int] = sent['price'] as int?;
        return FakeResponse(statusCode: 200, data: menus[i]);
      };
      backend.routes['POST /v1/shops/3/menus/${m['menu_id']}/archive'] =
          (o, b) {
            writes.add('ARCHIVE ${m['menu_id']}');
            menus.removeWhere((x) => x['menu_id'] == m['menu_id']);
            return FakeResponse(
              statusCode: 200,
              data: menuJson(menuId: m['menu_id'] as int, archived: true),
            );
          };
    }
  }

  final menus = defaultMenusJson();
  final writes = <String>[];

  /// 메뉴마다 마지막 PUT 이 보낸 정가.
  final prices = <int, int?>{};
  late final VisitTestBackend backend;
}

Future<CustomerTestSetup> _open(WidgetTester tester, _Server server) async {
  final setup = CustomerTestSetup(server.backend.call, overrides: _today);
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 1200);
  await pushOnHome<Object?>(tester, setup, '/settings/menus');
  return setup;
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.tap(finder);
  await settle(tester);
}

List<String> _names(WidgetTester tester) => [
  for (final t in tester.widgetList<Text>(find.byType(Text)))
    if (t.data != null &&
        ['목욕', '위생', '부분 미용', '전체 미용', '스포팅', '발톱'].contains(t.data))
      t.data!,
];

void main() {
  testWidgets('메뉴를 순서대로 이름·기본 소요와 함께 보인다', (tester) async {
    await _open(tester, _Server());

    expect(find.byKey(ScreenKeys.settingsMenus), findsOneWidget);
    expect(_names(tester), ['목욕', '위생', '부분 미용', '전체 미용', '스포팅']);
    expect(
      find.text('${AppStrings.durationText(150)} · ${AppStrings.priceUnset}'),
      findsOneWidget,
    );
  });

  testWidgets('메뉴를 더하면 이름·기본 소요를 보내고 목록을 다시 불러온다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, _button(AppStrings.addMenu));
    await tester.enterText(find.byType(TextField).first, '발톱');
    // 매장 기본을 풀면 60분부터 고른다. 길게 누르면 30분씩.
    await _tap(tester, find.bySemanticsLabel(AppStrings.useShopDefault));
    await tester.longPress(find.bySemanticsLabel(AppStrings.shorter));
    await settle(tester);
    await _tap(tester, _button(AppStrings.save));

    expect(server.writes, ['POST 발톱 null']);
    expect(server.menus.last['default_duration_minutes'], 30);
    expect(_names(tester).last, '발톱');
  });

  testWidgets('이름이 비면 보내지 않고, 같은 이름이면(MENU_NAME_TAKEN) 문구를 보인다', (
    tester,
  ) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, _button(AppStrings.addMenu));
    await _tap(tester, _button(AppStrings.save));
    expect(find.text(AppStrings.menuNameRequired), findsOneWidget);
    expect(server.writes, isEmpty);

    await tester.enterText(find.byType(TextField).first, '목욕');
    await _tap(tester, _button(AppStrings.save));
    expect(find.textContaining('같은 이름의 메뉴'), findsOneWidget);
  });

  testWidgets('수정은 이름·기본 소요를 바꾸고 순서는 그대로 보낸다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.edit} 목욕'));
    expect(find.text(AppStrings.editMenu), findsOneWidget);
    await tester.enterText(find.byType(TextField).first, '목욕+');
    await tester.longPress(find.bySemanticsLabel(AppStrings.longer));
    await settle(tester);
    await _tap(tester, _button(AppStrings.save));

    expect(server.writes, ['PUT 1 1']);
    expect(server.menus.first['name'], '목욕+');
    expect(server.menus.first['default_duration_minutes'], 90);
  });

  testWidgets('아래로 내리면 이웃과 순서값을 맞바꾼다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.moveDown} 목욕'));

    expect(server.writes, ['PUT 1 2', 'PUT 2 1']);
    expect(_names(tester).take(2), ['위생', '목욕']);
  });

  testWidgets('맨 위는 올릴 수 없고 맨 아래는 내릴 수 없다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.moveUp} 목욕'));
    await _tap(tester, find.bySemanticsLabel('${AppStrings.moveDown} 스포팅'));

    expect(server.writes, isEmpty);
  });

  testWidgets('둘째 PUT이 실패해 순서값이 같아져도 다시 누르면 순서가 바뀐다', (tester) async {
    final server = _Server();
    var failNext = true;
    server.backend.routes['PUT /v1/shops/3/menus/2'] = (o, body) {
      final sent = bodyOf(body);
      server.writes.add('PUT 2 ${sent['sort_order']}');
      if (failNext) {
        failNext = false;
        return const FakeResponse(
          statusCode: 500,
          data: {'code': 'HTTP_ERROR', 'message': 'x'},
        );
      }
      final i = server.menus.indexWhere((x) => x['menu_id'] == 2);
      server.menus[i] = menuJson(
        menuId: 2,
        name: sent['name'] as String,
        defaultDurationMinutes: sent['default_duration_minutes'] as int?,
        sortOrder: sent['sort_order'] as int,
      );
      return FakeResponse(statusCode: 200, data: server.menus[i]);
    };
    await _open(tester, server);

    // 첫 시도: 둘째 PUT(위생)이 실패해 두 메뉴의 순서값이 둘 다 2로 같아진다.
    await _tap(tester, find.bySemanticsLabel('${AppStrings.moveDown} 목욕'));
    expect(server.writes, ['PUT 1 2', 'PUT 2 1']);
    expect(server.menus[0]['sort_order'], 2);
    expect(server.menus[1]['sort_order'], 2);
    expect(find.textContaining('문제가 생겼습니다'), findsOneWidget);
    expect(_names(tester), ['목욕', '위생', '부분 미용', '전체 미용', '스포팅']);

    // 같은 ▼를 다시 누르면 순서값이 같아도(v / v+1) 풀린다.
    await _tap(tester, find.bySemanticsLabel('${AppStrings.moveDown} 목욕'));
    expect(server.writes, ['PUT 1 2', 'PUT 2 1', 'PUT 1 3', 'PUT 2 2']);
    expect(_names(tester).take(2), ['위생', '목욕']);
  });

  testWidgets('보관은 확인을 거쳐 보내고 목록에서 빠진다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.archiveMenu} 스포팅'));
    expect(find.text(AppStrings.archiveMenuConfirm), findsOneWidget);
    await _tap(tester, _button(AppStrings.cancel));
    expect(server.writes, isEmpty);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.archiveMenu} 스포팅'));
    await _tap(tester, _button(AppStrings.archiveMenu));

    expect(server.writes, ['ARCHIVE 5']);
    expect(_names(tester), isNot(contains('스포팅')));
  });

  testWidgets('메뉴가 없으면 안내한다', (tester) async {
    final server = _Server()..menus.clear();
    await _open(tester, server);

    expect(find.text(AppStrings.menusEmpty), findsOneWidget);
  });

  testWidgets('정가를 적어 더하면 보내고, 목록에 소요와 정가를 보인다 — 비우면 가격 미정', (tester) async {
    final server = _Server();
    await _open(tester, server);
    expect(
      find.text('${AppStrings.durationText(60)} · ${AppStrings.priceUnset}'),
      findsNWidgets(2),
    );

    await _tap(tester, _button(AppStrings.addMenu));
    await tester.enterText(find.byType(TextField).first, '발톱');
    await tester.enterText(find.byType(TextField).last, '35000');
    await _tap(tester, _button(AppStrings.save));

    expect(server.writes, ['POST 발톱 35000']);
    expect(find.text('${AppStrings.useShopDefault} · 35,000원'), findsOneWidget);
  });

  testWidgets('정가만 고쳐도 보내고, 순서를 바꿀 때도 정가를 그대로 보낸다 — 빼면 가격 미정이 된다', (
    tester,
  ) async {
    final server = _Server();
    server.menus[0] = menuJson(
      menuId: 1,
      name: '목욕',
      sortOrder: 1,
      price: 30000,
    );
    await _open(tester, server);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.edit} 목욕'));
    expect(find.text('30000'), findsOneWidget);
    await tester.enterText(find.byType(TextField).last, '32000');
    await _tap(tester, _button(AppStrings.save));
    expect(server.prices[1], 32000);

    await _tap(tester, find.bySemanticsLabel('${AppStrings.moveDown} 목욕'));
    expect(server.prices, {1: 32000, 2: null});
    expect(
      find.text('${AppStrings.durationText(60)} · 32,000원'),
      findsOneWidget,
    );
  });

  testWidgets('정가가 1억 원을 넘으면 보내지 않는다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, _button(AppStrings.addMenu));
    await tester.enterText(find.byType(TextField).first, '발톱');
    await tester.enterText(find.byType(TextField).last, '100000001');
    await _tap(tester, _button(AppStrings.save));

    expect(find.text(AppStrings.amountTooLarge), findsOneWidget);
    expect(server.writes, isEmpty);
  });

  test('금액은 세 자리마다 쉼표를 찍는다', () {
    expect(AppStrings.wonText(0), '0원');
    expect(AppStrings.wonText(999), '999원');
    expect(AppStrings.wonText(1000), '1,000원');
    expect(AppStrings.wonText(100000000), '100,000,000원');
  });
}
