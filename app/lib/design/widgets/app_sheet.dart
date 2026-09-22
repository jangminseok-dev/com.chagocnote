import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_spacing.dart';
import 'app_glass_card.dart';

/// 유리 표면 위, 잡이(grabber)가 달린 드래그-해제 바텀시트.
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
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.md),
        child: AppGlassCard(
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
    );
  }
}
