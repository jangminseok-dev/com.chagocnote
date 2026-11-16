// 서류 설정(⑪-B) — 동의서의 글·보내는 글·기준값을 매장이 자기 가게에 맞게 고친다.
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:chagocnote/features/customer/screens/form_text_edit_screens.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/form_settings_fixtures.dart';
import '../../../support/visit_test_backend.dart';

const _settings = '/v1/shops/3/form-settings';
const _texts = '/v1/shops/3/consent-texts';

/// 서류 설정 서버 — 받은 본문을 적고 그대로 저장해 돌려준다. [putError] 가 있으면 저장하지 않는다.
class _Server {
  Map<String, dynamic> settings = formSettingsJson();
  Map<String, dynamic> texts = consentTextsJson();
  FakeResponse? putError;
  final puts = <Map<String, dynamic>>[];
  final textPuts = <(String, Object?)>[];

  late final backend = VisitTestBackend({
    'GET $_settings': (o, b) => FakeResponse(statusCode: 200, data: settings),
    'PUT $_settings': (o, body) {
      final sent = bodyOf(body);
      puts.add(sent);
      if (putError case final error?) return error;
      settings = formSettingsJson(
        linkDays: sent['link_days'] as int,
        seniorAge: sent['senior_age'] as int,
        consentDays: sent['consent_days'] as int,
        reservationText: sent['reservation_text'] as String? ?? defaultReservationText,
        consentText: sent['consent_text'] as String? ?? defaultConsentText,
        intakeKeepDays: sent['intake_keep_days'] as int? ?? 30,
        intakeHidden: [...(sent['intake_hidden'] as List? ?? const []).cast<String>()],
      );
      return FakeResponse(statusCode: 200, data: settings);
    },
    'GET $_texts': (o, b) => FakeResponse(statusCode: 200, data: texts),
    for (final part in ['basic', 'senior', 'condition'])
      'PUT $_texts/$part': (o, body) {
        final sent = bodyOf(body)['body'];
        textPuts.add((part, sent));
        if (putError case final error?) return error;
        final saved = consentTextJson(part, body: sent as String?, edited: sent != null);
        texts = {
          'parts': [for (final p in texts['parts'] as List) (p as Map)['part'] == part ? saved : p],
        };
        return FakeResponse(statusCode: 200, data: saved);
      },
  });
}

Future<CustomerTestSetup> _open(WidgetTester tester, _Server server, {String path = '/settings/forms', bool owner = true}) async {
  final setup = CustomerTestSetup(server.backend.call, role: owner ? 'owner' : 'staff');
  addTearDown(setup.container.dispose);
  useTallView(tester, height: 1800);
  await pushOnHome<Object?>(tester, setup, path);
  return setup;
}

AppChoiceChip _chip(WidgetTester tester, String label) =>
    tester.widget<AppChoiceChip>(find.widgetWithText(AppChoiceChip, label));

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder);
  await tester.tap(finder);
  await settle(tester);
}

AppButton _saveButton(WidgetTester tester) => tester.widget<AppButton>(find.byKey(FormTextEdit.saveKey));

