import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../design/tokens/app_spacing.dart';
import '../../../design/tokens/app_typography.dart';
import '../../../design/widgets/app_button.dart';
import '../../../design/widgets/app_card.dart';
import '../../../design/widgets/app_choice_chip.dart';
import '../../../design/widgets/pressable.dart';
import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';
import 'customer_labels.dart';

enum _AgeMode { birthDate, birthYear, unknown }

/// 기타 질병 한 줄(이름 + 메모).
class _OtherEntry {
  _OtherEntry({String label = '', String note = ''})
    : label = TextEditingController(text: label),
      note = TextEditingController(text: note);

  final TextEditingController label;
  final TextEditingController note;

  void dispose() {
    label.dispose();
    note.dispose();
  }
}

/// 반려동물 폼 — 등록 3단계, 반려동물 추가, 반려동물 수정이 함께 쓴다(설계 8.1).
///
/// 필수: 이름, 종류, 품종, 성별, 중성화, 나이(생일 / 태어난 해 / 모름),
/// 몸무게, 질병(하나 이상 또는 "질병 없음"). 특이사항만 선택이다. 입력 규칙을
/// 여기서 먼저 확인해 요청 없이 알려 주고, 통과하면 [onSubmit]에 넘긴다.
class PetForm extends StatefulWidget {
  const PetForm({
    super.key,
    required this.conditionTypes,
    required this.today,
    required this.submitLabel,
    required this.busy,
    required this.onSubmit,
    this.initial,
    this.errorText,
  });

  final List<ConditionType> conditionTypes;
  final DateTime today;
  final String submitLabel;
  final bool busy;
  final ValueChanged<PetFields> onSubmit;

  /// 수정할 때의 처음 값.
  final Pet? initial;

  /// 서버가 거절한 문구(부모가 준다).
  final String? errorText;

  @override
  State<PetForm> createState() => _PetFormState();
}

class _PetFormState extends State<PetForm> {
  final _name = TextEditingController();
  final _breed = TextEditingController();
  final _birthDate = TextEditingController();
  final _birthYear = TextEditingController();
  final _weight = TextEditingController();
  final _memo = TextEditingController();

  String? _species;
  String? _sex;
  bool? _neutered;
  _AgeMode? _ageMode;
  bool _noKnownConditions = false;

  /// 고른 정해진 질병(코드 → 메모 입력 칸). 칩 순서를 지키려고 삽입 순서를 쓴다.
  final Map<String, TextEditingController> _conditions = {};
  final List<_OtherEntry> _others = [];

  Map<String, String> _errors = {};

  @override
  void initState() {
    super.initState();
    final pet = widget.initial;
    if (pet == null) return;
    _name.text = pet.name;
    _breed.text = pet.breed;
    _species = pet.species;
    _sex = pet.sex;
    _neutered = pet.neutered;
    if (pet.birthDate != null) {
      _ageMode = _AgeMode.birthDate;
      _birthDate.text = formatDate(pet.birthDate!);
    } else if (pet.birthYear != null) {
      _ageMode = _AgeMode.birthYear;
      _birthYear.text = '${pet.birthYear}';
    } else {
      _ageMode = _AgeMode.unknown;
    }
    _weight.text = weightText(pet.weightKg);
    _memo.text = pet.memo ?? '';
    _noKnownConditions = pet.noKnownConditions;
    for (final c in pet.conditions) {
      if (c.typeCode == ConditionType.otherCode) {
        _others.add(
          _OtherEntry(label: c.customLabel ?? '', note: c.note ?? ''),
        );
      } else {
        _conditions[c.typeCode] = TextEditingController(text: c.note ?? '');
      }
    }
  }

  @override
  void dispose() {
    for (final c in [_name, _breed, _birthDate, _birthYear, _weight, _memo]) {
      c.dispose();
    }
    for (final c in _conditions.values) {
      c.dispose();
    }
    for (final o in _others) {
      o.dispose();
    }
    super.dispose();
  }

  void _toggleCondition(String code) {
    setState(() {
      final removed = _conditions.remove(code);
      if (removed != null) {
        removed.dispose();
      } else {
        _conditions[code] = TextEditingController();
        _noKnownConditions = false;
      }
    });
  }

  void _addOther() {
    setState(() {
      _others.add(_OtherEntry());
      _noKnownConditions = false;
    });
  }

  void _removeOther(_OtherEntry entry) {
    setState(() => _others.remove(entry));
    entry.dispose();
  }

  /// "질병 없음"을 누르면 고른 질병을 모두 비운다(둘은 함께 설 수 없다).
  void _toggleNoKnown() {
    setState(() {
      _noKnownConditions = !_noKnownConditions;
      if (_noKnownConditions) {
        for (final c in _conditions.values) {
          c.dispose();
        }
        _conditions.clear();
        for (final o in _others) {
          o.dispose();
        }
        _others.clear();
      }
    });
  }

