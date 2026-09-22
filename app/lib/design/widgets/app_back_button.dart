import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../l10n/app_strings.dart';
import '../tokens/app_colors.dart';
import 'pressable.dart';

/// 화면 머리에 두는 공통 뒤로 가기 버튼.
///
/// 기본 동작은 쌓인 화면이 있으면 뒤로 가고, 없으면 홈으로 간다.
/// [onTap]을 주면 그 동작으로 바꿀 수 있다.
class AppBackButton extends StatelessWidget {
  const AppBackButton({super.key, this.onTap});

  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Pressable(
      semanticLabel: AppStrings.back,
      onTap: onTap ?? () => _defaultBack(context),
      child: const Icon(Icons.arrow_back_ios_new, color: AppColors.ink),
    );
  }

  void _defaultBack(BuildContext context) {
    if (context.canPop()) {
      context.pop();
    } else {
      context.go('/home');
    }
  }
}
