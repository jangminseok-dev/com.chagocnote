// ④-3a 완료 기준 — 실제 백엔드(MinIO 포함)에 붙은 앱을 시뮬레이터에서 조작해 영상 올리기(압축·포스터·
// 앞 60초 자르기)·크게 보기 재생·원본 저장·방문당 3편 한도·회전 메타를 확인한다. 도구는 `flow_kit.dart`.
//
// 영상 선택기만 바꿔 끼운다 — `integration_test/assets/` 의 표본(만든 명령은 `app/CLAUDE.md`)을 부를 때마다
// 차례로 앱 임시 폴더에 복사해 준다. 압축(네이티브 채널)·발급·올리기·확인·덧붙이기·재생은 실제로 한다.
// 앨범 저장만 받은 파일을 살펴보는 대역으로 바꾼다(시스템 권한 창을 누를 수 없다). 대기열의 간격 재시도는
// 흐름이 기다리지 않게 멈춰 둔다.
//
// 표본 폴더는 `--dart-define=VIDEO_ASSETS=<절대 경로>` 로 받는다(pubspec assets 에 넣지 않는다). 시뮬레이터는
// 맥 파일을 그대로 읽는다. 안드로이드 에뮬레이터는 먼저 `adb push integration_test/assets/. /data/local/tmp/vflow/`
// 하고 `VIDEO_ASSETS=/data/local/tmp/vflow` 를 준다.
//
// 준비(infra/ 에서): bash ../app/tool/prepare_record_flow.sh → 마지막 줄의 --dart-define 들(실행마다 새로)
// 실행(app/ 에서):
//   SHOTS_DIR=... flutter drive --driver=test_driver/integration_test.dart \
//     --target=integration_test/video_flow_test.dart -d <기기> \
//     --dart-define=APP_ENV=dev --dart-define=API_BASE_URL=http://127.0.0.1:8080 \
//     --dart-define=VIDEO_ASSETS=<표본 폴더> <준비의 --dart-define 들>

import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:chagocnote/app.dart';
import 'package:chagocnote/core/error/error_messages.dart';
import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/proxy/photo_album.dart';
import 'package:chagocnote/core/router/screen_keys.dart';
import 'package:chagocnote/design/bridge/glass_setup.dart';
import 'package:chagocnote/design/widgets/app_button.dart';
import 'package:chagocnote/design/widgets/app_video_player.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/upload_job.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:chagocnote/features/visit/state/visit_providers.dart';
import 'package:chagocnote/l10n/app_strings.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';

import 'flow_kit.dart';

const shopId = int.fromEnvironment('SHOP');
const visitA = int.fromEnvironment('VISIT_A');
const visitB = int.fromEnvironment('VISIT_B');
const ownerName = String.fromEnvironment('OWNER');
const assets = String.fromEnvironment('VIDEO_ASSETS');

/// 앨범 대신 — `pickVideo` 가 부를 때마다 [order]의 표본을 차례로 임시 폴더에 복사해 준다.
class VideoPicker implements MediaPicker {
  VideoPicker(this.order);

  final List<String> order;
  var picked = 0;

  @override
  Future<String?> pickVideo() async {
    final name = order[picked++];
    final copy = File('${Directory.systemTemp.path}/vflow-$picked-$name');
    await File('$assets/$name').copy(copy.path);
    return copy.path;
  }

  @override
  Future<String?> takeVideo({required int maxSeconds}) async => null;

  @override
  Future<List<String>> pickPhotos({required int limit}) async => const [];

  @override
  Future<String?> takePhoto() async => null;
}

/// 앨범 대신 — 저장하라고 받은 파일을 그 자리에서 살펴 적어 둔다(화면은 저장 뒤 임시 파일을 지운다).
class RecordingAlbum implements PhotoAlbum {
  final saved = <({String path, int size, String box})>[];

  @override
  Future<void> save(String path) async {
    final bytes = await File(path).readAsBytes();
    // mp4 는 4번째 바이트부터 'ftyp' 상자로 시작한다.
    final box = bytes.length < 8
        ? ''
        : String.fromCharCodes(bytes.sublist(4, 8));
    saved.add((path: path, size: bytes.length, box: box));
  }
}

/// 대기열의 간격 재시도를 멈춰 둔다(돌지 않는 타이머).
Timer _never(Duration delay, void Function() run) =>
    Timer(const Duration(days: 1), () {});

final picker = VideoPicker([
  'sample-5s-portrait.mp4',
  'sample-65s-small.mp4',
  'sample-5s-portrait.mp4',
  'sample-4s-rot90-silent.mp4',
]);
final album = RecordingAlbum();

Future<List<RecordMedia>> videosOf(int visitId) async {
  final detail = await container.read(visitApiProvider).detail(shopId, visitId);
  final media = detail.record?.media ?? const <RecordMedia>[];
  return [
    for (final m in media)
      if (m.kind == MediaKind.video) m,
  ]..sort((a, b) => a.mediaId.compareTo(b.mediaId));
}

