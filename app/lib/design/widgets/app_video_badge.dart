import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_typography.dart';

/// 영상 타일 위 재생 표시와 길이("0:42"). 타일·넘기기·피드 카드가 같이 쓴다.
///
/// 반투명 검정 알약 안에 흰 재생 아이콘과 길이를 둔다. 자리(보통 왼쪽 아래)는 부모가 정한다.
/// [compact]이거나 [durationSeconds]가 null(압축 중이라 아직 모른다)이면 아이콘만.
class AppVideoBadge extends StatelessWidget {
  const AppVideoBadge({super.key, this.durationSeconds, this.compact = false});

  final int? durationSeconds;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final seconds = compact ? null : durationSeconds;
    return Container(
      padding: EdgeInsets.fromLTRB(2, 2, seconds == null ? 2 : 6, 2),
      decoration: BoxDecoration(
        color: AppColors.ink.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(AppRadius.pill),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.play_arrow_rounded,
            size: 16,
            color: AppColors.white,
          ),
          if (seconds != null)
            Text(
              formatDuration(seconds),
              style: AppTypography.caption.copyWith(
                fontSize: 10,
                height: 1,
                color: AppColors.white,
              ),
            ),
        ],
      ),
    );
  }
}

/// 초를 "m:ss" 로. 3600 이상은 "h:mm:ss".
String formatDuration(int seconds) {
  final h = seconds ~/ 3600;
  final m = seconds % 3600 ~/ 60;
  final s = (seconds % 60).toString().padLeft(2, '0');
  if (h > 0) return '$h:${m.toString().padLeft(2, '0')}:$s';
  return '$m:$s';
}
