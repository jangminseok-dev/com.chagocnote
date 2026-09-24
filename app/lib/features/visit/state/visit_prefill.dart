import '../api/visit_models.dart';

/// 카톡 초안이 예약 등록 화면에 미리 채우는 값(③-A3). 다음 예약 초안
/// (`NextVisitDraft`)과 달리 어느 칸이든 비어 있을 수 있다.
///
/// [customerId]가 있으면 ①(고객 찾기)을 건너뛰고 ②로 바로 간다. 없으면 ①에서
/// 고른 뒤 ②가 나머지 칸으로 채워진다. [petIds]는 그 보호자의 아이만 남는다.
/// [menus]가 있으면 소요를 메뉴 기본 소요의 합으로 채우고 "지난번처럼"으로
/// 덮어쓰지 않는다. 없으면 기존처럼 "지난번처럼"을 부른다.
class VisitPrefill {
  const VisitPrefill({
    this.customerId,
    this.date,
    this.at,
    this.petIds = const {},
    this.menus = const [],
  });

  final int? customerId;
  final DateTime? date;

  /// `HH:MM`.
  final String? at;
  final Set<int> petIds;
  final List<MenuBrief> menus;
}
