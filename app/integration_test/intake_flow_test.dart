// ⑪-C3 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해, 보호자가 낸 문진표가 고객 탭의 `받은 문진표 1` 로
// 들어오고 누르기 두 번([줄] → [이대로 등록])으로 고객·아이가 생기는지, 문진표 링크를 보내면 보낸 서류에 남는지,
// 서류 설정에서 칸을 끄고 질문을 더한 것이 서버에 남는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_intake_flow.sh → 마지막 줄의 --dart-define 들(기기마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/intake_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>
//
// 공유 시트만 바꿔 끼운다(받은 글을 적어 두는 [RecordingShareSheet]) — 실제 시트는 테스트가 닫지 못한다.
// **보내는 글은 문진표 주소(토큰)다** — 단계 이름·실패 문구·스크린샷 설명에 적지 않는다. 적은 이름·번호도 찍지 않는다.

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/features/customer/screens/intake_questions_screen.dart';
import 'package:chagocnote/features/customer/screens/received_intake_screens.dart';
import 'package:chagocnote/features/customer/state/form_settings_providers.dart';
import 'package:chagocnote/features/customer/state/intake_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const ownerName = String.fromEnvironment('OWNER');

const question = '산책은 얼마나 하나요?';

class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];

  @override
  Future<void> shareText(String text, {required Rect origin}) async {
    shared.add(text);
  }
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑪-C3 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
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

    await step('I1', '고객 탭에 받은 문진표 1 — 누르면 목록, 줄을 누르면 한 장(빈 칸 없음)', () async {
      await tap(find.text(AppStrings.tabCustomers));
      await waitFor(find.text(AppStrings.receivedIntakeEntry(1)));
      await shot('I1-entry');
      await tap(find.text(AppStrings.receivedIntakeEntry(1)));
      await waitFor(find.byKey(ScreenKeys.receivedIntake));
      await shot('I1-list');
      await tap(find.text('모카'));
      await waitFor(find.byKey(ScreenKeys.intakeAnswer));
      await waitFor(find.byKey(IntakeAnswerScreen.registerKey));
      await shot('I1-answer');
    });

    await step('I2', '[이대로 등록] 한 번으로 고객·아이가 생기고 새 아이의 상세로 간다 — 답은 사라진다', () async {
      await tap(find.byKey(IntakeAnswerScreen.registerKey));
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await waitFor(find.text('모카'));
      await shot('I2-pet');
      final left = await container.read(intakeApiProvider).answers(shopId);
      soft(left.isEmpty, '등록한 답이 남아 있다(${left.length})');
      router.go('/home');
      await waitFor(find.byKey(ScreenKeys.home));
      await tap(find.text(AppStrings.tabCustomers));
      await pumpFor(const Duration(seconds: 1));
      soft(find.textContaining('받은 문진표').evaluate().isEmpty, '받은 문진표 줄이 남아 있다');
      soft(find.text('모카').evaluate().isNotEmpty, '고객 목록에 새 아이가 없다');
    });

    await step('I3', '고객 등록의 첫 화면에서 [문진표 링크 보내기] — 공유 창에 주소만, 보낸 서류에 새 손님', () async {
      router.push('/customers/new');
      await waitFor(find.byKey(ScreenKeys.registerCustomer));
      await shot('I3-register');
      await tap(find.byKey(const ValueKey('intake-send-new')));
      await pumpFor(const Duration(seconds: 2));
      soft(share.shared.length == 1, '공유 시트가 한 번 불리지 않았다(${share.shared.length})');
      soft(
        share.shared.isNotEmpty && share.shared.first.contains('/f/') && !share.shared.first.contains(' '),
        '공유한 것이 주소 하나가 아니다',
      );
      router.go('/home');
      await waitFor(find.byKey(ScreenKeys.home));
      await tap(find.text(AppStrings.tabCustomers));
      await tap(find.text(AppStrings.sentFormsEntry(1)));
      await waitFor(find.byKey(ScreenKeys.sentForms));
      await waitFor(find.text(AppStrings.sentIntakeNew));
      soft(find.textContaining('http').evaluate().isEmpty, '화면에 주소가 보인다');
      await shot('I3-forms');
    });

    await step('I4', '등록된 아이의 보호자 탭 — [새 아이 문진표 보내기]·[문진표 다시 받기]로 링크가 둘 더 나간다', () async {
      router.go('/home');
      await waitFor(find.byKey(ScreenKeys.home));
      await tap(find.text(AppStrings.tabCustomers));
      await tap(find.text('모카'));
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await tap(find.text(AppStrings.petTabOwner));
      await tap(find.byKey(const ValueKey('intake-send-customer')));
      await pumpFor(const Duration(seconds: 2));
      await tap(find.byKey(const ValueKey('intake-send-pet')));
      await pumpFor(const Duration(seconds: 2));
      await shot('I4-owner');
      soft(share.shared.length == 3, '링크가 둘 더 나가지 않았다(${share.shared.length})');
      soft(share.shared.toSet().length == share.shared.length, '같은 주소가 다시 나갔다');
    });

    await step('I5', '설정 → 서류 — 몸무게 칸을 끄고 보관 기간을 90일로, 서버에 남는다', () async {
      router.push('/settings/forms');
      await waitFor(find.byKey(ScreenKeys.formSettings));
      await reveal(find.text(AppStrings.formSectionIntake));
      await tap(find.byKey(const ValueKey('intake-field-weight')));
      await shot('I5-fields');
      await tap(find.text('90일'));
      await pumpFor(const Duration(seconds: 1));
      await shot('I5-keep');
      final saved = await container.read(formSettingsApiProvider).settings(shopId);
      soft(saved.intakeHidden.length == 1 && saved.intakeHidden.first == 'weight', '끈 칸이 서버에 없다');
      soft(saved.intakeKeepDays == 90, '보관 기간이 서버에 없다(${saved.intakeKeepDays})');
    });

    await step('I6', '매장이 더한 질문 — 하나 더하고 꼭 답하기를 켜 저장하면 설정에 개수가 보인다', () async {
      // 목록이 아래로 내려가 있다 — 다시 열어 위에서부터 찾는다(흐름 도구는 아래로만 굴린다).
      router.pop();
      await pumpFor(const Duration(milliseconds: 500));
      router.push('/settings/forms');
      await waitFor(find.byKey(ScreenKeys.formSettings));
      await tap(find.text(AppStrings.formIntakeQuestions(0)));
      await waitFor(find.byKey(ScreenKeys.intakeQuestions));
      await tap(find.byKey(IntakeQuestionsScreen.addKey));
      await enter('intake-question-0', question);
      await tap(find.byKey(const ValueKey('intake-question-required-0')));
      await shot('I6-question');
      await tap(find.byKey(IntakeQuestionsScreen.saveKey));
      await waitFor(find.text(AppStrings.formIntakeQuestions(1)));
      soft(find.byKey(ScreenKeys.intakeQuestions).evaluate().isEmpty, '저장 뒤 질문 화면이 남아 있다');
      final saved = await container.read(intakeApiProvider).questions(shopId);
      soft(saved.length == 1 && saved.first.label == question && saved.first.required, '질문이 서버에 없다');
      await shot('I6-settings');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
