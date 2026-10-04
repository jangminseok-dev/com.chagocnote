// 공유 시트 채널(⑤ 설계 9.2)의 Dart 쪽 — 네이티브 채널을 흉내 내 글과 버튼 사각형이 규약대로
// 가는지, 채널 오류가 그대로 나오는지 보고, 테스트 대역 FakeShareSheet 자체도 확인한다.
import 'package:chagocnote/core/proxy/share_sheet.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import '../../support/fake_share_sheet.dart';

const _channel = MethodChannel(ChannelShareSheet.channelName);

final _messenger =
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger;

void _mock(Future<Object?> Function(MethodCall call) handler) {
  _messenger.setMockMethodCallHandler(_channel, handler);
  addTearDown(() => _messenger.setMockMethodCallHandler(_channel, null));
}

const _link = 'http://127.0.0.1:3010/r/TEST-TOKEN';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('shareText 는 글과 버튼 사각형을 채널에 보낸다', () async {
    final calls = <MethodCall>[];
    _mock((call) async {
      calls.add(call);
      return null;
    });

    await ChannelShareSheet().shareText(
      _link,
      origin: const Rect.fromLTWH(16, 700, 361, 52),
    );

    expect(calls.single.method, 'shareText');
    expect(calls.single.arguments, {
      'text': _link,
      'x': 16.0,
      'y': 700.0,
      'width': 361.0,
      'height': 52.0,
    });
  });

  test('채널 오류는 그대로 던진다', () async {
    _mock((call) async => throw PlatformException(code: 'NO_VIEW'));

    await expectLater(
      ChannelShareSheet().shareText(_link, origin: Rect.zero),
      throwsA(isA<PlatformException>().having((e) => e.code, 'code', 'NO_VIEW')),
    );
  });

  test('대역은 받은 글과 사각형을 차례로 적는다', () async {
    final fake = FakeShareSheet();
    const first = Rect.fromLTWH(0, 0, 10, 10);
    const second = Rect.fromLTWH(16, 700, 361, 52);

    await fake.shareText('첫째', origin: first);
    await fake.shareText('둘째', origin: second);

    expect(fake.shared, ['첫째', '둘째']);
    expect(fake.origins, [first, second]);

    fake.error = PlatformException(code: 'NO_VIEW');
    await expectLater(
      fake.shareText('셋째', origin: first),
      throwsA(isA<PlatformException>()),
    );
  });
}
