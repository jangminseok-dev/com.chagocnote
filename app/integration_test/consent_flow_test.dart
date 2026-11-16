// ⑪-A3 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해, 방문 상세의 동의 줄에서 그 자리에서 서명받고
// (네이티브 서명 칸), 동의 줄이 사라지고, 받은 서명을 다시 보고, 다른 아이에게 동의서 링크를 보내고, 고객 탭의
// 보낸 서류에서 그 링크를 끊는지 확인한다. 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_consent_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/consent_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>
//
// 공유 시트만 바꿔 끼운다(받은 글을 적어 두는 [RecordingShareSheet]) — 실제 시트는 테스트가 닫지 못한다.
// **링크 주소에는 토큰이 들어 있다** — 단계 이름·실패 문구·스크린샷 설명에 적지 않고 길이와 같다·다르다만 본다.

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/features/customer/screens/consent_sign_screen.dart';
import 'package:chagocnote/features/customer/screens/consent_signatures_screen.dart';
import 'package:chagocnote/features/customer/screens/signature_pad.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const petId = int.fromEnvironment('PET');
const visitId = int.fromEnvironment('VISIT');
const otherPetId = int.fromEnvironment('PET2');
const otherVisitId = int.fromEnvironment('VISIT2');
const ownerName = String.fromEnvironment('OWNER');

class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];

  @override
  Future<void> shareText(String text, {required Rect origin}) async {
    shared.add(text);
  }
}

final signScreen = find.byKey(ScreenKeys.consentSign);
Finder consentLine() => find.textContaining('미용 동의서');

