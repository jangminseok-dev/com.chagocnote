// 홈의 [매출] 탭 — 사장에게는 기간의 매출, 직원에게는 안내(⑧-2). 오늘은 2026-11-14 토요일이다.
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:chagocnote/features/sales/screens/sales_tab.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/sales_fixtures.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_test_backend.dart';

const _summaryPath = 'GET /v1/shops/3/sales/summary';

/// 요약을 주는 가짜 서버. [summary]가 요청(기간·anchor)을 보고 응답을 정한다.
class _World {
  _World({
    String role = 'owner',
    FakeResponse Function(RequestOptions options)? summary,
  }) {
    final backend = VisitTestBackend({
      _summaryPath: (o, b) {
        asked.add((o.queryParameters['span'] as String, o.queryParameters['anchor'] as String));
        return (summary ?? _default)(o);
      },
    });
    setup = CustomerTestSetup(
      backend.call,
      role: role,
      overrides: [
        todayProvider.overrideWithValue(DateTime(2026, 11, 14)),
        mediaImagesProvider.overrideWithValue(images),
      ],
    );
  }

  late final CustomerTestSetup setup;
  final images = FakeMediaImages();

  /// 서버가 받은 (기간, anchor).
  final asked = <(String, String)>[];

  static FakeResponse _default(RequestOptions o) =>
      FakeResponse(statusCode: 200, data: salesSummaryJson());

  Future<void> open(WidgetTester tester, {Size size = const Size(390, 2600)}) async {
    tester.view.physicalSize = size;
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(setup.container.dispose);
    await tester.pumpWidget(customerRouterApp(setup.container));
    await settle(tester);
    await tester.tap(find.text(AppStrings.tabSales));
    await settle(tester);
  }
}

FakeResponse _ok(Map<String, dynamic> json) => FakeResponse(statusCode: 200, data: json);

Finder _bar(String label) => find.bySemanticsLabel(label);

Map<String, dynamic> _weekJson() => salesSummaryJson(
  span: 'week', start: '2026-11-09', end: '2026-11-15', revenue: 1770000, weekdays: null,
  previous: {'start': '2026-11-02', 'end': '2026-11-07', 'revenue': 1470000},
  buckets: salesNovemberBuckets().sublist(8, 15),
);

Map<String, dynamic> _yearJson() => salesSummaryJson(
  span: 'year', start: '2026-01-01', end: '2026-12-31', revenue: 30000000,
  previous: {'start': '2025-01-01', 'end': '2025-11-14', 'revenue': 20000000},
  buckets: [
    for (var m = 1; m <= 12; m++)
      {
        'key': '2026-${m.toString().padLeft(2, '0')}',
        'revenue': m <= 11 ? m * 500000 : 0,
        'visit_count': m <= 11 ? m * 5 : 0,
        'future': m > 11,
        'pets': <Map<String, dynamic>>[],
      },
  ],
);

Map<String, dynamic> _emptyJson() => salesSummaryJson(
  revenue: 0, visitCount: 0, pricedCount: 0, average: null, previous: null, report: null,
  pets: {'count': 0, 'new_count': 0, 'returning_count': 0, 'faces': [], 'new': [], 'returning': []},
  buckets: [
    for (final b in salesNovemberBuckets()) {...b, 'revenue': 0, 'visit_count': 0, 'pets': <Map<String, dynamic>>[]},
  ],
  payments: [], menus: [], regulars: [], weekdays: [0, 0, 0, 0, 0, 0, 0],
  bookings: {'remaining': 4, 'expected_amount': null, 'no_show': 0, 'canceled': 1},
  unrecordedCount: 0, duePetCount: 2,
);

