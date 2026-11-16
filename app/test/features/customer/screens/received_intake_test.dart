// 받은 문진표(⑪-C) — 고객 탭의 줄, 목록, 한 장, [이대로 등록], 빈 칸만 채우는 폼, 다시 받은 답의 반영.
import 'dart:convert';

import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/customer/screens/received_intake_screens.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/intake_fixtures.dart';
import '../../../support/visit_test_backend.dart';

const _taken = FakeResponse(statusCode: 409, data: {'code': 'CUSTOMER_PHONE_TAKEN', 'message': 'x'});
const _gone = FakeResponse(statusCode: 404, data: {'code': 'INTAKE_ANSWER_NOT_FOUND', 'message': 'x'});

/// 받은 문진표를 답하는 가짜 서버. 등록·더하기·고치기가 성공하면 그 답이 목록에서 사라진다(서버가 지운다).
class _World {
  _World({List<Map<String, dynamic>>? answers, FakeResponse? listError, this.registerError, this.deleteError})
    : answers = answers ?? [intakeAnswerJson()] {
    Map<String, dynamic> body(List<int>? raw) => jsonDecode(utf8.decode(raw!)) as Map<String, dynamic>;
    FakeResponse saved(String call, List<int>? raw, FakeResponse ok) {
      final sent = body(raw);
      writes.add((call, sent));
      this.answers.removeWhere((a) => a['answer_id'] == sent['intake_answer_id']);
      return ok;
    }

    final base = VisitTestBackend({
      'GET /v1/shops/3/intake-answers': (o, b) => listError ?? FakeResponse(statusCode: 200, data: {'items': this.answers}),
      for (final id in [51, 52, 53])
        'GET /v1/shops/3/intake-answers/$id': (o, b) {
          final found = this.answers.where((a) => a['answer_id'] == id);
          return found.isEmpty ? _gone : FakeResponse(statusCode: 200, data: found.first);
        },
      'DELETE /v1/shops/3/intake-answers/51': (o, b) {
        if (deleteError != null) return deleteError!;
        this.answers.removeWhere((a) => a['answer_id'] == 51);
        return const FakeResponse(statusCode: 204);
      },
      'POST /v1/shops/3/customers': (o, b) {
        if (registerError != null) {
          writes.add(('register', body(b)));
          return registerError!;
        }
        return saved('register', b, FakeResponse(statusCode: 201, data: customerDetailJson()));
      },
      'POST /v1/shops/3/customers/7/pets': (o, b) => saved('addPet', b, FakeResponse(statusCode: 201, data: petDetailJson())),
      'PUT /v1/shops/3/pets/11': (o, b) => saved('updatePet', b, FakeResponse(statusCode: 200, data: petDetailJson())),
      'GET /v1/shops/3/pets/11': (o, b) =>
          FakeResponse(statusCode: 200, data: petDetailJson(pet: petJson(memo: '예민해요', noKnownConditions: true))),
      'GET /v1/shops/3/pet-condition-types': (o, b) => const FakeResponse(statusCode: 200, data: conditionTypesJson),
      'GET /v1/shops/3/customers/lookup': (o, b) =>
          const FakeResponse(statusCode: 200, data: {'customer_id': 7, 'name': '김민지', 'pet_names': ['콩이']}),
    });
    setup = CustomerTestSetup(base.call);
  }

  final List<Map<String, dynamic>> answers;
  final FakeResponse? registerError;
  final FakeResponse? deleteError;
  final writes = <(String, Map<String, dynamic>)>[];
  late final CustomerTestSetup setup;

  Future<void> open(WidgetTester tester, String path) async {
    useTallView(tester, height: 2200);
    addTearDown(setup.container.dispose);
    await pushOnHome<Object?>(tester, setup, path);
  }
}

Future<void> _tap(WidgetTester tester, Finder finder) async {
  await tester.ensureVisible(finder.first);
  await tester.tap(finder.first);
  await settle(tester);
}

AppButton _button(WidgetTester tester, Key key) => tester.widget<AppButton>(find.byKey(key));

