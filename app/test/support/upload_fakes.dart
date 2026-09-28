import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:chagocnote/core/proxy/media_files.dart';
import 'package:chagocnote/core/proxy/media_images.dart';
import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/core/proxy/photo_album.dart';
import 'package:chagocnote/core/proxy/photo_renditions.dart';
import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:chagocnote/core/proxy/video_transcoder.dart';
import 'package:chagocnote/features/visit/api/record_models.dart';
import 'package:chagocnote/features/visit/state/upload_job.dart';
import 'package:chagocnote/features/visit/state/upload_queue.dart';
import 'package:flutter/widgets.dart';

/// 렌디션 대역 — 크기가 정해진 파일 셋을 쓴다. [broken]에 든 원본은 읽을 수 없는 사진이다.
class FakeRenditionMaker implements PhotoRenditionMaker {
  final broken = <String>{};

  /// 원본·표시용·썸네일 바이트 수.
  static const sizes = (original: 300, display: 100, thumb: 20);

  @override
  Future<PhotoRenditions> make(String source, Directory outDir) async {
    if (broken.contains(source)) throw StateError('읽을 수 없는 사진');
    await outDir.create(recursive: true);
    Future<String> write(String name, int length) async {
      final path = '${outDir.path}/$name.jpg';
      await File(path).writeAsBytes(List<int>.filled(length, 7));
      return path;
    }

    return PhotoRenditions(
      original: await write('original', sizes.original),
      display: await write('display', sizes.display),
      thumb: await write('thumb', sizes.thumb),
      width: 3000,
      height: 2000,
    );
  }
}

/// 인터넷 복귀 신호 대역 — [restore]로 신호를 보낸다.
class FakeNetworkWatcher implements NetworkWatcher {
  final _controller = StreamController<void>.broadcast();

  @override
  Stream<void> get restored => _controller.stream;

  void restore() => _controller.add(null);
}

/// 다시 시도 예약 대역 — 기다리지 않고 요청된 간격만 적어 두고, [fire]로 예약된 것을 돌린다.
class FakeRetryScheduler {
  final delays = <Duration>[];
  final _timers = <_FakeTimer>[];

  Timer call(Duration delay, void Function() run) {
    delays.add(delay);
    final timer = _FakeTimer(run);
    _timers.add(timer);
    return timer;
  }

  /// 아직 취소되지 않은 예약을 모두 돌린다.
  void fire() {
    final due = [
      for (final t in _timers)
        if (t.isActive) t,
    ];
    _timers.clear();
    for (final t in due) {
      t.run();
    }
  }
}

class _FakeTimer implements Timer {
  _FakeTimer(this._run);

  final void Function() _run;
  bool _active = true;

  void run() {
    if (!_active) return;
    _active = false;
    _run();
  }

  @override
  void cancel() => _active = false;

  @override
  bool get isActive => _active;

  @override
  int get tick => 0;
}

/// 사진·영상 고르기 대역 — 고를 경로와 찍을 경로를 미리 정해 둔다.
class FakeMediaPicker implements MediaPicker {
  FakeMediaPicker({
    this.picked = const [],
    this.taken,
    this.pickedVideo,
    this.takenVideo,
  });

  List<String> picked;
  String? taken;
  String? pickedVideo;
  String? takenVideo;
  final limits = <int>[];

  /// [takeVideo]에 넘어온 최대 길이(초).
  final videoMaxSeconds = <int>[];

  @override
  Future<List<String>> pickPhotos({required int limit}) async {
    limits.add(limit);
    return picked;
  }

  @override
  Future<String?> takePhoto() async => taken;

  @override
  Future<String?> pickVideo() async => pickedVideo;

  @override
  Future<String?> takeVideo({required int maxSeconds}) async {
    videoMaxSeconds.add(maxSeconds);
    return takenVideo;
  }
}

