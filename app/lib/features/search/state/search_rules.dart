import '../../../l10n/app_strings.dart';
import '../api/search_models.dart';

/// 검색어의 길이 — 서버의 규칙과 같다(다듬은 뒤 2~100자).
const searchMinLength = 2;
const searchMaxLength = 100;

/// 공백류(줄바꿈·탭)를 빈칸 하나로 줄이고 앞뒤를 뗀다. 두 자 미만이면 묻지 않는다(null). 백 자에서 자른다.
String? cleanSearchText(String text) {
  final cleaned = text.trim().split(RegExp(r'\s+')).join(' ');
  if (cleaned.length < searchMinLength) return null;
  return cleaned.length > searchMaxLength ? cleaned.substring(0, searchMaxLength).trim() : cleaned;
}

/// 종류의 이름.
String kindLabel(SearchKind kind) => switch (kind) {
  SearchKind.careNote => AppStrings.searchKindCareNote,
  SearchKind.internalNote => AppStrings.searchKindInternalNote,
  SearchKind.visitMemo => AppStrings.searchKindVisitMemo,
  SearchKind.petMemo => AppStrings.searchKindPetMemo,
  SearchKind.conditionNote => AppStrings.searchKindConditionNote,
  SearchKind.customerMemo => AppStrings.searchKindCustomerMemo,
};

/// 줄의 제목 — 아이 이름, 아이가 없는 줄(보호자 메모·보호자만의 방문)은 보호자 이름.
String titleOf(SearchItem item) => item.petName ?? item.ownerName;

/// 줄의 둘째 줄 — 종류와 방문 날(`케어 노트 · 11월 3일`). 날짜가 없으면 종류만.
String metaLine(SearchItem item) {
  final date = item.date;
  return date == null ? kindLabel(item.kind) : AppStrings.searchMeta(kindLabel(item.kind), date);
}

/// 줄을 눌렀을 때 갈 곳. 방문이 있으면 방문 상세, 없으면 열 아이의 상세(보호자 메모는 [보호자] 탭으로),
/// 둘 다 없으면 갈 곳이 없다(null — 아이가 없는 보호자의 메모).
String? destinationOf(SearchItem item) {
  if (item.visitId != null) return '/visits/${item.visitId}';
  if (item.openPetId == null) return null;
  final tab = item.kind == SearchKind.customerMemo ? '?tab=owner' : '';
  return '/pets/${item.openPetId}$tab';
}