  void _submit() {
    final errors = <String, String>{};
    final name = _name.text.trim();
    final breed = _breed.text.trim();
    if (name.isEmpty) errors['name'] = AppStrings.petNameRequired;
    if (_species == null) errors['species'] = AppStrings.speciesRequired;
    if (breed.isEmpty) errors['breed'] = AppStrings.breedRequired;
    if (_sex == null) errors['sex'] = AppStrings.sexRequired;
    if (_neutered == null) errors['neutered'] = AppStrings.neuteredRequired;

    DateTime? birthDate;
    int? birthYear;
    switch (_ageMode) {
      case null:
        errors['age'] = AppStrings.ageRequired;
      case _AgeMode.birthDate:
        birthDate = parseBirthDate(_birthDate.text, widget.today);
        if (birthDate == null) errors['age'] = AppStrings.birthDateInvalid;
      case _AgeMode.birthYear:
        birthYear = int.tryParse(_birthYear.text.trim());
        if (birthYear == null || !isValidBirthYear(birthYear, widget.today)) {
          errors['age'] = AppStrings.birthYearInvalid;
        }
      case _AgeMode.unknown:
        break;
    }

    final weight = parseWeight(_weight.text);
    if (weight == null) errors['weight'] = AppStrings.weightInvalid;

    final conditions = [
      for (final e in _conditions.entries)
        ConditionEntry(typeCode: e.key, note: optionalText(e.value.text)),
      for (final o in _others)
        ConditionEntry(
          typeCode: ConditionType.otherCode,
          customLabel: optionalText(o.label.text),
          note: optionalText(o.note.text),
        ),
    ];
    if (_others.any((o) => optionalText(o.label.text) == null)) {
      errors['conditions'] = AppStrings.otherLabelRequired;
    } else if (conditions.isEmpty && !_noKnownConditions) {
      errors['conditions'] = AppStrings.healthRequired;
    }

    setState(() => _errors = errors);
    if (errors.isNotEmpty) return;

    widget.onSubmit(
      PetFields(
        name: name,
        species: _species!,
        breed: breed,
        sex: _sex!,
        neutered: _neutered!,
        birthDate: birthDate,
        birthYear: birthYear,
        weightKg: weight!,
        noKnownConditions: _noKnownConditions,
        conditions: conditions,
        memo: optionalText(_memo.text),
      ),
    );
  }

  Widget _label(String text) => Padding(
    padding: const EdgeInsets.only(top: AppSpacing.lg, bottom: AppSpacing.xs),
    child: Text(text, style: AppTypography.caption),
  );

