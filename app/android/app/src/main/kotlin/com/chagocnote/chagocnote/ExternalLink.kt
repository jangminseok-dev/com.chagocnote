package com.chagocnote.chagocnote

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * 바깥 주소 열기(⑫ 설계 5.4) — Dart `core/proxy/external_link.dart` 의 채널 규약을 따른다.
 *
 * `open{url}` 은 `ACTION_VIEW`(+ `CATEGORY_BROWSABLE`)로 기기의 브라우저(또는 그 주소를 맡는 앱)에 맡기고
 * 곧바로 끝난다. 웹뷰가 아니다. `https` 이고 호스트가 있는 주소만 연다 — 아니면 `BAD_URL`, 열 앱이 없으면
 * `NO_BROWSER`. 주소를 오류 문구에 싣지 않는다.
 */
class ExternalLinkChannel(
    private val activity: Activity,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler {

    init {
        MethodChannel(messenger, CHANNEL).setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        if (call.method != "open") {
            result.notImplemented()
            return
        }
        val uri = call.argument<String>("url")?.let(Uri::parse)
        if (uri == null || uri.scheme?.lowercase() != "https" || uri.host.isNullOrEmpty()) {
            result.error("BAD_URL", "https 주소가 아니다", null)
            return
        }
        val view = Intent(Intent.ACTION_VIEW, uri).addCategory(Intent.CATEGORY_BROWSABLE)
        try {
            activity.startActivity(view)
            result.success(null)
        } catch (e: ActivityNotFoundException) {
            result.error("NO_BROWSER", "주소를 열 앱이 없다", null)
        }
    }

    private companion object {
        const val CHANNEL = "chagocnote/external_link"
    }
}
