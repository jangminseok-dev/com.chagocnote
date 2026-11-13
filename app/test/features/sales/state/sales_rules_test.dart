// 매출 탭의 문장·기간 규칙 — 값은 손으로 적는다.
import 'package:chagocnote/features/sales/api/sales_models.dart';
import 'package:chagocnote/features/sales/state/sales_rules.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/sales_fixtures.dart';

SalesSummary _s({
  SalesSpan asked = SalesSpan.month,
  String span = 'month',
  String start = '2026-11-01',
  String end = '2026-11-30',
  String? elapsedEnd = '2026-11-14',
  int revenue = 3250000,
  Map<String, dynamic>? previous = const {'start': '2026-10-01', 'end': '2026-10-14', 'revenue': 2830000},
  Map<String, dynamic>? yearAgo,
  int? goal,
  Map<String, dynamic>? pets,
  List<Map<String, dynamic>>? buckets,
  int visitCount = 48,
}) => SalesSummary.fromJson(
  salesSummaryJson(
    span: span, start: start, end: end, elapsedEnd: elapsedEnd, revenue: revenue, previous: previous,
    yearAgo: yearAgo, goal: goal, pets: pets, buckets: buckets, visitCount: visitCount,
  ),
  asked,
);

Map<String, dynamic> _window(String start, String end, int revenue) => {
  'start': start,
  'end': end,
  'revenue': revenue,
};

