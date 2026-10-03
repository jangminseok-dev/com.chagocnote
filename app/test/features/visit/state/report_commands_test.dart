import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/features/auth/state/session_controller.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:chagocnote/features/visit/api/report_models.dart';
import 'package:chagocnote/features/visit/state/feed_controller.dart';
import 'package:chagocnote/features/visit/state/report_commands.dart';
import 'package:chagocnote/features/visit/state/report_providers.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

const _shop = customerTestShopId;
const _reportPath = '/v1/shops/3/visits/101/report';
const _settingsPath = '/v1/shops/3/report-settings';

const _visitKey = (shopId: _shop, visitId: 101);
final _dayKey = (shopId: _shop, date: DateTime(2026, 10, 2));
final _monthKey = monthKeyOf(_shop, DateTime(2026, 10, 2));
const FeedQuery _feedQuery = (shopId: _shop, petId: null);
const FeedQuery _petFeedQuery = (shopId: _shop, petId: 11);
const _customerKey = (shopId: _shop, customerId: 7);

/// 서버의 지금 미리보기 — 1 은 보이고, 2 는 그 사이 다른 기기에서 뺐다.
Map<String, dynamic> _preview({bool live = false}) => visitReportJson(
  media: [
    reportMediaJson(mediaId: 1),
    reportMediaJson(mediaId: 2, hidden: true),
  ],
  link: reportLinkJson(live: live),
);

FakeResponse _error(int status, String code) =>
    FakeResponse(statusCode: status, data: {'code': code, 'message': 'x'});

/// 읽기는 모두 되는 가짜 서버. 쓰기(와 바꿔 끼울 읽기)는 테스트가 [routes]로 준다.
CustomerTestSetup _setup(Map<String, FakeHandler> routes) {
  final setup = CustomerTestSetup(
    VisitTestBackend({
      'GET /v1/shops/3/visits/101': (o, b) =>
          FakeResponse(statusCode: 200, data: visitDetailJson()),
      'GET /v1/shops/3/visits/feed': (o, b) =>
          FakeResponse(statusCode: 200, data: feedJson()),
      'GET $_reportPath': (o, b) =>
          FakeResponse(statusCode: 200, data: _preview()),
      'GET $_settingsPath': (o, b) =>
          FakeResponse(statusCode: 200, data: reportSettingsJson()),
      ...routes,
    }).call,
  );
  addTearDown(setup.container.dispose);
  return setup;
}

/// 알림장이 바꾸는 화면(방문 상세·하루 목록·피드·반려동물 상세의 [기록] 탭·미리보기·설정)과
/// 바꾸지 않는 화면(달력·고객 상세)을 모두 보고 있는 상태를 만든다.
Future<void> _watchEverything(CustomerTestSetup setup) async {
  final c = setup.container;
  c.listen(visitDetailProvider(_visitKey), (_, _) {});
  c.listen(dayVisitsProvider(_dayKey), (_, _) {});
  c.listen(feedControllerProvider(_feedQuery), (_, _) {});
  c.listen(feedControllerProvider(_petFeedQuery), (_, _) {});
  c.listen(visitReportProvider(_visitKey), (_, _) {});
  c.listen(reportSettingsProvider(_shop), (_, _) {});
  c.listen(calendarMonthProvider(_monthKey), (_, _) {});
  c.listen(customerDetailProvider(_customerKey), (_, _) {});
  await _settle(setup);
  setup.adapter.requests.clear();
}

Future<void> _settle(CustomerTestSetup setup) async {
  final c = setup.container;
  await c.read(visitDetailProvider(_visitKey).future);
  await c.read(dayVisitsProvider(_dayKey).future);
  await c.read(feedControllerProvider(_feedQuery).future);
  await c.read(feedControllerProvider(_petFeedQuery).future);
  await c.read(visitReportProvider(_visitKey).future);
  await c.read(reportSettingsProvider(_shop).future);
  await c.read(calendarMonthProvider(_monthKey).future);
  await c.read(customerDetailProvider(_customerKey).future);
}

/// 보내기·끊기 뒤에 다시 읽는 것 — 방문 상세, 하루 목록, 피드 둘(전체와 그 아이의 [기록] 탭), 미리보기.
const _rereads = [
  'GET /v1/shops/3/visits/101',
  'GET /v1/shops/3/visits',
  'GET /v1/shops/3/visits/feed',
  'GET /v1/shops/3/visits/feed',
  'GET $_reportPath',
];