void main() {
  testWidgets('설정을 건드리지 않은 매장은 기본값이 골라져 있고 줄마다 무슨 일이 생기는지 적혀 있다', (tester) async {
    await _open(tester, _Server());

    expect(find.byKey(ScreenKeys.formSettings), findsOneWidget);
    expect(_chip(tester, '14일').selected, isTrue);
    expect(_chip(tester, '10살').selected, isTrue);
    expect(_chip(tester, '1년').selected, isTrue);
    expect(find.text(AppStrings.formLinkDaysHint(14)), findsOneWidget);
    expect(find.text(AppStrings.formSeniorAgeHint(10)), findsOneWidget);
    expect(find.text(AppStrings.formConsentDaysHint(365)), findsOneWidget);
    for (final title in [AppStrings.consentPartTitleBasic, AppStrings.consentPartTitleSenior, AppStrings.consentPartTitleCondition]) {
      expect(find.text(title), findsOneWidget);
    }
    expect(find.text(AppStrings.formPartWhenSenior(10)), findsOneWidget);
    expect(find.text(AppStrings.formEdited), findsNothing);
  });

  testWidgets('칩을 누르면 다섯 칸 전체를 보내고 다시 읽은 값으로 그린다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.widgetWithText(AppChoiceChip, '8살'));

    expect(server.puts.single, {
      'link_days': 14, 'senior_age': 8, 'consent_days': 365, 'reservation_text': null, 'consent_text': null,
      'intake_keep_days': 30, 'intake_hidden': <String>[],
    });
    expect(_chip(tester, '8살').selected, isTrue);
    expect(find.text(AppStrings.formPartWhenSenior(8)), findsOneWidget);
  });

  testWidgets('칩에 없는 값은 직접 정하고, 범위 밖이면 보내지 않고 그 자리에서 말한다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    await _tap(tester, find.byKey(const ValueKey('form-custom-link_days')));
    await tester.enterText(find.byKey(const ValueKey('form-custom-input')), '45');
    await _tap(tester, find.byKey(const ValueKey('form-custom-save')));
    expect(find.text(AppStrings.formRangeNotice(1, 30)), findsOneWidget);
    expect(server.puts, isEmpty);

    await tester.enterText(find.byKey(const ValueKey('form-custom-input')), '21');
    await _tap(tester, find.byKey(const ValueKey('form-custom-save')));

    expect(server.puts.single['link_days'], 21);
    expect(_chip(tester, '21일').selected, isTrue);       // 지금 값이 칩에 없으면 그 값의 칩이 보인다
  });

  testWidgets('저장이 거절되면 그 자리에서 말하고 값은 다시 읽은 것으로 남는다', (tester) async {
    final server = _Server()
      ..putError = const FakeResponse(statusCode: 403, data: {'code': 'PERMISSION_DENIED', 'message': 'x'});
    await _open(tester, server);

    await _tap(tester, find.widgetWithText(AppChoiceChip, '7일'));

    expect(_chip(tester, '14일').selected, isTrue);
    expect(find.byKey(const ValueKey('form-settings-notice')), findsOneWidget);
  });

  testWidgets('직원에게는 읽기 전용이다 — 칩이 눌리지 않고 글은 볼 수만 있다', (tester) async {
    final server = _Server();
    await _open(tester, server, owner: false);

    expect(find.text(AppStrings.reportSettingsOwnerOnly), findsOneWidget);
    expect(_chip(tester, '7일').onTap, isNull);
    await _tap(tester, find.text(AppStrings.consentPartTitleSenior));
    expect(find.byKey(ScreenKeys.formTextEdit), findsOneWidget);
    expect(find.byKey(FormTextEdit.saveKey), findsNothing);
    expect(tester.widget<TextField>(find.byKey(FormTextEdit.inputKey)).readOnly, isTrue);
  });

  testWidgets('토막의 글을 고치면 보호자가 받는 모습이 따라 바뀌고 저장하면 고침이 붙는다', (tester) async {
    final server = _Server();
    await _open(tester, server);
    await _tap(tester, find.text(AppStrings.consentPartTitleSenior));

    expect(tester.widget<TextField>(find.byKey(FormTextEdit.inputKey)).controller!.text, 'senior 의 기본 글');
    expect(_saveButton(tester).onPressed, isNull);                 // 바꾼 것이 없다
    await tester.enterText(find.byKey(FormTextEdit.inputKey), '쉬어 가며 미용해요.');
    await tester.pump();
    expect(find.descendant(of: find.byKey(FormTextEdit.previewKey), matching: find.text('쉬어 가며 미용해요.')), findsOneWidget);
    await _tap(tester, find.byKey(FormTextEdit.saveKey));

    expect(server.textPuts, [('senior', '쉬어 가며 미용해요.')]);
    expect(find.byKey(ScreenKeys.formSettings), findsOneWidget);
    expect(find.byKey(ScreenKeys.formTextEdit), findsNothing);
    expect(find.text(AppStrings.formEdited), findsOneWidget);
  });

  testWidgets('빈 글로는 저장할 수 없고 기본 글로 되돌릴 수 있다', (tester) async {
    final server = _Server()..texts = consentTextsJson(senior: '고친 글');
    await _open(tester, server, path: '/settings/forms/text/senior');

    await tester.enterText(find.byKey(FormTextEdit.inputKey), '   ');
    await tester.pump();
    expect(_saveButton(tester).onPressed, isNull);
    expect(find.text(AppStrings.formTextEmpty), findsOneWidget);

    await _tap(tester, find.byKey(FormTextEdit.resetKey));

    expect(server.textPuts, [('senior', null)]);
  });

  testWidgets('고치다가 뒤로 가면 한 번 묻고, 저장이 실패하면 적은 글이 남는다', (tester) async {
    final server = _Server()
      ..putError = const FakeResponse(statusCode: 422, data: {'code': 'VALIDATION_ERROR', 'message': 'x'});
    await _open(tester, server, path: '/settings/forms/text/basic');
    await tester.enterText(find.byKey(FormTextEdit.inputKey), '우리 가게의 글');
    await tester.pump();

    await _tap(tester, find.byKey(FormTextEdit.saveKey));
    expect(find.byKey(ScreenKeys.formTextEdit), findsOneWidget);
    expect(tester.widget<TextField>(find.byKey(FormTextEdit.inputKey)).controller!.text, '우리 가게의 글');
    expect(find.byKey(FormTextEdit.noticeKey), findsOneWidget);

    await _tap(tester, find.bySemanticsLabel(AppStrings.back).last);
    expect(find.text(AppStrings.formLeaveAsk), findsOneWidget);
    await _tap(tester, find.text(AppStrings.formLeaveStay));
    expect(find.byKey(ScreenKeys.formTextEdit), findsOneWidget);
  });

  testWidgets('보내는 글은 자리 칩을 눌러 넣고 보호자가 받는 모습을 예시로 보인다', (tester) async {
    final server = _Server();
    await _open(tester, server, path: '/settings/forms/message/reservation');

    final input = find.byKey(FormTextEdit.inputKey);
    expect(tester.widget<TextField>(input).controller!.text, defaultReservationText);
    await tester.enterText(input, '예약 확인했어요 ');
    await tester.pump();
    await _tap(tester, find.byKey(const ValueKey('form-slot-{날짜}')));

    expect(tester.widget<TextField>(input).controller!.text, '예약 확인했어요 {날짜}');
    expect(find.descendant(of: find.byKey(FormTextEdit.previewKey), matching: find.textContaining('{')), findsNothing);
    expect(find.byKey(const ValueKey('form-slot-{링크}')), findsNothing);       // 예약 안내에는 링크가 없다
    await _tap(tester, find.byKey(FormTextEdit.saveKey));

    expect(server.puts.single['reservation_text'], '예약 확인했어요 {날짜}');
    expect(server.puts.single['link_days'], 14);
  });

  testWidgets('동의서를 보내는 글에서 링크 자리를 빼거나 모르는 자리를 적으면 저장되지 않고 까닭을 말한다', (tester) async {
    final server = _Server();
    await _open(tester, server, path: '/settings/forms/message/consent');

    await tester.enterText(find.byKey(FormTextEdit.inputKey), '동의서를 읽어 주세요');
    await tester.pump();
    expect(_saveButton(tester).onPressed, isNull);
    expect(find.text(AppStrings.formLinkSlotMissing), findsOneWidget);

    await tester.enterText(find.byKey(FormTextEdit.inputKey), '{이름} 님 {링크}');
    await tester.pump();
    expect(_saveButton(tester).onPressed, isNull);
    expect(find.text(AppStrings.formUnknownSlot), findsOneWidget);
    expect(server.puts, isEmpty);
  });
}
