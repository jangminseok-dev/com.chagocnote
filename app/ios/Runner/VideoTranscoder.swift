import AVFoundation
import Flutter
import UIKit

/// 영상 압축·포스터(④-3a 설계 3.2절) — Dart `core/proxy/video_transcoder.dart` 의 채널 규약을 따른다.
///
/// `transcode{source, outDir, maxSeconds}` 는 원본의 앞 maxSeconds 를 1080p mp4 로 내보내고
/// 1초 지점 프레임을 JPEG 포스터로 만든 뒤 `{video, thumb, width, height, durationSeconds, trimmed}`
/// 를 돌려준다. 진행률은 이벤트 채널로 0…1 을 보낸다. 외부 패키지 없이 AVFoundation 만 쓴다.
final class VideoTranscoderPlugin: NSObject, FlutterPlugin, FlutterStreamHandler {
  static let channelName = "chagocnote/video_transcoder"
  static let progressChannelName = "chagocnote/video_transcoder/progress"

  /// 포스터 긴 변 — 목록 썸네일 크기(사진 썸네일과 같은 300px).
  private static let posterSide: CGFloat = 300

  /// 진행 중인 내보내기 — 한 번에 하나만, `cancel` 이 멈출 대상.
  private var current: AVAssetExportSession?
  private var progressTimer: Timer?
  private var eventSink: FlutterEventSink?
  private let queue = DispatchQueue(label: "chagocnote.video_transcoder", qos: .userInitiated)

