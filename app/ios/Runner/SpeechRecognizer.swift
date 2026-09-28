import AVFoundation
import Flutter
import Speech
import UIKit

/// 음성 인식(④-3b 설계 3.4절) — Dart `core/proxy/speech_recognizer.dart` 의 채널 규약을 따른다.
///
/// 인식은 `SFSpeechRecognizer` 에 `requiresOnDeviceRecognition` 을 걸어 기기 안에서만 한다(서버로 소리를
/// 보내지 않는다). 소리는 `AVAudioEngine` 입력 노드 탭으로 받아 요청에 붙인다. 결과는 이벤트 채널로
/// `{type: partial|final|ended|error, text?, code?}` 를 보낸다. 외부 패키지 없이 Speech·AVFoundation 만 쓴다.
///
/// 한 번에 한 세션만 듣는다. 듣는 중에 또 `start` 가 오면 앞 것을 조용히 취소하고 새로 시작한다
/// (다른 칸의 마이크를 누른 경우 — Dart 가 앞 것을 끝내지만 순서가 엇갈려도 견딘다).
final class SpeechRecognizerPlugin: NSObject, FlutterPlugin, FlutterStreamHandler {
  static let channelName = "chagocnote/speech"
  static let eventsChannelName = "chagocnote/speech/events"

  /// 입력 탭 버퍼 크기(프레임).
  private static let bufferSize: AVAudioFrameCount = 1024

  private var eventSink: FlutterEventSink?

  /// 진행 중인 세션 — 없으면 셋 다 nil.
  private var engine: AVAudioEngine?
  private var request: SFSpeechAudioBufferRecognitionRequest?
  private var task: SFSpeechRecognitionTask?
  /// 인식기는 세션 동안 붙잡아 둔다 — 놓으면 작업이 함께 사라진다.
  private var recognizer: SFSpeechRecognizer?

  /// 세션 번호 — 끝나거나 취소된 세션의 늦은 콜백을 버리려고 세션마다 올린다.
  private var generation = 0
  /// `stop` 을 받았다 — 이제 오는 오류는 알리지 않고 `ended` 만 보낸다.
  private var stopping = false
  /// 시작 전 오디오 세션 설정 — 끝날 때 되돌린다. 없으면 바꾼 적이 없다.
  private var previousAudio: (AVAudioSession.Category, AVAudioSession.Mode, AVAudioSession.CategoryOptions)?

