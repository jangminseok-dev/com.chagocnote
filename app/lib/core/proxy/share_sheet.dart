import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// OS 공유 시트(⑤ 설계 9.2) — 글자(주소)만 넘긴다. 결과(보냈는지·취소했는지)는 받지 않는다.
///
/// 외부 패키지 없이 네이티브가 띄운다.
/// - iOS `ios/Runner/ShareSheet.swift`: `UIActivityViewController`. 시트 머리에 보일 것(주소의
///   호스트)을 직접 준다 — 맡겨 두면 iOS 가 머리를 그리려고 그 주소를 받아 온다.
/// - 안드로이드 `android/app/src/main/kotlin/com/chagocnote/chagocnote/ShareSheet.kt`:
///   `ACTION_SEND` 선택기. 이 앱도 글 공유를 받으므로(③-A3) 선택기에서 자기 자신을 뺀다.
///
/// 채널 규약: 메서드 채널 [ChannelShareSheet.channelName] 의 `shareText({text, x, y, width, height})`.
/// 시트를 띄운 뒤 곧바로 끝난다(닫힐 때까지 기다리지 않는다).
abstract class ShareSheet {
  /// [origin] 은 누른 버튼의 화면 좌표 사각형이다 — 아이패드는 공유 시트가 말풍선이라 붙일 자리가
  /// 꼭 필요하다(없으면 UIKit 이 죽는다).
  Future<void> shareText(String text, {required Rect origin});
}

class ChannelShareSheet implements ShareSheet {
  ChannelShareSheet({MethodChannel? channel})
    : _channel = channel ?? const MethodChannel(channelName);

  static const channelName = 'chagocnote/share_sheet';

  final MethodChannel _channel;

  // 채널 오류는 삼키지 않는다 — 화면이 문구로 알린다.
  @override
  Future<void> shareText(String text, {required Rect origin}) =>
      _channel.invokeMethod<void>('shareText', {
        'text': text,
        'x': origin.left,
        'y': origin.top,
        'width': origin.width,
        'height': origin.height,
      });
}

final shareSheetProvider = Provider<ShareSheet>((ref) => ChannelShareSheet());
