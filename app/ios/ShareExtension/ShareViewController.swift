import UIKit
import UniformTypeIdentifiers

/// 카톡 등에서 [공유] → 차곡노트(③-A3, 설계 7절).
///
/// 글만 App Group 에 적고 본체 앱을 연 뒤 바로 끝난다 — 화면을 그리지 않는다.
/// 토큰·키체인·네트워크에 접근하지 않는다. 서버 호출은 본체가 한다.
final class ShareViewController: UIViewController {
  private static let appGroup = "group.com.chagocnote.app"
  private static let sharedTextKey = "sharedText"
  private static let hostURL = URL(string: "chagocnote://share")!
  private static let maxLength = 1000

  override func viewDidLoad() {
    super.viewDidLoad()
    view.backgroundColor = .clear
    let items = (extensionContext?.inputItems as? [NSExtensionItem]) ?? []
    let providers = items.flatMap { $0.attachments ?? [] }
    guard let provider = providers.first(where: {
      $0.hasItemConformingToTypeIdentifier(UTType.plainText.identifier)
    }) else {
      finish()
      return
    }
    provider.loadItem(forTypeIdentifier: UTType.plainText.identifier, options: nil) { [weak self] data, _ in
      let text = (data as? String)
        ?? (data as? NSAttributedString)?.string
        ?? (data as? Data).flatMap { String(data: $0, encoding: .utf8) }
      DispatchQueue.main.async {
        guard let self else { return }
        if let text = text?.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty {
          UserDefaults(suiteName: Self.appGroup)?
            .set(String(text.prefix(Self.maxLength)), forKey: Self.sharedTextKey)
          self.openHostApp()
        }
        self.finish()
      }
    }
  }

  /// 확장에서 본체를 여는 공식 API 는 없다. `NSExtensionContext.open`은 Today·iMessage 확장점만
  /// 지원하고, 응답자 체인의 옛 `openURL:`은 iOS 18부터 아무것도 열지 않는다. 그래서 응답자 체인에서
  /// UIApplication 을 찾아 `openURL:options:completionHandler:`를 셀렉터·IMP 로 직접 부른다 —
  /// 확장 전용 API 제한 아래에서도 컴파일되고 iOS 18 에서 동작하는, 널리 쓰이는 우회다.
  /// 그래도 실패하면 본체가 다음에 열릴 때 App Group 의 글을 `getPending`으로 집어 온다.
  private func openHostApp() {
    let selector = NSSelectorFromString("openURL:options:completionHandler:")
    var responder: UIResponder? = self
    while let current = responder {
      if let app = current as? UIApplication, app.responds(to: selector) {
        typealias OpenURL = @convention(c) (
          AnyObject, Selector, NSURL, NSDictionary, (@convention(block) (Bool) -> Void)?
        ) -> Void
        let fn = unsafeBitCast(app.method(for: selector), to: OpenURL.self)
        fn(app, selector, Self.hostURL as NSURL, NSDictionary(), nil)
        return
      }
      responder = current.next
    }
  }

  private func finish() {
    extensionContext?.completeRequest(returningItems: nil)
  }
}
