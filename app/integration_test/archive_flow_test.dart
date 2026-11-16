// ⑫-3 완료 기준 — 실제 백엔드에 붙은 앱을 시뮬레이터에서 조작해, 알림장 설정의 몸무게가 보이는 모습·리뷰 남기기 줄
// ([열어 보기]는 채널을 부른 데까지)·가족 수, 보낸 알림장의 리뷰 줄 빼기, 보호자 연결 줄의 가족 수를 확인한다.
// 도구는 `flow_kit.dart`.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_archive_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
//   준비가 알림장을 보내고 보호자 계정(웹 세션)으로 이은 뒤 가족 한 명을 잇는다. 보호자 웹은 떠 있지 않아도 된다.
//   에뮬레이터는 `adb reverse tcp:8080 tcp:8080`.
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/archive_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/external_link.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_switch.dart';
import 'package:chagocnote/features/visit/state/report_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const petId = int.fromEnvironment('PET');
const visitId = int.fromEnvironment('VISIT');
const month = int.fromEnvironment('MONTH');
const day = int.fromEnvironment('DAY');
const ownerName = String.fromEnvironment('OWNER');

/// 시뮬레이터에서 브라우저를 띄우지 않는다 — 채널을 부른 주소만 적는다(설계 5.4).
class RecordingExternalLink implements ExternalLink {
  final opened = <Uri>[];

  @override
  Future<void> open(Uri url) async {
    if (!isOpenableUrl(url)) throw ArgumentError('https 주소만 열 수 있다');
    opened.add(url);
  }
}

const reviewUrl = 'https://m.place.naver.com/place/1/review';

Finder switchOf(String label) =>
    find.byWidgetPredicate((w) => w is AppSwitch && w.semanticLabel == label);

/// 설정 → 알림장을 연다.
Future<void> openReportSettings() async {
  router.go('/home');
  await pumpFor(const Duration(milliseconds: 300));
  router.push('/settings/report');
  await waitFor(find.byKey(ScreenKeys.reportSettings));
  await pumpFor(const Duration(seconds: 1));
}

/// 서버에 다시 물어 [ok] 가 될 때까지 기다린다(화면은 다시 읽은 값으로 그린다).
Future<bool> serverSays(Future<bool> Function() ok) async {
  final end = DateTime.now().add(const Duration(seconds: 10));
  while (DateTime.now().isBefore(end)) {
    if (await ok()) return true;
    await pumpFor(const Duration(milliseconds: 500));
  }
  return false;
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('⑫-3 완료 기준', timeout: const Timeout(Duration(minutes: 10)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    final link = RecordingExternalLink();
    await t.pumpWidget(
      buildRoot(overrides: [externalLinkProvider.overrideWithValue(link)]),
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
    final api = container.read(reportApiProvider);

    await step('A1', '설정 — 몸무게를 켜면 스위치 아래에 보호자가 받는 모습', () async {
      await openReportSettings();
      await reveal(find.text(AppStrings.reportWeightOff));
      await shot('A1-weight-off');
      await tap(switchOf(AppStrings.reportItemWeight));
      await waitFor(find.byKey(const ValueKey('report-weight-preview')));
      await shot('A1-weight-on');
      soft(
        await serverSays(() async => (await api.settings(shopId)).showWeight),
        '서버의 몸무게가 켜지지 않았다',
      );
    });

    await step('A2', '리뷰 주소를 넣고 [저장] — 다시 읽은 값으로 그리고 보호자가 받는 모습이 진하다', () async {
      await reveal(find.text(AppStrings.reviewEmptyPreview));
      await enter('report-review-url', reviewUrl);
      await tap(btn(AppStrings.save));
      soft(
        await serverSays(
          () async => (await api.settings(shopId)).reviewUrl == reviewUrl,
        ),
        '서버에 리뷰 주소가 없다',
      );
      await pumpFor(const Duration(seconds: 1));
      soft(
        find.text(AppStrings.reviewEmptyPreview).evaluate().isEmpty,
        '저장한 뒤에도 "주소를 넣으면" 안내가 남았다',
      );
      soft(fieldText('report-review-url') == reviewUrl, '칸의 주소가 다르다');
      await shot('A2-review-saved');
    });

    await step('A3', '[열어 보기] — 바깥 주소 열기 채널이 그 주소를 받는다', () async {
      await tap(btn(AppStrings.reviewOpen));
      soft(
        link.opened.length == 1 && link.opened.single == Uri.parse(reviewUrl),
        '열어 보기가 그 주소로 채널을 부르지 않았다',
      );
    });

    await step('A4', '가족 수 [+] — 고객 한 명당 4명까지, 서버도 4', () async {
      await tap(p(AppStrings.familyMore));
      await waitFor(find.text(AppStrings.familyMaxLine(4)));
      soft(
        await serverSays(
          () async => (await api.guardianSettings(shopId)).familyMax == 4,
        ),
        '서버의 가족 수가 4 가 아니다',
      );
      await shot('A4-family');
    });

    await step('A5', '보낸 알림장의 사진 고르기 — 리뷰 줄을 끄고 [저장] 하면 그 알림장만 뺀다', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 300));
      router.push('/visits/$visitId/report?pick=1');
      final review = find.byKey(const ValueKey('report-preview-review'));
      await waitFor(review);
      await reveal(review);
      soft(t.widget<AppSwitch>(review).value, '보낸 알림장의 리뷰 줄이 처음부터 꺼져 있다');
      await tap(review);
      await shot('A5-review-off');
      await tap(btn(AppStrings.save));
      soft(
        await serverSays(
          () async =>
              (await api.preview(shopId, visitId)).link.showReview == false,
        ),
        '서버의 그 알림장에 리뷰 줄이 남았다',
      );
      // 다시 열면 꺼진 채로 시작한다.
      router.push('/visits/$visitId/report?pick=1');
      await waitFor(review);
      await reveal(review);
      await pumpFor(const Duration(seconds: 1));
      soft(!t.widget<AppSwitch>(review).value, '다시 연 고르기에서 리뷰 줄이 켜져 있다');
    });

    await step('A6', '반려동물 상세 [보호자] 탭 — 연결 줄에 "· 가족 1명"', () async {
      router.go('/home');
      await pumpFor(const Duration(milliseconds: 300));
      router.push('/pets/$petId');
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await tap(find.text(AppStrings.petTabOwner));
      final line = find.text(
        '${AppStrings.guardianLinkedOn(month, day)} · ${AppStrings.guardianFamilyCount(1)}',
      );
      await reveal(line);
      await t.ensureVisible(line);
      await shot('A6-family-count');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
