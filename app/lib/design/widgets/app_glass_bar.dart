import 'package:flutter/widgets.dart';

import '../bridge/glass_surface.dart';
import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// [AppGlassBar]의 슬롯 하나(아이콘 + 라벨).
class AppGlassBarItem {
  const AppGlassBarItem({required this.icon, required this.label});

  final IconData icon;
  final String label;
}

/// 하단 3슬롯 유리 탭바(캘린더 · 고객 · 매출).
///
/// 선택된 슬롯은 잉크 색, 나머지는 보조 색으로 그린다.
class AppGlassBar extends StatelessWidget {
  const AppGlassBar({
    super.key,
    required this.items,
    required this.currentIndex,
    required this.onTap,
  });

  final List<AppGlassBarItem> items;
  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return GlassSurface(
      radius: AppRadius.pill,
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
      child: SizedBox(
        height: 56,
        child: Row(
          children: [
            for (var i = 0; i < items.length; i++)
              Expanded(
                child: _BarItem(
                  item: items[i],
                  selected: i == currentIndex,
                  onTap: () => onTap(i),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _BarItem extends StatelessWidget {
  const _BarItem({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final AppGlassBarItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = selected ? AppColors.ink : AppColors.secondary;
    return Pressable(
      onTap: onTap,
      semanticLabel: item.label,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(item.icon, size: 19, color: color),
          const SizedBox(height: 2),
          Text(
            item.label,
            style: AppTypography.caption.copyWith(
              color: color,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}
