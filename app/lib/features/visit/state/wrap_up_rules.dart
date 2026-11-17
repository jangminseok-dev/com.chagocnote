/// 하루 마무리(⑬ 설계 3.6)의 순수 함수 — 장의 차례, 하루 머리의 남은 일 낱말, 결제 장의 저장 본문.
library;

import '../../../l10n/app_strings.dart';
import '../api/record_models.dart';
import '../api/visit_models.dart';
import '../api/wrap_up_models.dart';
import 'photo_edits.dart';

/// 장의 열쇠 — 한 방문이 결제·알림장 두 장일 수 있다.
String cardKey(WrapUpCard card) => '${card.kind.code}:${card.visit.visitId}';

/// 고른 종류([start])의 장부터, 그다음은 서버의 차례(정리 → 결제 → 알림장, 그 안에서 시작 순).
List<WrapUpCard> orderCards(List<WrapUpCard> cards, WrapUpKind? start) => start == null
    ? cards
    : [
        for (final c in cards)
          if (c.kind == start) c,
        for (final c in cards)
          if (c.kind != start) c,
      ];

/// 하루 머리의 남은 일 — 종류와 낱말, 0 인 것은 빼고 차례대로.
List<(WrapUpKind, String)> remainingWords(DayCounts counts) => [
  if (counts.unresolved > 0) (WrapUpKind.unresolved, AppStrings.remainingUnresolved(counts.unresolved)),
  if (counts.unpaid > 0) (WrapUpKind.unpaid, AppStrings.remainingUnpaid(counts.unpaid)),
  if (counts.reportUnsent > 0)
    (WrapUpKind.reportUnsent, AppStrings.remainingReportUnsent(counts.reportUnsent)),
];

/// 달력의 고른 날 카드 — 남은 일을 한 줄로(없으면 빈 글).
String remainingLine(DayCounts counts) => [for (final w in remainingWords(counts)) w.$2].join(' · ');

/// 결제 장의 [저장] — 기록 전체 교체지만 총액·결제 수단만 바꾼다(다른 칸·사진 자리·버전은 읽은 기록 그대로).
/// 기록이 없으면 총액·수단만 있는 새 기록이다.
RecordInput paymentInputOf(
  VisitRecord? record, {
  required int total,
  required PaymentMethod method,
}) => RecordInput(
  version: record?.version,
  weightKg: record?.weightKg,
  careNote: record?.careNote,
  internalNote: record?.internalNote,
  paymentMethod: method,
  totalAmount: total,
  items: [
    for (final i in record?.items ?? const <RecordItem>[]) (menuId: i.menuId, amount: i.amount),
  ],
  media: record == null ? const [] : keptPlacements(record.media),
);
