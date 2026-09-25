// ④-2b 완료 기준 — 실제 백엔드(MinIO 포함)에 붙은 앱을 시뮬레이터에서 조작해 사진 보기(넘기기·크게 보기·
// 원본 저장·전/후 바꾸기·대표로·삭제)와 피드·달력·고객 탭 사진·[기록] 탭을 확인한다. 도구는 `flow_kit.dart`.
//
// 사진 선택기만 바꿔 끼운다 — 부를 때마다 4000×3000 PNG 두 장. 렌디션·올리기·앨범 저장은 실제로 한다.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_record_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로).
// 앨범 저장 권한은 테스트가 시스템 창을 누를 수 없어 미리 준다. `flutter drive`는 끝날 때 앱을 지워 권한도
// 사라지므로 실행할 때마다 바로 앞에 한 번(도는 중에 주면 시뮬레이터가 앱을 끈다):
//   xcrun simctl privacy <기기> grant photos-add com.chagocnote.app
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/photo_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 <준비의 --dart-define 들>

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_photo_fan.dart';
import 'package:chagocnote/design/widgets/app_photo_tile.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/screens/feed_view.dart';
import 'package:chagocnote/features/visit/state/photo_edits.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const visitA = int.fromEnvironment('VISIT_A');
const ownerName = String.fromEnvironment('OWNER');

/// 앨범 대신 — 부를 때마다 PNG 두 장.
class TwoPhotos implements MediaPicker {
  var made = 0;

  Future<String> _make() => makePhoto('pflow-$made', made++);

  @override
  Future<List<String>> pickPhotos({required int limit}) async => [
    await _make(),
    await _make(),
  ];

  @override
  Future<String?> takePhoto() => _make();
}

/// 서버의 기록 사진(보이는 순서 — 대표부터).
Future<List<RecordMedia>> gallery() async {
  final detail = await container.read(visitApiProvider).detail(shopId, visitA);
  return galleryOrder(detail.record?.media ?? const []);
}

String shape(List<RecordMedia> media) =>
    [for (final m in media) '${m.mediaId}:${m.phase.code}'].join(' ');

/// 사진이 들어간 타일(회색 자리가 아닌 것)이 있는가.
bool anyPhotoTile() => t
    .widgetList<AppPhotoTile>(find.byType(AppPhotoTile))
    .any((w) => w.image != null);

/// 서버의 기록에 사진이 [count]장 붙을 때까지 기다린다(대기열이 올려 붙인다). 사진 줄은 가로라 넷째
/// 타일은 화면 밖에서 그려지지 않는다 — 화면 대신 서버를 본다.
Future<void> waitForPhotos(int count) async {
  final end = DateTime.now().add(const Duration(seconds: 90));
  while ((await gallery()).length < count) {
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('사진이 $count장 붙지 않았다');
    }
    await pumpFor(const Duration(seconds: 1));
  }
}

