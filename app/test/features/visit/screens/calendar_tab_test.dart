import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_dashed_tile.dart';
import 'package:chagocnote/design/widgets/app_photo_fan.dart';
import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/features/visit/state/calendar_selection.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_fixtures.dart';
import '../../../support/visit_test_backend.dart';

final _today = [todayProvider.overrideWithValue(DateTime(2026, 9, 22))];

/// 9월 — 월요일 휴무, 15일(지난날) 3마리, 22일(오늘) 5마리, 25일(앞날) 예약 4,
/// 정리 안 된 예약 2건(가장 오래된 날 8월 30일).
VisitTestBackend _backend() => VisitTestBackend({
  'GET /v1/shops/3/visits/calendar': (o, b) {
    final month = o.queryParameters['month'] as String;
    if (month != '2026-09') {
      final parts = month.split('-').map(int.parse).toList();
      return FakeResponse(
        statusCode: 200,
        data: calendarJson(year: parts[0], month: parts[1]),
      );
    }
    return FakeResponse(
      statusCode: 200,
      data: calendarJson(
        days: {
          15: {'visit_count': 3, 'completed_count': 3},
          22: {'visit_count': 5, 'completed_count': 1, 'open_count': 4},
          25: {'visit_count': 4, 'open_count': 4},
          30: {'visit_count': 1, 'open_count': 1, 'unresolved_count': 1},
        },
        closedDays: {7, 14, 21, 28},
        unresolvedTotal: 2,
        oldestUnresolvedDate: '2026-08-30',
      ),
    );
  },
  'GET /v1/shops/3/visits': (o, b) {
    final date = o.queryParameters['date'] as String;
    return FakeResponse(
      statusCode: 200,
      data: dayJson(
        date: date,
        items: date == '2026-09-22'
            ? [
                dayItemJson(
                  visitJson(date: date, start: '10:00', status: 'completed'),
                ),
                dayItemJson(
                  visitJson(
                    visitId: 102,
                    date: date,
                    start: '13:00',
                    pet: visitPetJson(petId: 12, name: '보리'),
                  ),
                ),
              ]
            : date == '2026-09-25'
            ? [
                dayItemJson(
                  visitJson(
                    date: date,
                    start: '11:00',
                    pet: visitPetJson(name: '몽이'),
                  ),
                ),
              ]
            : [],
      ),
    );
  },
});

Future<void> _pumpHome(WidgetTester tester, CustomerTestSetup setup) async {
  tester.view.physicalSize = const Size(390, 844);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
  await tester.pumpWidget(customerRouterApp(setup.container));
  await settle(tester);
}

Finder _button(String label) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label == label);

