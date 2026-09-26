import 'dart:async';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 영상 압축·포스터(④-3a 설계 3절) — 화면·대기열이 네이티브 채널을 직접 부르지 않게 감싼 자리.
///
/// 압축은 외부 패키지 없이 네이티브가 한다.
/// - iOS `ios/Runner/VideoTranscoder.swift`: `AVAssetExportSession`(1920×1080 프리셋, mp4,
///   앞 maxSeconds, moov 를 앞으로)과 `AVAssetImageGenerator`(1초 지점 프레임 → JPEG, 긴 변 300px).
///   진행률은 `exportSession.progress` 를 0.2초마다, 취소는 `cancelExport()`. `AppDelegate` 가
///   채널을 등록한다(공유 받기 채널과 같은 자리).
/// - 안드로이드 `android/app/src/main/kotlin/.../VideoTranscoder.kt`: Media3 `Transformer`
///   (H.264·AAC, `ClippingConfiguration` 0…maxSeconds, 긴 변 1080)와 `MediaMetadataRetriever`
///   (1초 프레임·회전을 반영한 가로·세로·길이). 진행률은 `Transformer.getProgress` 를 200ms 마다,
///   취소는 `Transformer.cancel()`.
///
/// 채널 규약:
/// - 메서드 채널 [ChannelVideoTranscoder.channelName]
///   - `transcode({source, outDir, maxSeconds})` → `{video, thumb, width, height,
///     durationSeconds, trimmed}`. 네이티브가 `outDir/video.mp4`·`outDir/thumb.jpg` 를 쓴다.
///   - `cancel()` — 진행 중인 압축을 멈춘다. 멈춘 `transcode` 는 `CANCELLED` 로 끝난다.
///   - 실패는 `PlatformException` 코드 `UNSUPPORTED`(코덱·손상)·`TOO_SHORT`(압축 뒤 길이 0)·
///     `CANCELLED`.
/// - 이벤트 채널 [ChannelVideoTranscoder.progressChannelName] — 0…1 의 진행률(double).
class VideoTranscodeResult {
  const VideoTranscodeResult({
    required this.video,
    required this.thumb,
    required this.width,
    required this.height,
    required this.durationSeconds,
    required this.trimmed,
  });

  /// `outDir/video.mp4` — 1080p H.264·AAC, 앞 maxSeconds.
  final String video;

  /// `outDir/thumb.jpg` — 1초 지점 프레임, 긴 변 300px.
  final String thumb;

  /// 압축본 기준(회전 반영).
  final int width;
  final int height;
  final int durationSeconds;

  /// 원본이 maxSeconds 를 넘어 잘랐는지.
  final bool trimmed;
}

/// 압축 실패. [code]는 `UNSUPPORTED`·`TOO_SHORT`·`CANCELLED` 중 하나다.
class VideoTranscodeException implements Exception {
  const VideoTranscodeException(this.code);

  final String code;

  @override
  String toString() => 'VideoTranscodeException($code)';
}

abstract class VideoTranscoder {
  /// [source]를 앞 [maxSeconds]까지 압축해 [outDir]에 `video.mp4`·`thumb.jpg` 를 쓴다.
  Future<VideoTranscodeResult> transcode(
    String source,
    Directory outDir, {
    int maxSeconds = 60,
    void Function(double progress)? onProgress,
  });

  /// 진행 중인 압축을 멈춘다.
  Future<void> cancel();
}

class ChannelVideoTranscoder implements VideoTranscoder {
  ChannelVideoTranscoder({MethodChannel? channel, EventChannel? progress})
    : _channel = channel ?? const MethodChannel(channelName),
      _progress = progress ?? const EventChannel(progressChannelName);

  static const channelName = 'chagocnote/video_transcoder';
  static const progressChannelName = 'chagocnote/video_transcoder/progress';

  static const _codes = {'UNSUPPORTED', 'TOO_SHORT', 'CANCELLED'};

  final MethodChannel _channel;
  final EventChannel _progress;

  @override
  Future<VideoTranscodeResult> transcode(
    String source,
    Directory outDir, {
    int maxSeconds = 60,
    void Function(double progress)? onProgress,
  }) async {
    final subscription = onProgress == null
        ? null
        : _progress.receiveBroadcastStream().listen(
            (value) => onProgress((value as num).toDouble()),
          );
    try {
      final result = await _channel.invokeMapMethod<String, Object?>(
        'transcode',
        {'source': source, 'outDir': outDir.path, 'maxSeconds': maxSeconds},
      );
      return VideoTranscodeResult(
        video: result!['video']! as String,
        thumb: result['thumb']! as String,
        width: result['width']! as int,
        height: result['height']! as int,
        durationSeconds: result['durationSeconds']! as int,
        trimmed: result['trimmed']! as bool,
      );
    } on PlatformException catch (e) {
      throw VideoTranscodeException(
        _codes.contains(e.code) ? e.code : 'UNSUPPORTED',
      );
    } on MissingPluginException {
      // 이 플랫폼에는 압축이 없다(테스트·웹).
      throw const VideoTranscodeException('UNSUPPORTED');
    } finally {
      await subscription?.cancel();
    }
  }

  @override
  Future<void> cancel() async {
    try {
      await _channel.invokeMethod<void>('cancel');
    } on MissingPluginException {
      // 이 플랫폼에는 압축이 없다 — 멈출 것도 없다.
    }
  }
}

final videoTranscoderProvider = Provider<VideoTranscoder>(
  (ref) => ChannelVideoTranscoder(),
);
