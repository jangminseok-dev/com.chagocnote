// 바깥 주소 열기 채널(⑫ 설계 5.4)의 Dart 쪽 — 네이티브 채널을 흉내 내 주소가 규약대로 가는지,
// https 가 아닌 주소는 채널을 부르지 않는지, 채널 오류가 그대로 나오는지 보고, 대역 자체도 확인한다.
import 'package:chagocnote/core/proxy/external_link.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_external_link.dart';

const _channel = MethodChannel(ChannelExternalLink.channelName);

final _messenger =
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

void _mock(Future<Object?> Function(MethodCall call) handler) {
  _messenger.setMockMethodCallHandler(_channel, handler);
  addTearDown(() => _messenger.setMockMethodCallHandler(_channel, null));
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('open 은 주소를 글자 그대로 채널에 보낸다', () async {
    final calls = <MethodCall>[];
    _mock((call) async {
      calls.add(call);
      return null;
    });

    await ChannelExternalLink().open(
      Uri.parse('https://m.place.naver.com/place/1/review?entry=pll'),
    );

    expect(calls.single.method, 'open');
    expect(calls.single.arguments, {
      'url': 'https://m.place.naver.com/place/1/review?entry=pll',
    });
  });

  for (final bad in [
    'http://example.com',
    'javascript:alert(1)',
    'https:///no-host',
    'file:///etc/hosts',
    'intent://scan/#Intent;scheme=zxing;end',
  ]) {
    test('https 가 아니거나 호스트가 없으면($bad) 채널을 부르지 않고 던진다', () async {
      var called = false;
      _mock((call) async {
        called = true;
        return null;
      });

      await expectLater(
        ChannelExternalLink().open(Uri.parse(bad)),
        throwsArgumentError,
      );
      expect(called, isFalse);
    });
  }

  test('대문자 스킴도 https 로 본다', () async {
    final calls = <MethodCall>[];
    _mock((call) async {
      calls.add(call);
      return null;
    });

    await ChannelExternalLink().open(Uri.parse('HTTPS://naver.me/abc'));

    expect(calls, hasLength(1));
  });

  test('채널 오류는 그대로 던진다', () async {
    _mock((call) async => throw PlatformException(code: 'NO_BROWSER'));

    await expectLater(
      ChannelExternalLink().open(Uri.parse('https://naver.me/abc')),
      throwsA(
        isA<PlatformException>().having((e) => e.code, 'code', 'NO_BROWSER'),
      ),
    );
  });

  test('대역은 연 주소를 차례로 적고, error 가 있으면 던진다', () async {
    final fake = FakeExternalLink();

    await fake.open(Uri.parse('https://a.example/1'));
    await fake.open(Uri.parse('https://b.example/2'));
    expect(fake.opened, [
      Uri.parse('https://a.example/1'),
      Uri.parse('https://b.example/2'),
    ]);

    fake.error = PlatformException(code: 'FAILED');
    await expectLater(
      fake.open(Uri.parse('https://c.example/3')),
      throwsA(isA<PlatformException>()),
    );
    expect(fake.opened, hasLength(2));
  });
}
