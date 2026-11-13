// NotificationApi 를 실제 네트워크 없이(FakeHttpClientAdapter) 검증한다 — 경로·메서드, 본문 모양,
// 응답 해석. 알림톡 오류 코드의 문구도 여기서 본다.
import 'dart:convert';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/proxy/api_client.dart';
import 'package:chagocnote/core/storage/token_store.dart';
import 'package:chagocnote/features/visit/api/notification_api.dart';
import 'package:chagocnote/features/visit/api/notification_models.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/fake_http_client_adapter.dart';
import '../../../support/visit_fixtures.dart';

({NotificationApi api, FakeHttpClientAdapter adapter}) _build(
  FakeHandler handle,
) {
  final adapter = FakeHttpClientAdapter(handle);
  final dio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final refreshDio = Dio(BaseOptions())..httpClientAdapter = adapter;
  final store = MemoryTokenStore()..save(access: 'a', refresh: 'r');
  final client = ApiClient(tokenStore: store, dio: dio, refreshDio: refreshDio);
  return (api: NotificationApi(client), adapter: adapter);
}

Map<String, dynamic> _json(List<int>? body) =>
    jsonDecode(utf8.decode(body!)) as Map<String, dynamic>;

FakeHandler _answer(Object? data, {int status = 200}) =>
    (options, body) => FakeResponse(statusCode: status, data: data);

String _line(FakeHttpClientAdapter adapter) {
  final request = adapter.requests.single;
  return '${request.method} ${request.path}';
}

const _base = '/v1/shops/3/notification';