  Widget _error(String key) {
    final message = _errors[key];
    if (message == null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.xs),
      child: Text(message, style: AppTypography.caption),
    );
  }

  Widget _chips(List<Widget> chips) =>
      Wrap(spacing: AppSpacing.sm, runSpacing: AppSpacing.sm, children: chips);

  @override
  Widget build(BuildContext context) {
    final breeds = switch (_species) {
      'dog' => AppStrings.dogBreeds,
      'cat' => AppStrings.catBreeds,
      _ => const <String>[],
    };
    final fixedTypes = widget.conditionTypes
        .where((t) => t.code != ConditionType.otherCode)
        .toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _name,
          inputFormatters: [LengthLimitingTextInputFormatter(50)],
          decoration: InputDecoration(
            labelText: AppStrings.petNameLabel,
            errorText: _errors['name'],
          ),
        ),
        _label(AppStrings.speciesLabelText),
        _chips([
          for (final species in ['dog', 'cat'])
            AppChoiceChip(
              label: AppStrings.speciesLabel(species),
              selected: _species == species,
              onTap: () => setState(() => _species = species),
            ),
        ]),
        _error('species'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _breed,
          inputFormatters: [LengthLimitingTextInputFormatter(50)],
          decoration: InputDecoration(
            labelText: AppStrings.breedLabel,
            errorText: _errors['breed'],
          ),
        ),
        if (breeds.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm),
          _chips([
            for (final breed in breeds)
              AppChoiceChip(
                label: breed,
                selected: _breed.text.trim() == breed,
                onTap: () => setState(() => _breed.text = breed),
              ),
          ]),
        ],
        _label(AppStrings.sexLabelText),
        _chips([
          for (final sex in ['female', 'male'])
            AppChoiceChip(
              label: AppStrings.sexLabel(sex),
              selected: _sex == sex,
              onTap: () => setState(() => _sex = sex),
            ),
          AppChoiceChip(
            label: AppStrings.neuteredYes,
            selected: _neutered == true,
            onTap: () => setState(() => _neutered = true),
          ),
          AppChoiceChip(
            label: AppStrings.neuteredNo,
            selected: _neutered == false,
            onTap: () => setState(() => _neutered = false),
          ),
        ]),
        _error('sex'),
        _error('neutered'),
        _label(AppStrings.ageLabel),
        _chips([
          AppChoiceChip(
            label: AppStrings.ageByBirthDate,
            selected: _ageMode == _AgeMode.birthDate,
            onTap: () => setState(() => _ageMode = _AgeMode.birthDate),
          ),
          AppChoiceChip(
            label: AppStrings.ageByBirthYear,
            selected: _ageMode == _AgeMode.birthYear,
            onTap: () => setState(() => _ageMode = _AgeMode.birthYear),
          ),
          AppChoiceChip(
            label: AppStrings.ageUnknown,
            selected: _ageMode == _AgeMode.unknown,
            onTap: () => setState(() => _ageMode = _AgeMode.unknown),
          ),
        ]),
        if (_ageMode == _AgeMode.birthDate)
          TextField(
            key: const Key('birth_date_field'),
            controller: _birthDate,
            keyboardType: TextInputType.datetime,
            inputFormatters: [LengthLimitingTextInputFormatter(10)],
            decoration: const InputDecoration(
              hintText: AppStrings.birthDateHint,
            ),
          ),
        if (_ageMode == _AgeMode.birthYear)
          TextField(
            key: const Key('birth_year_field'),
            controller: _birthYear,
            keyboardType: TextInputType.number,
            inputFormatters: [
              FilteringTextInputFormatter.digitsOnly,
              LengthLimitingTextInputFormatter(4),
            ],
            decoration: const InputDecoration(
              hintText: AppStrings.birthYearHint,
            ),
          ),
        _error('age'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _weight,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          inputFormatters: [
            FilteringTextInputFormatter.allow(RegExp(r'[0-9.]')),
            LengthLimitingTextInputFormatter(5),
          ],
          decoration: InputDecoration(
            labelText: AppStrings.weightLabel,
            hintText: AppStrings.weightHint,
            suffixText: AppStrings.weightUnit,
            errorText: _errors['weight'],
          ),
        ),
        _label(AppStrings.conditionsLabel),
        _chips([
          for (final type in fixedTypes)
            AppChoiceChip(
              label: type.label,
              selected: _conditions.containsKey(type.code),
              onTap: () => _toggleCondition(type.code),
            ),
          AppChoiceChip(
            label: '+ ${AppStrings.conditionOther}',
            selected: false,
            onTap: _addOther,
          ),
          AppChoiceChip(
            label: AppStrings.noKnownConditions,
            selected: _noKnownConditions,
            onTap: _toggleNoKnown,
          ),
        ]),
        for (final type in fixedTypes)
          if (_conditions.containsKey(type.code))
            _ConditionNote(title: type.label, note: _conditions[type.code]!),
        for (final other in _others)
          _OtherCondition(entry: other, onRemove: () => _removeOther(other)),
        _error('conditions'),
        const SizedBox(height: AppSpacing.sm),
        TextField(
          controller: _memo,
          minLines: 2,
          maxLines: 5,
          inputFormatters: [LengthLimitingTextInputFormatter(500)],
          decoration: const InputDecoration(
            labelText: AppStrings.petMemoLabel,
            hintText: AppStrings.petMemoHint,
          ),
        ),
        if (widget.errorText != null) ...[
          const SizedBox(height: AppSpacing.md),
          Text(widget.errorText!, style: AppTypography.caption),
        ],
        const SizedBox(height: AppSpacing.xl),
        Center(
          child: AppButton(
            label: widget.submitLabel,
            filled: true,
            busy: widget.busy,
            onPressed: widget.busy ? null : _submit,
          ),
        ),
        const SizedBox(height: AppSpacing.xl),
      ],
    );
  }
}

class _ConditionNote extends StatelessWidget {
  const _ConditionNote({required this.title, required this.note});

  final String title;
  final TextEditingController note;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        child: Row(
          children: [
            SizedBox(
              width: 96,
              child: Text(title, style: AppTypography.bodyStrong),
            ),
            Expanded(
              child: TextField(
                controller: note,
                inputFormatters: [LengthLimitingTextInputFormatter(100)],
                decoration: const InputDecoration(
                  hintText: AppStrings.conditionNoteHint,
                  border: InputBorder.none,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OtherCondition extends StatelessWidget {
  const _OtherCondition({required this.entry, required this.onRemove});

  final _OtherEntry entry;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.sm),
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        child: Row(
          children: [
            SizedBox(
              width: 96,
              child: TextField(
                controller: entry.label,
                inputFormatters: [LengthLimitingTextInputFormatter(30)],
                decoration: const InputDecoration(
                  hintText: AppStrings.conditionOtherHint,
                  border: InputBorder.none,
                ),
              ),
            ),
            Expanded(
              child: TextField(
                controller: entry.note,
                inputFormatters: [LengthLimitingTextInputFormatter(100)],
                decoration: const InputDecoration(
                  hintText: AppStrings.conditionNoteHint,
                  border: InputBorder.none,
                ),
              ),
            ),
            Pressable(
              semanticLabel: AppStrings.removeCondition,
              onTap: onRemove,
              child: const Icon(Icons.close, size: 18),
            ),
          ],
        ),
      ),
    );
  }
}
