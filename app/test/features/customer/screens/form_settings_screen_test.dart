// 서류 설정(⑪-B) — 동의서의 글·보내는 글·기준값을 매장이 자기 가게에 맞게 고친다.
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/features/customer/screens/form_text_edit_screens.dart';
import 'package:chagocnote/features/customer/screens/intake_questions_screen.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/form_settings_fixtures.dart';
import '../../../support/intake_fixtures.dart';
import '../../../support/visit_test_backend.dart';

const _settings = '/v1/shops/3/form-settings';
const _texts = '/v1/shops/3/consent-texts';
const _questions = '/v1/shops/3/intake-questions';

/// 서류 설정 서버 — 받은 본문을 적고 그대로 저장해 돌려준다. [putError] 가 있으면 저장하지 않는다.
class _Server {
  Map<String, dynamic> settings = formSettingsJson();
  Map<String, dynamic> texts = consentTextsJson();
  FakeResponse? putError;
  final puts = <Map<String, dynamic>>[];
  final textPuts = <(String, Object?)>[];
  List<Map<String, dynamic>> questions = [];
  final questionPuts = <List<Map<String, dynamic>>>[];

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
    'GET $_questions': (o, b) => FakeResponse(statusCode: 200, data: {'items': questions}),
    'PUT $_questions': (o, body) {
      final sent = [...(bodyOf(body)['items'] as List).cast<Map<String, dynamic>>()];
      questionPuts.add(sent);
      if (putError case final error?) return error;
      var next = 100;
      questions = [
        for (final q in sent) intakeQuestionJson(q['question_id'] as int? ?? next++, q['label'] as String, required: q['required'] as bool),
      ];
      return FakeResponse(statusCode: 200, data: {'items': questions});
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

    await _tap(tester, find.widgetWithText(AppChoiceChip, '7일').first);   // 링크 기간(뒤의 것은 문진표 보관)

    expect(_chip(tester, '14일').selected, isTrue);
    expect(find.byKey(const ValueKey('form-settings-notice')), findsOneWidget);
  });

  testWidgets('직원에게는 읽기 전용이다 — 칩이 눌리지 않고 글은 볼 수만 있다', (tester) async {
    final server = _Server();
    await _open(tester, server, owner: false);

    expect(find.text(AppStrings.reportSettingsOwnerOnly), findsOneWidget);
    expect(tester.widget<AppChoiceChip>(find.widgetWithText(AppChoiceChip, '7일').first).onTap, isNull);
    expect(tester.widget<AppSwitch>(find.byKey(const ValueKey('intake-field-breed'))).onChanged, isNull);
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

  // ── 문진표(⑪-C) ──────────────────────────────────────────────────────────
  testWidgets('문진표의 칸을 끄면 끈 칸의 목록과 함께 전체를 보내고, 끌 수 없는 칸은 까닭과 함께 적혀 있다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    expect(find.text(AppStrings.formIntakeAlways), findsOneWidget);
    expect(tester.widget<AppSwitch>(find.byKey(const ValueKey('intake-field-weight'))).value, isTrue);
    await _tap(tester, find.byKey(const ValueKey('intake-field-weight')));
    await _tap(tester, find.byKey(const ValueKey('intake-field-style')));

    expect(server.puts.last['intake_hidden'], ['weight', 'style']);
    expect(server.puts.last['link_days'], 14);                  // 다른 칸은 지금 값 그대로
    expect(tester.widget<AppSwitch>(find.byKey(const ValueKey('intake-field-weight'))).value, isFalse);

    await _tap(tester, find.byKey(const ValueKey('intake-field-weight')));   // 다시 켠다
    expect(server.puts.last['intake_hidden'], ['style']);
  });

  testWidgets('확인하지 않은 문진표를 지우는 때는 칩으로 고르고 직접 정할 수도 있다', (tester) async {
    final server = _Server();
    await _open(tester, server);

    expect(find.text(AppStrings.formIntakeKeepHint(30)), findsOneWidget);
    await _tap(tester, find.widgetWithText(AppChoiceChip, '90일'));
    expect(server.puts.single['intake_keep_days'], 90);
    expect(find.text(AppStrings.formIntakeKeepHint(90)), findsOneWidget);

    await _tap(tester, find.byKey(const ValueKey('form-custom-intake_keep_days')));
    await tester.enterText(find.byKey(const ValueKey('form-custom-input')), '0');
    await _tap(tester, find.byKey(const ValueKey('form-custom-save')));
    expect(server.puts, hasLength(1));                           // 범위 밖은 보내지 않는다
  });

  testWidgets('매장이 더한 질문 — 더하고 꼭 답하기를 켜고 저장하면 목록 전체를 보내고 설정으로 돌아와 개수가 보인다', (tester) async {
    final server = _Server()..questions = [intakeQuestionJson(1, '산책은 얼마나 하나요?')];
    await _open(tester, server);

    await _tap(tester, find.text(AppStrings.formIntakeQuestions(1)));
    expect(find.byKey(ScreenKeys.intakeQuestions), findsOneWidget);
    expect(tester.widget<AppButton>(find.byKey(IntakeQuestionsScreen.saveKey)).onPressed, isNull);   // 바꾼 것이 없다

    await _tap(tester, find.byKey(IntakeQuestionsScreen.addKey));
    await tester.enterText(find.byKey(const ValueKey('intake-question-1')), ' 다른 아이와 잘 지내나요? ');
    await _tap(tester, find.byKey(const ValueKey('intake-question-required-1')));
    await _tap(tester, find.byKey(IntakeQuestionsScreen.saveKey));

    expect(server.questionPuts.single, [
      {'question_id': 1, 'label': '산책은 얼마나 하나요?', 'required': false},
      {'question_id': null, 'label': '다른 아이와 잘 지내나요?', 'required': true},
    ]);
    expect(find.byKey(ScreenKeys.intakeQuestions), findsNothing);
    expect(find.text(AppStrings.formIntakeQuestions(2)), findsOneWidget);
  });

  testWidgets('질문을 고치고 지울 수 있다 — 지운 질문은 보내는 목록에서 빠진다', (tester) async {
    final server = _Server()
      ..questions = [intakeQuestionJson(1, '산책은 얼마나 하나요?'), intakeQuestionJson(2, '간식을 줘도 되나요?', required: true)];
    await _open(tester, server, path: '/settings/forms/questions');

    await _tap(tester, find.byKey(const ValueKey('intake-question-remove-0')));
    await tester.enterText(find.byKey(const ValueKey('intake-question-0')), '간식을 드려도 될까요?');
    await _tap(tester, find.byKey(IntakeQuestionsScreen.saveKey));

    expect(server.questionPuts.single, [
      {'question_id': 2, 'label': '간식을 드려도 될까요?', 'required': true},
    ]);
  });

  testWidgets('빈 질문은 보내지 않고 그 자리에서 말하고, 다섯 개가 차면 더할 수 없다', (tester) async {
    final server = _Server()..questions = [for (var i = 1; i <= 4; i++) intakeQuestionJson(i, '질문 $i')];
    await _open(tester, server, path: '/settings/forms/questions');

    await _tap(tester, find.byKey(IntakeQuestionsScreen.addKey));
    expect(tester.widget<AppButton>(find.byKey(IntakeQuestionsScreen.addKey)).onPressed, isNull);
    expect(find.text(AppStrings.intakeQuestionFull), findsOneWidget);
    expect(tester.widget<TextField>(find.byKey(const ValueKey('intake-question-4'))).maxLength, 100);

    await _tap(tester, find.byKey(IntakeQuestionsScreen.saveKey));
    expect(find.text(AppStrings.intakeQuestionEmpty), findsOneWidget);
    expect(server.questionPuts, isEmpty);
  });

  testWidgets('질문 저장이 실패하면 적은 것이 남고 그 자리에서 말한다', (tester) async {
    final server = _Server()
      ..putError = const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL', 'message': 'x'});
    await _open(tester, server, path: '/settings/forms/questions');

    await _tap(tester, find.byKey(IntakeQuestionsScreen.addKey));
    await tester.enterText(find.byKey(const ValueKey('intake-question-0')), '산책은 얼마나 하나요?');
    await _tap(tester, find.byKey(IntakeQuestionsScreen.saveKey));

    expect(find.byKey(ScreenKeys.intakeQuestions), findsOneWidget);
    expect(find.text('산책은 얼마나 하나요?'), findsOneWidget);
    expect(tester.widget<AppButton>(find.byKey(IntakeQuestionsScreen.saveKey)).busy, isFalse);
  });

  testWidgets('직원에게 질문은 읽기 전용이다 — 더하기·지우기·저장이 없다', (tester) async {
    final server = _Server()..questions = [intakeQuestionJson(1, '산책은 얼마나 하나요?')];
    await _open(tester, server, path: '/settings/forms/questions', owner: false);

    expect(find.text('산책은 얼마나 하나요?'), findsOneWidget);
    expect(tester.widget<TextField>(find.byKey(const ValueKey('intake-question-0'))).readOnly, isTrue);
    expect(tester.widget<AppSwitch>(find.byKey(const ValueKey('intake-question-required-0'))).onChanged, isNull);
    for (final key in [IntakeQuestionsScreen.addKey, IntakeQuestionsScreen.saveKey, const ValueKey('intake-question-remove-0')]) {
      expect(find.byKey(key), findsNothing);
    }
  });
}