  static func register(with registrar: FlutterPluginRegistrar) {
    let plugin = VideoTranscoderPlugin()
    let channel = FlutterMethodChannel(name: channelName, binaryMessenger: registrar.messenger())
    registrar.addMethodCallDelegate(plugin, channel: channel)
    let progress = FlutterEventChannel(name: progressChannelName, binaryMessenger: registrar.messenger())
    progress.setStreamHandler(plugin)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "transcode":
      guard let args = call.arguments as? [String: Any],
            let source = args["source"] as? String,
            let outDir = args["outDir"] as? String,
            let maxSeconds = args["maxSeconds"] as? Int else {
        result(FlutterError(code: "UNSUPPORTED", message: "인자가 올바르지 않다", details: nil))
        return
      }
      // 대기열이 하나씩 보내므로 실제로는 오지 않지만, 겹치면 앞의 세션을 잃는다.
      guard current == nil else {
        result(FlutterError(code: "BUSY", message: "이미 압축 중이다", details: nil))
        return
      }
      transcode(source: URL(fileURLWithPath: source),
                outDir: URL(fileURLWithPath: outDir, isDirectory: true),
                maxSeconds: maxSeconds, result: result)
    case "cancel":
      // 멈춘 세션은 완료 콜백에서 .cancelled 로 끝나 CANCELLED 를 돌려준다.
      current?.cancelExport()
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

  // MARK: - 압축

  private func transcode(source: URL, outDir: URL, maxSeconds: Int, result: @escaping FlutterResult) {
    let asset = AVURLAsset(url: source)
    // 영상 트랙이 없으면(음성만·손상) 내보낼 것이 없다.
    guard asset.isReadable, !asset.tracks(withMediaType: .video).isEmpty else {
      result(FlutterError(code: "UNSUPPORTED", message: "읽을 수 있는 영상 트랙이 없다", details: nil))
      return
    }
    // 1080p 프리셋이 이 원본과 맞지 않으면 AVFoundation 이 내보내지 못한다.
    guard AVAssetExportSession.exportPresets(compatibleWith: asset).contains(AVAssetExportPreset1920x1080),
          let session = AVAssetExportSession(asset: asset, presetName: AVAssetExportPreset1920x1080) else {
      result(FlutterError(code: "UNSUPPORTED", message: "1080p 로 내보낼 수 없는 영상이다", details: nil))
      return
    }

    let video = outDir.appendingPathComponent("video.mp4")
    let thumb = outDir.appendingPathComponent("thumb.jpg")
    // 내보내기는 이미 있는 파일에 쓰지 못한다 — 다시 시도한 흔적을 지운다.
    try? FileManager.default.createDirectory(at: outDir, withIntermediateDirectories: true)
    try? FileManager.default.removeItem(at: video)

    let limit = CMTime(seconds: Double(maxSeconds), preferredTimescale: 600)
    let trimmed = CMTimeCompare(asset.duration, limit) > 0
    session.outputURL = video
    session.outputFileType = .mp4
    // moov 를 앞으로 — 받는 쪽이 끝까지 받기 전에 재생을 시작할 수 있다.
    session.shouldOptimizeForNetworkUse = true
    // 앞 maxSeconds 만 — 긴 원본은 자르고 trimmed 로 알린다.
    session.timeRange = CMTimeRange(start: .zero, duration: CMTimeMinimum(asset.duration, limit))

    current = session
    startProgress(session)

    session.exportAsynchronously { [weak self] in
      guard let self else { return }
      // 상태 확인·결과 읽기·포스터 만들기는 무거우므로 백그라운드 큐에서.
      self.queue.async {
        let outcome = self.finish(session: session, video: video, thumb: thumb, trimmed: trimmed)
        DispatchQueue.main.async {
          // 짧은 영상은 타이머가 한 번도 돌기 전에 끝난다 — 마지막 값(완료면 1)을 한 번 더 보낸다.
          self.eventSink?(Double(session.progress))
          self.stopProgress()
          self.current = nil
          result(outcome)
        }
      }
    }
  }

  /// 내보내기가 끝난 뒤 결과 영상을 다시 읽어 크기·길이·포스터를 만든다. 실패면 FlutterError.
  private func finish(session: AVAssetExportSession, video: URL, thumb: URL, trimmed: Bool) -> Any {
    switch session.status {
    case .cancelled:
      try? FileManager.default.removeItem(at: video)
      return FlutterError(code: "CANCELLED", message: nil, details: nil)
    case .completed:
      break
    default:
      try? FileManager.default.removeItem(at: video)
      return FlutterError(code: "UNSUPPORTED", message: session.error?.localizedDescription, details: nil)
    }

    // 원본이 아니라 압축본 기준이어야 서버에 올리는 값과 실제 파일이 맞는다.
    let output = AVURLAsset(url: video)
    let duration = CMTimeGetSeconds(output.duration)
    let durationSeconds = duration.isFinite ? Int(duration.rounded(.down)) : 0
    guard durationSeconds >= 1, let track = output.tracks(withMediaType: .video).first else {
      try? FileManager.default.removeItem(at: video)
      return FlutterError(code: "TOO_SHORT", message: nil, details: nil)
    }
    // 세로로 찍은 영상은 naturalSize 가 가로이고 회전이 preferredTransform 에 있다 — 화면에 보이는 크기로.
    let size = track.naturalSize.applying(track.preferredTransform)
    let width = Int(abs(size.width).rounded())
    let height = Int(abs(size.height).rounded())

    // 첫 프레임은 검은 화면이 흔하다 — 1초 지점(짧으면 가운데)을 포스터로.
    let generator = AVAssetImageGenerator(asset: output)
    generator.appliesPreferredTrackTransform = true
    generator.maximumSize = CGSize(width: Self.posterSide, height: Self.posterSide)
    let at = CMTimeMinimum(CMTime(seconds: 1, preferredTimescale: 600),
                           CMTimeMultiplyByRatio(output.duration, multiplier: 1, divisor: 2))
    do {
      let image = try generator.copyCGImage(at: at, actualTime: nil)
      guard let data = UIImage(cgImage: image).jpegData(compressionQuality: 0.8) else {
        return FlutterError(code: "UNSUPPORTED", message: "포스터를 JPEG 로 만들지 못했다", details: nil)
      }
      try data.write(to: thumb, options: .atomic)
    } catch {
      return FlutterError(code: "UNSUPPORTED", message: error.localizedDescription, details: nil)
    }

    return [
      "video": video.path,
      "thumb": thumb.path,
      "width": width,
      "height": height,
      "durationSeconds": durationSeconds,
      "trimmed": trimmed,
    ] as [String: Any]
  }

  // MARK: - 진행률

  /// 내보내기 세션은 진행률을 알려 주지 않는다 — 0.2초마다 읽어 이벤트로 보낸다.
  private func startProgress(_ session: AVAssetExportSession) {
    progressTimer?.invalidate()
    // 시작점 0 을 먼저 — 화면이 바로 진행 막대를 그린다.
    eventSink?(Double(session.progress))
    progressTimer = Timer.scheduledTimer(withTimeInterval: 0.2, repeats: true) { [weak self] _ in
      self?.eventSink?(Double(session.progress))
    }
  }

  private func stopProgress() {
    progressTimer?.invalidate()
    progressTimer = nil
  }
}
