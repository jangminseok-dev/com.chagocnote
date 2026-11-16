import 'package:chagocnote/core/proxy/external_link.dart';

/// 바깥 주소 열기 대역 — 연 주소를 적어 둔다. 테스트가 `externalLinkProvider`를 이걸로 override 한다.
/// 실제 채널처럼 https 가 아니면 [ArgumentError] 를 던진다.
class FakeExternalLink implements ExternalLink {
  final opened = <Uri>[];

  /// 있으면 적지 않고 이것을 던진다(채널 오류 흉내).
  Object? error;

  @override
  Future<void> open(Uri url) async {
    if (!isOpenableUrl(url)) throw ArgumentError('https 주소만 열 수 있다');
    if (error case final error?) throw error;
    opened.add(url);
  }
}
