import '../../../l10n/app_strings.dart';
import '../api/check_models.dart';

/// 확인할 것 한 줄의 글(설계 3.4). 화면은 부르기만 한다.
String checkLine(VisitCheck c) => switch (c.code) {
  CheckCode.caution => AppStrings.checkCaution(c.reason!),
  CheckCode.noShow => AppStrings.checkNoShow(c.count!),
  CheckCode.firstVisit => AppStrings.checkFirstVisit,
  CheckCode.consent =>
    c.consentState == ConsentState.expired && c.receivedOn != null
        ? AppStrings.checkConsentExpired(c.receivedOn!)
        : AppStrings.checkConsentMissing([
            for (final r in c.consentReasons)
              switch (r) {
                ConsentReason.senior => AppStrings.consentReasonSenior,
                ConsentReason.conditions => AppStrings.consentReasonConditions,
              },
          ]),
  CheckCode.conditions => AppStrings.checkConditions([
    for (final item in c.conditions) item.label,
  ]),
  CheckCode.longAbsence => AppStrings.checkLongAbsence(
    c.days!,
    c.lastVisitOn!,
  ),
};

/// 묶음 하나 — 보호자 항목(제목·아이 없음) 또는 한 아이의 항목.
class CheckSection {
  const CheckSection({this.title, this.petId, required this.checks});

  /// 아이 이름. 아이가 하나뿐이거나 이름을 모르면 null.
  final String? title;

  /// 아이 묶음이면 그 아이 — [받았어요]가 누구의 동의인지 안다.
  final int? petId;
  final List<VisitCheck> checks;
}

/// 미리 보기를 묶음으로 — 보호자 묶음이 먼저, 그다음 아이별. 빈 묶음은 뺀다.
/// 아이가 둘 이상일 때만 아이 이름을 제목으로 단다.
List<CheckSection> checkSections(
  VisitChecksPreview preview,
  Map<int, String> petNames,
) => [
  if (preview.customer.isNotEmpty) CheckSection(checks: preview.customer),
  for (final pet in preview.pets)
    if (pet.checks.isNotEmpty)
      CheckSection(
        title: preview.pets.length > 1 ? petNames[pet.petId] : null,
        petId: pet.petId,
        checks: pet.checks,
      ),
];

/// 방문 상세 — 그 방문의 항목 전부를 묶음 하나로.
List<CheckSection> detailSections(List<VisitCheck> checks, {int? petId}) => [
  if (checks.isNotEmpty) CheckSection(petId: petId, checks: checks),
];

/// 미리 보기 조회 키의 아이 목록 — 목록은 값으로 비교되지 않아 글자로 잇는다.
String petIdsKey(Iterable<int> ids) => (ids.toList()..sort()).join(',');
