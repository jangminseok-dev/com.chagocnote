import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';

/// 받아쓰기 중인 메모 칸의 컨트롤러 — 아직 굳지 않은 인식 결과([pending])만 회색으로 그린다.
///
/// 그리기만 한다. 구간을 정하고 글을 넣는 것은 받아쓰기 세션(`features/visit/state/dictation.dart`)이다.
class DictationTextEditingController extends TextEditingController {
  DictationTextEditingController({super.text});

  TextRange? _pending;

  /// 진행 중 구간. null 이면 회색 글이 없다.
  TextRange? get pending => _pending;

  set pending(TextRange? range) {
    if (range == _pending) return;
    _pending = range;
    notifyListeners();
  }

  @override
  TextSpan buildTextSpan({
    required BuildContext context,
    TextStyle? style,
    required bool withComposing,
  }) {
    final range = _pending;
    if (range == null) {
      return super.buildTextSpan(
        context: context,
        style: style,
        withComposing: withComposing,
      );
    }
    return TextSpan(
      style: style,
      children: [
        TextSpan(text: range.textBefore(text)),
        TextSpan(
          text: range.textInside(text),
          style: const TextStyle(color: AppColors.secondary),
        ),
        TextSpan(text: range.textAfter(text)),
      ],
    );
  }
}
