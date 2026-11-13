// 매출 탭에서 이어지는 화면(⑧-3) — 방문 목록, 다시 올 때가 지난 아이, 목표, 요약 공유. 오늘은 2026-11-14 토요일이다.
import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/router/app_router.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/today_provider.dart';
import 'package:chagocnote/design/widgets/app_back_button.dart';
import 'package:chagocnote/design/widgets/pressable.dart';
import 'package:chagocnote/features/sales/screens/sales_tab.dart';
import 'package:chagocnote/features/visit/screens/register_visit_screen.dart';
import 'package:chagocnote/features/visit/state/calendar_selection.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../../support/customer_test_app.dart';
import '../../../support/fake_http_client_adapter.dart';
import '../../../support/sales_fixtures.dart';
import '../../../support/upload_fakes.dart';
import '../../../support/visit_test_backend.dart';

const _summary = '/v1/shops/3/sales/summary';
const _visits = '/v1/shops/3/sales/visits';
const _duePets = '/v1/shops/3/sales/due-pets';
const _goal = '/v1/shops/3/sales/goal';

FakeResponse _ok(Object json) => FakeResponse(statusCode: 200, data: json);

/// 매출의 경로 넷을 주는 가짜 서버. 그 밖의 경로는 기본 백엔드에 있으면 그것이, 없으면 404 가 답한다
/// (방문 상세·반려동물 상세로 넘어간 것만 확인한다).
class _World {
  _World({
    Map<String, dynamic> Function(RequestOptions o)? summary,
    FutureOr<FakeResponse> Function(RequestOptions o)? visits,
    FutureOr<FakeResponse> Function(RequestOptions o)? duePets,
    FutureOr<FakeResponse> Function(int? amount)? putGoal,
  }) {
    final base = VisitTestBackend();
    setup = CustomerTestSetup(
      (o, b) {
        if (o.path == _summary) {
          return _ok((summary ?? (_) => salesSummaryJson(goal: goal))(o));
        }
        if (o.path == _visits) {
          visitQueries.add(Map.of(o.queryParameters));
          return (visits ?? (_) => _ok(salesPageJson([])))(o);
        }
        if (o.path == _duePets) return (duePets ?? (_) => _ok(salesPageJson([])))(o);
        if (o.path == _goal && o.method == 'PUT') {
          final amount = bodyOf(b)['monthly_amount'] as int?;
          goalBodies.add(bodyOf(b));
          if (putGoal != null) return putGoal(amount);
          goal = amount;
          return _ok({'monthly_amount': amount});
        }
        if (base.routes.containsKey('${o.method} ${o.path}')) return base.call(o, b);
        return const FakeResponse(statusCode: 404, data: {});
      },
      overrides: [
        todayProvider.overrideWith((ref) => DateTime(2026, 11, 14)),
        mediaImagesProvider.overrideWithValue(FakeMediaImages()),
      ],
    );
  }

  late final CustomerTestSetup setup;

  /// 서버에 저장된 목표.
  int? goal;
  final goalBodies = <Map<String, dynamic>>[];
  final visitQueries = <Map<String, dynamic>>[];

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

  /// 주소로 바로 연다.
  Future<void> push(WidgetTester tester, String location) async {
    unawaited(setup.container.read(routerProvider).push(location));
    await settle(tester);
  }
}

Map<String, dynamic> _october() => salesSummaryJson(
  start: '2026-10-01', end: '2026-10-31', elapsedEnd: '2026-10-31', revenue: 6100000,
  previous: {'start': '2026-09-01', 'end': '2026-09-30', 'revenue': 5000000},
);

