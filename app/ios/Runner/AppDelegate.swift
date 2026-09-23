import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    SharedTextPlugin.register(with: engineBridge.pluginRegistry.registrar(forPlugin: "SharedTextPlugin")!)
  }
}

/// 공유 받기(③-A3) — 공유 확장이 App Group 에 남긴 글을 Dart 로 넘긴다.
///
/// 확장은 글을 적고 `chagocnote://share` 로 본체를 연다. 이 플러그인은 씬의
/// URL 열림(콜드 스타트는 연결 옵션, 떠 있으면 openURLContexts)을 받아 글을
/// 읽고 지운 뒤 `onSharedText` 로 부른다. Dart 가 아직 준비 전이면 들고 있다가
/// `getPending` 으로 준다. 토큰·서버 호출은 없다 — Dart 의 몫이다.
final class SharedTextPlugin: NSObject, FlutterPlugin, FlutterSceneLifeCycleDelegate {
  static let channelName = "com.chagocnote.app/share"
  static let appGroup = "group.com.chagocnote.app"
  static let sharedTextKey = "sharedText"

  private let channel: FlutterMethodChannel
  private var pending: String?

  static func register(with registrar: FlutterPluginRegistrar) {
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
    let plugin = SharedTextPlugin(channel: channel)
    registrar.addMethodCallDelegate(plugin, channel: channel)
    registrar.addSceneDelegate(plugin)
  }

  private init(channel: FlutterMethodChannel) {
    self.channel = channel
    super.init()
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    guard call.method == "getPending" else {
      result(FlutterMethodNotImplemented)
      return
    }
    // 준비 전에 들고 있던 글, 없으면 App Group 에 남은 글(연결 옵션을 놓친 경우의 안전망).
    let text = pending ?? takeFromAppGroup()
    pending = nil
    result(text)
  }

  func scene(_ scene: UIScene, willConnectTo session: UISceneSession,
             options connectionOptions: UIScene.ConnectionOptions?) -> Bool {
    guard let contexts = connectionOptions?.urlContexts else { return false }
    return open(contexts)
  }

  func scene(_ scene: UIScene, openURLContexts URLContexts: Set<UIOpenURLContext>) -> Bool {
    return open(URLContexts)
  }

  private func open(_ contexts: Set<UIOpenURLContext>) -> Bool {
    guard contexts.contains(where: { $0.url.scheme == "chagocnote" && $0.url.host == "share" }),
          let text = takeFromAppGroup() else { return false }
    // Dart 쪽 핸들러가 아직 없으면 invoke 가 버려진다 — 들고 있다가 getPending 으로 준다.
    pending = text
    channel.invokeMethod("onSharedText", arguments: text) { [weak self] reply in
      if !(reply is FlutterError) && reply as? NSObject != FlutterMethodNotImplemented {
        self?.pending = nil
      }
    }
    return true
  }

  private func takeFromAppGroup() -> String? {
    let defaults = UserDefaults(suiteName: SharedTextPlugin.appGroup)
    guard let text = defaults?.string(forKey: SharedTextPlugin.sharedTextKey) else { return nil }
    defaults?.removeObject(forKey: SharedTextPlugin.sharedTextKey)
    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
    return trimmed.isEmpty ? nil : trimmed
  }
}
