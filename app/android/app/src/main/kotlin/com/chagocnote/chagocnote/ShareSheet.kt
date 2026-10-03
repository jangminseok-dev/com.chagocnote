package com.chagocnote.chagocnote

import android.app.Activity
import android.content.Intent
import io.flutter.plugin.common.BinaryMessenger
import io.flutter.plugin.common.MethodCall
import io.flutter.plugin.common.MethodChannel

/**
 * 공유 시트(⑤ 설계 9.2) — Dart `core/proxy/share_sheet.dart` 의 채널 규약을 따른다.
 *
 * `shareText{text, x, y, width, height}` 는 `ACTION_SEND` 선택기를 띄우고 곧바로 끝난다(보냈는지·
 * 취소했는지는 돌려주지 않는다). 글자만 넘긴다. 사각형은 아이패드용이라 여기서는 쓰지 않는다.
 */
class ShareSheetChannel(
    private val activity: Activity,
    messenger: BinaryMessenger,
) : MethodChannel.MethodCallHandler {

    init {
        MethodChannel(messenger, CHANNEL).setMethodCallHandler(this)
    }

    override fun onMethodCall(call: MethodCall, result: MethodChannel.Result) {
        if (call.method != "shareText") {
            result.notImplemented()
            return
        }
        val text = call.argument<String>("text")
        if (text == null) {
            result.error("BAD_ARGS", "인자가 올바르지 않다", null)
            return
        }
        val send = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text)
        // 이 앱도 글 공유를 받는다(③-A3) — 빼지 않으면 선택기에 차곡노트가 뜨고, 누르면 알림장 링크가
        // 카톡 초안 화면으로 들어온다.
        val chooser = Intent.createChooser(send, null)
            .putExtra(Intent.EXTRA_EXCLUDE_COMPONENTS, arrayOf(activity.componentName))
        activity.startActivity(chooser)
        result.success(null)
    }

    private companion object {
        const val CHANNEL = "chagocnote/share_sheet"
    }
}
