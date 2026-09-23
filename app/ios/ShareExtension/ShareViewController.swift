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

  /// 확장에서 본체를 여는 공식 API 는 없다 — 응답자 체인에서 UIApplication 을
  /// 찾아 `openURL:` 을 부른다(널리 쓰이는 방법).
  private func openHostApp() {
    let selector = sel_registerName("openURL:")
    var responder: UIResponder? = self
    while let current = responder {
      if current.responds(to: selector) && !(current is UIViewController) {
        current.perform(selector, with: Self.hostURL)
        return
      }
      responder = current.next
    }
  }

  private func finish() {
    extensionContext?.completeRequest(returningItems: nil)
  }
}
