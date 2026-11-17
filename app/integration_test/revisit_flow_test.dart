// ⑬-2 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해 다시 올 때가 된 아이(곧·지남)를 보고, [안내]·[예약]을
// 누르기 둘로 끝내고, 주기를 그 자리에서 바꾸고, 어제의 남은 일을 하루 마무리에서 장마다 누르기 둘 이하로 끝내는지 확인한다
// (설계 6절의 횟수). 도구는 `flow_kit.dart`. 공유 시트는 받은 글을 적어 두는 대역이다 — 글은 찍지 않고 아이 이름이
// 들었는지만 본다.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_revisit_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`·`tcp:9010`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/revisit_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const ownerName = String.fromEnvironment('OWNER');
const staffName = String.fromEnvironment('STAFF');
const kong = int.fromEnvironment('KONG');

/// 어제(서울) — `2026-11-16` 꼴. 준비 스크립트가 넘긴다(기기의 시간대에 기대지 않는다).
const yday = String.fromEnvironment('YDAY');

/// 받은 글을 적어 두는 공유 시트.
class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];

  @override
  Future<void> shareText(String text, {required Rect origin}) async => shared.add(text);
}

/// 누른 횟수 — 설계 6절의 합격선과 견준다.
int taps = 0;

Future<void> press(Finder f) async {
  taps++;
  await tap(f);
}

Finder labelStarts(String prefix) =>
    find.byWidgetPredicate((w) => w is AppButton && w.label.startsWith(prefix));

