package com.chagocnote.chagocnote

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.speech.RecognitionListener
import android.speech.RecognitionSupport
import android.speech.RecognitionSupportCallback
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.annotation.RequiresApi
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * 음성 인식(④-3b 설계 3.5절) — Dart `core/proxy/speech_recognizer.dart` 의 채널 규약을 따른다.
 *
 * API 31+ 의 `createOnDeviceSpeechRecognizer` 로만 인식한다(기기 안에서만 — 서버로 소리를 보내지
 * 않는다). 30 이하는 기기 미지원이다. 결과는 이벤트 채널로 `{type: partial|final|ended|error,
 * text?, code?}` 를 보낸다. 오류 순서·의미는 iOS `SpeechRecognizer.swift` 와 같다 — 시작 전 실패도
 * `error` 뒤 `ended` 이벤트로 알리고, 권한 오류는 현재 권한 상태로 가른다, `stop` 뒤 오류는 `ended` 만.
 *
 * 인식기는 세션마다 만들고 끝나면 `destroy()` 한다. 채널 핸들러·리스너 모두 메인 스레드에서 돈다.
 * 권한 결과는 `MainActivity.onRequestPermissionsResult` 가 [onRequestPermissionsResult] 로 넘겨 준다.
 */
class SpeechRecognizerChannel(
    private val activity: Activity,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler, EventChannel.StreamHandler {

    private var eventSink: EventChannel.EventSink? = null

    /** 진행 중인 세션의 인식기 — 없으면 null. 리스너가 자기 인식기인지 견줘 늦은 콜백을 버린다. */
    private var recognizer: SpeechRecognizer? = null

    /** `stop` 을 받았다 — 이제 오는 오류는 알리지 않고 `ended` 만 보낸다. */
    private var stopping = false

    /** 권한 창의 답을 기다리는 호출. */
    private var permissionResult: MethodChannel.Result? = null

    init {
        MethodChannel(messenger, CHANNEL).setMethodCallHandler(this)
        EventChannel(messenger, EVENTS_CHANNEL).setStreamHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        when (call.method) {
            "availability" -> availability(call.argument<String>("locale") ?: DEFAULT_LOCALE, result)
            "requestPermission" -> requestPermission(result)
            "start" -> {
                start(call.argument<String>("locale") ?: DEFAULT_LOCALE)
                result.success(null)
            }
            "stop" -> {
                stop()
                result.success(null)
            }
            "cancel" -> {
                // Dart 가 취소를 알고 있다 — 이벤트 없이 조용히.
                teardown()
                result.success(null)
            }
            "openSettings" -> {
                activity.startActivity(
                    Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
                        .setData(Uri.fromParts("package", activity.packageName, null)),
                )
                result.success(null)
            }
            else -> result.notImplemented()
        }
    }

    override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
        eventSink = events
    }

    override fun onCancel(arguments: Any?) {
        eventSink = null
    }

    // 가용성·권한

    private fun availability(locale: String, result: MethodChannel.Result) {
        // 온디바이스 인식은 31 부터 — 그 아래이거나 이 기기에 온디바이스 인식 서비스가 없다.
        if (!onDeviceAvailable()) {
            result.success(mapOf("supported" to false, "reason" to "device"))
            return
        }
        // 31~32 는 언어를 미리 물을 수 없다 — `start` 의 언어 오류(unsupported)로 가른다.
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            result.success(mapOf("supported" to true))
            return
        }
        checkLocale(locale, result)
    }

    /** 이 언어 모델이 기기에 깔려 있는가. 내려받을 수 있기만 해도 `locale` — 내려받기를 유도하지 않는다. */
    @RequiresApi(Build.VERSION_CODES.TIRAMISU)
    private fun checkLocale(locale: String, result: MethodChannel.Result) {
        val checker = SpeechRecognizer.createOnDeviceSpeechRecognizer(activity)
        checker.checkRecognitionSupport(
            recognizeIntent(locale),
            activity.mainExecutor,
            object : RecognitionSupportCallback {
                override fun onSupportResult(support: RecognitionSupport) {
                    checker.destroy()
                    val language = locale.substringBefore('-')
                    val installed = support.installedOnDeviceLanguages.any {
                        it.equals(locale, ignoreCase = true) || it.equals(language, ignoreCase = true)
                    }
                    result.success(
                        if (installed) mapOf("supported" to true)
                        else mapOf("supported" to false, "reason" to "locale"),
                    )
                }

                override fun onError(error: Int) {
                    // 인식 서비스가 지원 여부조차 답하지 못한다 — 기기 쪽 문제로 본다.
                    checker.destroy()
                    result.success(mapOf("supported" to false, "reason" to "device"))
                }
            },
        )
    }

    private fun requestPermission(result: MethodChannel.Result) {
        if (permitted()) {
            result.success("granted")
            return
        }
        permissionResult = result
        activity.requestPermissions(arrayOf(Manifest.permission.RECORD_AUDIO), PERMISSION_REQUEST_CODE)
    }

    /** `MainActivity` 가 넘겨 주는 권한 창의 답. 우리 요청 코드가 아니면 무시한다. */
    fun onRequestPermissionsResult(requestCode: Int, grantResults: IntArray) {
        if (requestCode != PERMISSION_REQUEST_CODE) return
        val result = permissionResult ?: return
        permissionResult = null
        val granted = grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED
        result.success(if (granted) "granted" else "denied")
    }

    /** 지금 마이크 권한이 허용인가 — 시작 전과 오류를 읽을 때 쓴다. */
    private fun permitted(): Boolean =
        activity.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED

    private fun onDeviceAvailable(): Boolean =
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S &&
            SpeechRecognizer.isOnDeviceRecognitionAvailable(activity)

    // 듣기

    private fun start(locale: String) {
        // 앞 세션이 남아 있으면 조용히 치운다.
        teardown()

        if (!onDeviceAvailable()) {
            fail("unsupported")
            return
        }
        if (!permitted()) {
            fail("denied")
            return
        }

        val recognizer = SpeechRecognizer.createOnDeviceSpeechRecognizer(activity)
        this.recognizer = recognizer
        stopping = false
        recognizer.setRecognitionListener(Listener(recognizer))
        recognizer.startListening(recognizeIntent(locale))
    }

    /** 소리를 그만 받는다 — 뒤이어 `onResults` 또는 `onError` 가 온다. */
    private fun stop() {
        val recognizer = recognizer ?: return
        if (stopping) return
        stopping = true
        recognizer.stopListening()
    }

    private fun recognizeIntent(locale: String): Intent =
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE, locale)
            .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)

    private inner class Listener(private val owner: SpeechRecognizer) : RecognitionListener {
        /** 끝났거나 취소된 세션의 늦은 콜백이 아닌가. */
        private val current get() = recognizer === owner

        override fun onPartialResults(partialResults: Bundle?) {
            if (!current) return
            send(mapOf("type" to "partial", "text" to firstText(partialResults)))
        }

        override fun onResults(results: Bundle?) {
            if (!current) return
            val text = firstText(results)
            if (text.isEmpty()) {
                finish(if (stopping) null else "noSpeech")
            } else {
                send(mapOf("type" to "final", "text" to text))
                finish(null)
            }
        }

        override fun onError(error: Int) {
            if (!current) return
            // 멈추라고 한 뒤의 오류(말이 없었음 등)는 알리지 않는다 — 끝났다는 것만.
            finish(if (stopping) null else code(error))
        }

        override fun onReadyForSpeech(params: Bundle?) {}
        override fun onBeginningOfSpeech() {}
        override fun onRmsChanged(rmsdB: Float) {}
        override fun onBufferReceived(buffer: ByteArray?) {}
        override fun onEndOfSpeech() {}
        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    private fun firstText(bundle: Bundle?): String =
        bundle?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()

    /** 인식 오류를 채널 오류 코드로. */
    private fun code(error: Int): String {
        // 듣는 도중 설정에서 권한을 거둔 경우 — 코드보다 현재 상태가 정확하다(iOS 와 같은 규칙).
        if (!permitted()) return "denied"
        return when (error) {
            SpeechRecognizer.ERROR_NO_MATCH, SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "noSpeech"
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "denied"
            SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED, SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE -> "unsupported"
            else -> "failed"
        }
    }

    // 끝내기

    /** 세션을 정리하고 (오류가 있으면 먼저) `ended` 를 보낸다. */
    private fun finish(error: String?) {
        teardown()
        fail(error)
    }

    /** 오류가 있으면 알리고 `ended` 를 보낸다 — 시작 전 실패는 세션이 없으니 이것만. */
    private fun fail(error: String?) {
        if (error != null) send(mapOf("type" to "error", "code" to error))
        send(mapOf("type" to "ended"))
    }

    /** 세션을 치운다. 이벤트는 보내지 않는다. `recognizer` 를 비워 늦은 콜백을 버린다. */
    private fun teardown() {
        val recognizer = recognizer ?: return
        this.recognizer = null
        stopping = false
        recognizer.cancel()
        recognizer.destroy()
    }

    private fun send(event: Map<String, Any>) {
        // 듣는 쪽이 없으면 조용히 버린다.
        eventSink?.success(event)
    }

    private companion object {
        const val CHANNEL = "chagocnote/speech"
        const val EVENTS_CHANNEL = "chagocnote/speech/events"
        const val DEFAULT_LOCALE = "ko-KR"
        const val PERMISSION_REQUEST_CODE = 4301
    }
}
