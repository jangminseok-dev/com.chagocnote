import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 클립보드 — 화면이 [Clipboard] 플러그인을 직접 부르지 않게 감싼 자리.
///
/// 사진 선택기·카메라·마이크(④-2·④-3)도 같은 모양으로 `core/proxy/`에 둔다.
/// 화면은 프로바이더만 읽고, 테스트는 프로바이더를 override 한다.
abstract class AppClipboard {
  /// 클립보드의 글. 비었거나 글이 아니면 null.
  Future<String?> readText();

  Future<void> writeText(String text);
}

/// 실제 기기의 클립보드.
class SystemClipboard implements AppClipboard {
  const SystemClipboard();

  @override
  Future<String?> readText() async =>
      (await Clipboard.getData(Clipboard.kTextPlain))?.text;

  @override
  Future<void> writeText(String text) =>
      Clipboard.setData(ClipboardData(text: text));
}

final clipboardProvider = Provider<AppClipboard>(
  (ref) => const SystemClipboard(),
);
