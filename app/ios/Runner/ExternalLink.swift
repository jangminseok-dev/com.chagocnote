import Flutter
import UIKit

/// 바깥 주소 열기(⑫ 설계 5.4) — Dart `core/proxy/external_link.dart` 의 채널 규약을 따른다.
///
/// `open{url}` 은 기기의 브라우저(또는 그 주소를 맡는 앱)로 연다. 웹뷰가 아니다. `https` 이고 호스트가
/// 있는 주소만 연다 — 아니면 `BAD_URL`. 열지 못하면 `FAILED`. 주소를 오류 문구에 싣지 않는다.
final class ExternalLinkPlugin: NSObject, FlutterPlugin {
  static let channelName = "chagocnote/external_link"

  static func register(with registrar: FlutterPluginRegistrar) {
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
    registrar.addMethodCallDelegate(ExternalLinkPlugin(), channel: channel)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    guard call.method == "open" else {
      result(FlutterMethodNotImplemented)
      return
    }
    guard let args = call.arguments as? [String: Any],
          let text = args["url"] as? String,
          let url = URL(string: text),
          url.scheme?.lowercased() == "https",
          let host = url.host, !host.isEmpty else {
      result(FlutterError(code: "BAD_URL", message: "https 주소가 아니다", details: nil))
      return
    }
    UIApplication.shared.open(url, options: [:]) { opened in
      result(opened ? nil : FlutterError(code: "FAILED", message: "주소를 열지 못했다", details: nil))
    }
  }
}
