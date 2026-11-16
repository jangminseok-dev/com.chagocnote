/// 아이의 미용 주기를 말로 바꾸는 순수 함수(⑬ 설계 3.1·3.4) — 계산은 서버가 하고, 여기는 받은 값을 글로만 바꾼다.
/// visit(목록·완료 시트)와 customer(반려동물 상세)가 함께 쓴다 — customer 는 visit 를 import 할 수 없어 core 에 둔다.
library;

/// 주기의 출처. 직접 정함(manual)·계산(computed)은 주기를 안다. 간격 하나(single)·모름(none)은 매장의 기본 간격으로
/// 어림한다 — 계산한 숫자가 사실처럼 보이지 않게 늘 가려 말한다.
enum CycleSource {
  manual('manual'),
  computed('computed'),
  single('single'),
  none('none');

  const CycleSource(this.code);

  final String code;

  /// 모르는 값(서버가 더한 출처)은 모른다(none)로 읽는다 — 어림이라고 말하는 쪽이 안전하다.
  static CycleSource parse(Object? code) =>
      values.firstWhere((s) => s.code == code, orElse: () => none);

  bool get estimated => this == single || this == none;
}

/// 반려동물 상세의 주기 줄 첫 글. [visited] 는 완료 방문이 한 번이라도 있는가.
String cycleSourceLine({
  required CycleSource source,
  required int weeks,
  int? lastIntervalWeeks,
  required bool visited,
}) => switch (source) {
  CycleSource.manual => '$weeks주마다 와요 · 직접 정함',
  CycleSource.computed => '보통 $weeks주마다 와요 · 지난 방문에서 계산',
  CycleSource.single => '지난번에는 ${lastIntervalWeeks ?? weeks}주 만에 왔어요',
  CycleSource.none => visited ? '아직 한 번 왔어요' : '미용 주기 정하기',
};

/// 어림인 아이의 날짜가 무엇으로 정해졌는지.
String estimateNote(int defaultWeeks) => '다음은 매장 기본 간격($defaultWeeks주)으로 어림해요';

/// 다음 올 때 — 늘 "쯤"을 붙인다(지난 간격일 뿐 약속이 아니다).
String dueLine(DateTime due, {required bool estimated}) =>
    '다음은 ${due.month}월 ${due.day}일쯤${estimated ? '(어림)' : ''}';

/// 마지막 완료 방문의 날 + 주.
DateTime nextDueOf(DateTime lastVisit, int weeks) =>
    DateTime(lastVisit.year, lastVisit.month, lastVisit.day + weeks * 7);

/// 완료 시트의 다음 예약 줄이 말하는 간격의 출처.
String draftSourceLabel(CycleSource source) => switch (source) {
  CycleSource.computed => '보통 오는 간격',
  CycleSource.manual => '직접 정한 간격',
  CycleSource.single || CycleSource.none => '매장 기본 간격(어림)',
};
