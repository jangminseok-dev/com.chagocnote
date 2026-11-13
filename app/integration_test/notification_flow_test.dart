// ⑥-2 완료 기준 — 실제 백엔드(dev 의 가짜 게이트웨이 — 실제 발송 없음)에 붙은 앱을 시뮬레이터에서 조작해
// 채널 연동·알림톡 설정·방문 상세의 발송 내역·다른 방법으로 보내기·알림장을 알림톡으로 보내기를 확인한다.
// 도구는 `flow_kit.dart`.
//
// 매장 둘을 쓴다 — 앱에서 연동 화면을 직접 밟는 새 매장(템플릿은 "심사 중"까지만 본다. 앱 안에서 승인을
// 당길 방법이 없다)과, 준비 스크립트가 연동·승인·예약까지 끝낸 매장(발송을 본다).
// 공유 시트만 바꿔 끼운다 — 받은 글을 적어 두는 [RecordingShareSheet]. 글에는 번호·주소가 들 수 있어
// 흐름은 찍지 않고 개수와 비었는지만 본다.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_notification_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/notification_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_sheet_action.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const visitOk = int.fromEnvironment('VISIT_OK');
const visitFail = int.fromEnvironment('VISIT_FAIL');
const visitDone = int.fromEnvironment('VISIT_DONE');
const ownerName = String.fromEnvironment('OWNER');
const staffName = String.fromEnvironment('STAFF');
const newOwnerName = String.fromEnvironment('OWNER_NEW');
const channelId = String.fromEnvironment('CHANNEL');
const adminPhone = String.fromEnvironment('ADMIN_PHONE');

/// 공유 시트 자리 — 받은 글을 차례로 적어 둔다(찍지 않는다).
class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];

  @override
  Future<void> shareText(String text, {required Rect origin}) async {
    shared.add(text);
  }
}

bool shown(String text) => find.textContaining(text).evaluate().isNotEmpty;

Future<void> bring(Finder f) async {
  await reveal(f);
  await t.ensureVisible(f.first);
  await pumpFor(const Duration(milliseconds: 300));
}

Future<void> openNotificationSettings() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 500));
  await tap(p(AppStrings.settingsLabel));
  await waitFor(find.byKey(ScreenKeys.settings));
  await tap(p(AppStrings.settingsNotification));
  await waitFor(find.byKey(ScreenKeys.notificationSettings));
}

