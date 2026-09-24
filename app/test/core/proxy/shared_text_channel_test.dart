// 공유 받기(③-A3)의 Dart 쪽 — 네이티브 채널을 흉내 내 pending 글이 들어오고,
// 다듬어지고(앞뒤 공백·1000자), 비면 무시되는지 본다.
import 'package:chagocnote/core/proxy/shared_text_channel.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

const _channel = MethodChannel(SharedTextChannel.name);

void _mockPending(String? pending, List<String> calls) {
  TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
      .setMockMethodCallHandler(_channel, (call) async {
        calls.add(call.method);
        return call.method == 'getPending' ? pending : null;
      });
  addTearDown(
    () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(_channel, null),
  );
}

/// 네이티브가 Dart 를 부르는 것을 흉내 낸다.
Future<void> _nativeSends(String text) => TestDefaultBinaryMessengerBinding
    .instance
    .defaultBinaryMessenger
    .handlePlatformMessage(
      SharedTextChannel.name,
      const StandardMethodCodec().encodeMethodCall(
        MethodCall('onSharedText', text),
      ),
      (_) {},
    );

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('시작 때 getPending 을 한 번 부르고, 받아 둔 글이 pending 에 들어간다', () async {
    final calls = <String>[];
    _mockPending('  내일 2시 두부  ', calls);
    final container = ProviderContainer.test();

    expect(container.read(pendingSharedTextProvider), isNull);
    await Future<void>.delayed(Duration.zero);
    expect(calls, ['getPending']);
    expect(container.read(pendingSharedTextProvider), '내일 2시 두부');
  });

  test('네이티브가 onSharedText 를 부르면 pending 이 바뀌고, 비우면 null 이다', () async {
    _mockPending(null, []);
    final container = ProviderContainer.test();
    container.read(pendingSharedTextProvider);
    await Future<void>.delayed(Duration.zero);

    await _nativeSends('모레 오후 3시 콩이 목욕');
    expect(container.read(pendingSharedTextProvider), '모레 오후 3시 콩이 목욕');

    container.read(pendingSharedTextProvider.notifier).clear();
    expect(container.read(pendingSharedTextProvider), isNull);
  });

  test('빈 글은 무시하고, 1000자를 넘으면 앞 1000자만 둔다', () async {
    _mockPending(null, []);
    final container = ProviderContainer.test();
    container.read(pendingSharedTextProvider);
    await Future<void>.delayed(Duration.zero);

    await _nativeSends('   ');
    expect(container.read(pendingSharedTextProvider), isNull);

    await _nativeSends('가' * 1200);
    expect(container.read(pendingSharedTextProvider)!.length, 1000);
  });

  test('채널이 없는 플랫폼(테스트·웹)에서는 조용히 넘어간다', () async {
    final container = ProviderContainer.test();
    container.read(pendingSharedTextProvider);
    await Future<void>.delayed(Duration.zero);
    expect(container.read(pendingSharedTextProvider), isNull);
  });
}
