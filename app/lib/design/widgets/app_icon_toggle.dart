import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import 'pressable.dart';

/// 아이콘 두세 개 중 하나를 고르는 토글(목록 ☰ / 격자 ▦).
///
/// 고른 쪽은 잉크 바탕 + 흰 아이콘, 나머지는 보조 색 아이콘이다.
/// [labels]는 스크린리더가 읽는 이름으로 [icons]와 같은 순서다.
class AppIconToggle extends StatelessWidget {
  const AppIconToggle({
    super.key,
    required this.icons,
    required this.labels,
    required this.currentIndex,
    required this.onChanged,
  }) : assert(icons.length == labels.length);

  final List<IconData> icons;
  final List<String> labels;
  final int currentIndex;
  final ValueChanged<int> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(color: AppColors.line, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < icons.length; i++)
            Pressable(
              onTap: () => onChanged(i),
              semanticLabel: labels[i],
              selected: i == currentIndex,
              // 탭 영역은 44×44, 칠하는 면은 그 안의 36×30 이다.
              child: SizedBox(
                width: 44,
                height: 44,
                child: Center(
                  child: Container(
                    width: 36,
                    height: 30,
                    decoration: BoxDecoration(
                      color: i == currentIndex
                          ? AppColors.ink
                          : const Color(0x00000000),
                      borderRadius: BorderRadius.circular(AppRadius.sm),
                    ),
                    alignment: Alignment.center,
                    child: Icon(
                      icons[i],
                      size: 18,
                      color: i == currentIndex
                          ? AppColors.white
                          : AppColors.secondary,
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