void main() {
  test('overview 는 채널·설정·템플릿을 읽는다', () async {
    final s = _build(_answer(notificationOverviewJson()));

    final overview = await s.api.overview(3);

    expect(_line(s.adapter), 'GET $_base');
    expect(overview.channel.status, ChannelStatus.linked);
    expect(overview.channel.linkedAt!.wall, DateTime(2026, 10, 14, 10));
    expect(overview.channel.senderVerified, isFalse);
    expect(overview.channel.smsFallbackEnabled, isFalse);
    expect(overview.settings!.reminderTime, '18:00');
    expect(overview.settings!.nextVisitAfterWeeks, isNull);
    expect(overview.settings!.nextVisitCooldownDays, 30);
    expect(overview.settings!.nextVisitEnabled, isFalse);
    expect(
      overview.templateOf(NotificationKind.confirm),
      TemplateStatus.approved,
    );
    expect(overview.templateOf(NotificationKind.nextVisit), isNull);
  });

  test('연동 전에는 설정이 없다', () async {
    final s = _build(_answer(notificationOverviewJson(channel: 'none')));

    final overview = await s.api.overview(3);

    expect(overview.channel.status, ChannelStatus.none);
    expect(overview.settings, isNull);
    expect(overview.templates, isEmpty);
  });

  test('채널 상태 글자 넷을 enum 으로 바꾼다', () async {
    for (final (code, status) in [
      ('none', ChannelStatus.none),
      ('token_requested', ChannelStatus.tokenRequested),
      ('linked', ChannelStatus.linked),
      ('unlinked', ChannelStatus.unlinked),
    ]) {
      final s = _build(_answer(notificationOverviewJson(channel: code)));
      expect((await s.api.overview(3)).channel.status, status);
    }
  });

  test('settingsBody 는 아홉 칸이고 한 칸만 바꾼다', () async {
    final s = _build(
      _answer(
        notificationOverviewJson(senderVerified: true, smsFallback: true),
      ),
    );
    final overview = await s.api.overview(3);

    final body = overview.settingsBody(field: 'reminder_enabled', value: false);

    expect(body, {
      'confirm_enabled': true,
      'reminder_enabled': false,
      'report_enabled': true,
      'change_enabled': true,
      'next_visit_enabled': false,
      'sms_fallback_enabled': true,
      'reminder_time': '18:00',
      'next_visit_after_weeks': null,
      'next_visit_cooldown_days': 30,
    });
    expect(overview.settingsBody()['reminder_enabled'], isTrue);
  });

  test('온보딩 요청 본문은 서버 칸 이름 그대로다', () async {
    final seen = <String, Map<String, dynamic>>{};
    final s = _build((options, body) {
      seen['${options.method} ${options.path}'] = _json(body);
      final overview =
          options.path.endsWith('/channel') || options.path.endsWith('/sender');
      return FakeResponse(
        statusCode: overview ? 200 : 202,
        data: overview
            ? notificationOverviewJson()
            : {'status': 'token_requested'},
      );
    });

    await s.api.requestChannelToken(
      3,
      searchId: '@hisshaus',
      adminPhone: '01012345678',
      categoryCode: '00100010001',
    );
    final linked = await s.api.linkChannel(
      3,
      searchId: '@hisshaus',
      adminPhone: '01012345678',
      categoryCode: '00100010001',
      token: '000000',
    );
    await s.api.requestSenderVerification(3, '0212345678');
    final verified = await s.api.confirmSender(
      3,
      phone: '0212345678',
      code: '000000',
    );

    const inputs = {
      'search_id': '@hisshaus',
      'admin_phone': '01012345678',
      'category_code': '00100010001',
    };
    expect(seen, {
      'POST $_base/channel/token': inputs,
      'POST $_base/channel': {...inputs, 'token': '000000'},
      'POST $_base/sender/verification': {'phone': '0212345678'},
      'POST $_base/sender': {'phone': '0212345678', 'code': '000000'},
    });
    expect(linked.channel.status, ChannelStatus.linked);
    expect(verified.channel.status, ChannelStatus.linked);
  });

  test('연동 해제는 DELETE 다', () async {
    final s = _build(_answer(null, status: 204));

    await s.api.unlinkChannel(3);

    expect(_line(s.adapter), 'DELETE $_base/channel');
  });

  test('설정은 받은 본문 그대로 PUT 하고 응답을 읽는다', () async {
    final s = _build(
      _answer(
        notificationOverviewJson(
          settings: notificationSettingsJson(reminderTime: '09:30'),
        ),
      ),
    );

    final overview = await s.api.updateSettings(3, {'reminder_time': '09:30'});

    final request = s.adapter.requests.single;
    expect('${request.method} ${request.path}', 'PUT $_base/settings');
    expect(_json(s.adapter.lastBodyByPath[request.path]), {
      'reminder_time': '09:30',
    });
    expect(overview.settings!.reminderTime, '09:30');
  });

  test('내역은 칸을 읽고 next_visit 과 fallback_sent 를 enum 으로 바꾼다', () async {
    final s = _build(
      _answer({
        'items': [
          notificationMessageJson(
            messageId: 9,
            kind: 'next_visit',
            status: 'fallback_sent',
            sentAt: '2026-10-02T14:03:00+09:00',
          ),
          notificationMessageJson(
            messageId: 8,
            kind: 'reminder',
            status: 'failed',
            errorKind: 'permanent',
            shareText: '[두부네] 내일 14:00 예약을 잊지 마세요.',
          ),
        ],
      }),
    );

    final rows = await s.api.forVisit(3, 101);

    expect(_line(s.adapter), 'GET /v1/shops/3/visits/101/notifications');
    expect(rows.map((m) => (m.messageId, m.kind, m.status, m.errorKind)), [
      (9, NotificationKind.nextVisit, NotificationStatus.fallbackSent, null),
      (
        8,
        NotificationKind.reminder,
        NotificationStatus.failed,
        NotificationErrorKind.permanent,
      ),
    ]);
    expect(rows.first.sentAt!.wall, DateTime(2026, 10, 2, 14, 3));
    expect(rows.first.scheduledAt.wall, DateTime(2026, 10, 2, 14, 2));
    expect(rows.last.shareText, '[두부네] 내일 14:00 예약을 잊지 마세요.');
    expect(rows.last.sentAt, isNull);
  });

  test('내역은 모르는 종류와 상태의 줄을 뺀다', () async {
    final s = _build(
      _answer({
        'items': [
          notificationMessageJson(messageId: 1, kind: 'brand_new'),
          notificationMessageJson(messageId: 2, status: 'weird'),
          notificationMessageJson(messageId: 3),
          notificationMessageJson(messageId: 4, status: 'scheduled'),
        ],
      }),
    );

    final rows = await s.api.forVisit(3, 101);

    expect(rows.map((m) => m.messageId), [3, 4]);
  });

  test('재발송은 종류의 서버 글자로 부르고 message_id 를 돌려준다', () async {
    final s = _build(_answer({'message_id': 9}, status: 201));

    final id = await s.api.resend(3, 101, NotificationKind.nextVisit);

    expect(
      _line(s.adapter),
      'POST /v1/shops/3/visits/101/notifications/next_visit/resend',
    );
    expect(id, 9);
  });

  test('줄 하나를 읽는다', () async {
    final s = _build(
      _answer(notificationMessageJson(messageId: 9, status: 'accepted')),
    );

    final row = await s.api.message(3, 9);

    expect(_line(s.adapter), 'GET /v1/shops/3/notifications/9');
    expect(row!.status, NotificationStatus.accepted);
  });

  test('알림톡 오류 코드는 앱의 문구로 바뀐다', () {
    String text(String code) =>
        messageFor(ApiException(statusCode: 409, code: code, message: 'x'));

    expect(text('NOTIFICATION_CHANNEL_NOT_LINKED'), '먼저 카카오톡 채널을 연동해 주세요.');
    expect(text('NOTIFICATION_CHANNEL_LINKED'), '이미 연동된 채널이 있어요.');
    expect(text('NOTIFICATION_TOKEN_INVALID'), '인증번호가 틀렸거나 시간이 지났어요.');
    expect(text('NOTIFICATION_SENDER_NOT_VERIFIED'), '발신번호를 먼저 인증해 주세요.');
    expect(text('NOTIFICATION_TEMPLATE_NOT_APPROVED'), '아직 심사가 끝나지 않은 알림이에요.');
    expect(text('NOTIFICATION_ALREADY_PENDING'), '이미 보내는 중이에요.');
    expect(
      text('NOTIFICATION_MESSAGE_NOT_FOUND'),
      '다시 보낼 알림을 찾지 못했어요. 화면을 새로 불러왔어요.',
    );
    expect(text('NOTIFICATION_RATE_LIMITED'), '요청이 너무 잦아요. 잠시 뒤에 다시 해 주세요.');
    expect(
      text('NOTIFICATION_PROVIDER_UNAVAILABLE'),
      '카카오톡 연결이 잠시 원활하지 않아요. 다시 시도해 주세요.',
    );
  });
}
