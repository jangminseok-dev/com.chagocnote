import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import 'app_card.dart';

/// 불투명 흰 면 위, 잡이(grabber)가 달린 드래그-해제 바텀시트.
///
/// 시트는 스크롤 콘텐츠처럼 글을 읽는 곳이라 글래스를 쓰지 않는다(설계 6.2,
/// 최종 검토 D). 뒤에는 옅은 막([AppColors.scrim])을 깐다.
///
/// 드래그로 닫는 동작은 `showModalBottomSheet`의 기본 `enableDrag`를
/// 그대로 쓴다 — 별도 제스처 코드를 새로 만들지 않는다.
abstract final class AppSheet {
  static Future<T?> show<T>(
    BuildContext context, {
    required WidgetBuilder builder,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      backgroundColor: Colors.transparent,
      barrierColor: AppColors.scrim,
      isScrollControlled: true,
      builder: (context) => _AppSheetShell(builder: builder),
    );
  }
}

class _AppSheetShell extends StatelessWidget {
  const _AppSheetShell({required this.builder});

  final WidgetBuilder builder;

  @override
  Widget build(BuildContext context) {
    // 키보드가 올라오면 그만큼 아래 여백을 둬 시트 내용이 가려지지 않게 한다.
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: AppCard(
            padding: const EdgeInsets.symmetric(
              vertical: AppSpacing.md,
              horizontal: AppSpacing.lg,
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 36,
                  height: 4,
                  margin: const EdgeInsets.only(bottom: AppSpacing.md),
                  decoration: BoxDecoration(
                    color: AppColors.line,
                    borderRadius: BorderRadius.circular(AppRadius.pill),
                  ),
                ),
                builder(context),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
