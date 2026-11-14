import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:chagocnote/core/router/app_router.dart';
import 'package:dio/dio.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import 'customer_fixtures.dart';
import 'customer_test_app.dart';
import 'fake_http_client_adapter.dart';
import 'visit_fixtures.dart';

/// 예약 화면 테스트의 가짜 서버. 기본 응답을 두고, 테스트가 `METHOD path`
/// 단위로 바꿔 끼운다. 모르는 요청은 실패시킨다.
final _notificationsPath = RegExp(r'^/v1/shops/3/visits/\d+/notifications$');

class VisitTestBackend {
  VisitTestBackend([Map<String, FakeHandler> overrides = const {}]) {
    routes.addAll(overrides);
  }

  final Map<String, FakeHandler> routes = {
    'GET /v1/shops/3/visit-settings': (o, b) =>
        FakeResponse(statusCode: 200, data: settingsJson()),
    'GET /v1/shops/3/menus': (o, b) =>
        FakeResponse(statusCode: 200, data: {'items': defaultMenusJson()}),
    'GET /v1/shops/3/customers': (o, b) =>
        FakeResponse(statusCode: 200, data: pageJson(items: [_family()])),
    'GET /v1/shops/3/customers/7': (o, b) => FakeResponse(
      statusCode: 200,
      data: customerDetailJson(
        customer: customerJson(name: '이수진'),
        pets: [petJson(petId: 11, name: '두부')],
      ),
    ),
    'GET /v1/shops/3/visits/calendar': (o, b) {
      final month = (o.queryParameters['month'] as String).split('-');
      return FakeResponse(
        statusCode: 200,
        data: calendarJson(
          year: int.parse(month[0]),
          month: int.parse(month[1]),
        ),
      );
    },
    'GET /v1/shops/3/visits/slots': (o, b) {
      final date = o.queryParameters['date'] as String;
      final at = o.queryParameters['at'] as String?;
      final duration = o.queryParameters['duration'] as int;
      return FakeResponse(
        statusCode: 200,
        data: at == null
            ? slotsJson(date: date, durationMinutes: duration)
            : slotAtJson(date: date, at: at, durationMinutes: duration),
      );
    },
    'GET /v1/shops/3/visits': (o, b) => FakeResponse(
      statusCode: 200,
      data: dayJson(date: o.queryParameters['date'] as String),
    ),
    'GET /v1/shops/3/visits/defaults': (o, b) =>
        FakeResponse(statusCode: 200, data: defaultsJson()),
    'POST /v1/shops/3/visits': (o, b) =>
        FakeResponse(statusCode: 201, data: savedJson([visitJson()])),
    'POST /v1/shops/3/visit-drafts': (o, b) =>
        FakeResponse(statusCode: 200, data: visitDraftJson()),
    // 예약 등록은 확인할 것을 묻는다(③-B) — 따로 정하지 않은 테스트에는 아무것도 없다.
    'GET /v1/shops/3/visit-checks': (o, b) =>
        FakeResponse(statusCode: 200, data: checksPreviewJson()),
  };

  static Map<String, dynamic> _family() => familyJson(
    customerId: 7,
    name: '이수진',
    pets: [petSummaryJson(petId: 11, name: '두부')],
  );

  FutureOr<FakeResponse> call(RequestOptions options, Uint8List? body) {
    final handler = routes['${options.method} ${options.path}'];
    // 방문 상세는 알림톡 내역을 함께 읽는다 — 따로 정하지 않은 테스트에는 빈 내역(연동 안 된 매장)이다.
    if (handler == null &&
        options.method == 'GET' &&
        _notificationsPath.hasMatch(options.path)) {
      return FakeResponse(statusCode: 200, data: {'items': <Object>[]});
    }
    if (handler == null) {
      fail('예상하지 못한 요청: ${options.method} ${options.path}');
    }
    return handler(options, body);
  }
}

Map<String, dynamic> bodyOf(Uint8List? body) =>
    jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

/// 요청이 가짜 시간 0 에 걸려 있으면 `pumpAndSettle`만으로는 끝나지 않는다
/// (그릴 프레임이 없으면 시간이 흐르지 않는다) — 1ms 를 흘린 뒤 기다린다.
Future<void> settle(WidgetTester tester) async {
  await tester.pump(const Duration(milliseconds: 1));
  await tester.pumpAndSettle();
}

/// 폼·목록 전체가 한 화면에 그려지게 세로로 긴 화면을 쓴다(목록이 게으르게 그린다).
void useTallView(WidgetTester tester, {double height = 2000}) {
  tester.view.physicalSize = Size(390, height);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

/// 쌓아 연 화면이 닫힐 때 돌려받은 값. 닫히지 않았으면 [closed]가 false 다 —
/// 테스트가 닫힘을 `await`로 기다리면 닫히지 않을 때 멈춰 버린다.
class Closed<T> {
  bool closed = false;
  T? value;
}

/// 홈을 띄우고 [path]를 쌓아 연다.
Future<Closed<T>> pushOnHome<T>(
  WidgetTester tester,
  CustomerTestSetup setup,
  String path, {
  Object? extra,
}) async {
  await tester.pumpWidget(customerRouterApp(setup.container));
  await tester.pumpAndSettle();
  final closed = Closed<T>();
  setup.container
      .read(routerProvider)
      .push<T>(path, extra: extra)
      .then(
        (value) => closed
          ..closed = true
          ..value = value,
      );
  await settle(tester);
  return closed;
}
