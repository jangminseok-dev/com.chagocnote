// 음성 인식 채널(④-3b 설계 3.1)의 Dart 쪽 — 네이티브 채널을 흉내 내 가용성·권한·시작 인자·
// 이벤트·오류 코드가 규약대로 오가는지 보고, 테스트 대역 FakeSpeechRecognizer 자체도 확인한다.
import 'package:chagocnote/core/proxy/speech_recognizer.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/upload_fakes.dart';

const _method = MethodChannel(ChannelSpeechRecognizer.channelName);
const _events = EventChannel(ChannelSpeechRecognizer.eventsChannelName);

final _messenger =
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

void _mockMethods(Future<Object?> Function(MethodCall call) handler) {
  _messenger.setMockMethodCallHandler(_method, handler);
  addTearDown(() => _messenger.setMockMethodCallHandler(_method, null));
}

/// 네이티브 이벤트 쪽 흉내 — 받은 싱크를 쥐고 있다가 [send]로 흘린다.
class _Events extends MockStreamHandler {
  MockStreamHandlerEventSink? sink;
  var listened = 0;
  var cancelled = 0;

  void send(Map<String, Object?> event) => sink!.success(event);

  @override
  void onListen(Object? arguments, MockStreamHandlerEventSink events) {
    listened++;
    sink = events;
  }

  @override
  void onCancel(Object? arguments) => cancelled++;
}

_Events _mockEvents() {
  final handler = _Events();
  _messenger.setMockStreamHandler(_events, handler);
  addTearDown(() => _messenger.setMockStreamHandler(_events, null));
  return handler;
}

