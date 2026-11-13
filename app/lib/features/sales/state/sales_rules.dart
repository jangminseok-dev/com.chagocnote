/// 매출 탭의 문장·기간·숫자 표기 규칙(설계 ⑧ 3.2). 화면은 여기서 글자를 받아 그리기만 한다.
library;

import '../../../core/time/shop_time.dart';
import '../../../l10n/app_strings.dart';
import '../api/sales_models.dart';

/// `3250000` → `3,250,000`.
String won(int amount) {
  final digits = amount.abs().toString();
  final out = StringBuffer(amount < 0 ? '-' : '');
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) out.write(',');
    out.write(digits[i]);
  }
  return out.toString();
}

/// 문장 속의 금액 — 만 원으로 나누어떨어지면 `42만 원`, 아니면 `425,000원`.
String amountPhrase(int amount) => amount != 0 && amount % 10000 == 0
    ? '${won(amount ~/ 10000)}만 원'
    : '${won(amount)}원';

/// [anchor]가 든 기간의 첫날.
DateTime _startOf(SalesSpan span, DateTime anchor) => switch (span) {
  SalesSpan.day => DateTime(anchor.year, anchor.month, anchor.day),
  SalesSpan.week => DateTime(anchor.year, anchor.month, anchor.day - (anchor.weekday - 1)),
  SalesSpan.month => DateTime(anchor.year, anchor.month),
  SalesSpan.year => DateTime(anchor.year),
};

/// 기간을 [step]만큼(±1) 옮긴 anchor. 월은 그 달 1일, 연은 그 해 1월 1일로 맞춘다 —
/// 31일에서 한 달 앞으로 갈 때 날짜가 넘치지 않게.
DateTime shiftAnchor(SalesSpan span, DateTime anchor, int step) => switch (span) {
  SalesSpan.day => DateTime(anchor.year, anchor.month, anchor.day + step),
  SalesSpan.week => DateTime(anchor.year, anchor.month, anchor.day + 7 * step),
  SalesSpan.month => DateTime(anchor.year, anchor.month + step),
  SalesSpan.year => DateTime(anchor.year + step),
};

/// 다음 기간으로 갈 수 있는가 — 다음 기간의 첫날이 오늘 뒤면 못 간다.
bool canGoNext(SalesSpan span, DateTime anchor, DateTime today) {
  final next = _startOf(span, shiftAnchor(span, _startOf(span, anchor), 1));
  return !next.isAfter(DateTime(today.year, today.month, today.day));
}

/// 기간의 제목. 월은 영문 월([enMonth])과 연도([small]), 연은 [enText], 주·일은 한글([ko]).
typedef PeriodTitle = ({int? enMonth, String? enText, String? small, String? ko});

PeriodTitle periodTitle(SalesSummary s) => switch (s.span) {
  SalesSpan.month => (enMonth: s.start.month, enText: null, small: '${s.start.year}', ko: null),
  SalesSpan.year => (enMonth: null, enText: '${s.start.year}', small: null, ko: null),
  SalesSpan.week => (
    enMonth: null,
    enText: null,
    small: null,
    ko: s.start.month == s.end.month
        ? '${s.start.month}월 ${s.start.day}일 – ${s.end.day}일'
        : '${s.start.month}월 ${s.start.day}일 – ${s.end.month}월 ${s.end.day}일',
  ),
  SalesSpan.day => (
    enMonth: null,
    enText: null,
    small: null,
    ko: '${s.start.month}월 ${s.start.day}일 ${AppStrings.weekdaysShort[s.start.weekday - 1]}요일',
  ),
};

/// 끝 글자에 받침이 있으면 '과', 없으면 '와'.
String _withParticle(String word) {
  final code = word.codeUnitAt(word.length - 1);
  final hasFinal = code >= 0xAC00 && code <= 0xD7A3 && (code - 0xAC00) % 28 != 0;
  return '$word${hasFinal ? '과' : '와'}';
}

String _versus(String name, int now, int before) {
  final diff = now - before;
  if (diff == 0) return '${_withParticle(name)} 같아요.';
  return '$name보다 ${amountPhrase(diff.abs())} ${diff > 0 ? '많아요' : '적어요'}.';
}

/// 견준 앞 창의 이름. 진행 중인 기간은 같은 길이만큼만 견주므로 그 끝을 말한다.
String _previousName(SalesSummary s, CompareWindow previous) {
  final ongoing = s.elapsedEnd != null && s.elapsedEnd!.isBefore(s.end);
  return switch (s.span) {
    SalesSpan.day => '그 전날',
    SalesSpan.week => ongoing ? '지난주 같은 요일까지' : '그 전 주',
    SalesSpan.month => ongoing ? '지난달 ${previous.end.day}일까지' : '그 전 달',
    SalesSpan.year =>
      ongoing ? '작년 ${previous.end.month}월 ${previous.end.day}일까지' : '그 전 해',
  };
}

/// 앞 기간과 견준 문장. 견줄 것이 없거나 앞 기간의 매출이 0 이면 없다.
String? compareSentence(SalesSummary s) {
  final previous = s.previous;
  if (previous == null || previous.revenue == 0) return null;
  return _versus(_previousName(s, previous), s.revenue, previous.revenue);
}

/// 작년 같은 때와 견준 문장.
String? yearAgoSentence(SalesSummary s) {
  final ago = s.yearAgo;
  return ago == null ? null : _versus('작년 같은 때', s.revenue, ago.revenue);
}

/// `이번 달 목표 500만 원의 65%`. 목표가 없으면 없다.
String? goalSentence(SalesSummary s) {
  final goal = s.goalAmount;
  if (goal == null || goal <= 0) return null;
  return '이번 달 목표 ${amountPhrase(goal)}의 ${s.revenue * 100 ~/ goal}%';
}

/// 목표의 진행(0~1).
double goalProgress(SalesSummary s) {
  final goal = s.goalAmount;
  if (goal == null || goal <= 0) return 0;
  return (s.revenue / goal).clamp(0, 1).toDouble();
}

/// `41마리가 48번 다녀갔어요`. 아이가 없으면(보호자만의 방문뿐) 횟수만.
String facesLine(SalesSummary s) => s.petCount > 0
    ? '${s.petCount}마리가 ${s.visitCount}번 다녀갔어요'
    : '${s.visitCount}번 다녀갔어요';

/// 처음 고를 칸 — 오늘 칸이 있으면 그것, 없으면 방문이 있는 마지막 칸. 연 보기의 막대는 고르지 않는다.
String? selectedBucketKey(SalesSummary s, DateTime today) {
  if (s.span == SalesSpan.year) return null;
  final todayKey = isoDay(today);
  for (final bucket in s.buckets) {
    if (bucket.key == todayKey && !bucket.future) return bucket.key;
  }
  for (final bucket in s.buckets.reversed) {
    if (bucket.visitCount > 0) return bucket.key;
  }
  return null;
}

/// 결제 수단의 이름. 모르는 값은 '기타'다.
String paymentLabel(String method) => switch (method) {
  'card' => AppStrings.paymentCard,
  'cash' => AppStrings.paymentCash,
  'transfer' => AppStrings.paymentTransfer,
  'none' => AppStrings.salesPaymentNone,
  _ => AppStrings.salesPaymentOther,
};

/// 막대의 높이 비율(0~1) — 가장 큰 값이 1 이다. 모두 0 이면 모두 0, 음수는 0 으로 친다.
List<double> barRatios(List<int> values) {
  var max = 0;
  for (final v in values) {
    if (v > max) max = v;
  }
  return [for (final v in values) max == 0 || v <= 0 ? 0.0 : v / max];
}
