import 'package:chagocnote/core/time/grooming_cycle.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('출처마다 반려동물 상세의 말이 다르다(설계 3.1 의 표)', () {
    expect(
      cycleSourceLine(source: CycleSource.manual, weeks: 6, visited: true),
      '6주마다 와요 · 직접 정함',
    );
    expect(
      cycleSourceLine(source: CycleSource.computed, weeks: 6, visited: true),
      '보통 6주마다 와요 · 지난 방문에서 계산',
    );
    expect(
      cycleSourceLine(
        source: CycleSource.single,
        weeks: 4,
        lastIntervalWeeks: 6,
        visited: true,
      ),
      '지난번에는 6주 만에 왔어요',
    );
    expect(
      cycleSourceLine(source: CycleSource.none, weeks: 4, visited: true),
      '아직 한 번 왔어요',
    );
    expect(
      cycleSourceLine(source: CycleSource.none, weeks: 4, visited: false),
      '미용 주기 정하기',
    );
    expect(estimateNote(4), '다음은 매장 기본 간격(4주)으로 어림해요');
  });

  test('다음 올 때에는 늘 쯤을 붙이고 어림이면 (어림)을 붙인다', () {
    expect(dueLine(DateTime(2026, 12, 3), estimated: false), '다음은 12월 3일쯤');
    expect(dueLine(DateTime(2026, 12, 3), estimated: true), '다음은 12월 3일쯤(어림)');
    expect(nextDueOf(DateTime(2026, 11, 1), 5), DateTime(2026, 12, 6));
  });

  test('모르는 출처는 none 이고 single·none 은 어림이다', () {
    expect(CycleSource.parse('computed'), CycleSource.computed);
    expect(CycleSource.parse('weird'), CycleSource.none);
    expect(CycleSource.parse(null), CycleSource.none);
    expect(
      [for (final s in CycleSource.values) s.estimated],
      [false, false, true, true],
    );
  });

  test('완료 시트의 다음 예약 줄이 말하는 간격의 출처', () {
    expect(draftSourceLabel(CycleSource.computed), '보통 오는 간격');
    expect(draftSourceLabel(CycleSource.manual), '직접 정한 간격');
    expect(draftSourceLabel(CycleSource.single), '매장 기본 간격(어림)');
    expect(draftSourceLabel(CycleSource.none), '매장 기본 간격(어림)');
  });
}
