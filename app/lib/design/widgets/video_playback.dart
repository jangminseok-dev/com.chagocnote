import 'package:flutter/widgets.dart';

/// 재생 하나의 상태 — 모양 위젯이 그리는 데 필요한 것만.
class PlaybackState {
  const PlaybackState({
    this.initialized = false,
    this.playing = false,
    this.buffering = false,
    this.position = Duration.zero,
    this.duration = Duration.zero,
    this.error,
  });

  final bool initialized;
  final bool playing;
  final bool buffering;
  final Duration position;
  final Duration duration;

  /// 열기 실패의 원인. 서명 URL 만료(403)는 `MEDIA_URL_EXPIRED`, 연결 실패는 `NETWORK` 인
  /// `ApiException` 으로 바꿔 둔다 — 화면이 `loadMessageFor` 로 문구를 고른다.
  final Object? error;
}

/// 재생 컨트롤 — 화면이 페이지마다 만들고 dispose 한다. 구현(`video_player`)은
/// `core/proxy/video_playback.dart` 에 있다 — 모양 위젯은 이 추상만 안다(core 를 import 하지 않는다).
abstract class VideoPlayback extends Listenable {
  PlaybackState get state;

  /// 영상 면(가로세로비 포함). 열리기 전에는 빈 자리.
  Widget buildSurface();

  /// 서명 URL 원본을 스트리밍으로 연다(기기에 캐시하지 않는다). 실패는 던지지 않고 [PlaybackState.error] 에
  /// 둔다. 이미 연 것이 있으면 닫고 새로 연다(다시 시도의 새 URL).
  Future<void> open(String url);
  Future<void> play();
  Future<void> pause();
  Future<void> seekTo(Duration position);
  Future<void> dispose();
}

abstract class VideoPlaybackFactory {
  VideoPlayback create();
}