/// 이벤트 채널 메시지가 Dart 쪽 스트림까지 닿도록 한 박자 쉰다.
Future<void> _settle() => Future<void>.delayed(Duration.zero);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('availability 와 requestPermission 이 채널 결과를 그대로 돌려준다', () async {
    Object? availability = {'supported': false, 'reason': 'locale'};
    Object? permission = 'denied';
    final calls = <String>[];
    _mockMethods((call) async {
      calls.add(call.method);
      return switch (call.method) {
        'availability' => availability,
        'requestPermission' => permission,
        _ => null,
      };
    });
    final recognizer = ChannelSpeechRecognizer();

    final locale = await recognizer.availability();
    expect((locale.supported, locale.reason), (false, SpeechUnsupported.locale));
    expect(await recognizer.requestPermission(), SpeechPermission.denied);

    availability = {'supported': false, 'reason': 'device'};
    permission = 'granted';
    final device = await recognizer.availability();
    expect((device.supported, device.reason), (false, SpeechUnsupported.device));
    expect(await recognizer.requestPermission(), SpeechPermission.granted);

    availability = {'supported': true, 'reason': null};
    final ok = await recognizer.availability();
    expect((ok.supported, ok.reason), (true, null));

    expect(calls, [
      'availability',
      'requestPermission',
      'availability',
      'requestPermission',
      'availability',
    ]);
  });

  test('start 는 locale 을 보내고, 이벤트 채널의 partial·final·ended·error 가 SpeechEvent 로 온다', () async {
    final native = _mockEvents();
    final calls = <MethodCall>[];
    _mockMethods((call) async {
      calls.add(call);
      return null;
    });
    final recognizer = ChannelSpeechRecognizer();
    final seen = <SpeechEvent>[];
    final subscription = recognizer.events.listen(seen.add);
    addTearDown(subscription.cancel);

    await recognizer.start();
    await recognizer.start(locale: 'en-US');
    await _settle();
    native
      ..send({'type': 'partial', 'text': '발톱'})
      ..send({'type': 'final', 'text': '발톱 정리'})
      ..send({'type': 'error', 'code': 'noSpeech'})
      ..send({'type': 'ended'});
    await _settle();

    expect(calls.map((c) => c.method), ['start', 'start']);
    expect(calls.map((c) => c.arguments), [
      {'locale': 'ko-KR'},
      {'locale': 'en-US'},
    ]);
    expect(seen, hasLength(4));
    expect(seen[0], isA<SpeechPartial>().having((e) => e.text, 'text', '발톱'));
    expect(seen[1], isA<SpeechFinal>().having((e) => e.text, 'text', '발톱 정리'));
    expect(
      seen[2],
      isA<SpeechError>().having((e) => e.code, 'code', SpeechErrorCode.noSpeech),
    );
    expect(seen[3], isA<SpeechEnded>());
  });

  test('events 는 늦게 구독한 쪽도 받는다', () async {
    final native = _mockEvents();
    final recognizer = ChannelSpeechRecognizer();

    final first = <SpeechEvent>[];
    final a = recognizer.events.listen(first.add);
    await _settle();
    native.send({'type': 'partial', 'text': '목욕'});
    await _settle();
    await a.cancel();

    // 앞 구독이 끝난 뒤에 구독해도 네이티브를 다시 듣지 않고 같은 흐름을 받는다.
    final second = <SpeechEvent>[];
    final b = recognizer.events.listen(second.add);
    addTearDown(b.cancel);
    final third = <SpeechEvent>[];
    final c = recognizer.events.listen(third.add);
    addTearDown(c.cancel);
    await _settle();
    native.send({'type': 'final', 'text': '목욕 끝'});
    await _settle();

    expect(first.single, isA<SpeechPartial>());
    expect(second.single, isA<SpeechFinal>().having((e) => e.text, 'text', '목욕 끝'));
    expect(third.single, isA<SpeechFinal>());
    expect((native.listened, native.cancelled), (1, 0));
  });

  test('네이티브가 없으면 availability 는 device 미지원, start 는 unsupported 오류 이벤트, 나머지는 조용하다', () async {
    // 메서드 채널에 처리기가 없다 — MissingPluginException.
    _mockEvents();
    final recognizer = ChannelSpeechRecognizer();
    final seen = <SpeechEvent>[];
    final subscription = recognizer.events.listen(seen.add);
    addTearDown(subscription.cancel);

    final availability = await recognizer.availability();
    expect(
      (availability.supported, availability.reason),
      (false, SpeechUnsupported.device),
    );
    await recognizer.start();
    await recognizer.stop();
    await recognizer.cancel();
    await recognizer.openSettings();
    await _settle();

    expect(
      seen.single,
      isA<SpeechError>().having((e) => e.code, 'code', SpeechErrorCode.unsupported),
    );
  });

  test('모르는 오류 코드는 failed 다', () async {
    final native = _mockEvents();
    var startCode = 'denied';
    _mockMethods((call) async => throw PlatformException(code: startCode));
    final recognizer = ChannelSpeechRecognizer();
    final seen = <SpeechEvent>[];
    final subscription = recognizer.events.listen(seen.add);
    addTearDown(subscription.cancel);
    await _settle();

    await recognizer.start();
    startCode = 'kAFAssistantErrorDomain';
    await recognizer.start();
    native
      ..send({'type': 'error', 'code': 'unsupported'})
      ..send({'type': 'error', 'code': 'ERROR_SERVER'});
    await _settle();

    expect(seen.map((e) => (e as SpeechError).code), [
      SpeechErrorCode.denied,
      SpeechErrorCode.failed,
      SpeechErrorCode.unsupported,
      SpeechErrorCode.failed,
    ]);
  });

  test('FakeSpeechRecognizer 가 호출을 세고 이벤트를 흘린다', () async {
    final fake = FakeSpeechRecognizer()
      ..availabilityResult = const SpeechAvailability(
        supported: false,
        reason: SpeechUnsupported.locale,
      )
      ..permissionResult = SpeechPermission.denied;
    final seen = <SpeechEvent>[];
    final subscription = fake.events.listen(seen.add);
    addTearDown(subscription.cancel);

    expect((await fake.availability()).reason, SpeechUnsupported.locale);
    expect(await fake.requestPermission(), SpeechPermission.denied);
    await fake.start();
    await fake.start(locale: 'en-US');
    await fake.stop();
    await fake.cancel();
    await fake.openSettings();
    fake
      ..emitPartial('귀')
      ..emitFinal('귀 청소')
      ..emitError(SpeechErrorCode.noSpeech)
      ..emitEnded();
    await _settle();

    expect(fake.starts, ['ko-KR', 'en-US']);
    expect(
      (fake.permissionRequests, fake.stops, fake.cancels, fake.settingsOpened),
      (1, 1, 1, 1),
    );
    expect(seen, hasLength(4));
    expect(seen[0], isA<SpeechPartial>().having((e) => e.text, 'text', '귀'));
    expect(seen[1], isA<SpeechFinal>().having((e) => e.text, 'text', '귀 청소'));
    expect(
      seen[2],
      isA<SpeechError>().having((e) => e.code, 'code', SpeechErrorCode.noSpeech),
    );
    expect(seen[3], isA<SpeechEnded>());
  });
}
