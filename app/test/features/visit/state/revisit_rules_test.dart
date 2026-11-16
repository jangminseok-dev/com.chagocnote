import 'package:chagocnote/features/visit/api/revisit_models.dart';
import 'package:chagocnote/features/visit/api/visit_models.dart';
import 'package:chagocnote/features/visit/state/revisit_rules.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/visit_fixtures.dart';

void main() {
  test('안내 글은 서버와 같은 셋 — 매장·아이·주를 채우고 모르는 자리는 그대로 둔다', () {
    expect(
      fillRevisitMessage('{아이} {아이} {주}주 · {매장} · {모르는칸}', shop: '히스', pet: '콩이', weeks: 6),
      '콩이 콩이 6주 · 히스 · {모르는칸}',
    );
  });

  test('빈 글·공백뿐·300자 넘는 글은 저장하지 않는다', () {
    expect(revisitMessageProblem(''), AppStrings.revisitMessageEmpty);
    expect(revisitMessageProblem('  \n '), AppStrings.revisitMessageEmpty);
    expect(revisitMessageProblem('가' * 301), AppStrings.revisitMessageTooLong);
    expect(revisitMessageProblem('가' * 300), isNull);
    expect(revisitMessageProblem('칩이 없는 글'), isNull);
  });

  test('줄 아래의 말 — 지금 값으로 무슨 일이 생기는지', () {
    expect(AppStrings.revisitDefaultWeeksNote(4), "한 번 온 아이: 4주 뒤로 잡고, 4주가 지나면 '지남'에 올라요");
    expect(AppStrings.revisitSoonCountNote(3), "지금 3마리가 '곧'에 있어요");
    expect(AppStrings.revisitSampleVisitsNote(6), '최근 6번의 방문 사이 간격의 가운데 값을 써요');
    expect(AppStrings.revisitMinGapNote(7), '7일 안에 다시 온 방문은 주기 계산에서 빼요');
    expect(AppStrings.revisitMinGapNote(0), '모든 방문을 셈에 넣어요');
  });

  group('다시 올 때 목록의 줄과 [예약]의 날(⑬)', () {
    final today = DateTime(2026, 11, 17); // 화요일

    RevisitItem item({
      String due = '2026-11-12',
      bool estimated = false,
      String source = 'computed',
      String last = '2026-10-01',
    }) => RevisitItem.tryParse(
      revisitItemJson(dueDate: due, estimated: estimated, cycleSource: source, lastVisitDate: last),
    )!;

    test('지남·곧·오늘·어림의 줄', () {
      expect(revisitRowLine(item(), today), '6주마다 · 5일 지남');
      expect(revisitRowLine(item(due: '2026-11-20'), today), '6주마다 · 3일 뒤쯤');
      expect(revisitRowLine(item(due: '2026-11-17'), today), '6주마다 · 오늘쯤');
      // 어림이면 주기를 말하지 않고 지난 사실만 — 36일 전 → 5주 전.
      expect(
        revisitRowLine(item(source: 'none', estimated: true, last: '2026-10-12'), today),
        '5주 전에 왔어요 · 어림',
      );
    });

    NextVisitDraft draft(String startsAt) =>
        NextVisitDraft.fromJson(nextDraftJson(startsAt: startsAt));

    test('지난 초안의 날은 내일 이후의 가장 가까운 같은 요일로, 시각은 그대로', () {
      final moved = draftForBooking(draft('2026-11-10T14:30:00+09:00'), today);
      expect(moved.startsAt.wall, DateTime(2026, 11, 24, 14, 30));
      // 오늘이 그 요일이어도 다음 주다(오늘 지난 시각에 잡지 않는다).
      expect(draftForBooking(draft('2026-11-17T10:00:00+09:00'), today).startsAt.wall,
          DateTime(2026, 11, 24, 10, 0));
      // 수요일 초안 → 내일(수)
      expect(draftForBooking(draft('2026-11-04T09:00:00+09:00'), today).startsAt.wall,
          DateTime(2026, 11, 18, 9, 0));
      // 앞날이면 그대로
      expect(draftForBooking(draft('2026-11-20T14:00:00+09:00'), today).startsAt.wall,
          DateTime(2026, 11, 20, 14, 0));
    });
  });
}
