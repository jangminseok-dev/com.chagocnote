import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 고를 수 있는 알약 칩("강아지 / 고양이", 질병 칩 등).
///
/// 고른 칩은 잉크 채움 + 흰 글자, 안 고른 칩은 흰 면 + 구분선 테두리다.
/// 여러 개를 묶을 때는 화면이 `Wrap`으로 늘어놓는다 — 하나만 고를지 여럿을
/// 고를지는 화면이 정한다.
class AppChoiceChip extends StatelessWidget {
  const AppChoiceChip({
    super.key,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      selected: selected,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
        decoration: BoxDecoration(
          color: selected ? AppColors.ink : AppColors.white,
          borderRadius: BorderRadius.circular(AppRadius.pill),
          border: Border.all(
            color: selected ? AppColors.ink : AppColors.line,
            width: 1,
          ),
        ),
        // 높이(Pressable 의 최소 44)는 채우되 가로는 글자 폭만큼만 — `alignment`를
        // 주면 Wrap·Column 안에서 가로 폭을 다 채워 버린다.
        child: Align(
          widthFactor: 1,
          // 이름표는 Pressable 이 읽는다 — 글자를 한 번 더 읽지 않게 뺀다.
          child: ExcludeSemantics(
            child: Text(
              label,
              style: AppTypography.body.copyWith(
                color: selected ? AppColors.white : AppColors.ink,
                fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