/// 영상 압축 대역 — 원본을 `video.mp4` 로 복사하고 작은 `thumb.jpg` 를 쓰며, 정해 둔
/// 크기·길이·[trimmed]를 돌려준다. [progressSteps]를 진행률로 순서대로 흘린다.
class FakeVideoTranscoder implements VideoTranscoder {
  int width = 1080;
  int height = 1920;
  int durationSeconds = 5;
  bool trimmed = false;

  /// 있으면 transcode 가 이 코드(`UNSUPPORTED` 등)로 던진다.
  String? failWith;
  List<double> progressSteps = const [0.5, 1];

  /// 있으면 완료될 때까지 기다린다(압축 중 상태를 보는 테스트).
  Completer<void>? gate;

  final calls = <(String source, int maxSeconds)>[];
  var cancelled = 0;

  @override
  Future<VideoTranscodeResult> transcode(
    String source,
    Directory outDir, {
    int maxSeconds = 60,
    void Function(double progress)? onProgress,
  }) async {
    calls.add((source, maxSeconds));
    await gate?.future;
    if (failWith case final code?) throw VideoTranscodeException(code);
    for (final p in progressSteps) {
      onProgress?.call(p);
    }
    await outDir.create(recursive: true);
    final video = await File(source).copy('${outDir.path}/video.mp4');
    final thumb = '${outDir.path}/thumb.jpg';
    await File(thumb).writeAsBytes(
      List<int>.filled(FakeRenditionMaker.sizes.thumb, 7),
    );
    return VideoTranscodeResult(
      video: video.path,
      thumb: thumb,
      width: width,
      height: height,
      durationSeconds: durationSeconds,
      trimmed: trimmed,
    );
  }

  @override
  Future<void> cancel() async {
    cancelled++;
    final waiting = gate;
    if (waiting != null && !waiting.isCompleted) {
      waiting.completeError(const VideoTranscodeException('CANCELLED'));
    }
  }
}

/// 대기열 대역 — 정해 둔 항목을 보이고, 넣기·빼기를 적어 둔다(파일·네트워크 없음).
class FakeUploadQueue extends UploadQueue {
  FakeUploadQueue([this.initial = const []]);

  final List<UploadJob> initial;
  final added = <({int visitId, MediaPhase phase, List<String> sources})>[];
  final removed = <String>[];
  final retried = <String>[];
  final addedVideos = <({int visitId, MediaPhase phase, String source})>[];

  /// [addVideo]가 돌려줄 결과.
  VideoAddOutcome videoOutcome = VideoAddOutcome.added;

  @override
  Future<List<UploadJob>> build() async => initial;

  @override
  Future<void> retry(String id) async => retried.add(id);

  @override
  Future<void> addPhotos({
    required int shopId,
    required int visitId,
    required MediaPhase phase,
    required List<String> sources,
  }) async => added.add((visitId: visitId, phase: phase, sources: sources));

  @override
  Future<VideoAddOutcome> addVideo({
    required int shopId,
    required int visitId,
    required MediaPhase phase,
    required String source,
  }) async {
    addedVideos.add((visitId: visitId, phase: phase, source: source));
    return videoOutcome;
  }

  @override
  Future<void> remove(String id) async => removed.add(id);
}

/// 1×1 회색 PNG.
final _grayPixel = Uint8List.fromList(const [
  0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0x00, 0x00, 0x00, 0x0D, //
  0x49, 0x48, 0x44, 0x52, 0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
  0x08, 0x00, 0x00, 0x00, 0x00, 0x3A, 0x7E, 0x9B, 0x55, 0x00, 0x00, 0x00,
  0x0A, 0x49, 0x44, 0x41, 0x54, 0x78, 0x9C, 0x63, 0x68, 0x00, 0x00, 0x00,
  0x82, 0x00, 0x81, 0x77, 0xCD, 0x72, 0xB6, 0x00, 0x00, 0x00, 0x00, 0x49,
  0x45, 0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82,
]);