/// 넘기기 안의 사진은 그 자리에서 누른다 — `tap`의 `ensureVisible`이 가로 넘기기까지 굴려 가운데 사진이
/// 옆으로 밀린다.
Future<void> openViewerAt(String label) async {
  await waitFor(p(label));
  await t.tap(p(label).first);
  await pumpFor(const Duration(milliseconds: 500));
  await waitFor(find.byKey(ScreenKeys.photoViewer));
  await pumpFor(const Duration(seconds: 2));
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('④-2b 완료 기준', timeout: const Timeout(Duration(minutes: 20)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(
      buildRoot(
        overrides: [mediaPickerProvider.overrideWithValue(TwoPhotos())],
      ),
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

    await step('1', '미용 중 전 사진 둘 → 완료하기(케어 메모) → 완료 뒤 후 사진 둘', () async {
      await openVisit(visitA);
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.pickFromAlbum));
      await waitForPhotos(2);
      await tap(btn(AppStrings.actionComplete));
      await waitFor(find.byKey(ScreenKeys.visitRecord));
      await pumpFor(const Duration(seconds: 1));
      await enter('careNote', '얼굴은 둥글게, 귀는 짧게.');
      await tap(btn(AppStrings.completeWithRecord));
      await waitFor(find.text(AppStrings.completeTitle));
      await tap(btn(AppStrings.close));
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.pickFromAlbum));
      await waitForPhotos(4);
      await pumpFor(const Duration(seconds: 2));
      await shot('01-four-photos');
      final media = await gallery();
      note('사진 ${shape(media)}');
      soft(media.length == 4, '사진이 넷이 아니다');
      soft(
        media.take(2).every((m) => m.phase == MediaPhase.after),
        '후 사진이 앞(대표)이 아니다',
      );
    });

    await step('2', '상세 넘기기(대표부터·01 / 04) → 가운데 사진 → 크게 보기', () async {
      await openVisit(visitA);
      await pumpFor(const Duration(seconds: 2));
      await shot('02a-detail-pager');
      soft(find.text('01 / 04').evaluate().isNotEmpty, '페이저가 01 / 04 가 아니다');
      await openViewerAt(AppStrings.openPhotoLabel('후', 1));
      await shot('02b-viewer');
      soft(find.text('후 · 1 / 4').evaluate().isNotEmpty, '크게 보기가 대표 사진부터가 아니다');
    });

    await step('3', '원본 저장 → 앨범', () async {
      await tap(p(AppStrings.saveOriginal));
      await waitFor(
        find.text(AppStrings.savedToAlbum),
        timeout: const Duration(seconds: 30),
      );
      await shot('03-saved');
      // 알림 띠가 아래 버튼 줄을 가리는 동안 기다린다.
      await pumpFor(const Duration(seconds: 4));
    });

    await step('4', '대표로 → 전으로 바꾸기 → 삭제, 서버의 기록이 따라 바뀐다', () async {
      final before = await gallery();
      // 둘째 후 사진의 크게 보기를 경로로 연다 — 안드로이드는 테스트가 만든 가짜 밀기를 확대 영역(InteractiveViewer)이
      // 받지 않는다(진짜 터치로는 넘어간다 — 2026-09-26 에뮬레이터에서 확인). 넘기기 자체는 위젯 테스트가 본다.
      router.push('/visits/$visitA/photos/${before[1].mediaId}');
      await waitFor(find.text('후 · 2 / 4'));
      await pumpFor(const Duration(seconds: 1));
      soft(find.text('후 · 2 / 4').evaluate().isNotEmpty, '둘째 후 사진으로 넘어가지 않았다');
      await tap(p(AppStrings.makeCover));
      await waitFor(find.text('후 · 1 / 4'));
      final covered = await gallery();
      note('대표로 뒤 ${shape(covered)}');
      soft(covered.first.mediaId == before[1].mediaId, '둘째 후 사진이 대표가 되지 않았다');
      await shot('04a-made-cover');

      await tap(p(AppStrings.toBefore));
      await pumpFor(const Duration(seconds: 2));
      final toggled = await gallery();
      note('전으로 뒤 ${shape(toggled)}');
      soft(
        toggled.firstWhere((m) => m.mediaId == before[1].mediaId).phase ==
            MediaPhase.before,
        '전으로 바뀌지 않았다',
      );
      await shot('04b-to-before');

      await tap(p(AppStrings.deletePhoto));
      await tap(btn(AppStrings.delete));
      await pumpFor(const Duration(seconds: 2));
      final left = await gallery();
      note('삭제 뒤 ${shape(left)}');
      soft(left.length == 3, '사진이 셋이 아니다');
      await shot('04c-deleted');
    });

    await step('5', '피드 — [피드]로 바꾸면 방금 끝낸 미용이 사진·케어 메모·사진 수로', () async {
      router.go('/home');
      await pumpFor(const Duration(seconds: 1));
      await tap(p(AppStrings.viewAsFeed));
      await waitFor(find.byType(FeedCard));
      await pumpFor(const Duration(seconds: 2));
      await shot('05-feed');
      soft(find.text('얼굴은 둥글게, 귀는 짧게.').evaluate().isNotEmpty, '피드에 케어 메모가 없다');
      soft(
        find.text(AppStrings.mediaCount(3)).evaluate().isNotEmpty,
        '피드에 사진 3장이 없다',
      );
    });

    await step('6', '달력 — 오늘 칸에 대표 사진, 미리보기에 부채꼴', () async {
      await tap(p(AppStrings.viewAsCalendar));
      await pumpFor(const Duration(seconds: 2));
      await shot('06-calendar');
      soft(anyPhotoTile(), '달력 칸에 사진이 없다');
      soft(find.byType(AppPhotoFan).evaluate().isNotEmpty, '미리보기에 사진이 없다');
    });

    await step('7', '고객 탭 — 콩이 프로필 사진, 상세 [기록] 탭', () async {
      await tap(find.text(AppStrings.tabCustomers));
      await pumpFor(const Duration(seconds: 2));
      await shot('07a-customers');
      soft(anyPhotoTile(), '가족 카드에 프로필 사진이 없다');
      await tap(find.text('콩이'));
      await waitFor(find.byKey(ScreenKeys.petDetail));
      await pumpFor(const Duration(seconds: 1));
      soft(anyPhotoTile(), '반려동물 상세에 프로필 사진이 없다');
      await tap(find.text(AppStrings.petTabRecords));
      await waitFor(find.byType(FeedCard));
      await pumpFor(const Duration(seconds: 1));
      await shot('07b-pet-records');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
