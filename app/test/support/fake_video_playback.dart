import 'package:chagocnote/design/widgets/video_playback.dart';
import 'package:flutter/widgets.dart';

/// 재생 대역 — 플랫폼 없이 상태만 바꾸고, 부른 것을 [calls]에 적는다.
/// [failWith]가 있으면 open 이 그 오류를 상태에 둔다(던지지 않는다 — 진짜와 같다).
class FakeVideoPlayback extends ChangeNotifier implements VideoPlayback {
  FakeVideoPlayback({this.failWith});

  Object? failWith;
  Duration length = const Duration(seconds: 31);

  /// `open URL`·`play`·`pause`·`seek 밀리초`·`dispose` 를 부른 순서대로.
  final calls = <String>[];

  @override
  PlaybackState state = const PlaybackState();

  void _set(PlaybackState next) {
    state = next;
    notifyListeners();
  }

  /// 재생이 끝까지 갔다(진짜 컨트롤러처럼 멈추고 끝에 선다).
  void finish() => _set(
    PlaybackState(initialized: true, position: length, duration: length),
  );

  @override
  Widget buildSurface() => const SizedBox(key: Key('video-surface'));

  @override
  Future<void> open(String url) async {
    calls.add('open $url');
    final error = failWith;
    _set(
      error != null
          ? PlaybackState(error: error)
          : PlaybackState(initialized: true, duration: length),
    );
  }

  @override
  Future<void> play() async {
    calls.add('play');
    final from = state.position >= length ? Duration.zero : state.position;
    _set(
      PlaybackState(
        initialized: true,
        playing: true,
        position: from,
        duration: length,
      ),
    );
  }

  @override
  Future<void> pause() async {
    calls.add('pause');
    _set(
      PlaybackState(
        initialized: state.initialized,
        position: state.position,
        duration: state.duration,
      ),
    );
  }

  @override
  Future<void> seekTo(Duration position) async {
    calls.add('seek ${position.inMilliseconds}');
    _set(
      PlaybackState(
        initialized: state.initialized,
        playing: state.playing,
        position: position,
        duration: state.duration,
      ),
    );
  }

  @override
  Future<void> dispose() async {
    calls.add('dispose');
    super.dispose();
  }
}

/// 재생 만들기 대역 — 만든 재생을 [created]에 모은다. [failWith]를 새 재생에 넘긴다.
class FakeVideoPlaybackFactory implements VideoPlaybackFactory {
  Object? failWith;
  final created = <FakeVideoPlayback>[];

  @override
  VideoPlayback create() {
    final playback = FakeVideoPlayback(failWith: failWith);
    created.add(playback);
    return playback;
  }
}
