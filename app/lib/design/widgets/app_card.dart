import 'package:flutter/widgets.dart';

import '../tokens/app_colors.dart';
import '../tokens/app_radius.dart';
import '../tokens/app_shadows.dart';
import '../tokens/app_spacing.dart';

/// 목록 행·카드·시트에 쓰는 불투명 카드.
///
/// 설계 6.2: 글래스는 떠 있는 조작 계층(탭바 등)에만 쓰고, 스크롤 콘텐츠와
/// 시트는 이 흰 면(구분선 테두리 + 옅은 그림자)으로 그린다 — 보조 문구가
/// 뒤 배경에 묻히지 않고 또렷이 읽힌다.
class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(AppSpacing.lg),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: const BorderRadius.all(Radius.circular(AppRadius.lg)),
        border: Border.all(color: AppColors.line, width: 1),
        boxShadow: AppShadows.soft,
      ),
      child: child,
    );
  }
}
