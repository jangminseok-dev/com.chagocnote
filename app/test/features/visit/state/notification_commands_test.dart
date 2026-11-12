// 알림톡 쓰기와 기다리기 — 설정·온보딩 쓰기는 한눈에 보기를 다시 읽게 하고, 알림장 발송 결과와 재발송은
// 1초 간격으로 본다. 기다림은 `notificationPollWaitProvider`를 바꿔 끼워 곧바로 흘린다.
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/visit/api/notification_models.dart';
import 'package:chagocnote/features/visit/state/notification_commands.dart';
import 'package:chagocnote/features/visit/state/notification_providers.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

const _shop = customerTestShopId;
const _visitKey = (shopId: _shop, visitId: 101);
const _overviewPath = '/v1/shops/3/notification';
const _listPath = '/v1/shops/3/visits/101/notifications';
const _resendPath = '/v1/shops/3/visits/101/notifications/confirm/resend';

FakeResponse _ok(Object? data, {int status = 200}) =>
    FakeResponse(statusCode: status, data: data);

FakeResponse _error(int status, String code) =>
    FakeResponse(statusCode: status, data: {'code': code, 'message': 'x'});

Map<String, dynamic> _items(List<Map<String, dynamic>> items) => {
  'items': items,
};

Map<String, dynamic> _report(int id, String status, {String? shareText}) =>
    notificationMessageJson(
      messageId: id,
      kind: 'report',
      status: status,
      errorKind: status == 'failed' ? 'permanent' : null,
      shareText: shareText,
    );

/// 기다림을 세기만 하고 곧바로 흘리는 가짜 서버 묶음. [lists]는 내역 GET 이 차례로 줄 답이다(마지막 답은
/// 남아서 되풀이된다).
class _World {
  _World({
    List<Object> lists = const [],
    Map<String, FakeHandler> routes = const {},
  }) : _lists = [...lists] {
    setup = CustomerTestSetup(
      VisitTestBackend({
        'GET /v1/shops/3/visits/101': (o, b) => _ok(visitDetailJson()),
        'GET $_overviewPath': (o, b) => _ok(notificationOverviewJson()),
        'GET $_listPath': (o, b) {
          final next = _lists.length > 1 ? _lists.removeAt(0) : _lists.first;
          return next is FakeResponse ? next : _ok(next);
        },
        ...routes,
      }).call,
      overrides: [
        notificationPollWaitProvider.overrideWithValue(() async => waits++),
      ],
    );
    addTearDown(setup.container.dispose);
  }

  final List<Object> _lists;
  late final CustomerTestSetup setup;
  var waits = 0;

  NotificationCommands get commands =>
      setup.container.read(notificationCommandsProvider);

  int count(String call) => setup.calls.where((c) => c == call).length;
}

