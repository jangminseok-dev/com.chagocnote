import 'dart:async';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_sheet_action.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../../support/customer_test_app.dart';
import '../../../../support/fake_http_client_adapter.dart';
import '../../../../support/visit_fixtures.dart';
import '../../../../support/visit_test_backend.dart';

const _path = '/v1/shops/3/notification';

FakeResponse _error(int status, String code) =>
    FakeResponse(statusCode: status, data: {'code': code, 'message': 'x'});

/// 알림톡 서버. GET 은 지금의 [overview]로 답한다. 쓰기는 받은 본문을 적고 [overview]를 바꾼 뒤 그것으로
/// 답한다 — `…Error`가 있으면 바꾸지 않고 그것으로 답한다. 게이트가 있으면 끝날 때까지 답을 붙든다.
class _Server {
  _Server({Map<String, dynamic>? overview})
    : overview = overview ?? notificationOverviewJson();

  Map<String, dynamic> overview;
  FakeResponse? getError;
  Completer<void>? getGate;
  Completer<void>? putGate;
  FakeResponse? tokenError;
  FakeResponse? linkError;
  FakeResponse? putError;
  FakeResponse? senderCodeError;
  final tokens = <Map<String, dynamic>>[];
  final links = <Map<String, dynamic>>[];
  final puts = <Map<String, dynamic>>[];
  final senderRequests = <Map<String, dynamic>>[];
  final senderConfirms = <Map<String, dynamic>>[];
  var unlinks = 0;

