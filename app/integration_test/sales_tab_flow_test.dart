// ⑧-2·⑧-3 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 홈의 [매출] 탭이 서버의 숫자를 그대로
// 보이고, 숫자를 누르면 그 방문들·아이들로 이어지고, 목표를 정하고 요약을 공유하는지 확인한다. 도구는 `flow_kit.dart`.
// 공유 시트는 받은 글을 적어 두는 대역이다(OS 시트를 띄우지 않는다).
//
// 준비(infra/ 에서): bash ../app/tool/prepare_sales_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`·`tcp:9010`(사진).
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/sales_tab_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/features/sales/screens/sales_tab.dart';
import 'package:chagocnote/features/sales/state/sales_rules.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const ownerName = String.fromEnvironment('OWNER');
const staffName = String.fromEnvironment('STAFF');

/// 어제가 지난달이면(오늘이 1일) 매출 탭에서 ‹ 를 한 번 눌러야 그 달이 보인다.
const back = int.fromEnvironment('BACK');
const monthRevenue = int.fromEnvironment('MONTH_REVENUE');
const yearRevenue = int.fromEnvironment('YEAR_REVENUE');

/// 어제의 두 방문(콩이·두부)이 한 메뉴의 이름 — 기본 메뉴의 첫째라 준비 스크립트가 서버에서 읽어 넘긴다.
const menuName = String.fromEnvironment('MENU');

/// 받은 글을 적어 두는 공유 시트.
class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];

  @override
  Future<void> shareText(String text, {required Rect origin}) async => shared.add(text);
}

/// 매출 탭의 이번 달 월 보기를 연다. 탭은 앞 단계가 고른 기간에 머물러 있다 — [월]을 눌러 이번 달로 돌린다.
Future<void> openThisMonth() async {
  await openSalesTab();
  await tap(find.text(AppStrings.salesSpanMonth));
  await pumpFor(const Duration(milliseconds: 500));
  // 앞 단계가 아래로 내려 둔 본문을 맨 위로 — 목록은 보이는 것만 그려 큰 숫자가 없을 수 있다.
  final body = find.descendant(of: find.byType(SalesTab), matching: find.byType(Scrollable));
  if (body.evaluate().isNotEmpty) t.state<ScrollableState>(body.first).position.jumpTo(0);
  await pumpFor(const Duration(milliseconds: 300));
}

/// 매출 탭의 월 보기(어제가 든 달)를 연다.
Future<void> openMonth() async {
  await openThisMonth();
  if (back == 1) await tap(p(AppStrings.salesPrev));
  await waitRevenue(monthRevenue);
}

/// 이어진 화면에서 매출 탭으로 돌아온다.
Future<void> backToTab() async {
  router.pop();
  await waitFor(find.byType(SalesTab));
  await pumpFor(const Duration(milliseconds: 500));
}

final revenue = find.byKey(const Key('sales-revenue'));

String get shownRevenue => t.widget<Text>(revenue).data ?? '';

/// 큰 숫자가 [amount]가 될 때까지 기다린다.
Future<void> waitRevenue(int amount) async {
  final want = won(amount);
  final end = DateTime.now().add(const Duration(seconds: 20));
  while (revenue.evaluate().isEmpty || shownRevenue != want) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('큰 숫자가 $want 이 되지 않았다(지금: ${revenue.evaluate().isEmpty ? '없음' : shownRevenue})');
    }
    await pumpFor(const Duration(milliseconds: 200));
  }
}

