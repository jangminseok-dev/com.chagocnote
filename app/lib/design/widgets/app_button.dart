import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 알약 모양 버튼("기록 수정" 등).
///
/// `filled`이면 잉크색 채움 + 흰 글자, 아니면 아웃라인. `busy`면 작은
/// 스피너를 보여주고 탭을 막는다. `onPressed`가 null이거나 `busy`면
/// 비활성 색(보조 텍스트 색)으로 그린다.
class AppButton extends StatelessWidget {
  const AppButton({
    super.key,
    required this.label,
    required this.onPressed,
    this.filled = false,
    this.busy = false,
    this.icon,
  });

  final String label;
  final VoidCallback? onPressed;
  final bool filled;
  final bool busy;
  final IconData? icon;

  bool get _enabled => onPressed != null && !busy;

  @override
  Widget build(BuildContext context) {
    final Color background = filled
        ? (_enabled ? AppColors.ink : AppColors.line)
        : Colors.transparent;
    final Color foreground = filled
        ? AppColors.white
        : (_enabled ? AppColors.ink : AppColors.secondary);
    final Color borderColor = _enabled ? AppColors.ink : AppColors.secondary;

    return Pressable(
      onTap: _enabled ? onPressed : null,
      semanticLabel: label,
      child: Container(
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
        decoration: BoxDecoration(
          color: background,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: filled ? null : Border.all(color: borderColor, width: 1),
        ),
        alignment: Alignment.center,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (busy) ...[
              SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(foreground),
                ),
              ),
              const SizedBox(width: AppSpacing.sm),
            ] else if (icon != null) ...[
              Icon(icon, size: 16, color: foreground),
              const SizedBox(width: AppSpacing.sm),
            ],
            Text(label, style: AppTypography.bodyStrong.copyWith(color: foreground)),
          ],
        ),
      ),
    );
  }
}
