// 재생 자리(④-3a 설계 5.4) — video_player 의 플랫폼 인터페이스를 대역으로 바꿔, 초기화 이벤트와
// 초기화 실패가 모양 위젯이 그릴 상태(PlaybackState)로 옮겨지는지 본다.
import 'dart:async';

import 'package:chagocnote/core/error/api_exception.dart';
import 'package:chagocnote/core/proxy/video_playback.dart';
import 'package:flutter/services.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:video_player_platform_interface/video_player_platform_interface.dart';

/// 플랫폼 대역 — 만든 플레이어마다 [initialized] 이벤트를 흘리거나 [failure]로 실패한다.
/// `PlatformInterface.verify` 가 토큰을 보므로 `implements` 가 아니라 `extends` 다.
class _FakePlatform extends VideoPlayerPlatform {
  PlatformException? failure;
  final created = <String?>[];
  final volumes = <double>[];
  final _events = <int, StreamController<VideoEvent>>{};

  @override
  Future<void> init() async {}

  @override
  Future<int?> createWithOptions(VideoCreationOptions options) async {
    created.add(options.dataSource.uri);
    return created.length;
  }

  @override
  Stream<VideoEvent> videoEventsFor(int playerId) {
    final events = _events[playerId] = StreamController<VideoEvent>();
    final error = failure;
    if (error != null) {
      events.addError(error);
    } else {
      events.add(
        VideoEvent(
          eventType: VideoEventType.initialized,
          duration: const Duration(seconds: 31),
          size: const Size(1080, 1920),
        ),
      );
    }
    return events.stream;
  }

  @override
  Future<void> dispose(int playerId) async => _events.remove(playerId)?.close();

  @override
  Future<void> setLooping(int playerId, bool looping) async {}

  @override
  Future<void> play(int playerId) async {}

  @override
  Future<void> pause(int playerId) async {}

  @override
  Future<void> setVolume(int playerId, double volume) async =>
      volumes.add(volume);

  @override
  Future<void> seekTo(int playerId, Duration position) async {}

  @override
  Future<Duration> getPosition(int playerId) async => Duration.zero;

  @override
  Widget buildViewWithOptions(VideoViewOptions options) =>
      const SizedBox.shrink();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  late _FakePlatform platform;
  late VideoPlayerPlayback playback;

  setUp(() {
    platform = _FakePlatform();
    VideoPlayerPlatform.instance = platform;
    playback = VideoPlayerPlayback();
  });
  tearDown(() => playback.dispose());

  test('open 이 초기화 이벤트를 받으면 initialized 와 길이가 상태에 실린다', () async {
    var notified = 0;
    playback.addListener(() => notified++);

    await playback.open('http://media.test/b/original/shops/3/71.mp4?sig=a');

    expect(platform.created, [
      'http://media.test/b/original/shops/3/71.mp4?sig=a',
    ]);
    expect(playback.state.initialized, isTrue);
    expect(playback.state.duration, const Duration(seconds: 31));
    expect(playback.state.playing, isFalse);
    expect(playback.state.error, isNull);
    expect(platform.volumes.last, 1.0, reason: '소리는 켠다');
    expect(notified, greaterThan(0));
  });

  test('초기화가 403 으로 실패하면 만료 오류로, 연결 실패면 인터넷 없음으로 바꿔 상태에 둔다', () async {
    platform.failure = PlatformException(
      code: 'VideoError',
      message: 'Failed to load video: HTTP 403 Forbidden',
    );
    await playback.open('http://media.test/v.mp4?sig=old');

    final expired = playback.state.error;
    expect(expired, isA<ApiException>());
    expect((expired! as ApiException).code, 'MEDIA_URL_EXPIRED');
    expect((expired as ApiException).statusCode, 403);
    expect(playback.state.initialized, isFalse);

    // 같은 자리에서 다시 열면(다시 시도) 앞 오류는 지워지고 새 원인이 실린다.
    platform.failure = PlatformException(
      code: 'VideoError',
      message:
          'Video player had error androidx.media3.exoplayer.ExoPlaybackException: '
          'Source error java.net.SocketException: Network is unreachable',
    );
    await playback.open('http://media.test/v.mp4?sig=new');

    final offline = playback.state.error;
    expect(offline, isA<ApiException>());
    expect((offline! as ApiException).isNetwork, isTrue);

    // 알 수 없는 실패는 원본 그대로.
    platform.failure = PlatformException(
      code: 'VideoError',
      message: 'Failed to load video: Cannot Open',
    );
    await playback.open('http://media.test/v.mp4?sig=new');
    expect(playback.state.error, isA<PlatformException>());
  });
}
