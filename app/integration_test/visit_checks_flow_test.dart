// ③-B2 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해, 노령·지병 아이의 예약에 "확인할 것"이
// 하루 목록·방문 상세에 보이고, [받았어요]로 동의 줄이 사라지고, 주의 고객 표시가 목록·예약 등록에 보이며,
// 확인할 것이 있어도 예약이 저장되는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_visit_checks_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/visit_checks_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>
//
// 주의 사유는 흐름이 적는 고정 글("흐름 확인용 사유")이다 — 실제 사유를 찍지 않는다.

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/features/customer/state/customer_providers.dart';
import 'package:chagocnote/features/visit/api/check_models.dart';
import 'package:chagocnote/features/visit/screens/visit_checks_block.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const customerId = int.fromEnvironment('CUSTOMER');
const petId = int.fromEnvironment('PET');
const visitId = int.fromEnvironment('VISIT');
const date = String.fromEnvironment('DATE');
const nextDate = String.fromEnvironment('NEXT');
const ownerName = String.fromEnvironment('OWNER');

const reason = '흐름 확인용 사유';

final block = find.byType(VisitChecksBlock);
final consentLine = find.textContaining('미용 동의서를 받아 주세요');
final conditionsLine = p('지병 · 심장 질환');
final received = find.byKey(ValueKey('consent-received-$petId'));

Future<void> bring(Finder f) async {
  await reveal(f);
  await t.ensureVisible(f.first);
  await pumpFor(const Duration(milliseconds: 300));
}

Future<void> openPet({bool ownerTab = false}) async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 300));
  router.push('/pets/$petId');
  await waitFor(find.byKey(ScreenKeys.petDetail));
  if (ownerTab) {
    await tap(find.text(AppStrings.petTabOwner));
    await waitFor(btn(AppStrings.editOwner));
  }
  await pumpFor(const Duration(seconds: 1));
}

Future<List<CheckCode>> serverCodes() async => [
  for (final c
      in (await container.read(visitApiProvider).detail(shopId, visitId))
          .checks)
    c.code,
];

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('③-B2 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (
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

    await step('C1', '하루 목록 — 예약 줄에 "확인 2"(첫 방문·동의, 지병은 세지 않는다)', () async {
      router.push('/visits/day/$date');
      await waitFor(find.byKey(ScreenKeys.day));
      await waitFor(find.textContaining(AppStrings.checkCount(2)));
      await shot('C1-day');
    });

    await step('C2', '방문 상세 — 묶음에 첫 방문·동의·지병, 지병을 누르면 메모', () async {
      await openVisit(visitId);
      await waitFor(block);
      await bring(block);
      soft(
        find.text(AppStrings.checkFirstVisit).evaluate().isNotEmpty,
        '첫 방문 줄이 없다',
      );
      soft(consentLine.evaluate().isNotEmpty, '동의 줄이 없다');
      soft(received.evaluate().isNotEmpty, '[받았어요]가 없다');
      await tap(conditionsLine);
      await waitFor(find.text('심장 질환 — 약 복용 중'));
      await shot('C2-detail');
    });

    await step('C3', '[받았어요] — 동의 줄이 사라지고 서버에도 없다', () async {
      await tap(received);
      final end = DateTime.now().add(const Duration(seconds: 20));
      while (consentLine.evaluate().isNotEmpty) {
        if (DateTime.now().isAfter(end)) throw TestFailure('동의 줄이 남아 있다');
        await pumpFor(const Duration(milliseconds: 200));
      }
      await shot('C3-received');
      soft(
        find.text(AppStrings.checkFirstVisit).evaluate().isNotEmpty,
        '첫 방문 줄까지 사라졌다',
      );
      soft(
        !(await serverCodes()).contains(CheckCode.consent),
        '서버에는 동의 항목이 남아 있다',
      );
    });

    await step('C4', '반려동물 상세 — 기본 탭에 받은 날, [보호자] 탭에서 주의 표시', () async {
      await openPet();
      await waitFor(find.textContaining('에 받았어요'));
      await bring(find.text(AppStrings.groomingConsentLabel));
      await shot('C4-consent-row');
      await tap(find.text(AppStrings.petTabOwner));
      await waitFor(btn(AppStrings.editOwner));
      await tap(find.byKey(const ValueKey('caution-set')));
      await waitFor(find.text(AppStrings.cautionSheetTitle));
      await enter('caution-reason', reason);
      await shot('C4-sheet');
      await tap(btn(AppStrings.save));
      await waitFor(find.text(reason));
      await bring(find.text(reason));
      await shot('C4-caution-row');
      final detail = await container
          .read(customerApiProvider)
          .customer(shopId, customerId);
      soft(detail.customer.caution?.reason == reason, '서버에 주의 표시가 없다');
    });

    await step('C5', '고객 목록 — 그 가족의 줄에 "주의"', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 500));
      await tap(find.text(AppStrings.tabCustomers));
      await waitFor(find.textContaining('· ${AppStrings.cautionMark}'));
      await shot('C5-list');
    });

    await step('C6', '예약 등록 — 묶음에 주의 줄이 뜨고, 그래도 저장된다', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 300));
      router.push('/visits/new?date=$nextDate');
      await waitFor(find.byKey(ScreenKeys.registerVisit));
      await tap(find.text('노을'));
      await waitFor(block);
      await bring(block);
      soft(
        find.text(AppStrings.checkCaution(reason)).evaluate().isNotEmpty,
        '주의 줄이 없다',
      );
      soft(
        find.byKey(ValueKey('consent-received-$petId')).evaluate().isEmpty,
        '등록 화면에 [받았어요]가 있다',
      );
      await shot('C6-preview');
      await tap(p('14:00'));
      final save = find.byWidgetPredicate(
        (w) => w is AppButton && w.label.startsWith('예약 저장'),
      );
      await waitFor(save);
      await tap(save);
      final end = DateTime.now().add(const Duration(seconds: 20));
      while (find.byKey(ScreenKeys.registerVisit).evaluate().isNotEmpty) {
        if (DateTime.now().isAfter(end)) throw TestFailure('저장 뒤에도 등록 화면이 남아 있다');
        await pumpFor(const Duration(milliseconds: 200));
      }
      final saved = await container
          .read(visitApiProvider)
          .day(shopId, DateTime.parse(nextDate));
      soft(saved.items.length == 1, '예약이 저장되지 않았다(${saved.items.length}건)');
      await shot('C6-saved');
    });

    await step('C7', '주의 표시 지우기 — 줄이 돌아가고 서버에도 없다', () async {
      await openPet(ownerTab: true);
      await bring(find.text(reason));
      await tap(p(AppStrings.cautionMore));
      await waitFor(p(AppStrings.cautionClear));
      await tap(p(AppStrings.cautionClear));
      await waitFor(find.text(AppStrings.cautionClearConfirm));
      await tap(btn(AppStrings.cautionClear));
      await waitFor(find.text(AppStrings.cautionNone));
      await shot('C7-cleared');
      final detail = await container
          .read(customerApiProvider)
          .customer(shopId, customerId);
      soft(detail.customer.caution == null, '서버에 주의 표시가 남아 있다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