/// 서명 칸에 손가락으로 긋는다.
Future<void> drawSignature() async {
  final pad = find.byKey(SignaturePad.canvasKey);
  await reveal(pad);
  await t.ensureVisible(pad);
  await pumpFor(const Duration(milliseconds: 300));
  final box = t.getRect(pad);
  final gesture = await t.startGesture(Offset(box.left + box.width * 0.2, box.center.dy));
  for (final (fx, fy) in [(0.35, 0.3), (0.5, 0.7), (0.65, 0.3), (0.8, 0.6)]) {
    await gesture.moveTo(Offset(box.left + box.width * fx, box.top + box.height * fy));
    await t.pump(const Duration(milliseconds: 40));
  }
  await gesture.up();
  await pumpFor(const Duration(milliseconds: 300));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑪-A3 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (tester) async {
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

    await step('C1', '노령·지병 아이의 방문 상세 — 동의 줄과 버튼 셋', () async {
      await openVisit(visitId);
      await waitFor(consentLine());
      for (final label in [AppStrings.consentSend, AppStrings.consentSignHere, AppStrings.consentReceived]) {
        soft(btn(label).evaluate().isNotEmpty, '버튼이 없다: $label');
      }
      await shot('C1-visit');
    });

    await step('C2', '[여기서 서명] 한 번으로 서명 화면 — 토막 셋, 빠진 것은 그 자리에서 말한다', () async {
      await tap(find.byKey(ValueKey('consent-sign-$petId')));
      await waitFor(signScreen);
      await waitFor(find.text(AppStrings.consentPartTitleBasic));
      for (final title in [AppStrings.consentPartTitleSenior, AppStrings.consentPartTitleCondition]) {
        soft(find.text(title).evaluate().isNotEmpty, '토막이 없다: $title');
      }
      soft(find.textContaining('심장 질환').evaluate().isNotEmpty, '지병의 이름이 없다');
      soft(find.textContaining('약 복용 중').evaluate().isEmpty, '지병의 메모가 보인다');
      soft(find.textContaining('법적').evaluate().isEmpty, '효력을 말하는 글이 있다');
      await shot('C2-document');
      await tap(find.byKey(ConsentSignScreen.submitKey));
      await waitFor(find.text(AppStrings.consentNameMissing));
    });

    await step('C3', '이름·서명·체크 → 보내기 → 보냈어요 → [닫기] → 동의 줄이 사라진다', () async {
      await enter('consent-name', '김초코');
      await drawSignature();
      soft(find.text(AppStrings.signaturePadHint).evaluate().isEmpty, '그었는데 빈 칸의 안내가 남아 있다');
      await shot('C3-signed');
      await tap(find.byKey(ConsentSignScreen.agreeKey));
      await tap(find.byKey(ConsentSignScreen.submitKey));
      await waitFor(find.text(AppStrings.consentDoneTitle));
      soft(signScreen.evaluate().isNotEmpty, '보낸 뒤 화면이 저절로 닫혔다');
      await shot('C3-done');
      await tap(find.byKey(ConsentSignScreen.closeKey));
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await pumpFor(const Duration(seconds: 1));
      soft(consentLine().evaluate().isEmpty, '서명했는데 동의 줄이 남아 있다');
      await shot('C3-visit-after');
    });

    await step('C4', '반려동물 상세 — 서명 받음 → [서명 보기] → 한 장에 그때의 글과 서명 그림', () async {
      router.push('/pets/$petId');
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await waitFor(find.textContaining('서명 받음'));
      await tap(find.byKey(const ValueKey('grooming-consent-signatures')));
      await waitFor(find.byKey(ScreenKeys.consentSignatures));
      await waitFor(find.textContaining(AppStrings.signatureViaShop));
      await shot('C4-list');
      await tap(find.textContaining(AppStrings.signatureViaShop));
      await waitFor(find.text(AppStrings.signatureDetailTitle));
      soft(find.text(AppStrings.signatureNoteShop).evaluate().isNotEmpty, '매장에서 받은 서명이라는 글이 없다');
      // 글이 길어 이름과 그림은 화면 아래에 있다 — 내려서 본다.
      await reveal(find.byKey(ConsentSignatureScreen.imageKey));
      await t.ensureVisible(find.byKey(ConsentSignatureScreen.imageKey));
      await pumpFor(const Duration(milliseconds: 500));
      soft(find.text(AppStrings.signatureSigner('김초코')).evaluate().isNotEmpty, '적은 이름이 없다');
      final drawn = t.widget<Image>(find.byKey(ConsentSignatureScreen.imageKey)).image as MemoryImage;
      soft(drawn.bytes.length > 100, '서명 그림이 비어 있다');
      await shot('C4-signature');
    });

    await step('C5', '다른 아이의 방문에서 [동의서 보내기] 한 번 — 공유 시트에 주소 하나, 버튼이 [다시 공유]로', () async {
      await openVisit(otherVisitId);
      await waitFor(consentLine());
      await tap(find.byKey(ValueKey('consent-send-$otherPetId')));
      await waitFor(btn(AppStrings.consentShareAgain));
      soft(share.shared.length == 1, '공유 시트가 한 번 불리지 않았다(${share.shared.length})');
      soft(share.shared.isNotEmpty && share.shared.first.contains('/f/'), '공유한 글이 서류 주소가 아니다');
      soft(find.textContaining('에 보냈어요').evaluate().isNotEmpty, '보낸 날이 줄에 없다');
      await tap(find.byKey(ValueKey('consent-send-$otherPetId')));
      await pumpFor(const Duration(seconds: 1));
      soft(share.shared.length == 2 && share.shared[0] == share.shared[1], '다시 공유한 주소가 처음과 다르다');
      await shot('C5-sent');
    });

    await step('C6', '고객 탭의 보낸 서류 1 → 목록 → [링크 끊기] → 줄이 사라진다', () async {
      router.go('/home');
      await waitFor(find.byKey(ScreenKeys.home));
      await tap(find.text(AppStrings.tabCustomers));
      await waitFor(find.text(AppStrings.sentFormsEntry(1)));
      await shot('C6-entry');
      await tap(find.text(AppStrings.sentFormsEntry(1)));
      await waitFor(find.byKey(ScreenKeys.sentForms));
      await waitFor(find.text('라떼'));
      soft(find.textContaining('http').evaluate().isEmpty, '화면에 주소가 보인다');
      await shot('C6-forms');
      await tap(btn(AppStrings.sentFormRevoke));
      await waitFor(find.text(AppStrings.sentFormRevokeAsk));
      await tap(find.text(AppStrings.sentFormRevokeConfirm));
      await waitFor(find.text(AppStrings.sentFormsEmpty));
      await shot('C6-revoked');
    });

    await step('C7', '끊은 뒤 그 방문의 버튼은 다시 [동의서 보내기]이고, 보내면 새 주소다', () async {
      await openVisit(otherVisitId);
      await waitFor(btn(AppStrings.consentSend));
      await tap(find.byKey(ValueKey('consent-send-$otherPetId')));
      await waitFor(btn(AppStrings.consentShareAgain));
      soft(share.shared.length == 3 && share.shared[2] != share.shared[0], '끊은 뒤에도 같은 주소가 나갔다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
