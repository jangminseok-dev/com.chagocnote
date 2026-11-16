// ⑪-B 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해, 예약을 저장하면 보낼 것 시트가 뜨고 공유 한 번으로
// 나가는지, 방문 상세에서 다시 열어 토막을 빼고 보내는지, 서류 설정에서 고친 글이 서명 화면에 보이는지, 노령 나이를
// 바꾸면 동의 줄이 사라지는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_forms_flow.sh → 마지막 줄의 --dart-define 들(기기마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/forms_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>
//
// 공유 시트만 바꿔 끼운다(받은 글을 적어 두는 [RecordingShareSheet]) — 실제 시트는 테스트가 닫지 못한다.
// **보내는 글에는 서류 주소(토큰)가 들어 있다** — 단계 이름·실패 문구·스크린샷 설명에 적지 않는다.

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_choice_chip.dart';
import 'package:chagocnote/features/customer/screens/form_text_edit_screens.dart';
import 'package:chagocnote/features/visit/screens/send_bundle_sheet.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const petId = int.fromEnvironment('PET');
const date = String.fromEnvironment('DATE');
const ownerName = String.fromEnvironment('OWNER');

const newSeniorText = '나이가 많은 아이는 쉬어 가며 천천히 미용해요.';

class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];

  @override
  Future<void> shareText(String text, {required Rect origin}) async {
    shared.add(text);
  }
}

