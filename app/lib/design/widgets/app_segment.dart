import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 밑줄로 선택 상태를 표시하는 텍스트 탭("캘린더 · 기록").
class AppSegment extends StatelessWidget {
  const AppSegment({
    super.key,
    required this.labels,
    required this.currentIndex,
    required this.onChanged,
  });

  final List<String> labels;
  final int currentIndex;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (var i = 0; i < labels.length; i++) ...[
          if (i > 0) const SizedBox(width: AppSpacing.lg),
          _SegmentTab(
            label: labels[i],
            selected: i == currentIndex,
            onTap: () => onChanged(i),
          ),
        ],
      ],
    );
  }
}

class _SegmentTab extends StatelessWidget {
  const _SegmentTab({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.ink : AppColors.secondary;
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      // IntrinsicWidth로 밑줄 너비를 텍스트 너비에 맞춘다. Row 안에서
      // flex가 아닌 자식은 주축 폭이 무한대로 느슨하게 주어지는데,
      // IntrinsicWidth가 그 안에서 실제 필요한 유한 폭을 계산해준다.
      child: IntrinsicWidth(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              label,
              textAlign: TextAlign.center,
              style: AppTypography.body.copyWith(
                color: color,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w400,
              ),
            ),
            const SizedBox(height: AppSpacing.xs),
            Container(
              height: 2,
              color: selected ? AppColors.ink : const Color(0x00000000),
            ),
          ],
        ),
      ),
    );
  }
}
