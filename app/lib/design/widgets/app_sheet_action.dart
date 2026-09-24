import 'package:flutter/material.dart';

import '../tokens/app_spacing.dart';
import '../tokens/app_typography.dart';
import 'pressable.dart';

/// 시트(`AppSheet`) 안의 한 줄 항목 — 누르면 [onTap]. 보통 `Navigator.pop(값)`을 넘긴다.
class AppSheetAction extends StatelessWidget {
  const AppSheetAction({super.key, required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onTap,
      semanticLabel: label,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        alignment: Alignment.center,
        child: Text(label, style: AppTypography.body),
      ),
    );
  }
}
