import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';

/// 화면 아래에 잠깐 떠서 알리는 한 줄("이미 같은 시각에 잡힌 예약이 있어요").
///
/// 루트 `MaterialApp`의 `ScaffoldMessenger`에 띄우므로, 부른 화면이 곧 닫혀도
/// 그 아래 화면 위에 남는다. 확인이 필요한 일에는 시트를 쓴다 — 이것은
/// 답을 받지 않는 알림이다.
abstract final class AppSnackBar {
  static void show(BuildContext context, String text) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            text,
            style: AppTypography.body.copyWith(color: AppColors.white),
          ),
          backgroundColor: AppColors.ink,
          behavior: SnackBarBehavior.floating,
          margin: const EdgeInsets.fromLTRB(
            AppSpacing.lg,
            0,
            AppSpacing.lg,
            AppSpacing.lg,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(AppRadius.md),
          ),
          duration: const Duration(seconds: 3),
        ),
      );
  }
}