/// 서버의 기록에 영상이 [count]편 붙을 때까지 기다린다.
Future<List<RecordMedia>> waitForVideos(int visitId, int count) async {
  final end = DateTime.now().add(const Duration(seconds: 120));
  while (true) {
    final videos = await videosOf(visitId);
    if (videos.length >= count) return videos;
    if (DateTime.now().isAfter(end)) {
      throw TestFailure('영상이 $count편 붙지 않았다(${videos.length})');
    }
    await pumpFor(const Duration(seconds: 1));
  }
}

String shape(RecordMedia m) =>
    '${m.mediaId}:${m.phase.code} ${m.width}×${m.height} ${m.durationSeconds}초';

/// 영상을 고르고 대기열의 그 영상이 거친 단계·진행률을 모아 둔다.
Future<({bool preparing, List<double> progress})> pickWatching() async {
  var preparing = false;
  final progress = <double>[];
  final sub = container.listen(uploadQueueProvider, (_, next) {
    for (final j in next.value ?? const <UploadJob>[]) {
      if (j.kind == MediaKind.video && j.stage == UploadStage.preparing) {
        preparing = true;
        if (progress.isEmpty || progress.last != j.progress) {
          progress.add(j.progress);
        }
      }
    }
  });
  await t.tap(btn(AppStrings.pickVideo).first);
  await pumpFor(const Duration(milliseconds: 100));
  await shot('${current.padLeft(2, '0')}b-after-pick');
  sub.close();
  return (preparing: preparing, progress: progress);
}

Future<(int, int)> imageSize(List<int> bytes) async {
  final codec = await ui.instantiateImageCodec(Uint8List.fromList(bytes));
  final frame = await codec.getNextFrame();
  return (frame.image.width, frame.image.height);
}

