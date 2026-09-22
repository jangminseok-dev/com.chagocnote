import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// 상태 칩("완료" 등). 탭할 수 없는 표시 전용 요소라 [Pressable]을 쓰지
/// 않는다.
class AppChip extends StatelessWidget {
  const AppChip({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: label,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.xs,
        ),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(color: AppColors.secondary, width: 1),
        ),
        child: Text(
          label,
          style: AppTypography.caption.copyWith(color: AppColors.ink),
        ),
      ),
    );
  }
}