Finder consentLine() => find.textContaining('미용 동의서');
Finder chip(String label) => find.byWidgetPredicate((w) => w is AppChoiceChip && w.label == label);

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑪-B 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
    t = tester;
    final share = RecordingShareSheet();
    await initializeGlass();
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
    late int visitId;

    await step('F1', '예약을 저장하면 보낼 것 시트가 뜬다 — 예약 안내와 동의서, 빈 자리 없이', () async {
      router.push('/visits/new?date=$date');
      await waitFor(find.byKey(ScreenKeys.registerVisit));
      await tap(find.text('초코'));
      await tap(p('14:00'));
      final save = find.byWidgetPredicate((w) => w is AppButton && w.label.startsWith('예약 저장'));
      await waitFor(save);
      await tap(save);
      await waitFor(find.text(AppStrings.bundleSheetTitle));
      for (final label in [AppStrings.bundlePartReservation, AppStrings.bundlePartConsent]) {
        soft(find.text(label).evaluate().isNotEmpty, '토막이 없다: $label');
      }
      final reservation = t.widget<TextField>(find.byKey(const ValueKey('bundle-part-reservation'))).controller!.text;
      soft(reservation.contains('초코') && reservation.contains('오후 2:00'), '예약 안내에 아이·시각이 없다');
      soft(!reservation.contains('{') && !reservation.contains('\n\n'), '예약 안내에 빈 자리·빈 줄이 있다');
      await shot('F1-sheet');
    });

    await step('F2', '[보내기] 한 번으로 나가고 등록 화면이 닫힌다 — 저장 뒤 누르기 1번', () async {
      await tap(find.byKey(SendBundleSheet.sendKey));
      final gone = DateTime.now().add(const Duration(seconds: 20));
      while (find.byKey(ScreenKeys.registerVisit).evaluate().isNotEmpty) {
        if (DateTime.now().isAfter(gone)) throw TestFailure('보낸 뒤에도 등록 화면이 남아 있다');
        await pumpFor(const Duration(milliseconds: 200));
      }
      soft(share.shared.length == 1, '공유 시트가 한 번 불리지 않았다(${share.shared.length})');
      soft(share.shared.isNotEmpty && share.shared.first.contains('/f/'), '보낸 글에 동의서 주소가 없다');
      final saved = await container.read(visitApiProvider).day(shopId, DateTime.parse(date));
      soft(saved.items.length == 1, '예약이 저장되지 않았다(${saved.items.length}건)');
      visitId = saved.items.first.visit.visitId;
    });

    await step('F3', '방문 상세 — 보낸 날이 보이고, ··· 의 [보호자에게 보내기]로 다시 열어 동의서를 빼고 보낸다', () async {
      await openVisit(visitId);
      await waitFor(consentLine());
      soft(find.textContaining('에 보냈어요').evaluate().isNotEmpty, '보낸 날이 줄에 없다');
      await tap(find.bySemanticsLabel(AppStrings.more));
      await tap(find.text(AppStrings.actionSendToGuardian));
      await waitFor(find.text(AppStrings.bundleSheetTitle));
      await tap(find.byKey(const ValueKey('bundle-toggle-consent')));
      await shot('F3-removed');
      await tap(find.byKey(SendBundleSheet.sendKey));
      await pumpFor(const Duration(seconds: 1));
      soft(share.shared.length == 2 && !share.shared.last.contains('/f/'), '뺀 동의서가 나갔다');
      soft(find.byKey(ScreenKeys.visitDetail).evaluate().isNotEmpty, '방문 상세가 닫혔다');
    });

    await step('F4', '설정 → 서류 — 설정 없이 기본값이고, 노령 안내의 글을 고쳐 저장하면 고침이 붙는다', () async {
      router.push('/settings/forms');
      await waitFor(find.byKey(ScreenKeys.formSettings));
      await shot('F4-settings');
      // 목록이 게을러 아래의 칩은 내려야 그려진다.
      for (final label in ['14일', '10살', '1년']) {
        await reveal(chip(label));
        soft(t.widget<AppChoiceChip>(chip(label)).selected, '기본값이 골라져 있지 않다: $label');
      }
      await shot('F4-settings-bottom');
      await tap(find.text(AppStrings.consentPartTitleSenior));
      await waitFor(find.byKey(ScreenKeys.formTextEdit));
      await t.enterText(find.byKey(FormTextEdit.inputKey), newSeniorText);
      await pumpFor(const Duration(milliseconds: 300));
      soft(
        find.descendant(of: find.byKey(FormTextEdit.previewKey), matching: find.text(newSeniorText)).evaluate().isNotEmpty,
        '보호자가 받는 모습이 따라 바뀌지 않았다',
      );
      await shot('F4-edit');
      await tap(find.byKey(FormTextEdit.saveKey));
      await waitFor(find.text(AppStrings.formEdited));
      soft(find.byKey(ScreenKeys.formTextEdit).evaluate().isEmpty, '저장 뒤 고치는 화면이 남아 있다');
    });

    await step('F5', '방문 상세의 [여기서 서명] — 서명 화면에 고친 글이 보인다', () async {
      router.pop();
      await openVisit(visitId);
      await tap(find.byKey(ValueKey('consent-sign-$petId')));
      await waitFor(find.byKey(ScreenKeys.consentSign));
      await waitFor(find.text(newSeniorText));
      await shot('F5-sign');
      await tap(find.bySemanticsLabel(AppStrings.back).last);
      await tap(find.text(AppStrings.consentLeave));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
    });

    await step('F6', '노령으로 보는 나이를 직접 20살로 — 12살 아이의 동의 줄이 사라진다', () async {
      router.push('/settings/forms');
      await waitFor(find.byKey(ScreenKeys.formSettings));
      await tap(find.byKey(const ValueKey('form-custom-senior_age')));
      await t.enterText(find.byKey(const ValueKey('form-custom-input')), '30');
      await tap(find.byKey(const ValueKey('form-custom-save')));
      soft(find.byKey(const ValueKey('form-custom-input')).evaluate().isNotEmpty, '범위 밖의 값인데 시트가 닫혔다');
      await t.enterText(find.byKey(const ValueKey('form-custom-input')), '20');
      await tap(find.byKey(const ValueKey('form-custom-save')));
      await reveal(chip('20살'));
      soft(t.widget<AppChoiceChip>(chip('20살')).selected, '바꾼 값이 골라져 있지 않다');
      await shot('F6-age');
      router.pop();
      await pumpFor(const Duration(seconds: 1));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await pumpFor(const Duration(seconds: 1));
      soft(consentLine().evaluate().isEmpty, '노령이 아닌데 동의 줄이 남아 있다');
      await shot('F6-visit');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