void main() {
  test('금액에는 세 자리마다 쉼표를 넣는다', () {
    expect(won(3250000), '3,250,000');
    expect(won(0), '0');
    expect(won(999), '999');
    expect(won(1000), '1,000');
    expect(won(99999999), '99,999,999');
    expect(won(-5000), '-5,000');
  });

  test('만 원으로 나누어떨어지면 만 원으로, 아니면 원으로 말한다', () {
    expect(amountPhrase(420000), '42만 원');
    expect(amountPhrase(10000), '1만 원');
    expect(amountPhrase(5000000), '500만 원');
    expect(amountPhrase(100000000), '10,000만 원');
    expect(amountPhrase(425000), '425,000원');
    expect(amountPhrase(9000), '9,000원');
    expect(amountPhrase(0), '0원');
  });

  test('기간을 앞뒤로 옮긴다', () {
    expect(shiftAnchor(SalesSpan.day, DateTime(2026, 11, 1), -1), DateTime(2026, 10, 31));
    expect(shiftAnchor(SalesSpan.week, DateTime(2026, 11, 14), -1), DateTime(2026, 11, 7));
    expect(shiftAnchor(SalesSpan.week, DateTime(2026, 12, 30), 1), DateTime(2027, 1, 6));
    expect(shiftAnchor(SalesSpan.month, DateTime(2026, 1, 31), -1), DateTime(2025, 12, 1));
    expect(shiftAnchor(SalesSpan.month, DateTime(2026, 3, 31), -1), DateTime(2026, 2, 1));
    expect(shiftAnchor(SalesSpan.month, DateTime(2026, 12, 15), 1), DateTime(2027, 1, 1));
    expect(shiftAnchor(SalesSpan.year, DateTime(2028, 2, 29), -1), DateTime(2027, 1, 1));
  });

  test('이번 기간에서는 다음으로 가지 못한다', () {
    final today = DateTime(2026, 11, 14); // 토요일
    expect(canGoNext(SalesSpan.day, DateTime(2026, 11, 14), today), isFalse);
    expect(canGoNext(SalesSpan.day, DateTime(2026, 11, 13), today), isTrue);
    expect(canGoNext(SalesSpan.week, DateTime(2026, 11, 9), today), isFalse); // 이번 주의 월요일
    expect(canGoNext(SalesSpan.week, DateTime(2026, 11, 8), today), isTrue); // 지난주의 일요일
    expect(canGoNext(SalesSpan.month, DateTime(2026, 11, 1), today), isFalse);
    expect(canGoNext(SalesSpan.month, DateTime(2026, 10, 31), today), isTrue);
    expect(canGoNext(SalesSpan.year, DateTime(2026, 1, 1), today), isFalse);
    expect(canGoNext(SalesSpan.year, DateTime(2025, 12, 31), today), isTrue);
    // 일요일인 오늘 — 다음 주는 내일부터라 아직 못 간다.
    expect(canGoNext(SalesSpan.week, DateTime(2026, 11, 15), DateTime(2026, 11, 15)), isFalse);
  });

  test('기간의 제목', () {
    final month = periodTitle(_s());
    expect((month.enMonth, month.enText, month.small, month.ko), (11, null, '2026', null));
    final year = periodTitle(_s(span: 'year', start: '2026-01-01', end: '2026-12-31'));
    expect((year.enMonth, year.enText, year.small, year.ko), (null, '2026', null, null));
    final week = periodTitle(_s(span: 'week', start: '2026-11-09', end: '2026-11-15'));
    expect(week.ko, '11월 9일 – 15일');
    final acrossMonths = periodTitle(_s(span: 'week', start: '2026-12-28', end: '2027-01-03'));
    expect(acrossMonths.ko, '12월 28일 – 1월 3일');
    final day = periodTitle(_s(span: 'day', start: '2026-11-14', end: '2026-11-14'));
    expect(day.ko, '11월 14일 토요일');
  });

  group('앞 기간과 견주는 문장', () {
    test('진행 중인 달은 지난달 같은 날까지와 견준다', () {
      expect(compareSentence(_s()), '지난달 14일까지보다 42만 원 많아요.');
      expect(
        compareSentence(_s(revenue: 2405000)),
        '지난달 14일까지보다 425,000원 적어요.',
      );
      expect(compareSentence(_s(revenue: 2830000)), '지난달 14일까지와 같아요.');
    });

    test('진행 중인 달이 지난달보다 길면 견준 창의 끝날을 말한다', () {
      final march = _s(
        start: '2026-03-01', end: '2026-03-31', elapsedEnd: '2026-03-30', revenue: 100000,
        previous: _window('2026-02-01', '2026-02-28', 60000),
      );
      expect(compareSentence(march), '지난달 28일까지보다 4만 원 많아요.');
    });

    test('지난 기간은 그 앞 기간 전체와 견준다', () {
      final october = _s(
        start: '2026-10-01', end: '2026-10-31', elapsedEnd: '2026-10-31', revenue: 5000000,
        previous: _window('2026-09-01', '2026-09-30', 4000000),
      );
      expect(compareSentence(october), '그 전 달보다 100만 원 많아요.');
      expect(
        compareSentence(_s(
          start: '2026-10-01', end: '2026-10-31', elapsedEnd: '2026-10-31', revenue: 4000000,
          previous: _window('2026-09-01', '2026-09-30', 4000000),
        )),
        '그 전 달과 같아요.',
      );
    });

    test('일·주·연의 이름', () {
      SalesSummary of(String span, String start, String end, String elapsed, Map<String, dynamic> previous) =>
          _s(span: span, start: start, end: end, elapsedEnd: elapsed, revenue: 200000, previous: previous);

      expect(
        compareSentence(of('day', '2026-11-14', '2026-11-14', '2026-11-14', _window('2026-11-13', '2026-11-13', 100000))),
        '그 전날보다 10만 원 많아요.',
      );
      expect(
        compareSentence(of('week', '2026-11-09', '2026-11-15', '2026-11-11', _window('2026-11-02', '2026-11-04', 300000))),
        '지난주 같은 요일까지보다 10만 원 적어요.',
      );
      expect(
        compareSentence(of('week', '2026-11-02', '2026-11-08', '2026-11-08', _window('2026-10-26', '2026-11-01', 200000))),
        '그 전 주와 같아요.',
      );
      expect(
        compareSentence(of('year', '2026-01-01', '2026-12-31', '2026-11-14', _window('2025-01-01', '2025-11-14', 100000))),
        '작년 11월 14일까지보다 10만 원 많아요.',
      );
      expect(
        compareSentence(of('year', '2025-01-01', '2025-12-31', '2025-12-31', _window('2024-01-01', '2024-12-31', 200000))),
        '그 전 해와 같아요.',
      );
    });

    test('견줄 것이 없거나 앞 기간이 0 이면 문장이 없다', () {
      expect(compareSentence(_s(previous: null)), isNull);
      expect(compareSentence(_s(previous: _window('2026-10-01', '2026-10-14', 0))), isNull);
      expect(compareSentence(_s(elapsedEnd: null, previous: null)), isNull);
    });

    test('작년 줄', () {
      expect(yearAgoSentence(_s()), isNull);
      expect(
        yearAgoSentence(_s(yearAgo: _window('2025-11-01', '2025-11-14', 2000000))),
        '작년 같은 때보다 125만 원 많아요.',
      );
      expect(
        yearAgoSentence(_s(revenue: 1000000, yearAgo: _window('2025-11-01', '2025-11-14', 2000000))),
        '작년 같은 때보다 100만 원 적어요.',
      );
      expect(
        yearAgoSentence(_s(revenue: 2000000, yearAgo: _window('2025-11-01', '2025-11-14', 2000000))),
        '작년 같은 때와 같아요.',
      );
    });
  });

  test('목표 문장과 진행 — 퍼센트는 버리고 진행은 0 과 1 사이로 자른다', () {
    expect(goalSentence(_s()), isNull);
    expect(goalProgress(_s()), 0);
    final sixtyFive = _s(goal: 5000000);
    expect(goalSentence(sixtyFive), '이번 달 목표 500만 원의 65%');
    expect(goalProgress(sixtyFive), closeTo(0.65, 0.0001));
    expect(goalSentence(_s(goal: 5000000, revenue: 0)), '이번 달 목표 500만 원의 0%');
    final over = _s(goal: 2500000);
    expect(goalSentence(over), '이번 달 목표 250만 원의 130%');
    expect(goalProgress(over), 1);
    expect(goalSentence(_s(goal: 3333333, revenue: 1111111)), '이번 달 목표 3,333,333원의 33%');
  });

  test('다녀간 아이 줄', () {
    expect(facesLine(_s()), '41마리가 48번 다녀갔어요');
    final ownerOnly = _s(pets: {'count': 0, 'new_count': 0, 'returning_count': 0}, visitCount: 2);
    expect(facesLine(ownerOnly), '2번 다녀갔어요');
  });

  test('처음 고르는 칸 — 오늘 방문이 있으면 오늘, 없으면 방문이 있는 마지막 칸, 그것도 없으면 없다', () {
    expect(selectedBucketKey(_s(), DateTime(2026, 11, 14)), '2026-11-14');
    // 오늘은 아직 방문이 없다 — "0원 0건" 카드를 띄우지 않고 어제를 고른다.
    final quietToday = _s(buckets: [
      {'key': '2026-11-13', 'revenue': 100000, 'visit_count': 4, 'future': false, 'pets': <Map<String, dynamic>>[]},
      {'key': '2026-11-14', 'revenue': 0, 'visit_count': 0, 'future': false, 'pets': <Map<String, dynamic>>[]},
      {'key': '2026-11-15', 'revenue': 0, 'visit_count': 0, 'future': true, 'pets': <Map<String, dynamic>>[]},
    ]);
    expect(selectedBucketKey(quietToday, DateTime(2026, 11, 14)), '2026-11-13');
    // 지난 달을 보면 방문이 있는 마지막 날.
    expect(selectedBucketKey(_s(), DateTime(2026, 12, 20)), '2026-11-14');
    final empty = _s(buckets: [
      {'key': '2026-11-01', 'revenue': 0, 'visit_count': 0, 'future': false, 'pets': <Map<String, dynamic>>[]},
    ]);
    expect(selectedBucketKey(empty, DateTime(2026, 12, 20)), isNull);
    expect(selectedBucketKey(_s(buckets: []), DateTime(2026, 11, 14)), isNull);
    // 연 보기의 막대는 고르는 것이 아니라 그 달로 간다.
    expect(selectedBucketKey(_s(span: 'year', start: '2026-01-01', end: '2026-12-31'), DateTime(2026, 11, 14)), isNull);
  });

  test('결제 수단의 이름 — 모르는 값은 기타다', () {
    expect(paymentLabel('card'), '카드');
    expect(paymentLabel('cash'), '현금');
    expect(paymentLabel('transfer'), '계좌'); // 기록 화면과 같은 말
    expect(paymentLabel('none'), '미선택');
    expect(paymentLabel('point'), '기타');
  });

  test('막대의 높이 비율 — 가장 큰 칸이 1 이고 모두 0 이거나 음수여도 0 과 1 사이다', () {
    expect(barRatios([0, 50, 100]), [0, 0.5, 1]);
    expect(barRatios([0, 0, 0]), [0, 0, 0]);
    expect(barRatios([]), isEmpty);
    expect(barRatios([-10, 20]), [0, 1]);
  });

  group('목표 칸 읽기', () {
    test('숫자만 읽고 빈 칸과 0 은 목표 없음이다', () {
      expect(parseGoal('5000000'), 5000000);
      expect(parseGoal(' 5,000,000원 '), 5000000);
      expect(parseGoal(''), isNull);
      expect(parseGoal('   '), isNull);
      expect(parseGoal('0'), isNull);
      expect(parseGoal('000'), isNull);
      expect(parseGoal('원'), isNull);
      expect(parseGoal('1'), 1);
    });

    test('1억까지 받고 그 위는 막는다', () {
      expect(parseGoal('100000000'), 100000000);
      expect(() => parseGoal('100000001'), throwsFormatException);
      expect(() => parseGoal('99999999999999999999999999'), throwsFormatException);
    });
  });

  test('마지막으로 다녀간 지 — 이레 안은 날, 그 밖은 주(버림)', () {
    final today = DateTime(2026, 11, 14, 15, 30);
    expect(sinceLabel(DateTime(2026, 11, 14), today), '오늘');
    expect(sinceLabel(DateTime(2026, 11, 13), today), '1일 전');
    expect(sinceLabel(DateTime(2026, 11, 8), today), '6일 전');
    expect(sinceLabel(DateTime(2026, 11, 7), today), '1주 전');
    expect(sinceLabel(DateTime(2026, 9, 18), today), '8주 전'); // 57일
    expect(sinceLabel(DateTime(2026, 9, 12), today), '9주 전'); // 63일
    expect(sinceLabel(DateTime(2025, 11, 14), today), '52주 전');
    expect(sinceLabel(DateTime(2026, 11, 20), today), '오늘', reason: '앞날이 와도 죽지 않는다');
  });

  test('방문 목록의 제목', () {
    expect(visitsTitle(SalesVisitFilter.unrecorded), '금액을 적지 않은 방문');
    expect(visitsTitle(SalesVisitFilter.noShow), '노쇼한 방문');
    expect(visitsTitle(SalesVisitFilter.canceled), '취소한 방문');
    expect(visitsTitle(SalesVisitFilter.menu, menuName: '전체 미용'), '전체 미용 한 방문');
    expect(visitsTitle(SalesVisitFilter.menu), '메뉴의 방문');
    expect(visitsTitle(SalesVisitFilter.menu, menuName: ''), '메뉴의 방문');
  });

  group('요약 공유 글', () {
    test('진행 중인 달 — 설계 3.4 의 네 줄', () {
      expect(
        shareText('Hiss Haus', _s()),
        'Hiss Haus · 2026년 11월 (14일까지)\n'
        '매출 3,250,000원 · 방문 48건\n'
        '카드 2,400,000원 / 현금 550,000원 / 계좌 300,000원\n'
        '전체 미용 2,100,000원(30건) · 목욕 750,000원(15건) · 스파 400,000원(8건)',
      );
    });

    test('아이의 이름이 한 글자도 없다', () {
      final text = shareText('Hiss Haus', _s());
      for (final name in ['보리', '코코', '두부', '몽이']) {
        expect(text.contains(name), isFalse, reason: name);
      }
    });

    test('기간의 머리 — 지난 달, 일, 주, 달을 걸친 주, 연', () {
      String head(SalesSummary s) => shareText('매장', s).split('\n').first;
      expect(
        head(_s(start: '2026-10-01', end: '2026-10-31', elapsedEnd: '2026-10-31')),
        '매장 · 2026년 10월',
      );
      expect(
        head(_s(asked: SalesSpan.day, span: 'day', start: '2026-11-14', end: '2026-11-14')),
        '매장 · 2026년 11월 14일',
      );
      expect(
        head(_s(asked: SalesSpan.week, span: 'week', start: '2026-11-09', end: '2026-11-15')),
        '매장 · 2026년 11월 9일~15일',
      );
      expect(
        head(_s(asked: SalesSpan.week, span: 'week', start: '2026-10-26', end: '2026-11-01', elapsedEnd: '2026-11-01')),
        '매장 · 2026년 10월 26일~11월 1일',
      );
      expect(
        head(_s(asked: SalesSpan.year, span: 'year', start: '2026-01-01', end: '2026-12-31')),
        '매장 · 2026년 (11월 14일까지)',
      );
      expect(
        head(_s(asked: SalesSpan.year, span: 'year', start: '2025-01-01', end: '2025-12-31', elapsedEnd: '2025-12-31')),
        '매장 · 2025년',
      );
      expect(
        head(_s(start: '2026-12-01', end: '2026-12-31', elapsedEnd: null)),
        '매장 · 2026년 12월',
        reason: '앞날의 기간',
      );
    });

    test('조정·미선택·기타 수단이 든 요약, 결제 수단과 메뉴가 없으면 그 줄이 없다', () {
      final mixed = SalesSummary.fromJson(
        salesSummaryJson(
          revenue: 90000,
          visitCount: 2,
          payments: [
            {'method': 'none', 'amount': 40000},
            {'method': 'point', 'amount': 50000},
          ],
          menus: [
            {'menu_id': 1, 'name': '목욕', 'amount': 100000, 'count': 2, 'pet': null},
            {'menu_id': null, 'name': '조정', 'amount': -10000, 'count': 0, 'pet': null},
          ],
        ),
        SalesSpan.month,
      );
      expect(shareText('매장', mixed).split('\n').sublist(1), [
        '매출 90,000원 · 방문 2건',
        '미선택 40,000원 / 기타 50,000원',
        '목욕 100,000원(2건) · 조정 -10,000원',
      ]);

      final empty = SalesSummary.fromJson(
        salesSummaryJson(revenue: 0, visitCount: 0, payments: [], menus: []),
        SalesSpan.month,
      );
      expect(shareText('매장', empty), '매장 · 2026년 11월 (14일까지)\n매출 0원 · 방문 0건');
    });
  });

  test('오늘의 일 보기는 어제와 견준다 — 지난 날은 그 전날', () {
    final day = _s(
      asked: SalesSpan.day, span: 'day', start: '2026-11-14', end: '2026-11-14', revenue: 510000,
      previous: _window('2026-11-13', '2026-11-13', 440000),
    );
    expect(compareSentence(day, today: DateTime(2026, 11, 14, 9)), '어제보다 7만 원 많아요.');
    expect(compareSentence(day, today: DateTime(2026, 11, 15)), '그 전날보다 7만 원 많아요.');
    expect(compareSentence(day), '그 전날보다 7만 원 많아요.');
    expect(
      compareSentence(day.span == SalesSpan.day ? _s(revenue: 3250000) : day, today: DateTime(2026, 11, 14)),
      '지난달 14일까지보다 42만 원 많아요.',
      reason: '월 보기는 그대로',
    );
  });

  test('목표는 이번 달의 월 보기에서만', () {
    final today = DateTime(2026, 11, 14);
    expect(isGoalPeriod(_s(), today), isTrue);
    expect(isGoalPeriod(_s(start: '2026-10-01', end: '2026-10-31', elapsedEnd: '2026-10-31'), today), isFalse);
    expect(isGoalPeriod(_s(start: '2025-11-01', end: '2025-11-30', elapsedEnd: '2025-11-30'), today), isFalse);
    expect(
      isGoalPeriod(_s(asked: SalesSpan.week, span: 'week', start: '2026-11-09', end: '2026-11-15'), today),
      isFalse,
    );
    expect(
      isGoalPeriod(_s(asked: SalesSpan.year, span: 'year', start: '2026-01-01', end: '2026-12-31'), today),
      isFalse,
    );
  });

  group('방문 목록의 주소', () {
    final today = DateTime(2026, 11, 14, 22);

    test('요약의 기간이 그대로 가고 다시 읽으면 같은 조건이다', () {
      final october = _s(start: '2026-10-01', end: '2026-10-31', elapsedEnd: '2026-10-31');
      final path = visitsPath(october, SalesVisitFilter.menu, menuId: 2, menuName: '목욕 & 스파');
      final uri = Uri.parse(path);

      expect(uri.path, '/sales/visits');
      expect(uri.queryParameters, {
        'span': 'month', 'anchor': '2026-10-01', 'filter': 'menu', 'menu_id': '2', 'menu': '목욕 & 스파',
      });
      expect(visitsQueryOf(uri.queryParameters, today), (
        span: SalesSpan.month,
        anchor: DateTime(2026, 10, 1),
        filter: SalesVisitFilter.menu,
        menuId: 2,
      ));
      expect(Uri.parse(visitsPath(october, SalesVisitFilter.noShow)).queryParameters.containsKey('menu_id'), isFalse);
    });

    test('깨진 질의는 기본값이다', () {
      const fallback = (span: SalesSpan.month, filter: SalesVisitFilter.unrecorded, menuId: null);
      for (final query in <Map<String, String>>[
        {},
        {'span': 'decade', 'anchor': 'yesterday', 'filter': 'everything'},
        {'span': '', 'anchor': '2026-02-31', 'filter': 'menu'},
        {'anchor': '2026-13-01', 'filter': 'menu', 'menu_id': 'abc'},
        {'anchor': '20261114'},
      ]) {
        final read = visitsQueryOf(query, today);
        expect((span: read.span, filter: read.filter, menuId: read.menuId), fallback, reason: '$query');
        expect(read.anchor, DateTime(2026, 11, 14), reason: '$query');
      }
    });

    test('메뉴가 아닌 종류에 붙은 메뉴 ID 는 버린다', () {
      final read = visitsQueryOf({'filter': 'no_show', 'menu_id': '4', 'span': 'year'}, today);
      expect((read.span, read.filter, read.menuId), (SalesSpan.year, SalesVisitFilter.noShow, null));
    });
  });

  test('목록 줄의 날짜', () {
    expect(visitDateLabel(DateTime(2026, 11, 14)), '11월 14일 토');
    expect(visitDateLabel(DateTime(2026, 11, 2)), '11월 2일 월');
    expect(visitDateLabel(DateTime(2026, 11, 15)), '11월 15일 일');
  });
}
