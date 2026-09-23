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

  /// 확장에서 본체를 여는 공식 API — `NSExtensionContext.open(_:completionHandler:)`
  /// (iOS 8+). 예전엔 응답자 체인에서 UIApplication 을 찾아 비공식 `openURL:`
  /// 을 불러야 했지만(당시엔 이 API 가 잘 알려지지 않았다), iOS 18부터 그
  /// 경로는 "BUG IN CLIENT OF UIKIT … Force returning false"로 조용히
  /// 실패한다. `extensionContext.open`은 시스템이 확장을 위해 공식으로 여는
  /// 길이라 APPLICATION_EXTENSION_API_ONLY 제한과 부딪히지 않고, iOS 18에서도
  /// 그대로 동작한다. 이 호출이 실패해도 App Group 에는 이미 적어 뒀으니
  /// 본체가 다음에 뜰 때 안전망(`getPending`)으로 읽어 간다.
  private func openHostApp() {
    extensionContext?.open(Self.hostURL, completionHandler: nil)
  }

  private func finish() {
    extensionContext?.completeRequest(returningItems: nil)
  }
}
