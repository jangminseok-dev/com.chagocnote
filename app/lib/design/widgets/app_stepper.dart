import 'package:flutter/material.dart';

import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// `[−] 값 [+]` — 정수를 한 칸씩 바꾼다. 범위 끝에서는 그쪽 단추가 눌리지 않는다.
/// 이름표([decreaseLabel]·[increaseLabel])는 부르는 쪽이 준다(모양 위젯은 문구를 모른다).
class AppStepper extends StatelessWidget {
  const AppStepper({
    super.key,
    required this.value,
    required this.min,
    required this.max,
    required this.label,
    required this.onChanged,
    required this.decreaseLabel,
    required this.increaseLabel,
  });

  final int value;
  final int min;
  final int max;
  final String Function(int value) label;
  final ValueChanged<int> onChanged;
  final String decreaseLabel;
  final String increaseLabel;

  @override
  Widget build(BuildContext context) {
    final canDown = value > min;
    final canUp = value < max;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Pressable(
          semanticLabel: decreaseLabel,
          onTap: canDown ? () => onChanged(value - 1) : null,
          child: Opacity(
            opacity: canDown ? 1 : 0.3,
            child: const Icon(Icons.remove, size: 20),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
          child: Text(label(value), style: AppTypography.titleKo),
        ),
        Pressable(
          semanticLabel: increaseLabel,
          onTap: canUp ? () => onChanged(value + 1) : null,
          child: Opacity(
            opacity: canUp ? 1 : 0.3,
            child: const Icon(Icons.add, size: 20),
          ),
        ),
      ],
    );
  }
}
