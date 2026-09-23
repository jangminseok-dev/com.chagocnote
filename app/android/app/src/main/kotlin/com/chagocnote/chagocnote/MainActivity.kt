package com.chagocnote.chagocnote

import android.content.Intent
import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

/**
 * 공유 받기(③-A3) — 다른 앱이 ACTION_SEND 로 넘긴 글을 Dart 로 전한다.
 *
 * 글만 오간다. 토큰·서버 호출은 Dart(앱 본체)가 한다. Dart 가 아직 뜨기 전에
 * 온 글은 들고 있다가 `getPending` 으로 준다(콜드 스타트). 떠 있으면 바로
 * `onSharedText` 로 부른다(launchMode 가 singleTask 라 onNewIntent 로 온다).
 */
class MainActivity : FlutterActivity() {
    private var channel: MethodChannel? = null
    private var pending: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        take(intent, coldStart = true)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        take(intent, coldStart = false)
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).also { ch ->
            ch.setMethodCallHandler { call, result ->
                if (call.method == "getPending") {
                    result.success(pending)
                    pending = null
                } else {
                    result.notImplemented()
                }
            }
        }
    }

    /**
     * [coldStart]면(onCreate) Dart 엔진이 아직 `onStart` 전이라 이 시점에 invoke 해도
     * 메시지가 버려진다("Dropping platform message on channel") — 그래서 콜드
     * 스타트에는 절대 invoke 하지 않고 들고만 있다가 `getPending` 으로 준다.
     * 떠 있을 때(onNewIntent)는 바로 invoke 하되, 받는 쪽이 없으면(notImplemented·
     * 오류) pending 으로 되돌려 다음 `getPending` 에서 줄 수 있게 한다(iOS 플러그인과
     * 같은 규칙).
     */
    private fun take(intent: Intent?, coldStart: Boolean) {
        if (intent?.action != Intent.ACTION_SEND || intent.type?.startsWith("text/") != true) return
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)?.trim().orEmpty()
        // 회전 등으로 같은 인텐트를 다시 읽지 않게 비운다.
        intent.removeExtra(Intent.EXTRA_TEXT)
        if (text.isEmpty()) return
        val ch = channel
        if (coldStart || ch == null) {
            pending = text
            return
        }
        ch.invokeMethod("onSharedText", text, object : MethodChannel.Result {
            override fun success(result: Any?) {}
            override fun error(errorCode: String, errorMessage: String?, errorDetails: Any?) {
                pending = text
            }
            override fun notImplemented() {
                pending = text
            }
        })
    }

    private companion object {
        const val CHANNEL = "com.chagocnote.app/share"
    }
}
