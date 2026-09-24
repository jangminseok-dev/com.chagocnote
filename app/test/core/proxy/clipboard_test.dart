import 'package:chagocnote/core/proxy/clipboard.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('SystemClipboard 는 플랫폼 클립보드를 읽고 쓴다', () async {
    final calls = <MethodCall>[];
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(SystemChannels.platform, (call) async {
          calls.add(call);
          if (call.method == 'Clipboard.getData') return {'text': '콩이'};
          return null;
        });
    addTearDown(
      () => TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(SystemChannels.platform, null),
    );

    const clipboard = SystemClipboard();
    expect(await clipboard.readText(), '콩이');
    await clipboard.writeText('ABC123');
    expect(calls.map((c) => c.method), [
      'Clipboard.getData',
      'Clipboard.setData',
    ]);
    expect(calls.last.arguments, {'text': 'ABC123'});
  });
}
