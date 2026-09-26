import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'app_button.dart';

/// 오류 문구와 행동 버튼. 화면마다 복사하던 블록을 하나로.
///
/// [onRetry]가 있으면 [다시 시도], [onBack]이 있으면 [돌아가기]를 보인다. 다시 해도 같은 오류(권한·없음)는
/// [onRetry] 없이 [onBack]만 주고, 뒤로 갈 곳도 없으면 문구만 남는다(오류 화면 다듬기 설계 2절).
///
/// 기본은 화면 가운데(목록·상세의 `AsyncValue.when(error: …)` 자리). [AppErrorRetry.inline]은
/// 흐름 안에 여백을 두고 놓이고(달력 아래, 카드 안), [AppErrorRetry.row]는 한 줄(작은 글씨 +
/// 버튼)로 좁은 자리에 들어간다(시간 칸, 임시 휴무 목록).
class AppErrorRetry extends StatelessWidget {
  const AppErrorRetry({
    super.key,
    required this.message,
    this.onRetry,
    this.onBack,
  }) : _layout = _Layout.centered;

  const AppErrorRetry.inline({
    super.key,
    required this.message,
    this.onRetry,
    this.onBack,
  }) : _layout = _Layout.inline;

  const AppErrorRetry.row({
    super.key,
    required this.message,
    this.onRetry,
    this.onBack,
  }) : _layout = _Layout.row;

  final String message;
  final VoidCallback? onRetry;
  final VoidCallback? onBack;
  final _Layout _layout;

  @override
  Widget build(BuildContext context) {
    final button = onRetry != null
        ? AppButton(label: AppStrings.retry, onPressed: onRetry)
        : onBack != null
        ? AppButton(label: AppStrings.goBack, onPressed: onBack)
        : null;
    return switch (_layout) {
      _Layout.centered => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
            if (button != null) ...[
              const SizedBox(height: AppSpacing.lg),
              button,
            ],
          ],
        ),
      ),
      _Layout.inline => Padding(
        padding: const EdgeInsets.all(AppSpacing.lg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              message,
              style: AppTypography.body,
              textAlign: TextAlign.center,
            ),
            if (button != null) ...[
              const SizedBox(height: AppSpacing.md),
              button,
            ],
          ],
        ),
      ),
      _Layout.row => Row(
        children: [
          Expanded(child: Text(message, style: AppTypography.caption)),
          ?button,
        ],
      ),
    };
  }
}

enum _Layout { centered, inline, row }
