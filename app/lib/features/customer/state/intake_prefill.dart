/// 받은 문진표를 등록 화면의 처음 값으로 옮기는 계산(⑪-C). 순수 함수 — 다시 치는 칸이 없게 하되
/// **빈 칸을 지어내지 않는다**(끈 칸·모르겠어요는 비워 두고 사장이 채운다).
/// ⑯ 의 글 붙여넣기도 이 형([PetPrefill])을 쓴다.
library;

import '../api/customer_models.dart';
import '../api/intake_models.dart';
import 'customer_input.dart';

/// 반려동물 폼의 처음 값. 비어 있는 칸은 `null` 이다.
class PetPrefill {
  const PetPrefill({
    this.name,
    this.species,
    this.breed,
    this.sex,
    this.neutered,
    this.birthDate,
    this.birthYear,
    this.birthUnknown = false,
    this.weightKg,
    this.noKnownConditions,
    this.conditions = const [],
    this.memo,
    this.changed = const {},
  });

  final String? name;
  final String? species;
  final String? breed;
  final String? sex;
  final bool? neutered;
  final DateTime? birthDate;
  final int? birthYear;
  final bool birthUnknown; // 나이 모름을 골라 둔다
  final double? weightKg;
  final bool? noKnownConditions;
  final List<ConditionEntry> conditions;
  final String? memo;

  /// 다시 받은 답이 지금 값과 다르게 채운 칸의 코드 — 폼이 무엇이 답에서 왔는지 보인다.
  final Set<String> changed;
}

List<ConditionEntry> _conditions(IntakeAnswer answer) => [
  for (final c in answer.conditions) ConditionEntry(typeCode: c.typeCode, customLabel: c.customLabel, note: c.note),
];

String? _text(String? value) => (value == null || value.trim().isEmpty) ? null : value;

/// 폼을 미리 채울 값. [current] 가 있으면(다시 받기) 지금 값 위에 **적어 낸 칸만** 덮는다 —
/// 기존 메모는 덮지 않고 답의 초안을 아래에 덧붙인다.
PetPrefill prefillOf(IntakeAnswer answer, {Pet? current}) {
  final draft = _text(answer.memoDraft);
  if (current == null) {
    return PetPrefill(
      name: answer.petName,
      species: answer.species,
      breed: answer.breed,
      sex: answer.sex,
      neutered: answer.neutered,
      birthDate: answer.birthDate,
      birthYear: answer.birthYear,
      birthUnknown: answer.birthUnknown,
      weightKg: answer.weightKg,
      noKnownConditions: answer.noKnownConditions,
      conditions: _conditions(answer),
      memo: draft,
    );
  }
  final changed = <String>{};
  T pick<T>(String code, T? answered, T now) {
    if (answered == null || answered == now) return now;
    changed.add(code);
    return answered;
  }

  final birthAnswered = answer.birthDate != null || answer.birthYear != null || answer.birthUnknown;
  if (birthAnswered && (answer.birthDate != current.birthDate || answer.birthYear != current.birthYear)) {
    changed.add('birth');
  }
  final conditionsAnswered = answer.noKnownConditions != null;
  if (conditionsAnswered) changed.add('conditions');
  final memo = draft == null ? current.memo : [?_text(current.memo), draft].join('\n');
  if (draft != null) changed.add('memo');
  return PetPrefill(
    name: pick('name', _text(answer.petName), current.name),
    species: pick('species', answer.species, current.species),
    breed: pick('breed', _text(answer.breed), current.breed),
    sex: pick('sex', answer.sex, current.sex),
    neutered: pick('neutered', answer.neutered, current.neutered),
    birthDate: birthAnswered ? answer.birthDate : current.birthDate,
    birthYear: birthAnswered ? answer.birthYear : current.birthYear,
    birthUnknown: birthAnswered ? answer.birthUnknown : (current.birthDate == null && current.birthYear == null),
    weightKg: pick('weight', answer.weightKg, current.weightKg),
    noKnownConditions: conditionsAnswered ? answer.noKnownConditions : current.noKnownConditions,
    conditions: conditionsAnswered
        ? _conditions(answer)
        : [
            for (final c in current.conditions)
              ConditionEntry(typeCode: c.typeCode, customLabel: c.customLabel, note: c.note),
          ],
    memo: memo,
    changed: changed,
  );
}

/// 곧바로 등록할 수 있는 값. 빈 필수 칸이 있거나 메모가 넘치면 `null` — 폼에서 채운다.
PetFields? readyPetFields(IntakeAnswer answer) {
  final name = _text(answer.petName);
  final breed = _text(answer.breed);
  if (answer.missing.isNotEmpty || answer.memoOver > 0 || name == null) return null;
  if (answer.species == null || breed == null || answer.sex == null || answer.neutered == null) return null;
  if (answer.weightKg == null || answer.noKnownConditions == null) return null;
  return PetFields(
    name: name,
    species: answer.species!,
    breed: breed,
    sex: answer.sex!,
    neutered: answer.neutered!,
    birthDate: answer.birthDate,
    birthYear: answer.birthYear,
    weightKg: answer.weightKg!,
    noKnownConditions: answer.noKnownConditions!,
    conditions: _conditions(answer),
    memo: _text(answer.memoDraft),
  );
}

/// 새 고객으로 곧바로 등록할 보호자 값. 이름이나 번호가 없으면 `null`. 마케팅 수신 동의는 받지 않았다 — 끈다.
CustomerFields? readyCustomerFields(IntakeAnswer answer) {
  final name = _text(answer.guardianName);
  final digits = phoneDigits(answer.guardianPhone ?? '');
  if (name == null || !isValidPhone(digits)) return null;
  return CustomerFields(name: name, phone: digits, phoneAlt: null, marketingConsent: false, memo: null);
}