void main() {
  group('알림장 발송 결과 기다리기', () {
    test('이번 보내기가 만든 줄이 없으면 한 번 읽고 ReportNotSent 다', () async {
      final world = _World(lists: [_items([])]);

      final result = await world.commands.awaitReport(_shop, 101, before: {});

      expect(result, isA<ReportNotSent>());
      expect(world.count('GET $_listPath'), 1);
      expect(world.waits, 0);
    });

    test('새 줄이 sent 나 fallback_sent 면 ReportDelivered 다', () async {
      for (final status in ['sent', 'fallback_sent']) {
        final world = _World(
          lists: [
            _items([_report(5, status)]),
          ],
        );
        expect(
          await world.commands.awaitReport(_shop, 101, before: {}),
          isA<ReportDelivered>(),
        );
      }
    });

    test('접수 두 번 뒤 실패하면 ReportFailed 이고 문안을 싣는다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'accepted')]),
          _items([_report(5, 'accepted')]),
          _items([_report(5, 'failed', shareText: '문안')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: {});

      expect(result, isA<ReportFailed>());
      expect((result as ReportFailed).shareText, '문안');
      expect(world.count('GET $_listPath'), 3);
      expect(world.waits, 2);
    });

    test('줄곧 접수 중이면 열 번 읽고 ReportPending 이다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'accepted')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: {});

      expect(result, isA<ReportPending>());
      expect(world.count('GET $_listPath'), 10);
      expect(world.waits, 9);
    });

    test('보내기 전 내역을 읽지 못했으면(before 가 null) 읽지 않고 ReportNotSent 다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'sent')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: null);

      expect(result, isA<ReportNotSent>());
      expect(world.count('GET $_listPath'), 0);
    });

    test('보내기 전부터 있던 sent 줄만 있으면 새 발송으로 치지 않는다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'sent')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: {5});

      expect(result, isA<ReportNotSent>());
    });

    test('새 줄이 있으면 옛 줄이 아니라 새 줄을 본다', () async {
      final world = _World(
        lists: [
          _items([_report(6, 'failed', shareText: '새'), _report(5, 'sent')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: {5});

      expect(result, isA<ReportFailed>());
    });

    test('새 줄이 취소됐으면 ReportNotSent 다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'canceled')]),
        ],
      );

      expect(
        await world.commands.awaitReport(_shop, 101, before: {}),
        isA<ReportNotSent>(),
      );
    });

    test('다른 종류의 줄은 보지 않는다', () async {
      final world = _World(
        lists: [
          _items([notificationMessageJson(messageId: 7, kind: 'confirm')]),
        ],
      );

      expect(
        await world.commands.awaitReport(_shop, 101, before: {}),
        isA<ReportNotSent>(),
      );
    });

    test('읽기 한 번이 실패하면 건너뛰고 다음에 다시 읽는다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'accepted')]),
          _error(500, 'INTERNAL'),
          _items([_report(5, 'sent')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: {});

      expect(result, isA<ReportDelivered>());
      expect(world.count('GET $_listPath'), 3);
    });

    test('보내기 전 내역의 모양이 어긋나도 예외를 올리지 않고 null 이다', () async {
      final world = _World(
        lists: [
          {'items': 'x'},
        ],
      );

      expect(await world.commands.reportRowIds(_shop, 101), isNull);
    });

    test('기다리는 중 내역의 모양이 어긋나도 건너뛰고 다음에 다시 읽는다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'accepted')]),
          {'items': 'x'},
          _items([_report(5, 'sent')]),
        ],
      );

      final result = await world.commands.awaitReport(_shop, 101, before: {});

      expect(result, isA<ReportDelivered>());
      expect(world.count('GET $_listPath'), 3);
    });

    test('끝나면 방문의 내역을 다시 읽게 한다', () async {
      final world = _World(
        lists: [
          _items([_report(5, 'sent')]),
        ],
      );
      final c = world.setup.container;
      c.listen(visitNotificationsProvider(_visitKey), (_, _) {});
      await c.read(visitNotificationsProvider(_visitKey).future);
      world.setup.adapter.requests.clear();

      await world.commands.awaitReport(_shop, 101, before: {});
      await c.read(visitNotificationsProvider(_visitKey).future);

      expect(world.count('GET $_listPath'), 2); // 기다리며 한 번, 무효화로 한 번
    });

    test('보내기 전 줄 ID 는 report 줄만 모으고 읽지 못하면 null 이다', () async {
      final world = _World(
        lists: [
          _items([
            _report(5, 'sent'),
            notificationMessageJson(messageId: 7, kind: 'confirm'),
            _report(3, 'canceled'),
          ]),
          _error(500, 'INTERNAL'),
        ],
      );

      expect(await world.commands.reportRowIds(_shop, 101), {5, 3});
      expect(await world.commands.reportRowIds(_shop, 101), isNull);
    });
  });

  group('다시 보내기', () {
    _World resendWorld(List<Object> states, {FakeHandler? post}) {
      final answers = [...states];
      return _World(
        lists: [_items([])],
        routes: {
          'POST $_resendPath':
              post ?? (o, b) => _ok({'message_id': 9}, status: 201),
          'GET /v1/shops/3/notifications/9': (o, b) {
            final next = answers.length > 1
                ? answers.removeAt(0)
                : answers.first;
            return next is FakeResponse ? next : _ok(next);
          },
        },
      );
    }

    test('재발송하고 끝난 상태가 될 때까지만 본다', () async {
      final world = resendWorld([
        notificationMessageJson(messageId: 9, status: 'sending'),
        notificationMessageJson(messageId: 9, status: 'sent'),
      ]);

      await world.commands.resend(_shop, 101, NotificationKind.confirm);

      expect(world.count('POST $_resendPath'), 1);
      expect(world.count('GET /v1/shops/3/notifications/9'), 2);
      expect(world.waits, 2);
    });

    test('다섯 번 봐도 접수 중이면 멈춘다', () async {
      final world = resendWorld([
        notificationMessageJson(messageId: 9, status: 'accepted'),
      ]);

      await world.commands.resend(_shop, 101, NotificationKind.confirm);

      expect(world.count('GET /v1/shops/3/notifications/9'), 5);
    });

    test('상태 읽기가 실패해도 재발송은 성공으로 끝난다', () async {
      final world = resendWorld([_error(500, 'INTERNAL')]);

      await world.commands.resend(_shop, 101, NotificationKind.confirm);

      expect(world.count('GET /v1/shops/3/notifications/9'), 5);
    });

    test('재발송 직후와 끝난 뒤 내역을 다시 읽게 한다', () async {
      final world = resendWorld([
        notificationMessageJson(messageId: 9, status: 'sent'),
      ]);
      final c = world.setup.container;
      c.listen(visitNotificationsProvider(_visitKey), (_, _) {});
      await c.read(visitNotificationsProvider(_visitKey).future);
      world.setup.adapter.requests.clear();

      await world.commands.resend(_shop, 101, NotificationKind.confirm);
      await c.read(visitNotificationsProvider(_visitKey).future);

      expect(world.count('GET $_listPath'), greaterThanOrEqualTo(1));
    });

    test('404 면 예외가 올라오고 내역을 다시 읽게 한다', () async {
      final world = resendWorld([
        notificationMessageJson(messageId: 9),
      ], post: (o, b) => _error(404, 'NOTIFICATION_MESSAGE_NOT_FOUND'));
      final c = world.setup.container;
      c.listen(visitNotificationsProvider(_visitKey), (_, _) {});
      await c.read(visitNotificationsProvider(_visitKey).future);
      world.setup.adapter.requests.clear();

      await expectLater(
        world.commands.resend(_shop, 101, NotificationKind.confirm),
        throwsA(
          isA<ApiException>().having(
            (e) => e.code,
            'code',
            'NOTIFICATION_MESSAGE_NOT_FOUND',
          ),
        ),
      );
      await c.read(visitNotificationsProvider(_visitKey).future);

      expect(world.count('GET $_listPath'), 1);
      expect(world.count('GET /v1/shops/3/notifications/9'), 0);
    });
  });

  group('설정·온보딩 쓰기', () {
    const inputs = (
      searchId: '@hisshaus',
      adminPhone: '01012345678',
      categoryCode: '001',
    );

    final writes =
        <String, (String, Future<void> Function(NotificationCommands))>{
          '인증번호 받기': (
            'POST $_overviewPath/channel/token',
            (c) => c.requestChannelToken(
              _shop,
              searchId: inputs.searchId,
              adminPhone: inputs.adminPhone,
              categoryCode: inputs.categoryCode,
            ),
          ),
          '연동': (
            'POST $_overviewPath/channel',
            (c) => c.linkChannel(
              _shop,
              searchId: inputs.searchId,
              adminPhone: inputs.adminPhone,
              categoryCode: inputs.categoryCode,
              token: '000000',
            ),
          ),
          '연동 해제': (
            'DELETE $_overviewPath/channel',
            (c) => c.unlinkChannel(_shop),
          ),
          '설정': (
            'PUT $_overviewPath/settings',
            (c) => c.updateSettings(_shop, {'reminder_time': '09:30'}),
          ),
          '발신번호 인증번호 받기': (
            'POST $_overviewPath/sender/verification',
            (c) => c.requestSenderVerification(_shop, '0212345678'),
          ),
          '발신번호 인증': (
            'POST $_overviewPath/sender',
            (c) => c.confirmSender(_shop, phone: '0212345678', code: '000000'),
          ),
        };

    for (final MapEntry(key: name, value: (route, call)) in writes.entries) {
      test('$name 은 성공하면 한눈에 보기를 다시 읽게 한다', () async {
        final world = _World(
          lists: [_items([])],
          routes: {route: (o, b) => _ok(notificationOverviewJson())},
        );
        final c = world.setup.container;
        c.listen(notificationOverviewProvider(_shop), (_, _) {});
        await c.read(notificationOverviewProvider(_shop).future);
        world.setup.adapter.requests.clear();

        await call(world.commands);
        await c.read(notificationOverviewProvider(_shop).future);

        expect(world.setup.calls, [route, 'GET $_overviewPath']);
      });

      test('$name 은 실패해도 한눈에 보기를 다시 읽게 하고 예외를 올린다', () async {
        final world = _World(
          lists: [_items([])],
          routes: {
            route: (o, b) => _error(409, 'NOTIFICATION_CHANNEL_NOT_LINKED'),
          },
        );
        final c = world.setup.container;
        c.listen(notificationOverviewProvider(_shop), (_, _) {});
        await c.read(notificationOverviewProvider(_shop).future);
        world.setup.adapter.requests.clear();

        await expectLater(call(world.commands), throwsA(isA<ApiException>()));
        await c.read(notificationOverviewProvider(_shop).future);

        expect(world.setup.calls, [route, 'GET $_overviewPath']);
      });
    }
  });

  test('방문 상세를 다시 읽으면 내역도 따라 다시 읽는다', () async {
    final world = _World(lists: [_items([])]);
    final c = world.setup.container;
    c.listen(visitNotificationsProvider(_visitKey), (_, _) {});
    await c.read(visitNotificationsProvider(_visitKey).future);
    expect(world.count('GET $_listPath'), 1);

    c.invalidate(visitDetailProvider(_visitKey));
    await c.read(visitNotificationsProvider(_visitKey).future);

    expect(world.count('GET /v1/shops/3/visits/101'), 2);
    expect(world.count('GET $_listPath'), 2);
  });
}
