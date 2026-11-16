// 받은 문진표를 반려동물 폼의 처음 값으로 옮기는 계산(⑪-C) — 다시 치는 칸이 없다, 지어내지 않는다.
import 'package:chagocnote/features/customer/api/customer_models.dart';
import 'package:chagocnote/features/customer/api/intake_models.dart';
import 'package:chagocnote/features/customer/state/intake_prefill.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_fixtures.dart';
import '../../../support/intake_fixtures.dart';

IntakeAnswer _answer([Map<String, dynamic> change = const {}]) =>
    IntakeAnswer.fromJson({...intakeAnswerJson(), ...change});

void main() {
  test('다 찬 답은 그대로 등록할 값이 된다 — 메모는 초안이다', () {
    final fields = readyPetFields(_answer())!;

    expect((fields.name, fields.species, fields.breed, fields.sex, fields.neutered), ('모카', 'dog', '푸들', 'male', false));
    expect((fields.birthDate, fields.birthYear, fields.weightKg, fields.noKnownConditions), (null, 2022, 4.5, true));
    expect(fields.memo, '조심할 것: 드라이기 소리\n원하는 스타일: 곰돌이 컷');
    expect(readyCustomerFields(_answer())!.toJson(), {
      'name': '박새롬', 'phone': '01099990000', 'phone_alt': null, 'marketing_consent': false, 'memo': null,
    });
  });

  test('지병을 고른 답은 종류와 한 줄을 함께 옮긴다', () {
    final fields = readyPetFields(_answer({
      'no_known_conditions': false,
      'conditions': [
        {'type_code': 'heart_disease', 'label': '심장 질환', 'custom_label': null, 'note': '약 복용 중'},
        {'type_code': 'other', 'label': '기타', 'custom_label': '슬개골', 'note': null},
      ],
    }))!;

    expect(fields.noKnownConditions, isFalse);
    expect([for (final c in fields.conditions) (c.typeCode, c.customLabel, c.note)], [
      ('heart_disease', null, '약 복용 중'), ('other', '슬개골', null)]);
  });

  test('빈 필수 칸이 있거나 메모가 넘치면 곧바로 등록할 수 없다 — 지어내지 않는다', () {
    expect(readyPetFields(_answer({'weight_kg': null, 'missing': ['weight']})), isNull);
    expect(readyPetFields(_answer({'breed': null, 'missing': ['breed']})), isNull);
    expect(readyPetFields(_answer({'memo_over': 3})), isNull);
    expect(readyPetFields(_answer({'pet_name': null})), isNull);
    // 생일은 몰라요여도 된다(둘 다 비운다).
    final unknown = readyPetFields(_answer({'birth_year': null, 'birth_unknown': true}))!;
    expect((unknown.birthDate, unknown.birthYear), (null, null));
    // 보호자 이름·번호가 없는 답으로는 새 고객을 만들 수 없다.
    expect(readyCustomerFields(_answer({'guardian_phone': null})), isNull);
  });

  test('폼을 미리 채운다 — 빈 칸은 비워 둔다', () {
    final prefill = prefillOf(_answer({'weight_kg': null, 'breed': null, 'birth_year': null, 'birth_unknown': true}));

    expect((prefill.name, prefill.species, prefill.breed, prefill.weightKg), ('모카', 'dog', null, null));
    expect((prefill.birthUnknown, prefill.noKnownConditions, prefill.memo), (
      true, true, '조심할 것: 드라이기 소리\n원하는 스타일: 곰돌이 컷'));
  });

  test('다시 받은 답은 지금 값 위에 적어 낸 칸만 덮고, 메모는 덮지 않고 덧붙인다', () {
    final current = Pet.fromJson(petJson(petId: 11, name: '콩이', memo: '예민해요'));
    final answer = _answer({
      'mode': 'update', 'pet_id': 11, 'pet_name': '콩이', 'species': null, 'breed': null, 'sex': null,
      'neutered': null, 'birth_year': null, 'weight_kg': 5.1, 'no_known_conditions': null, 'dislikes': null,
      'style': '짧게', 'memo_draft': '원하는 스타일: 짧게',
    });

    final prefill = prefillOf(answer, current: current);

    expect((prefill.name, prefill.breed, prefill.species, prefill.weightKg), (
      current.name, current.breed, current.species, 5.1));
    expect(prefill.noKnownConditions, current.noKnownConditions);
    expect(prefill.memo, '예민해요\n원하는 스타일: 짧게');
    expect(prefill.changed, {'weight', 'memo'});
  });

  group('다시 받은 답의 지병', () {
    final current = Pet.fromJson(petJson(petId: 11, name: '콩이'));     // 슬개골 탈구(메모 2기)
    Map<String, dynamic> update(Map<String, dynamic> more) => {
      'mode': 'update', 'pet_id': 11, 'pet_name': '콩이', 'species': null, 'breed': null, 'sex': null,
      'neutered': null, 'birth_year': null, 'weight_kg': null, 'dislikes': null, 'style': null, 'memo_draft': '', ...more,
    };

    test('새로 적은 지병은 기존 지병 위에 더한다 — 매장이 적어 둔 지병과 메모는 남는다', () {
      final prefill = prefillOf(_answer(update({
        'no_known_conditions': false,
        'conditions': [{'type_code': 'skin', 'label': '피부 질환', 'custom_label': null, 'note': '발 사이'}],
      })), current: current);

      expect([for (final c in prefill.conditions) (c.typeCode, c.note)], [('patella_luxation', '2기'), ('skin', '발 사이')]);
      expect(prefill.noKnownConditions, isFalse);
      expect(prefill.changed, {'conditions'});
    });

    test('같은 지병을 다시 적으면 답의 메모로 바뀌고, 메모 없이 적었으면 기존 메모가 남는다', () {
      List<(String, String?)> merged(String? note) => [
        for (final c in prefillOf(_answer(update({
          'no_known_conditions': false,
          'conditions': [{'type_code': 'patella_luxation', 'label': '슬개골 탈구', 'custom_label': null, 'note': note}],
        })), current: current).conditions) (c.typeCode, c.note),
      ];

      expect(merged('3기로 진행'), [('patella_luxation', '3기로 진행')]);
      expect(merged(null), [('patella_luxation', '2기')]);
    });

    test('지금 값과 같은 답은 바뀐 칸으로 치지 않는다', () {
      final prefill = prefillOf(_answer(update({
        'no_known_conditions': false,
        'conditions': [{'type_code': 'patella_luxation', 'label': '슬개골 탈구', 'custom_label': null, 'note': '2기'}],
      })), current: current);

      expect(prefill.changed, isEmpty);
    });

    test('없어요를 고르면 비우고 바뀐 칸으로 알린다', () {
      final prefill = prefillOf(_answer(update({'no_known_conditions': true, 'conditions': []})), current: current);

      expect(prefill.noKnownConditions, isTrue);
      expect(prefill.conditions, isEmpty);
      expect(prefill.changed, {'conditions'});
    });
  });
}