Future<void> openRevisits() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 500));
  router.push('/revisits');
  await waitFor(find.byKey(ScreenKeys.revisits));
  await pumpFor(const Duration(seconds: 1));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑬-2 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
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

    await step('R1', '캘린더 탭의 "다시 올 때가 된 아이 3" → 지남(보리·두부)·곧(콩이)', () async {
      // 앞선 흐름이 피드 보기를 기억해 뒀을 수 있다 — 달력 보기로 돌린다.
      final calendar = find.bySemanticsLabel(AppStrings.viewAsCalendar);
      if (calendar.evaluate().isNotEmpty) await tap(calendar);
      await waitFor(find.text(AppStrings.revisitBanner(3)));
      await shot('R1-banner');
      await tap(find.text(AppStrings.revisitBanner(3)));
      await waitFor(find.byKey(ScreenKeys.revisits));
      await waitFor(find.text('보리'));
      soft(find.text('두부').evaluate().isNotEmpty, '지남에 두부가 없다');
      soft(find.text('콩이').evaluate().isEmpty, '지남에 콩이가 있다');
      soft(find.textContaining('어림').evaluate().isNotEmpty, '보리의 줄이 어림이 아니다');
      await shot('R1-due');
      await tap(find.text(AppStrings.revisitsSoonTab(1)));
      await waitFor(find.text('콩이'));
      soft(find.text('5주마다 · 5일 뒤쯤').evaluate().isNotEmpty, '콩이의 줄이 다르다');
      await shot('R1-soon');
    });

    await step('R2', '콩이 [안내] → [보내기] — 누르기 둘, 글에 아이 이름, 줄에 오늘 안내', () async {
      taps = 0;
      await press(btn(AppStrings.revisitNudge));
      await waitFor(btn(AppStrings.revisitNudgeSend));
      await shot('R2-sheet');
      await press(btn(AppStrings.revisitNudgeSend));
      await waitFor(find.text('오늘 안내'));
      soft(taps == 2, '누르기가 둘이 아니다($taps)');
      soft(share.shared.length == 1, '공유 시트가 한 번 불리지 않았다(${share.shared.length})');
      soft(share.shared.isNotEmpty && share.shared.first.contains('콩이'), '글에 아이 이름이 없다');
      note('안내 글 ${share.shared.isEmpty ? 0 : share.shared.first.split('\n').length}줄');
      await shot('R2-nudged');
    });

    await step('R3', '보리 [예약] → [예약 저장] — 누르기 둘, 돌아오면 보리가 지남에서 빠진다', () async {
      await openRevisits();
      await waitFor(find.text('보리'));
      taps = 0;
      await press(btn(AppStrings.revisitBook).first);
      await waitFor(find.byKey(ScreenKeys.registerVisit));
      await waitFor(labelStarts('예약 저장'));
      await shot('R3-register');
      await press(labelStarts('예약 저장'));
      await closeBundle();
      await waitFor(find.byKey(ScreenKeys.revisits));
      await pumpFor(const Duration(seconds: 1));
      soft(taps == 2, '누르기가 둘이 아니다($taps)');
      soft(find.text('보리').evaluate().isEmpty, '예약을 잡았는데 보리가 남았다');
      soft(find.text('두부').evaluate().isNotEmpty, '두부가 없어졌다');
      await shot('R3-after');
    });

    await step('R4', '두부의 주기 글 → [+] → [저장] — 8주로 정하면 곧으로 옮긴다', () async {
      await tap(find.textContaining('7주마다'));
      await waitFor(btn(AppStrings.save));
      await shot('R4-sheet');
      await tap(find.bySemanticsLabel(AppStrings.stepUp));
      await tap(btn(AppStrings.save));
      await pumpFor(const Duration(seconds: 1));
      soft(find.text('두부').evaluate().isEmpty, '8주로 정했는데 두부가 지남에 남았다');
      await tap(find.text(AppStrings.revisitsSoonTab(2)));
      await waitFor(find.text('두부'));
      soft(find.text('8주마다 · 6일 뒤쯤').evaluate().isNotEmpty, '두부의 줄이 다르다');
      await shot('R4-soon');
    });

    await step('R5', '어제 하루 머리의 "결제 안 적음 1" → 하루 마무리: 결제 장 둘, 알림장 장 하나로 끝난다', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 500));
      router.push('/visits/day/$yday');
      await waitFor(find.byKey(ScreenKeys.day));
      await waitFor(find.text(AppStrings.remainingUnpaid(1)));
      soft(find.text(AppStrings.remainingReportUnsent(1)).evaluate().isNotEmpty, '알림장 안 보냄이 없다');
      await shot('R5-day-head');
      await tap(find.text(AppStrings.remainingUnpaid(1)));
      await waitFor(find.byKey(ScreenKeys.wrapUp));
      await waitFor(find.text(AppStrings.wrapUpKindUnpaid));
      soft(fieldText('wrap-up-total') == '35000', '총액이 메뉴 정가로 채워져 있지 않다');
      await shot('R5-payment');
      taps = 0;
      await press(find.text(AppStrings.paymentCard));
      await press(btn(AppStrings.save));
      soft(taps == 2, '결제 장이 누르기 둘이 아니다($taps)');
      await waitFor(find.text(AppStrings.wrapUpKindReport));
      await shot('R5-report');
      taps = 0;
      await press(btn(AppStrings.wrapUpReportSkip));
      await waitFor(find.text(AppStrings.wrapUpDonePast));
      soft(taps == 1, '알림장 장이 누르기 하나가 아니다($taps)');
      soft(find.textContaining('원').evaluate().isEmpty, '끝 화면에 금액이 있다');
      await shot('R5-done');
      await tap(btn(AppStrings.close));
      await waitFor(find.byKey(ScreenKeys.day));
      await pumpFor(const Duration(seconds: 1));
      soft(find.text(AppStrings.remainingUnpaid(1)).evaluate().isEmpty, '하루 머리에 결제 안 적음이 남았다');
      soft(find.textContaining(AppStrings.paidMark).evaluate().isNotEmpty, '어제 줄에 결제 완료가 없다');
      await shot('R5-day-after');
    });

    await step('R6', '반려동물 상세의 주기 줄 — 콩이는 계산한 5주, 오늘 안내', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 500));
      router.push('/pets/$kong');
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await reveal(find.text('보통 5주마다 와요 · 지난 방문에서 계산'));
      soft(find.text('오늘 안내').evaluate().isNotEmpty, '안내한 날이 없다');
      await shot('R6-pet');
    });

    await step('R7', '직원 — 목록은 보이고 바꾸는 줄은 없다', () async {
      await logout();
      await login(staffName);
      await openRevisits();
      await tap(find.text(AppStrings.revisitsSoonTab(2)));
      await waitFor(find.text('콩이'));
      soft(find.text(AppStrings.revisitChange).evaluate().isEmpty, '직원에게 바꾸기가 있다');
      await shot('R7-staff');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
