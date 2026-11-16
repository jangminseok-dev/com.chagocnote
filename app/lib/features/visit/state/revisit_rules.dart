/// 다시 올 때(⑬)의 순수 함수 — 안내 글 채우기와 템플릿 검사. 서버의 `revisit_rules` 와 같은 규칙이다.
library;

import '../../../l10n/app_strings.dart';

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
