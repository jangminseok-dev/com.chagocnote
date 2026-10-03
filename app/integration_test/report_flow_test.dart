// ⑤-3 완료 기준 — 실제 백엔드와 보호자 웹(compose 의 `web`)에 붙은 앱을 시뮬레이터에서 조작해 알림장
// 보내기·링크 열기·다시 공유·설정·끊기·다시 보내기를 확인한다. 도구는 `flow_kit.dart`.
//
// 공유 시트만 바꿔 끼운다 — 받은 글(링크)을 적어 두는 [RecordingShareSheet]. 마지막 확인에서만 실제
// 채널로도 넘겨 OS 공유 시트를 띄운다(여는 것까지 — 흐름은 시트를 띄운 채 끝난다).
// 링크에는 토큰이 들어 있다. 흐름은 주소를 찍지 않고 같다·다르다만 본다.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_report_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   보호자 웹(http://127.0.0.1:3010)이 떠 있어야 한다 — 흐름이 받은 링크를 실제로 연다.
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`·`tcp:9010`에 더해 `adb reverse tcp:3010 tcp:3010`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/report_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'dart:convert';

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/core/time/shop_time.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/features/visit/screens/feed_view.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const visitId = int.fromEnvironment('VISIT');
const ownerName = String.fromEnvironment('OWNER');
const staffName = String.fromEnvironment('STAFF');

/// 공유 시트 자리 — 받은 글을 차례로 적어 둔다. [real] 이면 실제 채널로도 넘긴다.
class RecordingShareSheet implements ShareSheet {
  final shared = <String>[];
  var real = false;
  final _channel = ChannelShareSheet();

  @override
  Future<void> shareText(String text, {required Rect origin}) async {
    shared.add(text);
    if (real) await _channel.shareText(text, origin: origin);
  }
}

/// 보호자 웹이 그 주소에 준 첫 HTML.
Future<String> openLink(String url) async =>
    utf8.decode(await download(url), allowMalformed: true);

/// 찾아서 화면 안으로 옮긴다 — 방문 상세의 알림장 줄과 버튼은 맨 아래라, 옮겨야 스크린샷에 보인다.
Future<void> bring(Finder f) async {
  await reveal(f);
  await t.ensureVisible(f.first);
  await pumpFor(const Duration(milliseconds: 300));
}

final sentChip = find.text(
  '${AppStrings.statusCompleted} · ${AppStrings.reportSentMark}',
);

final amountSwitch = find.byWidgetPredicate(
  (w) => w is AppSwitch && w.semanticLabel == AppStrings.reportItemAmount,
);

bool get amountOn => t.widget<AppSwitch>(amountSwitch).value;

Future<void> waitAmount(bool on) async {
  final end = DateTime.now().add(const Duration(seconds: 20));
  while (amountOn != on) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('금액 스위치가 $on 이 되지 않았다');
    }
    await pumpFor(const Duration(milliseconds: 100));
  }
}

Future<void> openReportSettings() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 500));
  await tap(p(AppStrings.settingsLabel));
  await waitFor(find.byKey(ScreenKeys.settings));
  await tap(p(AppStrings.settingsReport));
  await waitFor(find.byKey(ScreenKeys.reportSettings));
  await waitFor(amountSwitch);
}

/// 방문 상세에서 미리보기를 열어 [shown]("2개 중 N개")이 보일 때까지 기다린다.
Future<void> openPreview(String shown) async {
  await tap(btn(AppStrings.reportStart));
  await waitFor(find.byKey(ScreenKeys.reportPreview));
  await waitFor(find.text(shown));
  await pumpFor(const Duration(seconds: 1));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑤-3 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (
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
    await login(ownerName);

    await step('1', '완료한 방문 상세 — "아직 안 보냄"과 [알림장 보내기]', () async {
      await openVisit(visitId);
      soft(sentChip.evaluate().isEmpty, '보내기 전인데 "알림장 보냄" 꼬리표가 있다');
      await bring(btn(AppStrings.reportStart));
      await shot('01-detail-unsent');
      soft(
        find.text(AppStrings.reportNotSent).evaluate().isNotEmpty,
        '"아직 안 보냄"이 없다',
      );
    });

    await step('2', '미리보기 — 전 사진을 빼고 [보내기] → 링크를 공유 시트에 한 번 넘기고 상세가 보낸 모습', () async {
      await openPreview(AppStrings.reportShownCount(2, 2));
      await shot('02a-preview');
      await tap(p('전 사진 1'));
      await waitFor(find.text(AppStrings.reportShownCount(2, 1)));
      await shot('02b-preview-one-hidden');
      await tap(btn(AppStrings.reportSend));
      // 닫히면 방문 상세가 스스로 다시 읽어 아래 버튼이 [다시 공유]로 바뀐다.
      await waitFor(btn(AppStrings.reportShareAgain));
      soft(share.shared.length == 1, '공유 시트가 한 번 불리지 않았다(${share.shared.length})');
      await openVisit(visitId);
      await waitFor(sentChip);
      await shot('02c-detail-sent');
      soft(
        find.text(AppStrings.reportNotViewed).evaluate().isNotEmpty,
        '"아직 안 열었어요"가 없다',
      );
    });

    await step('3', '받은 링크를 보호자 웹이 연다 — 이름·케어 메모가 있고 뺀 전 사진은 없다', () async {
      final page = await openLink(share.shared.first);
      note('링크 ${share.shared.first.length}글자, 첫 HTML ${page.length}글자');
      soft(page.contains('두부의 미용 알림장'), '알림장 제목이 없다');
      soft(page.contains('눈물 자국을 닦았어요.'), '케어 메모가 없다');
      soft(page.contains('미용 후'), '후 사진이 없다');
      soft(!page.contains('미용 전'), '뺀 전 사진이 보인다');
    });

    await step('4', '하루 목록·피드에 "알림장 보냄" 표시', () async {
      final detail = await container
          .read(visitApiProvider)
          .detail(shopId, visitId);
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 500));
      router.push('/visits/day/${isoDay(detail.visit.startsAt.day)}');
      await waitFor(find.byKey(ScreenKeys.day));
      await waitFor(
        find.descendant(
          of: find.byKey(ScreenKeys.day),
          matching: find.textContaining(AppStrings.reportSentMark),
        ),
      );
      await shot('04a-day');
      router.go('/home');
      await pumpFor(const Duration(seconds: 1));
      await tap(p(AppStrings.viewAsFeed));
      await waitFor(
        find.descendant(
          of: find.byType(FeedCard),
          matching: find.textContaining(AppStrings.reportSentMark),
        ),
      );
      await pumpFor(const Duration(seconds: 1));
      await shot('04b-feed');
    });

    await step('5', '보낸 방문은 되돌리지 못한다 — "링크를 먼저 끊어 주세요"', () async {
      await openVisit(visitId);
      await tap(p(AppStrings.more));
      await tap(find.text(AppStrings.actionRevert));
      await bring(find.text('알림장을 보낸 방문이에요. 링크를 먼저 끊어 주세요.'));
      await shot('05-revert-refused');
      soft(
        btn(AppStrings.reportShareAgain).evaluate().isNotEmpty,
        '되돌리기가 거절됐는데 보낸 모습이 아니다',
      );
    });

    await step('6', '[다시 공유] — 같은 주소를 넘긴다', () async {
      await tap(btn(AppStrings.reportShareAgain));
      soft(share.shared.length == 2, '공유 시트가 다시 불리지 않았다(${share.shared.length})');
      soft(share.shared.last == share.shared.first, '다시 공유한 주소가 처음과 다르다');
    });

    await step('7', '설정 — 사장이 금액을 켜면 다시 열어도 켜져 있고(끄고 나온다), 직원은 읽기 전용', () async {
      await openReportSettings();
      soft(!amountOn, '금액이 처음부터 켜져 있다');
      await tap(amountSwitch);
      await waitAmount(true);
      await shot('07a-settings-amount-on');
      await openReportSettings();
      soft(amountOn, '다시 열었더니 금액이 꺼져 있다');
      await tap(amountSwitch);
      await waitAmount(false);
      await logout();
      await login(staffName);
      await openReportSettings();
      await shot('07b-settings-staff');
      soft(
        find.text(AppStrings.reportSettingsOwnerOnly).evaluate().isNotEmpty,
        '직원에게 읽기 전용 안내가 없다',
      );
      soft(!amountOn, '사장이 끈 금액이 직원에게 켜져 보인다');
      soft(
        t.widget<AppSwitch>(amountSwitch).onChanged == null,
        '직원의 스위치가 눌린다',
      );
    });

    // 여기부터 직원이다 — 끊기·보내기는 직원도 한다(record:write).
    await step('8', '직원이 [링크 끊기] → "아직 안 보냄", 옛 주소는 닫힌 알림장', () async {
      await openVisit(visitId);
      await tap(p(AppStrings.more));
      await tap(find.text(AppStrings.reportRevoke));
      await waitFor(find.text(AppStrings.reportRevokeConfirm));
      await shot('08a-revoke-confirm');
      await tap(btn(AppStrings.reportRevoke));
      await bring(find.text(AppStrings.reportNotSent));
      await shot('08b-revoked');
      soft(
        btn(AppStrings.reportStart).evaluate().isNotEmpty,
        '끊었는데 [알림장 보내기]가 없다',
      );
      final page = await openLink(share.shared.first);
      soft(page.contains('닫힌 알림장이에요'), '옛 주소가 닫힌 알림장이 아니다');
      soft(!page.contains('두부의 미용 알림장'), '옛 주소가 아직 열린다');
    });

    await step('9', '다시 보내기 — 전 사진은 여전히 빠져 있고, 새 주소는 옛 주소와 다르다', () async {
      await openPreview(AppStrings.reportShownCount(2, 1));
      await shot('09a-preview-still-hidden');
      await tap(btn(AppStrings.reportSend));
      await waitFor(btn(AppStrings.reportShareAgain));
      await shot('09b-detail-resent');
      soft(share.shared.length == 3, '공유 시트가 불리지 않았다(${share.shared.length})');
      soft(share.shared.last != share.shared.first, '새 주소가 옛 주소와 같다');
      final page = await openLink(share.shared.last);
      soft(page.contains('두부의 미용 알림장'), '새 주소가 열리지 않는다');
    });

    await step('10', '실제 채널로 [다시 공유] — OS 공유 시트가 뜬다(여는 것까지)', () async {
      share.real = true;
      await tap(btn(AppStrings.reportShareAgain));
      // 시트는 채널이 끝난 뒤에 올라온다 — 시뮬레이터에서는 몇 초 걸린다.
      await pumpFor(const Duration(seconds: 8));
      await shot('10-share-sheet');
      soft(share.shared.length == 4, '공유 시트가 불리지 않았다(${share.shared.length})');
      soft(share.shared.last == share.shared[2], '다시 공유한 주소가 새 주소와 다르다');
      soft(
        find.text(AppStrings.reportShareAgainFailed).evaluate().isEmpty,
        '공유 시트를 띄우지 못했다는 안내가 떴다',
      );
      // 시트가 머리를 그리려고 주소를 받아 오면 보호자보다 먼저 열린다 — 띄운 것만으로 열람이 찍히면 안 된다.
      final detail = await container
          .read(visitApiProvider)
          .detail(shopId, visitId);
      soft(detail.report.firstViewedAt == null, '공유 시트를 띄운 것만으로 열람이 찍혔다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
