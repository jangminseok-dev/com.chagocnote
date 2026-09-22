import '../../../l10n/app_strings.dart';
import '../api/customer_models.dart';
import '../state/customer_input.dart';

/// 반려동물 한 줄 요약 — "강아지 · 말티즈 · 여아(중성화) · 5살 · 3.2kg".
String petSummaryLine(Pet pet) {
  final sex = pet.neutered
      ? '${AppStrings.sexLabel(pet.sex)}(${AppStrings.neutered})'
      : AppStrings.sexLabel(pet.sex);
  return [
    AppStrings.speciesLabel(pet.species),
    pet.breed,
    sex,
    pet.ageLabel,
    formatWeight(pet.weightKg),
  ].join(' · ');
}

/// `2021.03.04`. 날짜만 있는 값(생일)은 그대로, 시각이 있는 값은 기기 시각으로 바꿔 찍는다.
String formatDate(DateTime date) {
  final d = date.isUtc ? date.toLocal() : date;
  return '${d.year}.${d.month.toString().padLeft(2, '0')}.${d.day.toString().padLeft(2, '0')}';
}
