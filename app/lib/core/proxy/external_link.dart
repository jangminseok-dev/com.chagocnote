import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 바깥 주소 열기(⑫ 설계 5.4) — 알림장 설정의 [열어 보기]가 매장이 넣은 리뷰 주소를 기기의 브라우저로
/// 연다. 웹뷰가 아니다(앱은 웹뷰를 쓰지 않는다). `https` 만 연다.
///
/// 외부 패키지 없이 네이티브가 연다.
/// - iOS `ios/Runner/ExternalLink.swift`: `UIApplication.open`.
/// - 안드로이드 `android/app/src/main/kotlin/com/chagocnote/chagocnote/ExternalLink.kt`:
///   `ACTION_VIEW`(+ `CATEGORY_BROWSABLE`). 열 앱이 없으면 `NO_BROWSER`.
///
/// 채널 규약: 메서드 채널 [ChannelExternalLink.channelName] 의 `open({url})`. 열기를 맡기고 곧바로
/// 끝난다(브라우저가 닫힐 때까지 기다리지 않는다). 네이티브도 `https` 가 아니면 `BAD_URL` 이다.
abstract class ExternalLink {
  /// [url] 이 `https` 가 아니거나 호스트가 없으면 채널을 부르지 않고 [ArgumentError] 를 던진다.
  /// 채널 오류(`PlatformException`)는 그대로 던진다 — 화면이 문구로 알린다.
  Future<void> open(Uri url);
}

/// `https` 이고 호스트가 있는가. 스킴은 대소문자를 가리지 않는다(`Uri` 가 소문자로 읽는다).
bool isOpenableUrl(Uri url) => url.scheme == 'https' && url.host.isNotEmpty;

class ChannelExternalLink implements ExternalLink {
  ChannelExternalLink({MethodChannel? channel})
    : _channel = channel ?? const MethodChannel(channelName);

  static const channelName = 'chagocnote/external_link';

  final MethodChannel _channel;

  @override
  Future<void> open(Uri url) async {
    if (!isOpenableUrl(url)) {
      // 주소를 오류 문구에 싣지 않는다.
      throw ArgumentError('https 주소만 열 수 있다');
    }
    await _channel.invokeMethod<void>('open', {'url': url.toString()});
  }
}

final externalLinkProvider = Provider<ExternalLink>(
  (ref) => ChannelExternalLink(),
);
