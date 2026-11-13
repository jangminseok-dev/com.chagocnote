// ⑦-3 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해, 보호자 계정에 이어진 고객의 [보호자] 탭에
// "보호자 계정 연결됨 · ○월 ○일"이 보이고 직원이 연결을 끊을 수 있는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_guardian_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   준비가 알림장을 보내고 보호자 계정(웹 세션)으로 이어 둔다. 보호자 웹은 떠 있지 않아도 된다.
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/guardian_link_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const customerId = int.fromEnvironment('CUSTOMER');
const petId = int.fromEnvironment('PET');
const month = int.fromEnvironment('MONTH');
const day = int.fromEnvironment('DAY');
const ownerName = String.fromEnvironment('OWNER');
const staffName = String.fromEnvironment('STAFF');

final linkedLine = find.text(AppStrings.guardianLinkedOn(month, day));
final anyLinkedLine = find.textContaining(AppStrings.guardianLinked);
final more = p(AppStrings.guardianLinkMore);

/// 반려동물 상세를 열고 [보호자] 탭으로 간다. 탭의 본문(보호자 수정 버튼)이 그려질 때까지 기다린다.
Future<void> openOwnerTab() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 300));
  router.push('/pets/$petId');
  await waitFor(find.byKey(ScreenKeys.petDetail));
  await tap(find.text(AppStrings.petTabOwner));
  await waitFor(btn(AppStrings.editOwner));
  await pumpFor(const Duration(seconds: 1));
}

/// 줄을 화면 안으로 옮긴다 — 보호자 탭은 길다.
Future<void> bring(Finder f) async {
  await reveal(f);
  await t.ensureVisible(f.first);
  await pumpFor(const Duration(milliseconds: 300));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑦-3 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (
    tester,
  ) async {
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

    await step('G1', '사장 — 보호자 탭에 "보호자 계정 연결됨 · 이은 날"', () async {
      await openOwnerTab();
      final link = await container
          .read(customerApiProvider)
          .guardianLink(shopId, customerId);
      soft(link.linked, '서버에 이어져 있지 않다');
      await waitFor(linkedLine);
      await bring(linkedLine);
      await shot('G1-linked');
      soft(more.evaluate().length == 1, '연결 더 보기(···)가 하나가 아니다');
    });

    await step('G2', '··· → [연결 끊기] → 확인에서 [취소] — 줄이 남는다', () async {
      await tap(more);
      await waitFor(p(AppStrings.endGuardianLink));
      await tap(p(AppStrings.endGuardianLink));
      await waitFor(find.text(AppStrings.endGuardianLinkConfirm));
      await shot('G2-confirm');
      await tap(btn(AppStrings.cancel));
      await pumpFor(const Duration(seconds: 1));
      soft(linkedLine.evaluate().isNotEmpty, '취소했는데 줄이 사라졌다');
    });

    await step('G3', '직원 — 같은 줄이 보이고, 끊으면 알리고 줄이 사라진다', () async {
      await logout();
      await login(staffName);
      await openOwnerTab();
      await waitFor(linkedLine);
      await bring(linkedLine);
      await tap(more);
      await waitFor(p(AppStrings.endGuardianLink));
      await tap(p(AppStrings.endGuardianLink));
      await waitFor(find.text(AppStrings.endGuardianLinkConfirm));
      await tap(btn(AppStrings.endGuardianLink));
      await waitFor(find.text(AppStrings.guardianLinkEnded));
      await shot('G3-ended');
      await pumpFor(const Duration(seconds: 2));
      soft(anyLinkedLine.evaluate().isEmpty, '끊었는데 줄이 남아 있다');
      soft(more.evaluate().isEmpty, '끊었는데 ··· 가 남아 있다');
    });

    await step('G4', '화면을 다시 열어도 줄이 없다 — 서버에서 끊겼다', () async {
      await openOwnerTab();
      await pumpFor(const Duration(seconds: 3));
      await shot('G4-reopened');
      soft(anyLinkedLine.evaluate().isEmpty, '다시 열었더니 줄이 있다');
      // 줄이 없는 것은 읽지 못했을 때도 같다 — 서버에 직접 물어 끊긴 것을 확인한다.
      final link = await container
          .read(customerApiProvider)
          .guardianLink(shopId, customerId);
      soft(!link.linked, '서버에는 아직 이어져 있다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
