import 'package:flutter/material.dart';

import '../../l10n/app_strings.dart';
import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 이미 보이는 내용 위에 까는 얇은 오류 띠 — 새로 불러오다 실패해도 받은 데이터는 그대로 둔다
/// (오류 화면 다듬기 설계 3.1). 스크롤 콘텐츠 위라 글래스가 아니라 불투명 흰 면이다.
///
/// [offline]이면 와이파이 끊김 아이콘, 아니면 느낌표. [onRetry]가 있으면 오른쪽에 [다시 시도].
class AppErrorBanner extends StatelessWidget {
  const AppErrorBanner({
    super.key,
    required this.message,
    this.offline = false,
    this.onRetry,
  });

  final String message;
  final bool offline;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      // 높이는 [다시 시도]의 누르는 자리(44)에 맞춘다 — 버튼이 없어도 띠 높이가 같다.
      constraints: const BoxConstraints(minHeight: 44),
      padding: const EdgeInsets.only(left: AppSpacing.lg),
      decoration: const BoxDecoration(
        color: AppColors.white,
        border: Border(bottom: BorderSide(color: AppColors.line)),
      ),
      child: Row(
        children: [
          Icon(
            offline ? Icons.wifi_off_rounded : Icons.error_outline_rounded,
            size: 16,
            color: AppColors.ink,
          ),
          const SizedBox(width: AppSpacing.sm),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: Text(message, style: AppTypography.caption),
            ),
          ),
          // 버튼이 없으면 오른쪽 여백만.
          if (onRetry == null) const SizedBox(width: AppSpacing.lg),
          if (onRetry != null)
            Pressable(
              semanticLabel: AppStrings.retry,
              onTap: onRetry,
              child: SizedBox(
                height: 44,
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.lg,
                  ),
                  child: Center(
                    child: Text(
                      AppStrings.retry,
                      style: AppTypography.caption.copyWith(
                        color: AppColors.ink,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
