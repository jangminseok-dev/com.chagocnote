/// 다시 올 때(⑬)의 순수 함수 — 안내 글 채우기와 템플릿 검사. 서버의 `revisit_rules` 와 같은 규칙이다.
library;

import '../../../l10n/app_strings.dart';
import '../api/revisit_models.dart';
import '../api/visit_models.dart';

const revisitMessageMax = 300;

/// 넣을 수 있는 자리 — 서버가 채우는 셋.
const revisitSlotPet = '{아이}';
const revisitSlotWeeks = '{주}';
const revisitSlotShop = '{매장}';
const revisitSlots = [revisitSlotPet, revisitSlotWeeks, revisitSlotShop];

/// 칩의 이름표.
String revisitSlotLabel(String slot) => switch (slot) {
  revisitSlotPet => AppStrings.revisitChipPet,
  revisitSlotWeeks => AppStrings.revisitChipWeeks,
  revisitSlotShop => AppStrings.revisitChipShop,
  _ => slot,
};

/// 템플릿에 값을 채운다 — 한 번에 바꾼다(채운 값 안의 `{…}` 를 다시 바꾸지 않는다). 모르는 자리는 그대로.
String fillRevisitMessage(
  String template, {
  required String shop,
  required String pet,
  required int weeks,
}) => template.replaceAllMapped(
  RegExp(r'\{(매장|아이|주)\}'),
  (m) => switch (m.group(1)) {
    '매장' => shop,
    '아이' => pet,
    _ => '$weeks',
  },
);

/// 저장을 막는 까닭. 괜찮으면 null.
String? revisitMessageProblem(String text) {
  if (text.trim().isEmpty) return AppStrings.revisitMessageEmpty;
  if (text.runes.length > revisitMessageMax) return AppStrings.revisitMessageTooLong;
  return null;
}

/// 다시 올 때 목록의 줄(⑬ 설계 3.3) — 지남 `6주마다 · 5일 지남`, 곧 `6주마다 · 3일 뒤쯤`(오늘이면 `오늘쯤`),
/// 어림이면 주기를 말하지 않고 지난 사실만 `5주 전에 왔어요 · 어림`.
String revisitRowLine(RevisitItem item, DateTime today) {
  final day = DateTime(today.year, today.month, today.day);
  if (item.estimated) {
    final days = day.difference(item.lastVisitDate).inDays;
    // 서버의 안내 글 `{주}` 와 같은 셈 — 주로 반올림, 최소 1.
    final weeks = ((days / 7) + 0.5).floor();
    return AppStrings.revisitEstimatedLine(weeks < 1 ? 1 : weeks);
  }
  final gap = item.dueDate.difference(day).inDays;
  return gap < 0
      ? AppStrings.revisitDueLine(item.cycleWeeks, -gap)
      : AppStrings.revisitSoonLine(item.cycleWeeks, gap);
}

/// [예약]이 여는 초안 — 날이 오늘이거나 지났으면 **내일 이후**의 가장 가까운 같은 요일로(오늘 지난 시각에 잡지
/// 않는다), 시각은 그대로. 앞날이면 그대로다.
NextVisitDraft draftForBooking(NextVisitDraft draft, DateTime today) {
  final day = DateTime(today.year, today.month, today.day);
  final at = draft.startsAt.day;
  if (at.isAfter(day)) return draft;
  var next = DateTime(day.year, day.month, day.day + 1);
  while (next.weekday != at.weekday) {
    next = DateTime(next.year, next.month, next.day + 1);
  }
  return draft.movedTo(next);
}