/// 방문 상세의 알림톡 블록에 [text]가 든 줄이 뜰 때까지 상세를 다시 읽으며 기다린다 — 발송은 서버의
/// 디스패처가 몇 초 뒤에 한다.
Future<void> awaitRow(String text) async {
  final end = DateTime.now().add(const Duration(seconds: 40));
  while (!shown(text)) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('알림톡 줄이 뜨지 않았다: $text');
    }
    container.invalidate(visitDetailProvider);
    await pumpFor(const Duration(seconds: 2));
  }
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑥-2 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    final share = RecordingShareSheet();
    await t.pumpWidget(
      buildRoot(overrides: [shareSheetProvider.overrideWithValue(share)]),
    );
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
    await login(newOwnerName);

    await step('1', '새 매장 — 준비 안내, 인증번호 받기, 연동하면 스위치와 "심사 중"', () async {
      await openNotificationSettings();
      await waitFor(find.text(AppStrings.notificationPrepare1));
      await shot('01-unlinked');
      soft(find.byType(AppSwitch).evaluate().isEmpty, '연동 전인데 스위치가 있다');

      await enter('notification_search_id', channelId);
      await enter('notification_admin_phone', adminPhone);
      await enter('notification_category', '003001');
      await tap(btn(AppStrings.notificationRequestToken));
      await waitFor(find.byKey(const ValueKey('notification_token')));
      await shot('01-token');
      await enter('notification_token', '000000');
      await tap(btn(AppStrings.notificationLink));

      await waitFor(find.textContaining('연동됨'));
      await pumpFor(const Duration(seconds: 1));
      await shot('01-linked');
      soft(
        find.byType(AppSwitch).evaluate().length == 6,
        '스위치가 여섯이 아니다(${find.byType(AppSwitch).evaluate().length})',
      );
      // 디스패처의 10분 주기가 그 사이에 돌았으면 이미 승인이다 — 둘 가운데 하나면 된다.
      soft(
        shown(AppStrings.notificationTemplatePending) ||
            shown(AppStrings.notificationTemplateApproved),
        '템플릿 상태 문구가 없다',
      );
      soft(find.byType(TextField).evaluate().isEmpty, '연동 뒤에도 입력 칸이 남았다');
    });

    await logout();
    await login(ownerName);

    await step('2', '연동·승인된 매장 — "승인됨", 리마인드 시각을 바꾸면 다시 열어도 그대로', () async {
      await openNotificationSettings();
      await waitFor(find.text(AppStrings.notificationTemplateApproved));
      await tap(find.text('18:00'));
      await tap(
        find.byWidgetPredicate(
          (w) => w is AppSheetAction && w.label == '09:30',
        ),
      );
      await waitFor(find.text('09:30'));
      await shot('02-settings');

      await openNotificationSettings();
      await waitFor(find.text(AppStrings.notificationTemplateApproved));
      soft(shown('09:30'), '다시 열었더니 바꾼 시각이 아니다');
      soft(!shown('18:00'), '옛 시각이 남아 있다');
    });

    await step('3', '예약한 방문 — "예약 접수 · 보냄"과 전날 리마인드 예정', () async {
      await openVisit(visitOk);
      await awaitRow(
        '${AppStrings.notificationRowConfirm} · ${AppStrings.notificationSent('')}',
      );
      await bring(find.text(AppStrings.notificationBlockTitle));
      await shot('03-detail-sent');
      soft(shown(AppStrings.notificationRowReminder), '전날 리마인드 줄이 없다');
      soft(shown('09:30 예정'), '리마인드가 바꾼 시각으로 예정되지 않았다');
      soft(share.shared.isEmpty, '아무것도 누르지 않았는데 공유 시트가 불렸다');
    });

    await step('4', '못 받는 번호 — "못 보냈어요"와 [다른 방법으로 보내기]', () async {
      await openVisit(visitFail);
      await awaitRow(
        '${AppStrings.notificationRowConfirm} · ${AppStrings.notificationFailed} · ${AppStrings.notificationFailedPermanent}',
      );
      await bring(btn(AppStrings.notificationShareInstead));
      await shot('04-detail-failed');
      await tap(btn(AppStrings.notificationShareInstead));
      soft(share.shared.length == 1, '공유 시트가 불리지 않았다(${share.shared.length})');
      soft(
        share.shared.isNotEmpty && share.shared.last.isNotEmpty,
        '공유 시트에 넘긴 글이 비었다',
      );
      soft(
        btn(AppStrings.notificationResend).evaluate().isEmpty,
        '영구 실패인데 [다시 보내기]가 있다',
      );
    });

    await step('5', '알림장 보내기 — "알림톡으로 보냈어요", 공유 시트는 뜨지 않는다', () async {
      await openVisit(visitDone);
      await tap(btn(AppStrings.reportStart));
      await waitFor(find.byKey(ScreenKeys.reportPreview));
      await pumpFor(const Duration(seconds: 1));
      await tap(btn(AppStrings.reportSend));
      await waitFor(
        find.text(AppStrings.reportSentByAlimtalk),
        timeout: const Duration(seconds: 20),
      );
      await shot('05-sent-by-alimtalk');
      soft(share.shared.length == 1, '알림톡으로 나갔는데 공유 시트가 불렸다');
      await waitFor(find.byKey(ScreenKeys.visitDetail));
      await awaitRow(
        '${AppStrings.notificationRowReport} · ${AppStrings.notificationSent('')}',
      );
      await bring(find.text(AppStrings.notificationBlockTitle));
      await shot('05-detail-report');
    });

    await logout();
    await login(staffName);

    await step('6', '직원 — 알림톡 설정은 읽기 전용', () async {
      await openNotificationSettings();
      await waitFor(find.text(AppStrings.notificationOwnerOnly));
      await shot('06-staff');
      soft(
        t
            .widgetList<AppSwitch>(find.byType(AppSwitch))
            .every((s) => s.onChanged == null),
        '직원인데 눌리는 스위치가 있다',
      );
      soft(p(AppStrings.more).evaluate().isEmpty, '직원에게 연동 해제가 보인다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
