import 'package:chagocnote/core/proxy/clipboard.dart';

/// 메모리 클립보드. 테스트가 `clipboardProvider`를 이걸로 override 한다.
class FakeClipboard implements AppClipboard {
  FakeClipboard([this.text]);

  String? text;

  @override
  Future<String?> readText() async => text;

  @override
  Future<void> writeText(String value) async => text = value;
}
