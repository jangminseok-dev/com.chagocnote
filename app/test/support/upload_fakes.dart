import 'dart:async';
import 'dart:io';

import 'package:chagocnote/core/proxy/media_picker.dart';
import 'package:chagocnote/core/proxy/network_watcher.dart';
import 'package:chagocnote/core/proxy/photo_renditions.dart';

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

/// 사진 고르기 대역 — 고를 경로와 찍을 경로를 미리 정해 둔다.
class FakeMediaPicker implements MediaPicker {
  FakeMediaPicker({this.picked = const [], this.taken});

  List<String> picked;
  String? taken;
  final limits = <int>[];

  @override
  Future<List<String>> pickPhotos({required int limit}) async {
    limits.add(limit);
    return picked;
  }

  @override
  Future<String?> takePhoto() async => taken;
}