  static func register(with registrar: FlutterPluginRegistrar) {
    let plugin = SpeechRecognizerPlugin()
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
    registrar.addMethodCallDelegate(plugin, channel: channel)
    let events = FlutterEventChannel(name: eventsChannelName, binaryMessenger: registrar.messenger())
    events.setStreamHandler(plugin)

    let center = NotificationCenter.default
    center.addObserver(plugin, selector: #selector(onInterruption(_:)),
                       name: AVAudioSession.interruptionNotification, object: nil)
    center.addObserver(plugin, selector: #selector(onRouteChange(_:)),
                       name: AVAudioSession.routeChangeNotification, object: nil)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "availability":
      let locale = (call.arguments as? [String: Any])?["locale"] as? String ?? "ko-KR"
      result(availability(locale: locale))
    case "requestPermission":
      requestPermission(result: result)
    case "start":
      let locale = (call.arguments as? [String: Any])?["locale"] as? String ?? "ko-KR"
      start(locale: locale)
      result(nil)
    case "stop":
      stop()
      result(nil)
    case "cancel":
      // Dart 가 취소를 알고 있다 — 이벤트 없이 조용히.
      teardown(cancelTask: true)
      result(nil)
    case "openSettings":
      UIApplication.shared.open(URL(string: UIApplication.openSettingsURLString)!)
      result(nil)
    default:
      result(FlutterMethodNotImplemented)
    }
  }

  // MARK: - FlutterStreamHandler

  func onListen(withArguments arguments: Any?, eventSink events: @escaping FlutterEventSink) -> FlutterError? {
    eventSink = events
    return nil
  }

  func onCancel(withArguments arguments: Any?) -> FlutterError? {
    eventSink = nil
    return nil
  }

  // MARK: - 가용성·권한

  private func availability(locale: String) -> [String: Any] {
    // 이 언어의 인식기가 아예 없다.
    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale)) else {
      return ["supported": false, "reason": "locale"]
    }
    // 온디바이스 인식이 없는 기기(시뮬레이터 포함)거나 지금 인식기를 쓸 수 없다.
    guard recognizer.supportsOnDeviceRecognition, recognizer.isAvailable else {
      return ["supported": false, "reason": "device"]
    }
    return ["supported": true]
  }

  /// 음성 인식 권한을 먼저, 허용이면 마이크 권한을 묻는다. 둘 다 허용이어야 granted.
  private func requestPermission(result: @escaping FlutterResult) {
    SFSpeechRecognizer.requestAuthorization { status in
      DispatchQueue.main.async {
        guard status == .authorized else {
          result("denied")
          return
        }
        Self.requestRecordPermission { granted in
          DispatchQueue.main.async { result(granted ? "granted" : "denied") }
        }
      }
    }
  }

  private static func requestRecordPermission(_ done: @escaping (Bool) -> Void) {
    if #available(iOS 17.0, *) {
      AVAudioApplication.requestRecordPermission(completionHandler: done)
    } else {
      AVAudioSession.sharedInstance().requestRecordPermission(done)
    }
  }

  /// 지금 두 권한이 모두 허용인가 — 시작 전과 오류를 읽을 때 쓴다.
  private static var permitted: Bool {
    let record: Bool
    if #available(iOS 17.0, *) {
      record = AVAudioApplication.shared.recordPermission == .granted
    } else {
      record = AVAudioSession.sharedInstance().recordPermission == .granted
    }
    return record && SFSpeechRecognizer.authorizationStatus() == .authorized
  }

  // MARK: - 듣기

  private func start(locale: String) {
    // 앞 세션이 남아 있으면 조용히 치운다.
    teardown(cancelTask: true)

    guard let recognizer = SFSpeechRecognizer(locale: Locale(identifier: locale)),
          recognizer.supportsOnDeviceRecognition, recognizer.isAvailable else {
      fail("unsupported")
      return
    }
    guard Self.permitted else {
      fail("denied")
      return
    }

    let audio = AVAudioSession.sharedInstance()
    previousAudio = (audio.category, audio.mode, audio.categoryOptions)
    do {
      try audio.setCategory(.record, mode: .measurement, options: .duckOthers)
      try audio.setActive(true, options: .notifyOthersOnDeactivation)
    } catch {
      restoreAudio()
      fail("failed")
      return
    }

    let request = SFSpeechAudioBufferRecognitionRequest()
    // 서버 인식으로 넘어가지 않게 — 기기 안에서만.
    request.requiresOnDeviceRecognition = true
    request.shouldReportPartialResults = true

    let engine = AVAudioEngine()
    let input = engine.inputNode
    let format = input.outputFormat(forBus: 0)
    // 입력 장치가 없으면 형식이 비어 있고, 탭을 걸면 예외로 앱이 죽는다.
    guard format.sampleRate > 0, format.channelCount > 0 else {
      restoreAudio()
      fail("failed")
      return
    }
    input.installTap(onBus: 0, bufferSize: Self.bufferSize, format: format) { buffer, _ in
      request.append(buffer)
    }
    engine.prepare()
    do {
      try engine.start()
    } catch {
      input.removeTap(onBus: 0)
      restoreAudio()
      fail("failed")
      return
    }

    generation += 1
    let current = generation
    stopping = false
    self.recognizer = recognizer
    self.engine = engine
    self.request = request
    self.task = recognizer.recognitionTask(with: request) { [weak self] result, error in
      DispatchQueue.main.async {
        self?.onRecognition(generation: current, result: result, error: error)
      }
    }
  }

  /// 소리를 그만 받고 인식기에 끝을 알린다 — 마지막 결과는 인식 콜백이 `final` 로 보낸다.
  private func stop() {
    guard task != nil, !stopping else { return }
    stopping = true
    stopAudio()
    request?.endAudio()
  }

  private func onRecognition(generation: Int, result: SFSpeechRecognitionResult?, error: Error?) {
    // 이미 끝났거나 취소된 세션의 늦은 콜백.
    guard generation == self.generation, task != nil else { return }

    if let result {
      let text = result.bestTranscription.formattedString
      guard result.isFinal else {
        send(["type": "partial", "text": text])
        return
      }
      if text.isEmpty {
        finish(error: stopping ? nil : "noSpeech")
      } else {
        send(["type": "final", "text": text])
        finish(error: nil)
      }
      return
    }
    if let error {
      // 멈추라고 한 뒤의 오류(말이 없었음 등)는 알리지 않는다 — 끝났다는 것만.
      finish(error: stopping ? nil : Self.code(for: error))
    }
  }

  /// 인식 오류를 채널 오류 코드로.
  private static func code(for error: Error) -> String {
    // 듣는 도중 설정에서 권한을 거둔 경우 — 코드보다 현재 상태가 정확하다.
    guard permitted else { return "denied" }
    let error = error as NSError
    switch (error.domain, error.code) {
    case ("kAFAssistantErrorDomain", 1110):
      // "No speech detected".
      return "noSpeech"
    case ("kLSRErrorDomain", 201), ("kLSRErrorDomain", 300):
      // 받아쓰기가 꺼져 있음 · 온디바이스 인식기를 띄우지 못함(언어 모델 없음).
      return "unsupported"
    default:
      return "failed"
    }
  }

  // MARK: - 끝내기

  /// 세션을 정리하고 (오류가 있으면 먼저) `ended` 를 보낸다.
  private func finish(error: String?) {
    teardown(cancelTask: false)
    if let error { send(["type": "error", "code": error]) }
    send(["type": "ended"])
  }

  /// 시작 전에 실패했다 — 세션이 없으니 정리할 것 없이 알리기만.
  private func fail(_ code: String) {
    send(["type": "error", "code": code])
    send(["type": "ended"])
  }

  private func stopAudio() {
    guard let engine else { return }
    engine.inputNode.removeTap(onBus: 0)
    engine.stop()
    self.engine = nil
  }

  /// 세션을 치운다. 이벤트는 보내지 않는다. 번호를 올려 늦은 콜백을 버린다.
  private func teardown(cancelTask: Bool) {
    guard task != nil else { return }
    generation += 1
    stopAudio()
    request?.endAudio()
    if cancelTask { task?.cancel() }
    task = nil
    request = nil
    recognizer = nil
    stopping = false
    restoreAudio()
  }

  /// 줄였던 다른 앱 소리를 되돌리고 카테고리도 시작 전으로 — `.record` 로 두면 이후 영상 재생이 무음이 된다.
  private func restoreAudio() {
    guard let previous = previousAudio else { return }
    previousAudio = nil
    let audio = AVAudioSession.sharedInstance()
    try? audio.setActive(false, options: .notifyOthersOnDeactivation)
    try? audio.setCategory(previous.0, mode: previous.1, options: previous.2)
  }

  private func send(_ event: [String: Any]) {
    // 듣는 쪽이 없으면 조용히 버린다.
    eventSink?(event)
  }

  // MARK: - 인터럽션·라우트

  /// 전화·알람 등이 오디오를 가져갔다 — 세션을 끝낸다(이어 듣기는 Dart 가 정한다).
  @objc private func onInterruption(_ note: Notification) {
    guard let raw = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
          AVAudioSession.InterruptionType(rawValue: raw) == .began else { return }
    DispatchQueue.main.async { [weak self] in
      guard let self, self.task != nil else { return }
      self.finish(error: nil)
    }
  }

  /// 입력 장치가 빠지거나 새로 붙었다 — 엔진의 입력 형식이 바뀌어 탭이 더는 맞지 않으니 끝낸다.
  @objc private func onRouteChange(_ note: Notification) {
    guard let raw = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
          let reason = AVAudioSession.RouteChangeReason(rawValue: raw),
          reason == .oldDeviceUnavailable || reason == .newDeviceAvailable else { return }
    DispatchQueue.main.async { [weak self] in
      guard let self, self.task != nil else { return }
      self.finish(error: nil)
    }
  }
}
