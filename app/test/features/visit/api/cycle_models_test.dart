import 'package:chagocnote/core/time/grooming_cycle.dart';
import 'package:chagocnote/features/visit/api/revisit_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/api/wrap_up_models.dart';
import 'package:chagocnote/features/visit/api/visit_marks.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

void main() {
  test('새 칸이 없는 옛 응답도 기본값으로 읽는다', () {
    final day = DayVisits.fromJson(
      dayJson(items: [dayItemJson(visitJson())])
        ..['counts'].remove('unpaid')
        ..['counts'].remove('report_unsent')
        ..['counts'].remove('checks'),
    );
    expect(
      (day.counts.unpaid, day.counts.reportUnsent, day.counts.checks),
      (0, 0, 0),
    );
    final item = DayVisitItem.fromJson(
      dayItemJson(visitJson())..remove('marks'),
    );
    expect(item.marks, isEmpty);
    final detail = VisitDetail.fromJson(
      visitDetailJson()
        ..remove('marks')
        ..remove('report_skipped'),
    );
    expect(detail.marks, isEmpty);
    expect(detail.reportSkipped, isFalse);
    final draft = NextVisitDraft.fromJson(
      nextDraftJson(intervalWeeks: 5)
        ..remove('cycle_weeks')
        ..remove('cycle_source'),
    );
    expect((draft.cycleWeeks, draft.cycleSource), (5, CycleSource.none));
  });

  test('남은 일의 수와 낱말을 읽는다', () {
    final day = DayVisits.fromJson(
      dayJson(
        unpaid: 2,
        reportUnsent: 1,
        checks: 3,
        items: [
          dayItemJson(visitJson(), marks: ['paid', 'report_sent', 'x']),
        ],
      ),
    );
    expect((day.counts.unpaid, day.counts.reportUnsent, day.counts.checks), (
      2,
      1,
      3,
    ));
    expect(day.items.single.marks, [VisitMark.paid, VisitMark.reportSent]);
    final month = CalendarMonth.fromJson(
      calendarJson(
        days: {
          3: {'unresolved_count': 1, 'unpaid_count': 2, 'report_unsent_count': 1},
        },
      ),
    );
    expect(month.days[2].remainingCount, 4);
    expect(month.days[3].remainingCount, 0);
  });

  test('초안은 주기와 출처를 싣고 날을 옮겨도 시각은 그대로다', () {
    final draft = NextVisitDraft.fromJson(
      nextDraftJson(
        startsAt: '2026-10-30T14:30:00+09:00',
        cycleWeeks: 6,
        cycleSource: 'computed',
      ),
    );
    expect((draft.cycleWeeks, draft.cycleSource), (6, CycleSource.computed));
    final moved = draft.movedTo(DateTime(2026, 11, 20));
    expect(moved.startsAt.wall, DateTime(2026, 11, 20, 14, 30));
    expect((moved.customerId, moved.cycleWeeks), (7, 6));
    expect(moved.petIds, [11]);
  });

  test('다시 올 때의 줄 — 모르는 출처는 none 으로, 깨진 줄은 버린다', () {
    final item = RevisitItem.tryParse(
      revisitItemJson(cycleSource: 'weird', nudgedOn: '2026-11-10'),
    )!;
    expect(item.cycleSource, CycleSource.none);
    expect(item.nudgedOn, DateTime(2026, 11, 10));
    expect(RevisitItem.tryParse({'pet': null}), isNull);
    final page = RevisitPage.fromJson({
      'items': [revisitItemJson(), 'broken'],
      'next_cursor': 'abc',
    });
    expect((page.items.length, page.nextCursor), (1, 'abc'));
    expect(RevisitCounts.fromJson({'soon': 2, 'due': 3}).total, 5);
  });

  test('하루 마무리의 장 — 모르는 종류의 장은 버린다', () {
    final day = DayWrapUp.fromJson({
      'date': '2026-11-16',
      'cards': [
        wrapUpCardJson(kind: 'unpaid', totalAmount: 30000, paymentMethod: 'card'),
        wrapUpCardJson(kind: 'deposit_waiting'),
        wrapUpCardJson(kind: 'report_unsent'),
      ],
    });
    expect([for (final c in day.cards) c.kind], [
      WrapUpKind.unpaid,
      WrapUpKind.reportUnsent,
    ]);
    expect(day.cards.first.prefill!.totalAmount, 30000);
    expect(day.cards.last.prefill, isNull);
  });

  test('매장의 다시 올 때 설정과 처음 글', () {
    final s = RevisitSettings.fromJson(revisitSettingsJson(soonDays: 10));
    expect((s.defaultCycleWeeks, s.revisitSoonDays, s.revisitMessage), (4, 10, null));
    expect(s.defaultMessage, contains('{아이}'));
    expect((s.countUnsentReports, s.cycleSampleVisits, s.cycleMinGapDays), (
      true,
      6,
      7,
    ));
  });
}
