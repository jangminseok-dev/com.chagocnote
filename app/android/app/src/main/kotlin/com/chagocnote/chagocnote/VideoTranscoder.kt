package com.chagocnote.chagocnote

import android.content.Context
import android.graphics.Bitmap
import android.media.MediaMetadataRetriever
import android.net.Uri
import android.os.Handler
import android.os.Looper
import androidx.annotation.OptIn
import androidx.media3.common.MediaItem
import androidx.media3.common.MimeTypes
import androidx.media3.common.util.UnstableApi
import androidx.media3.effect.Presentation
import androidx.media3.transformer.Composition
import androidx.media3.transformer.EditedMediaItem
import androidx.media3.transformer.Effects
import androidx.media3.transformer.ExportException
import androidx.media3.transformer.ExportResult
import androidx.media3.transformer.ProgressHolder
import androidx.media3.transformer.Transformer
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import java.io.File
import java.io.FileOutputStream
import kotlin.concurrent.thread
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

/**
 * 영상 압축·포스터(④-3a 설계 3.3절) — Dart `core/proxy/video_transcoder.dart` 의 채널 규약을 따른다.
 *
 * `transcode{source, outDir, maxSeconds}` 는 원본의 앞 maxSeconds 를 1080p H.264·AAC mp4 로
 * 내보내고 1초 지점 프레임을 JPEG 포스터로 만든 뒤 `{video, thumb, width, height,
 * durationSeconds, trimmed}` 를 돌려준다. 진행률은 이벤트 채널로 0…1 을 보낸다.
 * 오류 코드·순서는 iOS `VideoTranscoder.swift` 와 같다.
 *
 * Media3 `Transformer` 는 만든 스레드의 Looper 로 콜백하고 그 스레드에서만 부를 수 있다 —
 * 채널 핸들러가 메인 스레드에서 돌므로 만들기·`start`·`cancel`·폴링 모두 메인에서 한다.
 */