void main() {
  testWidgets('고객 탭에는 받은 문진표가 있을 때만 줄이 있고 누르면 목록으로 간다', (tester) async {
    final world = _World(answers: [intakeAnswerJson(), intakeAnswerJson(answerId: 52, petName: '라떼')]);
    await world.open(tester, '/home');
    await _tap(tester, find.text(AppStrings.tabCustomers));

    await _tap(tester, find.text(AppStrings.receivedIntakeEntry(2)));

    expect(find.byKey(ScreenKeys.receivedIntake), findsOneWidget);
    expect(find.text('모카'), findsOneWidget);
    expect(find.text('라떼'), findsOneWidget);
    expect(find.text(AppStrings.receivedIntakeMeta('박새롬', DateTime(2026, 11, 16))), findsNWidgets(2));
  });

  testWidgets('받은 문진표가 없거나 읽지 못하면 고객 탭에 줄이 없다', (tester) async {
    for (final world in [
      _World(answers: []),
      _World(listError: const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL_ERROR', 'message': 'x'})),
    ]) {
      await world.open(tester, '/home');
      await _tap(tester, find.text(AppStrings.tabCustomers));
      expect(find.textContaining('받은 문진표'), findsNothing);
      await tester.pumpWidget(const SizedBox());
    }
  });

  testWidgets('한 장의 등록 버튼은 굴리지 않아도 보이고(누르기 두 번), 답의 카드는 폭을 채운다', (tester) async {
    final world = _World();
    await world.open(tester, '/intake-answers/51');
    tester.view.physicalSize = const Size(390, 700) * tester.view.devicePixelRatio;   // 보통 폰 — 답이 화면보다 길다
    await settle(tester);

    final button = tester.getRect(find.byKey(IntakeAnswerScreen.registerKey));
    expect(button.bottom, lessThanOrEqualTo(700));
    expect(find.byKey(IntakeAnswerScreen.registerKey).hitTestable(), findsOneWidget);
    final card = tester.getSize(find.byKey(const ValueKey('intake-section-${AppStrings.intakeSectionPet}')));
    expect(card.width, greaterThan(300));
  });

  testWidgets('한 장은 보호자가 적은 답을 그대로 보이고, 다 찼으면 [이대로 등록] 한 번으로 새 고객이 된다', (tester) async {
    final world = _World(answers: [intakeAnswerJson(extras: [{'label': '산책은 얼마나 하나요?', 'body': '하루 한 번'}])]);
    await world.open(tester, '/intake-answers');

    await _tap(tester, find.byKey(const ValueKey('intake-answer-51')));       // 누르기 1
    expect(find.byKey(ScreenKeys.intakeAnswer), findsOneWidget);
    for (final text in ['박새롬', '010-9999-0000', '모카', '푸들', '2022년생', '4.5kg', AppStrings.intakeNoConditions,
      '드라이기 소리', '곰돌이 컷', '산책은 얼마나 하나요?', '하루 한 번', AppStrings.intakeTargetNew('박새롬')]) {
      expect(find.text(text), findsOneWidget, reason: text);
    }
    expect(_button(tester, IntakeAnswerScreen.registerKey).label, AppStrings.intakeRegisterNow);

    await _tap(tester, find.byKey(IntakeAnswerScreen.registerKey));           // 누르기 2

    final (call, sent) = world.writes.single;
    expect(call, 'register');
    expect(sent['intake_answer_id'], 51);
    expect(sent['customer'], {'name': '박새롬', 'phone': '01099990000', 'phone_alt': null, 'marketing_consent': false, 'memo': null});
    expect((sent['pet'] as Map)['name'], '모카');
    expect((sent['pet'] as Map)['memo'], '조심할 것: 드라이기 소리\n원하는 스타일: 곰돌이 컷');
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('번호가 같은 고객이 미리 이어져 있으면 그 고객의 새 아이로 더한다', (tester) async {
    final world = _World(answers: [intakeAnswerJson(matchedCustomer: {'customer_id': 7, 'name': '김민지'})]);
    await world.open(tester, '/intake-answers/51');

    expect(find.text(AppStrings.intakeTargetMatched('김민지')), findsOneWidget);
    await _tap(tester, find.byKey(IntakeAnswerScreen.registerKey));

    final (call, sent) = world.writes.single;
    expect((call, sent['intake_answer_id'], sent['name']), ('addPet', 51, '모카'));
  });

  testWidgets('빈 필수 칸이 있으면 지어내지 않고 그 칸만 채우는 폼으로 간다', (tester) async {
    final world = _World(answers: [intakeAnswerJson(breed: null, weightKg: null, missing: ['breed', 'weight'])]);
    await world.open(tester, '/intake-answers/51');

    expect(find.text(AppStrings.intakeMissing('품종 · 몸무게')), findsOneWidget);
    expect(_button(tester, IntakeAnswerScreen.registerKey).label, AppStrings.intakeFillAndRegister);
    expect(find.byKey(IntakeAnswerScreen.editKey), findsNothing);
    await _tap(tester, find.byKey(IntakeAnswerScreen.registerKey));

    expect(find.byKey(ScreenKeys.intakeRegister), findsOneWidget);
    expect(world.writes, isEmpty);
    TextField field(String label) => tester.widget<TextField>(find.widgetWithText(TextField, label));
    expect(field(AppStrings.petNameLabel).controller!.text, '모카');           // 답이 채워져 있다
    expect(field(AppStrings.breedLabel).controller!.text, '');                // 빈 칸은 비어 있다
    expect(field(AppStrings.weightLabel).controller!.text, '');

    await tester.enterText(find.widgetWithText(TextField, AppStrings.breedLabel), '푸들');
    await tester.enterText(find.widgetWithText(TextField, AppStrings.weightLabel), '4.5');
    await _tap(tester, find.widgetWithText(AppButton, AppStrings.save));

    final (call, sent) = world.writes.single;
    expect((call, sent['intake_answer_id']), ('register', 51));
    expect(((sent['pet'] as Map)['breed'], (sent['pet'] as Map)['weight_kg']), ('푸들', 4.5));
  });

  testWidgets('다른 기기가 먼저 등록했으면 알리고 목록으로 돌아간다 — 고객이 둘 생기지 않는다', (tester) async {
    final world = _World(registerError: _gone);
    await world.open(tester, '/intake-answers/51');

    await _tap(tester, find.byKey(IntakeAnswerScreen.registerKey));

    expect(find.text(AppStrings.intakeGone), findsOneWidget);
    expect(find.byKey(ScreenKeys.intakeAnswer), findsNothing);
    expect(world.writes, hasLength(1));
  });

  testWidgets('그 번호의 고객이 그 사이 등록됐으면 그 고객의 새 아이로 더할지 묻는다', (tester) async {
    final world = _World(registerError: _taken);
    await world.open(tester, '/intake-answers/51');

    await _tap(tester, find.byKey(IntakeAnswerScreen.registerKey));
    expect(find.text(AppStrings.intakePhoneTaken('김민지')), findsOneWidget);
    await _tap(tester, find.text(AppStrings.intakeAddToExisting));

    expect([for (final (call, _) in world.writes) call], ['register', 'addPet']);
    expect(world.writes.last.$2['intake_answer_id'], 51);
    expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
  });

  testWidgets('[지우기]는 한 번 묻고, 지우면 목록으로 돌아가 줄이 없다', (tester) async {
    final world = _World();
    await world.open(tester, '/intake-answers');
    await _tap(tester, find.byKey(const ValueKey('intake-answer-51')));

    await _tap(tester, find.byKey(IntakeAnswerScreen.deleteKey));
    expect(find.text(AppStrings.intakeDeleteAsk), findsOneWidget);
    await _tap(tester, find.text(AppStrings.intakeKeep));
    expect(world.answers, hasLength(1));

    await _tap(tester, find.byKey(IntakeAnswerScreen.deleteKey));
    await _tap(tester, find.text(AppStrings.intakeDeleteConfirm).last);

    expect(world.answers, isEmpty);
    expect(find.byKey(ScreenKeys.receivedIntake), findsOneWidget);
    expect(find.text(AppStrings.receivedIntakeEmpty), findsOneWidget);
  });

  testWidgets('지우기가 실패하면 그 자리에서 말하고 한 장이 남는다', (tester) async {
    final world = _World(deleteError: const FakeResponse(statusCode: 500, data: {'code': 'INTERNAL_ERROR', 'message': 'x'}));
    await world.open(tester, '/intake-answers/51');

    await _tap(tester, find.byKey(IntakeAnswerScreen.deleteKey));
    await _tap(tester, find.text(AppStrings.intakeDeleteConfirm).last);

    expect(find.byKey(ScreenKeys.intakeAnswer), findsOneWidget);
    expect(world.answers, hasLength(1));
    expect(_button(tester, IntakeAnswerScreen.deleteKey).onPressed, isNotNull);
  });

  testWidgets('다시 받은 답은 지금 값 위에 적어 낸 칸만 덮어 채우고 메모는 덧붙인다', (tester) async {
    final world = _World(answers: [
      intakeAnswerJson(
        mode: 'update', petId: 11, petName: '콩이', guardianName: null, guardianPhone: null,
        matchedCustomer: {'customer_id': 7, 'name': '김민지'}, species: null, breed: null, sex: null, neutered: null,
        birthYear: null, weightKg: 5.1, noKnownConditions: null, dislikes: null, style: '짧게',
        memoDraft: '원하는 스타일: 짧게',
      ),
    ]);
    await world.open(tester, '/intake-answers/51');

    expect(find.text(AppStrings.intakeTargetUpdate('콩이')), findsOneWidget);
    expect(find.text(AppStrings.intakeNotAnswered), findsNothing);      // 적지 않은 칸은 줄이 없다
    expect(_button(tester, IntakeAnswerScreen.registerKey).label, AppStrings.intakeApply);
    await _tap(tester, find.byKey(IntakeAnswerScreen.registerKey));

    expect(find.byKey(ScreenKeys.intakeRegister), findsOneWidget);
    expect(find.text(AppStrings.intakeChangedFields('몸무게 · 메모')), findsOneWidget);
    TextField field(String label) => tester.widget<TextField>(find.widgetWithText(TextField, label));
    expect(field(AppStrings.weightLabel).controller!.text, '5.1');
    expect(field(AppStrings.breedLabel).controller!.text, '말티즈');            // 지금 값 그대로
    expect(field(AppStrings.petMemoLabel).controller!.text, '예민해요\n원하는 스타일: 짧게');

    await _tap(tester, find.widgetWithText(AppButton, AppStrings.save));

    final (call, sent) = world.writes.single;
    expect((call, sent['intake_answer_id'], sent['weight_kg'], sent['memo']), ('updatePet', 51, 5.1, '예민해요\n원하는 스타일: 짧게'));
  });

  testWidgets('넘친 메모는 폼에서 잘리지 않는다 — 넘친 글자 수를 보이고, 줄이기 전에는 보내지 않는다', (tester) async {
    final long = '가' * 520;
    final world = _World(answers: [intakeAnswerJson(memoDraft: long, memoOver: 20)]);
    await world.open(tester, '/intake-answers/51/register');
    TextField memo() => tester.widget<TextField>(find.widgetWithText(TextField, AppStrings.petMemoLabel));

    expect(memo().controller!.text.length, 520);
    expect(find.text(AppStrings.petMemoOver(20)), findsOneWidget);

    await tester.enterText(find.widgetWithText(TextField, AppStrings.petMemoLabel), '가' * 510);   // 고쳐도 뒤가 잘리지 않는다
    await settle(tester);
    expect(memo().controller!.text.length, 510);
    expect(find.text(AppStrings.petMemoOver(10)), findsOneWidget);
    await _tap(tester, find.widgetWithText(AppButton, AppStrings.save));
    expect(world.writes, isEmpty);

    await tester.enterText(find.widgetWithText(TextField, AppStrings.petMemoLabel), '가' * 500);
    await settle(tester);
    expect(find.textContaining('넘쳐요'), findsNothing);
    await _tap(tester, find.widgetWithText(AppButton, AppStrings.save));
    expect((world.writes.single.$2['pet'] as Map)['memo'], '가' * 500);
  });

  testWidgets('고객 탭을 당겨 새로 읽으면 그 사이 받은 문진표의 줄이 생긴다', (tester) async {
    final world = _World(answers: []);
    await world.open(tester, '/home');
    await _tap(tester, find.text(AppStrings.tabCustomers));
    expect(find.textContaining('받은 문진표'), findsNothing);

    world.answers.add(intakeAnswerJson());
    tester.view.physicalSize = const Size(390, 844);   // 당김의 문턱은 화면 높이의 1/4 이다 — 긴 화면에서는 닿지 않는다
    await settle(tester);
    await tester.fling(find.textContaining('두부').hitTestable().first, const Offset(0, 400), 1000);
    await settle(tester);

    expect(find.text(AppStrings.receivedIntakeEntry(1)), findsOneWidget);
  });

  testWidgets('문진표 끝에서 서명했으면 한 장에 미용 동의서 줄이 있고 등록하면 그 아이의 동의가 된다고 적혀 있다', (tester) async {
    final world = _World(answers: [
      intakeAnswerJson(consent: {'signed_on': '2026-11-16', 'parts': ['basic', 'senior']}),
      intakeAnswerJson(answerId: 52, petName: '라떼'),
    ]);
    await world.open(tester, '/intake-answers/51');

    expect(find.text(AppStrings.intakeSectionConsent), findsOneWidget);
    expect(find.text(AppStrings.intakeConsentSigned(DateTime(2026, 11, 16))), findsOneWidget);
    expect(find.text('미용 안내 · 나이가 많은 아이'), findsOneWidget);
    expect(find.text(AppStrings.intakeConsentNote), findsOneWidget);
  });

  testWidgets('서명이 없는 답에는 미용 동의서 줄이 없다', (tester) async {
    final world = _World();
    await world.open(tester, '/intake-answers/51');

    expect(find.text(AppStrings.intakeSectionConsent), findsNothing);
  });
}
