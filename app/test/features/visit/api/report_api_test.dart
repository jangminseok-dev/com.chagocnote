// ReportApi 를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로·메서드, 본문 모양,
// 응답 해석. 방문 상세·하루 목록·피드에 더해진 알림장 칸도 여기서 본다.
import 'dart:convert';

import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/api/report_api.dart';
import 'package:chagocnote/features/visit/api/report_models.dart';
import 'package:chagocnote/features/visit/api/visit_api.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

({ReportApi api, VisitApi visits, FakeHttpClientAdapter adapter}) _build(
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: ReportApi(client), visits: VisitApi(client), adapter: adapter);
}

Map<String, dynamic> _json(List<int>? body) =>
    jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

const _reportPath = '/v1/shops/3/visits/101/report';
const _settingsPath = '/v1/shops/3/report-settings';

void main() {
  test('미리보기는 뺀 것까지 미디어와 케어 메모·링크·설정을 읽는다', () async {
    final responses = [
      visitReportJson(
        media: [
          reportMediaJson(mediaId: 52),
          reportMediaJson(
            mediaId: 53,
            kind: 'video',
            hidden: true,
            durationSeconds: 12,
          ),
          reportMediaJson(mediaId: 51, phase: 'before'),
        ],
        careNote: '발바닥 각질',
        settings: reportSettingsJson(linkDays: 7, showWeight: true),
      ),
      visitReportJson(
        link: reportLinkJson(
          live: true,
          expiresAt: null,
          firstViewedAt: '2026-10-02T18:05:00+09:00',
        ),
      ),
    ];
    final s = _build(
      (options, body) =>
          FakeResponse(statusCode: 200, data: responses.removeAt(0)),
    );

    final preview = await s.api.preview(3, 101);

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'GET $_reportPath');
    expect(
      preview.media.map(
        (m) => (m.mediaId, m.kind, m.phase, m.hidden, m.durationSeconds),
      ),
      [
        (52, MediaKind.photo, MediaPhase.after, false, null),
        (53, MediaKind.video, MediaPhase.after, true, 12),
        (51, MediaKind.photo, MediaPhase.before, false, null),
      ],
    );
    expect(preview.media.first.thumbUrl, thumbUrl(52));
    expect(preview.careNote, '발바닥 각질');
    expect(preview.link.live, isFalse);
    expect(preview.link.url, isNull);
    expect(preview.link.expiresAt, isNull);
    expect(preview.link.firstViewedAt, isNull);
    expect(preview.link.createdAt, isNull);
    expect(preview.settings.linkDays, 7);
    expect(preview.settings.showWeight, isTrue);

    final sent = await s.api.preview(3, 101);

    expect(sent.media, isEmpty);
    expect(sent.careNote, isNull);
    expect(sent.link.live, isTrue);
    expect(sent.link.url, 'http://127.0.0.1:3010/r/TEST-TOKEN');
    expect(sent.link.expiresAt, isNull);
    expect(sent.link.firstViewedAt!.wall, DateTime(2026, 10, 2, 18, 5));
    expect(sent.link.createdAt!.wall, DateTime(2026, 10, 2, 15, 30));
    expect(sent.settings.linkDays, 30);

    // 앱이 모르는 상태는 살아 있는 링크가 아니다 — 주소가 있어도 [다시 공유]를 내지 않는다.
    expect(
      ReportLink.fromJson({
        ...reportLinkJson(live: true),
        'status': 'expired',
      }).live,
      isFalse,
    );
  });

  test('보내기는 hidden_media_ids 를 본문에 싣고(없으면 빈 배열) 링크가 든 미리보기를 돌려준다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: visitReportJson(
          media: [
            reportMediaJson(mediaId: 52),
            reportMediaJson(mediaId: 51, phase: 'before', hidden: true),
          ],
          link: reportLinkJson(live: true),
        ),
      ),
    );

    final sent = await s.api.send(3, 101, hiddenMediaIds: [51]);

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'PUT $_reportPath');
    expect(_json(s.adapter.lastBodyByPath[_reportPath]), {
      'hidden_media_ids': [51],
    });
    expect(sent.media.map((m) => (m.mediaId, m.hidden)), [
      (52, false),
      (51, true),
    ]);
    expect(sent.link.live, isTrue);
    expect(sent.link.expiresAt!.wall, DateTime(2026, 11, 1, 15, 30));

    await s.api.send(3, 101, hiddenMediaIds: []);
    expect(_json(s.adapter.lastBodyByPath[_reportPath]), {
      'hidden_media_ids': <int>[],
    });
  });

  test('끊기는 DELETE 를 보낸다', () async {
    final s = _build((options, body) => const FakeResponse(statusCode: 204));

    await s.api.revoke(3, 101);

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'DELETE $_reportPath');
  });

  test('설정 읽기·바꾸기 — 무기한은 link_days: null 을 그대로 보낸다', () async {
    final s = _build(
      (options, body) => FakeResponse(
        statusCode: 200,
        data: options.method == 'GET'
            ? reportSettingsJson(
                linkDays: 7,
                showMenus: false,
                showShopInfo: true,
                showWeight: false,
                showAmount: true,
              )
            : reportSettingsJson(
                linkDays: null,
                showMenus: true,
                showShopInfo: true,
                showWeight: false,
                showAmount: false,
              ),
      ),
    );

    final read = await s.api.settings(3);

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'GET $_settingsPath');
    expect(read.linkDays, 7);
    expect(
      (read.showMenus, read.showShopInfo, read.showWeight, read.showAmount),
      (false, true, false, true),
    );

    final saved = await s.api.updateSettings(
      3,
      const ReportSettings(
        linkDays: null,
        showMenus: true,
        showShopInfo: false,
        showWeight: true,
        showAmount: false,
      ),
    );

    expect(s.adapter.requests.last.method, 'PUT');
    expect(_json(s.adapter.lastBodyByPath[_settingsPath]), {
      'link_days': null,
      'show_menus': true,
      'show_shop_info': false,
      'show_weight': true,
      'show_amount': false,
    });
    expect(saved.linkDays, isNull);
    expect(
      (saved.showMenus, saved.showShopInfo, saved.showWeight, saved.showAmount),
      (true, true, false, false),
    );
  });

  test('방문 상세의 report, 하루 목록·피드 항목의 report_sent 를 읽는다', () async {
    final s = _build((options, body) {
      switch (options.path) {
        case '/v1/shops/3/visits/101':
          return FakeResponse(statusCode: 200, data: visitDetailJson());
        case '/v1/shops/3/visits/102':
          return FakeResponse(
            statusCode: 200,
            data: visitDetailJson(
              report: reportLinkJson(
                live: true,
                firstViewedAt: '2026-10-02T18:05:00+09:00',
              ),
            ),
          );
        case '/v1/shops/3/visits':
          return FakeResponse(
            statusCode: 200,
            data: dayJson(
              items: [
                dayItemJson(visitJson(status: 'completed'), reportSent: true),
                dayItemJson(visitJson(visitId: 102, status: 'completed')),
              ],
            ),
          );
      }
      return FakeResponse(
        statusCode: 200,
        data: feedJson(
          items: [
            feedItemJson(reportSent: true),
            feedItemJson(visitId: 102),
          ],
        ),
      );
    });

    final notSent = (await s.visits.detail(3, 101)).report;
    expect(notSent.live, isFalse);
    expect(notSent.url, isNull);

    final sent = (await s.visits.detail(3, 102)).report;
    expect(sent.live, isTrue);
    expect(sent.url, 'http://127.0.0.1:3010/r/TEST-TOKEN');
    expect(sent.expiresAt!.wall, DateTime(2026, 11, 1, 15, 30));
    expect(sent.firstViewedAt!.wall, DateTime(2026, 10, 2, 18, 5));

    final day = await s.visits.day(3, DateTime(2026, 10, 2));
    expect(day.items.map((i) => i.reportSent), [true, false]);

    final feed = await s.visits.feed(3);
    expect(feed.items.map((i) => i.reportSent), [true, false]);
  });
}
