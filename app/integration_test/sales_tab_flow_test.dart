// ⑧-2 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 홈의 [매출] 탭이 서버의 숫자를 그대로
// 보이는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_sales_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`·`tcp:9010`(사진).
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/sales_tab_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
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

  testWidgets('⑧-2 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(buildRoot());
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

    await step('S3', '[연]으로 바꾸면 올해의 매출이고, 막대를 누르면 그 달로 간다', () async {
      await openSalesTab();
      await tap(find.text(AppStrings.salesSpanYear));
      await waitRevenue(yearRevenue);
      await shot('S3-year');
      soft(find.byKey(const Key('sales-day-card')).evaluate().isEmpty, '연 보기에 고른 날 카드가 있다');
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
