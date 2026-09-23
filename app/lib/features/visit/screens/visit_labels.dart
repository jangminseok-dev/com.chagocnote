import '../../../l10n/app_strings.dart';
import '../api/visit_models.dart';

/// `14:00`.
String hhmm(DateTime t) =>
    '${t.hour.toString().padLeft(2, '0')}:${t.minute.toString().padLeft(2, '0')}';

/// `10월 2일 금`.
String dayLabel(DateTime d) =>
    '${d.month}월 ${d.day}일 ${AppStrings.weekdaysShort[d.weekday - 1]}';

bool sameDay(DateTime a, DateTime b) =>
    a.year == b.year && a.month == b.month && a.day == b.day;

String statusLabel(String status) => switch (status) {
  VisitStatus.reserved => AppStrings.statusReserved,
  VisitStatus.inProgress => AppStrings.statusInProgress,
  VisitStatus.completed => AppStrings.statusCompleted,
  VisitStatus.canceled => AppStrings.statusCanceled,
  VisitStatus.noShow => AppStrings.statusNoShow,
  _ => status,
};

String warningLabel(String warning) => switch (warning) {
  VisitWarning.overlap => AppStrings.warningOverlap,
  VisitWarning.closedDay => AppStrings.warningClosedDay,
  VisitWarning.outsideHours => AppStrings.warningOutsideHours,
  _ => warning,
};

/// 보호자 이름. 익명화한 고객이면 "삭제된 고객".
String ownerLabel(CustomerBrief customer) =>
    customer.name ?? AppStrings.deletedCustomer;

/// 묶음의 이름 — 반려동물 이름을 잇고, 보호자만의 방문이면 "보호자만".
String visitsTitle(List<Visit> visits) {
  final names = [
    for (final v in visits)
      v.pet == null
          ? AppStrings.ownerOnly
          : (v.pet!.name ?? AppStrings.deletedCustomer),
  ];
  return names.join(' · ');
}

String menusLabel(List<MenuBrief> menus) =>
    menus.isEmpty ? AppStrings.noMenu : menus.map((m) => m.name).join(', ');

/// 상태가 섞인 묶음의 아이별 상태 — "두부 완료 · 보리 미용 중".
String statusSummary(List<Visit> visits) => [
  for (final v in visits)
    '${v.pet == null ? AppStrings.ownerOnly : (v.pet!.name ?? AppStrings.deletedCustomer)} '
        '${statusLabel(v.status)}',
].join(' · ');