void main() {
  group('방문 목록으로', () {
    testWidgets('메뉴 줄을 누르면 그 메뉴의 방문이 열린다 — 조정 줄은 눌리지 않는다', (tester) async {
      final w = _World(
        summary: (o) => salesSummaryJson(
          menus: [
            {'menu_id': 1, 'name': '전체 미용', 'amount': 2100000, 'count': 30, 'pet': null},
            {'menu_id': null, 'name': '조정', 'amount': -10000, 'count': 0, 'pet': null},
          ],
        ),
        visits: (o) => _ok(salesPageJson([salesVisitJson(7, pet: petCardJson(101, '보리'), amount: 45000)])),
      );
      await w.open(tester);

      await tester.tap(find.text('조정'), warnIfMissed: false);
      await settle(tester);
      expect(find.byKey(ScreenKeys.salesVisits), findsNothing);

      await tester.tap(find.text('전체 미용'));
      await settle(tester);

      expect(find.byKey(ScreenKeys.salesVisits), findsOneWidget);
      expect(find.text('전체 미용 한 방문'), findsOneWidget);
      expect(w.visitQueries.single, {
        'span': 'month', 'anchor': '2026-11-01', 'filter': 'menu', 'menu_id': 1,
      });
      expect(find.text('보리'), findsOneWidget);
      expect(find.text('11월 14일 토'), findsOneWidget);
      expect(find.text('45,000원'), findsOneWidget);
    });

    testWidgets('지난 달에서 노쇼를 누르면 지난 달의 목록이다', (tester) async {
      final w = _World(
        summary: (o) => o.queryParameters['anchor'] == '2026-11-14' ? salesSummaryJson() : _october(),
      );
      await w.open(tester);
      await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
      await settle(tester);

      await tester.tap(find.bySemanticsLabel(AppStrings.salesFactLabel('노쇼', 2)));
      await settle(tester);

      expect(find.text('노쇼한 방문'), findsOneWidget);
      expect(
        (w.visitQueries.single['span'], w.visitQueries.single['anchor'], w.visitQueries.single['filter']),
        ('month', '2026-10-01', 'no_show'),
      );
      expect(find.text(AppStrings.salesVisitsEmpty), findsOneWidget, reason: '빈 목록은 안내 한 줄');
    });

    testWidgets('취소도 목록으로 가고, 0 건이면 눌리지 않는다', (tester) async {
      final w = _World(
        summary: (o) => salesSummaryJson(
          bookings: {'remaining': 12, 'expected_amount': null, 'no_show': 0, 'canceled': 3},
        ),
      );
      await w.open(tester);

      expect(find.bySemanticsLabel(AppStrings.salesFactLabel('노쇼', 0)), findsNothing);
      await tester.tap(find.text('노쇼'), warnIfMissed: false);
      await settle(tester);
      expect(find.byKey(ScreenKeys.salesVisits), findsNothing);

      await tester.tap(find.bySemanticsLabel(AppStrings.salesFactLabel('취소', 3)));
      await settle(tester);
      expect(find.text('취소한 방문'), findsOneWidget);
      expect(w.visitQueries.single['filter'], 'canceled');
    });

    testWidgets('금액을 적지 않은 방문 — 이름을 보일 수 없는 줄도 보이고 눌러서 방문으로 간다', (tester) async {
      final w = _World(
        visits: (o) => _ok(
          salesPageJson([
            salesVisitJson(9, date: '2026-11-13', pet: petCardJson(102, '코코')),
            salesVisitJson(8, date: '2026-11-02'),
          ]),
        ),
      );
      await w.open(tester);

      await tester.tap(find.text('금액을 적지 않은 완료 방문 3건'));
      await settle(tester);

      expect(find.text('금액을 적지 않은 방문'), findsOneWidget);
      expect(w.visitQueries.single['filter'], 'unrecorded');
      expect(find.text('코코'), findsOneWidget);
      expect(find.text('11월 13일 금'), findsOneWidget);
      // 아이를 보일 수 없는 방문은 날짜가 줄의 이름이다. 금액 자리에는 아무것도 없다.
      expect(find.text('11월 2일 월'), findsOneWidget);
      expect(find.textContaining('원'), findsNothing);
      expect(find.textContaining('보호자만'), findsNothing);

      await tester.tap(find.text('11월 2일 월'));
      await settle(tester);
      expect(find.byKey(ScreenKeys.visitDetail), findsOneWidget);
      expect(w.setup.adapter.requests.any((r) => r.path == '/v1/shops/3/visits/8'), isTrue);
    });

    testWidgets('방문에서 돌아오면 목록과 요약을 다시 읽는다', (tester) async {
      final w = _World(visits: (o) => _ok(salesPageJson([salesVisitJson(9, pet: petCardJson(102, '코코'))])));
      await w.open(tester);
      await tester.tap(find.text('금액을 적지 않은 완료 방문 3건'));
      await settle(tester);
      await tester.tap(find.text('코코'));
      await settle(tester);
      int count(String path) => w.setup.adapter.requests.where((r) => r.path == path).length;
      expect((count(_visits), count(_summary)), (1, 1));

      await tester.tap(find.byType(AppBackButton));
      await settle(tester);
      expect(count(_visits), 2);

      await tester.tap(find.byType(AppBackButton));
      await settle(tester);
      expect(find.byType(SalesTab), findsOneWidget);
      expect(count(_summary), 2);
    });

    testWidgets('다음 쪽이 실패하면 보인 줄은 그대로이고 [다시 시도]로 이어 붙는다', (tester) async {
      var fail = true;
      final w = _World(
        visits: (o) {
          if (o.queryParameters['cursor'] == null) {
            return _ok(salesPageJson([salesVisitJson(9, pet: petCardJson(102, '코코'))], nextCursor: 'c1'));
          }
          if (fail) return const FakeResponse(statusCode: 503, data: {});
          return _ok(salesPageJson([salesVisitJson(8, pet: petCardJson(101, '보리'))]));
        },
      );
      await w.open(tester);
      await w.push(tester, '/sales/visits?span=month&anchor=2026-11-14&filter=no_show');

      await tester.tap(find.text(AppStrings.loadMore));
      await settle(tester);

      expect(find.text('코코'), findsOneWidget);
      expect(find.text('보리'), findsNothing);
      expect(find.text(AppStrings.loadMore), findsNothing);

      fail = false;
      await tester.tap(find.text(AppStrings.retry));
      await settle(tester);

      expect(find.text('코코'), findsOneWidget);
      expect(find.text('보리'), findsOneWidget);
      expect(find.text(AppStrings.retry), findsNothing);
      expect(find.text(AppStrings.loadMore), findsNothing, reason: '마지막 쪽');
      expect(w.visitQueries.map((q) => q['cursor']), [null, 'c1', 'c1']);
    });

    testWidgets('깨진 주소는 기본값으로 읽는다 — 이번 달의 금액을 적지 않은 방문', (tester) async {
      final w = _World();
      await w.open(tester);

      await w.push(tester, '/sales/visits?span=decade&anchor=2026-02-31&filter=menu&menu_id=abc');

      expect(find.text('금액을 적지 않은 방문'), findsOneWidget);
      expect(w.visitQueries.single, {'span': 'month', 'anchor': '2026-11-14', 'filter': 'unrecorded'});
    });

    testWidgets('처음 읽기에 실패하면 원인 문구와 [다시 시도]', (tester) async {
      var fail = true;
      final w = _World(
        visits: (o) => fail ? const FakeResponse(statusCode: 503, data: {}) : _ok(salesPageJson([])),
      );
      await w.open(tester);
      await w.push(tester, '/sales/visits?filter=canceled');
      expect(find.text(AppStrings.retry), findsOneWidget);

      fail = false;
      await tester.tap(find.text(AppStrings.retry));
      await settle(tester);
      expect(find.text(AppStrings.salesVisitsEmpty), findsOneWidget);
    });
  });

  group('다시 올 때가 지난 아이', () {
    testWidgets('줄을 누르면 목록이 열리고, 아이를 누르면 반려동물 상세로 간다', (tester) async {
      final w = _World(
        duePets: (o) => _ok(
          salesPageJson([
            duePetJson(101, '보리', '2026-09-12', photo: 'https://media.test/101.jpg'),
            duePetJson(102, '코코', '2026-09-18'),
          ]),
        ),
      );
      await w.open(tester);

      await tester.tap(find.text('다시 올 때가 지난 아이 7마리'));
      await settle(tester);

      expect(find.byKey(ScreenKeys.duePets), findsOneWidget);
      expect(find.text('9주 전'), findsOneWidget);
      expect(find.text('8주 전'), findsOneWidget);

      await tester.tap(find.text('코코'));
      await settle(tester);
      expect(find.byKey(ScreenKeys.petDetail), findsOneWidget);
    });

    testWidgets('지난 달을 보다가 눌러도 기간을 싣지 않고, 없으면 안내가 보인다', (tester) async {
      final w = _World(
        summary: (o) => o.queryParameters['anchor'] == '2026-11-14' ? salesSummaryJson() : _october(),
      );
      await w.open(tester);
      await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
      await settle(tester);

      await tester.tap(find.text('다시 올 때가 지난 아이 7마리'));
      await settle(tester);

      expect(find.text(AppStrings.salesDuePetsEmpty), findsOneWidget);
      final request = w.setup.adapter.requests.lastWhere((r) => r.path == _duePets);
      expect(request.queryParameters, isEmpty);
    });
  });

  group('메뉴 모두 보기', () {
    testWidgets('다섯을 넘으면 [모두 보기]가 그 자리에서 편다', (tester) async {
      final w = _World(
        summary: (o) => salesSummaryJson(
          menus: [
            for (var i = 1; i <= 7; i++)
              {'menu_id': i, 'name': '메뉴$i', 'amount': 10000 * (8 - i), 'count': 1, 'pet': null},
          ],
        ),
      );
      await w.open(tester);
      expect(find.text('메뉴5'), findsOneWidget);
      expect(find.text('메뉴6'), findsNothing);

      await tester.tap(find.text(AppStrings.salesShowAllMenus));
      await settle(tester);

      expect(find.text('메뉴7'), findsOneWidget);
      expect(find.text(AppStrings.salesShowAllMenus), findsNothing);
      expect(find.byType(SalesTab), findsOneWidget);
    });

    testWidgets('다섯 이하면 [모두 보기]가 없다', (tester) async {
      final w = _World();
      await w.open(tester);
      expect(find.text(AppStrings.salesShowAllMenus), findsNothing);
    });
  });

  group('목표', () {
    Future<void> openSheet(WidgetTester tester) async {
      await tester.tap(find.byKey(const Key('sales-goal')));
      await settle(tester);
      expect(find.text(AppStrings.salesGoalTitle), findsOneWidget);
    }

    Future<void> save(WidgetTester tester, String text) async {
      await tester.enterText(find.byType(TextField), text);
      await tester.tap(find.text(AppStrings.save));
      await settle(tester);
    }

    testWidgets('목표가 없으면 [이번 달 목표 정하기] — 정하면 문장이 생긴다', (tester) async {
      final w = _World();
      await w.open(tester);
      expect(find.text(AppStrings.salesSetGoal), findsOneWidget);
      expect(find.byKey(const Key('sales-goal-line')), findsNothing);

      await openSheet(tester);
      expect(find.text(AppStrings.salesGoalClear), findsNothing, reason: '지울 목표가 없다');
      await save(tester, '5000000');

      expect(w.goalBodies, [{'monthly_amount': 5000000}]);
      expect(find.text(AppStrings.salesGoalTitle), findsNothing, reason: '시트가 닫힌다');
      expect(find.text('이번 달 목표 500만 원의 65%'), findsOneWidget);
      expect(find.text(AppStrings.salesSetGoal), findsNothing);
    });

    testWidgets('목표 줄을 누르면 지금 값이 든 시트 — [목표 지우기]로 사라진다', (tester) async {
      final w = _World()..goal = 5000000;
      await w.open(tester);

      await openSheet(tester);
      expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, '5000000');
      await tester.tap(find.text(AppStrings.salesGoalClear));
      await settle(tester);

      expect(w.goalBodies, [{'monthly_amount': null}]);
      expect(find.textContaining('이번 달 목표 500만 원'), findsNothing);
      expect(find.text(AppStrings.salesSetGoal), findsOneWidget);
    });

    testWidgets('빈 칸과 0 은 지우기다', (tester) async {
      final w = _World()..goal = 5000000;
      await w.open(tester);
      await openSheet(tester);
      await save(tester, '');
      await openSheet(tester);
      await save(tester, '0');

      expect(w.goalBodies, [{'monthly_amount': null}, {'monthly_amount': null}]);
    });

    testWidgets('1억은 통과하고 1억 1원은 보내지 않고 막는다', (tester) async {
      final w = _World();
      await w.open(tester);
      await openSheet(tester);

      await save(tester, '100000001');
      expect(find.text(AppStrings.salesGoalTooBig), findsOneWidget);
      expect(w.goalBodies, isEmpty);
      expect(find.text(AppStrings.salesGoalTitle), findsOneWidget);

      await save(tester, '100000000');
      expect(w.goalBodies, [{'monthly_amount': 100000000}]);
      expect(find.text(AppStrings.salesGoalTitle), findsNothing);
    });

    testWidgets('붙여넣은 쉼표·글자는 걸러지고 아홉 자리에서 끊긴다', (tester) async {
      final w = _World();
      await w.open(tester);
      await openSheet(tester);

      await save(tester, '3,000,000원');
      expect(w.goalBodies, [{'monthly_amount': 3000000}]);

      await openSheet(tester);
      await tester.enterText(find.byType(TextField), '12345678901234');
      expect(tester.widget<TextField>(find.byType(TextField)).controller!.text, '123456789');
    });

    testWidgets('저장을 연타해도 요청은 한 번이다', (tester) async {
      final gate = Completer<void>();
      final w = _World(
        putGoal: (amount) async {
          await gate.future;
          return _ok({'monthly_amount': amount});
        },
      );
      await w.open(tester);
      await openSheet(tester);
      await tester.enterText(find.byType(TextField), '4000000');

      await tester.tap(find.text(AppStrings.save));
      await tester.pump(const Duration(milliseconds: 1));
      await tester.tap(find.text(AppStrings.save), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 1));
      await tester.tap(find.text(AppStrings.save), warnIfMissed: false);
      await tester.pump(const Duration(milliseconds: 1));

      expect(w.goalBodies, hasLength(1));
      gate.complete();
      await settle(tester);
      expect(find.text(AppStrings.salesGoalTitle), findsNothing);
    });

    testWidgets('실패하면 시트가 남고 원인 문구가 보인다 — 요약은 다시 읽는다', (tester) async {
      final w = _World(putGoal: (amount) => const FakeResponse(statusCode: 503, data: {}));
      await w.open(tester);
      await openSheet(tester);
      final before = w.setup.adapter.requests.where((r) => r.path == _summary).length;

      await save(tester, '4000000');

      expect(find.text(AppStrings.salesGoalTitle), findsOneWidget);
      expect(find.text(messageFor(ApiException(statusCode: 503, code: 'X', message: ''))), findsOneWidget);
      expect(w.setup.adapter.requests.where((r) => r.path == _summary).length, before + 1);

      // 다시 누르면 다시 보낸다(멎지 않았다).
      await tester.tap(find.text(AppStrings.save));
      await settle(tester);
      expect(w.goalBodies, hasLength(2));
    });

    testWidgets('이번 달의 월 보기가 아니면 목표를 정할 수 없다', (tester) async {
      final w = _World(
        summary: (o) => switch ((o.queryParameters['span'], o.queryParameters['anchor'])) {
          ('month', '2026-11-14') => salesSummaryJson(),
          ('month', _) => _october(),
          _ => salesSummaryJson(
            span: 'week', start: '2026-11-09', end: '2026-11-15', revenue: 1770000, weekdays: null,
            buckets: [],
          ),
        },
      );
      await w.open(tester);
      expect(find.byKey(const Key('sales-goal')), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
      await settle(tester);
      expect(find.byKey(const Key('sales-goal')), findsNothing, reason: '지난 달');

      await tester.tap(find.text(AppStrings.salesSpanWeek));
      await settle(tester);
      expect(find.byKey(const Key('sales-goal')), findsNothing, reason: '주 보기');
    });
  });

  group('요약 공유', () {
    testWidgets('지금 보는 기간의 글을 공유 시트에 넘긴다 — 아이 이름이 없다', (tester) async {
      final w = _World();
      await w.open(tester);

      await tester.tap(find.text(AppStrings.salesShare));
      await settle(tester);

      final text = w.setup.shareSheet.shared.single;
      expect(
        text,
        'Hiss Haus · 2026년 11월 (14일까지)\n'
        '매출 3,250,000원 · 방문 48건\n'
        '카드 2,400,000원 / 현금 550,000원 / 계좌 300,000원\n'
        '전체 미용 2,100,000원(30건) · 목욕 750,000원(15건) · 스파 400,000원(8건)',
      );
      for (final name in ['보리', '코코', '두부', '몽이']) {
        expect(text.contains(name), isFalse, reason: name);
      }
      final origin = w.setup.shareSheet.origins.single;
      expect(origin.width > 0 && origin.height > 0, isTrue, reason: '누른 버튼의 자리');
    });

    testWidgets('지난 달을 보면 지난 달의 글이다', (tester) async {
      final w = _World(
        summary: (o) => o.queryParameters['anchor'] == '2026-11-14' ? salesSummaryJson() : _october(),
      );
      await w.open(tester);
      await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
      await settle(tester);

      await tester.tap(find.text(AppStrings.salesShare));
      await settle(tester);

      expect(w.setup.shareSheet.shared.single, startsWith('Hiss Haus · 2026년 10월\n매출 6,100,000원'));
    });

    testWidgets('공유 시트가 실패하면 스낵바로 알린다', (tester) async {
      final w = _World();
      w.setup.shareSheet.error = PlatformException(code: 'FAILED');
      await w.open(tester);

      await tester.tap(find.text(AppStrings.salesShare));
      await settle(tester);

      expect(find.text(AppStrings.salesShareFailed), findsOneWidget);
    });

    testWidgets('빈 기간에는 공유가 없다', (tester) async {
      final w = _World(
        summary: (o) => salesSummaryJson(
          revenue: 0, visitCount: 0, pricedCount: 0, average: null, previous: null, payments: [], menus: [],
          regulars: [], weekdays: null, report: null, unrecordedCount: 0,
        ),
      );
      await w.open(tester);
      expect(find.text(AppStrings.salesShare), findsNothing);
    });
  });

  group('⑧-2 에서 미룬 것', () {
    testWidgets('오늘의 일 보기는 어제와 견준다', (tester) async {
      final w = _World(
        summary: (o) => o.queryParameters['span'] == 'day'
            ? salesSummaryJson(
                span: 'day', start: o.queryParameters['anchor'] as String, end: o.queryParameters['anchor'] as String,
                elapsedEnd: o.queryParameters['anchor'] as String, revenue: 510000, buckets: [], weekdays: null,
                previous: {'start': '2026-11-13', 'end': '2026-11-13', 'revenue': 440000},
              )
            : salesSummaryJson(),
      );
      await w.open(tester);
      await tester.tap(find.text(AppStrings.salesSpanDay).first);
      await settle(tester);
      expect(find.text('어제보다 7만 원 많아요.'), findsOneWidget);

      await tester.tap(find.bySemanticsLabel(AppStrings.salesPrev));
      await settle(tester);
      expect(find.text('그 전날보다 7만 원 많아요.'), findsOneWidget);
    });

    testWidgets('매출 탭의 + 는 캘린더에서 고른 날이 아니라 오늘로 예약 등록을 연다', (tester) async {
      final w = _World();
      await w.open(tester);
      w.setup.container.read(selectedDateProvider.notifier).select(DateTime(2026, 11, 20));

      await tester.tap(find.bySemanticsLabel(AppStrings.addReservation));
      await settle(tester);

      expect(find.byKey(ScreenKeys.registerVisit), findsOneWidget);
      expect(
        tester.widget<RegisterVisitScreen>(find.byType(RegisterVisitScreen)).date,
        DateTime(2026, 11, 14),
      );
    });

    testWidgets('고른 날 카드의 읽기 이름에 금액이 있다', (tester) async {
      final w = _World();
      await w.open(tester);
      expect(
        find.bySemanticsLabel(AppStrings.salesBarLabel(AppStrings.dayHeading(14, 6), '510,000')),
        findsOneWidget,
      );
    });

    testWidgets('글자를 키워도 요일 글자가 잘리지 않는다', (tester) async {
      final w = _World();
      tester.platformDispatcher.textScaleFactorTestValue = 2;
      addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
      await w.open(tester, size: const Size(390, 5000));

      expect(tester.takeException(), isNull);
      expect(find.text('토'), findsWidgets);
    });
  });

  testWidgets('골든 — 방문 목록', (tester) async {
    final w = _World(
      visits: (o) => _ok(
        salesPageJson([
          salesVisitJson(9, date: '2026-11-13', pet: petCardJson(101, '보리', photo: 'https://media.test/101.jpg')),
          salesVisitJson(8, date: '2026-11-11', pet: petCardJson(102, '코코'), amount: 45000),
          salesVisitJson(7, date: '2026-11-02'),
        ], nextCursor: 'c1'),
      ),
    );
    await w.open(tester, size: const Size(390, 844));
    await w.push(tester, '/sales/visits?span=month&anchor=2026-11-14&filter=unrecorded');

    await expectLater(find.byKey(ScreenKeys.salesVisits), matchesGoldenFile('goldens/sales_visits.png'));
  });

  testWidgets('골든 — 다시 올 때가 지난 아이', (tester) async {
    final w = _World(
      duePets: (o) => _ok(
        salesPageJson([
          duePetJson(101, '보리', '2026-07-04', photo: 'https://media.test/101.jpg'),
          duePetJson(102, '코코', '2026-09-12'),
          duePetJson(103, '두부', '2026-09-18', photo: 'https://media.test/103.jpg'),
        ]),
      ),
    );
    await w.open(tester, size: const Size(390, 844));
    await w.push(tester, '/sales/due-pets');

    await expectLater(find.byKey(ScreenKeys.duePets), matchesGoldenFile('goldens/due_pets.png'));
  });

  testWidgets('[더 보기]로 이어 읽은 뒤 방문에 다녀와도 읽은 줄이 그대로다', (tester) async {
    final w = _World(
      visits: (o) => o.queryParameters['cursor'] == null
          ? _ok(salesPageJson([salesVisitJson(9, pet: petCardJson(102, '코코'))], nextCursor: 'c1'))
          : _ok(salesPageJson([salesVisitJson(8, pet: petCardJson(101, '보리'))])),
    );
    await w.open(tester);
    await w.push(tester, '/sales/visits?span=month&anchor=2026-11-14&filter=no_show');
    await tester.tap(find.text(AppStrings.loadMore));
    await settle(tester);
    expect(find.text('보리'), findsOneWidget);

    await tester.tap(find.text('보리'));
    await settle(tester);
    await tester.tap(find.byType(AppBackButton));
    await settle(tester);

    expect(find.byKey(ScreenKeys.salesVisits), findsOneWidget);
    expect(find.text('코코'), findsOneWidget);
    expect(find.text('보리'), findsOneWidget, reason: '둘째 쪽의 줄이 사라지지 않는다');
    expect(w.visitQueries.map((q) => q['cursor']), [null, 'c1', null, 'c1']);
  });

  testWidgets('글자뿐인 누를 것도 누름 영역의 높이는 44 이상이다', (tester) async {
    final w = _World(
      summary: (o) => salesSummaryJson(
        menus: [
          for (var i = 1; i <= 7; i++)
            {'menu_id': i, 'name': '메뉴$i', 'amount': 10000 * (8 - i), 'count': 1, 'pet': null},
        ],
      ),
    );
    await w.open(tester);

    double heightOf(Finder text) =>
        tester.getSize(find.ancestor(of: text, matching: find.byType(Pressable)).first).height;

    for (final label in [
      AppStrings.salesSetGoal,
      AppStrings.salesShowAllMenus,
      AppStrings.salesShare,
      '다시 올 때가 지난 아이 7마리',
      '금액을 적지 않은 완료 방문 3건',
    ]) {
      expect(heightOf(find.text(label)), greaterThanOrEqualTo(44), reason: label);
    }

    w.goal = 5000000;
    await tester.drag(find.byKey(const Key('sales-revenue')), const Offset(0, 400));
    await settle(tester);
    expect(tester.getSize(find.byKey(const Key('sales-goal'))).height, greaterThanOrEqualTo(44), reason: '목표 줄');
  });
}