/// 사진 로더 대역 — 네트워크 없이 회색 한 점([image])을 보이고, 물어본 URL 을 적어 둔다.
/// 골든은 [image]를 먼저 읽어 두어(precache) 디코딩 시점에 따라 달라지지 않게 한다.
class FakeMediaImages implements MediaImages {
  final urls = <String>[];
  final image = MemoryImage(_grayPixel);

  @override
  ImageProvider of(String url) {
    urls.add(url);
    return image;
  }

  /// 원본으로 보이라고 한 URL — [urls]에도 적는다.
  final originals = <String>[];

  @override
  ImageProvider original(String url) {
    originals.add(url);
    return of(url);
  }

  /// 받아 달라고 한 원본 URL.
  final files = <String>[];

  @override
  Future<String> fileOf(String url) async {
    files.add(url);
    return '/fake/${files.length}.jpg';
  }
}

/// 앨범 대역 — 저장한 파일 경로를 적어 두고, [denied]면 권한 없음으로 던진다.
class FakePhotoAlbum implements PhotoAlbum {
  final saved = <String>[];
  bool denied = false;

  @override
  Future<void> save(String path) async {
    if (denied) throw const PhotoAlbumDenied();
    saved.add(path);
  }
}

/// 큰 파일 받기 대역 — 임시 폴더에 작은 파일을 실제로 써서 그 경로를 준다(화면이 지우는지 본다).
/// [gate]가 있으면 완료될 때까지 붙든다(받는 중에 화면을 나가는 테스트).
class FakeMediaFiles implements MediaFiles {
  final urls = <String>[];
  final paths = <String>[];
  Completer<void>? gate;

  @override
  Future<String> download(String url, {required String suffix}) async {
    urls.add(url);
    await gate?.future;
    final dir = await Directory.systemTemp.createTemp('fake-media-files');
    final file = File('${dir.path}/${urls.length}$suffix');
    await file.writeAsBytes(const [1, 2, 3]);
    paths.add(file.path);
    return file.path;
  }
}

/// 음성 인식 대역 — 가용성·권한을 정해 두고, 호출을 세며, emit* 로 이벤트를 흘린다.
class FakeSpeechRecognizer implements SpeechRecognizer {
  SpeechAvailability availabilityResult = const SpeechAvailability(
    supported: true,
  );
  SpeechPermission permissionResult = SpeechPermission.granted;

  final _events = StreamController<SpeechEvent>.broadcast();

  /// start 에 넘긴 locale 들.
  final starts = <String>[];
  var stops = 0;
  var cancels = 0;
  var settingsOpened = 0;
  var permissionRequests = 0;

  /// start·stop·cancel 을 부른 차례.
  final calls = <String>[];

  /// 정해 두면 cancel 이 이것이 끝날 때까지 기다린다(네이티브 cancel 이 늦는 경우).
  Completer<void>? cancelGate;

  @override
  Future<SpeechAvailability> availability() async => availabilityResult;

  @override
  Future<SpeechPermission> requestPermission() async {
    permissionRequests++;
    return permissionResult;
  }

  @override
  Stream<SpeechEvent> get events => _events.stream;

  @override
  Future<void> start({String locale = 'ko-KR'}) async {
    starts.add(locale);
    calls.add('start');
  }

  @override
  Future<void> stop() async {
    stops++;
    calls.add('stop');
  }

  @override
  Future<void> cancel() async {
    cancels++;
    calls.add('cancel');
    await cancelGate?.future;
  }

  @override
  Future<void> openSettings() async => settingsOpened++;

  void emitPartial(String text) => _events.add(SpeechPartial(text));

  void emitFinal(String text) => _events.add(SpeechFinal(text));

  void emitEnded() => _events.add(const SpeechEnded());

  void emitError(SpeechErrorCode code) => _events.add(SpeechError(code));
}