  late final backend = VisitTestBackend({
    'GET $_path': (o, b) async {
      await getGate?.future;
      return getError ?? FakeResponse(statusCode: 200, data: overview);
    },
    'POST $_path/channel/token': (o, body) {
      tokens.add(bodyOf(body));
      return tokenError ??
          FakeResponse(statusCode: 202, data: {'status': 'token_requested'});
    },
    'POST $_path/channel': (o, body) {
      links.add(bodyOf(body));
      if (linkError case final error?) return error;
      overview = notificationOverviewJson(
        templates: [
          for (final kind in const [
            'confirm',
            'reminder',
            'report',
            'change',
            'cancel',
          ])
            notificationTemplateJson(kind: kind, status: 'pending'),
        ],
      );
      return FakeResponse(statusCode: 200, data: overview);
    },
    'DELETE $_path/channel': (o, b) {
      unlinks++;
      overview = notificationOverviewJson(channel: 'unlinked');
      return FakeResponse(statusCode: 204, data: null);
    },
    'PUT $_path/settings': (o, body) async {
      final sent = bodyOf(body);
      puts.add(sent);
      await putGate?.future;
      if (putError case final error?) return error;
      final channel = Map<String, dynamic>.of(
        overview['channel'] as Map<String, dynamic>,
      )..['sms_fallback_enabled'] = sent['sms_fallback_enabled'];
      final templates = [
        ...(overview['templates'] as List).cast<Map<String, dynamic>>(),
      ];
      // 다음 예약 제안을 처음 켜면 그 템플릿이 등록된다.
      if (sent['next_visit_enabled'] == true &&
          !templates.any((t) => t['kind'] == 'next_visit')) {
        templates.add(
          notificationTemplateJson(kind: 'next_visit', status: 'pending'),
        );
      }
      overview = {
        'channel': channel,
        'settings': Map<String, dynamic>.of(sent)
          ..remove('sms_fallback_enabled'),
        'templates': templates,
      };
      return FakeResponse(statusCode: 200, data: overview);
    },
    'POST $_path/sender/verification': (o, body) {
      senderRequests.add(bodyOf(body));
      return FakeResponse(
        statusCode: 202,
        data: {'status': 'verification_requested'},
      );
    },
    'POST $_path/sender': (o, body) {
      final sent = bodyOf(body);
      senderConfirms.add(sent);
      if (senderCodeError case final error?) return error;
      final channel =
          Map<String, dynamic>.of(overview['channel'] as Map<String, dynamic>)
            ..['sender_verified'] = true
            ..['sender_number'] = sent['phone'];
      overview = {...overview, 'channel': channel};
      return FakeResponse(statusCode: 200, data: overview);
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
  useTallView(tester, height: 1400);
  await pushOnHome<Object?>(tester, setup, '/settings/notification');
  return setup;
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

bool _enabled(WidgetTester tester, String label) =>
    tester.widget<AppButton>(_button(label)).onPressed != null;

Finder _field(String key) => find.byKey(Key(key));

String _text(WidgetTester tester, String key) =>
    tester.widget<TextField>(_field(key)).controller!.text;

Finder _switch(String label) =>
    find.byWidgetPredicate((w) => w is AppSwitch && w.semanticLabel == label);

bool _on(WidgetTester tester, String label) =>
    tester.widget<AppSwitch>(_switch(label)).value;

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await settle(tester);
}

Future<void> _fillInputs(
  WidgetTester tester, {
  String phone = '01012345678',
}) async {
  await tester.enterText(_field('notification_search_id'), '@hisshaus');
  await tester.enterText(_field('notification_admin_phone'), phone);
  await tester.enterText(_field('notification_category'), '00100010001');
  await settle(tester);
}

const _inputs = {
  'search_id': '@hisshaus',
  'admin_phone': '01012345678',
  'category_code': '00100010001',
};

const _kinds = ['예약 접수', '전날 리마인드', '예약 변경·취소', '알림장', '다음 예약 제안'];

void main() {
  group('연동 전', () {
    _Server unlinked([String channel = 'none']) =>
        _Server(overview: notificationOverviewJson(channel: channel));

    testWidgets('안내 세 줄과 입력 세 칸이 보인다', (tester) async {
      await _open(tester, unlinked());

      expect(find.byKey(ScreenKeys.notificationSettings), findsOneWidget);
      expect(find.text('알림톡 설정'), findsOneWidget);
      expect(find.text('카카오톡 채널을 만들어요.'), findsOneWidget);
      expect(find.text('채널의 비즈니스 인증을 받아요. 며칠 걸려요.'), findsOneWidget);
      expect(find.text('채널 관리자센터에서 "관리자 추가 인증"을 꺼요.'), findsOneWidget);
      expect(find.byType(TextField), findsNWidgets(3));
      expect(find.byType(AppSwitch), findsNothing);
      expect(_field('notification_token'), findsNothing);
    });

    testWidgets('세 칸을 채우고 번호가 맞아야 인증번호 받기가 눌린다', (tester) async {
      await _open(tester, unlinked());

      expect(_enabled(tester, '인증번호 받기'), isFalse);
      await _fillInputs(tester, phone: '0101234');
      expect(_enabled(tester, '인증번호 받기'), isFalse);
      await _fillInputs(tester);
      expect(_enabled(tester, '인증번호 받기'), isTrue);
    });

    testWidgets('인증번호 받기는 세 칸을 보내고 6자리 칸을 연다', (tester) async {
      final server = unlinked();
      await _open(tester, server);
      await _fillInputs(tester);

      await _tap(tester, _button('인증번호 받기'));

      expect(server.tokens, [_inputs]);
      expect(_field('notification_token'), findsOneWidget);
      for (final key in [
        'notification_search_id',
        'notification_admin_phone',
        'notification_category',
      ]) {
        expect(tester.widget<TextField>(_field(key)).enabled, isFalse);
      }
      expect(_enabled(tester, '연동하기'), isFalse);
    });

    testWidgets('연동하기는 세 칸과 인증번호를 보내고 연동 뒤 화면으로 바뀐다', (tester) async {
      final server = unlinked();
      await _open(tester, server);
      await _fillInputs(tester);
      await _tap(tester, _button('인증번호 받기'));
      await tester.enterText(_field('notification_token'), '000000');
      await settle(tester);

      await _tap(tester, _button('연동하기'));

      expect(server.links, [
        {..._inputs, 'token': '000000'},
      ]);
      expect(find.byType(TextField), findsNothing);
      expect(find.text('연동됨 · 10월 14일'), findsOneWidget);
    });

    testWidgets('인증번호가 틀리면 문구를 보이고 입력을 지우지 않는다', (tester) async {
      final server = unlinked()
        ..linkError = _error(400, 'NOTIFICATION_TOKEN_INVALID');
      await _open(tester, server);
      await _fillInputs(tester);
      await _tap(tester, _button('인증번호 받기'));
      await tester.enterText(_field('notification_token'), '123456');
      await settle(tester);

      await _tap(tester, _button('연동하기'));

      expect(find.text('인증번호가 틀렸거나 시간이 지났어요.'), findsOneWidget);
      expect(_text(tester, 'notification_search_id'), '@hisshaus');
      expect(_text(tester, 'notification_admin_phone'), '01012345678');
      expect(_text(tester, 'notification_category'), '00100010001');
      expect(_text(tester, 'notification_token'), '123456');
    });

    testWidgets('요청이 잦으면 429 문구를 보이고 6자리 칸은 열리지 않는다', (tester) async {
      final server = unlinked()
        ..tokenError = _error(429, 'NOTIFICATION_RATE_LIMITED');
      await _open(tester, server);
      await _fillInputs(tester);

      await _tap(tester, _button('인증번호 받기'));

      expect(find.text('요청이 너무 잦아요. 잠시 뒤에 다시 해 주세요.'), findsOneWidget);
      expect(_field('notification_token'), findsNothing);
    });

    testWidgets('다시 입력을 누르면 첫 단계로 돌아간다', (tester) async {
      await _open(tester, unlinked());
      await _fillInputs(tester);
      await _tap(tester, _button('인증번호 받기'));

      await _tap(tester, _button('다시 입력'));

      expect(_field('notification_token'), findsNothing);
      expect(
        tester.widget<TextField>(_field('notification_search_id')).enabled,
        isTrue,
      );
      expect(_text(tester, 'notification_search_id'), '@hisshaus');
    });

    testWidgets('직원에게는 사장님이 연동할 수 있어요만 보인다', (tester) async {
      await _open(tester, unlinked(), role: 'staff');

      expect(find.text('사장님이 연동할 수 있어요.'), findsOneWidget);
      expect(find.byType(TextField), findsNothing);
      expect(find.byType(AppButton), findsNothing);
    });

    for (final channel in ['token_requested', 'unlinked']) {
      testWidgets('채널이 $channel 이어도 연동 전 화면이다', (tester) async {
        await _open(tester, unlinked(channel));

        expect(find.byType(TextField), findsNWidgets(3));
        expect(_field('notification_token'), findsNothing);
      });
    }

    testWidgets('읽지 못하면 다시 시도가 보이고 누르면 다시 읽는다', (tester) async {
      final server = unlinked()..getError = _error(500, 'INTERNAL');
      await _open(tester, server);

      expect(find.byType(TextField), findsNothing);
      server.getError = null;
      await _tap(tester, _button(AppStrings.retry));

      expect(find.byType(TextField), findsNWidgets(3));
    });

    testWidgets('연동 전 골든', (tester) async {
      await _open(tester, unlinked());

      await expectLater(
        find.byKey(ScreenKeys.notificationSettings),
        matchesGoldenFile('goldens/notification_settings_unlinked.png'),
      );
    });
  });

  group('연동 후', () {
    testWidgets('채널 줄과 스위치 다섯과 문자 대체가 보인다', (tester) async {
      await _open(tester, _Server());

      expect(find.text('연동됨 · 10월 14일'), findsOneWidget);
      expect(
        tester
            .widgetList<AppSwitch>(find.byType(AppSwitch))
            .map((s) => s.semanticLabel),
        [..._kinds, '문자로 대신 보내기'],
      );
      expect(
        [for (final kind in _kinds) _on(tester, kind)],
        [true, true, true, true, false],
      );
      expect(_on(tester, '문자로 대신 보내기'), isFalse);
      expect(find.text('사장만 바꿀 수 있어요.'), findsNothing);
    });

    testWidgets('스위치를 누르면 아홉 칸 전체를 보내고 응답으로 다시 그린다', (tester) async {
      final server = _Server();
      await _open(tester, server);

      await _tap(tester, _switch('전날 리마인드'));

      expect(server.puts, [
        {
          'confirm_enabled': true,
          'reminder_enabled': false,
          'report_enabled': true,
          'change_enabled': true,
          'next_visit_enabled': false,
          'sms_fallback_enabled': false,
          'reminder_time': '18:00',
          'next_visit_after_weeks': null,
          'next_visit_cooldown_days': 30,
        },
      ]);
      expect(_on(tester, '전날 리마인드'), isFalse);
    });

    testWidgets('보내는 중에는 다른 누름을 받지 않는다', (tester) async {
      final server = _Server()..putGate = Completer<void>();
      await _open(tester, server);

      await tester.tap(_switch('전날 리마인드'));
      await tester.pump();
      await tester.tap(_switch('알림장'));
      await tester.pump();
      server.putGate!.complete();
      await settle(tester);

      expect(server.puts.length, 1);
    });

    testWidgets('다시 읽는 중이거나 읽기에 실패했으면 누름을 보내지 않는다', (tester) async {
      final server = _Server();
      await _open(tester, server);

      // PUT 은 끝났고 다시 읽기(GET)가 아직 오지 않았다 — 화면은 옛 값을 보이고 있다.
      server.getGate = Completer<void>();
      await _tap(tester, _switch('전날 리마인드'));
      await _tap(tester, _switch('알림장'));
      expect(server.puts, hasLength(1));

      server.getGate!.complete();
      server.getGate = null;
      await settle(tester);
      expect(_on(tester, '전날 리마인드'), isFalse);

      // 다시 읽기가 실패해 "이전 내용"을 보이는 동안에도 눌리지 않는다 — [다시 시도]로 읽은 뒤에 눌린다.
      server.getError = _error(503, 'x');
      await _tap(tester, _switch('알림장'));
      expect(server.puts, hasLength(2));
      await _tap(tester, _switch('예약 접수'));
      expect(server.puts, hasLength(2));

      server.getError = null;
      await _tap(tester, find.text(AppStrings.retry));
      await _tap(tester, _switch('예약 접수'));
      expect(server.puts, hasLength(3));
    });

    testWidgets('서버가 거절하면 문구를 보이고 서버 값으로 돌아간다', (tester) async {
      final server = _Server()
        ..putError = _error(409, 'NOTIFICATION_CHANNEL_NOT_LINKED');
      await _open(tester, server);

      await _tap(tester, _switch('전날 리마인드'));

      expect(find.text('먼저 카카오톡 채널을 연동해 주세요.'), findsOneWidget);
      expect(_on(tester, '전날 리마인드'), isTrue);
    });

    for (final (status, text) in [
      ('pending', '심사 중이에요(보통 1~3일)'),
      ('approved', '승인됨'),
      ('rejected', '반려됐어요 · 운영자가 확인 중'),
    ]) {
      testWidgets('템플릿이 $status 이면 "$text"를 보인다', (tester) async {
        await _open(
          tester,
          _Server(
            overview: notificationOverviewJson(
              templates: [
                notificationTemplateJson(kind: 'confirm', status: status),
              ],
            ),
          ),
        );

        expect(find.text(text), findsOneWidget);
      });
    }

    testWidgets('변경·취소 줄은 둘 가운데 나쁜 쪽 문구다', (tester) async {
      await _open(
        tester,
        _Server(
          overview: notificationOverviewJson(
            templates: [
              notificationTemplateJson(kind: 'change'),
              notificationTemplateJson(kind: 'cancel', status: 'pending'),
            ],
          ),
        ),
      );

      expect(find.text('심사 중이에요(보통 1~3일)'), findsOneWidget);
      expect(find.text('승인됨'), findsNothing);
    });

    testWidgets('다음 예약 제안은 템플릿이 없으면 문구가 없고 켜면 심사 중을 보인다', (tester) async {
      final server = _Server(
        overview: notificationOverviewJson(templates: const []),
      );
      await _open(tester, server);
      expect(find.text('심사 중이에요(보통 1~3일)'), findsNothing);

      await _tap(tester, _switch('다음 예약 제안'));

      expect(server.puts.single['next_visit_enabled'], isTrue);
      expect(_on(tester, '다음 예약 제안'), isTrue);
      expect(find.text('심사 중이에요(보통 1~3일)'), findsOneWidget);
      expect(find.text('지난 미용 뒤'), findsOneWidget);
      expect(find.text('다시 보내지 않는 기간'), findsOneWidget);
    });

    testWidgets('리마인드가 켜져 있을 때만 시각 줄이 보이고 고르면 닫히며 한 번 보낸다', (tester) async {
      final server = _Server();
      await _open(tester, server);
      expect(find.text('보내는 시각'), findsOneWidget);
      expect(find.text('18:00'), findsOneWidget);

      await _tap(tester, find.text('18:00'));
      await _tap(
        tester,
        find.byWidgetPredicate(
          (w) => w is AppSheetAction && w.label == '09:30',
        ),
      );

      expect(server.puts.single['reminder_time'], '09:30');
      expect(find.byType(AppSheetAction), findsNothing);
      expect(find.text('09:30'), findsOneWidget);

      // 같은 값을 고르면 보내지 않는다.
      await _tap(tester, find.text('09:30'));
      await _tap(
        tester,
        find.byWidgetPredicate(
          (w) => w is AppSheetAction && w.label == '09:30',
        ),
      );
      expect(server.puts.length, 1);

      await _tap(tester, _switch('전날 리마인드'));
      expect(find.text('보내는 시각'), findsNothing);
    });

    testWidgets('주 고르기의 지난 방문 간격대로는 null 을, 쿨다운은 일수를 보낸다', (tester) async {
      final server = _Server(
        overview: notificationOverviewJson(
          settings: notificationSettingsJson(
            nextVisitEnabled: true,
            nextVisitAfterWeeks: 4,
          ),
        ),
      );
      await _open(tester, server);

      await _tap(tester, find.text('4주'));
      await _tap(
        tester,
        find.byWidgetPredicate(
          (w) => w is AppSheetAction && w.label == '지난 방문 간격대로',
        ),
      );
      await _tap(tester, find.text('30일'));
      await _tap(
        tester,
        find.byWidgetPredicate((w) => w is AppSheetAction && w.label == '60일'),
      );

      expect(server.puts.length, 2);
      expect(server.puts.first.containsKey('next_visit_after_weeks'), isTrue);
      expect(server.puts.first['next_visit_after_weeks'], isNull);
      expect(server.puts.last['next_visit_cooldown_days'], 60);
      expect(find.text('지난 방문 간격대로'), findsOneWidget);
      expect(find.text('60일'), findsOneWidget);
    });

    testWidgets('서버 값이 목록에 없으면 그 값도 고를 수 있게 보인다', (tester) async {
      await _open(
        tester,
        _Server(
          overview: notificationOverviewJson(
            settings: notificationSettingsJson(
              nextVisitEnabled: true,
              nextVisitCooldownDays: 45,
            ),
          ),
        ),
      );

      await _tap(tester, find.text('45일'));

      expect(
        tester
            .widgetList<AppSheetAction>(find.byType(AppSheetAction))
            .map((a) => a.label),
        ['45일', '14일', '30일', '60일', '90일'],
      );
    });

    testWidgets('직원은 스위치가 눌리지 않고 더 보기가 없다', (tester) async {
      final server = _Server();
      await _open(tester, server, role: 'staff');

      expect(find.text('사장만 바꿀 수 있어요.'), findsOneWidget);
      expect(
        tester
            .widgetList<AppSwitch>(find.byType(AppSwitch))
            .every((s) => s.onChanged == null),
        isTrue,
      );
      expect(find.bySemanticsLabel(AppStrings.more), findsNothing);
      await tester.tap(find.text('18:00'), warnIfMissed: false);
      await settle(tester);
      expect(find.byType(AppSheetAction), findsNothing);
      expect(server.puts, isEmpty);
    });

    testWidgets('연동 해제는 확인 뒤 DELETE 하고 연동 전 화면으로 돌아간다', (tester) async {
      final server = _Server();
      await _open(tester, server);

      await _tap(tester, find.bySemanticsLabel(AppStrings.more));
      await _tap(
        tester,
        find.byWidgetPredicate(
          (w) => w is AppSheetAction && w.label == '연동 해제',
        ),
      );
      expect(find.text('예정된 알림톡이 모두 취소돼요. 연동을 해제할까요?'), findsOneWidget);
      expect(server.unlinks, 0);
      await _tap(tester, _button('연동 해제'));

      expect(server.unlinks, 1);
      expect(find.byType(TextField), findsNWidgets(3));
    });

    testWidgets('해제 확인에서 취소하면 보내지 않는다', (tester) async {
      final server = _Server();
      await _open(tester, server);

      await _tap(tester, find.bySemanticsLabel(AppStrings.more));
      await _tap(
        tester,
        find.byWidgetPredicate(
          (w) => w is AppSheetAction && w.label == '연동 해제',
        ),
      );
      await _tap(tester, _button(AppStrings.cancel));

      expect(server.unlinks, 0);
      expect(find.text('연동됨 · 10월 14일'), findsOneWidget);
    });

    testWidgets('발신번호 인증 없이 문자 대체를 켜면 시트가 뜨고 PUT 은 나가지 않는다', (tester) async {
      final server = _Server();
      await _open(tester, server);

      await _tap(tester, _switch('문자로 대신 보내기'));

      expect(find.text('발신번호 인증'), findsOneWidget);
      expect(_field('notification_sender_phone'), findsOneWidget);
      expect(server.puts, isEmpty);
    });

    testWidgets('시트에서 인증을 마치면 닫히고 문자 대체를 켜는 PUT 이 한 번 나간다', (tester) async {
      final server = _Server();
      await _open(tester, server);
      await _tap(tester, _switch('문자로 대신 보내기'));

      expect(_enabled(tester, '인증번호 받기'), isFalse);
      await tester.enterText(_field('notification_sender_phone'), '0212345678');
      await settle(tester);
      await _tap(tester, _button('인증번호 받기'));
      await tester.enterText(_field('notification_sender_code'), '000000');
      await settle(tester);
      await _tap(tester, _button('확인'));

      expect(server.senderRequests, [
        {'phone': '0212345678'},
      ]);
      expect(server.senderConfirms, [
        {'phone': '0212345678', 'code': '000000'},
      ]);
      expect(find.text('발신번호 인증'), findsNothing);
      expect(server.puts.single['sms_fallback_enabled'], isTrue);
      expect(_on(tester, '문자로 대신 보내기'), isTrue);
      expect(find.textContaining('발신번호 0212345678'), findsOneWidget);
    });

    testWidgets('시트의 인증번호가 틀리면 시트 안에 문구를 보이고 닫지 않는다', (tester) async {
      final server = _Server()
        ..senderCodeError = _error(400, 'NOTIFICATION_TOKEN_INVALID');
      await _open(tester, server);
      await _tap(tester, _switch('문자로 대신 보내기'));
      await tester.enterText(_field('notification_sender_phone'), '0212345678');
      await settle(tester);
      await _tap(tester, _button('인증번호 받기'));
      await tester.enterText(_field('notification_sender_code'), '123456');
      await settle(tester);

      await _tap(tester, _button('확인'));

      expect(find.text('인증번호가 틀렸거나 시간이 지났어요.'), findsOneWidget);
      expect(find.text('발신번호 인증'), findsOneWidget);
      expect(server.puts, isEmpty);
    });

    testWidgets('발신번호를 이미 인증했으면 문자 대체는 바로 PUT 한다', (tester) async {
      final server = _Server(
        overview: notificationOverviewJson(senderVerified: true),
      );
      await _open(tester, server);

      await _tap(tester, _switch('문자로 대신 보내기'));

      expect(find.text('발신번호 인증'), findsNothing);
      expect(server.puts.single['sms_fallback_enabled'], isTrue);
    });

    testWidgets('심사 중 골든', (tester) async {
      await _open(
        tester,
        _Server(
          overview: notificationOverviewJson(
            templates: [
              for (final kind in const [
                'confirm',
                'reminder',
                'report',
                'change',
                'cancel',
              ])
                notificationTemplateJson(kind: kind, status: 'pending'),
            ],
          ),
        ),
      );

      await expectLater(
        find.byKey(ScreenKeys.notificationSettings),
        matchesGoldenFile('goldens/notification_settings_pending.png'),
      );
    });

    testWidgets('전부 승인 골든', (tester) async {
      await _open(
        tester,
        _Server(
          overview: notificationOverviewJson(
            senderVerified: true,
            smsFallback: true,
            settings: notificationSettingsJson(
              nextVisitEnabled: true,
              nextVisitAfterWeeks: 4,
            ),
            templates: [
              for (final kind in const [
                'confirm',
                'reminder',
                'report',
                'change',
                'cancel',
                'next_visit',
              ])
                notificationTemplateJson(kind: kind),
            ],
          ),
        ),
      );

      await expectLater(
        find.byKey(ScreenKeys.notificationSettings),
        matchesGoldenFile('goldens/notification_settings_approved.png'),
      );
    });

    testWidgets('발신번호 인증 시트 골든', (tester) async {
      await _open(tester, _Server());
      await _tap(tester, _switch('문자로 대신 보내기'));

      await expectLater(
        find.byType(MaterialApp),
        matchesGoldenFile('goldens/notification_sender_sheet.png'),
      );
    });
  });
}