@OptIn(UnstableApi::class)
class VideoTranscoderChannel(
    private val context: Context,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler, EventChannel.StreamHandler {

    private val main = Handler(Looper.getMainLooper())

    /** 진행 중인 압축 — 한 번에 하나만, `cancel` 이 멈출 대상. */
    private var current: Transformer? = null
    private var pendingResult: MethodChannel.Result? = null
    private var pendingVideo: File? = null
    private var lastProgress = 0.0
    private var eventSink: EventChannel.EventSink? = null
    private var poll: Runnable? = null

    init {
        MethodChannel(messenger, CHANNEL).setMethodCallHandler(this)
        EventChannel(messenger, PROGRESS_CHANNEL).setStreamHandler(this)
    }

    override fun onMethodCall(call: io.flutter.plugin.common.MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "transcode" -> {
                val source = call.argument<String>("source")
                val outDir = call.argument<String>("outDir")
                val maxSeconds = call.argument<Int>("maxSeconds")
                if (source == null || outDir == null || maxSeconds == null) {
                    result.error("UNSUPPORTED", "인자가 올바르지 않다", null)
                    return
                }
                // 대기열이 하나씩 보내므로 실제로는 오지 않지만, 겹치면 앞의 압축을 잃는다.
                if (current != null) {
                    result.error("BUSY", "이미 압축 중이다", null)
                    return
                }
                transcode(File(source), File(outDir), maxSeconds, result)
            }
            "cancel" -> {
                cancel()
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    // region EventChannel.StreamHandler

    override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
        eventSink = events
    }

    override fun onCancel(arguments: Any?) {
        eventSink = null
    }

    // endregion

    private fun transcode(source: File, outDir: File, maxSeconds: Int, result: MethodChannel.Result) {
        // 영상 트랙이 없으면(음성만·손상) 내보낼 것이 없다.
        val info = readInfo(source)
        if (info == null) {
            result.error("UNSUPPORTED", "읽을 수 있는 영상 트랙이 없다", null)
            return
        }

        val video = File(outDir, "video.mp4")
        // 다시 시도한 흔적을 지운다.
        outDir.mkdirs()
        video.delete()

        val limitMs = maxSeconds * 1000L
        val trimmed = info.durationMs > limitMs
        // 앞 maxSeconds 만 — 긴 원본은 자르고 trimmed 로 알린다.
        val mediaItem = MediaItem.Builder()
            .setUri(Uri.fromFile(source))
            .setClippingConfiguration(
                MediaItem.ClippingConfiguration.Builder()
                    .setEndPositionMs(min(info.durationMs, limitMs))
                    .build()
            )
            .build()
        val edited = EditedMediaItem.Builder(mediaItem)
            .setEffects(Effects(emptyList(), listOf(Presentation.createForHeight(targetHeight(info)))))
            .build()

        val transformer = Transformer.Builder(context)
            .setVideoMimeType(MimeTypes.VIDEO_H264)
            .setAudioMimeType(MimeTypes.AUDIO_AAC)
            .addListener(object : Transformer.Listener {
                override fun onCompleted(composition: Composition, exportResult: ExportResult) {
                    lastProgress = 1.0
                    // 결과 읽기·포스터 만들기는 무거우므로 메인 밖에서.
                    thread(name = "chagocnote.video_transcoder") {
                        val outcome = finish(video, File(outDir, "thumb.jpg"), trimmed)
                        main.post { complete(outcome) }
                    }
                }

                override fun onError(
                    composition: Composition,
                    exportResult: ExportResult,
                    exportException: ExportException,
                ) {
                    video.delete()
                    complete(Outcome.Failure("UNSUPPORTED", exportException.toString()))
                }
            })
            .build()

        current = transformer
        pendingResult = result
        pendingVideo = video
        lastProgress = 0.0
        transformer.start(edited, video.path)
        startProgress(transformer)
    }

    /**
     * `Transformer.cancel()` 은 리스너를 부르지 않는다 — 여기서 CANCELLED 로 끝낸다.
     */
    private fun cancel() {
        val transformer = current ?: return
        transformer.cancel()
        pendingVideo?.delete()
        complete(Outcome.Failure("CANCELLED", null))
    }

    /** 압축 하나를 끝낸다 — 마지막 진행률을 보내고 상태를 비운 뒤 Dart 에 답한다. 메인에서만. */
    private fun complete(outcome: Outcome) {
        val result = pendingResult ?: return
        // 짧은 영상은 폴링이 한 번도 돌기 전에 끝난다 — 마지막 값(완료면 1)을 한 번 더 보낸다.
        eventSink?.success(lastProgress)
        stopProgress()
        current = null
        pendingResult = null
        pendingVideo = null
        when (outcome) {
            is Outcome.Success -> result.success(outcome.value)
            is Outcome.Failure -> result.error(outcome.code, outcome.message, null)
        }
    }

    /** 압축본을 다시 읽어 크기·길이·포스터를 만든다. 원본이 아니라 압축본 기준이어야 서버에 올리는 값과 실제 파일이 맞는다. */
    private fun finish(video: File, thumb: File, trimmed: Boolean): Outcome {
        val info = readInfo(video)
        val durationSeconds = ((info?.durationMs ?: 0L) / 1000L).toInt()
        if (info == null || durationSeconds < 1) {
            video.delete()
            return Outcome.Failure("TOO_SHORT", null)
        }

        // 첫 프레임은 검은 화면이 흔하다 — 1초 지점(짧으면 가운데)을 포스터로.
        val atUs = min(1_000_000L, info.durationMs * 1000L / 2)
        val retriever = MediaMetadataRetriever()
        try {
            retriever.setDataSource(video.path)
            // 프레임은 회전 메타가 반영된 채로 나온다.
            val frame = retriever.getFrameAtTime(atUs, MediaMetadataRetriever.OPTION_CLOSEST_SYNC)
                ?: return Outcome.Failure("UNSUPPORTED", "포스터 프레임을 읽지 못했다")
            val scale = POSTER_SIDE / max(frame.width, frame.height).toDouble()
            val poster = if (scale < 1) {
                Bitmap.createScaledBitmap(
                    frame,
                    (frame.width * scale).roundToInt(),
                    (frame.height * scale).roundToInt(),
                    true,
                )
            } else {
                frame
            }
            FileOutputStream(thumb).use { poster.compress(Bitmap.CompressFormat.JPEG, 80, it) }
        } catch (e: Exception) {
            return Outcome.Failure("UNSUPPORTED", e.toString())
        } finally {
            retriever.release()
        }

        return Outcome.Success(
            mapOf(
                "video" to video.path,
                "thumb" to thumb.path,
                "width" to info.width,
                "height" to info.height,
                "durationSeconds" to durationSeconds,
                "trimmed" to trimmed,
            )
        )
    }

    // region 진행률

    /** Transformer 는 진행률을 알려 주지 않는다 — 200ms 마다 읽어 이벤트로 보낸다. */
    private fun startProgress(transformer: Transformer) {
        stopProgress()
        // 시작점 0 을 먼저 — 화면이 바로 진행 막대를 그린다.
        eventSink?.success(lastProgress)
        val holder = ProgressHolder()
        val runnable = object : Runnable {
            override fun run() {
                if (transformer.getProgress(holder) == Transformer.PROGRESS_STATE_AVAILABLE) {
                    lastProgress = holder.progress / 100.0
                    eventSink?.success(lastProgress)
                }
                main.postDelayed(this, PROGRESS_INTERVAL_MS)
            }
        }
        poll = runnable
        main.postDelayed(runnable, PROGRESS_INTERVAL_MS)
    }

    private fun stopProgress() {
        poll?.let { main.removeCallbacks(it) }
        poll = null
    }

    // endregion

    private class Info(val durationMs: Long, val width: Int, val height: Int)

    private sealed class Outcome {
        class Success(val value: Map<String, Any>) : Outcome()
        class Failure(val code: String, val message: String?) : Outcome()
    }

    /** 길이·회전을 반영한 가로·세로. 열 수 없거나 영상 트랙이 없으면 null. */
    private fun readInfo(file: File): Info? {
        val retriever = MediaMetadataRetriever()
        return try {
            retriever.setDataSource(file.path)
            if (retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_HAS_VIDEO) != "yes") return null
            val durationMs = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)?.toLongOrNull() ?: 0L
            val w = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_WIDTH)?.toIntOrNull() ?: 0
            val h = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_HEIGHT)?.toIntOrNull() ?: 0
            val rotation = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_VIDEO_ROTATION)?.toIntOrNull() ?: 0
            // 세로로 찍은 영상은 가로로 저장되고 회전이 메타에 있다 — 화면에 보이는 크기로.
            if (rotation % 180 != 0) Info(durationMs, h, w) else Info(durationMs, w, h)
        } catch (e: Exception) {
            null
        } finally {
            retriever.release()
        }
    }

    /**
     * 출력 높이 — iOS 1920×1080 프리셋과 같게 짧은 변 1080·긴 변 1920 안에 들어가도록 줄인다(키우지 않는다).
     * Presentation 은 회전이 반영된 프레임에 걸리므로 화면에 보이는 크기로 계산한다. 인코더가 짝수를 요구한다.
     */
    private fun targetHeight(info: Info): Int {
        val short = min(info.width, info.height)
        val long = max(info.width, info.height)
        val scale = min(1.0, min(1080.0 / short, 1920.0 / long))
        if (scale >= 1.0) return info.height
        return ((info.height * scale / 2).roundToInt()) * 2
    }

    private companion object {
        const val CHANNEL = "chagocnote/video_transcoder"
        const val PROGRESS_CHANNEL = "chagocnote/video_transcoder/progress"
        const val PROGRESS_INTERVAL_MS = 200L

        /** 포스터 긴 변 — 목록 썸네일 크기(사진 썸네일과 같은 300px). */
        const val POSTER_SIDE = 300
    }
}
