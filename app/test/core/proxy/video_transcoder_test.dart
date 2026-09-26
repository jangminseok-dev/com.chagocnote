// 영상 압축 채널(④-3a 설계 3.1)의 Dart 쪽 — 네이티브 채널을 흉내 내 인자·결과·진행률·
// 오류 코드가 규약대로 오가는지 보고, 테스트 대역 FakeVideoTranscoder 자체도 확인한다.
import 'dart:async';
import 'dart:io';

import 'package:chagocnote/core/proxy/video_transcoder.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/upload_fakes.dart';

const _method = MethodChannel(ChannelVideoTranscoder.channelName);
const _progress = EventChannel(ChannelVideoTranscoder.progressChannelName);

final _messenger =
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

void _mockMethods(Future<Object?> Function(MethodCall call) handler) {
  _messenger.setMockMethodCallHandler(_method, handler);
  addTearDown(() => _messenger.setMockMethodCallHandler(_method, null));
}

class _Progress extends MockStreamHandler {
  _Progress(this.values);

  final List<double> values;
  var listened = 0;
  var cancelled = 0;

  @override
  void onListen(Object? arguments, MockStreamHandlerEventSink events) {
    listened++;
    for (final v in values) {
      events.success(v);
    }
  }

  @override
  void onCancel(Object? arguments) => cancelled++;
}

void _mockProgress(_Progress handler) {
  _messenger.setMockStreamHandler(_progress, handler);
  addTearDown(() => _messenger.setMockStreamHandler(_progress, null));
}

const _result = {
  'video': '/out/video.mp4',
  'thumb': '/out/thumb.jpg',
  'width': 1080,
  'height': 1920,
  'durationSeconds': 60,
  'trimmed': true,
};

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('transcode 는 source·outDir·maxSeconds 를 그대로 보내고 결과 맵을 돌려준다', () async {
    final calls = <MethodCall>[];
    _mockMethods((call) async {
      calls.add(call);
      return _result;
    });

    final result = await ChannelVideoTranscoder().transcode(
      '/tmp/picked.mov',
      Directory('/out'),
      maxSeconds: 60,
    );

    expect(calls.single.method, 'transcode');
    expect(calls.single.arguments, {
      'source': '/tmp/picked.mov',
      'outDir': '/out',
      'maxSeconds': 60,
    });
    expect(result.video, '/out/video.mp4');
    expect(result.thumb, '/out/thumb.jpg');
    expect(result.width, 1080);
    expect(result.height, 1920);
    expect(result.durationSeconds, 60);
    expect(result.trimmed, isTrue);
  });

  test('진행률 이벤트가 onProgress 로 순서대로 오고, 끝나면 구독을 푼다', () async {
    final progress = _Progress([0.3, 1.0]);
    _mockProgress(progress);
    _mockMethods((call) async {
      // 이벤트가 먼저 도착하도록 한 박자 늦게 끝낸다.
      await Future<void>.delayed(Duration.zero);
      return _result;
    });

    final seen = <double>[];
    await ChannelVideoTranscoder().transcode(
      '/tmp/picked.mov',
      Directory('/out'),
      onProgress: seen.add,
    );

    expect(seen, [0.3, 1.0]);
    expect(progress.listened, 1);
    expect(progress.cancelled, 1);
  });

  test('네이티브 오류 코드는 VideoTranscodeException 으로, 모르는 코드는 UNSUPPORTED 가 된다', () async {
    var code = 'TOO_SHORT';
    _mockMethods((call) async => throw PlatformException(code: code));
    final transcoder = ChannelVideoTranscoder();

    Future<String> failure() async {
      try {
        await transcoder.transcode('/tmp/a.mov', Directory('/out'));
      } on VideoTranscodeException catch (e) {
        return e.code;
      }
      fail('던지지 않았다');
    }

    expect(await failure(), 'TOO_SHORT');
    code = 'CANCELLED';
    expect(await failure(), 'CANCELLED');
    code = 'AVFoundationErrorDomain';
    expect(await failure(), 'UNSUPPORTED');
  });

  test('네이티브가 없으면 transcode 는 UNSUPPORTED 이고 cancel 은 조용하다', () async {
    final transcoder = ChannelVideoTranscoder();
    await expectLater(
      transcoder.transcode('/tmp/a.mov', Directory('/out')),
      throwsA(
        isA<VideoTranscodeException>().having((e) => e.code, 'code', 'UNSUPPORTED'),
      ),
    );
    await transcoder.cancel();
  });

  test('cancel 은 메서드 cancel 을 부른다', () async {
    final calls = <String>[];
    _mockMethods((call) async {
      calls.add(call.method);
      return null;
    });

    await ChannelVideoTranscoder().cancel();

    expect(calls, ['cancel']);
  });

  group('FakeVideoTranscoder', () {
    late Directory temp;

    setUp(() async {
      temp = await Directory.systemTemp.createTemp('fake-video');
      addTearDown(() => temp.delete(recursive: true));
    });

    test('원본을 video.mp4 로 복사하고 thumb.jpg 를 쓰며, failWith 면 그 코드로 던진다', () async {
      final source = File('${temp.path}/picked.mov');
      await source.writeAsBytes([1, 2, 3]);
      final fake = FakeVideoTranscoder()..trimmed = true;
      final seen = <double>[];

      final result = await fake.transcode(
        source.path,
        Directory('${temp.path}/out'),
        maxSeconds: 60,
        onProgress: seen.add,
      );

      expect(await File(result.video).readAsBytes(), [1, 2, 3]);
      expect(result.video, '${temp.path}/out/video.mp4');
      expect(result.thumb, '${temp.path}/out/thumb.jpg');
      expect(File(result.thumb).lengthSync(), greaterThan(0));
      expect(
        (result.width, result.height, result.durationSeconds, result.trimmed),
        (1080, 1920, 5, true),
      );
      expect(seen, [0.5, 1]);
      expect(fake.calls, [(source.path, 60)]);

      fake.failWith = 'UNSUPPORTED';
      await expectLater(
        fake.transcode(source.path, Directory('${temp.path}/out2')),
        throwsA(
          isA<VideoTranscodeException>().having((e) => e.code, 'code', 'UNSUPPORTED'),
        ),
      );
    });

    test('gate 로 기다리는 중에 cancel 하면 CANCELLED 로 끝난다', () async {
      final source = File('${temp.path}/picked.mov');
      await source.writeAsBytes([1]);
      final fake = FakeVideoTranscoder()..gate = Completer<void>();

      final pending = expectLater(
        fake.transcode(source.path, Directory('${temp.path}/out')),
        throwsA(
          isA<VideoTranscodeException>().having((e) => e.code, 'code', 'CANCELLED'),
        ),
      );
      await fake.cancel();

      await pending;
      expect(fake.cancelled, 1);
    });
  });
}
