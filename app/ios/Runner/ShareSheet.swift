import Flutter
import LinkPresentation
import UIKit

/// 공유 시트(⑤ 설계 9.2) — Dart `core/proxy/share_sheet.dart` 의 채널 규약을 따른다.
///
/// `shareText{text, x, y, width, height}` 는 `UIActivityViewController` 를 띄우고 곧바로 끝난다
/// (닫힐 때까지 기다리지 않고, 보냈는지·취소했는지도 돌려주지 않는다). 받는 앱에는 글자로 넘긴다.
final class ShareSheetPlugin: NSObject, FlutterPlugin {
  static let channelName = "chagocnote/share_sheet"

  static func register(with registrar: FlutterPluginRegistrar) {
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
    registrar.addMethodCallDelegate(ShareSheetPlugin(), channel: channel)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    guard call.method == "shareText" else {
      result(FlutterMethodNotImplemented)
      return
    }
    guard let args = call.arguments as? [String: Any],
          let text = args["text"] as? String,
          let x = args["x"] as? Double,
          let y = args["y"] as? Double,
          let width = args["width"] as? Double,
          let height = args["height"] as? Double else {
      result(FlutterError(code: "BAD_ARGS", message: "인자가 올바르지 않다", details: nil))
      return
    }
    guard let top = topViewController() else {
      result(FlutterError(code: "NO_VIEW", message: "시트를 띄울 화면이 없다", details: nil))
      return
    }

    let sheet = UIActivityViewController(activityItems: [SharedText(text)], applicationActivities: nil)
    // 아이패드는 시트가 말풍선이다 — 붙일 자리가 없으면 UIKit 이 죽는다. Flutter 의 논리 좌표가 곧 포인트다.
    sheet.popoverPresentationController?.sourceView = top.view
    sheet.popoverPresentationController?.sourceRect = CGRect(x: x, y: y, width: width, height: height)
    top.present(sheet, animated: true)
    result(nil)
  }

  /// 키 윈도의 맨 위 화면 — 이미 떠 있는 것(다이얼로그 등)이 있으면 그 위에 띄워야 한다.
  private func topViewController() -> UIViewController? {
    let window = UIApplication.shared.connectedScenes
      .compactMap { ($0 as? UIWindowScene)?.keyWindow }
      .first
    var top = window?.rootViewController
    while let presented = top?.presentedViewController {
      top = presented
    }
    return top
  }
}

/// 넘길 글 — 시트 머리에 보일 것을 우리가 정해 준다.
///
/// 글자를 그대로 넘겨도 주소처럼 생겼으면 iOS 가 머리의 미리보기를 그리려고 그 주소를 받아 온다
/// (`LPMetadataProvider`) — 보호자보다 먼저 알림장을 여는 셈이다. 머리 정보를 직접 주면 받아 오지
/// 않는다. 머리에는 iOS 가 하던 대로 주소의 호스트만 보인다(주소가 아니면 글 그대로).
private final class SharedText: NSObject, UIActivityItemSource {
  private let text: String

  init(_ text: String) {
    self.text = text
  }

  func activityViewControllerPlaceholderItem(_ activityViewController: UIActivityViewController) -> Any {
    return text
  }

  func activityViewController(_ activityViewController: UIActivityViewController,
                              itemForActivityType activityType: UIActivity.ActivityType?) -> Any? {
    return text
  }

  func activityViewControllerLinkMetadata(_ activityViewController: UIActivityViewController) -> LPLinkMetadata? {
    let metadata = LPLinkMetadata()
    metadata.title = URL(string: text)?.host ?? text
    return metadata
  }
}