Future<void> openSalesTab() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 500));
  await tap(find.text(AppStrings.tabSales));
  await waitFor(find.byType(SalesTab));
  await pumpFor(const Duration(seconds: 1));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑧-2·⑧-3 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
    t = tester;
    await initializeGlass();
    final share = RecordingShareSheet();
    await t.pumpWidget(buildRoot(overrides: [shareSheetProvider.overrideWithValue(share)]));
    final end = DateTime.now().add(const Duration(seconds: 40));
    while (DateTime.now().isBefore(end)) {
      await t.pump(const Duration(milliseconds: 100));
      drain();
      if (find.byKey(ScreenKeys.login).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.home).evaluate().isNotEmpty ||
          find.byKey(ScreenKeys.shopSelect).evaluate().isNotEmpty) {
        break;
      }
    }
    if (find.byKey(ScreenKeys.login).evaluate().isEmpty) await logout();
    await login(ownerName);

    await step('S1', '사장 — 매출 탭의 월 보기에 서버의 매출이 그대로 보인다', () async {
      await openSalesTab();
      if (back == 1) await tap(p(AppStrings.salesPrev));
      await waitRevenue(monthRevenue);
      await pumpFor(const Duration(seconds: 2)); // 사진이 그려질 시간
      await shot('S1-month-top');
      soft(find.byKey(const Key('sales-chart')).evaluate().isNotEmpty, '차트가 없다');
      soft(find.text('2마리가 4번 다녀갔어요').evaluate().isNotEmpty, '다녀간 아이 줄이 다르다');
      soft(find.byKey(const Key('sales-day-card')).evaluate().isNotEmpty, '고른 날 카드가 없다');
      if (back == 0) {
        soft(find.text('이번 달 목표 50만 원의 20%').evaluate().isNotEmpty, '목표 줄이 없다');
      }
    });

    await step('S2', '아래로 내리면 결제 수단·메뉴의 조정·손님·예약이 있다', () async {
      await t.drag(revenue, const Offset(0, -560));
      await pumpFor(const Duration(seconds: 1));
      await shot('S2-month-bottom');
      for (final text in [
        AppStrings.salesPayment,
        AppStrings.paymentCard,
        AppStrings.paymentTransfer,
        '조정',
        AppStrings.salesNewPets,
        AppStrings.salesBookings,
      ]) {
        soft(find.text(text).evaluate().isNotEmpty, '"$text" 가 없다');
      }
      if (back == 0) {
        soft(find.text('정가로 약 25,000원').evaluate().isNotEmpty, '남은 예약의 예상 금액이 없다');
      }
    });

    await step('S3', '[연]으로 바꾸면 올해의 매출이다', () async {
      // 1월 1일에는 올해의 매출이 아직 없다(어제는 작년) — 빈 기간에는 큰 숫자가 없어 견줄 것이 없다.
      if (yearRevenue == 0) {
        note('올해 매출이 0 이라 연 보기 확인을 건너뛴다');
        return;
      }
      await openSalesTab();
      await tap(find.text(AppStrings.salesSpanYear));
      await waitRevenue(yearRevenue);
      await shot('S3-year');
      soft(find.byKey(const Key('sales-day-card')).evaluate().isEmpty, '연 보기에 고른 날 카드가 있다');
    });

    await step('S5', '금액을 적지 않은 방문 — 목록에서 방문 상세로 간다', () async {
      await openMonth();
      await tap(find.text(AppStrings.salesUnrecorded(1)));
      await waitFor(find.byKey(ScreenKeys.salesVisits));
      await waitFor(find.text('두부'));
      await shot('S5-unrecorded');
      soft(find.text(AppStrings.salesVisitsUnrecorded).evaluate().isNotEmpty, '제목이 다르다');
      soft(find.textContaining('원').evaluate().isEmpty, '금액 없는 줄에 금액이 있다');
      await tap(find.text('두부'));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      router.pop();
      await waitFor(find.byKey(ScreenKeys.salesVisits));
      await backToTab();
    });

    await step('S6', '노쇼를 누르면 그 달의 노쇼한 방문이다', () async {
      await openMonth();
      await tap(find.bySemanticsLabel(AppStrings.salesFactLabel(AppStrings.salesNoShow, 1)));
      await waitFor(find.byKey(ScreenKeys.salesVisits));
      await waitFor(find.text('콩이'));
      await shot('S6-no-show');
      soft(find.text(AppStrings.salesVisitsNoShow).evaluate().isNotEmpty, '제목이 다르다');
      soft(find.text('두부').evaluate().isEmpty, '노쇼가 아닌 방문이 있다');
      await backToTab();
    });

    await step('S7', '메뉴 줄을 누르면 그 메뉴의 방문 둘이다', () async {
      await openMonth();
      await tap(find.bySemanticsLabel(AppStrings.salesMenuRowLabel(menuName)));
      await waitFor(find.byKey(ScreenKeys.salesVisits));
      await waitFor(find.text('콩이'));
      await shot('S7-menu');
      soft(find.text(AppStrings.salesVisitsOfMenu(menuName)).evaluate().isNotEmpty, '제목이 다르다');
      soft(find.text('두부').evaluate().isNotEmpty, '두부의 방문이 없다');
      soft(find.text('30,000원').evaluate().isNotEmpty, '카드 방문의 금액이 없다');
      soft(find.text('50,000원').evaluate().isNotEmpty, '현금 방문의 금액이 없다');
      await backToTab();
    });

    await step('S8', '다시 올 때가 지난 아이 — 다시 올 때가 된 아이 화면(지남)에서 반려동물 상세로 간다(⑬)', () async {
      await openMonth();
      await tap(find.text(AppStrings.salesDuePets(1)));
      await waitFor(find.byKey(ScreenKeys.revisits));
      await waitFor(find.text('보리'));
      await shot('S8-revisits');
      // 한 번 온 아이는 매장 기본 간격(4주)으로 어림한다 — 60일 전 → 주로 반올림해 9주 전(서버의 안내 글과 같은 셈).
      soft(find.text('9주 전에 왔어요 · 어림').evaluate().isNotEmpty, '마지막 방문이 9주 전(어림)이 아니다');
      await tap(find.text('보리'));
      await waitFor(find.byKey(ScreenKeys.petDetail));
      router.pop();
      await waitFor(find.byKey(ScreenKeys.revisits));
      await backToTab();
    });

    await step('S9', '목표를 바꾸면 문장이 바뀌고, 지우면 [이번 달 목표 정하기]가 된다', () async {
      // 목표는 이번 달의 월 보기에만 있다 — 어제가 지난달이면(오늘이 1일) 이번 달은 빈 기간이지만 목표 줄은 있다.
      await openThisMonth();
      await waitFor(find.byKey(const Key('sales-goal')));
      await tap(find.byKey(const Key('sales-goal')));
      await waitFor(find.text(AppStrings.salesGoalTitle));
      soft(fieldText('sales-goal-amount') == '500000', '시트에 지금 목표가 없다');
      await enter('sales-goal-amount', '1000000');
      await shot('S9-goal-sheet');
      await tap(find.text(AppStrings.save));
      await waitFor(find.textContaining('이번 달 목표 100만 원의'));
      await shot('S9-goal-changed');
      await tap(find.byKey(const Key('sales-goal')));
      await waitFor(find.text(AppStrings.salesGoalTitle));
      await tap(find.text(AppStrings.salesGoalClear));
      await waitFor(find.text(AppStrings.salesSetGoal));
      soft(find.textContaining('이번 달 목표 100만 원의').evaluate().isEmpty, '지운 목표가 남아 있다');
    });

    await step('S10', '요약 공유 — 받은 글에 매출이 있고 아이 이름이 없다', () async {
      await openMonth();
      await tap(find.text(AppStrings.salesShare));
      await pumpFor(const Duration(seconds: 1));
      await shot('S10-share');
      soft(share.shared.length == 1, '공유 시트가 한 번 불리지 않았다(${share.shared.length})');
      final text = share.shared.isEmpty ? '' : share.shared.first;
      soft(text.contains('매출 ${won(monthRevenue)}원 · 방문 4건'), '글에 매출·방문 수가 없다');
      soft(text.contains('${AppStrings.paymentCard} 30,000원'), '글에 결제 수단이 없다');
      soft(text.contains('조정 25,000원'), '글에 조정 줄이 없다');
      for (final name in ['콩이', '두부', '보리', '김민지', '박두부', '최보리', '010']) {
        soft(!text.contains(name), '글에 이름·번호가 있다');
      }
      note('공유 글 ${text.split('\n').length}줄');
    });

    await step('S4', '직원에게는 안내만 보인다', () async {
      await logout();
      await login(staffName);
      await openSalesTab();
      await waitFor(find.text(AppStrings.salesOwnerOnly));
      await shot('S4-staff');
      soft(revenue.evaluate().isEmpty, '직원에게 매출이 보인다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