void main() {
  binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('④-3a 완료 기준', timeout: const Timeout(Duration(minutes: 20)), (
    tester,
  ) async {
    t = tester;
    await initializeGlass();
    await t.pumpWidget(
      buildRoot(
        overrides: [
          mediaPickerProvider.overrideWithValue(picker),
          photoAlbumProvider.overrideWithValue(album),
          uploadRetrySchedulerProvider.overrideWithValue(_never),
        ],
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

    await step('1', '5초 영상 — 준비 링이 돌고 올라가면 타일에 재생 배지와 0:05', () async {
      await openVisit(visitA);
      await tap(p(AppStrings.addPhoto));
      await shot('01a-add-sheet');
      final seen = await pickWatching();
      note('압축 단계 봄 ${seen.preparing}, 진행률 ${seen.progress}');
      soft(seen.preparing, '영상이 준비(압축) 단계를 거치지 않았다');
      final videos = await waitForVideos(visitA, 1);
      await pumpFor(const Duration(seconds: 2));
      await shot('01c-attached');
      note('붙은 영상 ${[for (final m in videos) shape(m)]}');
      final v = videos.single;
      soft(v.kind == MediaKind.video, 'kind 가 video 가 아니다');
      soft(v.durationSeconds == 5, '길이가 5 가 아니다(${v.durationSeconds})');
      soft(v.width == 1080 && v.height == 1920, '1080×1920 이 아니다');
      soft(v.displayUrl == null, '영상에 display 가 있다');
      soft(find.text('0:05').evaluate().isNotEmpty, '타일에 0:05 배지가 없다');
    });

    await step('2', '65초 영상 — 앞 60초 안내 스낵바, 서버가 받은 길이 60', () async {
      await openVisit(visitA);
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.pickVideo));
      await waitFor(
        find.text(AppStrings.videoTrimmed),
        timeout: const Duration(seconds: 60),
      );
      await shot('02a-trimmed');
      final videos = await waitForVideos(visitA, 2);
      await pumpFor(const Duration(seconds: 2));
      await shot('02b-attached');
      note('붙은 영상 ${[for (final m in videos) shape(m)]}');
      final v = videos.last;
      soft(v.durationSeconds == 60, '서버가 받은 길이가 60 이 아니다(${v.durationSeconds})');
      soft(v.width == 480 && v.height == 270, '480×270 을 키웠다(${v.width}×${v.height})');
      soft(find.text('1:00').evaluate().isNotEmpty, '타일에 1:00 배지가 없다');
    });

    await step('3', '크게 보기 재생 — 재생 버튼 → 위치가 0 보다 커짐 → [원본 저장] → 앨범', () async {
      final first = (await videosOf(visitA)).first;
      router.push('/visits/$visitA/photos/${first.mediaId}');
      await waitFor(find.byKey(ScreenKeys.photoViewer));
      await pumpFor(const Duration(seconds: 2));
      await shot('03a-viewer-poster');
      await tap(p(AppStrings.playVideo));
      // 넘기기가 옆 영상 페이지도 만들어 두므로, 연(초기화된) 플레이어를 본다.
      Iterable<AppVideoPlayer> opened() => t
          .widgetList<AppVideoPlayer>(find.byType(AppVideoPlayer))
          .where((w) => w.playback.state.initialized);
      final until = DateTime.now().add(const Duration(seconds: 30));
      while (!opened().any((w) => w.playback.state.position > Duration.zero)) {
        if (DateTime.now().isAfter(until)) {
          note('재생 상태 ${[for (final w in opened()) w.playback.state.error ?? '오류 없음']}');
          throw TestFailure('재생 위치가 0 에서 움직이지 않았다');
        }
        await pumpFor(const Duration(milliseconds: 200));
      }
      await pumpFor(const Duration(milliseconds: 800));
      note('연 플레이어 ${opened().length}개');
      final s = opened().single.playback.state;
      note('재생 위치 ${s.position.inMilliseconds}ms / ${s.duration.inMilliseconds}ms, 재생 중 ${s.playing}');
      await shot('03b-playing');
      soft(s.duration.inSeconds == 5, '재생 길이가 5초가 아니다');

      await tap(p(AppStrings.saveOriginal));
      await waitFor(
        find.text(AppStrings.savedToAlbum),
        timeout: const Duration(seconds: 30),
      );
      await shot('03c-saved');
      note('앨범에 넣은 파일 ${[for (final f in album.saved) '${f.path.split('/').last} ${f.size}B ${f.box}']}');
      soft(album.saved.length == 1, '앨범 저장이 한 번이 아니다');
      final saved = album.saved.last;
      soft(saved.path.endsWith('.mp4'), '저장한 파일이 mp4 가 아니다');
      soft(saved.size > 0 && saved.box == 'ftyp', '저장한 파일이 비었거나 mp4 상자가 아니다');
      soft(!File(saved.path).existsSync(), '받은 임시 파일이 남았다');
      // 알림 띠가 사라질 때까지.
      await pumpFor(const Duration(seconds: 4));
    });

    await step('4', '세 편이 붙으면 영상 항목이 비활성이고 누르면 한도 문구', () async {
      await openVisit(visitA);
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.pickVideo));
      final videos = await waitForVideos(visitA, 3);
      note('붙은 영상 ${[for (final m in videos) shape(m)]}');
      await pumpFor(const Duration(seconds: 2));
      await shot('04a-three');
      await tap(p(AppStrings.addPhoto));
      await pumpFor(const Duration(milliseconds: 500));
      await shot('04b-sheet-videos-full');
      bool disabled(String label) => t
          .widgetList<AppButton>(btn(label))
          .every((b) => b.onPressed == null);
      soft(disabled(AppStrings.pickVideo), '[앨범에서 영상]이 비활성이 아니다');
      soft(disabled(AppStrings.takeVideo), '[영상 찍기]가 비활성이 아니다');
      soft(!disabled(AppStrings.pickFromAlbum), '[앨범에서 사진]까지 비활성이다');
      final pickedBefore = picker.picked;
      await tap(p(AppStrings.pickVideo));
      final limit = messageFor(
        ApiException(statusCode: 422, code: 'MEDIA_LIMIT_EXCEEDED', message: ''),
      );
      await waitFor(find.text(limit));
      await shot('04c-limit');
      soft(picker.picked == pickedBefore, '한도인데 영상 선택기가 열렸다');
      soft((await videosOf(visitA)).length == 3, '서버의 영상이 셋이 아니다');
      await pumpFor(const Duration(seconds: 4));
    });

    await step('5', '회전 메타 영상은 세로로 붙는다(서버가 받은 width 1080·height 1920)', () async {
      await openVisit(visitB);
      await tap(p(AppStrings.addPhoto));
      await tap(btn(AppStrings.pickVideo));
      final videos = await waitForVideos(visitB, 1);
      await pumpFor(const Duration(seconds: 2));
      await shot('05a-rotated');
      final v = videos.single;
      note('붙은 영상 ${shape(v)}');
      soft(v.width == 1080 && v.height == 1920, '세로 1080×1920 이 아니다(${v.width}×${v.height})');
      soft(v.durationSeconds == 4, '길이가 4 가 아니다');
      final (w, h) = await imageSize(await download(v.thumbUrl));
      note('포스터 $w×$h');
      soft(h > w, '포스터가 세로가 아니다');
      soft(find.text('0:04').evaluate().isNotEmpty, '타일에 0:04 배지가 없다');
    });

    debugPrint('===== 결과 =====');
    for (final r in results) {
      debugPrint(r);
    }
    expect(results.where((r) => r.startsWith('FAIL')), isEmpty);
  });
}
