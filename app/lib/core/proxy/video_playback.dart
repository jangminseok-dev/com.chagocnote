import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../../design/widgets/video_playback.dart';
import '../error/api_exception.dart';

/// [VideoPlayback] 의 video_player 구현 — 화면·모양 위젯이 `video_player` 를 직접 import 하지 않게
/// 감싼 자리(④-3a 설계 5.1).
class VideoPlayerPlayback extends ChangeNotifier implements VideoPlayback {
  VideoPlayerController? _controller;
  Object? _error;

  /// 여는 도중 페이지가 사라질 수 있다(넘겨 버림) — 그 뒤에는 알리지 않는다.
  bool _disposed = false;

  @override
  PlaybackState get state {
    final controller = _controller;
    if (_error != null || controller == null) {
      return PlaybackState(error: _error);
    }
    final v = controller.value;
    // 초기화가 끝난 뒤에도 오류가 올 수 있다(스트리밍 중 연결 끊김, 서명 URL 만료) — video_player 는 이때
    // 예외를 던지지 않고 값의 errorDescription 에 둔다(pub-cache video_player.dart:686-688).
    if (v.hasError) {
      return PlaybackState(
        error: playbackErrorOf(
          PlatformException(code: 'VideoError', message: v.errorDescription),
        ),
      );
    }
    return PlaybackState(
      initialized: v.isInitialized,
      playing: v.isPlaying,
      buffering: v.isBuffering,
      position: v.position,
      duration: v.duration,
    );
  }

  @override
  Widget buildSurface() {
    final controller = _controller;
    if (controller == null || !controller.value.isInitialized) {
      return const SizedBox.shrink();
    }
    return AspectRatio(
      aspectRatio: controller.value.aspectRatio,
      child: VideoPlayer(controller),
    );
  }

  @override
  Future<void> open(String url) async {
    final old = _controller;
    _error = null;
    if (old != null) {
      old.removeListener(notifyListeners);
      await old.dispose();
      if (_disposed) return;
    }
    final controller = _controller = VideoPlayerController.networkUrl(
      Uri.parse(url),
    )..addListener(notifyListeners);
    notifyListeners();
    try {
      await controller.initialize();
      if (_disposed) return;
      await controller.setVolume(1); // 소리는 켠다. 반복은 없다(기본값).
    } on PlatformException catch (e) {
      if (_disposed) return;
      _error = playbackErrorOf(e);
      notifyListeners();
    }
  }

  @override
  Future<void> play() async => _controller?.play();

  @override
  Future<void> pause() async => _controller?.pause();

  @override
  Future<void> seekTo(Duration position) async =>
      _controller?.seekTo(position);

  @override
  Future<void> dispose() async {
    if (_disposed) return; // 두 번 부를 수 있다(페이지 dispose 와 겹치는 정리) — 한 번만 실제로 정리한다.
    _disposed = true;
    final controller = _controller;
    _controller = null;
    controller?.removeListener(notifyListeners);
    super.dispose();
    await controller?.dispose();
  }
}

/// 플랫폼 오류를 화면이 고를 원인으로. 플랫폼은 HTTP 상태·연결 실패를 오류 메시지 글로만 알린다
/// (iOS 는 CoreMedia -12660 이 403, NSURLError -1009 가 오프라인) — 글에서 찾고, 모르면 원본 그대로.
Object playbackErrorOf(PlatformException error) {
  final text = '${error.message} ${error.details}';
  if (text.contains('403') || text.contains('-12660')) {
    return ApiException(
      statusCode: 403,
      code: 'MEDIA_URL_EXPIRED',
      message: error.message ?? '',
    );
  }
  const offline = [
    'SocketException',
    'UnknownHost',
    'NETWORK_CONNECTION_FAILED',
    '-1009',
    'ENETDOWN',
    'offline',
  ];
  if (offline.any(text.contains)) {
    return ApiException.network(error.message ?? '');
  }
  return error;
}

class _VideoPlayerFactory implements VideoPlaybackFactory {
  const _VideoPlayerFactory();

  @override
  VideoPlayback create() => VideoPlayerPlayback();
}

final videoPlaybackFactoryProvider = Provider<VideoPlaybackFactory>(
  (ref) => const _VideoPlayerFactory(),
);
