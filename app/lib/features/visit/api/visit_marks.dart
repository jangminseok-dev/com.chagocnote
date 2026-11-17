/// 줄의 낱말(⑬ 설계 4.4 — 코드·차례의 정본, 낱말은 `screens/visit_labels.dart` 의 `markLabel`). 끝낸 일만 낱말이
/// 되고 남은 일은 머리의 숫자다. 서버가 더한 코드는 버린다 — 옛 앱이 죽지 않게.
enum VisitMark {
  paid('paid'),
  reportSent('report_sent'),
  passUsed('pass_used'),
  depositReceived('deposit_received');

  const VisitMark(this.code);

  final String code;
}

/// 서버의 `marks`(코드 목록)를 아는 것만, 정해 둔 차례로.
List<VisitMark> parseMarks(Object? json) {
  if (json is! List) return const [];
  final codes = {for (final c in json) c};
  return [
    for (final m in VisitMark.values)
      if (codes.contains(m.code)) m,
  ];
}

/// 한 줄의 낱말이 [max] 를 넘으면 앞의 [max] 개와 `+N` 으로 접는다.
List<String> foldWords(List<String> words, {int max = 4}) => words.length <= max
    ? words
    : [...words.take(max), '+${words.length - max}'];
