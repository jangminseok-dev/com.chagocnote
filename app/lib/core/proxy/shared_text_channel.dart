import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 공유 받기(③-A3) — 네이티브(iOS 공유 확장 → 본체, 안드로이드 `ACTION_SEND`)가
/// 넘긴 글을 받는 채널. 오가는 것은 글뿐이다. 토큰과 서버 호출은 앱 본체의
/// 몫이다(설계 7절 — 확장은 글만 앱 본체에 넘기고 앱을 연다).
///
/// - 네이티브 → Dart: `onSharedText(text)`.
/// - Dart → 네이티브: `getPending()` — 앱(Dart)이 뜨기 전에 받아 둔 글을 한 번
///   가져온다(콜드 스타트). 네이티브는 준 뒤 비운다.
class SharedTextChannel {
  SharedTextChannel([MethodChannel? channel])
    : _channel = channel ?? const MethodChannel(name);

  static const name = 'com.chagocnote.app/share';

  final MethodChannel _channel;

  /// 네이티브의 호출을 받기 시작하고, 받아 둔 글이 있으면 [onText]로 넘긴다.
  Future<void> start(void Function(String text) onText) async {
    _channel.setMethodCallHandler((call) async {
      if (call.method == 'onSharedText' && call.arguments is String) {
        onText(call.arguments as String);
      }
    });
    try {
      final pending = await _channel.invokeMethod<String>('getPending');
      if (pending != null) onText(pending);
    } on MissingPluginException {
      // 이 플랫폼에는 공유 받기가 없다(테스트·웹) — 조용히 넘어간다.
    }
  }
}

final sharedTextChannelProvider = Provider<SharedTextChannel>(
  (ref) => SharedTextChannel(),
);

/// 아직 열지 않은, 공유로 받은 글. 앱 루트가 로그인·매장 선택이 끝난 뒤
/// 초안 화면을 열고 [clear]한다.
class PendingSharedText extends Notifier<String?> {
  static const _maxLength = 1000;

  @override
  String? build() {
    // 처음 지켜보는 순간 채널을 연다. 받아 둔 글은 비동기로 들어온다.
    ref.read(sharedTextChannelProvider).start(set);
    return null;
  }

  /// 앞뒤 공백을 걷고 서버가 받는 길이(1000자)로 자른다. 비면 무시한다.
  void set(String text) {
    final trimmed = text.trim();
    if (trimmed.isEmpty) return;
    state = trimmed.length > _maxLength
        ? trimmed.substring(0, _maxLength)
        : trimmed;
  }

  void clear() => state = null;
}

final pendingSharedTextProvider = NotifierProvider<PendingSharedText, String?>(
  PendingSharedText.new,
);