void main() {
  test('보내기는 직전에 다시 읽어, 그 사이 다른 기기에서 뺀 사진을 되살리지 않는다', () async {
    final setup = _setup({
      'PUT $_reportPath': (o, b) =>
          FakeResponse(statusCode: 200, data: _preview(live: true)),
    });

    // 화면은 2 를 뺀 줄 모른다 — 이번에 누른 것은 1 하나다.
    final sent = await setup.container
        .read(reportCommandsProvider)
        .send(_shop, 101, changes: {1: true});

    expect(setup.calls, ['GET $_reportPath', 'PUT $_reportPath']);
    expect(bodyOf(setup.adapter.lastBodyByPath[_reportPath]), {
      'hidden_media_ids': [1, 2],
    });
    expect(sent.link.live, isTrue);
  });

  test('보내기·끊기가 끝나면 방문 상세·하루 목록·피드·미리보기를 다시 읽고, 달력·고객 쪽은 두지 않는다', () async {
    final setup = _setup({
      'PUT $_reportPath': (o, b) =>
          FakeResponse(statusCode: 200, data: _preview(live: true)),
      'DELETE $_reportPath': (o, b) => const FakeResponse(statusCode: 204),
    });
    await _watchEverything(setup);
    final commands = setup.container.read(reportCommandsProvider);

    await commands.send(_shop, 101, changes: const {});
    await _settle(setup);
    expect(
      setup.calls,
      unorderedEquals(['GET $_reportPath', 'PUT $_reportPath', ..._rereads]),
    );

    setup.adapter.requests.clear();
    await commands.revoke(_shop, 101);
    await _settle(setup);
    expect(setup.calls, unorderedEquals(['DELETE $_reportPath', ..._rereads]));
  });

  test('보내기·끊기는 실패해도 방문 상세·하루 목록·피드·미리보기를 다시 읽게 한다', () async {
    final setup = _setup({
      'PUT $_reportPath': (o, b) => _error(422, 'REPORT_EMPTY'),
      'DELETE $_reportPath': (o, b) => _error(404, 'REPORT_NOT_FOUND'),
    });
    await _watchEverything(setup);
    final commands = setup.container.read(reportCommandsProvider);

    await expectLater(
      commands.send(_shop, 101, changes: {1: true}),
      throwsA(
        isA<ApiException>().having((e) => e.code, 'code', 'REPORT_EMPTY'),
      ),
    );
    await _settle(setup);
    expect(
      setup.calls,
      unorderedEquals(['GET $_reportPath', 'PUT $_reportPath', ..._rereads]),
    );

    setup.adapter.requests.clear();
    await expectLater(
      commands.revoke(_shop, 101),
      throwsA(
        isA<ApiException>().having((e) => e.code, 'code', 'REPORT_NOT_FOUND'),
      ),
    );
    await _settle(setup);
    expect(setup.calls, unorderedEquals(['DELETE $_reportPath', ..._rereads]));
  });

  test('설정을 바꾸면 설정과 미리보기를 다시 읽는다', () async {
    final setup = _setup({
      'PUT $_settingsPath': (o, b) => FakeResponse(
        statusCode: 200,
        data: reportSettingsJson(linkDays: null, showWeight: true),
      ),
    });
    await _watchEverything(setup);

    final saved = await setup.container
        .read(reportCommandsProvider)
        .updateSettings(
          _shop,
          const ReportSettings(
            linkDays: null,
            showMenus: true,
            showShopInfo: true,
            showWeight: true,
            showAmount: false,
          ),
        );
    await _settle(setup);

    expect(saved.linkDays, isNull);
    expect(saved.showWeight, isTrue);
    expect(
      setup.calls,
      unorderedEquals([
        'PUT $_settingsPath',
        'GET $_settingsPath',
        'GET $_reportPath',
      ]),
    );
  });

  test('알림장 읽기·쓰기가 NOT_A_MEMBER 면 내 정보를 다시 불러온다', () async {
    FakeResponse notAMember(_, _) => _error(403, 'NOT_A_MEMBER');
    final setup = _setup({
      'GET $_reportPath': notAMember,
      'PUT $_reportPath': notAMember,
      'DELETE $_reportPath': notAMember,
      'GET $_settingsPath': notAMember,
      'PUT $_settingsPath': notAMember,
    });
    final c = setup.container;
    await c.read(sessionControllerProvider.future);
    final commands = c.read(reportCommandsProvider);

    final calls = <Future<Object?> Function()>[
      () => commands.send(_shop, 101, changes: const {}),
      () => commands.revoke(_shop, 101),
      () => commands.updateSettings(
        _shop,
        ReportSettings.fromJson(reportSettingsJson()),
      ),
      // 읽기는 화면이 보고 있는 동안만 살아 있다(autoDispose) — 보기 시작한 뒤에 읽는다.
      () {
        c.listen(visitReportProvider(_visitKey), (_, _) {}, onError: (_, _) {});
        return c.read(visitReportProvider(_visitKey).future);
      },
      () {
        c.listen(reportSettingsProvider(_shop), (_, _) {}, onError: (_, _) {});
        return c.read(reportSettingsProvider(_shop).future);
      },
    ];
    for (final (i, call) in calls.indexed) {
      await expectLater(call(), throwsA(isA<ApiException>()));
      expect(setup.gateway.refreshMeCallCount, i + 1);
    }
  });
}