void main() {
  testWidgets('직원에게는 "매출은 사장님만 볼 수 있어요." 만 보이고 요약을 부르지 않는다', (tester) async {
    final w = _World(role: 'staff');
    await w.open(tester);

    expect(find.text(AppStrings.salesOwnerOnly), findsOneWidget);
    expect(find.byKey(const Key('sales-revenue')), findsNothing);
    expect(find.text(AppStrings.salesSpanYear), findsNothing);
    expect(w.asked, isEmpty);
    expect(find.text('Hiss Haus'), findsOneWidget);
  });

  testWidgets('사장은 이번 달의 매출과 견준 문장과 다녀간 아이들을 본다', (tester) async {
    final w = _World();
    await w.open(tester);

    expect(w.asked, [('month', '2026-11-14')]);
    expect(find.text('Hiss Haus'), findsOneWidget);
    expect(find.text('November'), findsOneWidget);
    expect(find.text('2026'), findsOneWidget);
    expect(tester.widget<Text>(find.byKey(const Key('sales-revenue'))).data, '3,250,000');
    expect(find.text('지난달 14일까지보다 42만 원 많아요.'), findsOneWidget);
    expect(find.text('41마리가 48번 다녀갔어요'), findsOneWidget);
    expect(find.text('한 번에 평균 67,708원'), findsOneWidget);
    expect(find.byKey(const Key('sales-chart')), findsOneWidget);
    // 구역들
    for (final title in [
      AppStrings.salesPayment, AppStrings.salesMenu, AppStrings.salesGuests,
      AppStrings.salesBookings, AppStrings.salesWeekday, AppStrings.salesReport,
    ]) {
      expect(find.text(title), findsOneWidget, reason: title);
    }
    expect(find.text('카드'), findsOneWidget);
    expect(find.text('2,400,000'), findsOneWidget);
    expect(find.text('73%'), findsOneWidget); // 2,400,000 / 3,250,000 — 버림
    expect(find.text('전체 미용'), findsOneWidget);
    expect(find.text('30건'), findsOneWidget);
    expect(find.text(AppStrings.salesNewPets), findsOneWidget);
    expect(find.text('9번'), findsOneWidget);
    expect(find.text('정가로 약 84만 원'), findsOneWidget);
    expect(find.text('완료한 48건 가운데 40건에 알림장을 보냈고, 보호자가 31건을 열어 봤어요.'), findsOneWidget);
    expect(find.text('다시 올 때가 지난 아이 7마리'), findsOneWidget);
    expect(find.text('금액을 적지 않은 완료 방문 3건'), findsOneWidget);
    // 작년 줄과 목표는 오지 않았다.
    expect(find.textContaining('작년 같은 때'), findsNothing);
    expect(find.byKey(const Key('sales-goal-line')), findsNothing);
  });

  testWidgets('처음에는 오늘의 칸이 골라져 있고 그날의 카드가 보인다', (tester) async {
    final w = _World();
    await w.open(tester);

    final card = find.byKey(const Key('sales-day-card'));
    expect(card, findsOneWidget);
    expect(find.descendant(of: card, matching: find.text('510,000원')), findsOneWidget);
    expect(find.descendant(of: card, matching: find.text('보리 · 코코 · 두부')), findsOneWidget);
    expect(find.descendant(of: card, matching: find.text(AppStrings.dayHeading(14, 6))), findsOneWidget);
    // 사진 주소는 사진 프로바이더를 거친다.
    expect(w.images.urls, contains('https://media.test/101.jpg'));
  });

  testWidgets('칸을 누르면 그날의 카드로 바뀌고, 카드를 누르면 그날의 하루 화면으로 간다', (tester) async {
    final w = _World();
    await w.open(tester);

    await tester.tap(_bar(AppStrings.salesBarLabel('6일', '310,000')));
    await settle(tester);

    final card = find.byKey(const Key('sales-day-card'));
    expect(find.descendant(of: card, matching: find.text('310,000원')), findsOneWidget);
    expect(find.descendant(of: card, matching: find.text(AppStrings.dayHeading(6, 5))), findsOneWidget);
    expect(w.asked, hasLength(1), reason: '칸을 고를 때는 다시 읽지 않는다');

    await tester.tap(card);
    await settle(tester);
    expect(find.byKey(ScreenKeys.day), findsOneWidget);
  });

  testWidgets('아직 오지 않은 칸은 눌리지 않는다', (tester) async {
    final w = _World();
    await w.open(tester);

    await tester.tap(_bar(AppStrings.salesBarLabel('20일', '0')), warnIfMissed: false);
    await settle(tester);

    final card = find.byKey(const Key('sales-day-card'));
    expect(find.descendant(of: card, matching: find.text('510,000원')), findsOneWidget);
  });

  testWidgets('기간을 [주]로 바꾸면 주로 다시 읽고, ‹ 는 7일 앞으로, 이번 기간에서 › 는 눌리지 않는다', (tester) async {
    final w = _World(
      summary: (o) => _ok(o.queryParameters['span'] == 'week' ? _weekJson() : salesSummaryJson()),
    );
    await w.open(tester);

    // 이번 달 — 다음으로 가지 못한다.
    await tester.tap(find.bySemanticsLabel(AppStrings.salesNext), warnIfMissed: false);
    await settle(tester);
    expect(w.asked, [('month', '2026-11-14')]);

    await tester.tap(find.text(AppStrings.salesSpanWeek));
    await settle(tester);
    expect(w.asked.last, ('week', '2026-11-14'));
    expect(find.text('11월 9일 – 15일'), findsOneWidget);
    expect(find.text('지난주 같은 요일까지보다 30만 원 많아요.'), findsOneWidget);
    expect(find.text(AppStrings.salesWeekday), findsNothing, reason: '요일 구역은 월·연에만');

    await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
    await settle(tester);
    expect(w.asked.last, ('week', '2026-11-07'));

    // 지난 주에서는 다음으로 갈 수 있다.
    await tester.tap(find.bySemanticsLabel(AppStrings.salesNext));
    await settle(tester);
    expect(w.asked.last, ('week', '2026-11-14'));
  });

  testWidgets('월 보기에서 ‹ 를 누르면 지난달의 1일로 읽는다', (tester) async {
    final w = _World();
    await w.open(tester);

    await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
    await settle(tester);

    expect(w.asked.last, ('month', '2026-10-01'));
  });

  testWidgets('연 보기에서 막대를 누르면 그 달의 월 보기로 바뀐다', (tester) async {
    final w = _World(
      summary: (o) => _ok(o.queryParameters['span'] == 'year' ? _yearJson() : salesSummaryJson()),
    );
    await w.open(tester);
    await tester.tap(find.text(AppStrings.salesSpanYear));
    await settle(tester);
    expect(w.asked.last, ('year', '2026-11-14'));
    expect(find.text('작년 11월 14일까지보다 1,000만 원 많아요.'), findsOneWidget);
    expect(find.byKey(const Key('sales-day-card')), findsNothing, reason: '연 보기에는 고른 날 카드가 없다');

    await tester.tap(_bar(AppStrings.salesBarLabel('3월', '1,500,000')));
    await settle(tester);

    expect(w.asked.last, ('month', '2026-03-01'));
  });

  testWidgets('일 보기에는 차트가 없다', (tester) async {
    final w = _World(
      summary: (o) => _ok(
        o.queryParameters['span'] == 'day'
            ? salesSummaryJson(
                span: 'day', start: '2026-11-14', end: '2026-11-14', revenue: 510000, buckets: [], weekdays: null,
                previous: {'start': '2026-11-13', 'end': '2026-11-13', 'revenue': 440000},
              )
            : salesSummaryJson(),
      ),
    );
    await w.open(tester);
    // '일'은 요일 막대의 일요일에도 있다 — 기간 세그먼트의 것은 맨 앞이다.
    await tester.tap(find.text(AppStrings.salesSpanDay).first);
    await settle(tester);

    expect(find.text('11월 14일 토요일'), findsOneWidget);
    expect(find.text('그 전날보다 7만 원 많아요.'), findsOneWidget);
    expect(find.byKey(const Key('sales-chart')), findsNothing);
    expect(find.byKey(const Key('sales-day-card')), findsNothing);
  });

  testWidgets('목표가 있으면 문장과 진행선이 있고, 작년 줄은 올 때만 있다', (tester) async {
    final w = _World(
      summary: (o) => _ok(salesSummaryJson(
        goal: 5000000,
        yearAgo: {'start': '2025-11-01', 'end': '2025-11-14', 'revenue': 2000000},
      )),
    );
    await w.open(tester);

    expect(find.text('이번 달 목표 500만 원의 65%'), findsOneWidget);
    expect(find.byKey(const Key('sales-goal-line')), findsOneWidget);
    expect(find.text('작년 같은 때보다 125만 원 많아요.'), findsOneWidget);
  });

  testWidgets('조정·미선택 줄이 온 그대로 보이고 모르는 결제 수단은 기타다', (tester) async {
    final w = _World(
      summary: (o) => _ok(salesSummaryJson(
        revenue: 100000,
        payments: [
          {'method': 'card', 'amount': 60000},
          {'method': 'none', 'amount': 30000},
          {'method': 'point', 'amount': 20000}, // 합이 매출보다 크다 — 읽는 도중 저장된 것처럼
        ],
        menus: [
          {'menu_id': 1, 'name': '전체 미용', 'amount': 110000, 'count': 2, 'pet': null},
          {'menu_id': null, 'name': '조정', 'amount': -10000, 'count': 0, 'pet': null},
        ],
      )),
    );
    await w.open(tester);

    expect(find.text(AppStrings.salesPaymentNone), findsOneWidget);
    expect(find.text(AppStrings.salesPaymentOther), findsOneWidget);
    expect(find.text('조정'), findsOneWidget);
    expect(find.text('-10,000'), findsOneWidget);
    expect(find.text('0건'), findsNothing, reason: '조정 줄에는 건수가 없다');
    expect(tester.takeException(), isNull);
  });

  testWidgets('빈 기간은 안내가 보이고 예약과 다시 올 때가 지난 아이는 그대로다', (tester) async {
    final w = _World(summary: (o) => _ok(_emptyJson()));
    await w.open(tester);

    expect(find.text(AppStrings.salesEmptyTitle), findsOneWidget);
    expect(find.text(AppStrings.salesEmptyText), findsOneWidget);
    expect(find.byKey(const Key('sales-revenue')), findsNothing);
    expect(find.byKey(const Key('sales-chart')), findsNothing);
    for (final title in [
      AppStrings.salesPayment, AppStrings.salesMenu, AppStrings.salesGuests,
      AppStrings.salesWeekday, AppStrings.salesReport,
    ]) {
      expect(find.text(title), findsNothing, reason: title);
    }
    expect(find.text(AppStrings.salesBookings), findsOneWidget);
    expect(find.text(AppStrings.salesRemaining), findsOneWidget);
    expect(find.textContaining('정가로 약'), findsNothing, reason: '정가가 없으면 예상 금액이 없다');
    expect(find.text('다시 올 때가 지난 아이 2마리'), findsOneWidget);
    expect(find.textContaining('금액을 적지 않은'), findsNothing, reason: '0 이면 줄이 없다');
    expect(tester.takeException(), isNull);
  });

  testWidgets('매출은 0 인데 방문이 있으면(금액을 하나도 적지 않음) 빈 기간이 아니다', (tester) async {
    final w = _World(
      summary: (o) => _ok(salesSummaryJson(revenue: 0, pricedCount: 0, average: null, previous: null, payments: [], menus: [])),
    );
    await w.open(tester);

    expect(find.text(AppStrings.salesEmptyTitle), findsNothing);
    expect(tester.widget<Text>(find.byKey(const Key('sales-revenue'))).data, '0');
    expect(find.textContaining('한 번에 평균'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('사진 없는 아이는 빈 사진 칸이다', (tester) async {
    final w = _World();
    await w.open(tester);

    final blank = find.byWidgetPredicate((widget) => widget is AppPhotoTile && widget.image == null);
    expect(blank, findsWidgets);
    expect(w.images.urls.toSet(), {'https://media.test/101.jpg', 'https://media.test/103.jpg'});
  });

  for (final width in [320.0, 390.0]) {
    testWidgets('아주 큰 금액과 긴 이름에도 넘치지 않는다 — 폭 $width', (tester) async {
      final long = '띄어쓰기없는아주긴메뉴이름' * 3;
      final w = _World(
        summary: (o) => _ok(salesSummaryJson(
          revenue: 99999999, average: 99999999,
          payments: [
            {'method': 'card', 'amount': 99999999},
          ],
          menus: [
            {'menu_id': 1, 'name': long, 'amount': 99999999, 'count': 999, 'pet': petCardJson(1, long)},
          ],
          regulars: [
            {'pet': petCardJson(1, long), 'visit_count': 999},
          ],
          bookings: {'remaining': 999, 'expected_amount': 99999999, 'no_show': 999, 'canceled': 999},
        )),
      );
      await w.open(tester, size: Size(width, 2600));

      expect(tester.widget<Text>(find.byKey(const Key('sales-revenue'))).data, '99,999,999');
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('읽기에 실패하면 원인 문구와 [다시 시도], 다시 시도하면 나온다', (tester) async {
    var fail = true;
    final w = _World(
      summary: (o) => fail ? const FakeResponse(statusCode: 503, data: 'x') : _ok(salesSummaryJson()),
    );
    await w.open(tester);

    expect(find.text('서버에 잠시 문제가 있어요. 잠시 뒤 다시 시도해 주세요.'), findsOneWidget);
    // 기간 고르기는 읽지 못해도 남아 있다.
    expect(find.text(AppStrings.salesSpanYear), findsOneWidget);

    fail = false;
    await tester.tap(find.byWidgetPredicate((widget) => widget is AppButton && widget.label == AppStrings.retry));
    await settle(tester);
    expect(find.byKey(const Key('sales-revenue')), findsOneWidget);
  });

  testWidgets('당겨서 새로고침하면 다시 읽는다', (tester) async {
    final w = _World();
    await w.open(tester, size: const Size(390, 844));

    await tester.fling(find.byKey(const Key('sales-revenue')), const Offset(0, 400), 1000);
    await settle(tester);

    expect(w.asked, [('month', '2026-11-14'), ('month', '2026-11-14')]);
  });

  testWidgets('이번에는 메뉴·노쇼·다시 올 때가 지난 아이 줄에 누를 것이 없다', (tester) async {
    final w = _World();
    await w.open(tester);

    // 화살표(›)는 고른 날 카드와 기간 이동에만 있다.
    expect(find.byIcon(Icons.chevron_right), findsNWidgets(2));
    await tester.tap(find.text('전체 미용'), warnIfMissed: false);
    await tester.tap(find.text('다시 올 때가 지난 아이 7마리'), warnIfMissed: false);
    await settle(tester);
    expect(find.byType(SalesTab), findsOneWidget);
    expect(find.byKey(ScreenKeys.home), findsOneWidget);
  });

  testWidgets('매출 탭 골든 — 월 보기 위', (tester) async {
    final w = _World(summary: (o) => _ok(salesSummaryJson(goal: 5000000)));
    await w.open(tester, size: const Size(390, 844));

    await expectLater(find.byKey(ScreenKeys.home), matchesGoldenFile('goldens/sales_month_top.png'));
  });

  testWidgets('매출 탭 골든 — 월 보기 아래', (tester) async {
    final w = _World(summary: (o) => _ok(salesSummaryJson(goal: 5000000)));
    await w.open(tester, size: const Size(390, 844));
    await tester.drag(find.byKey(const Key('sales-revenue')), const Offset(0, -620));
    await settle(tester);

    await expectLater(find.byKey(ScreenKeys.home), matchesGoldenFile('goldens/sales_month_bottom.png'));
  });

  testWidgets('매출 탭 골든 — 빈 기간', (tester) async {
    final w = _World(summary: (o) => _ok(_emptyJson()));
    await w.open(tester, size: const Size(390, 844));

    await expectLater(find.byKey(ScreenKeys.home), matchesGoldenFile('goldens/sales_empty.png'));
  });
}
