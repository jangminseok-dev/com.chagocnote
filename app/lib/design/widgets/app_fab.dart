import 'package:flutter/material.dart';

import '../tokens/app_colors.dart';
import 'pressable.dart';

/// 검정 원 + 흰 더하기 아이콘의 플로팅 액션 버튼.
class AppFab extends StatelessWidget {
  const AppFab({
    super.key,
    required this.onPressed,
    this.icon = Icons.add,
    this.semanticLabel,
  });

  final VoidCallback onPressed;
  final IconData icon;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      onTap: onPressed,
      semanticLabel: semanticLabel ?? '추가',
      child: Container(
        width: 50,
        height: 50,
        decoration: const BoxDecoration(
          color: AppColors.ink,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Icon(icon, color: AppColors.white, size: 22),
      ),
    );
  }
}