void main() {
  testWidgets('지난날은 사진 자리 + 마릿수, 앞날은 점선 칸 + 예약 수, 휴무는 옅은 글자로 보인다', (
    tester,
  ) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    expect(find.text('09'), findsOneWidget);
    expect(find.text('September'), findsOneWidget);
    expect(find.text('2026'), findsOneWidget);
    // 지난날 15일과 오늘 22일은 사진 자리, 앞날 25·30일은 점선 칸.
    expect(find.byType(AppPhotoTile), findsNWidgets(2));
    expect(find.byType(AppDashedTile), findsNWidgets(2));
    expect(
      find.descendant(of: find.byType(AppPhotoTile), matching: find.text('5')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: find.byType(AppDashedTile), matching: find.text('4')),
      findsOneWidget,
    );
    expect(find.text(AppStrings.closedShort), findsNWidgets(4));
    expect(find.text(AppStrings.unresolvedBanner(2)), findsOneWidget);
    // '1'은 셋 — 1일 날짜 숫자, 30일 점선 타일의 예약 수, 30일 칸의 정리 안 된 예약 수.
    expect(find.text('1'), findsNWidgets(3));
  });

  testWidgets('완료 방문의 대표 사진이 있으면 칸에 보이고, 미리보기는 그날 사진을 부채꼴로 겹친다', (
    tester,
  ) async {
    final backend = _backend();
    backend.routes['GET /v1/shops/3/visits/calendar'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: calendarJson(
        days: {
          15: {
            'visit_count': 3,
            'completed_count': 3,
            'cover': thumbUrl(51),
            'covers': [thumbUrl(51), thumbUrl(52), thumbUrl(53)],
          },
          22: {
            'visit_count': 5,
            'completed_count': 1,
            'open_count': 4,
            'cover': thumbUrl(61),
            'covers': [thumbUrl(61)],
          },
          25: {'visit_count': 4, 'open_count': 4},
        },
      ),
    );
    final images = FakeMediaImages();
    final setup = CustomerTestSetup(
      backend.call,
      overrides: [..._today, mediaImagesProvider.overrideWithValue(images)],
    );
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    final tiles = tester.widgetList<AppPhotoTile>(find.byType(AppPhotoTile));
    expect(tiles.map((t) => t.image), everyElement(same(images.image)));
    expect(images.urls, containsAll([thumbUrl(51), thumbUrl(61)]));
    expect(
      tester.widget<AppPhotoFan>(find.byType(AppPhotoFan)).images,
      hasLength(1),
    );

    await tester.tap(find.bySemanticsLabel('9월 15일 화'));
    await settle(tester);
    expect(
      tester.widget<AppPhotoFan>(find.byType(AppPhotoFan)).images,
      hasLength(3),
    );

    await tester.tap(find.bySemanticsLabel('9월 25일 금'));
    await settle(tester);
    expect(find.byType(AppPhotoFan), findsNothing, reason: '사진 없는 날');
  });

  testWidgets('오늘이 골라져 있고 미리보기에 그날 줄이 보이며, 다른 날을 누르면 그날을 읽는다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    expect(find.text(AppStrings.dayHeading(22, 2)), findsOneWidget);
    expect(find.text(AppStrings.previewCounts(2, 1)), findsOneWidget);
    expect(find.text('두부'), findsOneWidget);
    expect(find.text('보리'), findsOneWidget);

    await tester.tap(find.bySemanticsLabel('9월 25일 금'));
    await settle(tester);

    expect(setup.container.read(selectedDateProvider), DateTime(2026, 9, 25));
    expect(find.text(AppStrings.dayHeading(25, 5)), findsOneWidget);
    expect(find.text('몽이'), findsOneWidget);
    final dayQueries = [
      for (final r in setup.adapter.requests)
        if (r.path == '/v1/shops/3/visits') r.queryParameters['date'],
    ];
    expect(dayQueries, ['2026-09-22', '2026-09-25']);
  });

  testWidgets('미리보기가 4줄을 넘으면 "외 N건"을 적는다', (tester) async {
    final backend = _backend();
    backend.routes['GET /v1/shops/3/visits'] = (o, b) => FakeResponse(
      statusCode: 200,
      data: dayJson(
        date: '2026-09-22',
        items: [
          for (var i = 0; i < 6; i++)
            dayItemJson(
              visitJson(
                visitId: 100 + i,
                date: '2026-09-22',
                start: '1$i:00',
                pet: visitPetJson(petId: 20 + i, name: '아이$i'),
              ),
              groupKey: 'g$i',
            ),
        ],
      ),
    );
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    expect(find.text('아이3'), findsOneWidget);
    expect(find.text('아이4'), findsNothing);
    expect(find.text(AppStrings.moreGroups(2)), findsOneWidget);
  });

  testWidgets('예약이 없는 날과 휴무일은 미리보기에 그렇게 적는다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    await tester.tap(find.bySemanticsLabel('9월 23일 수'));
    await settle(tester);
    expect(find.text(AppStrings.dayEmpty), findsOneWidget);
  });

  testWidgets('화살표로 달을 옮기면 그달을 읽고, 오늘이 없는 달은 1일을 고른다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    await tester.tap(find.bySemanticsLabel(AppStrings.nextMonth));
    await settle(tester);

    expect(find.text('October'), findsOneWidget);
    expect(setup.container.read(selectedDateProvider), DateTime(2026, 10, 1));
    final months = [
      for (final r in setup.adapter.requests)
        if (r.path.endsWith('/calendar')) r.queryParameters['month'],
    ];
    expect(months, ['2026-09', '2026-10']);

    await tester.tap(find.bySemanticsLabel(AppStrings.prevMonth));
    await settle(tester);
    expect(find.text('September'), findsOneWidget);
    expect(setup.container.read(selectedDateProvider), DateTime(2026, 9, 22));
  });

  testWidgets('"정리 안 된 예약 N건"을 누르면 가장 오래된 날의 하루 화면으로 간다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    await tester.tap(find.text(AppStrings.unresolvedBanner(2)));
    await settle(tester);

    expect(find.byKey(ScreenKeys.day), findsOneWidget);
    expect(find.text('30'), findsOneWidget);
    expect(find.text(AppStrings.yearMonth(2026, 8)), findsOneWidget);
  });

  testWidgets('미리보기를 누르면 고른 날의 하루 화면으로 간다', (tester) async {
    final setup = CustomerTestSetup(_backend().call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);

    await tester.tap(find.text(AppStrings.dayHeading(22, 2)));
    await settle(tester);

    expect(find.byKey(ScreenKeys.day), findsOneWidget);
    expect(find.text('22'), findsOneWidget);
  });

  testWidgets('월 요약을 불러오지 못하면 다시 시도한다', (tester) async {
    var fail = true;
    final backend = _backend();
    final ok = backend.routes['GET /v1/shops/3/visits/calendar']!;
    backend.routes['GET /v1/shops/3/visits/calendar'] = (o, b) =>
        fail ? const FakeResponse(statusCode: 503, data: 'x') : ok(o, b);
    final setup = CustomerTestSetup(backend.call, overrides: _today);
    addTearDown(setup.container.dispose);
    await _pumpHome(tester, setup);
    expect(_button(AppStrings.retry), findsOneWidget);

    fail = false;
    await tester.tap(_button(AppStrings.retry));
    await settle(tester);

    expect(find.byType(AppPhotoTile), findsNWidgets(2));
  });
}
