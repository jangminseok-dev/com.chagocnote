import 'dart:async';

import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 음성 인식(④-3b 설계 3.1) — 받아쓰기 세션·화면이 네이티브 채널을 직접 부르지 않게 감싼 자리.
///
/// 인식은 외부 패키지 없이 네이티브가 기기 안에서만 한다(서버 인식 없음).
/// - iOS `ios/Runner/SpeechRecognizer.swift`: `SFSpeechRecognizer`(ko-KR,
///   `requiresOnDeviceRecognition`)와 `AVAudioEngine` 입력 탭. `AppDelegate` 가 채널을 등록한다.
/// - 안드로이드 `android/app/src/main/kotlin/com/chagocnote/chagocnote/SpeechRecognizer.kt`:
///   API 31+ `createOnDeviceSpeechRecognizer` 와 `RecognitionListener`. 30 이하는 기기 미지원.
///
/// 채널 규약:
/// - 메서드 채널 [ChannelSpeechRecognizer.channelName]
///   - `availability()` → `{supported: bool, reason: 'device'|'locale'|null}`.
///   - `requestPermission()` → `'granted'|'denied'` — 마이크와 음성 인식이 둘 다 허용일 때만 granted.
///   - `start({locale})` — 듣기 시작. 결과는 이벤트 채널로 온다.
///   - `stop()` — 마지막 결과를 `final` 로 확정하고 `ended`. `cancel()` — 결과 없이 끝.
///   - `openSettings()` — 이 앱의 설정 화면을 연다.
///   - 실패는 `PlatformException` 코드 `denied`·`unsupported`·`noSpeech`·`failed`.
/// - 이벤트 채널 [ChannelSpeechRecognizer.eventsChannelName] — `{type: 'partial'|'final'|'ended'|
///   'error', text?, code?}`. `code` 는 위 넷 중 하나이고, 모르는 코드는 `failed` 로 읽는다.
enum SpeechUnsupported { device, locale }

class SpeechAvailability {
  const SpeechAvailability({required this.supported, this.reason});

  final bool supported;

  /// [supported]가 거짓일 때 까닭 — 기기(온디바이스 인식 없음)인지 언어(ko-KR 없음)인지.
  final SpeechUnsupported? reason;
}

enum SpeechPermission { granted, denied }

sealed class SpeechEvent {
  const SpeechEvent();
}

/// 아직 굳지 않은 중간 결과 — 이번 구간 전체 글이다.
class SpeechPartial extends SpeechEvent {
  const SpeechPartial(this.text);

  final String text;
}

/// 굳은 결과 — 이번 구간의 마지막 글이다.
class SpeechFinal extends SpeechEvent {
  const SpeechFinal(this.text);

  final String text;
}

/// 네이티브가 듣기를 끝냈다(요청했든 제 기준이든).
class SpeechEnded extends SpeechEvent {
  const SpeechEnded();
}

class SpeechError extends SpeechEvent {
  const SpeechError(this.code);

  final SpeechErrorCode code;
}

enum SpeechErrorCode { denied, unsupported, noSpeech, failed }

abstract class SpeechRecognizer {
  Future<SpeechAvailability> availability();

  /// 마이크와 음성 인식 둘 다 허용이어야 [SpeechPermission.granted].
  Future<SpeechPermission> requestPermission();

  /// 인식 결과·끝·오류. 브로드캐스트라 여럿이 들어도 된다.
  Stream<SpeechEvent> get events;

  Future<void> start({String locale = 'ko-KR'});

  /// 마지막 결과를 확정하고 끝낸다.
  Future<void> stop();

  /// 결과 없이 끝낸다.
  Future<void> cancel();

  Future<void> openSettings();
}

class ChannelSpeechRecognizer implements SpeechRecognizer {
  ChannelSpeechRecognizer({MethodChannel? channel, EventChannel? events})
    : _channel = channel ?? const MethodChannel(channelName),
      _eventChannel = events ?? const EventChannel(eventsChannelName);

  static const channelName = 'chagocnote/speech';
  static const eventsChannelName = 'chagocnote/speech/events';

  final MethodChannel _channel;
  final EventChannel _eventChannel;

  /// 네이티브가 없을 때처럼 Dart 쪽에서 내는 이벤트.
  final _local = StreamController<SpeechEvent>.broadcast();

  // 이벤트 채널은 한 번만 구독하고 나눠 준다. 받아쓰기 세션마다 구독을 풀고 다시 걸면
  // 네이티브가 listen·cancel 을 거듭 받아 그 사이 이벤트를 놓치므로, 늦게 구독한 쪽도
  // 같은 흐름을 받게 한다(인터넷 복귀 신호의 공유와 같은 까닭).
  late final Stream<SpeechEvent> _native = _eventChannel
      .receiveBroadcastStream()
      .map(_toEvent)
      .asBroadcastStream();

  @override
  late final Stream<SpeechEvent> events = Stream<SpeechEvent>.multi((out) {
    final native = _native.listen(out.addSync, onError: out.addErrorSync);
    final local = _local.stream.listen(out.addSync);
    out.onCancel = () async {
      await native.cancel();
      await local.cancel();
    };
  }, isBroadcast: true);

  @override
  Future<SpeechAvailability> availability() async {
    try {
      final result = await _channel.invokeMapMethod<String, Object?>(
        'availability',
      );
      return SpeechAvailability(
        supported: result!['supported']! as bool,
        reason: switch (result['reason']) {
          'device' => SpeechUnsupported.device,
          'locale' => SpeechUnsupported.locale,
          _ => null,
        },
      );
    } on MissingPluginException {
      // 이 플랫폼에는 인식이 없다(테스트·웹).
      return const SpeechAvailability(
        supported: false,
        reason: SpeechUnsupported.device,
      );
    }
  }

  @override
  Future<SpeechPermission> requestPermission() async {
    final result = await _channel.invokeMethod<String>('requestPermission');
    return result == 'granted'
        ? SpeechPermission.granted
        : SpeechPermission.denied;
  }

  @override
  Future<void> start({String locale = 'ko-KR'}) async {
    try {
      await _channel.invokeMethod<void>('start', {'locale': locale});
    } on PlatformException catch (e) {
      _local.add(SpeechError(_code(e.code)));
    } on MissingPluginException {
      _local.add(const SpeechError(SpeechErrorCode.unsupported));
    }
  }

  @override
  Future<void> stop() => _quietly('stop');

  @override
  Future<void> cancel() => _quietly('cancel');

  @override
  Future<void> openSettings() => _quietly('openSettings');

  Future<void> _quietly(String method) async {
    try {
      await _channel.invokeMethod<void>(method);
    } on MissingPluginException {
      // 이 플랫폼에는 인식이 없다 — 멈출 것도, 열 설정도 없다.
    }
  }

  static SpeechEvent _toEvent(Object? raw) {
    final event = raw! as Map<Object?, Object?>;
    return switch (event['type']) {
      'partial' => SpeechPartial(event['text']! as String),
      'final' => SpeechFinal(event['text']! as String),
      'error' => SpeechError(_code(event['code'] as String?)),
      _ => const SpeechEnded(),
    };
  }

  static SpeechErrorCode _code(String? code) => switch (code) {
    'denied' => SpeechErrorCode.denied,
    'unsupported' => SpeechErrorCode.unsupported,
    'noSpeech' => SpeechErrorCode.noSpeech,
    _ => SpeechErrorCode.failed,
  };
}

final speechRecognizerProvider = Provider<SpeechRecognizer>(
  (ref) => ChannelSpeechRecognizer(),
);
